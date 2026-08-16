"""Calibration findings for `stiffness_drift`, swept 2026-08-16.

INSTRUMENT
----------
Paperclip full-text corpus (`paperclip grep` over /papers/, `paperclip search
-s pmc,biorxiv`) was primary, per PLAN 6.2. NCBI E-utilities (`esearch`/
`efetch` against db=pmc) and Europe PMC's REST search were run as a second
instrument, and they earned their keep here: four of the six documents this
module leans on are not in Paperclip's index at all - Norman 2021 (Nat Protoc,
PMC7615740), Cresens 2026 (STAR Protoc, PMC13273567), Scott 2020 (Adv Healthc
Mater, PMC7274877) and Scholp 2024 (J Orthop Res, PMC11615420). Two of those
four are protocol chapters, which is the same gap the `cell_derived_matrix`
sweep hit. Every quote below was checked against the full text of the source it
is attributed to, on the instrument named beside it; nothing here comes from a
search snippet.

Europe PMC was used for phrase search specifically because PMC's own full-text
index silently degrades a long quoted phrase into an AND of its terms - the
phrase "stiffness did not change over the course of the experiment" returns
470,689 PMC records and 0 Europe PMC records, and only the second number means
anything. Where a NOT_REPORTED claim below rests on a phrase search, it rests
on Europe PMC.

QUERIES RUN
-----------
Corpus-wide `paperclip grep -i` over /papers/ (regex, full texts):

    (elastic|Young.s|storage) modul[a-z]+ .{0,60}(remained|was) (stable|unchanged) .{0,40}(over|for|during) .{0,20}(days|day|week)
    modul[a-z]+ (was|were) (re-?)?measured (at|on) (day|the endpoint|both)
    (stiffness|modulus) (of the (gels|substrates|hydrogels) )?(was|were) (also )?(re-?)?(measured|assessed|verified|checked) (again )?(at|after) (the )?(end of|endpoint|day 7|day 14|7 days|14 days|the culture)
    (stiffness|modulus) (drift|drifted|drifts)
    no (significant |detectable )?change in (the )?(elastic|Young.s|shear|storage) modulus (over|after|during|throughout)
    polyacrylamide.{0,100}(stiffness|modulus).{0,60}(stable|unchanged|did not change)
    polyacrylamide .{0,80}(stiffness|modulus) .{0,60}(over|during|throughout) .{0,30}(culture|days|day period|week)
    polyacrylamide.{0,120}(swell|degrad)
    (gels|substrates|hydrogels) (were|remained|are) (mechanically )?stable (over|for|throughout|during) (the )?[0-9a-z ]{0,25}(days|weeks|culture)
    gels (were|are) (used|discarded) (within|after) [0-9]{1,2} (days|day|weeks)
    coefficient of variation.{0,120}(SMA|myofibroblast)
    (well-to-well|field-to-field|inter-?well|intra-?assay) (variability|variation|CV).{0,140}(SMA|myofibroblast|fibroblast activation)
    (threshold|switch|transition) (stiffness|modulus).{0,80}(myofibroblast|SMA|activation)
    (.-SMA|alpha-?SMA)[- ]positive .{0,30}(cells|fraction|percentage).{0,120}(kPa)

plus Europe PMC phrase searches (hit counts as returned):

    "stiffness of the gels did not change"                                (1, false positive)
    "gel stiffness did not change"                                        (1, unrelated)
    "modulus did not change over" AND polyacrylamide                      (0)
    "gels were measured before and after"                                 (5, none a hydrogel substrate)
    "at the beginning and at the end of the culture" AND stiffness        (3, none a hydrogel substrate)
    "stiffness" AND "before and after culture" AND hydrogel               (15, none a modulus time course)
    "coefficient of variation" AND "percentage of alpha-SMA positive cells" (2)
    "Z prime" AND "alpha-SMA" AND "fibroblast" AND "assay"                (0)
    "per kPa" AND "alpha-SMA"                                             (1, unrelated)
    "increase in alpha-SMA" AND "per kPa"                                 (0)
    "Hill function" AND "substrate stiffness" AND "myofibroblast"         (2, both models not data)

plus nine `paperclip search -s pmc,biorxiv` semantic queries on substrate
modulus stability, endpoint rheology, PA gel softening in culture, and
stiffness-dependent myofibroblast dose-response. Roughly 250 titles were
screened; twelve papers were read in full text.

THE SHAPE OF THIS SCAFFOLD IS THE OPPOSITE OF EVERY OTHER ONE
--------------------------------------------------------------
Every protocol swept so far has recovered its effect-size and precision
constants and lost its failure constants. This one inverts. The two hazard
constants - does the modulus move, and does the movement depend on where you
set it - both came back with a real longitudinal measurement behind them. The
two readout constants did not: the dose-response is not published as a slope
and the field-to-field CV of an aSMA-positive fraction is not published at all.

That inversion is not a reprieve for the project's thesis. It is a different
and sharper version of it, because of *which* papers carry the drift numbers.

WHERE THE REPORTING BOUNDARY ACTUALLY FALLS
-------------------------------------------
The boundary is not between "measured" and "not measured". It is between
papers where drift is the experimental variable and papers where drift is a
nuisance. A modulus time course gets published if and only if the drift is the
point of the paper.

On the nuisance side, nominal stiffness is a property set once and never
revisited, and the corpus says so in its own words:

  - Shi & Janmey 2023 open their PA methods paper by listing, as an intrinsic
    property of the material, "resistance to degradation, providing stable
    mechanical properties over time". No measurement, no citation on that
    clause. Two sentences later the same paragraph concedes that the gel may
    swell in culture medium - as a handling problem, not a mechanical one.
  - Young & Engler 2014 describe PA gels of "1, 11, and 34 kPa whose stiffness
    did not change with time and were thus 'static.'" In the same sentence
    they give the *measured* time constants of their HA gels (tau = 69.9 hr),
    because the HA gels are the ones that are supposed to move. The static arm
    is asserted; the dynamic arm is characterised.
  - Cresens 2026, the current STAR Protocols recipe, makes the one-shot
    measurement canonical: rheology "after swelling for 16 h to guarantee that
    the gels have reached the swelling equilibrium". The protocol contains no
    step that revisits stiffness after cells are on it, and no note that one
    might want to.
  - Norman 2021, the Nature Protocols AFM chapter, names every ingredient of
    the hazard - swelling, protein stability, cell growth, degradation - in a
    single PAUSE POINT paragraph, and attaches no rate to any of them.
  - At least three independent methods papers state a shelf life ("All gels
    were used within 2 days of polymerization") without ever saying what
    happens on day 3. A shelf life is an admission that the number moves; it
    is not a measurement of how fast.

On the other side of the boundary, the drift is measured weekly and reported
to two significant figures - Scott 2020, Arral 2026, Young & Engler 2011 via
Young & Engler 2014, Nason-Tomaszewski 2023. Every one of those papers is
*about* time-varying mechanics. Arral 2026 states the boundary from the inside:
"most in vitro models present static mechanical environments ... failing to
capture the progressive, time-dependent stiffening".

So the honest read is that the field has professionalised the day-zero problem
and left the day-fourteen problem alone. Swelling-induced softening is handled,
thoroughly, by a 16-24 h equilibration step whose whole purpose is to make the
nominal value correct *at the start*. What no protocol asks is whether it is
still correct at the end.

THE REAL NEGATIVE RESULT, STATED PLAINLY
-----------------------------------------
Scott 2020 is a genuine counterexample to the strong form of the project's
hypothesis on this scaffold, and it should not be softened. They measured the
bulk shear storage modulus of PEG hydrogels once per week for 42 days, in three
formulations, with cells and without, and with a control for whether the
repeated measurement itself damaged the gel ("No differences in the final
storage moduli were observed between hydrogels that endured repeated
measurements ... and those that were measured only once after 42 days"). That
is a better-designed drift experiment than the twin needs. It exists. It is
findable. `modulus_drift_pct_per_day` and `drift_depends_on_nominal` are both
answered from it.

Three things keep it from closing the question:

1. It is 3D encapsulation in an MMP-degradable PEG network, not cells on top of
   a 2D gel of the kind `REGISTRY["stiffness_drift"]` describes. The registry's
   summary does name PEG, so the material is in scope; the geometry and the
   deliberate proteolytic lability are not.
2. The drift it reports is cell-driven, which contradicts the registry's own
   declaration for this protocol. `HazardSpec.driver` reads "time in culture,
   medium composition" and `driver_is_the_measured_phenotype=False`. Scott 2020
   says the opposite: "These changes depended on the presence of encapsulated
   cells and did not occur in acellular hydrogels", and the arm that stiffens
   is the arm where the cells transdifferentiate. If that transfers, this
   scaffold belongs in the coupled class, not the independent one, and the
   survivorship argument applies to it after all. Flagged rather than acted on,
   because one paper in a different geometry is not enough to re-declare a
   protocol.
3. The paper contradicts itself on the acellular arm. Section 2 says of the
   acellular gels that "Decreases in shear storage moduli were observed for all
   hydrogels over time, indicative of a decrease in hydrogel crosslink density
   likely due to endogenous enzymes present in the serum or retro-Michael
   addition reactions"; section 4 says the changes "did not occur in acellular
   hydrogels". Both sentences are in the paper. The cell-free drift rate - the
   one this scaffold as declared actually needs - is therefore not established
   even by the paper that measured it.

Nothing at all was found for the 2D polyacrylamide arm. Not a rate, not a
bound, not a null result. PA is the most-used substrate in the field and its
temporal stability rests on an assertion in an introduction.

THE UNITS TRAP, AND WHERE IT DOES AND DOES NOT BITE
----------------------------------------------------
Rheology papers report shear storage modulus G' and cell-biology papers report
Young's modulus E; the bridge is E = 2G'(1 + v), which needs an assumed
Poisson's ratio. Cresens 2026 writes the assumption down explicitly - "E ~ G' *
2 * (1 + v) -> E ~ G' * 3 Where v is Poisson's ratio ... assumed to be 0.5 for
PAAm gels" - and then warns that the result "may differ from values obtained by
direct compression or indentation-based methods such as AFM".

The trap does not bite `modulus_drift_pct_per_day`, and it is worth saying why
rather than just asserting it: a *fractional* change per day is dimensionless,
so if v is constant over the culture the factor of 2(1 + v) cancels top and
bottom and the percentage is the same whether it is computed on G' or on E.
That "if" is doing real work. A network losing crosslinks is not obliged to
hold its Poisson ratio fixed, nobody measured v at day 42, and the cancellation
is an assumption rather than an identity. It is recorded as one.

It does bite anything that needs an absolute modulus on the cell-biology scale,
which is why the `stiffness_response_curve` entry below is blocked rather than
derived from Scott's two-point spread: converting 1.42 and 2.90 kPa of G' into
4.3 and 8.7 kPa of E and reading a slope off them would produce a number that
looks like a measurement and is mostly a Poisson ratio.

WHAT WAS NOT FOUND, AND WHAT THAT DOES NOT LICENSE
---------------------------------------------------
No paper in this sweep reported the modulus of a nominally static 2D substrate
at the end of a cell culture. That is a statement about what was searched for
on two instruments, not a proof of absence: figure panels were not extracted,
supplementary characterisation files were not opened, and both are exactly
where such a measurement would hide if it were made in passing. The
NOT_REPORTED below is claimed only for the one constant where the phrase
searches were exhaustive enough to support it.
"""

