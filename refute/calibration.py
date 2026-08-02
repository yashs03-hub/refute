"""Calibration constants for the Experiment 4 digital twin.

EVERY constant here is one of three kinds, and the kind is always stated:

  MEASURED    - read directly off Experiment 4 (anchored fibrin gel contracture
                assay, human synovial fibroblasts, 12-well plate, June 2026).
  FITTED      - derived from MEASURED values by a fit recorded in this file.
  ASSUMED     - not observed in Experiment 4. These are the twin's soft spots
                and every one is flagged. Do not present a twin result that
                leans on an ASSUMED value without saying so.

The single most important ASSUMED value is `APROTININ_HAZARD_SCALE`: Experiment
4 contained no antifibrinolytic arm, so the twin has no empirical basis for how
much aprotinin extends scaffold survival. It only knows what happened *without*
it. A design that scores well purely because it added aprotinin is being scored
against an assumption, not a measurement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Source record
# --------------------------------------------------------------------------

SOURCE = (
    "Experiment 4, MPhil research project. Anchored fibrin gel contracture "
    "assay (Roberts 2022 'contracture-in-a-well' model), primary human synovial "
    "fibroblasts, 12-well plate, cast 2026-06-12, treatments applied Day 5. "
    "Conditions by column: N-SS (serum-starved control), N-T (TGF-b1), "
    "N-CM (MSC-conditioned media), N-CM+T (both). Rows A/B/C = replicates. "
    "n=10 evaluable (A1 excluded: casting failure; B3 excluded: contamination)."
)

# --------------------------------------------------------------------------
# Contraction kinetics
# --------------------------------------------------------------------------

# MEASURED - pooled mean fill% (gel area / well area) by hours since cast.
# Conditions were identical pre-treatment, so these pool all 10 evaluable wells.
OBSERVED_FILL_PCT: dict[int, float] = {24: 18.6, 72: 14.6, 96: 14.9, 120: 11.8}
OBSERVED_FILL_SD: dict[int, float] = {24: 5.3, 72: 2.6, 96: 3.1, 120: 2.4}

# MEASURED - nominal fill at cast: the gel fills the well.
INITIAL_FILL_PCT = 100.0

# FITTED - exponential decay fit reported in experiment4_analysis_summary.md.
# fill(t) = PLATEAU + (INITIAL - PLATEAU) * exp(-t / TAU)
PLATEAU_FILL_PCT = 13.8          # => 86% area reduction
CONTRACTION_HALF_TIME_H = 5.8
CONTRACTION_TAU_H = CONTRACTION_HALF_TIME_H / math.log(2)   # ~8.37 h

# KNOWN RESIDUAL - the single exponential predicts Day 1 almost exactly
# (18.70 vs 18.60 measured) but overpredicts Day 5 by +2.0 fill-points: the
# constructs kept creeping in slowly after the fast phase. At Day-5 SD 2.4
# with n=10 that is ~2.6 SE, so it is borderline - possibly real slow creep,
# possibly noise. Modelled as an optional slow linear term, default on but
# small, and WEAKLY IDENTIFIED: only one post-plateau timepoint constrains it.
SLOW_CREEP_PCT_PER_DAY = 0.5     # FITTED (weakly), from the Day-5 residual

# MEASURED - why dense early sampling matters. The first imageable timepoint
# was Day 1, by which contraction was already >=80% complete. That is why a
# Boltzmann sigmoid could not be fitted: t0 and slope were unidentifiable with
# a single pre-plateau point. A design that first images at 24 h inherits this.
FIRST_IMAGEABLE_TIMEPOINT_H = 24
CONTRACTION_FRACTION_COMPLETE_AT_24H = 0.94   # FITTED from the decay curve

# --------------------------------------------------------------------------
# Fibrinolytic scaffold failure
# --------------------------------------------------------------------------

# MEASURED - Day 10 endpoint. TGF-b+ arms (N-T, N-CM+T): 6/6 lysed.
# TGF-b- arms (N-SS, N-CM): 0/4 lysed (collapsed onto pins, not dissolved).
# Fisher exact p = 0.0048. Day 7 was transitional, not a clean cutoff.
LYSIS_OBSERVED = {
    "tgfb_positive": {"lysed": 6, "total": 6, "at_hours": 240},
    "tgfb_negative": {"lysed": 0, "total": 4, "at_hours": 240},
    "fisher_exact_p": 0.0048,
    "day7_note": "transitional - one N-CM well fully intact and tethered, "
                 "one N-T well held a large detached contracted gel, others lysing",
}

# FITTED - Weibull survival S(t) = exp(-(t / scale)^SHAPE), fitted to the two
# observed anchors: TGF-b+ ~50% failed at 168 h (Day 7, transitional) and
# 6/6 failed by 240 h (Day 10); TGF-b- 0/4 failed by 240 h.
LYSIS_WEIBULL_SHAPE = 4.108
LYSIS_SCALE_H_CONTRACTILE = 183.7      # TGF-b+ : S(168)=0.50, S(240)=0.05
LYSIS_SCALE_H_QUIESCENT = 494.5        # TGF-b- : S(168)=0.99, S(240)=0.95

# ASSUMED (NOT MEASURED) - Experiment 4 had no aprotinin arm. This multiplier
# on the Weibull scale encodes "aprotinin roughly quadruples scaffold survival",
# which is a literature-shaped guess, not a result. Sweep it; never report a
# single number that depends on it.
APROTININ_HAZARD_SCALE = 4.0
APROTININ_IS_ASSUMED = True
APROTININ_RECOMMENDED_KIU_PER_ML = (100, 200)

# --------------------------------------------------------------------------
# Well-level variation, attrition, measurement
# --------------------------------------------------------------------------

# MEASURED - per-well Day1->Day3 fill ratios spanned 0.60-0.96, i.e. large
# baseline heterogeneity between wells before any treatment existed. This is
# why an analysis must normalise each well to its OWN pre-treatment area: a
# between-well comparison at endpoint is swamped by this spread.
BASELINE_RATIO_RANGE = (0.60, 0.96)
WELL_EFFECT_LOG_SD = 0.18        # FITTED - lognormal multiplier reproducing that spread

# MEASURED - 2 of 12 wells lost, for two different reasons.
P_CAST_FAILURE = 1 / 12          # A1: construct never formed
P_CONTAMINATION = 1 / 12         # B3: microbial overgrowth, excluded all timepoints

# MEASURED - imaging protocol determines whether a well is measurable at all.
# Handheld whole-plate frames with glare defeated every segmentation method
# tried (brightness, texture, greenness, HSV-saturation, neck-profile). The
# locked protocol (individual well, centred, light on, dark matte background,
# saturated phenol-red medium) segmented 11/12.
P_MEASURE_OK_LOCKED_PROTOCOL = 11 / 12
P_MEASURE_OK_UNCONTROLLED = 0.10

# MEASURED - quantification precision was stated as +/-2-3 fill-points, driven
# by diffuse gel edges. FITTED split: segmentation error on a given well is
# partly a fixed bias (that well's edge is consistently read slightly in or
# out, so it CANCELS in a per-well ratio) and partly per-frame randomness
# (which does not). Split so the two add in quadrature to ~2.5.
MEASUREMENT_BIAS_PCT = 1.8       # per-well, systematic, cancels under ratioing
MEASUREMENT_NOISE_PCT = 1.7      # per-frame, random, does not cancel

# CONSEQUENCE, not an input: with ~1.7 fill-points of irreducible per-frame
# noise on a ~13.8 baseline, a per-well endpoint ratio carries ~17% noise.
# Detecting a difference smaller than that at n=3 is not possible. This is the
# binding constraint on the assay, and it is independent of fibrinolysis.

# MEASURED - Day-5 (t0) plateau by condition, before treatment could have acted.
# Included as a calibration check: the twin should show no condition separation
# at t0, because none existed.
DAY5_FILL_BY_CONDITION = {"N-SS": 13.1, "N-T": 11.3, "N-CM": 13.4, "N-CM+T": 10.4}

# MEASURED - the design actually run.
TREATMENT_TIME_H = 120           # Day 5 = t0
PLATE_WELLS = 12
CONDITIONS = ("N-SS", "N-T", "N-CM", "N-CM+T")


@dataclass(frozen=True)
class TwinParams:
    """A single parameterisation of the twin.

    Defaults are the Experiment 4 calibration. Vary these to propagate
    calibration uncertainty instead of reporting one point estimate.
    """

    plateau_fill_pct: float = PLATEAU_FILL_PCT
    contraction_tau_h: float = CONTRACTION_TAU_H
    slow_creep_pct_per_day: float = SLOW_CREEP_PCT_PER_DAY
    lysis_shape: float = LYSIS_WEIBULL_SHAPE
    lysis_scale_contractile_h: float = LYSIS_SCALE_H_CONTRACTILE
    lysis_scale_quiescent_h: float = LYSIS_SCALE_H_QUIESCENT
    aprotinin_hazard_scale: float = APROTININ_HAZARD_SCALE
    well_effect_log_sd: float = WELL_EFFECT_LOG_SD
    p_cast_failure: float = P_CAST_FAILURE
    p_contamination: float = P_CONTAMINATION
    measurement_noise_pct: float = MEASUREMENT_NOISE_PCT
    measurement_bias_pct: float = MEASUREMENT_BIAS_PCT

    # The quantity a design is scored on recovering. Experiment 4 never
    # measured it - the fibrinolysis destroyed the treatment window - so it is
    # injected as ground truth rather than calibrated.
    tgfb_effect_pct: float = -3.0     # TGF-b1 contracts further (lower fill)
    msc_cm_rescue_frac: float = 0.6   # MSC-CM reverses this fraction of it
    effect_is_injected: bool = field(default=True, init=False)


DEFAULT_PARAMS = TwinParams()
