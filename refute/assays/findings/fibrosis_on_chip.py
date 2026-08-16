"""Calibration sweep for `fibrosis_on_chip`, run 2026-08-15/16.

Scaffold: a microfluidic device with a flexible membrane under cyclic strain,
co-culturing epithelium and fibroblasts. Strain is the profibrotic stimulus and
the same variable fatigues the membrane, so on this protocol dose and hazard are
the same knob. Six constants were missing; all six are accounted for below.

INSTRUMENTS, AND WHICH ONE FOUND WHAT
-------------------------------------
Three were used, because the first two each have a gap the other covers.

  Paperclip (full-text corpus, ~3.4M papers)  - primary. Produced both recovered
      constants and every quoted absence. Full-text `grep` was decisive: the
      chip-to-chip CV lives in a supplementary table, and the seeding number
      lives in a subsection called "Success Rate of BBB Chips". Neither is in an
      abstract, and PLAN 6.1 predicted exactly that.
  NCBI E-utilities (PubMed/PMC)               - secondary, and used deliberately
      because Paperclip does not index book protocol chapters. It surfaced the
      two chapters that matter most here.
  WebSearch / WebFetch                        - used only to try to open those
      chapters. Both attempts failed; see THE GAP.

The claude.ai PubMed MCP was unavailable this session ("No claude.ai OAuth token
available"), so PubMed access was via `esearch`/`efetch`/`esummary` over HTTP.

QUERIES RUN
-----------
Paperclip `search -s pmc,biorxiv` (each returning 20-60 papers, then read or
grepped):

  1. lung-on-a-chip alveolus-on-chip cyclic stretch breathing PDMS membrane
     device failure rupture
  2. organ-on-a-chip microfluidic perfusion air bubble occlusion clogging
     troubleshooting practical challenges
  3. PDMS membrane fatigue cyclic stretch number of cycles until failure
     lifetime lung chip durability
  4. chips discarded excluded from analysis leakage bubbles contamination
     organ-on-chip experiment attrition
  5. cyclic strain amplitude dose dependent alpha-SMA collagen fibroblast
     5% 10% 15% stretch magnitude myofibroblast
  6. chip-to-chip variability coefficient of variation organ-on-chip
     reproducibility TEER inter-chip
  7. cell seeding success rate percentage of chips confluent monolayer
     organ-on-chip seeding optimization uneven
  8. stretchable membrane ruptured during cyclic stretching experiment chips
     lost lung chip strain amplitude damage
  9. air bubbles are a major cause of experiment failure in microfluidic cell
     culture frequency of occurrence
 10. fibrosis on chip TGF-beta microfluidic lung fibroblast collagen deposition
     chip model anti-fibrotic drug
 11. lung alveolar chip TEER ohm cm2 barrier baseline value transepithelial
     resistance alveolar epithelium on chip
 12. Liver-Chip performance assessment 870 chips economic analysis toxicity
     screen Emulate reproducibility

Paperclip `grep` (corpus-wide and `--from` the sets above): "membrane rupture",
"(chips|devices) were (excluded|discarded|lost|removed)", "due to (air )?bubble
(formation|ingress|entrapment)", "coefficient of variation", "[0-9]+ cycles",
"n = [0-9]+ chips", "failure rate", plus `--bool '"lung-on-a-chip" AND "bubble"'`
and `--bool '"organ-on-chip" AND "failure rate"'`.

PubMed/E-utilities: `("Methods Mol Biol"[Journal] OR "Methods Cell Biol"[Journal]
OR "Nat Protoc"[Journal] OR "Curr Protoc"[Journal] OR "Bio Protoc"[Journal] OR
"STAR Protoc"[Journal] OR "J Vis Exp"[Journal]) AND (organ-on-chip OR
organ-on-a-chip OR "lung-on-a-chip" OR microphysiological)` - 138 hits, 30
screened; plus `"lung-on-a-chip"[tiab] AND (stretch OR strain)`, and
`("organ-on-a-chip" OR "organ-on-chip") AND (troubleshooting[tiab] OR
"Notes"[Title]) AND (bubble OR seeding OR rupture)` over PMC.

Roughly 220 papers were touched: ~40 read in part or full, the rest reduced by
full-text grep. Query over-narrowing (PLAN 6.1's first failure mode) reproduced
immediately on E-utilities - a five-term ANDed query returned 0 - and is why the
Paperclip queries above are deliberately loose and the filtering is done by grep
afterwards.

THE GAP, STATED PLAINLY
-----------------------
Two protocol chapters are the single most likely home for these three failure
rates, and neither could be opened:

  Asmani & Zhao, "Fibrosis on a Chip for Screening of Anti-Fibrosis Drugs",
      Methods Mol Biol 2299:263-274 (2021), 10.1007/978-1-0716-1382-5_19
  Huh et al., "Microfabrication of human organs-on-chips",
      Nat Protoc 8:2135-2157 (2013), 10.1038/nprot.2013.137

Neither is in Paperclip; neither is in PMC ("Identifier not found in PMC" for
both); both publisher pages redirect to an auth wall. So the NOT_REPORTED claims
below rest on the retrievable corpus, and that qualification is repeated in each
`detail`. It is a real limit, though a bounded one: a Nature Protocols
TROUBLESHOOTING table is structurally a Problem/Cause/Solution grid and does not
carry incidence rates, so the more likely find there is another qualitative
entry rather than the missing number.

WHAT THE SWEEP ACTUALLY FOUND
-----------------------------
2 of 6 recovered. The split falls exactly along the predicted seam: one
precision constant and one attrition constant came back with real numbers, and
all three hazard/attrition constants that are *rates* did not - along with the
two readout constants, which fail for reasons that are about the model rather
than the corpus.

The absences are not silence. They are loud, and they take three recurring
forms, all quoted in the `detail` fields:

  1. A zero-event assertion with no denominator. "the membrane can withstand
     continuous cyclic stretching for >2 weeks without detectable structural
     defects" (Than & Kim 2026) - how many membranes, over how many cycles, is
     not said.
  2. A design argument in place of a measurement. "delamination could not occur
     during normal chip operation" (Stucki et al. 2018); "the risks of
     contamination, leakage, and air bubbles are nearly eliminated" (same
     paper). The hazard is argued away rather than counted.
  3. The failure mode listed but never apportioned. Cameron et al. 2022 name
     "an air bubble trapped in the channel" as one of several causes of a
     checkpoint failure, and give the checkpoint's overall rate but not the
     bubble's share of it.

The sharpest single case is Guttenplan et al. 2025, who get closer than anyone
else and then stop one step short: "the lack of systematic change in the
observed parameters suggests that electrode failure will be stochastic rather
than deterministic but with no failure observed in 1000 cycles". Stochastic
failure is precisely a per-cycle probability. The authors name the quantity, note
that it is the right way to think about the failure, and do not estimate it.

One incidental observation, recorded because it is the survivorship filter
visible in the act. Ewart et al. 2022 ran 870 Liver-Chips, the largest
organ-chip study published, and the per-timepoint sample counts in their Fig. 3
legend fall from n=46 on day 1 to n=40 on day 3 to n=29 on day 7 for a single
donor's albumin measurement. Roughly a third of the units are gone by day 7 and
no cause is given anywhere in the paper; the word "attrition" appears fifteen
times and every one refers to drug-pipeline attrition, not chip attrition. That
is not evidence for any constant here - the loss could be effluent sampling
rather than chip loss, which is itself the point - so it is recorded as prose
and not as a number.

Finally, the scaffold's own note is confirmed by the sources. n per condition is
tiny: Cameron's seeding figure rests on 7-8 chips, McMillan's cyclic durability
test on 5 devices, Luu's CVs on 3-4 devices per plate. Even where a rate is
published the denominator is small enough that the precision floor binds before
the failure rate does.
"""

