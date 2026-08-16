"""Calibration findings for `traction_force`, swept 2026-08-16.

INSTRUMENT
----------
Paperclip full-text corpus (`paperclip grep` over /papers/, plus `paperclip
search -s pmc,biorxiv`) was primary, per PLAN 6.2. NCBI E-utilities
(`esearch`/`efetch` against `db=pmc`) was the second instrument and is used
below in two distinct ways: to confirm absences independently, and to reach
three documents Paperclip does not index - Yang 2025 (PMC12491448), Feng 2018
(PMC5816190) and Marinkovic 2012 (PMC3423859). Only the first of those three
came back with a usable body; the other two are discussed under the limits they
impose on themselves.

Every number and every silence recorded here comes from a methods,
troubleshooting, limitations or results section. None of it is in an abstract,
and that is exactly why the previous pass got two of these constants wrong -
see the next section.

WHAT THIS PASS OVERTURNS
------------------------
`literature.py` recorded `baseline_strain_energy` as UNITS_MISMATCH, on the
reasoning that "the field reports traction *stress* ... where this protocol's
readout is strain *energy* per cell in pJ". That is true of abstracts and false
of the corpus. A single grep for a strain energy figure carrying pJ units
returns sixteen papers on the first pass, several of them fibroblasts on
compliant polyacrylamide. The old entry was a claim about the literature made
from a sample of abstracts, which is the specific error `NOT_YET_SEARCHED`
exists to prevent, and it should not have been filed under a reason that
asserts something about publishing practice.

`measurement_cv` was NOT_YET_SEARCHED and is now recoverable, though only by
division: nobody prints the CV, but several papers print mean and SD over a
stated number of cells, which is the same information.

QUERIES RUN
-----------
Corpus-wide `paperclip grep -i` over /papers/ (regex, full-text corpus):

    cells that detached
    (detached|detachment).{0,80}traction force
    [0-9.]+ ?% of (the )?cells (detached|had detached|were lost|delaminated)
    cells (that |which )?detached during (the )?(imaging|acquisition|experiment|measurement|time.?lapse)
    (cells|cell) (that |which )?detached (was|were) (excluded|discarded|removed|not)
    cells detached from the (gel|substrate|hydrogel)
    traction.{0,180}detached from the (substrate|gel|surface)
    (spontaneous|spontaneously) detach
    (remained adherent|remained attached|stayed adherent|still adherent)
    detach.{0,60}(correlat|associat|proportional|scale[sd]?) (with|to).{0,60}(traction|contractil|force)
    (traction|contractil).{0,60}(correlat|associat|predict).{0,60}detach
    (cells|those cells) (with|exerting|generating) (the )?(highest|higher|greatest|larger) (traction|forces|contractil)
    (fields of view|FOVs|images) were (excluded|discarded|rejected|removed)
    (excluded|discarded|rejected) (from (the )?analysis )?(due to|because of|owing to) (excessive |significant )?(drift|focus|defocus)
    (cells were analyzed|cells analysed|out of) .{0,40}(cells|of the cells) (imaged|recorded|seeded|analyzed)
    strain energy of [0-9.]+ ?.{0,4}J
    strain energy.{0,60}(pJ|fJ)
    strain energy.{0,90}[0-9] ?. ?[0-9.]+ pJ
    coefficient of variation.{0,60}(traction|strain energy|contractile)
    (traction|strain energy).{0,80}coefficient of variation
    TGF.{0,60}(strain energy|traction (force|stress))
    TGF.{0,30}fold increase in (traction|strain energy|contractil)

plus seven `paperclip search -s pmc,biorxiv` semantic queries on TFM protocol
troubleshooting, TGF-b1 effects on fibroblast traction, high-traction cells
detaching, and single-cell traction versus adhesion strength.

NCBI `esearch db=pmc`, with the counts they returned:

    "traction force microscopy" AND "detachment rate per hour"        0
    "traction force microscopy" AND "fields of view were excluded"    0
    "traction force microscopy" AND "fraction of cells that detached" 1
    "traction force microscopy" AND "images were discarded"           1
    "traction force microscopy" AND "probability of detachment"       1
    "traction force microscopy" AND "cells that detached"             6
    "traction force microscopy" AND "remained adherent"               6
    "traction force microscopy" AND "coefficient of variation"
                                  AND "strain energy"                15
    "traction force microscopy" AND "detachment rate"                17
    "cells that detached" AND "traction" AND "excluded"               3

Every non-zero list above was opened and read. Nine papers were read in full
text; grep hit-lists spanned several hundred more.

WHERE THE REPORTING BOUNDARY FALLS FOR THIS SCAFFOLD
-----------------------------------------------------
It falls between the cell and the run. Anything you can measure on a cell that
survived to the end of the acquisition is published, in numbers, with a
dispersion attached. Anything about which cells got to be in that set is not.

The clearest single illustration is Xing 2022, the paper that supplies both
recovered constants. Its TFM methods read, in full: "Primary fibroblasts were
plated onto the gel, washed after 4 h to remove unbound cells, and imaged
immediately." The wash is the survivorship step - it removes exactly the cells
whose adhesion lost to something - and it is one clause long, with no
denominator on either side of it. Four sentences later the same section gives
strain energy to four significant figures with an SD.

Three TFM protocol chapters name the failure modes and skip the rates. Teo 2020
(STAR Protocols) has five numbered troubleshooting entries, of which "Problem
5: Cells are dying." and "Problem 1: Beads in different areas are not in
focus." are precisely `p_detach_baseline_per_h` and `p_field_unusable`; each is
followed by a mitigation and no frequency. Mustapha 2022 (STAR Protocols) gets
closest to a criterion - "A successful run should have cells interacting with
the substrate at the end of the experiment" - which concedes that unsuccessful
runs exist without ever saying how many, and separately describes gel cracking
as "rendering the gel unusable", again with no rate. Zancla 2022's primer
discusses regularisation, noise and reconstruction error at length and never
discusses cell attrition at all.

THE PAIR, PRECISELY
-------------------
`p_detach_baseline_per_h` and `detach_force_coupling` do not fall the same way,
and the difference matters.

The marginal rate is nearly reported. Yang 2025 (Nat Commun) carries a methods
subsection headed "Measuring probability of cell detachment of hMSC" - a
defined, time-resolved detachment probability on a compliant hydrogel, scored
by live-cell imaging every ten minutes. So the quantity is constructible and
somebody has constructed it. What stops it being this constant is a stack of
mismatches, none of which is a judgement call: the cells are hMSCs, not
fibroblasts; the substrate is a photo-responsive hydrogel being cycled between
2.2 and 1.6 kPa every minute rather than a static gel; the statistic is a
cumulative probability over 24 h rather than a per-hour hazard; and the value
itself is in Fig. 3g, not in the text. It is the right shape of number for a
different assay, and mapping it across would be a fabrication.

The coupling is not reported, and the corpus does not merely omit it - it
declines to take the sign for granted, which is worse for this project than
silence would be.

What exists on the mechanism side is genuinely stronger than what the
`cell_derived_matrix` sweep found. Yang 2025 attributes detachment to the cell's
own contractility rather than to a processing variable: "The timing of
'snap-back' events, which are triggered when intracellular contractile forces
(pMyosin IIa) exceed extracellular adhesion forces, varies significantly between
individual cells". A force balance between cell-generated force and adhesion,
stated as the trigger, with acknowledged between-cell variation in when it
fires. That is the shape this scaffold assumes.

It is not, however, an estimate of the coupling, and four things stop it being
one. Contractility is indexed by pMyosin IIa immunofluorescence, not by measured
traction. The comparison is between substrate conditions, not between cells
within one condition. The force imbalance is driven by an externally imposed
rigidity cycle, so the driver is a parameter you set rather than the readout -
the same distinction that disqualified `fibrosis_on_chip` from the coupled
class. And no coefficient is fitted, anywhere.

What exists on the measurement side runs the other way. Paddillaya 2021 puts the
two ingredients of the coupling in one paper and on the same six cell lines: a
critical de-adhesion shear stress from a fluid-shear device, and single-cell
tractions by Reg-FTTC. If the coupling were being estimated by anyone, it would
be estimated here. It is not; the two are reported side by side as independent
"mechano-diagnostic features". And the association that does emerge across the
lines has the opposite sign to this scaffold's assumption - "Fibroblasts
(NIH3T3) had the highest values of tau-10 (3.83 +/- 0.32 Pa)", and in the same
paper's discussion, "Normal cells, however, exert higher tractions than invasive
and non-invasive cells and have prominent stress fibers". The cell type that
pulls hardest is the one that is hardest to shear off.

That is a between-cell-line association measured under applied shear, so it
does not refute a within-population coupling of detachment hazard to a cell's
own traction under no applied load. Those are different quantities and the
paper never claims otherwise. But it is the nearest thing the corpus has to
evidence on the question, it points the wrong way for the project's hypothesis,
and reporting `detach_force_coupling` as a clean NOT_REPORTED without saying so
would be recording an absence while suppressing the one piece of signal in it.

So: the marginal rate is NOT_REPORTED with a near-miss in an adjacent assay; the
coupling is NOT_REPORTED with an adjacent measurement whose sign is unhelpful.
Neither is a negative result for the project's central claim about publishing
practice. The second is a caution about the modelling assumption the twin will
be built on, and it should be sized in a pilot before it is trusted.
"""

