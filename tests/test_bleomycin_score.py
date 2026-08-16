"""`score_bleomycin_design` - power/testability arithmetic, the
survivorship-bias diagnostic (the mechanism this whole build exists to
demonstrate), and the multi-constant assumption-sensitivity sweep."""

from __future__ import annotations

from dataclasses import replace

import pytest

from refute.bleomycin_calibration import DEFAULT_BLEOMYCIN_PARAMS
from refute.bleomycin_design import (
    BLEOMYCIN_MSC,
    BLEOMYCIN_ONLY,
    BleomycinDesignSpec,
    OutOfTwinScopeError,
)
from refute.bleomycin_score import HEADLINE_CONTRAST, score_bleomycin_design


def _design(**overrides) -> BleomycinDesignSpec:
    base = dict(
        conditions=[BLEOMYCIN_ONLY, BLEOMYCIN_MSC],
        replicates_per_condition=20,
        msc_dosing_day=3.0,
        msc_route="IT",
        endpoint_day=21.0,
    )
    base.update(overrides)
    return BleomycinDesignSpec(**base)


def test_headline_contrast_matches_the_canonical_conditions():
    assert set(HEADLINE_CONTRAST) == {BLEOMYCIN_ONLY, BLEOMYCIN_MSC}


def test_a_design_missing_the_headline_contrast_scores_zero_not_an_error():
    """The exact footgun found by hand this session on the fibrin side: a
    design missing half the contrast the scorer tests must score a flat 0%,
    for a reason that has nothing to do with sample size - not raise, and
    not silently substitute another comparison."""
    design = _design(conditions=[BLEOMYCIN_ONLY], replicates_per_condition=50)
    score = score_bleomycin_design(design, n_sims=100)
    assert score.power == 0.0
    assert score.testable_rate == 0.0


def test_declined_design_is_distinguishable_from_a_zero_power_one():
    design = _design(replicates_per_condition=0)
    score = score_bleomycin_design(design, n_sims=50)
    assert score.declined
    assert "declines" in score.summary().lower()


def test_out_of_scope_condition_raises_rather_than_silently_scoring():
    design = _design(conditions=[BLEOMYCIN_ONLY, "tocilizumab_arm"],
                      out_of_twin_scope=["tocilizumab has no calibrated effect"])
    with pytest.raises(OutOfTwinScopeError):
        score_bleomycin_design(design, n_sims=50)


def test_adequate_replication_detects_the_injected_effect():
    design = _design(replicates_per_condition=30)
    score = score_bleomycin_design(design, n_sims=300)
    assert score.power > 0.7, score.power


def test_thin_replication_is_underpowered():
    design = _design(replicates_per_condition=2)
    score = score_bleomycin_design(design, n_sims=300)
    assert score.power < 0.5, score.power


# -- the survivorship-bias diagnostic -----------------------------------------


def test_survivorship_bias_diagnostic_is_silent_at_the_default_coupling():
    """coupling=0 is the twin's own default (see bleomycin_calibration.py).
    The diagnostic TEXT must not fire here - see bleomycin_twin.py's KNOWN
    RESIDUAL note on why the raw field can still be slightly nonzero."""
    design = _design(replicates_per_condition=40)
    score = score_bleomycin_design(design, n_sims=300, check_assumptions=False)
    assert not any("survivorship bias detected" in d for d in score.diagnoses)


def test_survivorship_bias_diagnostic_fires_once_coupling_is_swept_positive():
    """The key test for this whole build: switching the coupling constant
    on must (a) produce a positive survivorship_bias_ashcroft field and
    (b) emit the diagnostic naming it, at a coupling large enough to clear
    Monte Carlo noise."""
    design = _design(replicates_per_condition=60)
    params = replace(DEFAULT_BLEOMYCIN_PARAMS, mortality_severity_coupling=0.8)
    score = score_bleomycin_design(design, params=params, n_sims=400,
                                    check_assumptions=False)
    assert score.survivorship_bias_ashcroft > 0.2, score.survivorship_bias_ashcroft
    assert any("survivorship bias detected" in d for d in score.diagnoses)


def test_survivorship_bias_grows_with_coupling():
    design = _design(replicates_per_condition=60)
    biases = []
    for coupling in (0.0, 0.4, 0.8):
        params = replace(DEFAULT_BLEOMYCIN_PARAMS, mortality_severity_coupling=coupling)
        score = score_bleomycin_design(design, params=params, n_sims=400,
                                        check_assumptions=False)
        biases.append(score.survivorship_bias_ashcroft)
    assert biases[0] < biases[1] < biases[2], biases


# -- assumption sensitivity ----------------------------------------------------


def test_a_design_touching_no_late_or_iv_arm_sweeps_only_the_two_universal_constants():
    """Early + IT design never reaches late_dosing_effect_multiplier or
    p_iv_procedural_death - the sweep must not claim otherwise."""
    design = _design(msc_dosing_day=3.0, msc_route="IT")
    score = score_bleomycin_design(design, n_sims=150)
    assert set(score.assumptions_in_play) == {
        "mortality_severity_coupling", "p_dosing_failure",
    }


def test_a_late_iv_design_reaches_all_four_assumed_constants():
    design = _design(msc_dosing_day=14.0, msc_route="IV")
    score = score_bleomycin_design(design, n_sims=150)
    assert set(score.assumptions_in_play) == {
        "mortality_severity_coupling", "p_dosing_failure",
        "late_dosing_effect_multiplier", "p_iv_procedural_death",
    }


def test_power_range_is_reported_when_sensitive():
    design = _design(msc_dosing_day=14.0, msc_route="IV", replicates_per_condition=8)
    score = score_bleomycin_design(design, n_sims=200)
    if score.verdict_sensitive_to_assumption:
        lo, hi = score.power_range_under_assumptions
        assert lo <= score.power <= hi
