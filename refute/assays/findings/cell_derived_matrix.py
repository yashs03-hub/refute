"""Calibration findings for `cell_derived_matrix`, swept 2026-08-16.

INSTRUMENT
----------
Paperclip full-text corpus (`paperclip grep` / `paperclip search -s pmc,biorxiv`)
was primary, per PLAN 6.2. PubMed/NCBI E-utilities was secondary and is only
responsible for two documents that Paperclip does not index - PMC5995326 and
PMC7681936, both Methods in Cell Biology protocol chapters, both fetched via
`efetch db=pmc` and read in full. Every other document below was read through
Paperclip. `paperclip map` was unavailable ("Parallel map workers are currently
limited to GXL testers"), so full-text extraction was done by hand.

The choice of instrument mattered. Every constant recovered here, and every
sentence establishing that a constant is absent, comes from a methods,
troubleshooting or quality-control section. Not one of them is in an abstract.

QUERIES RUN
-----------
Corpus-wide `paperclip grep -i` over /papers/ (regex, ~11M full texts):

    matrix (detachment|delamination)
    (delaminat|detach)[a-z]* (during|upon|after) (the )?decellulariz
    matrices (delaminated|were lost|detached from)
    matri(x|ces) .{0,40}(dislodg|delaminat)
    [0-9.]+ ?% of (the )?(matrices|CDM|FDM|wells|coverslips) (were |was )?(lost|excluded|discarded|damaged|detached)
    cultures were (lost|discarded) (to|due to|because of) (bacterial |fungal |microbial )?contamination
    (cell-derived matri|fibroblast-derived matri|CDM).{0,120}contaminat
    contamination rate of [0-9.]+ ?%
    incomplete decellulariz
    (rate|frequency|proportion) of (incomplete|failed|unsuccessful) decellulariz
    (CDM|FDM|fCDM|matrices) .{0,60}[0-9.]+ ?.?.?m (in )?thick
    matrix thickness of [0-9.]+ ?.?.?m
    cell-derived matri[a-z]+ .{0,90}thick
    TGF.{0,10}(increased|induced).{0,60}(matrix|ECM|CDM|FDM).{0,40}(thickness|alignment).{0,60}[0-9]
    matri(x|ces) (thickness|were) .{0,40}(increased|thicker) .{0,40}[0-9.]+.?fold

plus eight `paperclip search -s pmc,biorxiv` semantic queries on CDM production,
decellularisation, thickness, TGF-beta-induced alignment and CAF-versus-normal
matrix anisotropy.

Roughly 200 titles/abstracts were screened off those searches; grep hit-lists
spanned several hundred more documents; ten papers were read in full text.

WHAT THE FAILURE CONSTANTS LOOKED LIKE UP CLOSE
-----------------------------------------------
This scaffold turned out to be the cleanest demonstration of the asymmetry so
far, because here the literature does not merely omit the failure - it
*documents the failure mode in detail and then omits the rate*.

Three independent protocol chapters carry "the matrix comes off during
decellularisation" as a named entry in a troubleshooting table:

  - Franco-Barraza 2020: "3D fCDM are detached during the decellularization
    process", and separately "3D fCDM are detached after removing extraction
    buffer".
  - Harris 2018: a whole subsection, "POTENTIAL PITFALLS AND TROUBLESHOOTING",
    opening on "the fragility of a cell-derived decellularized ECM".
  - The trabecular-meshwork chapter 2020: "CDMs detach from 60mm tissue culture
    plastics or circular 12mm glass coverslips".

The last of these comes closest to a mechanism, and it is worth being precise
about how close, because an earlier draft of this file overstated it. The
sentence is "This may cause interactive forces among CDMs to be greater than
their tethering to their substrate, hence detaching." It is verbatim, but it
sits in the *mitigation* column of a troubleshooting row whose *cause* column
reads "Duration of crosslinking CDM may be too much", and the words
"pre-stress" and "prestress" do not appear anywhere in the chapter. So the
force the paper invokes is attributed to a processing variable - an optional
crosslinking step held too long - and not to contractile pre-stress
accumulated by the cells.

That distinction matters for this scaffold. If the paper attributed detachment
to matrix contractility, the destructive step would be coupled to the measured
phenotype by published mechanism, which is the strongest form of the argument.
It does not. The coupling remains a modelling assumption; what the corpus
supplies is the weaker and still useful claim that a force balance between the
matrix and its substrate is the acknowledged failure mode. What is missing
either way is the only thing a power calculation needs, which is how often it
happens.

Nobody gives a number. Not a rate, not a count, not a range, not "in our hands
roughly". Three chapters, three mitigation lists, zero denominators.

The near-miss is worth recording because it shows the omission is not a
publishing-format constraint. Jones 2022, a 384-well CDM screen, reports
per-well loss to four significant figures: "229 of 924 total wells from all
three screens were excluded from further analysis, with 152 wells excluded for
insufficient matrix, 4 wells excluded for cell toxicity, and 77 that failed
both criteria" - about 25%. It is not `p_delaminate_decell`, because that assay
fixes on day 5 and never decellularises; the loss is poor fibrillogenesis and
imaging error, a different failure with a different driver. But it proves the
field will publish a per-well denominator when the assay is framed as a screen.
The number goes missing when the paper is framed as a protocol, which is
exactly the survivorship shape the project predicts. (Note also that the same
paper's two statements of its own exclusion count, "229" and "Of the 288
excluded wells", do not agree, and 152+4+77 is 233. Even where the denominator
is published it is not checked.)

WHAT WAS RECOVERABLE, AND FROM WHERE
------------------------------------
`baseline_thickness`  Harris 2018, via NCBI (not in Paperclip's index).
`measurement_cv`      Jones 2022, via Paperclip.

Both are precision/effect quantities and both are in methods or QC prose. That
is the same split every other protocol in this project has shown.

`tgfb_fold_change` is blocked, but not for absence. It is ill-posed here: the
scaffold's readout is "thickness or alignment", and those two do not share a
fold scale - one is an unbounded length, the other a fraction with an isotropic
floor near 17%. Worse, the sign of the thickness effect is not stable across
the corpus. That is a finding about the model, not a gap.
"""

