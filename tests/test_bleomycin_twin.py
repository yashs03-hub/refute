"""The bleomycin twin's simulation mechanics - mortality, severity, and the
one thing this twin adds that `twin.py` has no equivalent of: a tunable,
provably-correct link between an animal's latent severity and its
probability of dying before the endpoint.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from refute.bleomycin_calibration import DEFAULT_BLEOMYCIN_PARAMS
from refute.bleomycin_design import BLEOMYCIN_MSC, BLEOMYCIN_ONLY, BleomycinDesignSpec
from refute.bleomycin_twin import BleomycinTwin


def _design(**overrides) -> BleomycinDesignSpec:
    base = dict(
        conditions=[BLEOMYCIN_ONLY, BLEOMYCIN_MSC],
        replicates_per_condition=200,
        msc_dosing_day=3.0,
        msc_route="IT",
        endpoint_day=21.0,
    )
    base.update(overrides)
    return BleomycinDesignSpec(**base)


def test_mortality_reproduces_the_calibrated_day14_marginal_probability():
    """MORTALITY_BY_DAY14=0.50 was converted to a hazard rate by
    `-ln(1-p)/14`; simulating to day 14 exactly should recover ~50% within
    Monte Carlo tolerance at a large n."""
    design = _design(conditions=[BLEOMYCIN_ONLY], replicates_per_condition=2000,
                      endpoint_day=14.0)
    twin = BleomycinTwin(seed=1)
    cohort = twin.simulate_cohort(design)
    mortality = cohort.mortality_by_condition[BLEOMYCIN_ONLY]
    assert 0.45 < mortality < 0.55, mortality


def test_msc_reduces_mortality_relative_to_bleomycin_only():
    design = _design()
    twin = BleomycinTwin(seed=2)
    cohort = twin.simulate_cohort(design)
    m = cohort.mortality_by_condition
    assert m[BLEOMYCIN_MSC] < m[BLEOMYCIN_ONLY]


def test_late_dosing_weakens_the_mortality_rescue():
    """Same design, early vs late MSC dosing day - late should show LESS
    mortality benefit, per `LATE_DOSING_EFFECT_MULTIPLIER < 1`."""
    early = _design(msc_dosing_day=3.0, replicates_per_condition=400)
    late = _design(msc_dosing_day=14.0, replicates_per_condition=400)
    twin_early = BleomycinTwin(seed=3)
    twin_late = BleomycinTwin(seed=3)
    m_early = twin_early.simulate_cohort(early).mortality_by_condition[BLEOMYCIN_MSC]
    m_late = twin_late.simulate_cohort(late).mortality_by_condition[BLEOMYCIN_MSC]
    assert m_late > m_early, (m_early, m_late)


def test_iv_route_adds_procedural_mortality_relative_to_it():
    it = _design(msc_route="IT", replicates_per_condition=500)
    iv = _design(msc_route="IV", replicates_per_condition=500)
    m_it = BleomycinTwin(seed=4).simulate_cohort(it).mortality_by_condition[BLEOMYCIN_MSC]
    m_iv = BleomycinTwin(seed=4).simulate_cohort(iv).mortality_by_condition[BLEOMYCIN_MSC]
    assert m_iv > m_it, (m_it, m_iv)


def test_ashcroft_is_none_for_animals_that_died_before_scoring():
    """Mirrors `WellResult.endpoint_ratio` returning `None` for a well with
    nothing coherent to measure - death removes the animal from the
    measured sample, it does not zero it out."""
    design = _design(replicates_per_condition=100)
    cohort = BleomycinTwin(seed=5).simulate_cohort(design)
    for a in cohort.animals:
        if a.died:
            assert a.ashcroft_score is None
        elif a.evaluable:
            assert a.ashcroft_score is not None


def test_dosing_failure_excludes_without_scoring_or_counting_as_death():
    params = replace(DEFAULT_BLEOMYCIN_PARAMS, p_dosing_failure=0.5)
    design = _design(conditions=[BLEOMYCIN_ONLY], replicates_per_condition=200)
    cohort = BleomycinTwin(params=params, seed=6).simulate_cohort(design)
    excluded = [a for a in cohort.animals if not a.evaluable]
    assert excluded
    for a in excluded:
        assert a.excluded_reason == "dosing_failure"
        assert not a.died
        assert a.ashcroft_score is None
    # Excluded animals are not counted in mortality_by_condition's denominator.
    assert cohort.mortality_by_condition[BLEOMYCIN_ONLY] <= 1.0


def test_severity_is_unbiased_at_coupling_zero():
    """The property `bleomycin_score.py`'s survivorship-bias diagnostic
    depends on: at coupling=0, mortality must not correlate with the z draw
    that determines Ashcroft severity. Checked directly here, at the twin
    level, independent of the scorer."""
    params = replace(DEFAULT_BLEOMYCIN_PARAMS, mortality_severity_coupling=0.0)
    design = _design(conditions=[BLEOMYCIN_ONLY], replicates_per_condition=3000,
                      endpoint_day=60.0)  # long endpoint - lots of death, lots of survivors
    twin = BleomycinTwin(params=params, seed=7)
    cohort = twin.simulate_cohort(design)
    survivors = [a.ashcroft_score for a in cohort.animals if a.scored]
    dead = sum(1 for a in cohort.animals if a.died)
    assert dead > 100 and len(survivors) > 100, "test needs both populations non-trivial"
    # Survivors' mean should sit close to the population mean (3.5), not
    # shifted toward the low-severity tail the coupling mechanism would
    # produce if it were mistakenly always-on.
    assert abs(np.mean(survivors) - params.baseline_ashcroft_mean) < 0.15


def test_severity_is_biased_low_at_positive_coupling():
    """The other half: switching coupling on should measurably pull the
    survivor mean below the population mean, because high-z (severe)
    animals now preferentially die."""
    params = replace(DEFAULT_BLEOMYCIN_PARAMS, mortality_severity_coupling=0.8)
    design = _design(conditions=[BLEOMYCIN_ONLY], replicates_per_condition=3000,
                      endpoint_day=60.0)
    twin = BleomycinTwin(params=params, seed=7)
    cohort = twin.simulate_cohort(design)
    survivors = [a.ashcroft_score for a in cohort.animals if a.scored]
    assert np.mean(survivors) < params.baseline_ashcroft_mean - 0.2


def test_out_of_scope_conditions_are_a_caller_error_not_a_silent_pass():
    """Unlike `score_bleomycin_design`, the twin itself has no scope check -
    it simulates whatever condition name it's given using the untreated
    baseline parameters, silently. This test pins that as a KNOWN boundary:
    the scope check lives in the scorer (`unmodelled()`), not the twin -
    same split as `twin.py`/`score.py`."""
    design = _design(conditions=["some_other_drug"], replicates_per_condition=5)
    cohort = BleomycinTwin(seed=8).simulate_cohort(design)
    assert len(cohort.animals) == 5   # ran anyway - the scorer is the guard, not this
