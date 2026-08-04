"""The baseline rule, which a live run caught being wrong.

gpt-5.5 proposed adding treatment at 0.75 h and imaging at 1 h as the
normalisation baseline. That is a real protocol and a good baseline - fifteen
minutes into a 24 h treatment time-constant the gel has moved about 1% of the
effect. The twin nonetheless discarded every well, because it demanded an image
at or before t0 exactly, and scored the design 0%.

A scorer that rejects sound designs on a technicality manufactures agent
failures. These tests pin the corrected rule from both sides: the window is
wide enough to admit a baseline taken just after treatment, and narrow enough
to reject one taken after the effect has begun to develop.
"""

from __future__ import annotations

import math

from refute.calibration import DEFAULT_PARAMS
from refute.design import DesignSpec
from refute.score import score_design
from refute.twin import TREATMENT_TAU_H, baseline_tolerance_h

ARMS = ["N-SS", "N-T", "N-CM", "N-CM+T"]


def _design(treatment_h: float, imaging: list[float], endpoint: float) -> DesignSpec:
    return DesignSpec(
        conditions=ARMS,
        replicates_per_condition=3,
        imaging_times_h=imaging,
        treatment_time_h=treatment_h,
        endpoint_time_h=endpoint,
        antifibrinolytic=False,
        normalise_to_own_baseline=True,
        locked_imaging_protocol=True,
    )


def test_tolerance_is_derived_from_calibration_not_chosen():
    """It must fall out of the effect size, the treatment time-constant and the
    noise floor - if someone replaces it with a round number, the link to the
    measurements is lost."""
    tol = baseline_tolerance_h()
    contamination = abs(DEFAULT_PARAMS.tgfb_effect_pct) * (
        1.0 - math.exp(-tol / TREATMENT_TAU_H)
    )
    assert contamination < DEFAULT_PARAMS.measurement_noise_pct
    assert 1.0 < tol < 6.0, f"implausible tolerance {tol:.2f} h"


def test_baseline_just_after_treatment_is_accepted():
    """The exact design the twin used to throw away."""
    score = score_design(_design(0.75, [1.0, 6.0, 24.0, 48.0, 72.0], 72.0), n_sims=200)
    assert score.mean_usable_wells > 5, "wells discarded despite a valid baseline"
    assert score.testable_rate > 0.4
    assert not any("no imaging within" in d for d in score.diagnoses)


def test_baseline_long_after_treatment_is_still_rejected():
    """The window must not become a licence to normalise to a post-effect image:
    at 24 h the treatment has developed and the 'baseline' contains part of the
    effect it is supposed to divide out."""
    score = score_design(_design(0.0, [24.0, 48.0, 72.0], 72.0), n_sims=200)
    assert any("no imaging within" in d for d in score.diagnoses)


def test_a_true_pre_treatment_image_is_preferred_when_one_exists():
    """With images on both sides of t0, the earlier one is the baseline."""
    from refute.twin import ExperimentTwin

    design = _design(24.0, [1.0, 12.0, 26.0, 48.0], 48.0)
    plate = ExperimentTwin(seed=0).simulate_many(design, 1)[0]
    assert plate._baseline_time() == 12.0
