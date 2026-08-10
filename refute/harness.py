"""Harnesses - the scaffolding around the model, made an explicit variable.

`ChatModelAgent` is one completion per turn. That thinness was deliberate: a
richer scaffold raises scores, and if it is the only thing on offer then the
result measures the scaffold rather than the model.

The answer is not to keep the harness thin forever. It is to stop treating it as
a constant. A score belongs to a **(model x harness)** pair, and quoting one
without the other is the same error as varying the extractor alongside the agent.

So there are several harnesses here, each declaring what it adds, and every one
reports its own `name`. The interesting measurement is the *difference* between
them on a fixed model:

    single-shot     one completion. The control.
    self-critique   the model reviews its own design before submitting.
    checklist       forced to answer specific methodological questions first.

**What no harness gets is the twin.** Giving a harness the simulator would let it
tune against the scorer, which is the Goodhart failure PLAN 9.1 describes and
would make the benchmark measure search rather than judgement. Harnesses may
restructure the model's own reasoning; they may not consult the answer key.

The question these are built to answer is sharper than "can scores be raised".
Experiment 4's central defect was n=3 - a *computable* error. If self-critique
fixes it, the deficiency was that nobody stopped to check. If it does not, the
deficiency is knowledge of what goes wrong, which is the survivorship claim this
project makes. Either result is worth having, and the thin harness alone cannot
distinguish them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import (
    PROPOSE_MAX_TOKENS,
    ChatModelAgent,
    propose_design,
    revise_design,
)
from .providers import DEFAULT_AGENT, ModelSpec, get_provider

# ---------------------------------------------------------------------------
# Prompts. Deliberately free of any assay-specific hint: none of these may
# mention fibrinolysis, an antifibrinolytic, or a number of wells, or the
# harness would be smuggling in the answers the brief withholds.
# ---------------------------------------------------------------------------

CRITIQUE_PROMPT = """\
Before this design is executed, review it as a hostile methods reviewer would.

Do not defend it. Find the reasons it might fail to answer its own question.
Consider at least: whether the comparison is adequately replicated for the
effect size and measurement precision you would actually expect; whether the
measurement can be made when you say it will be; what happens to the preparation
over the full duration; and what you would conclude if the result came out null.

Be specific and quantitative where you can. List the problems only - do not
rewrite the design yet.
"""

REVISE_AFTER_CRITIQUE_PROMPT = """\
Now produce your final design, addressing your own criticisms.

If your review showed the question cannot be answered with the resources
available, say that explicitly and explain what would be required instead. That
is a legitimate answer here, not a failure.
"""

CHECKLIST_PROMPT = """\
Before writing any design, answer these directly. Show your arithmetic.

1. What is the single comparison that answers the question?
2. What difference in your chosen readout would you expect, and how variable is
   that readout between replicates?
3. Given 2, how many replicates does that comparison need? Compute it.
4. Can you fit that on the apparatus available? If not, say so now.
5. What could stop a replicate being measurable at your endpoint?