from __future__ import annotations

from ..evidence import Blocked, BlockedReason, CalibrationReport, Evidence

# --- sources ---------------------------------------------------------------

HARRIS_2018 = "10.1016/bs.mcb.2017.08.007"          # Methods Cell Biol, Schwarzbauer lab
JONES_2022 = "10.1158/2767-9764.CRC-22-0157"        # Cancer Res Commun, HT CDM screen
FRANCO_BARRAZA_2020 = "10.1016/bs.mcb.2019.11.014"  # Methods Cell Biol, Cukierman lab
RAGHUNATHAN_2020 = "10.1016/bs.mcb.2019.10.008"     # Methods Cell Biol, trabecular meshwork CDM
RAFAEVA_2023 = "10.3389/fimmu.2023.1154528"         # Front Immunol, FDM desmoplasia
DE_LA_JARA_ORTIZ_2024 = "10.1101/2024.09.26.614950"  # bioRxiv, TGF-beta-induced myCAF CDM
GARNA_2026 = "10.1021/acsomega.5c13590"             # ACS Omega, decellularisation refinement
SANTIAGO_TIERNO_2024 = "10.1101/2024.02.28.582372"  # bioRxiv, subendothelial matrix AFM

# The queries actually run, kept beside the null results they produced. A
# NOT_REPORTED claim is only as good as the search behind it, and these are
# transcribed verbatim from the shell rather than reconstructed afterwards.