from __future__ import annotations

from ..evidence import Blocked, BlockedReason, CalibrationReport, Evidence

# --- sources ---------------------------------------------------------------

SCOTT_2020 = "10.1002/adhm.201901593"        # Adv Healthc Mater, 42-day weekly rheology
NORMAN_2021 = "10.1038/s41596-021-00495-4"   # Nat Protoc, AFM on soft surfaces and gels
CRESENS_2026 = "10.1016/j.xpro.2026.104606"  # STAR Protoc, PAAm synthesis + rheology
SHI_2023 = "10.1101/2023.01.27.525967"       # bioRxiv, Janmey lab large PAAm gels
YOUNG_2014 = "10.1038/srep06425"             # Sci Rep, 'static' PA vs 'dynamic' HA
ARRAL_2026 = "10.64898/2026.06.01.729382"    # bioRxiv, stiffening silk gels + NHLF
NASON_TOMASZEWSKI_2023 = "10.1016/j.bioactmat.2023.10.001"  # Bioact Mater, PEG day 0 vs 18
MARURI_2022 = "10.3389/fcell.2022.886759"    # Front Cell Dev Biol, keratocytes on PA
NELSON_2023 = "10.1101/2023.03.01.530599"    # bioRxiv, high-content cardiac fibroblasts
SCHOLP_2024 = "10.1002/jor.25967"             # J Orthop Res, rat elbow arthrofibrosis
TAN_2017 = "10.1186/s41038-017-0080-1"       # Burns Trauma, review restating the threshold

