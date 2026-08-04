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

The agent model is a parameter; the extractor model should NOT be varied
alongside it. See `refute.providers` for why.
"""

from __future__ import annotations

from .design import DesignSpec
from .providers import DEFAULT_AGENT, DEFAULT_EXTRACTOR, ModelSpec, get_provider

# Reasoning tokens are charged against these budgets on the GPT-5 families, so
# they are set well above the length of the visible answer.
PROPOSE_MAX_TOKENS = 16000
EXTRACT_MAX_TOKENS = 8000

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