from __future__ import annotations

from ..evidence import Blocked, BlockedReason, CalibrationReport, Evidence

# --- sources ---------------------------------------------------------------

XING_2022 = "10.1038/s41598-022-26337-1"        # Sci Rep, WT vs diabetic dermal fibroblast TFM
PADDILLAYA_2025 = "10.1101/2025.03.20.644304"   # bioRxiv, HMF3s on elastic vs viscoelastic PA
PADDILLAYA_2021 = "10.1101/2021.12.30.474608"   # bioRxiv, de-adhesion strength + tractions, 6 lines
DURSO_2025 = "10.1016/j.mbm.2025.100158"        # Mech Bio Med, stiffness overrules TGF-b
MARINKOVIC_2012 = "10.1152/ajplung.00108.2012"  # AJP Lung, traction vs matrix stiffness
YANG_2025 = "10.1038/s41467-025-63854-9"        # Nat Commun, detachment under cyclic rigidity
MUSTAPHA_2022 = "10.1016/j.xpro.2022.101133"    # STAR Protocols, ultra-soft PAG TFM
TEO_2020 = "10.1016/j.xpro.2020.100098"         # STAR Protocols, PDMS TFM
ZANCLA_2022 = "10.1016/j.jbc.2022.101867"       # JBC, TFM primer
MARK_2020 = "10.7554/eLife.51912"               # eLife, spheroid collective forces in 3D
GHAGRE_2020 = "10.1101/2020.05.14.097006"       # bioRxiv, reference-free pattern contractility
FENG_2018 = "10.1073/pnas.1717870115"           # PNAS, ACTN4 podocyte detachment (abstract only)

