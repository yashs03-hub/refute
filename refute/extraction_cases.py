"""Hand-written designs with known specs, to validate extraction.

Extraction is the one component sitting directly upstream of the headline number
with nothing testing it. `0% -> 97% testable` could in principle be partly a
parsing artifact, and until this set runs there is no way to say it is not.

Each case is prose a researcher might plausibly write, paired with the fields it
should produce. Written to be *adversarial* rather than easy - the failure modes
each one probes are named in `probes`:

    units       days and hours mixed in the same paragraph
    negation    an absence stated in words, which must become `false`
    distractor  a named reagent that is NOT an antifibrinolytic
    scope       a feature the twin cannot represent, which must be recorded
                rather than dropped
    implicit    a fact stated obliquely, never with the field's vocabulary

`expected` lists only the fields the prose actually determines. A case does not
assert anything about a field its text leaves open - otherwise the test would be
measuring the extractor's guessing rather than its reading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExtractionCase:
    key: str
    prose: str
    expected: dict[str, Any]
    probes: tuple[str, ...] = ()
    note: str = ""


CASES: tuple[ExtractionCase, ...] = (
    # ---------------------------------------------------------------- units
    ExtractionCase(
        key="mixed_units",
        prose="""\
I would cast twelve constructs and split them across four groups of three:
serum-starved control, TGF-b1 alone, MSC-conditioned media alone, and both
together. Treatments go on at Day 5. I would photograph each well individually
on the fixed rig against the dark background at 6 hours, then on Day 1, Day 3,
Day 5 and finally Day 7, which is my endpoint. Each well's Day 7 area is divided
by its own Day 5 area before any group comparison. No aprotinin or other
protease inhibitor is included in the fibrin mix.""",
        expected={
            "replicates_per_condition": 3,
            "treatment_time_h": 120.0,
            "endpoint_time_h": 168.0,
            "imaging_times_h": [6.0, 24.0, 72.0, 120.0, 168.0],
            "antifibrinolytic": False,
            "normalise_to_own_baseline": True,
            "locked_imaging_protocol": True,
        },
        probes=("units", "negation"),
        note="Days and hours interleaved; the absence is stated in prose.",
    ),
    # ----------------------------------------------------------- distractor
    ExtractionCase(
        key="distractor_reagent",
        prose="""\
Two arms only - TGF-b1 and TGF-b1 plus conditioned media - at six wells each,
using the whole plate on the comparison that matters. Ascorbic acid at
50 ug/mL is included throughout to support collagen deposition. Treatment at
120 h, endpoint at 168 h, imaging at 2, 6, 12, 24, 48, 120 and 168 hours, each
well normalised to its own pre-treatment frame, all images taken in the jig with
the ruler in shot.""",
        expected={
            "replicates_per_condition": 6,
            "endpoint_time_h": 168.0,
            # Ascorbate is a named reagent and is NOT an antifibrinolytic. An
            # extractor pattern-matching "a chemical was added" gets this wrong.
            "antifibrinolytic": False,
            "normalise_to_own_baseline": True,
            "locked_imaging_protocol": True,
        },
        probes=("distractor",),
        note="A prominent reagent that must not be read as scaffold protection.",
    ),
    # ------------------------------------------------------------- implicit
    ExtractionCase(
        key="implicit_protection",
        prose="""\
Because cell-mediated proteolysis of fibrin is the obvious hazard over a
seven-day culture, I would supplement the gel with tranexamic acid throughout
and end the experiment at 168 hours rather than pushing to Day 10. Four
conditions, three wells each. Treatments at Day 5. Imaging at 4, 12, 24, 72, 120
and 168 hours. I would hand-hold the phone over the whole plate for speed.
Endpoint areas are compared between groups as means.""",
        expected={
            # Stated as a reason for a choice, never as "I am adding an
            # antifibrinolytic" - the extractor has to know what TXA is.
            "antifibrinolytic": True,
            "anticipates_scaffold_failure": True,
            "endpoint_time_h": 168.0,
            "replicates_per_condition": 3,
            # Both of these are stated in the negative sense and must come
            # through as False.
            "locked_imaging_protocol": False,
            "normalise_to_own_baseline": False,
        },
        probes=("implicit", "negation"),
        note="TXA named without the category word; two fields must be False.",
    ),
    # ---------------------------------------------------------------- scope
    ExtractionCase(
        key="out_of_scope_matrix",
        prose="""\
Fibrin is the wrong scaffold for a ten-day experiment, so I would cast the
constructs in rat-tail collagen I at 2 mg/mL instead, which the fibroblasts
remodel without dissolving. Otherwise: two arms, six wells each, treatment at
Day 5, endpoint Day 7, imaging at 6, 24, 120 and 168 hours, per-well
normalisation, fixed imaging rig.""",
        expected={
            "replicates_per_condition": 6,
            "endpoint_time_h": 168.0,
            "normalise_to_own_baseline": True,
            "locked_imaging_protocol": True,
            # The whole point: this must be RECORDED, not dropped. Scoring a
            # collagen design as though it were fibrin is the permissive failure.
            "__out_of_scope_nonempty__": True,
        },
        probes=("scope",),
        note="A design the twin cannot represent. Silence here is the bug.",
    ),
    # ----------------------------------------------------- units, aggressive
    ExtractionCase(
        key="everything_in_days",
        prose="""\
Design: four arms at n=3. Cast on day zero. Add treatments on day five.
Image on days one, two, three, five, seven and ten, with day ten as the
endpoint. Aprotinin at 200 KIU/mL goes into the fibrin mix because the gels
will not otherwise survive that long. Individual well images on the rig;
each construct is normalised to its own day-five image.""",
        expected={
            "replicates_per_condition": 3,
            "treatment_time_h": 120.0,
            "endpoint_time_h": 240.0,
            "imaging_times_h": [24.0, 48.0, 72.0, 120.0, 168.0, 240.0],
            "antifibrinolytic": True,
            "anticipates_scaffold_failure": True,
            "normalise_to_own_baseline": True,
            "locked_imaging_protocol": True,
        },
        probes=("units",),
        note="Every time is a spelled-out day; all must convert to hours.",
    ),
)


@dataclass
class CaseResult:
    """How one case fared."""

    key: str
    passed: bool
    mismatches: list[str] = field(default_factory=list)
    error: str | None = None


def check(case: ExtractionCase, spec: Any) -> CaseResult:
    """Compare an extracted spec against what the prose determines."""
    mismatches: list[str] = []
    for name, want in case.expected.items():
        if name == "__out_of_scope_nonempty__":
            got = spec.unmodelled()
            if bool(got) is not want:
                mismatches.append(
                    f"out_of_twin_scope: expected {'non-empty' if want else 'empty'}, "
                    f"got {got!r}"
                )
            continue

        got = getattr(spec, name)
        if name == "imaging_times_h":
            # Order-insensitive, and a design may legitimately image more often
            # than the prose enumerates; the stated times must all be present.
            missing = sorted(set(want) - set(got))
            if missing:
                mismatches.append(f"imaging_times_h: missing {missing} (got {sorted(got)})")
            continue

        if got != want:
            mismatches.append(f"{name}: expected {want!r}, got {got!r}")

    return CaseResult(key=case.key, passed=not mismatches, mismatches=mismatches)
