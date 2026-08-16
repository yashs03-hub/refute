"""Case 5 - bleomycin-induced pulmonary fibrosis (murine). The exception.

This scaffold was the standing prediction in `literature.py`: mortality should
be recoverable here, because animal welfare reporting obliges authors to
publish deaths. The prediction was right, and it is right in a more
interesting way than "the constant was found".

WHAT WAS SEARCHED
-----------------
The PubMed MCP was unavailable this session (`No claude.ai OAuth token`), so
NCBI E-utilities were queried directly for orientation and the sweep itself
ran on Paperclip's full-text index - which is the right instrument anyway, for
the reason PLAN Sec 6.1 records: these constants live in methods, figure
legends and welfare paragraphs, not abstracts.

Six semantic searches (`paperclip search -s pmc` / `-s pmc,biorxiv`) and
fourteen corpus-wide regex or boolean greps (`paperclip grep ... /papers/`)
over ~3.4M full texts. Roughly 150 titles and result snippets screened;
fourteen papers opened and grepped end to end:

    PMC11595013  Kadam & Schnitzer 2024   60-fold i.t. dose-ranging, day 14
    PMC5249201   Gilhodes 2017            4-dose i.t. study, Ashcroft by dose
    PMC6165886   Barbayianni 2018         IT vs OA route comparison
    PMC12645776  Salmaso 2025             intranasal dose optimisation, welfare
    PMC10877150  Kobayashi 2023           day-by-day Ashcroft time course
    PMC6237877   Kim KH 2018              day-14 cumulative mortality
    PMC7578219   Ferrini 2020             Ashcroft mean +/- SD, vehicle and BLM
    PMC10542701  Warheit-Niemi 2022       progressor / nonprogressor stratified
    PMC3834487   Kim SN 2010              1-4 mg/kg dose response
    PMC6107205   Heinemann 2018           CNN vs pathologist Ashcroft
    PMC11381007  Grandi 2024              mixed-mode BLM, Ashcroft +/- SD
    PMC12785816  (PHMG-p, not bleomycin - discarded)
    PMC4354010   Lawrenz 2014             intubation-mediated instillation
    PMC11088103  (mortality sentence too ambiguous to quote - discarded)

The ATS workshop report (Jenkins 2017, 10.1165/rcmb.2017-0096ST) named in
`literature.py` as the untested lead is *not in the Paperclip PMC corpus* -
`lookup doi` and `lookup pmid` both return nothing - so it remains unread, as
it was after the PubMed-only pass. Nothing below depends on it.

SECOND INSTRUMENT, AND WHAT IT CHANGED
--------------------------------------
Paperclip does not index book protocol chapters, and troubleshooting sections
are exactly where a failure rate would live, so both NOT_REPORTED claims were
re-run against NCBI E-utilities and the Europe PMC REST API before being made.

That pass found the field's four canonical bleomycin protocol chapters and
established that none of them is readable by either instrument:

    Liu, De Los Santos & Phan 2017   10.1007/978-1-4939-7113-8_2   no PMC
    O'Dwyer & Moore 2018             10.1007/978-1-4939-8570-8_24  no PMC
    Mekhael ... Ask 2021             10.1007/978-1-0716-1382-5_21  no PMC
    Zhou, Li & Zhang 2026 (JoVE)     10.3791/69131                 no PMC

`elink pubmed->pmc` returns nothing for all four; the ERJ interventional-timing
paper (10.1183/13993003.01105-2019) 403s. This is a real limit on the
p_dosing_failure claim and is stated as such below: it rests on open full text
plus two in-print statements by practitioners that the quantity is not
recorded, not on having read every protocol chapter.

What the second instrument did add is the single best item in the sweep. JoVE
2025, 10.3791/67676, a methods paper devoted to mouse intubation, describes the
exact failure mode - "compression of the trachea due to erroneous canulation of
the esophagus can obstruct breathing and increase mortality" - gives a
troubleshooting recipe for when "the endotracheal tube is entering the
esophagus repeatedly", and then says: "The number of re-attempts should be
specified in the IACUC protocol and always adhered to." The regulator caps the
failure count. The paper never reports it. That sentence is the boundary this
whole scaffold turns out to sit on, in one line.

Europe PMC, queried independently for the same failure-rate phrasings,
returned only the two qualitative statements Paperclip had already found. An
absence confirmed on two instruments.

WHICH SOURCE PRODUCED WHICH FINDING
-----------------------------------
    baseline_score, bleomycin_effect, animal_to_animal_sd
        all three off one sentence in Ferrini 2020 (10.3389/fvets.2020.588592),
        which states in its statistics section that every value is mean +/- SD -
        the thing that makes the third constant readable rather than derivable.
    mortality_by_day14
        Kim KH 2018 (10.1038/s41598-018-35320-8), a sentence naming day 14
        explicitly. Corroborating spread from Kadam 2024, Kim SN 2010,
        Barbayianni 2018 and Ferrini 2020, all cited in the note.
    mortality_severity_coupling, p_dosing_failure
        nothing. The queries that came back empty are recorded on the Blocked
        entries, and the sentences below are the negative evidence.

DID THE ASYMMETRY HOLD?
-----------------------
It broke, and the shape of the break is the result.

The claim under test is that papers report what an assay measures and omit how
it fails. For this protocol the failure mode splits into three quantities that
behave completely differently:

1.  MORTALITY BY DAY 14 - reported, routinely, numerically, and often in the
    abstract. It surfaced on the first query and then on every subsequent one:
    "cumulative mortality was 50% at day 14", "100% mortality in 3 U/kg",
    "the survival rate was 100% in the normal saline group, 40% in the BLM
    group", "the mortality rate was 40-50% on days 21, 28 and 35". A single
    regex returned 30+ distinct murine bleomycin papers carrying a mortality
    or survival percentage. This is the opposite of `scar_in_a_jar`, where
    reading the full text end to end found delamination mentioned in no
    direction at all. The asymmetry does not hold for this constant.

2.  DOSING FAILURE - not reported, and the literature says so about itself.
    Barbayianni et al. write that intratracheal administration "always
    resulted in peri-operative mortality (data not shown), a feature not
    usually reported (or even recorded)". Salmaso et al. call it
    "considerable" and give no number. A dedicated intubation methods paper
    tells you the IACUC protocol must specify how many failed attempts are
    allowed, and does not say how many occurred. Five phrasings across the
    full-text corpus and an independent Europe PMC pass returned no rate. The
    asymmetry holds exactly, on a quantity several independent groups agree
    exists and none publishes.

3.  MORTALITY-SEVERITY COUPLING - not reported, and *unidentifiable from what
    is reported*, for precisely the reason this project exists. Kadam &
    Schnitzer scored Ashcroft at every dose where nothing died and scored
    nothing at the dose where everything died: "In 3 U/kg bleomycin-treated
    groups, animals died in the middle of the study." The one paper that ran
    the direct test - Warheit-Niemi et al., stratifying mice into progressors
    and nonprogressors - found no collagen difference and attributed the null
    in print to survivor bias.

So the boundary is regulatory, not scientific, and it falls in a specific
place: a licence counts deaths, it does not record which animals died or how
fibrotic they were. Mortality enters the literature as a MARGINAL COUNT and
never as a COVARIATE. A twin built from this corpus can therefore have the
overall hazard and still cannot have the coupling - and the coupling is the
parameter that sets the direction and size of the bias. Regulation makes the
headline number visible and leaves the estimator's number exactly as missing
as it is in vitro.

That is a narrower claim than "the literature omits its failures", and a more
defensible one.

A note on register: the marginal hazard is itself violently dose-, strain- and
route-dependent (0% to 100% over a 60-fold dose range in one paper), so the
single value recorded below is a conditioned observation, not a constant of
nature. The note on that entry says so at length. Quotes preserve the source's
numbers verbatim; Greek letters are transliterated.
"""

