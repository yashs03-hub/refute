"""Constants recovered from published work, and the ones that were not.

`scar_in_a_jar` below is a PubMed-only attempt from 2026-08-04, kept as the
baseline the later Paperclip sweeps had to beat. Every other protocol's report
now comes from `assays/findings/` - one module per scaffold, produced by a
dual-instrument sweep (Paperclip plus NCBI E-utilities, every quote checked
against fetched full text) rather than an abstract skim. Values are LITERATURE
or DERIVED - never MEASURED. That tier is reserved for `fibrin_contracture`,
whose numbers are fitted to primary data in this repository.

Read the blocked lists as the substantive content. Across every protocol
attempted, effect sizes and precision estimates were recoverable far more
often than failure rates were - which is the asymmetry the project exists to
demonstrate, though the sweeps found it is not absolute: see
`findings/traction_force.py` and `findings/stiffness_drift.py` for the two
places a near-miss or a genuine measurement complicates the clean story, and
`findings/stiffness_drift.py` for a case where the swept evidence pushes back
on this registry's own hazard declaration.

The distinction between NOT_REPORTED and NOT_YET_SEARCHED is load-bearing and
is kept scrupulously. A constant is NOT_REPORTED only when a real query came
back empty on a real instrument, recorded in `searched=`.
"""

from __future__ import annotations

from . import findings
from .evidence import Blocked, BlockedReason, CalibrationReport, Evidence

# --- sources ---------------------------------------------------------------

GOOD_2019 = "10.1186/s42490-019-0014-z"        # scar-in-a-jar, BMC Biomed Eng

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

# --- the other five scaffolds -----------------------------------------------
# Each is a dual-instrument sweep (Paperclip + NCBI E-utilities) recorded as
# its own module in `findings/`, one searcher per scaffold, so five people
# could run these concurrently without touching this file. See each module
# for the reporting-boundary argument specific to it - it is not the same
# argument every time, and flattening them into one paragraph here would lose
# exactly the differences worth having.

# Every tier-1 scaffold has now been attempted. Kept as a tuple rather than
# deleted so a caller checking `NOT_ATTEMPTED` for a live denominator finds an
# explicit empty set instead of an AttributeError - see `adapt.py`'s docstring
# on why this list exists at all.
NOT_ATTEMPTED: tuple[str, ...] = ()

REPORTS: dict[str, CalibrationReport] = {
    r.key: r
    for r in (
        SCAR_IN_A_JAR,
        findings.traction_force.REPORT,
        findings.bleomycin_lung.REPORT,
        findings.cell_derived_matrix.REPORT,
        findings.fibrosis_on_chip.REPORT,
        findings.stiffness_drift.REPORT,
    )
}
