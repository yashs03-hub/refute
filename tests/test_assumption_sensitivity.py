"""A verdict that rests on an uncalibrated constant must say so.

`APROTININ_HAZARD_SCALE` is tagged ASSUMED in calibration.py: Experiment 4 had
no antifibrinolytic arm, so nothing measured it. One boolean in a design reaches
it, which makes it the one place a design can score well by finding a generous
corner of the model rather than by being good.
"""

from __future__ import annotations

from dataclasses import replace

from refute.calibration import APROTININ_HAZARD_SCALE_RANGE, DEFAULT_PARAMS
from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec
from refute.score import score_design


def _design(antifibrinolytic: bool, endpoint: float = 336.0, reps: int = 6) -> DesignSpec:
    return DesignSpec(
        conditions=["N-T", "N-CM+T"],
        replicates_per_condition=reps,
        imaging_times_h=[6, 24, 120, endpoint],
        treatment_time_h=120.0,
        endpoint_time_h=endpoint,
        antifibrinolytic=antifibrinolytic,
        antifibrinolytic_agent="aprotinin 200 KIU/mL" if antifibrinolytic else None,
        normalise_to_own_baseline=True,
        locked_imaging_protocol=True,
        anticipates_scaffold_failure=antifibrinolytic,
    )


def test_a_design_without_an_antifibrinolytic_pays_nothing():
    """Most designs never reach an ASSUMED constant and must report so honestly."""
    score = score_design(_design(antifibrinolytic=False), n_sims=100)
    assert score.assumptions_in_play == []
    assert score.power_range_under_assumptions is None
    assert score.verdict_sensitive_to_assumption is False


def test_using_an_antifibrinolytic_puts_the_assumption_in_play():
    score = score_design(_design(antifibrinolytic=True), n_sims=200)
    assert score.assumptions_in_play == ["aprotinin_hazard_scale"]
    lo, hi = score.power_range_under_assumptions
    assert 0.0 <= lo <= hi <= 1.0


def test_the_flag_actually_fires_for_some_design():
    """A guard that can never trip is decoration.

    A Day-14 endpoint is far past anything Experiment 4 observed, so whether the
    plate yields data at all depends entirely on the unmeasured constant.
    """
    score = score_design(_design(antifibrinolytic=True, endpoint=336.0), n_sims=300)
    assert score.verdict_sensitive_to_assumption is True
    assert any("ASSUMED constant" in d for d in score.diagnoses)
    # The diagnosis must name the range, or the reader cannot judge the span.
    lo, hi = APROTININ_HAZARD_SCALE_RANGE
    assert any(f"{lo:g}x to {hi:g}x" in d for d in score.diagnoses)


def test_the_summary_warns_before_showing_the_number():
    """The warning must precede the numbers it qualifies."""
    score = score_design(_design(antifibrinolytic=True, endpoint=336.0), n_sims=300)
    assert score.verdict_sensitive_to_assumption is True
    summary = score.summary()
    assert "NOT robust" in summary
    assert summary.index("NOT robust") < summary.index("power to recover")


def test_the_flag_does_not_fire_for_a_verdict_that_holds():
    """It must discriminate, not fire on everything that uses aprotinin."""
    # A Day-7 endpoint sits inside the observed window, so the conclusion
    # (underpowered, and infeasible on one plate) holds at either extreme.
    score = score_design(_design(antifibrinolytic=True, endpoint=168.0), n_sims=300)
    assert score.assumptions_in_play == ["aprotinin_hazard_scale"]
    assert score.verdict_sensitive_to_assumption is False


def test_feasibility_separates_unestimable_from_feasible():
    """`infeasible_as_scoped` is False in two opposite situations.

    Conflating them is what made the sensitivity check ambiguous, so the
    tri-state is what the verdict is built on.
    """
    thin = EXPERIMENT_4_AS_RUN.model_copy(
        update={"conditions": ["N-T"], "replicates_per_condition": 1}
    )
    score = score_design(thin, n_sims=50)
    assert score.replicates_needed == -1
    assert score.infeasible_as_scoped is False
    assert score.feasibility == "unestimable", "not the same as 'fits on a plate'"

    as_run = score_design(EXPERIMENT_4_AS_RUN, n_sims=200)
    assert as_run.feasibility == "infeasible"


def test_check_assumptions_false_skips_the_extra_work():
    score = score_design(
        _design(antifibrinolytic=True), n_sims=100, check_assumptions=False
    )
    assert score.assumptions_in_play == []
    assert score.power_range_under_assumptions is None


def test_the_band_brackets_the_point_estimate():
    """The default value must sit inside its own plausible range.

    If it did not, the sweep would be describing a different model than the one
    producing the headline number.
    """
    lo, hi = APROTININ_HAZARD_SCALE_RANGE
    assert lo <= DEFAULT_PARAMS.aprotinin_hazard_scale <= hi


def test_edges_are_paired_on_the_same_seed():
    """The comparison must isolate the constant, not simulation noise.

    Same seed, only the assumed constant differing, must reproduce exactly the
    powers the sensitivity pass reports.
    """
    design = _design(antifibrinolytic=True, endpoint=336.0)
    score = score_design(design, n_sims=200, seed=11)

    lo, hi = APROTININ_HAZARD_SCALE_RANGE
    manual = [
        score_design(
            design,
            params=replace(DEFAULT_PARAMS, aprotinin_hazard_scale=v),
            n_sims=200,
            seed=11,
            check_assumptions=False,
        ).power
        for v in (lo, hi)
    ]
    assert score.power_range_under_assumptions == (min(manual), max(manual))


def test_sensitivity_does_not_alter_the_headline_numbers():
    """The extra pass must annotate, never change what it annotates."""
    design = _design(antifibrinolytic=True, endpoint=336.0)
    with_check = score_design(design, n_sims=200, seed=3)
    without = score_design(design, n_sims=200, seed=3, check_assumptions=False)

    assert with_check.power == without.power
    assert with_check.testable_rate == without.testable_rate
    assert with_check.mean_lysed_fraction == without.mean_lysed_fraction
    # Only the annotation and its diagnosis line should differ.
    assert len(with_check.diagnoses) == len(without.diagnoses) + 1