from __future__ import annotations

from ..evidence import Blocked, BlockedReason, CalibrationReport, Evidence

# --- sources ---------------------------------------------------------------

FERRINI_2020 = "10.3389/fvets.2020.588592"       # Ashcroft mean +/- SD, C57BL/6
KIM_2018 = "10.1038/s41598-018-35320-8"          # cumulative mortality at day 14
KADAM_2024 = "10.3390/ijms252212300"             # 60-fold i.t. dose-ranging
BARBAYIANNI_2018 = "10.3389/fmed.2018.00269"     # IT vs OA routes
SALMASO_2025 = "10.1186/s12890-025-04001-4"      # intranasal dose optimisation
WARHEIT_NIEMI_2022 = "10.4049/immunohorizons.2200083"  # progressor stratification
GILHODES_2017 = "10.1371/journal.pone.0170561"   # Ashcroft by dose, no mortality
KOBAYASHI_2023 = "10.1538/expanim.23-0048"       # day-by-day Ashcroft table
KIM_SN_2010 = "10.5487/TR.2010.26.3.217"         # 1-4 mg/kg, mortality stated
OTOSCOPE_2025 = "10.3791/67676"                  # mouse intubation methods paper
ZHOU_2026 = "10.3791/69131"                      # aerosol i.t. delivery (no PMC)

