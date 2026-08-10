"""The agent under test, and the extractor that turns its prose into parameters.

Two distinct jobs, deliberately given to the model in different ways:

  propose_design()  - the thing being benchmarked. Free-text, no structure
                      imposed, no hints about what the twin checks.
  extract_design()  - NOT being benchmarked. Turns that prose into a
                      DesignSpec. This is extraction, which models are reliable
                      at, and it is kept separate so that a scoring failure is
                      never really a parsing failure.

The brief given to the agent contains only what was knowable BEFORE Experiment
4 was run. It must never mention fibrinolysis, aprotinin, the observed lysis
split, or the contraction half-time - those are the answers.

It DOES state what the apparatus can measure, and that line was added on
2026-08-10 after two live runs were refused a score. gpt-5.5 proposed
quantifying neck-width narrowing rather than projected area, which the twin
cannot simulate - its measurement model is calibrated for area segmentation
specifically. The brief had constrained the plate count and the camera but not
the readout, so the design was rejected for using the equipment differently than
assumed. That measures conformance to an unstated convention, not design quality.

Stating it leaks nothing: the readout is the standard one for the Roberts 2022
model and is a property of the equipment, in the same class as "ONE 12-well
plate". Neither defect the agent has to rediscover - n=3, and no reasoning about
scaffold loss - is hinted at by naming the units.

The agent model is a parameter; the extractor model should NOT be varied
alongside it. See `refute.providers` for why.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .design import DesignSpec
from .providers import DEFAULT_AGENT, DEFAULT_EXTRACTOR, ModelSpec, get_provider

# Reasoning tokens are charged against these budgets on the GPT-5 families, so
# they must sit well above the length of the visible answer. Measured, not
# guessed: the first live run gave gpt-5.5 16k for a proposal and it spent the
# whole budget thinking, returning empty text. Designing a plate is a long
# deliberation, so the ceiling is set generously - unused budget is not billed.
PROPOSE_MAX_TOKENS = 64000
EXTRACT_MAX_TOKENS = 32000

# Pre-registration only. Everything here was known before casting the plate.
EXPERIMENT_4_BRIEF = """\
Design a cell-contraction experiment.

QUESTION
Does MSC-conditioned media suppress TGF-b1-driven contraction in primary human
synovial fibroblasts?

AVAILABLE
- Primary human synovial fibroblasts (consented waste tissue).
- Anchored fibrin gel constructs, cast in a 12-well plate on the Roberts 2022
  "contracture-in-a-well" model: each construct is anchored at both ends by
  sutures over pins set in PDMS, holding the gel a few mm above the plate floor.
- Fibrinogen, thrombin, CaCl2. Standard culture reagents.
- Recombinant TGF-b1. MSC-conditioned media.
- Imaging: a phone camera on a fixed rig. No microscope, no gel-doc, no scanner.
- Quantification: projected gel area from those images, as a percentage of the
  well area. This is the only quantity the setup measures - there is no force
  transducer, and the images do not support anything finer.
- ONE 12-well plate. This is the whole experiment.

DELIVERABLE
A complete plate design: experimental arms and how many wells each gets, the
full timeline from casting through to the endpoint (state every timepoint you
would image, in hours since casting), the gel formulation, when treatments go
on, how you would image and quantify, and how you would analyse the result.

State your reasoning briefly. Be specific and concrete - this design will be
executed exactly as written.
"""

EXTRACTION_PROMPT = """\
Read the experimental design below and record it as structured fields.

Extract only what the design actually says. Do not correct it, improve it, or
fill in what a good design would have done. If the design omits something,
record the omission faithfully - `false` for an absent antifibrinolytic, and so
on. Convert all times to HOURS SINCE CASTING (Day 1 = 24, Day 5 = 120,
Day 7 = 168, Day 10 = 240).

`out_of_twin_scope` is for SUBSTITUTIONS ONLY, and is usually empty. Use it if
and only if the design changes the apparatus itself: a matrix that is not fibrin,
a readout that is not gel area, a different vessel or anchoring scheme, or an
added agent that alters scaffold degradation without being an antifibrinolytic.

