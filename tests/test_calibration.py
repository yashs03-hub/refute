"""The twin must reproduce what Experiment 4 actually measured.

These are not unit tests of code paths; they are the calibration contract. If
any of them fails, the twin is not a twin of this experiment and no design
score it produces means anything.
"""

from __future__ import annotations

import numpy as np
import pytest

from refute.calibration import (
    DAY5_FILL_BY_CONDITION,
    LYSIS_OBSERVED,
    OBSERVED_FILL_PCT,
    OBSERVED_FILL_SD,
    TwinParams,
)
from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec
from refute.score import score_design
from refute.twin import ExperimentTwin

N_SIMS = 300


def test_contraction_curve_matches_measured_timecourse():
    """Mean fill% at each measured timepoint must land within 1 SD."""
    twin = ExperimentTwin(seed=1)
    twin._treatment_time = EXPERIMENT_4_AS_RUN.treatment_time_h
    for t, observed in OBSERVED_FILL_PCT.items():
        pred = twin._fill_at(float(t), "N-SS", well_effect=1.0)
        sd = OBSERVED_FILL_SD[t]
        assert abs(pred - observed) <= sd, (
            f"t={t}h predicted {pred:.2f}, measured {observed:.2f} (SD {sd})"
        )


def test_contraction_is_essentially_complete_by_first_imaging():
    """The reason Day-1-first sampling cannot identify kinetics."""
    twin = ExperimentTwin(seed=1)
    twin._treatment_time = 120.0
    plateau = twin.p.plateau_fill_pct
    at_24h = twin._fill_at(24.0, "N-SS", 1.0)
    frac_done = (100.0 - at_24h) / (100.0 - plateau)
    assert frac_done > 0.9, f"only {frac_done:.0%} complete at 24 h"


def test_no_condition_separation_before_treatment():
    """All arms were identical until Day 5 - the twin must agree."""
    twin = ExperimentTwin(seed=2)
    twin._treatment_time = 120.0
    fills = [twin._fill_at(120.0, c, 1.0) for c in DAY5_FILL_BY_CONDITION]
    assert max(fills) - min(fills) < 1e-9


def test_lysis_split_reproduces_the_day10_observation():
    """6/6 TGF-b+ lysed, 0/4 TGF-b- lysed, at Day 10 without antifibrinolytic."""
    twin = ExperimentTwin(seed=3)
    plates = twin.simulate_many(EXPERIMENT_4_AS_RUN, N_SIMS)

    tgfb_pos, tgfb_neg = [], []
    for p in plates:
        frac = p.lysed_fraction
        tgfb_pos += [frac[c] for c in ("N-T", "N-CM+T") if c in frac]
        tgfb_neg += [frac[c] for c in ("N-SS", "N-CM") if c in frac]

    pos, neg = float(np.mean(tgfb_pos)), float(np.mean(tgfb_neg))
    assert pos > 0.85, f"TGF-b+ lysis {pos:.0%}, measured 6/6"
    assert neg < 0.15, f"TGF-b- lysis {neg:.0%}, measured 0/4"
    assert pos - neg > 0.7, "the contractility-dependent split is the whole finding"


def test_experiment_4_as_run_fails_to_recover_an_effect():
    """The real design could not have detected the effect it was testing for."""
    score = score_design(EXPERIMENT_4_AS_RUN, n_sims=N_SIMS, seed=4)
    assert score.power < 0.25, f"power {score.power:.0%}; the real plate had no endpoint"
    assert any("scaffold" in d for d in score.diagnoses)


def _repaired(reps: int = 3) -> DesignSpec:
    return DesignSpec(
        conditions=["N-SS", "N-T", "N-CM", "N-CM+T"],
        replicates_per_condition=reps,
        imaging_times_h=[2, 6, 12, 24, 48, 120, 144, 168],
        treatment_time_h=120.0,
        endpoint_time_h=168.0,
        antifibrinolytic=True,
        antifibrinolytic_agent="aprotinin 150 KIU/ml",
        normalise_to_own_baseline=True,
        locked_imaging_protocol=True,
        anticipates_scaffold_failure=True,
        rationale="Antifibrinolytic, dense early sampling, endpoint inside the window.",
    )


def test_fixing_lysis_makes_the_experiment_testable():
    """Adding an antifibrinolytic converts an unrunnable plate into a runnable one."""
    as_run = score_design(EXPERIMENT_4_AS_RUN, n_sims=N_SIMS, seed=5)
    repaired = score_design(_repaired(), n_sims=N_SIMS, seed=5)

    assert repaired.mean_lysed_fraction < 0.05, "scaffold should survive to endpoint"
    assert as_run.mean_lysed_fraction > 0.3
    assert repaired.testable_rate > as_run.testable_rate + 0.4
    assert repaired.identifies_contraction_kinetics
    assert not as_run.identifies_contraction_kinetics


def test_fixing_lysis_alone_still_leaves_it_underpowered():
    """The second, independent failure: precision, not biology, is binding.

    This is the finding that matters. Experiment 4 had TWO separable defects -
    a dissolving scaffold and roughly 17x too few wells. An agent that fixes
    only the scaffold produces a runnable experiment that still cannot answer
    the question.
    """
    repaired = score_design(_repaired(), n_sims=N_SIMS, seed=5)
    assert repaired.power < 0.25, "n=3 cannot resolve the injected effect"
    assert repaired.replicates_needed > 12, (
        f"needs {repaired.replicates_needed} per arm - more than a 12-well plate holds"
    )
    assert any("underpowered" in d for d in repaired.diagnoses)


def test_design_with_adequate_replication_does_recover_the_effect():
    """Sanity check that the twin is not simply incapable of showing power."""
    score = score_design(_repaired(reps=60), n_sims=120, seed=8)
    assert score.power > 0.8, f"with n=60 per arm power was only {score.power:.0%}"
    assert score.over_plate_capacity, "240 wells cannot be one 12-well plate"


def test_aprotinin_benefit_is_flagged_as_assumed():
    """Guard against quietly presenting the uncalibrated knob as measured."""
    from refute import calibration

    assert calibration.APROTININ_IS_ASSUMED is True


@pytest.mark.parametrize("scale", [2.0, 4.0, 8.0])
def test_scaffold_rescue_is_stable_across_the_assumed_aprotinin_range(scale):
    """The one uncalibrated constant must not decide the conclusion.

    Aprotinin's effect size is ASSUMED (Experiment 4 had no such arm), so the
    claim 'an antifibrinolytic saves the endpoint' has to hold across the
    plausible range rather than at one convenient value.
    """
    params = TwinParams(aprotinin_hazard_scale=scale)
    score = score_design(_repaired(), params=params, n_sims=N_SIMS, seed=6)
    assert score.mean_lysed_fraction < 0.15, (
        f"scale={scale} left {score.mean_lysed_fraction:.0%} of wells lysed"
    )
    # And the underpowering verdict is independent of it.
    assert score.replicates_needed > 12