# The queries kept verbatim beside the null results they produced. A
# NOT_REPORTED claim is only as good as the search behind it, and both claims
# below rest on full-text regex rather than abstract screening.

DOSING_QUERY = (
    "paperclip grep over /papers/ (~3.4M full texts), five phrasings: "
    "(1) 'bleomycin[^.]{0,200}(peri-operative|perioperative|procedure-related|"
    "instillation-related|technical fail)'; "
    "(2) 'bleomycin[^.]{0,200}(anesthetic death|anaesthetic death|died during "
    "(the )?(procedure|instillation|intubation))'; "
    "(3) '(intratracheal|oropharyngeal|instillation)[^.]{0,160}(unsuccessful|"
    "failed|misplac|oesophag|esophag)'; "
    "(4) '(instillation|intubation|aspiration)[^.]{0,100}success rate'; "
    "(5) --bool '\"bleomycin\" AND (\"excluded due to incorrect\" OR \"excluded "
    "because of unsuccessful\" OR \"improper instillation\" OR \"incorrect "
    "instillation\" OR \"failed instillation\")'. "
    "Plus a semantic pass for instillation-technique papers: 'protocol "
    "intratracheal instillation mouse technique success rate failed delivery "
    "lung distribution operator training'. "
    "Re-run on a second instrument because Paperclip does not index book "
    "protocol chapters: NCBI E-utilities esearch over pubmed for "
    "'bleomycin AND (Methods Mol Biol[Journal] OR \"Curr Protoc\"[Journal] OR "
    "\"Methods Cell Biol\"[Journal]) AND (fibrosis OR lung)' and for "
    "'intratracheal instillation mouse AND (Methods Mol Biol[Journal] OR "
    "\"Curr Protoc\"[Journal] OR \"J Vis Exp\"[Journal]) AND (protocol OR "
    "technique)', elink to PMC and efetch of every hit that had one; plus "
    "Europe PMC REST search '(bleomycin AND mice) AND (\"instillation failure\" "
    "OR \"unsuccessful instillation\" OR \"failed intubation\" OR "
    "\"peri-operative mortality\" OR \"procedural mortality\")'."
)

COUPLING_QUERY = (
    "paperclip grep over /papers/, five phrasings: "
    "(1) '(mice|animals) (that|which) died[^.]{0,200}(fibrosis|Ashcroft|"
    "severity|weight loss|hydroxyproline)'; "
    "(2) '(survival|mortality)[^.]{0,120}(correlat|associat)[^.]{0,100}"
    "(fibrosis (score|severity)|Ashcroft|hydroxyproline)'; "
    "(3) 'bleomycin[^.]{0,200}(hazard ratio|proportional hazards|Cox)'; "
    "(4) --bool '\"bleomycin\" AND (\"non-survivors\" OR \"survivors and "
    "non-survivors\" OR \"mice that succumbed\")'; "
    "(5) --bool '\"bleomycin\" AND (\"found dead\" OR \"died before the\" OR "
    "\"prior to the scheduled\")'. "
    "Plus a semantic pass: 'bleomycin lung fibrosis mice survivorship bias "
    "surviving animals underestimate treatment effect dropout severity "
    "dependent mortality'. "
    "Second instrument: Europe PMC REST search '(bleomycin AND (mouse OR mice) "
    "AND fibrosis) AND (\"survivor bias\" OR \"survivorship bias\" OR "
    "\"surviving animals\" AND \"underestimate\")', 7 hits, none a murine "
    "bleomycin study; plus the E-utilities protocol-chapter sweep described "
    "under DOSING_QUERY, whose four bleomycin chapters have no PMC record."
)