Do NOT put ordinary protocol detail there. Concentrations, seeding density, media
and serum, growth factor doses, medium changes, area units, the analysis plan and
QC or exclusion criteria are all normal parts of a fibrin-gel design, not
deviations from it - a design that simply describes this assay carefully has an
EMPTY `out_of_twin_scope`. Listing such detail wrongly blocks the design from
being scored at all.

DESIGN
------
{design_text}
"""


def propose_design(
    brief: str = EXPERIMENT_4_BRIEF, agent: ModelSpec = DEFAULT_AGENT
) -> str:
    """Ask the agent for a design. Returns free text.

    This is the measurement. `agent` is the independent variable of the whole
    benchmark, so it is recorded alongside every score.
    """
    return get_provider(agent.provider).complete(
        [{"role": "user", "content": brief}], agent, PROPOSE_MAX_TOKENS
    )


def revise_design(
    brief: str,
    previous_design: str,
    feedback: str,
    agent: ModelSpec = DEFAULT_AGENT,
) -> str:
    """Show the agent what the simulator did to its plate; ask for a redesign.

    The feedback reports consequences, never corrections - it says the scaffold
    was gone before the endpoint, not 'add aprotinin'. Working out the fix is
    the part under test.
    """
    return get_provider(agent.provider).complete(
        [
            {"role": "user", "content": brief},
            {"role": "assistant", "content": previous_design},
            {
                "role": "user",
                "content": (
                    f"Your design was run. Here is what happened:\n\n{feedback}\n\n"
                    "Produce a revised design that would actually answer the "
                    "question. Same format as before."
                ),
            },
        ],
        agent,
        PROPOSE_MAX_TOKENS,
    )


def extract_design(
    design_text: str, extractor: ModelSpec = DEFAULT_EXTRACTOR
) -> DesignSpec:
    """Free-text design -> DesignSpec. Extraction, not judgement.

    HOLD THIS CONSTANT. Varying the extractor alongside the agent confounds
    design quality with parsing fidelity: a lower score could mean the agent
    designed worse, or that its prose was read less accurately, and the two are
    indistinguishable after the fact.
    """
    spec = get_provider(extractor.provider).parse(
        [{"role": "user", "content": EXTRACTION_PROMPT.format(design_text=design_text)}],
        extractor,
        EXTRACT_MAX_TOKENS,
        DesignSpec,
    )
    assert isinstance(spec, DesignSpec)
    return spec


# ---------------------------------------------------------------------------
# The thing under test, as an interface
#
# `propose_design` and `revise_design` are one implementation - a single chat
# completion. The benchmark is about design quality, not about that particular
# scaffold, so the two methods a subject must supply are named separately from
# the way this module happens to supply them.
#
# Anything satisfying `Agent` can be scored: a tool-using loop, a multi-agent
# system, a human typing into a file. `refute.environment.RefuteEnv` accepts
# designs from any source and is the usual way in; this Protocol is for callers
# who want the CLI's propose-then-revise shape driven by their own agent.
# ---------------------------------------------------------------------------


@runtime_checkable
class Agent(Protocol):
    """A subject of the benchmark. Two methods, both returning free text."""

    def propose(self, brief: str) -> str:
        """First attempt at a design, from the brief alone."""
        ...

    def revise(self, brief: str, previous_design: str, feedback: str) -> str:
        """A second attempt, having been told what the simulator did to the first.

        `feedback` reports consequences, never corrections. Working out the fix
        is the part being measured.
        """
        ...


@dataclass
class ChatModelAgent:
    """The reference `Agent`: one model, one completion per turn.

    Deliberately thin. A richer scaffold here - retrieval, tool use, a critic -
    would improve scores and make the result a measurement of the scaffold
    rather than of the model, which is the same confound the extractor is held
    constant to avoid.
    """

    spec: ModelSpec = DEFAULT_AGENT

    def propose(self, brief: str) -> str:
        return propose_design(brief, self.spec)

    def revise(self, brief: str, previous_design: str, feedback: str) -> str:
        return revise_design(brief, previous_design, feedback, self.spec)

    def __str__(self) -> str:
        return str(self.spec)
