"""The extraction validation set.

Two layers. The checker and the fixtures are tested offline and always run. The
live check - does the extractor actually read these correctly - needs a
credential and is skipped without one, because a suite that silently costs money
is a suite people stop running.
"""

from __future__ import annotations

import os

import pytest

from refute.design import DesignSpec
from refute.extraction_cases import CASES, check


def test_every_case_probes_something_and_says_what():
    for c in CASES:
        assert c.probes, f"{c.key} must name the failure mode it probes"
        assert c.note, f"{c.key} must explain itself"
        assert c.expected, f"{c.key} must assert something"


def test_the_probes_cover_the_known_failure_modes():
    covered = {p for c in CASES for p in c.probes}
    assert {"units", "negation", "distractor", "scope", "implicit"} <= covered


def test_prose_never_uses_the_schema_vocabulary():
    """If the prose names the fields, the test measures copying, not reading.

    Only the distinctive names count. `conditions` is also the field name, but
    "four conditions, three wells each" is how a scientist writes - excluding
    ordinary English would make the fixtures unnatural, which is its own way of
    failing to test the real task.
    """
    tells = {n for n in DesignSpec.model_fields if "_" in n} | {"antifibrinolytic"}
    for c in CASES:
        lowered = c.prose.lower()
        for name in tells:
            assert name not in lowered, f"{c.key} leaks the schema term '{name}'"


def test_checker_accepts_a_correct_spec():
    from refute.design import EXPERIMENT_4_AS_RUN

    case = next(c for c in CASES if c.key == "everything_in_days")
    good = EXPERIMENT_4_AS_RUN.model_copy(
        update={
            "antifibrinolytic": True,
            "anticipates_scaffold_failure": True,
            "imaging_times_h": [24, 48, 72, 120, 168, 240],
        }
    )
    assert check(case, good).passed


def test_checker_reports_each_mismatch_by_field():
    from refute.design import EXPERIMENT_4_AS_RUN

    case = next(c for c in CASES if c.key == "everything_in_days")
    result = check(case, EXPERIMENT_4_AS_RUN)  # no antifibrinolytic, wrong times

    assert not result.passed
    joined = " ".join(result.mismatches)
    assert "antifibrinolytic" in joined
    assert "imaging_times_h" in joined


def test_checker_allows_extra_imaging_timepoints():
    """Imaging more often than the prose enumerates is not a parsing error."""
    from refute.design import EXPERIMENT_4_AS_RUN

    case = next(c for c in CASES if c.key == "everything_in_days")
    generous = EXPERIMENT_4_AS_RUN.model_copy(
        update={
            "antifibrinolytic": True,
            "anticipates_scaffold_failure": True,
            "imaging_times_h": [6, 24, 48, 72, 96, 120, 168, 240],
        }
    )
    assert check(case, generous).passed


def test_checker_catches_a_dropped_out_of_scope_feature():
    """The permissive failure: a collagen design read as though it were fibrin."""
    from refute.design import EXPERIMENT_4_AS_RUN

    case = next(c for c in CASES if c.key == "out_of_scope_matrix")
    dropped = EXPERIMENT_4_AS_RUN.model_copy(
        update={
            "conditions": ["N-T", "N-CM+T"],
            "replicates_per_condition": 6,
            "endpoint_time_h": 168.0,
            "out_of_twin_scope": [],  # the bug
        }
    )
    result = check(case, dropped)
    assert not result.passed
    assert any("out_of_twin_scope" in m for m in result.mismatches)


def test_checker_ignores_whitespace_only_scope_entries():
    from refute.design import EXPERIMENT_4_AS_RUN

    case = next(c for c in CASES if c.key == "out_of_scope_matrix")
    noise_only = EXPERIMENT_4_AS_RUN.model_copy(
        update={
            "conditions": ["N-T", "N-CM+T"],
            "replicates_per_condition": 6,
            "endpoint_time_h": 168.0,
            "out_of_twin_scope": ["  "],
        }
    )
    assert not check(case, noise_only).passed, "blank entries are not a recorded feature"


# ---------------------------------------------------------------------------
# The live check. Costs a handful of cheap extractor calls.
# ---------------------------------------------------------------------------

pytestmark_live = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") or not os.environ.get("REFUTE_LIVE_TESTS"),
    reason="needs OPENAI_API_KEY and REFUTE_LIVE_TESTS=1 (makes paid API calls)",
)


@pytestmark_live
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.key)
def test_extractor_reads_the_case_correctly(case):
    from refute.agent import extract_design

    spec = extract_design(case.prose)
    result = check(case, spec)
    assert result.passed, "\n".join(result.mismatches)