# The queries actually run, kept beside the null results they produced. A
# NOT_REPORTED claim is only as good as the search behind it, and these are
# transcribed from the shell rather than reconstructed afterwards. Each records
# both instruments, because an absence confirmed on one index is weaker than an
# absence confirmed on two and the difference should be visible in the entry.

DETACH_QUERY = (
    "paperclip grep -i over /papers/ (full-text corpus): "
    r"'cells that detached'; "
    r"'(detached|detachment).{0,80}traction force'; "
    r"'[0-9.]+ ?% of (the )?cells (detached|had detached|were lost|delaminated)'; "
    r"'cells (that |which )?detached during (the )?(imaging|acquisition|experiment|"
    r"measurement|time.?lapse)'; "
    r"'(cells|cell) (that |which )?detached (was|were) (excluded|discarded|removed|not)'; "
    r"'cells detached from the (gel|substrate|hydrogel)'; "
    r"'(spontaneous|spontaneously) detach'; "
    r"'(remained adherent|remained attached|stayed adherent|still adherent)'"
    " + paperclip search -s pmc,biorxiv 'traction force microscopy polyacrylamide "
    "bead displacement strain energy cell detachment during time-lapse acquisition' "
    "and 'traction force microscopy protocol troubleshooting cells do not adhere "
    "detach from polyacrylamide gel step-by-step'"
    " + NCBI esearch db=pmc: '\"traction force microscopy\" AND \"detachment rate per "
    "hour\"' (0 hits), '\"traction force microscopy\" AND \"fraction of cells that "
    "detached\"' (1 hit, an applied-shear assay), '\"traction force microscopy\" AND "
    "\"probability of detachment\"' (1 hit), '\"traction force microscopy\" AND "
    "\"cells that detached\"' (6), '\"traction force microscopy\" AND \"remained "
    "adherent\"' (6), '\"traction force microscopy\" AND \"detachment rate\"' (17) "
    "- all non-zero lists opened and read"
    " + full text of Teo 2020 (PMC7580222), Mustapha 2022 (PMC8808286) and Zancla "
    "2022 (PMC9092999) troubleshooting and limitations sections read end to end"
)