from __future__ import annotations

from ..evidence import Blocked, BlockedReason, CalibrationReport, Evidence

# --- sources ---------------------------------------------------------------

CAMERON_2022 = "10.3390/mi13101573"          # PDMS OOC fabrication + chip robustness
LUU_2023 = "10.3389/fmolb.2023.1160851"      # fibroblast activation, PREDICT96 OOC
JACHO_2022 = "10.1038/s41598-022-20383-5"    # FMT vs strain amplitude, 3D analogue
VISONE_2023 = "10.1002/adhm.202301481"       # uScar cardiac fibrosis beating chip
THAN_2026 = "10.1016/j.slast.2026.100431"    # porous PDMS membrane fabrication protocol
GUTTENPLAN_2025 = "10.3390/mi16111282"       # stretchable porous membranes, 1000 cycles
MCMILLAN_2020 = "10.3390/mi11080731"         # automated delamination / burst testing
STUCKI_2018 = "10.1038/s41598-018-32523-x"   # breathing alveolus-on-chip array
ZAMPROGNO_2021 = "10.1038/s42003-021-01695-0"  # 2nd-gen lung-on-chip, CE membrane
SACHS_2023 = "10.1101/2023.10.02.560601"     # robotic organoid seeding into chips
EWART_2022 = "10.1038/s43856-022-00209-1"    # 870 Liver-Chips
SUNG_2009 = "10.1007/s10544-009-9286-8"      # microscale bubble trap

