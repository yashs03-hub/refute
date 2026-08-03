"""Case 1 — anchored fibrin gel contracture assay. The only MEASURED protocol.

Every number here comes from `refute.calibration`, which is fitted to primary
data in `cases/exp4/`. Nothing in this module invents a value; if a constant is
not in the calibration module, it does not belong here.
"""

from __future__ import annotations

from .. import calibration as cal
from .base import AssayProtocol, CalibrationStatus, Constant, HazardSpec, ReadoutSpec

PROTOCOL = AssayProtocol(
    key="fibrin_contracture",
    name="Anchored fibrin gel contracture (Roberts 2022 'contracture-in-a-well')",
    unit="well",
    status=CalibrationStatus.MEASURED,
    summary=(
        "Primary human synovial fibroblasts in an anchored fibrin construct, "
        "tethered at both ends by sutures over pins in PDMS. Gel area contracts "
        "toward a plateau; the construct is imaged per-well by phone camera."
    ),
    why_it_matters=(
        "The reference case. Its treatment window was destroyed by "
        "cell-mediated fibrinolysis, and it was never published - which is the "
        "entire reason it is useful as ground truth."
    ),
    readout=ReadoutSpec(
        name="fill",
        units="% of well area occupied by gel",
        direction="decreases",
        destructive=False,
        constants=(
            Constant("plateau_fill_pct", cal.PLATEAU_FILL_PCT, "%",
                     "FITTED - exponential fit, 86% area reduction"),
            Constant("contraction_tau_h", cal.CONTRACTION_TAU_H, "h",
                     "FITTED - from 5.8 h half-time"),
            Constant("measurement_noise_pct", cal.MEASUREMENT_NOISE_PCT, "fill-points",
                     "FITTED - per-frame random component of +/-2-3 stated precision"),
            Constant("measurement_bias_pct", cal.MEASUREMENT_BIAS_PCT, "fill-points",
                     "FITTED - per-well systematic component; cancels under ratioing"),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Plasmin-mediated fibrinolysis dissolves the scaffold",
        driver="contractility (TGF-b1 exposure)",
        driver_is_the_measured_phenotype=True,
        mitigation="antifibrinolytic (aprotinin ~100-200 KIU/ml) - EFFECT SIZE ASSUMED",
        constants=(
            Constant("lysis_shape", cal.LYSIS_WEIBULL_SHAPE, "-",
                     "FITTED - Weibull shape from Day 7 / Day 10 anchors"),
            Constant("lysis_scale_contractile_h", cal.LYSIS_SCALE_H_CONTRACTILE, "h",
                     "FITTED - TGF-b+ : 6/6 lysed by 240 h"),
            Constant("lysis_scale_quiescent_h", cal.LYSIS_SCALE_H_QUIESCENT, "h",
                     "FITTED - TGF-b- : 0/4 lysed by 240 h (Fisher p=0.0048)"),
            Constant("aprotinin_hazard_scale", cal.APROTININ_HAZARD_SCALE, "x",
                     "ASSUMED - no antifibrinolytic arm existed. Sweep, never report a "
                     "single value"),
        ),
    ),
    attrition_constants=(
        Constant("p_cast_failure", cal.P_CAST_FAILURE, "probability",
                 "MEASURED - A1, construct never formed"),
        Constant("p_contamination", cal.P_CONTAMINATION, "probability",
                 "MEASURED - B3, microbial overgrowth"),
    ),
    calibration_needs=(),  # already calibrated
    notes=(
        "The treatment effect is INJECTED, not calibrated - fibrinolysis removed "
        "the endpoint before any MSC-CM contrast could be read. This protocol "
        "scores designs; it says nothing about whether MSC-CM works."
    ),
    references=(
        "Roberts et al. 2022, contracture-in-a-well model",
        "cases/exp4/PROVENANCE.md",
    ),
)