COUPLING_QUERY = (
    "paperclip grep -i over /papers/ (full-text corpus): "
    r"'detach.{0,60}(correlat|associat|proportional|scale[sd]?) (with|to).{0,60}"
    r"(traction|contractil|force)'; "
    r"'(traction|contractil).{0,60}(correlat|associat|predict).{0,60}detach'; "
    r"'(cells|those cells) (with|exerting|generating) (the )?(highest|higher|"
    r"greatest|larger) (traction|forces|contractil)'"
    " + paperclip search -s pmc,biorxiv 'cells generating the highest traction "
    "forces detach from the substrate spontaneously force-induced adhesion failure "
    "fibroblast' and 'correlation between single-cell traction force and adhesion "
    "strength detachment probability same cells'"
    " + NCBI esearch db=pmc: '(\"traction force\") AND (\"detached\") AND (\"higher "
    "traction\")' (81 hits, top 20 screened), '\"cells that detached\" AND "
    "\"traction\" AND \"excluded\"' (3 hits, all read)"
    " + full text of Yang 2025 (PMC12491448) and Paddillaya 2021 (bioRxiv "
    "2021.12.30.474608) read end to end for any per-cell stratification"
)

FIELD_QUERY = (
    "paperclip grep -i over /papers/ (full-text corpus): "
    r"'(fields of view|FOVs|images) were (excluded|discarded|rejected|removed)'; "
    r"'(excluded|discarded|rejected) (from (the )?analysis )?(due to|because of|"
    r"owing to) (excessive |significant )?(drift|focus|defocus)'; "
    r"'(cells were analyzed|cells analysed|out of) .{0,40}(cells|of the cells) "
    r"(imaged|recorded|seeded|analyzed)'"
    " + NCBI esearch db=pmc: '\"traction force microscopy\" AND \"fields of view "
    "were excluded\"' (0 hits), '\"traction force microscopy\" AND \"images were "
    "discarded\"' (1 hit, and it discards cells at image borders for segmentation "
    "reasons, not fields)"
    " + the three TFM protocol chapters above, read for any per-field loss figure"
)

# --- traction_force --------------------------------------------------------

