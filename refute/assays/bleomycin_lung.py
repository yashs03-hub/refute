"""Case 5 - bleomycin-induced pulmonary fibrosis (murine). LITERATURE tier.

Promoted 2026-08-16 from the scaffold in `tier1.py`, following the pattern
`fibrin_contracture.py` set: as each protocol clears calibration it gets its
own module and its status moves off SCAFFOLD. The evidence behind every
number here is `findings/bleomycin_lung.py` - read that module first, it is
the full dual-instrument sweep with every quote checked against fetched full
text. This module only carries the promotion: real values in, provenance
strings that trace back to the sweep, nothing re-derived.

WHAT PROMOTION DOES NOT DO
---------------------------
Making this protocol `runnable()` (every constant has a value, status is not
SCAFFOLD) satisfies the requirement-resolution seam - `gate.py`, `adapt.py`,
`requirements.py` will now report this protocol's requirements as filled. It
does NOT make `refute baseline` / `optimize` / `chat` / `advise` work for it.
`twin.py` and `score.py` model exactly one apparatus - an anchored fibrin gel,
contracted by fibroblasts, measured as gel area, failing by fibrinolysis -
and `DesignSpec` is documented as "the terms THE TWIN can simulate", singular.
There is no dispatch on assay key anywhere in the simulation path. Scoring a
bleomycin_lung design for real needs a second simulator - a mortality-by-day
model plus an Ashcroft-score distribution, entirely different mechanics from
fibrin contraction - which does not exist yet and is a separate, larger task.
This promotion makes the CALIBRATION RECORD honest; it does not unlock a
score.

TWO NUMBERS HERE ARE INVENTED, AND SAY SO LOUDLY
--------------------------------------------------
`mortality_severity_coupling` and `p_dosing_failure` remain BLOCKED in the
literature - `findings/bleomycin_lung.py` documents why the first is
*structurally* unrecoverable from any corpus (deaths enter the literature as a
marginal count, never as a covariate against severity) and the second is
recoverable in principle but absent from every source both instruments could
reach. `require_runnable()` needs every constant to carry a value, so both are
given ASSUMED placeholders here, in the same spirit as
`fibrin_contracture.py`'s `APROTININ_HAZARD_SCALE` - a number nobody measured,
picked so the scaffold can run at all, that must never be presented as
settled. Unlike aprotinin, NEITHER of these is currently swept at scoring time
by `score._annotate_assumption_sensitivity` - that function is hard-coded to
the one ASSUMED constant `fibrin_contracture` reaches. Generalising it to
cover this protocol's two is a real follow-up, not done here.

`mortality_severity_coupling` is the more consequential of the two by a wide
margin: it is the parameter that sets the direction and size of the
survivorship bias this whole scaffold exists to demonstrate. Set to 0.0
(severity-independent hazard - the conservative, bias-free null) rather than
to any positive value, because inventing a POSITIVE coupling here would be
asserting the very effect size the literature search just established cannot
be recovered from any published source.

`mortality_by_day14` is real (LITERATURE, not ASSUMED) but is explicitly NOT a
constant of the model - `findings/bleomycin_lung.py` states the same quantity
runs 0% to 100% across a 60-fold dose range in a single paper. 0.50 is kept as
a mid-range point estimate (Kim 2018, 5 mg/kg, day 14) because SOME value is
needed to run the scaffold, but any score produced against it inherits that
uncertainty undiminished. Read the provenance string on that constant before
trusting a number derived from it.
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

# --- sources -----------------------------------------------------------------
# Same DOIs as findings/bleomycin_lung.py; not re-imported from there because
# that module holds SEARCH EVIDENCE (Evidence/Blocked/CalibrationReport) and
# this one holds the PROMOTED REGISTRY VALUE - two different objects with two
# different lifecycles, and importing one from the other would make a future
# edit to the evidence record silently change what the twin's registry says,
# or vice versa.

FERRINI_2020 = "10.3389/fvets.2020.588592"   # Ashcroft mean +/- SD, C57BL/6
KIM_2018 = "10.1038/s41598-018-35320-8"      # cumulative mortality at day 14


def _missing(name: str, units: str, what: str) -> Constant:
    return Constant(name, None, units, f"UNCALIBRATED - {what}")


PROTOCOL = AssayProtocol(
    key="bleomycin_lung",
    name="Bleomycin-induced pulmonary fibrosis (murine)",
    unit="animal",
    status=CalibrationStatus.LITERATURE,
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
            Constant(
                "baseline_score", 0.3, "Ashcroft",
                f"LITERATURE - Ferrini 2020 ({FERRINI_2020}), saline/vehicle "
                "arm, oropharyngeal aspiration, C57BL/6, day 21, n=20, mean+/-SD "
                "stated explicitly. See findings/bleomycin_lung.py for the full "
                "quote and corroborating range.",
            ),
            Constant(
                "bleomycin_effect", 3.5, "Ashcroft",
                f"LITERATURE - Ferrini 2020 ({FERRINI_2020}), same arm/timepoint "
                "as baseline_score, n=34 bleomycin. A mid-range, not maximal, "
                "model - Kadam & Schnitzer 2024 report 4-5 at higher dose. See "
                "findings/bleomycin_lung.py.",
            ),
            Constant(
                "animal_to_animal_sd", 0.6, "Ashcroft",
                f"LITERATURE - Ferrini 2020 ({FERRINI_2020}), within-BLEOMYCIN-"
                "arm SD, read off a stated mean+/-SD rather than derived. The "
                "vehicle arm's SD is 0.2 - markedly heteroscedastic, so this is "
                "the treated-arm number, not a pooled one. See "
                "findings/bleomycin_lung.py.",
            ),
        ),
    ),
    hazard=HazardSpec(
        mechanism="Mortality / humane endpoint before the scheduled readout",
        driver="fibrosis severity (the measured phenotype)",
        driver_is_the_measured_phenotype=True,
        mitigation="lower bleomycin dose (weakens the model), earlier endpoint",
        constants=(
            Constant(
                "mortality_by_day14", 0.50, "probability",
                f"LITERATURE - Kim 2018 ({KIM_2018}), 5 mg/kg intratracheal, "
                "C57BL/6, n=12, cumulative mortality at day 14 stated "
                "explicitly. NOT a constant of the model: the same quantity "
                "runs 0%-100% across a 60-fold dose range in the corpus "
                "(Kadam & Schnitzer 2024). This is a mid-range point estimate, "
                "not a settled value - see findings/bleomycin_lung.py before "
                "trusting a score derived from it.",
            ),
            Constant(
                "mortality_severity_coupling", 0.0, "-",
                "ASSUMED - not measured, and the literature search establishes "
                "this is structurally unrecoverable from any corpus: deaths "
                "enter published bleomycin studies as a marginal count, never "
                "as a covariate against individual-animal severity, so no "
                "paper could report this even in principle "
                "(findings/bleomycin_lung.py, BLOCKED/mortality_severity_"
                "coupling). Set to 0.0 - severity-independent hazard, the "
                "conservative bias-free null - rather than any positive value, "
                "because a positive number here would assert the exact effect "
                "size the search just established cannot be recovered. This is "
                "the single most consequential invented constant in this "
                "scaffold: it sets the direction and size of the survivorship "
                "bias the protocol exists to demonstrate. Not yet swept at "
                "scoring time - see this module's docstring.",
            ),
        ),
    ),
    attrition_constants=(
        Constant(
            "p_dosing_failure", 0.0, "probability",
            "ASSUMED - not measured. Barbayianni 2018 states intratracheal "
            "administration 'always resulted in peri-operative mortality "
            "(data not shown), a feature not usually reported (or even "
            "recorded)'; Salmaso 2025 calls it 'considerable' with no number "
            "(findings/bleomycin_lung.py, BLOCKED/p_dosing_failure - absence "
            "confirmed on two instruments). Set to 0.0 for the same reason as "
            "mortality_severity_coupling - a nonzero guess would assert a "
            "magnitude no source states - despite the qualitative evidence "
            "suggesting the true rate is NOT negligible. Read as 'unmodelled', "
            "not as 'zero has been measured'.",
        ),
    ),
    calibration_needs=(
        "A per-animal (not marginal) link between severity and mortality, from "
        "a study that scores dead animals rather than excluding them",
        "A published rate of failed/technical-mortality intratracheal "
        "instillation, distinct from severity-driven death",
    ),
    paperclip_query=(
        "bleomycin pulmonary fibrosis mouse mortality dose strain humane "
        "endpoint attrition group size methods"
    ),
    references=(FERRINI_2020, KIM_2018),
    notes=(
        "Ethically loaded and worth stating: a twin that reduces the number of "
        "underpowered or doomed in vivo studies is a 3Rs argument as much as a "
        "commercial one. Reduction and refinement are exactly what a design "
        "simulator delivers - once one exists for this apparatus, which "
        "`twin.py` currently does not. See this module's docstring."
    ),
)
