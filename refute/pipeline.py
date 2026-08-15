"""The downstream half of the diagram in PIPELINE.md, run end to end.

    resolve  ->  gate  ->  simulate | tier 0  ->  advise  ->  outcome

Every stage already exists and is tested on its own. What did not exist is the
thing that walks them in order and keeps a record of the walk, and the absence
was not cosmetic: each stage answers a different question, and a caller holding
only the last answer cannot tell a refusal apart from a verdict. `narrative` is
that record - one line per stage, in the order the stages ran.

WHY THE WORDING IS PART OF THE CONTRACT
---------------------------------------
Four of the five exits are stops, and three of them are stops for reasons that
have nothing to do with the quality of the design:

    NOT_READY      the requirement set is still being filled
    OUT_OF_SCOPE   the simulator models a different apparatus
    REFUSE         there is no calibrated twin and no variance estimate

Each of those is easy to read as "your experiment is bad", and each would be
read that way by default, because the surrounding machinery is a scorer. So the
narrative says, in words, which one happened and what it is not. That is why
this module contains sentences rather than status codes, and why the tests
assert on the sentences.

THE FIFTH EXIT IS THE POINT
---------------------------
`TIER1` runs the twin and then the advisor. When the advisor finds that no
single change and no combination of changes improves the design, this returns
`terminal=True` and says the question is not answerable at this scale. That is
the most valuable output the system produces - it is the finding Experiment 4
itself yielded - and a pipeline with no box for it would loop forever polishing
a plate that should not be cast. It is reachable, and `tests/test_pipeline.py`
pins that it stays reachable.

NOTHING HERE READS A RESOLVED VALUE BEFORE THE GATE HAS ROUTED
---------------------------------------------------------------
The gate routes on coverage and provenance alone (see `resolve.py`). This module
is the first place a number is dereferenced, and only on the tier-0 path, where
the arithmetic genuinely needs one. A fixture whose every value is `null` still
runs all the way through here - it just degrades to a refusal at tier 0 rather
than producing a power figure, which is the correct behaviour and not a bug in
the fixture.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .advise import Advice, advise
from .assays.base import AssayProtocol, UncalibratedAssayError
from .calibration import PLATE_WELLS
from .design import DesignSpec, OutOfTwinScopeError
from .gate import Route, RouteDecision, route_design
from .requirements import requirement_version, tier0_needs, tier1_needs
from .resolve import Requirement, ResolutionSet, Resolver
from .score import score_design
from .tier0 import DEFAULT_ALPHA, Tier0Design, Tier0InputError, score_tier0

# The one phrase the terminal state is recognised by, here rather than inline so
# that the wording cannot drift between the module that writes it and the test
# that pins it. It must NOT appear on any other path: emitting it for a design
# that is merely unsearched is the most damaging wrong output this system can
# produce, because it is the one people quote.
NOT_ANSWERABLE = "not answerable at this scale"


@dataclass(frozen=True)
class PipelineResult:
    """What happened, at every stage, in a form a caller can act on.

    `score` is a `DesignScore` on the tier-1 path, a `Tier0Score` on the tier-0
    path, and None on every stop. `advice` is an `Advice` and is set only when
    the advisor found something that helps - a caller that wants the full list
    of changes that did *not* help should call `advise` itself.

    Typed loosely on purpose: binding this dataclass to both score types would
    force `score.py` and `tier0.py` into a common base class they do not want,
    and the two verdicts are deliberately not interchangeable.
    """

    decision: RouteDecision
    score: object | None = None
    advice: object | None = None
    terminal: bool = False
    narrative: list[str] = field(default_factory=list)

    @property
    def route(self) -> Route:
        return self.decision.route

    def render(self) -> str:
        """The narrative as printed text. The CLI's whole body."""
        return "\n".join(self.narrative)


def requirements_for(protocol: AssayProtocol) -> tuple[Requirement, ...]:
    """The union of what tier 1 and tier 0 need, tier 1 first, deduplicated.

    Both sets are asked for in one pass because the resolver should not have to
    be told which tier it is filling. Deciding that is the gate's job, and it
    can only decide it once it can see which of the two sets came back covered.
    """
    seen: set[str] = set()
    out: list[Requirement] = []
    for req in (*tier1_needs(protocol), *tier0_needs()):
        if req.key in seen:
            continue
        seen.add(req.key)
        out.append(req)
    return tuple(out)


