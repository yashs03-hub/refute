"""Calibration constants for the bleomycin_lung digital twin.

Mirrors `calibration.py`'s structure and discipline exactly, with one
vocabulary change: nothing here is MEASURED, because none of it is this
project's own primary data. The three-tier scheme is:

  LITERATURE  - a number a published paper states, quote-verified in
                `assays/findings/bleomycin_lung.py` (baseline) or the
                2026-08-16 MSC sweep memo (treatment arm).
  DERIVED     - computed from a LITERATURE number by a transform stated in
                this file. Inherits the LITERATURE number's uncertainty plus
                whatever the transform adds.
  ASSUMED     - not observed anywhere in either sweep. Every one is flagged,
                and every one is swept at scoring time by
                `bleomycin_score._annotate_assumption_sensitivity` rather
                than reported as a point value.

THE TWO NUMBERS THAT CARRY THE MOST WEIGHT
--------------------------------------------
`MORTALITY_SEVERITY_COUPLING = 0.0` is the single most consequential
constant in this file, inherited from `assays/bleomycin_lung.py`'s own
promotion: it is the parameter that decides whether this twin's survivors
are an unbiased sample of their arm (coupling=0, the current default) or a
biased one (coupling>0). Read `bleomycin_twin.py`'s docstring before
changing the default - the whole point of leaving it at 0 is that the
survivorship-bias mechanism this project exists to demonstrate should be
something a sensitivity sweep REVEALS, not something a hardcoded default
manufactures.

`MSC_TIMING_REGIME` encodes a real disagreement in the literature, not a
settled shape. `findings for MSC in bleomycin lung fibrosis` (2026-08-16
memo) found two independent meta-analyses that disagree about whether late
MSC dosing merely weakens the effect (ZHANG_2019: late-transplant MD=-0.51,
p=0.05, "sensitive and less stable" in the authors' own sensitivity
analysis) or effectively fails (ZHAO_2021's broader read: "no clear
evidence... early or delayed"), while two primary studies disagree in the
opposite direction depending on ROUTE (SABRY_2014, IV: late dosing
"eliminated the ability... to alter the course of disease"; GAZDHAR_2013,
intratracheal, dosed on day 7: still significantly better than control at
the day-14 endpoint). Modelled as a two-regime step function
(early/late split at day 7) rather than a fitted decay curve, because
fitting a curve to two studies that disagree about its SIGN would manufacture
precision the corpus does not have.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Source record
# --------------------------------------------------------------------------

BASELINE_SOURCE = (
    "assays/bleomycin_lung.py, promoted 2026-08-16 from "
    "assays/findings/bleomycin_lung.py's dual-instrument sweep. Ferrini 2020 "
    "(10.3389/fvets.2020.588592) for Ashcroft mean+/-SD; Kim 2018 "
    "(10.1038/s41598-018-35320-8) for day-14 mortality."
)

MSC_SOURCE = (
    "2026-08-16 literature sweep, 'MSC Therapy in Bleomycin-Induced "
    "Pulmonary Fibrosis (Mouse)'. Primary sources: ZHANG_2019 "
    "(10.3892/etm.2019.7205, meta-analysis, 6 studies/228 rats), LAN_2015 "
    "(10.1186/s13287-015-0081-6, mouse, exact IT-route match), REDDY_2016 "
    "(10.15283/ijsc16041, mouse, survival curve), SABRY_2014 "
    "(10.15283/ijsc.2014.7.1.33, rat, IV timing contrast), GAZDHAR_2013 "
    "(10.1371/journal.pone.0065453, rat, IT timing contrast), QIN_2022 "
    "(10.1093/jmcb/mjac010, IV-MSC toxicology, not a bleomycin paper - "
    "imported by analogy for the IV-procedural-hazard term only)."
)

# --------------------------------------------------------------------------
# Baseline (bleomycin-only) severity and mortality
# --------------------------------------------------------------------------

# LITERATURE - Ferrini 2020, absolute Ashcroft score of the bleomycin arm
# (not the vehicle arm) and its within-arm SD, day 21, n=34.
BLEOMYCIN_ONLY_ASHCROFT_MEAN = 3.5
BLEOMYCIN_ONLY_ASHCROFT_SD = 0.6

# LITERATURE - Kim 2018, cumulative mortality at day 14, 5 mg/kg IT, n=12.
# NOT a constant of the model - the same quantity runs 0%-100% across a
# 60-fold dose range in the corpus (see assays/bleomycin_lung.py). Kept as
# the twin's single point estimate because a design still needs ONE number
# to simulate against; the uncertainty this point estimate carries is not
# currently swept here (unlike every ASSUMED constant below) because it is
# LITERATURE tier, not ASSUMED - a real number, just a noisy one. Flagging
# rather than silently treating it as settled.
MORTALITY_BY_DAY14 = 0.50

# DERIVED - probability to hazard rate, exponential model: if
# P(death by day t) = 1 - exp(-rate*t), then rate = -ln(1-P)/t. The
# simplest defensible transform: bleomycin_lung's own findings module never
# fit a Weibull shape (unlike fibrin_contracture's lysis model, which had
# real multi-timepoint data to fit one from) so inventing a shape parameter
# here would assert precision the corpus does not support.
MORTALITY_HAZARD_PER_DAY = -math.log(1 - MORTALITY_BY_DAY14) / 14.0

# --------------------------------------------------------------------------
# MSC treatment effect - severity
# --------------------------------------------------------------------------

# LITERATURE - LAN_2015, exact species+route match to this twin's own
# baseline (mouse, intratracheal bleomycin, intratracheal MSC, day-21
# Ashcroft). BLM-only control 5.0+/-1.15 vs MSC-treated 2.13-3.90 depending
# on arm; taken as the absolute reduction from LAN_2015's OWN control, since
# mixing its treated-arm number with Ferrini's differently-dosed baseline
# would blend two studies' protocols into a number neither one measured.
MSC_ASHCROFT_EFFECT = 2.87            # 5.0 - 2.13, LAN_2015's own control/treated pair

# LITERATURE - ZHANG_2019 pooled meta-analysis, 6 studies, 228 rats, early
# transplantation: MD=-0.73 (95% CI -0.99,-0.48). The conservative end of
# the swept range: pooled, cross-species (rat, not this twin's mouse
# baseline), and on a possibly different Ashcroft-variant scale than
# LAN_2015's raw score.
MSC_ASHCROFT_EFFECT_CONSERVATIVE = 0.73

# The injected default sits at the exact-match end deliberately - see
# `bleomycin_score.py`'s docstring on why the point estimate is reported
# WITH the sensitivity sweep rather than as a hedge-by-averaging midpoint,
# mirroring `APROTININ_HAZARD_SCALE`'s own convention in calibration.py.
MSC_ASHCROFT_EFFECT_RANGE = (MSC_ASHCROFT_EFFECT_CONSERVATIVE, MSC_ASHCROFT_EFFECT)

# LITERATURE, genuinely disputed - LAN_2015's treated-arm SD (0.57-0.81) is
# SMALLER than its own control SD (1.15); GAZDHAR_2013's treated-arm SD
# (0.1-0.39) is much tighter than either. Neither paper states field-count
# per animal, which `assays/bleomycin_lung.py`'s own baseline note already
# flags as the likely driver of Ashcroft SD variation. Default sits near the
# middle of the observed 0.1-1.15 span; swept across the full span, not
# point-used, per the memo's explicit caution.
MSC_TREATED_ARM_SD = 0.8
MSC_TREATED_ARM_SD_RANGE = (0.1, 1.15)

# --------------------------------------------------------------------------
# MSC treatment effect - mortality
# --------------------------------------------------------------------------

# DERIVED - REDDY_2016: vehicle mortality ~50% by day 15 (matches this
# twin's own day-14 baseline closely - corroboration, not the source of
# MORTALITY_BY_DAY14 above), MSC-treated survival 66.66+/-3.3% by day 24.
# Converted to hazard rates via the same exponential transform as above,
# then to a ratio. NOT timepoint-matched (day 15 vs day 24) - flagged
# explicitly rather than silently treated as a clean day-14-to-day-14
# comparison.
_REDDY_VEHICLE_HAZARD = -math.log(1 - 0.50) / 15.0
_REDDY_MSC_HAZARD = -math.log(0.6666) / 24.0
MSC_MORTALITY_HAZARD_RATIO = _REDDY_MSC_HAZARD / _REDDY_VEHICLE_HAZARD  # ~0.35

# --------------------------------------------------------------------------
# Timing regime - ASSUMED functional form, LITERATURE-anchored where possible
# --------------------------------------------------------------------------

# Day post-bleomycin at which MSC dosing stops counting as "early". Chosen
# to match the field's own convention, stated directly in the sweep memo:
# "immediate transplantation <1 day in 13 studies; 1 to 7 days in 21
# studies; >7 days in 8 studies" (ZHAO_2021's own Table 1 breakdown).
EARLY_DOSING_CUTOFF_DAY = 7.0

# ASSUMED - how much of the early-regime effect (severity AND mortality
# rescue) survives dosing after the cutoff. The module docstring above
# states why this is a two-regime step rather than a fitted curve: the
# corpus disagrees about the SIGN of the late-dosing effect depending on
# route, not just its size. 0.3 is a rough middle between ZHANG_2019's
# late-transplant fragile-null (~0.70 of early, but p=0.05) and
# SABRY_2014/REDDY_2016's near-total failure/mortality at late IV dosing.
# Swept across the full disagreement, not point-used.
LATE_DOSING_EFFECT_MULTIPLIER = 0.3
LATE_DOSING_EFFECT_MULTIPLIER_RANGE = (0.0, 0.7)

# --------------------------------------------------------------------------
# IV route - procedural mortality, imported by analogy
# --------------------------------------------------------------------------

# ASSUMED, and the least-grounded constant in this file - not from any
# bleomycin-fibrosis paper (none in the sweep discusses this), imported from
# QIN_2022's IV-MSC toxicology work: a mouse died of pulmonary embolism at
# 1.0x10^8 cells/kg, about 2.5x REDDY_2016's actual bleomycin-study dose
# (4x10^7 cells/kg) - same order of magnitude, not a wild extrapolation, but
# a cross-study, cross-purpose import all the same. Modelled as a one-time
# added death probability at the moment of IV injection, independent of
# bleomycin-driven mortality. Applies to IV arms only; IT arms carry none of
# this term, which is exactly why IT is the calibration_needs-recommended
# route in `assays/bleomycin_lung.py`.
P_IV_PROCEDURAL_DEATH = 0.03
P_IV_PROCEDURAL_DEATH_RANGE = (0.0, 0.10)

# --------------------------------------------------------------------------
# Inherited from the registry promotion (assays/bleomycin_lung.py)
# --------------------------------------------------------------------------

# ASSUMED, both — see that module's docstring for the full reasoning. Copied
# here as the twin's own parameters rather than imported, because
# `assays/bleomycin_lung.py` holds the REGISTRY value (what the requirement-
# resolution seam reports) and this file holds the TWIN's parameter (what
# the simulator actually consumes) - two different objects with two
# different lifecycles, the same separation `assays/bleomycin_lung.py`
# itself draws against `assays/findings/bleomycin_lung.py`.
MORTALITY_SEVERITY_COUPLING = 0.0
P_DOSING_FAILURE = 0.0

# Swept range for the coupling term. 0 is the conservative null; the upper
# end is not a literature value (none exists - this is precisely the
# BLOCKED constant) but a probe magnitude large enough to make the
# survivorship-bias mechanism visible in a sensitivity sweep without
# asserting it as the true value.
MORTALITY_SEVERITY_COUPLING_RANGE = (0.0, 0.6)
P_DOSING_FAILURE_RANGE = (0.0, 0.15)

# --------------------------------------------------------------------------
# Apparatus
# --------------------------------------------------------------------------

# Not a fixed plate size like fibrin's 12-well - in vivo cohort size is
# constrained by cost/ethics, not a physical apparatus. Used only as
# `optimize`'s/`tier0`'s default capacity, freely overridable.
DEFAULT_COHORT_CAPACITY = 40


@dataclass(frozen=True)
class BleomycinTwinParams:
    """A single parameterisation of the bleomycin twin.

    Defaults are this file's point estimates. Vary these to propagate
    calibration uncertainty instead of reporting one number - see
    `bleomycin_score._annotate_assumption_sensitivity`, which does this
    automatically for every ASSUMED constant a design actually reaches.
    """

    baseline_ashcroft_mean: float = BLEOMYCIN_ONLY_ASHCROFT_MEAN
    baseline_ashcroft_sd: float = BLEOMYCIN_ONLY_ASHCROFT_SD
    mortality_hazard_per_day: float = MORTALITY_HAZARD_PER_DAY

    # Injected ground truth for the MSC effect - the twin asks "would this
    # design detect an effect of this size", mirroring `twin.py`'s
    # `tgfb_effect_pct`/`msc_cm_rescue_frac`.
    msc_ashcroft_effect: float = MSC_ASHCROFT_EFFECT
    msc_treated_arm_sd: float = MSC_TREATED_ARM_SD
    msc_mortality_hazard_ratio: float = MSC_MORTALITY_HAZARD_RATIO

    early_dosing_cutoff_day: float = EARLY_DOSING_CUTOFF_DAY
    late_dosing_effect_multiplier: float = LATE_DOSING_EFFECT_MULTIPLIER

    p_iv_procedural_death: float = P_IV_PROCEDURAL_DEATH

    mortality_severity_coupling: float = MORTALITY_SEVERITY_COUPLING
    p_dosing_failure: float = P_DOSING_FAILURE

    effect_is_injected: bool = field(default=True, init=False)


DEFAULT_BLEOMYCIN_PARAMS = BleomycinTwinParams()

# Every ASSUMED constant this twin can reach, and the range it is swept
# across at scoring time. `bleomycin_score._annotate_assumption_sensitivity`
# iterates this dict rather than a single hardcoded check, generalizing
# `score.py`'s aprotinin-only sweep to this twin's larger set of invented
# numbers.
ASSUMED_RANGES: dict[str, tuple[float, float]] = {
    "mortality_severity_coupling": MORTALITY_SEVERITY_COUPLING_RANGE,
    "p_dosing_failure": P_DOSING_FAILURE_RANGE,
    "late_dosing_effect_multiplier": LATE_DOSING_EFFECT_MULTIPLIER_RANGE,
    "p_iv_procedural_death": P_IV_PROCEDURAL_DEATH_RANGE,
}