# Chapters that would most plausibly carry the failure rates, and could not be
# opened by any of the three instruments. Named so the gap is auditable.
ASMANI_CHAPTER = "10.1007/978-1-0716-1382-5_19"  # Fibrosis on a Chip, MMB 2299
HUH_PROTOCOL = "10.1038/nprot.2013.137"          # Microfabrication of organs-on-chips

# The queries kept alongside the null results they produced. A NOT_REPORTED
# claim is only as good as the search behind it, so these are the literal
# strings run, not a summary of them.

RUPTURE_QUERY = (
    "[Paperclip -s pmc,biorxiv] 'PDMS membrane fatigue cyclic stretch number of "
    "cycles until failure lifetime lung chip durability' + 'stretchable membrane "
    "ruptured during cyclic stretching experiment chips lost lung chip strain "
    "amplitude damage' + 'lung-on-a-chip alveolus-on-chip cyclic stretch breathing "
    "PDMS membrane device failure rupture'; "
    "[Paperclip grep] -e 'membrane rupture' -e 'ruptur' -e 'torn' -e 'tear' -e "
    "'delaminat' over /papers/ and over the three result sets; "
    "'[0-9,]+ ?(million )?(stretch |strain |loading )?cycles'; "
    "--bool '\"lung-on-a-chip\" AND (\"rupture\" OR \"ruptured\" OR \"tore\" OR "
    "\"burst\")'; "
    "[E-utilities] '(\"Methods Mol Biol\"[Journal] OR \"Nat Protoc\"[Journal] OR "
    "\"Methods Cell Biol\"[Journal] OR \"Curr Protoc\"[Journal] OR \"STAR "
    "Protoc\"[Journal] OR \"J Vis Exp\"[Journal]) AND (organ-on-chip OR "
    "organ-on-a-chip OR \"lung-on-a-chip\" OR microphysiological)'"
)

BUBBLE_QUERY = (
    "[Paperclip -s pmc,biorxiv] 'organ-on-a-chip microfluidic perfusion air bubble "
    "occlusion clogging troubleshooting practical challenges' + 'air bubbles are a "
    "major cause of experiment failure in microfluidic cell culture frequency of "
    "occurrence' + 'chips discarded excluded from analysis leakage bubbles "
    "contamination organ-on-chip experiment attrition'; "
    "[Paperclip grep] 'due to (air )?bubble (formation|ingress|entrapment)' over "
    "/papers/; '(percent|%|rate|frequency|incidence|often|[0-9]+ of [0-9]+) "
    "[a-z ]{0,25}(bubble|failure)' over the bubble-paper set; "
    "--bool '\"lung-on-a-chip\" AND \"bubble\"'; "
    "[E-utilities] '(\"organ-on-a-chip\" OR \"organ-on-chip\") AND "
    "(troubleshooting[tiab] OR \"Notes\"[Title]) AND (bubble OR seeding OR rupture)' "
    "over PMC; 'microfluidic cell culture air bubble trap perfusion'"
)


# --- the report ------------------------------------------------------------