def _resolve_line(
    resolutions: ResolutionSet, requirements: tuple[Requirement, ...], resolver_name: str
) -> str:
    keys = [r.key for r in requirements]
    resolved = sum(
        1 for k in keys
        if (r := resolutions.resolutions.get(k)) is not None and r.resolved
    )
    line = (
        f"resolve: {resolved}/{len(keys)} required quantities resolved by "
        f"'{resolver_name}' (requirement set {resolutions.requirement_version})"
    )
    unsearched = resolutions.unsearched()
    if unsearched:
        line += f"; {len(unsearched)} not yet searched"
    return line


def _version_warning(protocol: AssayProtocol, resolutions: ResolutionSet) -> str | None:
    """Flag a resolver that answered a different revision of the requirement set.

    Not fatal, because a hand-written fixture legitimately carries a placeholder
    version and refusing it would make the offline test matrix unusable. But it
    is worth a line: a version skew presents exactly as an honest refusal - every
    quantity reports missing because the keys moved - and that is the failure
    mode nobody notices for hours.
    """
    expected = requirement_version(protocol)
    got = resolutions.requirement_version
    if got == expected:
        return None
    return (
        f"warning: this answers requirement set {got!r}, the registry is now at "
        f"{expected!r}. A key that was renamed will report as missing rather "
        f"than as a mismatch, so read any refusal below with that in mind."
    )


def _within_arm_sd(resolutions: ResolutionSet) -> float | None:
    """The tier-0 spread input, as an SD.

    `within_arm_sd` is the requirement's name, and tier 0 wants a within-arm
    SD in the same units as the effect. Almost every source reports an SD, so
    that is the default reading - but a resolution that has explicitly labelled
    its units as a squared quantity is taken at its word and rooted, because
    silently feeding a variance in where an SD belongs understates the spread
    and inflates power, which is an error in the permissive direction.
    """
    r = resolutions.resolutions.get("within_arm_sd")
    if r is None or r.value is None:
        return None
    units = r.units.lower()
    squared = "^2" in units or "²" in units or "variance" in units or "squared" in units
    if squared and r.value >= 0:
        return float(r.value) ** 0.5
    return float(r.value)


def _valueless(resolutions: ResolutionSet, keys: tuple[str, ...]) -> tuple[str, ...]:
    """Required keys the arithmetic cannot use, whether blocked or merely empty.

    Not the same set as `ResolutionSet.missing`. A `CONTEXT_DEPENDENT` key does
    not block tier 1 - it becomes a swept range - but tier 0 has no sweep, so it
    is as unusable there as an absent one. Reporting `missing()` on this path
    would name nothing and leave the refusal unexplained.
    """
    return tuple(
        k for k in keys
        if (r := resolutions.resolutions.get(k)) is None or r.value is None
    )


def _tier0_design(
    design: DesignSpec, protocol: AssayProtocol, resolutions: ResolutionSet
) -> Tier0Design:
    """Assemble the arithmetic's inputs from whatever actually resolved.

    Where the resolver found a number it is used; where it did not, the design's
    own structure supplies the shape of the comparison (how many arms, how many
    replicates) and nothing else. No effect size and no spread is ever invented -
    those stay None, and `score_tier0` refuses. That refusal is the point of the
    tier-0 gate, so this function must not defeat it with a default.
    """
    def value(key: str) -> float | None:
        r = resolutions.resolutions.get(key)
        return None if r is None else r.value

    n_per_arm = value("n_per_arm")
    alpha = value("alpha")
    return Tier0Design(
        assay=protocol.name,
        n_arms=max(len(design.conditions), 2),
        replicates_per_arm=(
            int(n_per_arm) if n_per_arm is not None
            else design.replicates_per_condition
        ),
        capacity=PLATE_WELLS,
        expected_effect=value("effect_size"),
        variability_sd=_within_arm_sd(resolutions),
        unit=protocol.unit,
        alpha=alpha if alpha is not None else DEFAULT_ALPHA,
        notes=(
            "inputs from the resolve loop; replication and arm count from the "
            "design as proposed"
        ),
    )