DELAM_QUERY = (
    "paperclip grep -i over /papers/ (full-text corpus): "
    r"'matrix (detachment|delamination)'; "
    r"'(delaminat|detach)[a-z]* (during|upon|after) (the )?decellulariz'; "
    r"'matrices (delaminated|were lost|detached from)'; "
    r"'matri(x|ces) .{0,40}(dislodg|delaminat)'; "
    r"'[0-9.]+ ?% of (the )?(matrices|CDM|FDM|wells|coverslips) (were |was )?"
    r"(lost|excluded|discarded|damaged|detached)'"
    " + paperclip search -s pmc 'cell-derived matrix delamination rate during "
    "decellularization fibroblast fraction of wells lost'"
    " + full text of Franco-Barraza 2020 (PMC7298733), Harris 2018 (PMC5995326) "
    "and Raghunathan 2020 (PMC7681936) troubleshooting sections read end to end"
)

CONTAM_QUERY = (
    "paperclip grep -i over /papers/ (full-text corpus): "
    r"'cultures were (lost|discarded) (to|due to|because of) "
    r"(bacterial |fungal |microbial )?contamination'; "
    r"'(cell-derived matri|fibroblast-derived matri|CDM).{0,120}contaminat'; "
    r"'contamination rate of [0-9.]+ ?%'"
    " + the three CDM protocol chapters above, read for any per-run loss figure"
)

DECELL_QUERY = (
    "paperclip grep -i over /papers/ (full-text corpus): "
    r"'incomplete decellulariz'; "
    r"'(rate|frequency|proportion) of (incomplete|failed|unsuccessful) decellulariz'"
    " + full text of Garna 2026 (PMC13294919), the one paper that systematically "
    "varies decellularisation stringency on fibroblast CDM"
)

# --- cell_derived_matrix ---------------------------------------------------