REPORT = CalibrationReport(
    key="fibrosis_on_chip",
    found=(
        Evidence(
            constant="chip_to_chip_cv",
            value=0.112,
            units="fraction",
            source=LUU_2023,
            quote=(
                "|Inter-plate variability (avg)|18%|11.2%|4.7%|11.5%| ... "
                "Intra-plate coefficient of variance (CV) was calculated for "
                "technical replicates within the plate (N=3-4) for each of 3 "
                "independent PREDICT96 plates. Inter-plate variability was "
                "calculated by averaging the CV values across the 3 plates for a "
                "given condition."
            ),
            note=(
                "Device-to-device CV of alpha-SMA mean fluorescence intensity in "
                "TGFb1-activated human dermal fibroblasts on the PREDICT96 "
                "organ-chip; the 11.2% column is the TGFb1-stimulated monoculture "
                "arm, which is the arm this scaffold's readout corresponds to. "
                "READ THE ROW LABEL WITH CARE: the row says 'Inter-plate' but the "
                "footnote defines it as the mean of the three intra-plate CVs, and "
                "intra-plate means across replicate devices. So 11.2% is a "
                "chip-to-chip figure, not a plate-to-plate one. That is visible "
                "only in the supplementary table - the Discussion reports the "
                "spread as '(4%-18%)' and the abstract does not mention "
                "variability at all. "
                "The full spread across all four conditions and three plates is "
                "2.5% to 32%, so 0.112 is a central estimate for one arm and the "
                "constant should be swept over roughly 0.05-0.30 rather than "
                "treated as a point. "
                "TRANSFERABILITY: PREDICT96 is a perfused barrier chip with no "
                "cyclic stretch, so this is the CV of a fibrotic-marker readout on "
                "a chip, not of a fibrotic-marker readout under cyclic strain. "
                "Adding a mechanical actuator should widen it: Visone et al. "
                f"({VISONE_2023}) report that one applied pressure delivers "
                "'about 7-12% in the different cell culture chambers of the "
                "device, with a mean value of 10%', i.e. a ~20% CV in the "
                "delivered stimulus before any biological variability, and Stucki "
                f"et al. ({STUCKI_2018}) measure 7.6 +/- 0.66% strain on a nominal "
                "8% chip. Both are stimulus-delivery spreads, not readout spreads, "
                "so they cannot simply be added - but they mean 0.112 is a floor "
                "for a stretch chip, not an estimate."
            ),
        ),
        Evidence(
            constant="p_seeding_failure",
            value=0.43,
            units="probability",
            source=CAMERON_2022,
            quote=(
                "In this case, since only approximately half of the chips were "
                "seeded with cells (and the other half acted as controls), out of "
                "the eight chips seeded with endothelial cells, 57% formed a "
                "confluent monolayer, based on visual assessment."
            ),
            derived=True,
            assumption=(
                "p_seeding_failure = 1 - 0.57. The paper reports the success "
                "fraction; the scaffold wants the failure probability, so the "
                "complement is taken. This assumes 'did not form a confluent "
                "monolayer' and 'seeding failed' are the same event, which is the "
                "paper's own framing - its Checkpoint 4 is a visual confluence "
                "check and its listed failure modes are seeding-stage ones (uneven "
                "ECM, a trapped air bubble, insufficient media)."
            ),
            note=(
                "THE DENOMINATOR DOES NOT DIVIDE. 57% of 8 is 4.56, which is not a "
                "whole number of chips; 4/7 = 57.1% does fit, and 7 is consistent "
                "with the paper's own Checkpoint 2 loss ('88% of 17 chips ... "
                "viable after five days on pump'). So the true denominator is "
                "about 7-8 and the estimate carries roughly a 95% interval of 0.15 "
                "to 0.75. Use it as a prior, not as a rate. "
                "The same paper's cross-model summary gives a compatible second "
                "figure - 'achieving fabrication success rates of over 85% and "
                "average culture formation and maintenance success rates of "
                "approximately 65%' - i.e. ~0.35 failure averaged over its "
                "blood-brain-barrier and small-airway chips, which brackets 0.43 "
                "from below. "
                "TRANSFERABILITY: endothelial cells on a PDMS/PET membrane in a "
                "perfused two-channel chip, not a stretched epithelium-fibroblast "
                "co-culture, so this is a same-architecture rather than "
                "same-assay number. It is nevertheless the only per-chip seeding "
                f"success rate found. Sachs & Costa ({SACHS_2023}) built an entire "
                "robotic seeding rig because 'When manual seedings were first "
                "attempted, they had high variability and failure rates' and never "
                "quantify either - which is the usual treatment, and why this one "
                "sentence in Cameron et al. is the whole recovery."
            ),
        ),
    ),
    blocked=(
        Blocked(
            constant="baseline_readout",
            reason=BlockedReason.ASSAY_SPECIFIC,
            detail=(
                "The unstretched control is 1.0 by construction almost everywhere, "
                "because the field reports this readout as a ratio to its own "
                f"static control. Jacho et al. ({JACHO_2022}) compute 'the relative "
                "gene expression for fold difference between strained samples and "
                "non-loaded control samples ... using the DDCt method'; Visone et "
                f"al. ({VISONE_2023}) report every marker as a fold change with "
                "respect to static. Where an absolute number does exist it is an "
                f"instrument reading - Luu et al. ({LUU_2023}) tabulate 'SMA MFI', "
                "a mean fluorescence intensity tied to one stain, one objective and "
                "one exposure. Neither form transfers. "
                "There is a real alternative, and it is a different quantity rather "
                "than a missing one: if the readout is barrier function, baseline "
                "TEER is published in ohm.cm2 and is physically meaningful. But it "
                "is not the AU the scaffold declares, it depends strongly on "
                "electrode geometry and medium, and switching to it changes what is "
                "being measured. That is a decision for whoever runs the assay, not "
                "a number the corpus is withholding. Same shape as "
                "`baseline_deposition` in scar_in_a_jar."
            ),
        ),
        Blocked(
            constant="strain_dose_response",
            reason=BlockedReason.CONTEXT_DEPENDENT,
            detail=(
                "Ill-posed as a scalar, and the literature shows why rather than "
                "hiding it. The only source found that applies more than one strain "
                f"amplitude to the same construct is Jacho et al. ({JACHO_2022}), "
                "who report that 'The a-SMA expression elevated significantly "
                "(P < 0.05) for 8% and 12% mechanical strain groups by 1.7 +/- 0.3 "
                "and 13.2 +/- 0.2-folds, respectively, compared to the control group "
                "(0% mechanical strain). On the other hand, no a-SMA expression was "
                "detected for the 4% mechanical strain group.' "
                "A linear slope fitted to 0-8% gives ~0.09 fold per % strain; fitted "
                "to 8-12% it gives ~2.9 fold per % strain. Same construct, same "
                "experiment, thirty-fold disagreement depending on which pair of "
                "points is used. The response is threshold-like, not proportional, "
                "so any single 'AU per % strain' is an artefact of the amplitudes "
                "chosen. "
                "On-chip the situation is worse in a different way: chip papers pick "
                f"one amplitude and stay there. Visone et al. ({VISONE_2023}) apply "
                "'a cyclic 10% uniaxial strain at 1 Hz' and report ~4-fold COL1A1 "
                "against static; there is no second amplitude, so no slope exists to "
                "extract. The scaffold needs a dose-response surface with a "
                "threshold term, swept over roughly 4-15%, and 4% may sit below the "
                "threshold entirely. "
                "This is a finding about the model, not a gap in the corpus. Note "
                "the consequence for the coupled-hazard design: because the same "
                "variable drives phenotype and rupture, and the phenotype response "
                "is threshold-like while fatigue damage accumulates smoothly, "
                "lowering strain to protect the membrane can cost the entire signal "
                "rather than a proportional fraction of it."
            ),
        ),
        Blocked(
            constant="p_rupture_per_1e5_cycles",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "Nothing in the retrievable corpus reports a per-cycle membrane "
                "failure probability, at any strain amplitude, for any "
                "organ-on-chip. What is published instead takes three shapes, none "
                "of which converts into this constant. "
                "(1) Zero-event assurance without a denominator. Than & Kim "
                f"({THAN_2026}): 'Our internal evaluations further confirm that the "
                "membrane can withstand continuous cyclic stretching for >2 weeks "
                "without detectable structural defects or performance degradation.' "
                "No n, no cycle count, no definition of 'detectable'. "
                "(2) The right idea, declined. Guttenplan et al. "
                f"({GUTTENPLAN_2025}) run a cyclic-strain durability test and write "
                "that 'the lack of systematic change in the observed parameters "
                "suggests that electrode failure will be stochastic rather than "
                "deterministic but with no failure observed in 1000 cycles, we do "
                "not anticipate electrode failure to limit their effectiveness'. "
                "They name the quantity as stochastic, observe 1000 cycles - one "
                "hundredth of the 1e5 this constant is scaled to - and stop. "
                f"McMillan et al. ({MCMILLAN_2020}) are the closest to a real "
                "denominator: 'Devices of 400 um gap distance showed no delamination "
                "resulting from pressurization at 500 mbar for 10 h, nor at cyclic "
                "pressurization (0 to 500 mbar, 0.2 Hz, 10,000 cycles)', n = 5 "
                "devices. Zero events in 5 x 10,000 device-cycles bounds the rate "
                "only uselessly loosely, and it is bond delamination in a "
                "Flexdym-polycarbonate device rather than fatigue rupture of a "
                "stretched PDMS membrane. "
                "(3) The hazard argued away instead of measured. Stucki et al. "
                f"({STUCKI_2018}): 'One might also consider testing the delamination "
                "pressure of the chip; however, because we were creating negative "
                "pressure inside the basal cell culture chamber, delamination could "
                "not occur during normal chip operation.' Zamprogno et al. "
                f"({ZAMPROGNO_2021}) do report membrane disruption, but it is "
                "enzymatic - MMP-8 digestion of a collagen-elastin membrane - not "
                "strain fatigue, and their data statement is 'No data was excluded.' "
                "The near-miss quantity that does exist is burst or delamination "
                "PRESSURE (PDMS-PDMS plasma bonds 'most often withstanding pressures "
                "between 2 and 3 bar ... reported ranging from approximately 0.7 to "
                "4 bar'). Converting a burst pressure into a per-cycle hazard needs "
                "an S-N fatigue curve for thin porous PDMS and the operating stress "
                "distribution, and neither is published - so this is not a unit "
                "conversion away, it is a pilot away. "
                "CAVEAT ON THIS CLAIM: two protocol chapters that could plausibly "
                f"hold a troubleshooting entry - Asmani & Zhao ({ASMANI_CHAPTER}) "
                f"and Huh et al. ({HUH_PROTOCOL}) - are in neither Paperclip nor "
                "PMC and are behind publisher auth. The claim is therefore about "
                "the retrievable corpus. A troubleshooting table would most likely "
                "add a fourth qualitative shape rather than the number."
            ),
            searched=RUPTURE_QUERY,
        ),
        Blocked(
            constant="p_bubble_per_day",
            reason=BlockedReason.NOT_REPORTED,
            detail=(
                "This is the cleanest absence of the six, because the field has "
                "built an entire hardware sub-literature around the problem without "
                "ever measuring how often it occurs. Bubble traps, debubbler "
                "modules, bubble-tolerant pumpless layouts and CFD-designed 3D "
                "bubble trappers were all read; not one reports an incidence. Sung "
                f"& Shuler ({SUNG_2009}) open with 'Formation of air bubbles is a "
                "serious obstacle to a successful operation of a long-term "
                "microfluidic systems using cell culture' and then characterise trap "
                "capacity in microlitres, never occurrence in events per day. "
                "Where organ-chip papers touch it, they either assert the risk away "
                f"- Stucki et al. ({STUCKI_2018}): 'because no external tubing or "
                "pumps are used for the perfusion, the risks of contamination, "
                "leakage, and air bubbles are nearly eliminated' - or list the "
                "failure mode without apportioning it. Cameron et al. "
                f"({CAMERON_2022}) are explicit that their seeding checkpoint 'can "
                "have many common failure modes ... These failure modes could "
                "include cell detachment due to an uneven extracellular matrix "
                "layer, an air bubble trapped in the channel, or even insufficient "
                "media supply', and give the checkpoint's rate but not the bubble's "
                "share of it. Their one quantified perfusion loss over five days "
                "('88% of 17 chips ... viable') is attributed to a tubing "
                "disconnection, not a bubble, so it cannot stand in for this "
                "constant. "
                "Corpus-wide grep for bubble-caused exclusions returns hits only "
                "outside organ-on-chip - a point-of-care test strip, cell-culture "
                "flaskettes - which shows the phrasing is findable and that "
                "organ-chip papers simply do not use it. "
                "Same protocol-chapter caveat as p_rupture_per_1e5_cycles: Asmani & "
                f"Zhao ({ASMANI_CHAPTER}) and Huh et al. ({HUH_PROTOCOL}) could not "
                "be opened."
            ),
            searched=BUBBLE_QUERY,
        ),
    ),
)