# --- the stops --------------------------------------------------------------
# Each returns the finished result rather than a fragment, so that the wording
# of an exit lives in exactly one place and cannot be half-overridden by the
# caller.


def _not_ready(decision: RouteDecision, narrative: list[str]) -> PipelineResult:
    narrative += [
        "outcome: NOT READY - the requirement set is not finished.",
        "  This is NOT a verdict on the design. Nothing was simulated and "
        "nothing is being",
        "  claimed about the experiment, because quantities the verdict depends "
        "on have not",
        "  been searched for yet - which is different from having been searched "
        "for and not",
        "  found. Finish the resolve loop and route again.",
    ]
    if decision.missing:
        narrative.append(f"  still open: {', '.join(decision.missing)}")
    return PipelineResult(decision=decision, narrative=narrative)


def _out_of_scope(decision: RouteDecision, narrative: list[str]) -> PipelineResult:
    narrative += [
        "outcome: OUT OF SCOPE - this is a limit of the simulator, not a "
        "problem with the design.",
        "  The twin models one apparatus. A design that leaves it is not a worse "
        "design; it",
        "  is one this twin has nothing to say about, and scoring it anyway "
        "would report a",
        "  confident number about a different experiment.",
        "  Tier 0 is still available: the power arithmetic is assay-blind, so it "
        "can assess",
        "  this comparison from your own effect size and within-arm SD even "
        "though the twin",
        "  cannot. Run `refute tier0`. What tier 0 cannot tell you is whether "
        "the preparation",
        "  survives to be measured.",
    ]
    if decision.unmodelled:
        narrative.append(
            "  unmodelled here: " + "; ".join(decision.unmodelled)
        )
    return PipelineResult(decision=decision, narrative=narrative)


def _refuse(
    decision: RouteDecision, narrative: list[str], missing: tuple[str, ...]
) -> PipelineResult:
    narrative.append(
        "outcome: REFUSED - no calibrated twin, and not enough to fall back on."
    )
    if missing:
        narrative.append(f"  tier 0 still needs: {', '.join(missing)}")
    narrative += [
        "  These are not defaults this tool can supply. A power figure computed "
        "from a",
        "  guessed variance looks like a calculation and is not one, which is "
        "the error this",
        "  project exists to criticise. Run a pilot, take the numbers from prior "
        "runs, or",
        "  record the design as unassessable.",
    ]
    return PipelineResult(decision=decision, narrative=narrative)


# --- the two scoring paths ---------------------------------------------------


def _run_tier0(
    design: DesignSpec,
    protocol: AssayProtocol,
    resolutions: ResolutionSet,
    decision: RouteDecision,
    narrative: list[str],
) -> PipelineResult:
    """Arithmetic, and a refusal when an input the arithmetic needs is absent.

    The gate routes here on coverage, and coverage is a claim about which keys
    resolved rather than about what they resolved to - so a set the gate calls
    covered can still arrive with `value=None` on every key. That is legal, and
    it is exactly what a hand-written fixture looks like. `Tier0InputError` is
    therefore an expected outcome on this path, not an exceptional one, and it
    degrades to the same refusal a missing key would produce.
    """
    t0 = _tier0_design(design, protocol, resolutions)
    try:
        score = score_tier0(t0)
    except Tier0InputError as exc:
        narrative.append(
            "tier 0: cannot compute - the numbers the arithmetic needs did not "
            "arrive with values."
        )
        narrative += [f"  {line}" for line in str(exc).splitlines()]
        return _refuse(
            replace(
                decision,
                route=Route.REFUSE,
                why=(
                    "routed to tier 0 on coverage, but the resolved entries carry "
                    "no usable value"
                ),
            ),
            narrative,
            _valueless(resolutions, tuple(r.key for r in tier0_needs())),
        )

    narrative.append(
        f"tier 0: power {score.power:.0%} at {t0.replicates_per_arm} "
        f"{t0.unit}s per arm across {t0.n_arms} arms; verdict "
        f"{score.feasibility}"
    )
    # Tier 0 has no mechanism and a reader who forgets that will take a green
    # verdict as an assurance the experiment will work. Said on every tier-0
    # output, without exception - the same rule `Tier0Score.summary` follows.
    narrative += [
        "outcome: TIER 0 - arithmetic, not simulation. It says whether the "
        "comparison could",
        "  resolve the effect you stated. It says nothing about whether the "
        "preparation",
        "  survives to be measured: Experiment 4 was destroyed by fibrinolysis, "
        "and no power",
        "  calculation would have predicted that.",
    ]
    # Terminal in the tier-0 sense: the replication the effect needs does not
    # fit the units available, and no rearrangement of this comparison changes
    # that. Not the same claim as the tier-1 terminal, so it is not phrased as
    # one - there is no mechanism here to have exhausted.
    terminal = score.feasibility in ("infeasible", "beyond-scale")
    if terminal:
        narrative.append(
            f"  The replication this effect needs does not fit the "
            f"{t0.capacity} {t0.unit}s available, so on these numbers the "
            f"question is {NOT_ANSWERABLE}. Narrow the comparison, measure more "
            f"precisely, or report that - the last is a legitimate answer."
        )
    return PipelineResult(
        decision=decision, score=score, terminal=terminal, narrative=narrative
    )


