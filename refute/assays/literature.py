"""Constants recovered from published work, and the ones that were not.

Everything here came from a PubMed-only attempt on 2026-08-04, recorded so the
Paperclip run has a baseline to beat and so the reasoning is auditable. Values
are LITERATURE or DERIVED - never MEASURED. That tier is reserved for
`fibrin_contracture`, whose numbers are fitted to primary data in this
repository.

Read the blocked lists as the substantive content. Across every protocol
attempted, effect sizes and precision estimates were recoverable and failure
rates were not - which is the asymmetry the project exists to demonstrate.

The distinction between NOT_REPORTED and NOT_YET_SEARCHED is load-bearing and
is kept scrupulously. Most constants below are NOT_YET_SEARCHED because a
shallow pass over abstracts is not a search; claiming otherwise would inflate
the headline with silence.
"""

from __future__ import annotations

from .evidence import Blocked, BlockedReason, CalibrationReport, Evidence

# --- sources ---------------------------------------------------------------

GOOD_2019 = "10.1186/s42490-019-0014-z"        # scar-in-a-jar, BMC Biomed Eng
MARINKOVIC_2012 = "10.1152/ajplung.00108.2012"  # traction vs matrix stiffness
YANG_2021 = "10.1007/978-1-0716-1382-5_14"      # TFM protocol chapter
JENKINS_2017 = "10.1165/rcmb.2017-0096ST"       # ATS bleomycin workshop report

# The query actually run, kept alongside the null results it produced. A
# NOT_REPORTED claim is only as good as the search behind it.
SCAR_QUERY = (
    "scar-in-a-jar macromolecular crowding collagen deposition cell layer "
    "detachment delamination troubleshooting ascorbate stability "
    "[PubMed + full text of Good 2019, PMC7422573]"
)

# --- scar_in_a_jar ---------------------------------------------------------
# The only protocol whose full text was retrievable, and therefore the only one
# where a NOT_REPORTED claim is currently defensible.

SCAR_IN_A_JAR = CalibrationReport(
    key="scar_in_a_jar",
    found=(
        Evidence(
            constant="tgfb_fold_change",
            value=4.7,
            units="x",
            source=GOOD_2019,
            quote=(
                "TGF-b (1 ng/ml) in crowding conditions significantly induced a "
                "3.2-fold increase in a-SMA, a 4.7-fold increase in collagen type I "
                "and a 3.7-fold increase in collagen type IV."
            ),
            note=(
                "Collagen I specifically. The paper's mean signal:background over "
                "480 IC50 determinations was 4.6, so 4.7 is not an outlier run."
            ),
        ),
        Evidence(
            constant="well_to_well_cv",
            value=0.107,
            units="fraction",
            source=GOOD_2019,
            quote=(
                "The average assay signal to background ratio of 4.6 ... achieving "
                "Z' values of 0.49-0.51 confirming assay robustness."
            ),
            derived=True,
            assumption=(
                "Z' = 1 - 3(sd_pos + sd_neg)/|mean_pos - mean_neg|. With Z'=0.50 and "
                "signal:background 4.6 (background normalised to 1), sd_pos + sd_neg "
                "= 0.6. Assumes constant CV across the range, i.e. sd proportional to "
                "mean, giving CV = 0.6/5.6. An equal-SD assumption instead gives ~0.065, "
                "so this constant is uncertain to roughly a factor of 1.6 and should be "
                "swept, not reported as a point value."
            ),
            note=(
                "NOT the CV quoted in the paper. The abstract says '<5' and the results "
                "say 'under 15%', and both refer to inter-assay CV of control-compound "
                "potency, not to well-to-well spread of the deposition readout. The "
                "abstract/results discrepancy is only visible in full text."
            ),
        ),
    ),
    blocked=(
        Blocked(
            constant="p_delaminate_by_endpoint",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "Full methods, results and discussion read end to end. Delamination "
                "is never mentioned, in any direction - not as a rate, not as an "
                "exclusion criterion, not as a limitation. The paper reports a >95% "
                "assay success rate over 480 IC50 determinations but does not "
                "decompose the ~5% of failures."
            ),
            searched=SCAR_QUERY,
        ),
        Blocked(
            constant="delamination_time_h",
            reason=BlockedReason.NOT_REPORTED,
            detail="Same source, same absence. No time-to-failure is reported.",
            searched=SCAR_QUERY,
        ),
        Blocked(
            constant="p_confluence_artifact",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "Confluence is specified as a precondition ('left for 24 h ... to "
                "reach confluence') but the frequency with which it fails is not "
                "given. The >95% success rate is a plate-level figure covering all "
                "causes and cannot be attributed to this one."
            ),
            searched=SCAR_QUERY,
        ),
        Blocked(
            constant="ascorbate_halflife_h",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "Concentration is given precisely (L-ascorbic acid, 50 ug/ml final) "
                "and the culture runs 72 h, but no replenishment schedule and no "
                "stability data appear. Ascorbate oxidises in culture medium over "
                "hours, so whether it was still present at the endpoint is "
                "unrecoverable from the paper."
            ),
            searched=SCAR_QUERY,
        ),
        Blocked(
            constant="baseline_deposition",
            reason=BlockedReason.ASSAY_SPECIFIC,
            detail=(
                "Reported as mean fluorescence intensity on a specific instrument "
                "and algorithm (CellInsight, 'Cell Health Profiling v4'). The number "
                "exists but is not transferable; only the ratio to background is."
            ),
        ),
    ),
)

