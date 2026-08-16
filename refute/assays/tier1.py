"""Tier-1 fibrosis assay scaffolds.

Selected on one criterion: **the fibrotic phenotype being measured is what
destroys the assay.** That coupling is what a power calculation cannot model
and what makes a twin worth building. An assay whose failure is merely a
function of elapsed time is real but ordinary.

**Two of the six do not meet that criterion, and saying so is cheaper than
being caught by it.** Checked 2026-08-15 against each protocol's own `driver`:

    coupled to the phenotype        traction_force, scar_in_a_jar,
                                    cell_derived_matrix, bleomycin_lung
    NOT coupled                     fibrosis_on_chip  (applied cyclic strain -
                                                       a parameter you set)
                                    stiffness_drift   (time in culture)

That matters because the coupled ones carry the property this project is
actually about: the units that fail are the ones carrying the largest effect, so
the survivors are biased toward the null and the requirement is not estimable
until the failure is fixed. An independent hazard has none of that. It is
easier - no survivorship bias, no coupling constant, and plausibly recoverable
from published methods, since a rupture rate per cycle is the kind of thing a
device paper reports.

So they are kept, but not claimed as instances of the coupled class. If the
generalisation is ever stated as "one mechanism, six instances", it is four.

Every protocol here is a SCAFFOLD. The structure is declared; the numbers are
absent and will raise `UncalibratedAssayError` if anything tries to score them.
Each carries the exact list of constants to extract and a Paperclip query to
find them - assay failure modes live in methods and troubleshooting sections,
which is why a full-text index is the right instrument.

As each is calibrated it should move to its own module (as
`fibrin_contracture.py` did) and its status change to LITERATURE or MEASURED.
"""

from __future__ import annotations

from .base import (
    AssayProtocol,
    CalibrationStatus,
    Constant,
    HazardSpec,
    ReadoutSpec,
    ScopeBasis,
    ScopeTerm,
)


def _missing(name: str, units: str, what: str) -> Constant:
    return Constant(name, None, units, f"UNCALIBRATED - {what}")


# ---------------------------------------------------------------------------
# 1. Traction force microscopy
# ---------------------------------------------------------------------------