REPORT = CalibrationReport(
    key="traction_force",
    found=(
        Evidence(
            constant="baseline_strain_energy",
            value=0.3555,
            units="pJ",
            source=XING_2022,
            quote=(
                "By aggregating the strains of each cell, we found that DB "
                "fibroblasts exerted significantly less strain energy (0.1986 +/- "
                "0.08698 pJ) compared to WT (0.3555 +/- 0.2907 pJ)."
            ),
            note=(
                "The WT arm - primary murine dermal fibroblasts, not the diabetic "
                "comparator - on a 12 kPa collagen-I-coupled polyacrylamide gel, "
                "which is the scaffold's substrate and roughly its stiffness. Unit "
                "is the cell: 'n animals = 3 per genotype, n cells >= 20 per "
                "animal'. "
                "Do not read this as a protocol-wide constant. Fibroblast strain "
                "energies in this sweep span 0.132 pJ on a 2 kPa micropatterned PDMS "
                f"substrate ({GHAGRE_2020}) and 0.19 +/- 0.12 pJ for HMF3s on a ~14.5 "
                f"kPa elastic PA gel ({PADDILLAYA_2025}), and the same HMF3s drop to "
                "0.01 +/- 0.01 pJ on a viscoelastic gel of matched storage modulus. "
                "Non-fibroblast values in the corpus run four orders of magnitude "
                "wider, from 0.000448 pJ for growth cones to 63 pJ on mixed "
                "collagen/fibronectin. Strain energy scales with spread area and "
                "substrate modulus, so this number is the reference point for a "
                "fibroblast on a ~12-15 kPa compliant gel and nothing more. "
                "Note also what the same methods section does immediately before "
                "measuring it: 'Primary fibroblasts were plated onto the gel, washed "
                "after 4 h to remove unbound cells, and imaged immediately.' The "
                "figure is conditioned on surviving that wash, and the wash has no "
                "denominator - see p_detach_baseline_per_h."
            ),
        ),
        Evidence(
            constant="measurement_cv",
            value=0.818,
            units="fraction",
            source=XING_2022,
            quote=(
                "By aggregating the strains of each cell, we found that DB "
                "fibroblasts exerted significantly less strain energy (0.1986 +/- "
                "0.08698 pJ) compared to WT (0.3555 +/- 0.2907 pJ)."
            ),
            derived=True,
            assumption=(
                "0.2907 / 0.3555 = 0.818. The paper never prints a CV; this is the "
                "quotient of the two numbers in the sentence above. Two things have "
                "to be assumed to read it as one. First, that the '+/-' is an SD: "
                "the paper's statistics section says 'Error bars represent standard "
                "deviation (SD) unless stated otherwise', which is a statement about "
                "figures rather than about in-text values, and the in-text values "
                "match the figure quantities. Second, that the spread is across "
                "cells rather than across animals - the caption gives 'n animals = 3 "
                "per genotype, n cells >= 20 per animal', so the SD is over roughly "
                "60 cells pooled from three animals and therefore carries "
                "animal-to-animal variance inside it. That makes 0.818 an upper "
                "bound on the within-animal cell-to-cell CV."
            ),
            note=(
                "This is a biological-plus-technical CV, which is the right quantity "
                "for a per-cell readout, but it is not a protocol constant and the "
                "same paper proves it: the identical calculation on the other two "
                "arms gives 0.438 (DB, 0.08698/0.1986) and 0.613 (DKO, "
                f"0.2343/0.3822). An independent paper ({PADDILLAYA_2025}) gives "
                "0.632 for HMF3s on elastic PA (0.12/0.19) and 1.0 on viscoelastic. "
                "So the honest reading is a range of roughly 0.44-0.82 with the "
                "high end here, not a point at 0.818; sweep it. "
                "For scale, the one place in this sweep where the words 'coefficient "
                f"of variation' are attached to a contractility readout at all is "
                f"Mark 2020 ({MARK_2020}), which reports '52% variability between "
                "individual tumoroids' - a between-unit spread of the same order for "
                "spheroids in 3D collagen. That paper also writes the formula "
                "backwards, as '(coefficient of variation, mean/st.dev.)', in three "
                "separate captions."
            ),
        ),
    ),
    blocked=(
        Blocked(
            constant="tgfb_fold_change",
            reason=BlockedReason.CONTEXT_DEPENDENT,
            detail=(
                "Ill-posed as a scalar, and this pass upgrades that from an "
                "assertion to a measurement. The previous entry rested on "
                f"Marinkovic 2012 ({MARINKOVIC_2012}), whose abstract states that "
                "'exogenous TGF-beta1 selectively accentuates tractions on stiff "
                "matrices, mimicking fibrotic lung, but not on physiological "
                "stiffness matrices, despite equivalent changes in Smad2/3 "
                "activation' - verified verbatim via NCBI, though that paper's full "
                "text is unavailable on both instruments, so the abstract is all "
                "there is. "
                f"D'Urso 2025 ({DURSO_2025}) now supplies the numbers, and they do "
                "not merely attenuate with stiffness, they change sign: "
                "'TGF-beta-induced cells on the soft gels exerted higher traction "
                "forces (121.2 +/- 58.1 Pa) compared to the control (p < 0.0001), as "
                "expected. However, fibroblasts cultured with TGF-beta on stiff gels "
                "showed slightly lower mean traction forces levels (245.9 +/- 103.6 "
                "Pa) than the control (p = 0.036).' Against controls of 101.3 +/- "
                "51.6 Pa (soft) and 270.5 +/- 168.6 Pa (stiff) that is 1.20x on soft "
                "and 0.91x on stiff. A single fold change would have to average a "
                "rise and a fall. "
                "Two further reasons not to collapse it. The quantity is traction "
                "stress in Pa, not strain energy in pJ, and the conversion needs the "
                "displacement field and spread area, which are not published "
                "alongside. And the paper contradicts itself on the stiff arm: the "
                "results section says TGF-beta gave 'slightly lower mean traction "
                "forces levels' while the discussion two paragraphs later says the "
                "same treatment 'leads to slightly increased cell traction forces and "
                "FA elongation'. The measured direction of a 9% effect is not stable "
                "within one manuscript. "
                "Sweep this as a response surface over substrate modulus. That is a "
                "finding about the model, not a gap in the corpus."
            ),
        ),
        Blocked(
            constant="p_detach_baseline_per_h",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "The failure is named repeatedly and counted never. Teo 2020 "
                f"({TEO_2020}) lists it as a numbered troubleshooting entry - "
                "'Problem 5' is, in full, 'Cells are dying.' - and answers it with "
                "phototoxicity and fibronectin-coating advice and no frequency. "
                f"Mustapha 2022 ({MUSTAPHA_2022}) states the acceptance criterion "
                "instead of the rate: 'A successful run should have cells "
                "interacting with the substrate at the end of the experiment', which "
                "concedes that unsuccessful runs exist and stops there. Zancla 2022 "
                f"({ZANCLA_2022}), the field's primer, treats every source of error "
                "in TFM except cell attrition. "
                "The exclusion is also built into working protocols and left "
                f"unquantified there. Xing 2022 ({XING_2022}) - the source of both "
                "constants recovered above - reads 'Primary fibroblasts were plated "
                "onto the gel, washed after 4 h to remove unbound cells, and imaged "
                "immediately.' Cells that lost their grip in the first four hours are "
                "removed by design, and neither the numerator nor the denominator is "
                "given. "
                f"The near-miss: Yang 2025 ({YANG_2025}) has a methods subsection "
                "headed 'Measuring probability of cell detachment of hMSC', with a "
                "real procedure - 'Cells were imaged every 10 minutes over a 24-hour "
                "period to monitor detachment events' - so the quantity is "
                "constructible and has been constructed. It is not this constant: "
                "hMSCs rather than fibroblasts, a photo-responsive hydrogel being "
                "cycled between 2.2 and 1.6 kPa every minute rather than a static "
                "gel, a cumulative 24 h probability rather than a per-hour hazard, "
                "and the value in Fig. 3g rather than in the text. The only textual "
                "statement of the result is comparative and unnumbered: 'cells on "
                "dynamic soft substrates exhibited a higher detachment rate over 24 "
                "hours compared to those on static substrates'. "
                "Confirmed absent on both instruments: NCBI returns zero PMC records "
                "for '\"traction force microscopy\" AND \"detachment rate per hour\"', "
                "and the one hit for '\"fraction of cells that detached\"' is a "
                "parallel-plate flow chamber applying 170 dyn/cm2, which is an "
                "adhesion-strength assay and not spontaneous loss."
            ),
            searched=DETACH_QUERY,
        ),
        Blocked(
            constant="detach_force_coupling",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "Nobody stratifies detachment by the detaching cell's own traction. "
                "But the absence is not clean, and the residue points the wrong way "
                "for this scaffold, so both halves are recorded. "
                "The mechanism half is stronger here than in any other protocol in "
                f"this project. Yang 2025 ({YANG_2025}) attributes detachment to "
                "cell-generated contractility rather than to a processing variable: "
                "'The timing of \"snap-back\" events, which are triggered when "
                "intracellular contractile forces (pMyosin IIa) exceed extracellular "
                "adhesion forces, varies significantly between individual cells'. A "
                "force balance, named as the trigger, with between-cell variation in "
                "when it fires. That is exactly the shape this scaffold assumes, and "
                "it is worth being precise about how much of the shape it supplies. "
                "It is not an estimate of the coupling. Contractility is indexed by "
                "pMyosin IIa immunofluorescence, not by measured traction. The "
                "contrast is between substrate conditions, not between cells within "
                "one condition. The imbalance is driven by an imposed rigidity cycle, "
                "so the driver is a parameter the experimenter sets rather than the "
                "readout - the same distinction that keeps fibrosis_on_chip out of "
                "the coupled class. And no coefficient is fitted. "
                f"The measurement half runs the other way. Paddillaya 2021 "
                f"({PADDILLAYA_2021}) puts both ingredients in one paper on the same "
                "six cell lines - critical de-adhesion shear stress from a fluid "
                "shear device, and single-cell tractions by Reg-FTTC - and reports "
                "them as two independent markers rather than as a coupling. What "
                "emerges across the lines is that the hardest-pulling cells are the "
                "hardest to remove: 'Fibroblasts (NIH3T3) had the highest values of "
                "tau-10 (3.83 +/- 0.32 Pa)', and 'Normal cells, however, exert higher "
                "tractions than invasive and non-invasive cells and have prominent "
                "stress fibers.' "
                "State what that does and does not license. It is a "
                "between-cell-line association measured under applied shear, so it "
                "does not refute a within-population coupling between a cell's own "
                "steady traction and its spontaneous detachment hazard under no "
                "applied load; those are different quantities and the paper claims "
                "nothing about the second. It is, though, the nearest evidence the "
                "corpus has, and it does not support the assumed sign. "
                f"One further pointer, recorded with its limits: Feng 2018 "
                f"({FENG_2018}) combines traction measurement with a detachment "
                "challenge in the same cells, but the paper is not open access on "
                "Europe PMC and is absent from Paperclip's index, so only the "
                "abstract could be read. An abstract is not a basis for a claim about "
                "what a paper reports, and it is cited here only to mark where "
                "somebody with access should look next."
            ),
            searched=COUPLING_QUERY,
        ),
        Blocked(
            constant="p_field_unusable",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "Every mechanism in the scaffold's own description - drift, focus "
                "loss, bead washout - is documented in the protocol literature as a "
                "named failure, and not one of them carries a frequency. "
                f"Mustapha 2022 ({MUSTAPHA_2022}) is explicit about the outcome and "
                "silent about the rate: bead-laden gels crack, and when they do, 'the "
                "beads will accumulate in the cracks, perturbing the otherwise "
                "uniform dispersion of the beads in the surrounding regions and "
                "rendering the gel unusable'. Its numbered problems cover "
                "non-polymerising gels, cracked gels and bad PIV parameters; its data "
                "analysis section opens on drift as the first of four processing "
                "steps and separates it into z drift and lateral drift. Teo 2020 "
                f"({TEO_2020}) supplies the other two: 'Problem 1 / Beads in "
                "different areas are not in focus' and 'Problem 4 / Beads are clumped "
                "up', each with a mitigation and no denominator. "
                "The rate is not reported anywhere, in any form: not as a fraction of "
                "fields, not as a count, not as a number of movies started versus "
                "finished. Nor is the softer version - how many cells entered the "
                "analysis out of how many were imaged - which several other "
                "single-cell imaging fields do print. "
                "Confirmed absent on both instruments. NCBI returns zero PMC records "
                "for '\"traction force microscopy\" AND \"fields of view were "
                "excluded\"', and the single hit for '\"images were discarded\"' "
                "discards cells at image borders to avoid segmentation error, which "
                "is a different failure. This is the one entry in this module resting "
                "mostly on absence rather than on a near-miss, and it should be read "
                "accordingly: it is a well-searched null, not a documented refusal."
            ),
            searched=FIELD_QUERY,
        ),
    ),
)