def _run_tier1(
    design: DesignSpec,
    decision: RouteDecision,
    narrative: list[str],
    n_sims: int,
) -> PipelineResult:
    """Simulate, then look for a change that helps, then say if none does."""
    try:
        score = score_design(design, n_sims=n_sims)
    except OutOfTwinScopeError as exc:
        # The gate is supposed to have caught this by comparing the design
        # against the protocol. If it reaches here the two disagree, and the
        # right answer is still the honest one rather than a traceback - a
        # verifier that crashes on a design it cannot model has told the user
        # nothing, and a stack trace reads as a bug in their experiment.
        narrative.append(
            "simulate: the twin refused - the design specifies something it does "
            "not model."
        )
        return _out_of_scope(
            replace(
                decision,
                route=Route.OUT_OF_SCOPE,
                why="the twin refused the design at simulation time",
                unmodelled=tuple(exc.reasons),
            ),
            narrative,
        )
    except UncalibratedAssayError as exc:
        narrative.append(
            "simulate: the protocol is not calibrated, so it cannot produce a "
            "score."
        )
        narrative += [f"  {line}" for line in str(exc).splitlines()]
        return _refuse(
            replace(
                decision,
                route=Route.REFUSE,
                why="the protocol routed to tier 1 is not calibrated",
            ),
            narrative,
            (),
        )

    if decision.sweep:
        narrative.append(
            "simulate: "
            + ", ".join(decision.sweep)
            + " were swept rather than fixed - each is assumed or ill-posed as a "
            "scalar, so any verdict below is reported as sensitive to them."
        )

    if score.declined:
        # Declining is an epistemic act, not a low score, and `advise` has
        # nothing to perturb. Reporting 0% power here would tell the proposer
        # their refusal failed, pushing them toward a plate they have just
        # correctly argued cannot work.
        narrative += [
            "simulate: nothing was simulated - this design assigns no wells.",
            "outcome: DECLINED - the design declines to run the experiment.",
            "  That is a recognised answer, not a failure, and it is the same "
            "verdict this",
            "  benchmark reports for Experiment 4. Judge it by whether declining "
            "was right:",
            "  `refute baselines` gives the ceiling on one plate.",
        ]
        return PipelineResult(
            decision=decision, score=score, terminal=True, narrative=narrative
        )

    narrative.append(
        f"simulate: power {score.power:.0%}, testable {score.testable_rate:.0%}, "
        f"{score.mean_lysed_fraction:.0%} of wells lost by the endpoint "
        f"({n_sims} plates)"
    )
    if score.verdict_sensitive_to_assumption:
        lo, hi = score.power_range_under_assumptions or (float("nan"),) * 2
        narrative.append(
            f"  this verdict does not survive the plausible range of "
            f"{', '.join(score.assumptions_in_play)}: power spans {lo:.0%}-{hi:.0%}."
        )

    result: Advice = advise(design, n_sims=n_sims)
    helpful = result.helpful
    if helpful:
        narrative.append(
            f"advise: {len(helpful)} of {len(result.suggestions)} changes tried "
            f"improve it; best is '{helpful[0].change}' "
            f"({helpful[0].before.power:.0%} -> {helpful[0].after.power:.0%} power)"
        )
        if result.best_combined is not None:
            _spec, combined = result.best_combined
            narrative.append(
                f"  applying every improvement in order "
                f"({' -> '.join(result.combination_order)}) reaches "
                f"{combined.power:.0%} power, {combined.testable_rate:.0%} testable"
            )
            if combined.power < 0.8:
                # Improvable and still doomed are not mutually exclusive, and
                # this is the case that produced Experiment 4's headline: 0% ->
                # 97% testable, power still 9%.
                narrative.append(
                    f"  Even so, {combined.power:.0%} is not 80%. The changes are "
                    f"worth making and they are still not enough, which is a "
                    f"different statement from either one alone."
                )
        narrative.append(
            "outcome: REVISE - the levers above are individually simulated, so "
            "each carries its"
        )
        narrative.append(
            "  own consequence rather than an opinion. Revising raises new "
            "grounding questions;"
        )
        narrative.append("  the resolve loop is re-entrant on purpose.")
        return PipelineResult(
            decision=decision, score=score, advice=result, narrative=narrative
        )

    narrative.append(
        "advise: there is no single change left to try - every lever the advisor "
        "knows about is already applied to this design."
        if not result.suggestions
        else f"advise: none of the {len(result.suggestions)} changes tried "
        f"improves this design."
    )
    need = (
        f"~{score.replicates_needed} wells per arm"
        if score.replicates_needed > 0
        else "an unestimable number of wells per arm"
    )
    narrative += [
        f"outcome: TERMINAL - the question is {NOT_ANSWERABLE}.",
        f"  At {score.power:.0%} power the design needs {need}, and the "
        f"apparatus as calibrated is one {PLATE_WELLS}-well plate.",
        "  Every single-lever change was simulated and none of them recovers it.",
        "  This is a fact about the apparatus, not a failure of the search and "
        "not a defect",
        "  in the design. Reporting it is the result - the finding this "
        "benchmark was built",
        "  to make reachable. The alternative, a loop that always has one more "
        "thing to try,",
        "  is how a doomed plate gets cast.",
    ]
    return PipelineResult(
        decision=decision, score=score, terminal=True, narrative=narrative
    )