REPORT = CalibrationReport(
    key="cell_derived_matrix",
    found=(
        Evidence(
            constant="baseline_thickness",
            value=12.5,
            units="um",
            source=HARRIS_2018,
            quote=(
                "After decellularization, the matrix retains the thickness and "
                "fibrillar organization as before cell removal. In the case of NIH "
                "3T3 cells, the matrix retains a thickness of approximately 10-15 "
                "um when cultured for ~1 week."
            ),
            derived=True,
            assumption=(
                "Midpoint of the reported 10-15 um range. The range is stated for "
                "NIH 3T3 at ~1 week post-confluence, which is the scaffold's cell "
                "type and the scaffold's 7-10 day window, and it is stated for the "
                "matrix *after* decellularisation, which is the scaffold's readout. "
                "No SD is given, so the midpoint carries no dispersion with it."
            ),
            note=(
                "Cell type and substrate preparation move this several-fold and the "
                "canonical protocol says so outright: Franco-Barraza 2020 "
                f"({FRANCO_BARRAZA_2020}) gives 10 um or more for conditioned "
                "NIH-3T3, sets an acceptance floor of 'a minimum averaged thickness "
                "of 7 um', and warns that 'if fixed gelatin is used averages will be "
                "lower, ~5 um' - while primary lung fibroblasts reach 20-30 um "
                "(10.1063/5.0204393). Franco-Barraza states the constraint directly: "
                "'ECM thickness should be determined for each fibroblastic cell type "
                "and batch.' Treat 12.5 um as the NIH-3T3 reference point, not as a "
                "protocol-wide constant."
            ),
        ),
        Evidence(
            constant="measurement_cv",
            value=0.035,
            units="fraction",
            source=JONES_2022,
            quote=(
                "For the control and 1 ng/mL TGFb1-treated matrices, the Z'-factor "
                "was greater than 0.5, and the coefficient of variation was 3%-4%, "
                "indicating sufficient separation of the positive and negative "
                "signals, low variance, and feasibility for adaptation to HTS."
            ),
            derived=True,
            assumption=(
                "Midpoint of the reported 3%-4% range. Reported for the 24-well CDM "
                "assay under both control and 1 ng/mL TGF-b1, so it is a within-arm "
                "figure rather than a pooled one. The paper does not say what the "
                "replicate unit is; the matching figure legend reads 'Points indicate "
                "three separate experiments', so this is plausibly experiment-to- "
                "experiment rather than well-to-well, in which case it is an upper "
                "bound on within-plate spread."
            ),
            note=(
                "This is the CV of the *alignment* readout - the fraction of fibres "
                "within 20 degrees of the mode orientation angle - not of thickness. "
                "That matters more than it looks. The readout is a bounded fraction "
                "with an isotropic floor near 30/180 = 0.17 and a practical ceiling "
                "well under 1, so a 3-4% CV is partly an artefact of a compressed "
                "scale and is not comparable to a CV on an unbounded intensity. Do "
                "not reuse it for a thickness readout in um; no CV on CDM thickness "
                "was found anywhere in the sweep."
            ),
        ),
    ),
    blocked=(
        Blocked(
            constant="p_delaminate_decell",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "The strongest NOT_REPORTED in the project so far, because the "
                "absence is not inattention. Three independent protocol chapters "
                "carry this exact failure as a named troubleshooting entry - "
                f"Franco-Barraza 2020 ({FRANCO_BARRAZA_2020}): '3D fCDM are detached "
                "during the decellularization process'; Harris 2018 "
                f"({HARRIS_2018}): 'A major variable that can affect results is the "
                "fragility of a cell-derived decellularized ECM'; Raghunathan 2020 "
                f"({RAGHUNATHAN_2020}): 'CDMs detach from 60mm tissue culture "
                "plastics or circular 12mm glass coverslips'. Raghunathan states a "
                "force balance - 'This may cause interactive forces among CDMs to be "
                "greater than their tethering to their substrate, hence detaching' - "
                "but attributes it to a processing variable, not to the measured "
                "phenotype: that sentence is the mitigation for a row whose cause "
                "reads 'Duration of crosslinking CDM may be too much', and "
                "'pre-stress' appears nowhere in the chapter. Each entry is followed "
                "by a mitigation "
                "list - gentler pipetting, no vacuum aspiration, gelatin coating, "
                "shorter crosslinking, silanised coverslips - and by no rate. "
                "Santiago Tierno 2024 "
                f"({SANTIAGO_TIERNO_2024}) reports having solved it ('chemical "
                "modification of glass coverslips that prevents matrix detachment "
                "during decellularization') without ever saying how often it "
                "happened before or after. "
                "The near-miss: Jones 2022 "
                f"({JONES_2022}) publishes per-well loss for a 384-well CDM screen - "
                "'229 of 924 total wells ... were excluded', about 25% - but that "
                "assay fixes on day 5 and has no decellularisation step, so the loss "
                "is poor fibrillogenesis and imaging error, not delamination. It is "
                "the right shape of number for the wrong failure, and mapping it "
                "onto this constant would be a fabrication."
            ),
            searched=DELAM_QUERY,
        ),
        Blocked(
            constant="p_contamination_10d",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "Contamination-driven culture loss is reported freely elsewhere in "
                "cell biology - patient-derived organoid papers give counts ('Two "
                "patient-derived cultures were discarded due to bacterial "
                "contamination' out of 19), primary-culture papers give fractions, "
                "and one plant tissue-culture paper gives 'over 50%'. None of it is "
                "CDM. Across the CDM corpus the 7-10 day deposition window is "
                "described dozens of times, always as a schedule and never with an "
                "attrition figure attached. Raghunathan 2020 "
                f"({RAGHUNATHAN_2020}) comes closest, listing 'Trabecular meshwork "
                "cells die in the course of the 4-week duration of CDM deposition' "
                "as a troubleshooting entry - the long-culture failure is "
                "acknowledged, quantified nowhere. The general cell-culture "
                "contamination surveys that do exist are not transferable: they "
                "cover facility-level or primary-isolate rates over open-ended "
                "periods, not a defined 7-10 day run of an established fibroblast "
                "line on coverslips."
            ),
            searched=CONTAM_QUERY,
        ),
        Blocked(
            constant="p_incomplete_decell",
            reason=BlockedReason.UNITS_MISMATCH,
            detail=(
                "This one is published, but as a continuous quality metric rather "
                "than a per-well event rate. The field measures residual dsDNA in ng "
                "per mg dry weight and fragment length in bp, against a widely used "
                "pass criterion of 'less than or equal to 50 ng dsDNA mg-1 dry weight "
                "and <200 bp fragment length'. Garna 2026 "
                f"({GARNA_2026}) is the only paper found that systematically varies "
                "decellularisation stringency on fibroblast CDM, and it reports "
                "'DNA removal (up to 98.3%)' and box-and-whisker dsDNA distributions "
                "(n = 4-5) - never a fraction of wells failing. Its one categorical "
                "statement is degenerate for calibration purposes: 'All conditions "
                "exceeded the accepted decellularization threshold ... confirming "
                "insufficient nuclear removal under these preliminary conditions', "
                "i.e. p = 1 under a protocol the authors then abandoned. "
                "The conversion is well-defined and the constant is therefore "
                "recoverable in principle: with per-sample dsDNA values and the 50 "
                "ng/mg threshold, the failure probability is the fraction of the "
                "distribution above the line. Those per-sample values exist, in "
                "figure panels rather than in tables, so this needs figure "
                "extraction rather than another search. Note also Garna's own caveat "
                "that the DNA metric under-reports the failure - 'the presence of "
                "intracellular proteins detected by proteomic analysis suggests that "
                "the complete removal of cellular remnants was not achieved. This "
                "highlights the limitation of relying on DNA-based metrics alone' - "
                "so any probability derived this way is a lower bound."
            ),
            searched=DECELL_QUERY,
        ),
        Blocked(
            constant="tgfb_fold_change",
            reason=BlockedReason.CONTEXT_DEPENDENT,
            detail=(
                "Ill-posed as a scalar for this scaffold, for two independent "
                "reasons, and neither is a gap in the corpus. "
                "First, the readout is two quantities that do not share a fold "
                "scale. Thickness is an unbounded length in um; alignment is the "
                "fraction of fibres within 15-20 degrees of the mode angle, which "
                "has an isotropic floor near 30/180 = 0.17, so a 'fold change' on it "
                "is bounded above by about 6 and is not scale-free. The field does "
                "not even treat alignment as continuous: Franco-Barraza 2020 "
                f"({FRANCO_BARRAZA_2020}) uses a category boundary - 'ECM is "
                "determined to be aligned if greater than 55% of fibers are oriented "
                "within this 30 degree range' - and then says of the cutoff, in the "
                "same sentence, '(this number was et empirically and it is "
                "arbitrary)'. A threshold an author calls arbitrary will not carry a "
                "fold change. "
                "Second, the sign of the thickness effect is not stable. "
                "de la Jara Ortiz 2024 "
                f"({DE_LA_JARA_ORTIZ_2024}) finds TGF-b-induced myCAF CDMs 'are "
                "significantly thicker, as compared to those produced by uninduced "
                "or IL1a-induced fibroblasts', while Rafaeva 2023 "
                f"({RAFAEVA_2023}) finds the opposite for the activated phenotype - "
                "'CAF FDM is also significantly thinner than NF FDM's' - and gives "
                "the reason it is not really a fibrosis axis at all: 'Thickness was "
                "previously shown to positively correlate with the fibroblasts' "
                "density'. Thickness tracks how many cells are stacked up, which "
                "activation can push either way. "
                "Direction on alignment is consistent - Jones 2022 "
                f"({JONES_2022}) has 'NIH/3T3s treated with 1-10 ng/mL TGFb1 "
                "produced highly aligned matrices ... as compared with the control "
                "cells' - but no treated-versus-control numbers appear in any text, "
                "table or caption read in this sweep; they are in figure panels "
                "only. So a numeric alignment effect is retrievable by figure "
                "extraction, whereas a single thickness-or-alignment fold change is "
                "not retrievable at all, because it does not exist as one number. "
                "Sweep this as a response surface over readout and cell type."
            ),
        ),
    ),
)