TRACTION_FORCE = AssayProtocol(
    key="traction_force",
    name="Traction force microscopy on compliant substrate",
    unit="cell (or field of view)",
    status=CalibrationStatus.SCAFFOLD,
    summary=(
        "Cells on a bead-embedded polyacrylamide gel of known modulus. Bead "
        "displacement is inverted to a traction field; the summary readout is "
        "strain energy or total contractile moment."
    ),
    species=ScopeTerm.unspecified(
        "summary names only 'cells'; traction force microscopy is run across "
        "many species and cell lines in the literature, and this scaffold does "
        "not select one."
    ),
    tissue=ScopeTerm.unspecified("no tissue of origin is named; see species."),
    cell_type=ScopeTerm.unspecified(
        "summary says 'cells', not a specific type - traction microscopy is run "
        "on fibroblasts, myofibroblasts and smooth muscle cells alike, and this "
        "scaffold's text does not pick one."
    ),
    why_it_matters=(
        "The closest scientific analogue to case 1: contraction measurement "
        "where contractility itself drives the dropout. Cells detach under high "
        "traction, so the STRONGEST responders are lost preferentially and the "
        "survivors systematically under-report the effect. The bias is toward "
        "the null, which is the direction that quietly kills a real finding."
    ),
    readout=ReadoutSpec(
        name="strain_energy",
        units="pJ per cell",
        direction="increases",
        destructive=False,
        constants=(
            _missing("baseline_strain_energy", "pJ", "untreated median"),
            _missing("tgfb_fold_change", "x", "profibrotic stimulus effect size"),
            _missing("measurement_cv", "fraction", "cell-to-cell CV of strain energy"),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Cell detaches from the substrate under its own traction",
        driver="traction force (the readout itself)",
        driver_is_the_measured_phenotype=True,
        mitigation="higher substrate ligand density; stiffer gel (changes the biology)",
        constants=(
            _missing("p_detach_baseline_per_h", "per hour", "untreated detachment rate"),
            _missing("detach_force_coupling", "-", "how detachment scales with traction"),
        ),
    ),
    attrition_constants=(
        _missing("p_field_unusable", "probability", "drift, focus loss, bead washout"),
    ),
    calibration_needs=(
        "Detachment/cell-loss rate in untreated vs TGF-b-treated conditions",
        "Whether detached cells are excluded or silently absent from analysis",
        "Cell-to-cell CV of strain energy (sets the precision floor)",
        "Typical n per condition and imaging duration",
    ),
    paperclip_query=(
        "traction force microscopy fibroblast detachment cell loss during "
        "acquisition methods limitations TGF-beta"
    ),
    notes=(
        "Watch for survivorship: many papers report traction only for cells that "
        "stayed adherent for the full acquisition. If detachment correlates with "
        "force, that exclusion is the bias, not a cleanup step."
    ),
)


# ---------------------------------------------------------------------------
# 2. Scar-in-a-jar
# ---------------------------------------------------------------------------

SCAR_IN_A_JAR = AssayProtocol(
    key="scar_in_a_jar",
    name="Scar-in-a-jar (macromolecular crowding, accelerated collagen deposition)",
    unit="well",
    status=CalibrationStatus.SCAFFOLD,
    summary=(
        "Fibroblasts under macromolecular crowding with ascorbate deposit "
        "collagen I into an insoluble matrix over days rather than weeks. "
        "Readout is deposited collagen I by immunofluorescence or hydroxyproline."
    ),
    species=ScopeTerm.unspecified(
        "summary says 'fibroblasts' with no species; Good 2019 (the calibrated "
        "source, see findings/) uses a human line but the scaffold's own text "
        "does not commit to it, and other scar-in-a-jar papers use other lines."
    ),
    tissue=ScopeTerm.unspecified("no tissue of origin is named; see species."),
    cell_type=ScopeTerm(
        term="fibroblast",
        basis=ScopeBasis.STATED,
        note="'Fibroblasts' is the literal word in the summary.",
    ),
    why_it_matters=(
        "Best practical second case: widely used in fibrosis drug discovery, "
        "purely in vitro, well documented. Crucially it is DEPOSITION rather "
        "than contraction, so it tests whether the twin architecture generalises "
        "to a different readout while keeping the treatment-causes-failure "
        "structure - the cell layer becomes contractile and delaminates, and "
        "more TGF-b means more delamination."
    ),
    readout=ReadoutSpec(
        name="deposited_collagen_I",
        units="integrated intensity per field (or ug hydroxyproline per well)",
        direction="increases",
        destructive=False,
        constants=(
            _missing("baseline_deposition", "AU", "untreated deposition at endpoint"),
            _missing("tgfb_fold_change", "x", "profibrotic effect size"),
            _missing("well_to_well_cv", "fraction", "replicate CV"),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Contractile cell layer delaminates from the culture surface",
        driver="contractility / TGF-b dose",
        driver_is_the_measured_phenotype=True,
        mitigation="surface coating, lower seeding density, shorter culture",
        constants=(
            _missing("p_delaminate_by_endpoint", "probability", "untreated vs treated"),
            _missing("delamination_time_h", "h", "when it typically occurs"),
        ),
    ),
    attrition_constants=(
        _missing("p_confluence_artifact", "probability", "overgrowth confounding signal"),
        _missing("ascorbate_halflife_h", "h", "ascorbate is unstable; sets feed schedule"),
    ),
    calibration_needs=(
        "Delamination / sheet-lifting frequency, untreated vs TGF-b",
        "Ascorbate replenishment schedule and its stability half-life",
        "Crowder identity and whether precipitation is reported",
        "Replicate CV of the deposition readout (sets the precision floor)",
        "Typical culture duration and endpoint",
    ),
    paperclip_query=(
        "scar-in-a-jar macromolecular crowding collagen deposition cell layer "
        "detachment delamination troubleshooting ascorbate stability"
    ),
)


# ---------------------------------------------------------------------------
# 3. Cell-derived matrix
# ---------------------------------------------------------------------------

CELL_DERIVED_MATRIX = AssayProtocol(
    key="cell_derived_matrix",
    name="Cell-derived matrix (CDM) with decellularisation",
    unit="well",
    status=CalibrationStatus.SCAFFOLD,
    summary=(
        "Fibroblasts deposit matrix over 7-10 days; cells are then removed, "
        "leaving an intact matrix characterised for composition, thickness, "
        "fibre alignment or stiffness."
    ),
    species=ScopeTerm.unspecified(
        "summary says 'fibroblasts' with no species named."
    ),
    tissue=ScopeTerm.unspecified("no tissue of origin is named; see species."),
    cell_type=ScopeTerm(
        term="fibroblast",
        basis=ScopeBasis.STATED,
        note="'Fibroblasts' is the literal word in the summary.",
    ),
    why_it_matters=(
        "The failure is concentrated in a single destructive step. Matrix "
        "delaminates during decellularisation, and delamination scales with how "
        "contractile the culture became - so the most fibrotic wells are the "
        "ones most likely to be lost at the last moment, after ten days of "
        "investment."
    ),
    readout=ReadoutSpec(
        name="matrix_thickness_or_alignment",
        units="um (or alignment order parameter)",
        direction="increases",
        destructive=True,
        constants=(
            _missing("baseline_thickness", "um", "untreated matrix"),
            _missing("tgfb_fold_change", "x", "profibrotic effect size"),
            _missing("measurement_cv", "fraction", "replicate CV"),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Matrix delaminates or tears during decellularisation",
        driver="matrix contractility / pre-stress accumulated during culture",
        driver_is_the_measured_phenotype=True,
        mitigation="gentler lysis buffer, crosslinking, matrix support",
        constants=(
            _missing("p_delaminate_decell", "probability", "untreated vs treated"),
        ),
    ),
    attrition_constants=(
        _missing("p_contamination_10d", "probability", "long culture contamination"),
        _missing("p_incomplete_decell", "probability", "residual nuclei"),
    ),
    calibration_needs=(
        "Delamination rate during decellularisation, by treatment arm",
        "Contamination rate over a 7-10 day culture",
        "Whether lost wells are reported or silently dropped",
    ),
    paperclip_query=(
        "cell-derived matrix decellularization delamination matrix detachment "
        "fibroblast methods limitations"
    ),
)


# ---------------------------------------------------------------------------
# 4. Fibrosis-on-chip under cyclic stretch
# ---------------------------------------------------------------------------

FIBROSIS_ON_CHIP = AssayProtocol(
    key="fibrosis_on_chip",
    name="Fibrosis-on-chip with cyclic mechanical stretch",
    unit="chip",
    status=CalibrationStatus.SCAFFOLD,
    summary=(
        "Microfluidic device with a flexible membrane under cyclic strain, "
        "co-culturing epithelium and fibroblasts. Strain is applied as a "
        "profibrotic stimulus; readout is deposition, marker expression or "
        "barrier function."
    ),
    species=ScopeTerm.unspecified(
        "summary names the co-culture ('epithelium and fibroblasts') but no "
        "species."
    ),
    tissue=ScopeTerm.unspecified("no tissue of origin is named; see species."),
    cell_type=ScopeTerm.unspecified(
        "a co-culture of two populations - epithelium and fibroblasts - is not "
        "one term. Recording either alone would misstate what the chip runs."
    ),
    why_it_matters=(
        "The tightest coupling on this list: the profibrotic STIMULUS and the "
        "failure mode are the same variable. Cyclic strain drives the fibrotic "
        "phenotype and fatigues the membrane toward rupture, so dose and hazard "
        "cannot be separated by design - only modelled."
    ),
    readout=ReadoutSpec(
        name="fibrotic_marker_or_barrier",
        units="AU (or TEER, ohm.cm2)",
        direction="increases",
        destructive=False,
        constants=(
            _missing("baseline_readout", "AU", "unstretched control"),
            _missing("strain_dose_response", "AU per % strain", "stimulus effect"),
            _missing("chip_to_chip_cv", "fraction", "replicate CV"),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Membrane rupture, bubble ingress, or channel occlusion",
        driver="applied cyclic strain amplitude and cycle count",
        driver_is_the_measured_phenotype=True,
        mitigation="lower strain amplitude (reduces the stimulus), degassing",
        constants=(
            _missing("p_rupture_per_1e5_cycles", "probability", "by strain amplitude"),
            _missing("p_bubble_per_day", "probability", "perfusion failure rate"),
        ),
    ),
    attrition_constants=(
        _missing("p_seeding_failure", "probability", "uneven or failed seeding"),
    ),
    calibration_needs=(
        "Chip failure rate by strain amplitude and duration",
        "Bubble / occlusion incidence per day of perfusion",
        "How many chips are typically run per condition (n is usually very small)",
    ),
    paperclip_query=(
        "organ-on-chip cyclic stretch membrane rupture device failure rate "
        "fibrosis lung chip limitations bubbles"
    ),
    notes=(
        "n per condition is often 3 or fewer because chips are expensive. That "
        "makes the precision floor - the second Experiment 4 finding - likely to "
        "bind here even harder than the failure rate does."
    ),
)


# ---------------------------------------------------------------------------
# 5. Bleomycin lung fibrosis (in vivo)
# ---------------------------------------------------------------------------

BLEOMYCIN_LUNG = AssayProtocol(
    key="bleomycin_lung",
    name="Bleomycin-induced pulmonary fibrosis (murine)",
    unit="animal",
    status=CalibrationStatus.SCAFFOLD,
    summary=(
        "Intratracheal or oropharyngeal bleomycin induces lung injury and "
        "fibrosis over 14-28 days. Readout is Ashcroft score, hydroxyproline, "
        "or micro-CT density."
    ),
    species=ScopeTerm(
        term="mouse",
        ontology_id="NCBITaxon:10090",
        basis=ScopeBasis.STATED,
        note="'(murine)' is in the protocol name itself.",
    ),
    tissue=ScopeTerm(
        term="lung",
        basis=ScopeBasis.STATED,
        note=(
            "'Lung injury and fibrosis' is in the summary; readout unit is "
            "'per lung'. No UBERON id verified - left unbound rather than "
            "guessed."
        ),
    ),
    cell_type=ScopeTerm.unspecified(
        "whole-organ endpoint (Ashcroft score / hydroxyproline per lung); the "
        "protocol does not isolate or name a single cell type."
    ),
    why_it_matters=(
        "Where the money is. Effectively every fibrosis drug programme runs it, "
        "and its mortality is SEVERITY-CORRELATED: the most fibrotic animals die "
        "before the endpoint, so the measured cohort is the survivors. That is "
        "textbook treatment-correlated dropout, biasing toward the null, at real "
        "budget and real ethical cost. Naming this as the generalisation target "
        "is a stronger claim than building a third in vitro case."
    ),
    readout=ReadoutSpec(
        name="ashcroft_or_hydroxyproline",
        units="Ashcroft score (or ug hydroxyproline per lung)",
        direction="increases",
        destructive=True,
        constants=(
            _missing("baseline_score", "Ashcroft", "saline control"),
            _missing("bleomycin_effect", "Ashcroft", "vehicle-bleomycin arm"),
            _missing("animal_to_animal_sd", "Ashcroft", "within-arm SD"),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Mortality / humane endpoint before the scheduled readout",
        driver="fibrosis severity (the measured phenotype)",
        driver_is_the_measured_phenotype=True,
        mitigation="lower bleomycin dose (weakens the model), earlier endpoint",
        constants=(
            _missing("mortality_by_day14", "probability", "by bleomycin dose"),
            _missing("mortality_severity_coupling", "-", "how death scales with severity"),
        ),
    ),
    attrition_constants=(
        _missing("p_dosing_failure", "probability", "failed intratracheal instillation"),
    ),
    calibration_needs=(
        "Mortality by bleomycin dose and strain, from methods and welfare reporting",
        "Whether deaths are excluded or carried as censored observations",
        "Within-arm SD of Ashcroft / hydroxyproline (sets the precision floor)",
        "Typical group sizes and any published power justification",
    ),
    paperclip_query=(
        "bleomycin pulmonary fibrosis mouse mortality dose strain humane endpoint "
        "attrition group size methods"
    ),
    notes=(
        "Ethically loaded and worth stating: a twin that reduces the number of "
        "underpowered or doomed in vivo studies is a 3Rs argument as much as a "
        "commercial one. Reduction and refinement are exactly what a design "
        "simulator delivers."
    ),
)


# ---------------------------------------------------------------------------
# 6. Stiffness-drift - a DIFFERENT defect class
# ---------------------------------------------------------------------------

STIFFNESS_DRIFT = AssayProtocol(
    key="stiffness_drift",
    name="Stiffness-tunable hydrogel substrate (mechanotransduction)",
    unit="well",
    status=CalibrationStatus.SCAFFOLD,
    summary=(
        "Cells cultured on polyacrylamide or PEG gels of defined modulus to test "
        "how substrate stiffness drives myofibroblast activation. Stiffness is "
        "the independent variable."
    ),
    species=ScopeTerm.unspecified("summary names only 'cells', no species."),
    tissue=ScopeTerm.unspecified("no tissue of origin is named; see species."),
    cell_type=ScopeTerm.unspecified(
        "myofibroblast activation (asma-positive fraction) is the READOUT, not "
        "the starting population; the protocol does not name what the cells "
        "were before activation."
    ),
    why_it_matters=(
        "A different failure class from everything else here, and the reason to "
        "build it. Nothing breaks. The gel swells or degrades over the culture, "
        "so the INDEPENDENT VARIABLE DRIFTS - the experiment silently measures a "
        "different stiffness than the one that was set, and returns complete, "
        "clean, publishable data about the wrong condition. Every other failure "
        "on this list yields missing or degraded data that a careful scientist "
        "eventually notices. This one yields a plausible answer."
    ),
    readout=ReadoutSpec(
        name="asma_positive_fraction",
        units="fraction of cells",
        direction="increases",
        destructive=False,
        constants=(
            _missing("stiffness_response_curve", "fraction per kPa", "activation vs modulus"),
            _missing("measurement_cv", "fraction", "field-to-field CV"),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Substrate modulus drifts from its nominal value (swelling/degradation)",
        driver="time in culture, medium composition",
        driver_is_the_measured_phenotype=False,
        mitigation="re-measure modulus at endpoint rather than trusting the nominal value",
        constants=(
            _missing("modulus_drift_pct_per_day", "% per day", "swelling/degradation rate"),
            _missing("drift_depends_on_nominal", "-", "whether soft gels drift faster"),
        ),
    ),
    calibration_needs=(
        "Measured modulus at endpoint vs nominal, across the stiffness range",
        "Whether studies re-measure modulus or report only the nominal value",
        "Culture duration over which drift becomes material",
    ),
    paperclip_query=(
        "polyacrylamide hydrogel substrate stiffness drift swelling degradation "
        "modulus change culture myofibroblast mechanotransduction"
    ),
    notes=(
        "Scored differently from the others: the question is not 'did the "
        "experiment survive' but 'did it measure the condition it claimed to'. "
        "Supporting this needs an input-drift term in the engine, which none of "
        "the failure-mode protocols require."
    ),
)


TIER1 = (
    TRACTION_FORCE,
    SCAR_IN_A_JAR,
    CELL_DERIVED_MATRIX,
    FIBROSIS_ON_CHIP,
    BLEOMYCIN_LUNG,
    STIFFNESS_DRIFT,
)