def run(
    design: DesignSpec,
    protocol: AssayProtocol,
    resolver: Resolver,
    n_sims: int = 400,
) -> PipelineResult:
    """Resolve, route, score, advise, and say what the answer means.

    The only function in this module a caller needs. It never raises for a
    design it cannot handle: `OutOfTwinScopeError`, `UncalibratedAssayError` and
    `Tier0InputError` are all outcomes with wording of their own, because a
    traceback in front of a researcher is indistinguishable from the tool being
    broken, and the whole value of those three exceptions is what they say.
    """
    requirements = requirements_for(protocol)
    resolutions = resolver.resolve(protocol.key, requirements)

    narrative = [_resolve_line(resolutions, requirements, resolver.name)]
    if warning := _version_warning(protocol, resolutions):
        narrative.append(warning)

    decision = route_design(design, protocol, resolutions)
    narrative.append(f"gate: {decision.route.value} - {decision.why}")

    # Carried on every route, including the ones that go on to produce a number.
    # These are things the resolve loop met that the requirement set has no term
    # for, and they are the honest edge of the twin: a set can be total over the
    # registry and still be answering a smaller question than the experiment
    # poses. The gate is right not to route on them - a hint that could refuse a
    # design on its own authority is a keyword search with extra steps - but
    # dropping them silently would let a verdict look narrower than it is.
    if resolutions.unmodelled_mentions:
        narrative.append(
            f"caveat: {len(resolutions.unmodelled_mentions)} thing(s) came back "
            f"that the twin has no term for. They did not route anything and "
            f"nothing below accounts for them:"
        )
        narrative += [f"  - {m}" for m in resolutions.unmodelled_mentions]

    if decision.route is Route.NOT_READY:
        return _not_ready(decision, narrative)
    if decision.route is Route.OUT_OF_SCOPE:
        return _out_of_scope(decision, narrative)
    if decision.route is Route.REFUSE:
        missing = decision.missing or tuple(
            resolutions.missing(r.key for r in tier0_needs())
        )
        return _refuse(decision, narrative, tuple(missing))
    if decision.route is Route.TIER0:
        return _run_tier0(design, protocol, resolutions, decision, narrative)
    return _run_tier1(design, decision, narrative, n_sims)