# --- traction_force --------------------------------------------------------
# Two constants are blocked for reasons that are *not* about the literature:
# one is published as a different quantity, and one cannot exist as a scalar.

TRACTION_FORCE = CalibrationReport(
    key="traction_force",
    found=(),
    blocked=(
        Blocked(
            constant="tgfb_fold_change",
            reason=BlockedReason.CONTEXT_DEPENDENT,
            detail=(
                "Ill-posed as a single number. Marinkovic et al. show TGF-b1 "
                "'selectively accentuates tractions on stiff matrices, mimicking "
                "fibrotic lung, but not on physiological stiffness matrices, despite "
                f"equivalent changes in Smad2/3 activation' ({MARINKOVIC_2012}). The "
                "fold change is a function of substrate modulus, so the protocol "
                "needs a response surface, not a constant. This is a finding about "
                "the model, not a gap in the corpus."
            ),
        ),
        Blocked(
            constant="baseline_strain_energy",
            reason=BlockedReason.UNITS_MISMATCH,
            detail=(
                "The field reports traction *stress* - Yang et al. give 100 pN/um to "
                f"2 nN/um ({YANG_2021}) - where this protocol's readout is strain "
                "*energy* per cell in pJ. Converting requires the displacement field "
                "and spread area, which are not published alongside the stresses."
            ),
        ),
        Blocked(
            constant="measurement_cv",
            reason=BlockedReason.NOT_YET_SEARCHED,
            detail="Only abstracts screened; cell-to-cell CV would be in figures.",
        ),
        Blocked(
            constant="p_detach_baseline_per_h",
            reason=BlockedReason.NOT_YET_SEARCHED,
            detail="Requires full-text methods across many TFM papers.",
        ),
        Blocked(
            constant="detach_force_coupling",
            reason=BlockedReason.NOT_YET_SEARCHED,
            detail="Requires detachment stratified by traction; likely unpublished.",
        ),
        Blocked(
            constant="p_field_unusable",
            reason=BlockedReason.NOT_YET_SEARCHED,
            detail="Field-rejection rates would sit in image-analysis methods.",
        ),
    ),
)

# --- bleomycin_lung --------------------------------------------------------
# Predicted most likely to calibrate, because welfare reporting forces mortality
# into the record. Untested: the ATS report's PMC full text returned empty.

BLEOMYCIN_LUNG = CalibrationReport(
    key="bleomycin_lung",
    found=(),
    blocked=tuple(
        Blocked(
            constant=name,
            reason=BlockedReason.NOT_YET_SEARCHED,
            detail=(
                "PubMed reached the ATS workshop report "
                f"({JENKINS_2017}) but its PMC full text returned an empty body, so "
                "no numbers were extracted. This protocol is the standing prediction: "
                "mortality should be recoverable here, because animal welfare "
                "reporting obliges authors to publish deaths - the one place the "
                "literature must record its failures."
            ),
        )
        for name in (
            "baseline_score",
            "bleomycin_effect",
            "animal_to_animal_sd",
            "mortality_by_day14",
            "mortality_severity_coupling",
            "p_dosing_failure",
        )
    ),
)

# Protocols not yet attempted at all. Listed rather than omitted so the
# denominator in any headline figure stays honest.
NOT_ATTEMPTED = ("cell_derived_matrix", "fibrosis_on_chip", "stiffness_drift")

REPORTS: dict[str, CalibrationReport] = {
    r.key: r for r in (SCAR_IN_A_JAR, TRACTION_FORCE, BLEOMYCIN_LUNG)
}