# The queries actually run, kept beside the null results they produced. A
# NOT_REPORTED claim is only as good as the search behind it, and these are
# transcribed from the shell rather than reconstructed afterwards.

CV_QUERY = (
    "paperclip grep -i over /papers/ (full-text corpus): "
    r"'coefficient of variation.{0,120}(SMA|myofibroblast)'; "
    r"'(well-to-well|field-to-field|inter-?well|intra-?assay) (variability|variation|CV)"
    r".{0,140}(SMA|myofibroblast|fibroblast activation)'"
    " + Europe PMC phrase search: "
    '\'"coefficient of variation" AND "percentage of alpha-SMA positive cells"\' (2 hits, '
    "both between-animal); "
    '\'"Z prime" AND "alpha-SMA" AND "fibroblast" AND "assay"\' (0 hits); '
    '\'"CV" AND "alpha-SMA positive" AND "wells" AND "high content"\' (8 hits, all '
    "conference abstract books); "
    '\'"Z-factor" AND "alpha-SMA" AND "myofibroblast"\' (12 hits, full text of the one '
    "phenotypic-screening paper among them, PMC11865240, read - it reports RZ' only as "
    "'above 0.5' and gives no CV)"
)

# --- stiffness_drift -------------------------------------------------------

REPORT = CalibrationReport(
    key="stiffness_drift",
    found=(
        Evidence(
            constant="modulus_drift_pct_per_day",
            value=1.85,
            units="% per day",
            source=SCOTT_2020,
            quote=(
                "Initial equilibrium shear storage moduli for the substrates examined "
                "were 0.33, 1.42, and 2.90 kPa; after 42 days of culture, all hydrogels "
                "exhibited similar storage moduli (0.3-0.7 kPa) regardless of initial "
                "modulus, with encapsulated AoAFs spreading and proliferating."
            ),
            derived=True,
            assumption=(
                "Computed for the stiffest arm only (10 wt%, the one that softens "
                "monotonically), whose endpoint the paper states separately as 'a final "
                "bulk storage modulus and calculated mesh size of 0.7 kPa and 10.3 nm, "
                "respectively, after 42 days'. Loss = (2.90 - 0.70)/2.90 = 75.9% over "
                "the 41 days between the 24 h equilibrium measurement and the day-42 "
                "endpoint, i.e. 1.85% of the initial modulus per day if drift is linear "
                "in time. A first-order decay fitted to the same two points gives 3.41% "
                "per day, so the constant is uncertain to a factor of ~1.8 on the choice "
                "of drift model alone and should be swept, not used as a point value. "
                "The figure is a fraction, so the G'-to-E conversion cancels - but only "
                "if Poisson's ratio is constant through 42 days of network degradation, "
                "which nobody measured."
            ),
            note=(
                "This is the PEG arm of the scaffold, and it is not transferable to the "
                "polyacrylamide arm. The gel is a Michael-addition PEG network built "
                "with MMP-cleavable crosslinks, i.e. engineered to be degraded by the "
                "cells inside it; polyacrylamide has neither hydrolysable nor "
                "protease-cleavable bonds in its backbone. Treat 1.85% per day as an "
                "upper bound set by a deliberately labile material, not as the rate a "
                "PA gel drifts at. "
                "Two further caveats. The measurement is 3D encapsulation, not cells on "
                "top of a 2D gel. And the paper attributes the drift to the cells - "
                "'These changes depended on the presence of encapsulated cells and did "
                "not occur in acellular hydrogels' - the finding this project's own "
                "registry now declares as the hazard's driver (owner call, 2026-08-16, "
                "see tier1.py's STIFFNESS_DRIFT.hazard), though the same paper "
                "complicates a clean version of that claim by reporting elsewhere that "
                "acellular gels also softened 'likely due to endogenous enzymes present "
                "in the serum or retro-Michael addition reactions'. So cell presence "
                "changes the drift, but does not fully explain it - the cell-free rate "
                "is nonzero, just apparently smaller. "
                "One independent PEG datapoint agrees on the order of magnitude and was "
                f"obtained the crude way. Nason-Tomaszewski 2023 "
                f"({NASON_TOMASZEWSKI_2023}) reports that 'To assess degradation the bulk "
                "elastic modulus was measured on days 0 and 18 showing that hydrogels "
                "soften from about 13.6 kPa with 95% CI [9.6 kPa, 16.1 kPa] to 1.9 kPa "
                "with 95% CI [1.5 kPa, 2.7 kPa] during culture' - 86% over 18 days, 4.8% "
                "per day linear. Same caveat: degradable PEG, 3D, and the softening is "
                "the intended behaviour. Note also that this is a two-point measurement "
                "with no intermediate timepoints, so it cannot distinguish the linear from "
                "the exponential model the way Scott's weekly series can. "
                f"For 2D, Arral 2026 ({ARRAL_2026}) is the closest thing: normal human "
                "lung fibroblasts on top of tyramine-modified silk gels, compressive "
                "modulus at days 2, 7 and 14, 'reaching 14.3 kPa at day 7 and 32.1 kPa "
                "by day 14' from 13.5 kPa at day 2 - a 2.4-fold *increase* over 12 days, "
                "about 11% per day. Different material, opposite sign, and stiffening by "
                "design, so it corroborates the magnitude class and nothing more. "
                "For polyacrylamide itself there is nothing to convert, bound or "
                "corroborate. The three most-cited PA methods documents in this sweep all "
                f"stop short of a measurement: Shi & Janmey 2023 ({SHI_2023}) assert "
                "'resistance to degradation, providing stable mechanical properties over "
                f"time' as a material property in an introduction; Young & Engler 2014 "
                f"({YOUNG_2014}) describe PA gels as being 'of 1, 11, and 34 kPa whose "
                "stiffness did not change with time and were thus static', in the same "
                "sentence that gives a measured time constant for the hyaluronic-acid "
                "gels they did characterise (the original reads \"thus 'static.'\", with "
                "the authors' own scare quotes); and Norman 2021 "
                f"({NORMAN_2021}), the Nature Protocols "
                "AFM chapter, names the whole hazard without a rate - 'Many hydrogels "
                "swell when placed in aqueous solutions after gelation. It's often "
                "advisable to wait until they are fully swollen to make measurements "
                "(often 24-48 h). For protein-based hydrogels, long-term stability will "
                "depend on protein stability. The stability of cell-laden hydrogels will "
                "additionally depend on the growth of the cells and the susceptibility of "
                "the hydrogel to degradation.' That last passage is the boundary in one "
                "paragraph: every term of the drift model is named and none is quantified."
            ),
        ),
        Evidence(
            constant="drift_depends_on_nominal",
            value=1.0,
            units="-",
            source=SCOTT_2020,
            quote=(
                "Cell-mediated reductions in stiffness were observed for all hydrogels "
                "over the first 7 days of culture, but thereafter, changes were dependent "
                "on the initial shear storage modulus. Specifically, the modulus of 10wt% "
                "hydrogels decreased throughout the duration of the study; whereas, shear "
                "storage moduli stabilized after 7 days in 7.5wt% hydrogels, and 5wt% "
                "hydrogels were observed to stiffen after 7 days."
            ),
            note=(
                "1.0 encodes 'yes, the drift depends on the nominal value'. Read straight "
                "off the sentence above, not computed. "
                "But the registry's gloss for this constant - 'whether soft gels drift "
                "faster' - is not what the source supports, and the difference matters "
                "for how the engine should use it. The dependence Scott 2020 measured is "
                "in SIGN, not in magnitude: the stiffest arm softens throughout, the "
                "middle arm plateaus, the softest arm reverses and stiffens after day 7. "
                "All three converge on 0.3-0.7 kPa by day 42 regardless of where they "
                "started, which is a collapse of the independent variable rather than a "
                "proportional drift on it. A model that implements this as 'soft gels "
                "drift faster' will get the soft arm's direction wrong. "
                "The measurement is 3D MMP-degradable PEG; whether a 2D PA range behaves "
                "this way is unknown. The one nearby statement about PA, from the current "
                f"STAR Protocols recipe (Cresens 2026, {CRESENS_2026}), says the "
                "dependence exists but reports it in the wrong quantity - 'Gels of "
                "varying stiffnesses swell differently depending on their stiffness, up "
                "to 130% in diameter for the gels produced here' - and the same protocol "
                "supplies the missing half of the link, that 'swelling leads to softening "
                "(decreased stiffness)'. Diameter is not modulus, so that pair is "
                "suggestive and not a measurement; see the note on units above."
            ),
        ),
    ),
    blocked=(
        Blocked(
            constant="stiffness_response_curve",
            reason=BlockedReason.CONTEXT_DEPENDENT,
            detail=(
                "Ill-posed as a scalar slope in fraction per kPa, for three reasons, and "
                "none of them is a gap in the corpus. "
                "First, the field parameterises this as a threshold, not a gradient. The "
                f"canonical statement, restated in reviews as settled ({TAN_2017}: 'In "
                "contractile wound granulation tissue and myofibroblasts cultured on "
                "elastic substrates, the threshold stiffness for the expression of a-SMA "
                "in stress fibers is approximately 20 kPa'), is a switch point in kPa. A "
                "threshold and a slope are different objects and the conversion between "
                "them needs the shape of the curve, which is not published. "
                "Second, the response is hysteretic, so it is not a function of the "
                f"current modulus at all. Scott 2020 ({SCOTT_2020}) found that after 42 "
                "days, by which time all three arms had converged to 0.3-0.7 kPa, "
                "'~20% of AoAFs in 7.5wt% hydrogels and ~45% of AoAFs in 10wt% hydrogels "
                "expressed diffuse aSMA staining after 42 days in culture, similar to day "
                "1', and that 'the percentage of aSMA + AoAFs did not correlate with bulk "
                "shear moduli in 7.5wt% and 10wt% hydrogels'. The fraction tracked the "
                "modulus the cells first saw, not the one they were sitting on. That is "
                "mechanical memory, and it is the reason this scaffold is worth building "
                "- but it also means a single-valued response curve cannot be right. "
                "Third, where a clean 2D dose-response does exist it is not in any text, "
                f"table or caption read in this sweep. Maruri 2022 ({MARURI_2022}) "
                "cultures corneal keratocytes on 1 kPa and 10 kPa PA and on glass and "
                "reports 'Quantification of the fraction of a-SMA-positive cells' in a "
                "figure panel with n = 8 substrates from 4 replicates; the numbers are in "
                "the panel. Europe PMC phrase searches for a published gradient - "
                "'\"per kPa\" AND \"alpha-SMA\"', '\"increase in alpha-SMA\" AND \"per "
                "kPa\"' - return one unrelated hit and zero respectively. "
                "Sweep this as a thresholded response with a memory term, not as a slope. "
                "If a single number is needed to get started, the two-point spread in "
                "Scott 2020 is the only candidate in the corpus and it should be "
                "converted honestly or not at all: 0.20 to 0.45 across 1.42 to 2.90 kPa "
                "of shear storage modulus is 0.17 per kPa on G', but 0.056 per kPa once "
                "E = 3G' is applied, and the whole difference is an assumed Poisson "
                "ratio of 0.5 in a 3D degradable gel."
            ),
        ),
        Blocked(
            constant="measurement_cv",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "The corpus publishes coefficients of variation constantly - for ELISAs, "
                "for clinical chemistry, for mass spectrometry, intra- and inter-assay, "
                "to one decimal place. It does not publish one for the fraction of cells "
                "scored aSMA-positive by imaging, on any substrate, in anything read "
                "here. Two near-misses, and neither can be mapped onto this constant "
                "without inventing the mapping. "
                f"Nelson 2023 ({NELSON_2023}) is the closest in assay design - a "
                "high-content screen of human cardiac fibroblasts, well medians as "
                "replicates - and it states a number: 'The sampling range for each "
                "parameter was calculated by paramMean + CDV * paramMean where COV=0.0396. "
                "This COV value, used to scale stochasticity in the model was determined "
                "by taking the average coefficient of variation in F-actin, procollagen I, "
                "and aSMA expression in human cardiac fibroblasts treated with TGFb from "
                "our in vitro experiments.' It is unusable as measurement_cv for three "
                "independent reasons: it is an average over three features so the aSMA "
                "component cannot be recovered; it is a CV of staining *intensity*, not "
                "of a positive *fraction*, and a bounded fraction and an unbounded "
                "intensity do not share a dispersion scale; and the replicate unit is the "
                "well median over a tile, n = 3, which is neither field-to-field nor "
                "well-to-well in the sense the scaffold needs. "
                f"Scholp 2024 ({SCHOLP_2024}) does publish a CV on exactly the right "
                "quantity - 'the mean, standard deviation, coefficient of variation "
                "(standard deviation divided by mean), and 95% confidence intervals were "
                "calculated for ROM, maximum extension, connective tissue density, and "
                "the percentage of a-SMA positive cells' - and the values it reports are "
                "64% to 170%. But those are between-animal CVs in a rat elbow "
                "arthrofibrosis model, i.e. biological variation in vivo, and using them "
                "as a well-level measurement CV would overstate the noise by an order of "
                "magnitude. The number is real; it is a measurement of something else. "
                "Worth noting what this near-miss pair implies. The only two published "
                "dispersions on an aSMA readout in this sweep are 4% and 150%, they are "
                "measurements of different things, and nothing in between exists. A "
                "power calculation on this scaffold has no defensible spread to use, and "
                "the fix is a pilot rather than another search."
            ),
            searched=CV_QUERY,
        ),
    ),
)
