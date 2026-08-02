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
"""

from __future__ import annotations

import os

from .design import DesignSpec

MODEL = "claude-opus-5"

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


def _client():
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pip install anthropic  (or run with --design to score a hand-written spec)"
        ) from exc
    if not os.environ.get("ANTHROPIC_API_KEY"):
        # The SDK also accepts an `ant auth login` profile; only warn if neither.
        pass
    return anthropic.Anthropic()


def propose_design(brief: str = EXPERIMENT_4_BRIEF, effort: str = "high") -> str:
    """Ask the agent for a design. Returns free text."""
    client = _client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": brief}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"model declined: {response.stop_details}")
    return "".join(b.text for b in response.content if b.type == "text")


def revise_design(brief: str, previous_design: str, feedback: str) -> str:
    """Show the agent what the simulator did to its plate; ask for a redesign.

    The feedback reports consequences, never corrections - it says the scaffold
    was gone before the endpoint, not 'add aprotinin'. Working out the fix is
    the part under test.
    """
    client = _client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        output_config={"effort": "high"},
        messages=[
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
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"model declined: {response.stop_details}")
    return "".join(b.text for b in response.content if b.type == "text")


def extract_design(design_text: str) -> DesignSpec:
    """Free-text design -> DesignSpec. Extraction, not judgement."""
    client = _client()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "low"},
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT.format(design_text=design_text),
            }
        ],
        output_format=DesignSpec,
    )
    spec = response.parsed_output
    if spec is None:  # pragma: no cover
        raise RuntimeError("extraction returned no parsed output")
    return spec
