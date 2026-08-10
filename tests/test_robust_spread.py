"""One anomalous well must not set the assay's precision floor.

A per-well endpoint ratio is a quotient, so its distribution has a heavy right
tail: a baseline measured small inflates the ratio without limit. `np.var` gives
every point equal leverage, so a single such well can dominate - and did. On a
120-well design the pooled within-arm SD read 4.61 where the robust estimate was
0.21, and that inflation propagated into `min_detectable_ratio_diff` and
`replicates_needed`.

The bug was invisible at n=6 (the tail is ~0.06% of wells, so a small design
rarely samples it) and only surfaced once the baselines set scored a design large
enough to hit it.
"""

from __future__ import annotations

import numpy as np

from refute.baselines import CEILING, EXPERT
from refute.score import _pooled_spread, _robust_sd, score_design
from refute.twin import MIN_MEASURABLE_FILL_PCT, ExperimentTwin


def test_robust_sd_matches_ordinary_sd_on_clean_data():
    """On well-behaved data the estimator must be a no-op, or it changes results
    it has no business changing."""
    rng = np.random.default_rng(0)
    clean = list(rng.normal(1.0, 0.2, 4000))
    np.testing.assert_allclose(_robust_sd(clean), np.std(clean, ddof=1), rtol=0.05)


def test_robust_sd_ignores_a_single_extreme_value():
    clean = [1.0, 1.1, 0.9, 1.05, 0.95, 1.02, 0.98] * 20
    poisoned = clean + [847.0]  # the actual value observed in the twin

    naive_clean = float(np.std(clean, ddof=1))
    naive_poisoned = float(np.std(poisoned, ddof=1))
    assert naive_poisoned > 20 * naive_clean, "the naive estimator must be shown to break"

    # The robust one barely moves.
    assert abs(_robust_sd(poisoned) - _robust_sd(clean)) < 0.01


def test_robust_sd_falls_back_when_mad_is_zero():
    """A degenerate arm has no tail to guard against; it must not divide by zero."""
    assert _robust_sd([2.0] * 10) == 0.0


def test_reps_needed_and_power_agree_on_a_large_design():
    """The bug's signature was an internal contradiction.

    CEILING reported 82% power while claiming 8272 wells per arm were needed,
    at n=60. Those cannot both be true: if the design has more replicates than
    it needs, power must be high.
    """
    score = score_design(CEILING, n_sims=400)
    assert score.power > 0.8
    assert 0 < score.replicates_needed <= CEILING.replicates_per_condition, (
        f"power is {score.power:.0%} at n={CEILING.replicates_per_condition} but the "
        f"scorer claims {score.replicates_needed} per arm are needed"
    )


def test_a_small_design_needs_more_than_it_has():
    """The converse, so the test above cannot pass by the estimate collapsing."""
    score = score_design(EXPERT, n_sims=400)
    assert score.power < 0.5
    assert score.replicates_needed > EXPERT.replicates_per_condition


def test_the_spread_is_stable_across_design_size():
    """EXPERT and CEILING differ only in replicates, so the assay's precision
    floor must be about the same. It was 0.26 vs 4.61."""
    lo = _pooled_spread(ExperimentTwin(seed=0).simulate_many(EXPERT, 400))[0]
    hi = _pooled_spread(ExperimentTwin(seed=0).simulate_many(CEILING, 400))[0]
    assert abs(hi - lo) < 0.1, f"spread moved from {lo:.3f} to {hi:.3f} with n alone"


def test_the_floor_is_physical_not_a_noise_multiple():
    """Regression on a fix that was wrong the first time.

    Thresholding the denominator at 3x measurement noise (5.1 fill-points) sits
    close to the TGF-b plateau of ~10.8, so it discarded legitimately strong
    contractors - preferentially removing the largest responders and biasing
    toward the null. That is the failure mode `assays/tier1.py` documents for
    traction force microscopy, and the guard must not reintroduce it.
    """
    from refute.calibration import MEASUREMENT_NOISE_PCT, PLATEAU_FILL_PCT

    assert MIN_MEASURABLE_FILL_PCT < 3.0 * MEASUREMENT_NOISE_PCT
    # Far enough below any plateau the model produces that no biology is cut.
    assert MIN_MEASURABLE_FILL_PCT < PLATEAU_FILL_PCT / 5


def test_the_guard_discards_almost_nothing():
    """If the floor were removing a meaningful share of wells it would be a
    selection effect rather than an artifact filter."""
    twin = ExperimentTwin(seed=0)
    plates = twin.simulate_many(CEILING, 200)

    measurable = below = 0
    for p in plates:
        base = p._baseline_time()
        for w in p.wells:
            if not w.evaluable:
                continue
            fill = w.fill_by_time.get(base)
            if fill is None:
                continue
            if fill < MIN_MEASURABLE_FILL_PCT:
                below += 1
            else:
                measurable += 1

    total = measurable + below
    assert total > 1000, "not enough wells to say anything"
    assert below / total < 0.005, f"floor discarded {below / total:.2%} of wells"