REPORT = CalibrationReport(
    key="bleomycin_lung",
    found=(
        Evidence(
            constant="baseline_score",
            value=0.3,
            units="Ashcroft",
            source=FERRINI_2020,
            quote=(
                "A significant increase in Ashcroft score values in BLM groups "
                "compared to vehicle can be observed either for Iso (0.3 ± 0.2 "
                "Vehicle vs. 3.5 ± 0.6 BLM; mean diff., 3.2; 95% CI, 2.5-3.8; "
                "p < 0.0001) or Alfa+Dex (0.3 ± 0.2 Vehicle vs. 3.2 ± 0.6 BLM; "
                "mean diff., 2.9; 95% CI, 2.4-3.4; p < 0.0001) protocols."
            ),
            note=(
                "Saline-instilled vehicle arm, not a naive arm - the distinction "
                "matters because instillation alone perturbs the lung. Female "
                "C57BL/6JOlaHsd, oropharyngeal aspiration of 25 ug/mouse "
                "bleomycin on days 0 and 4, scored at day 21 on the modified "
                "(Hubner) 0-8 Ashcroft scale by two blinded readers, n = 20 "
                "vehicle. Kobayashi 2023 gives 0.0 for a bleomycin-free arm "
                f"({KOBAYASHI_2023}), so 0.3 is the upper end of the plausible "
                "baseline rather than an outlier."
            ),
        ),
        Evidence(
            constant="bleomycin_effect",
            value=3.5,
            units="Ashcroft",
            source=FERRINI_2020,
            quote=(
                "A significant increase in Ashcroft score values in BLM groups "
                "compared to vehicle can be observed either for Iso (0.3 ± 0.2 "
                "Vehicle vs. 3.5 ± 0.6 BLM; mean diff., 3.2; 95% CI, 2.5-3.8; "
                "p < 0.0001) or Alfa+Dex (0.3 ± 0.2 Vehicle vs. 3.2 ± 0.6 BLM; "
                "mean diff., 2.9; 95% CI, 2.4-3.4; p < 0.0001) protocols."
            ),
            note=(
                "Absolute score of the bleomycin arm, which is what the scaffold "
                "asks for; the paper also gives the contrast directly as 3.2 "
                "(95% CI 2.5-3.8). n = 34 bleomycin. Consistent with the rest of "
                "the corpus at day 14-21: Kobayashi 2023 reports 4.2 at day 14 "
                f"({KOBAYASHI_2023}); Kadam & Schnitzer 2024 report 'scores "
                "between 4 and 5' at 0.25-0.5 U/kg and 2.9 at 0.1 U/kg "
                f"({KADAM_2024}). This is a mid-range, not a maximal, model."
            ),
        ),
        Evidence(
            constant="animal_to_animal_sd",
            value=0.6,
            units="Ashcroft",
            source=FERRINI_2020,
            quote=(
                "A significant increase in Ashcroft score values in BLM groups "
                "compared to vehicle can be observed either for Iso (0.3 ± 0.2 "
                "Vehicle vs. 3.5 ± 0.6 BLM; mean diff., 3.2; 95% CI, 2.5-3.8; "
                "p < 0.0001) or Alfa+Dex (0.3 ± 0.2 Vehicle vs. 3.2 ± 0.6 BLM; "
                "mean diff., 2.9; 95% CI, 2.4-3.4; p < 0.0001) protocols."
            ),
            note=(
                "Read off, not derived: the statistics section states 'All data "
                "were presented as mean ± SD', which is the whole reason this "
                "paper was used rather than the many that report SEM without a "
                "stated n. Within-arm SD of the BLEOMYCIN arm; the vehicle arm "
                "is 0.2, so the assay is markedly heteroscedastic and a single "
                "pooled SD will understate the treated arm. Ashcroft is a "
                "per-animal mean over many fields, so this SD is partly a "
                "function of how many fields were read - a protocol scoring "
                "fewer fields will show a larger one."
            ),
        ),
        Evidence(
            constant="mortality_by_day14",
            value=0.50,
            units="probability",
            source=KIM_2018,
            quote=(
                "As shown in Fig. 2a, the mice treated with bleomycin began to "
                "die at day 7 and cumulative mortality was 50% at day 14 in BLM "
                "mice."
            ),
            note=(
                "Male C57BL/6, 5 mg/kg bleomycin intratracheally on day 0, "
                "n = 12. Quoted because it names day 14 explicitly, which almost "
                "nothing else does. It is NOT a constant of the model and must be "
                "swept: over the corpus the same quantity runs from 0 to 1 as a "
                "function of dose, strain, sex and route. Kadam & Schnitzer 2024 "
                f"({KADAM_2024}) report 'We observed 100% mortality in 3 U/kg of "
                "bleomycin-treated mice' and 'No mortality was observed in "
                "bleomycin-dosed mice and NC' at 0.05-0.5 U/kg, same day-14 "
                f"endpoint, n = 5/group. Kim SN 2010 ({KIM_SN_2010}) report no "
                "mortality at 1, 2 or 4 mg/kg in ICR mice. Barbayianni 2018 "
                f"({BARBAYIANNI_2018}) report no deaths at 0.8 U/kg by "
                f"oropharyngeal aspiration. Ferrini 2020 ({FERRINI_2020}) report "
                "'neither mortality nor differences were observed'. A twin that "
                "hard-codes 0.50 for a low-dose protocol will be wrong by the "
                "whole range; the defensible use is as the upper-middle of a "
                "swept interval anchored to the dose actually planned. "
                "Usually reported is not always reported: Gilhodes et al. 2017 "
                f"({GILHODES_2017}) is a four-dose intratracheal study, 12 mice "
                "per dose plus 6 saline controls, reporting Ashcroft by dose, "
                "lung function, micro-CT and body weight, which never mentions "
                "death, exclusion or attrition in any direction."
            ),
        ),
    ),
    blocked=(
        Blocked(
            constant="mortality_severity_coupling",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "No paper reports a coefficient, hazard ratio or any other "
                "quantitative link between an individual animal's fibrosis "
                "severity and its probability of dying. What the corpus contains "
                "instead is the reason the coefficient cannot be recovered from "
                "it. Kadam & Schnitzer scored Ashcroft at every dose where "
                "nothing died and scored nothing at the dose where everything "
                "did - 'In 3 U/kg bleomycin-treated groups, animals died in the "
                f"middle of the study' ({KADAM_2024}) - so the dose-response "
                "surfaces for severity and for mortality do not overlap. The one "
                "direct test found returned a null the authors themselves "
                "attribute to the bias: 'We observed no difference in lung "
                "collagen between the bleomycin nonprogressor and progressor "
                "groups (Fig. 7A); however, due to survivor bias, it is possible "
                "that had all the mice in the bleomycin progressor group "
                "survived, they would have had increased hydroxyproline levels' "
                f"({WARHEIT_NIEMI_2022}). Deaths enter this literature as a count, "
                "never as a covariate - the dead animals are not scored, so the "
                "coupling is unidentifiable no matter how many papers are read. "
                "This is the constant a pilot cannot supply cheaply either, "
                "because estimating it requires deliberately running animals to "
                "the endpoint and scoring them."
            ),
            searched=COUPLING_QUERY,
        ),
        Blocked(
            constant="p_dosing_failure",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "The rate of failed intratracheal instillation is not published, "
                "and unusually the literature is explicit that it is not. "
                "Barbayianni et al.: 'However, IT administration (of BLM or "
                "saline) always resulted in peri-operative mortality (data not "
                "shown), a feature not usually reported (or even recorded), as it "
                "concerns almost exclusively handling, skill and chance' "
                f"({BARBAYIANNI_2018}). Salmaso et al., in a paper whose stated "
                "purpose is refining the model for animal welfare: 'This method "
                "requires a surgical incision of the trachea, which is associated "
                "with considerable peri-operative mortality and post-surgery "
                f"monitoring' ({SALMASO_2025}) - 'considerable', no number, and "
                "although that paper says 'Bodyweight and survival were "
                "monitored' it never publishes the survival figures either. "
                "Five phrasings across the full-text corpus returned no rate for "
                "any bleomycin study, and an independent Europe PMC query for "
                "the same phrasings returned only those two statements again. "
                "The clearest item comes from the methods literature rather than "
                "the bleomycin literature: a JoVE paper devoted to mouse "
                "intubation describes the failure mode ('compression of the "
                "trachea due to erroneous canulation of the esophagus can "
                "obstruct breathing and increase mortality'), gives a "
                "troubleshooting procedure for when 'the endotracheal tube is "
                "entering the esophagus repeatedly', and then states 'The number "
                "of re-attempts should be specified in the IACUC protocol and "
                f"always adhered to' ({OTOSCOPE_2025}) - the regulator caps the "
                "failure count and the paper never reports it. Zhou et al. 2026 "
                f"({ZHOU_2026}) likewise say noninvasive tracheal dripping 'poses "
                "a risk of asphyxiation' without quantifying it. The nearest "
                "published number is a delivery EFFICIENCY of >98% of inoculum "
                "for an intubation-mediated technique in a bacterial model "
                "(10.3791/52261), which is a different measurement of a "
                "different procedure and was not used. "
                "LIMIT ON THIS CLAIM: the field's four canonical bleomycin "
                "protocol chapters (10.1007/978-1-4939-7113-8_2, "
                "10.1007/978-1-4939-8570-8_24, 10.1007/978-1-0716-1382-5_21, "
                f"{ZHOU_2026}) have no PMC record and could not be read by "
                "either instrument, so a rate could in principle sit in one of "
                "their troubleshooting sections. What carries the claim is not "
                "the corpus null alone but Barbayianni's first-person statement "
                "that the quantity is not usually recorded at all. "
                "Note the contrast with mortality: the same papers that quantify "
                "severity-driven death to the percent leave the operator-driven "
                "failure as an aside, because the licence counts one and not the "
                "other."
            ),
            searched=DOSING_QUERY,
        ),
    ),
)
