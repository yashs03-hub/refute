"""A conversation about an experiment, where every claim is computed.

Modelled on Paperclip's chat, and on the one discipline that makes it
trustworthy: *cite from what you actually read, and never paraphrase beyond what
the text supports*. Paperclip's citation is a line number in a paper.

**refute's citation is the simulation.**

So the rule here is the same shape and just as strict: every statement about a
design carries the computed evidence that produced it. "This is underpowered"
is not an answer; "power 2% over 400 simulated plates, 50% of wells lost before
the endpoint" is, and you can ask why and get another computed answer.

WHAT THE MODEL IS ALLOWED TO DO, and it is very little:

    extract   prose -> DesignSpec. Models are reliable at this.
    nothing else.

Intent routing is keyword-based, not model-based - which is partly principle and
partly practical. Principle: routing to a tool is not a judgement, and keeping it
inspectable means a wrong answer is a bug rather than a mood. Practical: once a
design is in hand, every follow-up runs offline, so the conversation keeps
working when the network does not.

The model is NEVER asked whether a design is good, what to change, or why
something failed. Those come from `score_design` and `advise`. A chat interface
is exactly where that boundary erodes, because it feels natural to let the
assistant answer - so the boundary is enforced here in code, not in a docstring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from .advise import advise
from .calibration import DEFAULT_PARAMS, PLATE_WELLS, TwinParams
from .design import DesignSpec, OutOfTwinScopeError
from .score import DesignScore, score_design
from .twins import DEFAULT_ASSAY, get_twin

# Follow-ups are routed on these rather than by a model. Order matters: the
# first list whose pattern matches wins, so put the specific before the general.
INTENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("advise", (r"\bwhat (should|can|do) i (change|do|fix)", r"\bhow (do|can) i fix",
                r"\bimprove\b", r"\bsuggest", r"\bfix it\b", r"\badvice\b")),
    ("whatif", (r"\bwhat if\b", r"\bif i\b", r"\btry\b", r"\bsuppose\b",
                r"\binstead of\b")),
    ("why", (r"^why\b", r"\bwhy (is|did|does|was)\b", r"\bexplain\b",
             r"\breason", r"\bwhat went wrong")),
    ("scale", (r"\bhow many\b", r"\bwells (do|would) i need", r"\bsample size\b",
               r"\bpower\b")),
)

# Levers a "what if" can name, mapped to the field they change. Deliberately a
# closed list: a free-form perturbation would need the model to decide what the
# user meant, which is the boundary this module exists to hold.
WHATIF_LEVERS: dict[str, tuple[str, ...]] = {
    "antifibrinolytic": ("aprotinin", "antifibrinolytic", "tranexamic",
                         "aminocaproic", "protease inhibitor"),
    "replicates": ("replicate", "wells per", "n per", "more wells"),
    "endpoint": ("endpoint", "day ", "finish", "stop at", "earlier", "shorter"),
    "narrow": ("fewer arms", "two arms", "drop the", "narrow"),
}


@dataclass
class Turn:
    """One exchange. `evidence` is the citation and is never optional."""

    intent: str
    answer: str
    evidence: list[str] = field(default_factory=list)
    score: Any | None = None
    called_model: bool = False

    def render(self) -> str:
        out = [self.answer]
        if self.evidence:
            out.append("")
            out.append("  computed from:")
            out.extend(f"    {e}" for e in self.evidence)
        return "\n".join(out)


def _cite(score: Any, n_sims: int, capacity: int = PLATE_WELLS) -> list[str]:
    """The citation. Numbers a reader can check, plus how they were produced."""
    if hasattr(score, "mean_lysed_fraction"):
        loss_str = f"{score.mean_lysed_fraction:.0%} of wells lost by the endpoint"
        unit_str = f"mean usable wells per plate {score.mean_usable_wells:.1f}"
    else:
        loss_str = f"mean animals scored {getattr(score, 'mean_animals_scored', 0):.1f}"
        unit_str = f"mean animals scored {getattr(score, 'mean_animals_scored', 0):.1f}"

    lines = [
        f"{n_sims} simulated runs of the design as extracted",
        f"power {score.power:.0%} · testable {score.testable_rate:.0%} · {loss_str}",
        unit_str,
    ]
    if score.replicates_needed > 0:
        lines.append(
            f"needs ~{score.replicates_needed} units per arm; the apparatus "
            f"holds {capacity}"
        )
    else:
        lines.append(
            "required replication NOT estimable - too many units were lost for "
            "the surviving sample to support an estimate"
        )
    if score.verdict_sensitive_to_assumption:
        lines.append(
            "⚠ this verdict does not survive the plausible range of an ASSUMED "
            "constant"
        )
    return lines



class Session:
    """A conversation about one design.

    `extractor` is injected so the whole class is testable without a credential,
    and so the one model-dependent step is visible in the constructor rather
    than buried in a call site.
    """

    def __init__(
        self,
        extractor: Callable[[str], Any] | None = None,
        params: Any = None,
        n_sims: int = 400,
        assay: str = DEFAULT_ASSAY,
    ):
        self.assay = assay
        self.twin = get_twin(assay)
        self._extract = extractor
        self.params = params
        self.n_sims = n_sims
        self.design: Any | None = None
        self.score: Any | None = None
        self.history: list[Turn] = []

    # -- routing ---------------------------------------------------------

    @staticmethod
    def classify(text: str) -> str:
        lowered = text.lower()
        for intent, patterns in INTENT_PATTERNS:
            if any(re.search(p, lowered) for p in patterns):
                return intent
        return "design"

    def ask(self, text: str) -> Turn:
        turn = self._ask(text)
        self.history.append(turn)
        return turn

    def _ask(self, text: str) -> Turn:
        intent = self.classify(text)
        if self.design is None and intent != "design":
            return Turn(
                intent=intent,
                answer=(
                    "Describe the experiment first - the arms, how many "
                    "replicates each, when you treat, when you measure, and what "
                    "the endpoint is. Everything after that is computed from it."
                ),
            )
        handler = {
            "design": self._handle_design,
            "advise": self._handle_advise,
            "whatif": self._handle_whatif,
            "why": self._handle_why,
            "scale": self._handle_scale,
        }[intent]
        return handler(text)

    # -- handlers --------------------------------------------------------

    def _handle_design(self, text: str) -> Turn:
        if self._extract is None:
            return Turn(
                intent="design",
                answer=(
                    "No extractor is configured, so prose cannot be read into a "
                    "design. Pass a design spec directly, or configure one."
                ),
            )
        try:
            spec = self._extract(text)
        except Exception as exc:
            # A parsing failure must never be reported as a bad design.
            return Turn(
                intent="design",
                answer=(
                    f"Could not read that into a design ({type(exc).__name__}). "
                    "That is a parsing failure on our side, not a judgement about "
                    "your experiment - try describing the arms and timings more "
                    "plainly."
                ),
                called_model=True,
            )

        try:
            kwargs: dict[str, Any] = {"n_sims": self.n_sims}
            if self.params is not None:
                kwargs["params"] = self.params
            score = self.twin.score_fn(spec, **kwargs)
        except OutOfTwinScopeError as exc:
            return Turn(
                intent="design",
                answer=(
                    "I can't score this, and that is a limit of the simulator "
                    "rather than a problem with your design:\n  - "
                    + "\n  - ".join(exc.reasons)
                    + "\n\nThe twin models an anchored fibrin gel measured by "
                    "area. For anything else, `refute tier0` still answers the "
                    "power question from your own effect size and SD."
                ),
                called_model=True,
            )


        self.design, self.score = spec, score
        if score.declined:
            answer = (
                "That declines to run the experiment rather than proposing a "
                "cohort/plate. Nothing was simulated. Whether declining is right here is "
                "answered by the reference designs - see `refute baselines`."
            )
            return Turn(intent="design", answer=answer, score=score, called_model=True)

        answer = self._verdict_sentence(score)
        return Turn(
            intent="design",
            answer=answer,
            evidence=_cite(score, self.n_sims, capacity=self.twin.default_capacity),
            score=score,
            called_model=True,
        )

    def _verdict_sentence(self, score: Any) -> str:
        if score.power >= 0.8:
            return "This design can answer its question."
        if score.testable_rate < 0.5:
            return (
                "Most runs of this design would not yield a testable result at "
                "all - the problem is losing units, before any question of "
                "statistical power."
            )
        if score.feasibility == "infeasible":
            return (
                "This yields data but cannot resolve the effect, and no amount of "
                "care with the apparatus you have fixes that."
            )
        return "This design is underpowered for the effect it is looking for."

    def _handle_advise(self, _text: str) -> Turn:
        if self.twin.advise_fn is None:
            return Turn(
                intent="advise",
                answer=f"No advisor registered for assay '{self.assay}'.",
                evidence=_cite(self.score, self.n_sims, capacity=self.twin.default_capacity),
            )
        kwargs: dict[str, Any] = {"n_sims": self.n_sims}
        if self.params is not None:
            kwargs["params"] = self.params
        result = self.twin.advise_fn(self.design, **kwargs)
        helpful = result.helpful
        if not helpful:
            return Turn(
                intent="advise",
                answer="No single change to this design improves it.",
                evidence=_cite(self.score, self.n_sims, capacity=self.twin.default_capacity),
            )
        lines = [f"{len(helpful)} change(s) help, best first:", ""]
        evidence: list[str] = []
        for i, s in enumerate(helpful, 1):
            lines.append(f"  {i}. {s.change}")
            evidence.append(
                f"{s.change}: power {s.before.power:.0%} -> {s.after.power:.0%}, "
                f"testable {s.before.testable_rate:.0%} -> "
                f"{s.after.testable_rate:.0%}"
                + ("  [rests on an ASSUMED constant]" if s.assumption_sensitive else "")
            )
        if result.best_combined:
            _spec, combined = result.best_combined
            lines += ["", f"All of them together: power {combined.power:.0%}."]
            if combined.power < 0.8:
                lines.append(
                    "  Still short. The honest conclusion is that the question "
                    "cannot be answered at this scale."
                )
            evidence.append(
                "combined, applied in order: "
                + " -> ".join(result.combination_order)
            )
        return Turn(intent="advise", answer="\n".join(lines), evidence=evidence)

    def _handle_whatif(self, text: str) -> Turn:
        lowered = text.lower()
        lever = next(
            (k for k, words in WHATIF_LEVERS.items() if any(w in lowered for w in words)),
            None,
        )
        if lever is None:
            return Turn(
                intent="whatif",
                answer=(
                    "I can simulate changes to: an antifibrinolytic, the number "
                    "of replicates, the endpoint time, or narrowing the arms. "
                    "Name one and I will run it. I do not guess at changes I "
                    "cannot simulate."
                ),
            )

        if self.twin.key == "bleomycin_lung":
            from .bleomycin_advise import _variants as bleo_variants
            variants_fn = bleo_variants
        else:
            from .advise import _variants as fibrin_variants
            variants_fn = fibrin_variants

        for name, change, variant, _caveat in variants_fn(self.design):
            if name != lever:
                continue
            try:
                kwargs: dict[str, Any] = {"n_sims": self.n_sims}
                if self.params is not None:
                    kwargs["params"] = self.params
                after = self.twin.score_fn(variant, **kwargs)
            except OutOfTwinScopeError:
                continue
            direction = "better" if after.power > self.score.power else (
                "no better" if after.power <= self.score.power else "worse"
            )
            ev = [
                f"power {self.score.power:.0%} -> {after.power:.0%}",
                f"testable {self.score.testable_rate:.0%} -> {after.testable_rate:.0%}",
            ]
            if hasattr(self.score, "mean_lysed_fraction") and hasattr(after, "mean_lysed_fraction"):
                ev.append(
                    f"wells lost {self.score.mean_lysed_fraction:.0%} -> {after.mean_lysed_fraction:.0%}"
                )
            elif hasattr(self.score, "mean_animals_scored") and hasattr(after, "mean_animals_scored"):
                ev.append(
                    f"animals scored {self.score.mean_animals_scored:.1f} -> {after.mean_animals_scored:.1f}"
                )
            return Turn(
                intent="whatif",
                answer=f"{change} — {direction}.",
                evidence=ev,
                score=after,
            )
        return Turn(
            intent="whatif",
            answer=(
                f"'{lever}' does not apply to this design - it is already set "
                "that way, or the apparatus has no room for it."
            ),
        )

    def _handle_why(self, _text: str) -> Turn:
        if not self.score.diagnoses:
            return Turn(
                intent="why",
                answer="No structural failure modes were detected.",
                evidence=_cite(self.score, self.n_sims, capacity=self.twin.default_capacity),
            )
        return Turn(
            intent="why",
            answer="\n".join(f"  - {d}" for d in self.score.diagnoses),
            evidence=_cite(self.score, self.n_sims, capacity=self.twin.default_capacity),
        )

    def _handle_scale(self, _text: str) -> Turn:
        s = self.score
        if s.replicates_needed <= 0:
            return Turn(
                intent="scale",
                answer=(
                    "I cannot tell you, and that is the answer. Too many units "
                    "are lost before the endpoint for the survivors to support "
                    "an estimate - and the ones lost are the ones carrying the "
                    "largest effect. Fix the loss first; the number is only "
                    "answerable once units survive."
                ),
                evidence=_cite(s, self.n_sims, capacity=self.twin.default_capacity),
            )
        n_conds = getattr(s, "n_conditions", len(getattr(s, "conditions", [])))
        arms = max(n_conds, 1)
        total = s.replicates_needed * arms
        answer = (
            f"About {s.replicates_needed} per arm — {total} in total across "
            f"{arms} arms."
        )
        if total > self.twin.default_capacity:
            answer += (
                f" The apparatus holds {self.twin.default_capacity}, so this is not reachable "
                "at this scale. Narrowing to fewer arms is the only move that "
                "buys replication without more capacity."
            )
        return Turn(intent="scale", answer=answer, evidence=_cite(s, self.n_sims, capacity=self.twin.default_capacity))