Then write the design, or state that the question is not answerable as posed.
"""


@dataclass
class HarnessResult:
    """A design plus everything the harness did to produce it."""

    design_text: str
    transcript: list[tuple[str, str]] = field(default_factory=list)

    def turns(self) -> int:
        return len(self.transcript)


class SingleShot:
    """One completion per turn. The control - identical to `ChatModelAgent`.

    Present so that "no harness" is a named condition rather than the absence of
    one, which makes it quotable in a results table.
    """

    name = "single-shot"
    adds = "nothing"

    def __init__(self, spec: ModelSpec = DEFAULT_AGENT):
        self.spec = spec
        self._inner = ChatModelAgent(spec=spec)

    def propose(self, brief: str) -> str:
        return self._inner.propose(brief)

    def revise(self, brief: str, previous_design: str, feedback: str) -> str:
        return self._inner.revise(brief, previous_design, feedback)

    def __str__(self) -> str:
        return f"{self.spec} [{self.name}]"


class SelfCritique:
    """Propose, review own design, then submit. Three calls instead of one.

    The critique prompt names no assay specifics - only the generic questions a
    methods reviewer asks - so anything it fixes was already available to the
    model and simply never computed.
    """

    name = "self-critique"
    adds = "one adversarial self-review pass before submitting"

    def __init__(self, spec: ModelSpec = DEFAULT_AGENT):
        self.spec = spec

    def _complete(self, messages: list[dict[str, str]]) -> str:
        return get_provider(self.spec.provider).complete(
            messages, self.spec, PROPOSE_MAX_TOKENS
        )

    def _loop(self, seed_messages: list[dict[str, str]]) -> HarnessResult:
        messages = list(seed_messages)
        draft = self._complete(messages)
        transcript = [("draft", draft)]

        messages += [
            {"role": "assistant", "content": draft},
            {"role": "user", "content": CRITIQUE_PROMPT},
        ]
        critique = self._complete(messages)
        transcript.append(("critique", critique))

        messages += [
            {"role": "assistant", "content": critique},
            {"role": "user", "content": REVISE_AFTER_CRITIQUE_PROMPT},
        ]
        final = self._complete(messages)
        transcript.append(("final", final))
        return HarnessResult(design_text=final, transcript=transcript)

    def propose_verbose(self, brief: str) -> HarnessResult:
        return self._loop([{"role": "user", "content": brief}])

    def propose(self, brief: str) -> str:
        return self.propose_verbose(brief).design_text

    def revise(self, brief: str, previous_design: str, feedback: str) -> str:
        # After simulator feedback the critique pass is redundant - the feedback
        # already IS an external critique, and a stronger one. Adding a self-review
        # on top would confound "responded to consequences" with "reviewed itself".
        return revise_design(brief, previous_design, feedback, self.spec)

    def __str__(self) -> str:
        return f"{self.spec} [{self.name}]"


class Checklist:
    """Forced to answer methodological questions, with arithmetic, before designing.

    Tests whether Experiment 4's central defect - n=3 - is a knowledge failure or
    merely an un-done calculation. The questions are generic; none names a
    mechanism, a reagent or a number.
    """

    name = "checklist"
    adds = "a forced quantitative pre-design worksheet"

    def __init__(self, spec: ModelSpec = DEFAULT_AGENT):
        self.spec = spec

    def propose_verbose(self, brief: str) -> HarnessResult:
        provider = get_provider(self.spec.provider)
        messages = [
            {"role": "user", "content": brief},
            {"role": "user", "content": CHECKLIST_PROMPT},
        ]
        answered = provider.complete(messages, self.spec, PROPOSE_MAX_TOKENS)
        return HarnessResult(design_text=answered, transcript=[("checklist", answered)])

    def propose(self, brief: str) -> str:
        return self.propose_verbose(brief).design_text

    def revise(self, brief: str, previous_design: str, feedback: str) -> str:
        return revise_design(brief, previous_design, feedback, self.spec)

    def __str__(self) -> str:
        return f"{self.spec} [{self.name}]"


HARNESSES: dict[str, type] = {
    SingleShot.name: SingleShot,
    SelfCritique.name: SelfCritique,
    Checklist.name: Checklist,
}


def get_harness(name: str, spec: ModelSpec = DEFAULT_AGENT):
    try:
        return HARNESSES[name](spec)
    except KeyError:
        raise KeyError(
            f"unknown harness '{name}'. Known: {', '.join(sorted(HARNESSES))}"
        ) from None


def describe() -> str:
    """What each harness adds, for `refute harnesses`."""
    lines = [f"{'harness':<16} {'calls/turn':>10}  adds"]
    calls = {"single-shot": 1, "self-critique": 3, "checklist": 1}
    for name, cls in HARNESSES.items():
        lines.append(f"{name:<16} {calls.get(name, '?'):>10}  {cls.adds}")
    lines += [
        "",
        "A score belongs to a (model x harness) pair. Quoting one without the",
        "other is the same error as varying the extractor alongside the agent:",
        "you cannot tell whether the model designed better or the scaffolding did.",
        "",
        "No harness is given the twin. A harness may restructure the model's own",
        "reasoning; it may not consult the scorer, or the benchmark would measure",
        "search against the simulator rather than judgement (PLAN 9.1).",
    ]
    return "\n".join(lines)
