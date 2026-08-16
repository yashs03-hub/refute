# refute — build plan and state

Authoritative build state. `README.md` is the pitch; this is what is done, what
is next, and what is deliberately not being built.

Target: **re:AGENT — End to End Agentic Science**, 15–16 Aug 2026, San
Francisco. Confirmed attendance.

**Track B — Build the Dataset** (see §2). Track A was the earlier assumption and
was wrong: `refute` evaluates agents that automate a workflow rather than being
one, whereas Track B's brief — facts that "sit one line at a time across
thousands of papers" — is the §6 calibration almost verbatim.

> **Added 2026-08-16 — this repository is now layer 2 of a two-layer system.**
> The agreement with the other builder is `15 - SPEC - the whole system.md`.
> Layer 1 answers everything about a hypothesis that can be answered without a
> bench — the data and the literature, to exhaustion — and either stops, or hands
> over the residual it could not settle. **Layer 2, this repository, designs the
> experiment for that residual.** The seam in code is `HANDOFF.md`, and it is
> built: `handoff.py`, `intake.py`, `resolve.py`, `requirements.py`, `gate.py`,
> `pipeline.py`.
>
> Nothing below is invalidated by this — the twin, the scorer, the tiers and the
> Track B argument are all layer 2's internals and the SPEC says explicitly that
> they are layer 2's business. What changed is the *entry point*: designs no
> longer arrive only as prose from a user, they arrive as a residual from a layer
> that has already ruled things out. Two consequences the SPEC is emphatic about
> and this plan did not previously state: **"looked and it is not there" must
> stay distinguishable from "have not looked"** at the boundary as well as
> inside, and **the shared biological vocabulary is unagreed** — `vocabulary.py`
> declares this side's half and prints the gap.
>
> `INTEGRATION.md` predates the agreement and carries a superseded banner.
> `BUILD.md` is layer 1's build plan and is partly superseded by SPEC §8.

---

## 0. State

| Component | Status |
|---|---|
| `calibration.py` — constants tagged MEASURED / FITTED / ASSUMED | ✅ done |
| `twin.py` — contraction, lysis, heterogeneity, attrition, measurement | ✅ done |
| `design.py` — `DesignSpec`, plus Experiment 4 as run | ✅ done |
| `score.py` — power, testability, MDE, failure diagnosis | ✅ done |
| `assays/` — protocol registry behind a calibration gate | ✅ done (PR #2) |
| `providers.py` — OpenAI + Anthropic behind one interface | ✅ done (PR #3) |
| `agent.py` — propose / revise / extract | ✅ **run live, end to end** |
| `assays/evidence.py` · `sources.py` · `literature.py` — calibration harness | ✅ done |
| `baselines.py` — as-run / naive / expert / ceiling references | ✅ done — gives an agent's score a scale (§9.6) |
| `environment.py` — `RefuteEnv`, the benchmark as an environment | ✅ done (§9.4) |
| `api.py` — `/score` · `/score/text` · `/run` · `/assays` | ✅ done (§9.4) |
| `record.py` — serialise and replay an agent run | ✅ done — the demo no longer needs a network |
| First recorded run — `cases/exp4/runs/gpt-5.5-high.json` | ✅ done, and it broke four things (§10). gpt-5.5 **declined to run the experiment**, correctly, and the scorer gave it 0% until fixed |
| `extraction_cases.py` — 5 adversarial designs, known specs | ✅ done, and **5/5 pass live** |
| `tests/` | ✅ green. ⚠️ **Corrected 2026-08-16** — this row read "186 passing, 5 live-only skipped". It is several hundred more than that and the number moves hour to hour as work lands, so **run `python -m pytest -q`; do not quote a figure from this table** |
| `cli.py` — `baseline` · `baselines` · `sweep` · `tier0` · `harnesses` · `demo` · `assays` · `calibrate` · `check-extraction` · `replay` · `chat` · `infer` · `advise` · `route` · `search` · `providers` · `run` | ✅ done. ⚠️ **Corrected 2026-08-16** — eight subcommands were missing from this row: `tier0`, `harnesses`, `demo`, `chat`, `infer`, `advise`, `route`, `search` |
| Calibrating the six tier-1 scaffolds | 🟡 **in progress.** ⚠️ **Corrected 2026-08-16** — this read "blocked on Paperclip credential". The credential exists and works (§6.3), and the Track B sweep is running now. Not done: no scaffold has cleared `require_runnable()` yet |

**Landed 2026-08-15, and absent from the table above until 2026-08-16.** The
downstream half of the two-layer pipeline. Each is tested; none needs a network.

| Component | Status |
|---|---|
| `resolve.py` — `Requirement`, `Resolution`, `ResolutionSet`, the resolver seam | ✅ done. Invariants enforced at construction, not documented — see `HANDOFF.md` §2a |
| `requirements.py` — what a verdict depends on, read off the registry | ✅ done. The list is exogenous to the thing filling it, which is the property the whole split rests on |
| `gate.py` — `route_design` → `TIER1` · `TIER0` · `OUT_OF_SCOPE` · `REFUSE` · `NOT_READY` | ✅ done, and value-blind: it never dereferences a number, pinned by a tripwire test |
| `pipeline.py` — resolve → gate → simulate \| tier 0 → advise, with a per-stage narrative | ✅ done |
| `adapt.py` — the recorded literature findings crossing into a `ResolutionSet` | ✅ done. This is what lets the downstream half run on real recovery rates instead of on fixtures |
| `handoff.py` — layer 1's `Handoff` / `Finding` / `OpenItem`, and their crossing | ✅ done. Trace ids now survive it — `Resolution` gained `origin_event` 2026-08-16. The divergence note inside `handoff.py` still calls that gap open and has not caught up |
| `intake.py` — residual prose → assay choice + `DesignSpec` | ✅ done. Assay selection is deterministic, no model call. Nobody had owned this step |
| `vocabulary.py` — this side's declared terms | 🟡 **deliberately unfinished.** The alias map is empty and three of six facets are undeclared, because the vocabulary must be agreed with layer 1 before either side hardcodes. `coverage_report()` prints the size of the gap. **Do not cite it as an agreement** |
| `cases/fixtures/` — seven hand-written resolution sets | ✅ done. Simultaneously the gate's test matrix and the resolver's output spec |
| `NOT_SUPPLIED` blocked reason | ✅ added 2026-08-15, as a correction: the tier-0 quantities were being filed as `ASSAY_SPECIFIC`, which asserts something about publishing practice for numbers no paper was ever going to carry |
| Per-tier calibration reporting | ✅ done — `refute calibrate` splits *what the assay measures* from *how the assay breaks*, which is the asymmetry stated as a measurement |
| Optimizer — cheapest design meeting a power target | ✅ done, 2026-08-16 — `optimize.py`, `refute optimize`. Searches `replicates_per_condition` and imaging schedule only; `antifibrinolytic` has no default and must be stated, per §9.1's cheat-code warning. A tripwire test pins that `agent.py`/`environment.py`/`api.py` never import it — **human-facing only, never given to the harness** |
| Record a real agent run to `cases/exp4/runs/` | ✅ **done — corrected 2026-08-16.** This row said "needs one paid run", contradicting §7.1 item 4 and the row above it. `gpt-5.5-high.json` is committed and replays. What is genuinely still missing is narrower: that recording's final round **declined**, so it carries no scoreable revised design. A second run whose revision assigns wells is what would let the superseded ~57 be recomputed |
| Second case (qPCR artifact) | ⬜ not started — needs owner's go-ahead |
| Uncertainty propagation over calibration params | 🟡 partial — ASSUMED constants swept at scoring time (§9.1); FITTED ones not yet |
| Proto integration | ❌ **resolved: do not build** — Proto is sequence-typed (§2) |
| BenchFlow packaging — `refute` as an eval environment | 🟡 `RefuteEnv` is the interface; packaging as their environment not done (§2) |

PRs #1–#3 merged 2026-08-04. The loop runs: propose → extract → simulate →
revise → extract → simulate, against `openai:gpt-5.5`.

**First live result.** gpt-5.5 independently reproduced Experiment 4's two
defects — n=3 per arm, no antifibrinolytic, no reasoning about scaffold loss.
Given consequence-feedback it narrowed to the two arms that matter, filled the
plate (2×6), added a pre-treatment baseline and flagged scaffold failure:
testable 0% → 97%. Power still only reached 9%, with ~57 wells/arm required.
**Even the best design available on one plate cannot answer the question** —
that verdict is the finding.

> ⚠️ **`~57 wells/arm` is superseded and cannot be recomputed.** A non-robust
> variance estimator was fixed on 2026-08-10 (§9.5); it roughly halved every
> required-replication estimate. The as-run design went 50 → **20**, and
> `EXPERT` — the same 2-arm, n=6, aprotinin, Day-7 shape the agent converged on —
> needs **29**. The agent's revised spec was never serialised, so its own number
> cannot be recalculated: this is precisely the cost of §7.1 item 4 being
> outstanding. **Quote 9% power and 0% → 97% testable, which are unaffected; do
> not quote 57 until the run is replayed.**
>
> *Clarified 2026-08-16 — the conclusion is unchanged, the stated reason was
> imprecise.* The committed recording **does** serialise an extracted spec per
> round. The reason 57 still cannot be recomputed is that the run which produced
> it was attempt 2, which was never recorded, and the run that was recorded is
> attempt 3, whose revised round **declined and assigns no wells** (§10.3). So
> there is no revised design to re-score, and replaying the recording reports
> round 1 at ~49 wells/arm and a decline at the end. **Still do not quote 57.**
>
> The finding itself is untouched. `refute baselines` now demonstrates it more
> directly than the agent run does: `EXPERT`, hand-written with full hindsight,
> reaches 9% power on one plate, and `CEILING` — the same design with the plate
> limit lifted — reaches 83%. The constraint is the apparatus.

**The live runs found three bugs, two of them in the scorer, not the agent:**

1. gpt-5.5 at high effort spent a 16k budget entirely on reasoning and returned
   no visible text. Budgets raised; a ledger now counts reasoning tokens, which
   were ~85% of output.
2. The feedback demanded ~47 wells/arm without stating the brief's one-plate
   limit, so the agent scaled to 288 wells across 24 plates and was marked down
   for following the advice. A scorer that demands what it refuses to score is
   broken; infeasibility is now a named verdict.
3. The twin rejected a design that treated at 0.75 h and imaged at 1 h, because
   it demanded a baseline at or before t0 *exactly*. That is a good baseline.
   The grace period is now derived from the calibration (2.89 h).

Both scorer bugs were false negatives — confidently returning 0% for sound
designs — which is why tests missed them and running it for real did not.

**Remaining gap:** the extractor is now `gpt-5.4-mini` and its fidelity is
unvalidated. It is the leading suspect for any surprising score until the
adversarial extraction set exists.

**Operational constraint discovered:** the binding limit is rate, not cost.
10k TPM on gpt-5.5 vs 100k on gpt-5.4-mini, and pools are per-model — which is
why the extractor sits on a different model. A full loop on a frontier model is
throughput-bound at ~2–3 min regardless of credit balance.

---

## 1. What the twin found

Two independent, separately fixable defects in Experiment 4:

1. **Scaffold failure.** No antifibrinolytic; fibrinolysis fastest in the most
   contractile arm, so TGF-β arms fail first — the arms the contrast needs.
2. **Underpowering, independent of (1).** ±2–3 fill-points of quantification
   noise means ~50 wells/arm to resolve the effect. The experiment ran 3.

(2) was not designed in. It emerged from the simulation and contradicted the
test expectation originally written for the "repaired" design — the test was
wrong, not the twin. That is recorded because it is the single best evidence
that the scorer is mechanistic rather than a rubric agreeing with its author.

---

## 2. Platform context — where this sits

Two of the event's own tools define the layers either side of this project.

### Proto — the entity-design layer

Stanford Lab of Evolutionary Design, with Arc Institute. A design framework for
generative biology: `proto-tools` (model deployment) plus `proto-language`, a
specification framework built on four primitives. Those primitives map onto
this project almost exactly, one level up:

| Proto (sequence design) | `refute` (experiment design) |
|---|---|
| **Sequences** — the target system | `DesignSpec` — the plate |
| **Generators** — propose candidates | the agent proposing designs |
| **Constraints** — properties candidates must satisfy | scaffold survives to endpoint, n adequate, kinetics identifiable, fits the plate |
| **Optimizers** — search the solution space | propose → simulate → revise |

**The seam.** Proto's own write-up says it is "most powerful when paired with
experimental testing" and names "learning from experimental outcomes" as the
goal — but Proto stops at nominating candidates scored by predictive models. It
says nothing about whether the assay that adjudicates them can resolve them.

That is the argument to make:

> A generator that produces candidates faster than the assay can adjudicate
> them does not accelerate science; it accelerates the production of unresolved
> candidates. And when an underpowered assay fails to separate them, the
> conclusion drawn is that the *model* was wrong. Experiment 4 was ~17x
> underpowered — it would have failed to distinguish anything Proto handed it,
> and the blame would have landed in the wrong place.

Note the constraints differ in kind, in this project's favour: Proto's come
from predictive models, which are themselves fallible predictions. These come
from measurements of an assay that actually failed.

**RESOLVED 2026-08-04 — do not integrate.** The organisers' own tool description
settles the open question: Proto is "a high-level programming language for
designing DNA, RNA, and protein sequences", and its Segments are defined as
"contiguous sequence regions" grouped into Constructs. The primitives are
sequence-typed, not generic.

So the mapping in the table above is a genuine *analogy* and nothing more. Do
not force an integration: this design space is small and discrete
(antifibrinolytic y/n, replicates, timepoint schedule, endpoint), and a plain
grid or Bayesian search suffices. Keep the argument, drop the dependency — the
seam above is still the right thing to say to Proto's authors, and it costs
nothing to say without building on their stack.

### Paperclip — the knowledge layer

GXL's agent-native index over scientific literature: 7.5M PMC **full-text**
papers, 388K bioRxiv, 82K medRxiv, 3M arXiv, plus 580K clinical trials, 575K
UniProt, 256K PDB, 2.9M ChEMBL, 150M OpenAlex abstracts. MCP server at
`https://paperclip.gxl.ai/mcp`.

Full text is the operative property. Assay failure modes are documented in
**methods and troubleshooting sections**, never in abstracts and rarely in
results. An abstract index cannot calibrate a twin; a full-text one can.

**The positioning line, for the host's own judges:**

> Paperclip indexes what was published. `refute` covers what was not. Failure
> modes are absent from the corpus not because it is too small, but because it
> is filtered by what gets written up — and no amount of indexing recovers what
> was never recorded.

### BenchFlow — the harness layer, and the closest neighbour

Added 2026-08-04 after reading the organisers' tool list. This was missed
earlier and matters more than Proto ever did.

BenchFlow is "a framework for creating evals and environments for agents
learning", used to ship SkillsBench, FrontierPhysics, ClawsBench and PostTrain —
and the description says explicitly: *"You can use it to create data and
environment for life sciences to evaluate and improve agents."*

That is a one-line description of what `refute` is. An eval environment for
agents, in life sciences. Where Proto was an analogy, this is the same category.

**Implication.** `refute` should probably be packaged as a BenchFlow
environment rather than a standalone CLI. The twin becomes the environment, the
`DesignSpec` the action space, and `score_design` the reward — which is already
the internal architecture, so the port is mostly interface work.

**The distinction to keep sharp**, because "why not just use BenchFlow" is the
obvious question from a BenchFlow judge:

> BenchFlow is the harness for running evals. The hard part here was never the
> harness — it was obtaining a reward signal that is not another model's
> opinion. `refute` contributes the *scorer*, calibrated on measurements from an
> experiment that failed. Put it in BenchFlow and it becomes a benchmark other
> people can run; leave it out and it stays a demo.

Treat that as a genuine opportunity, not a threat: being a BenchFlow
environment is distribution, and BenchFlow is a co-host.

### The four-layer map

| Layer | Tool | Question it answers |
|---|---|---|
| Knowledge | Paperclip | What is already known? |
| Entity design | Proto | What candidate should I build? |
| Harness | BenchFlow | How do I run and score agents repeatably? |
| **Validation** | **`refute`** | **Can the experiment that tests it actually answer the question?** |

Nobody has built the fourth. That is the pitch — and the third is where it
should live.

### Tracks — which one this is

The event runs three tracks, plus bring-your-own:

| Track | Brief | Fit |
|---|---|---|
| A — Build the AI Scientist | Automate a scientific workflow end to end | Partial. `refute` *evaluates* such agents rather than being one |
| **B — Build the Dataset** | *"Assemble a research-ready dataset that doesn't exist yet because the facts sit one line at a time across thousands of papers. Read and retain the whole corpus, then find the pattern no single paper could show you."* | **Direct hit — this is §6** |
| C — Build the Biological Design | Literature into a generative pipeline | No |

**Track B is the calibration work in §6, almost verbatim.** Assay failure
constants sit one line at a time across thousands of methods sections; the
dataset does not exist; and the pattern no single paper can show is *which
constants are systematically absent*. §6 stopped looking like a side quest the
moment this track description appeared — it is a submission.

That also resolves what to build on the day. The strongest position is both:
Track B as the entry (the missing-constants dataset), with `refute` as the
working artefact that motivates it and gives the dataset a use.

---

## 3. Next, in order

1. **Stub-test the agent plumbing offline.** Run propose → extract → score with
   a canned design string and a stub extractor, so the code path is verified
   before the event. No credential is available locally (checked), so only
   *model quality* should remain untested — a plumbing bug must not eat the
   Saturday.
   ⚠️ **Corrected 2026-08-16:** "no credential is available locally" is no longer
   true of Paperclip — it is installed and a live search returns hits (§6.3). The
   reasoning still stands for the *model* credential, which is what this item was
   about.
2. **Run `agent.py` end to end once** on the event's Claude credits. Extraction
   fidelity is the most likely failure point: if the extractor mis-reads a
   design, the twin scores the wrong plate and it looks like the agent's fault.
3. **Build the optimizer.** Turn `sweep` from a grid that prints a table into a
   search that returns *the cheapest design achieving a power target* — fewest
   wells, fewest timepoints, subject to the twin's feasibility constraints.
   This is both the missing Proto primitive (§2) and the thing that makes this
   a product rather than a demo: if the bottleneck is the cost of finding out
   you were wrong, the deliverable is the minimum-cost sufficient experiment.
4. **Extraction adversarial check.** Hand-write 5 designs with known specs;
   confirm the extractor recovers them. Extraction failure must never be
   scoreable as design failure.
5. **Second case, calibrated via Paperclip.** Sweep methods sections for
   documented failure modes and extract constants. Candidates, best first:
   - **Engineered heart tissue (EHT) on flexible pillars** — the assay fails at
     *both* ends of the dose-response (positive inotropes raise rupture risk;
     negative inotropes abolish beating, so there is no readout). The
     deliverable is the usable dose window, which is what a cardiotoxicity
     screening group actually needs. Best commercial fit.
   - **Attached / stressed collagen lattice** — tension causes premature
     detachment, and detachment *is* the readout, so the failure yields a
     plausible number rather than missing data. Nastier than fibrinolysis and
     better documented.
   - **Scratch / wound-healing migration** — most-run assay in biology, pitfalls
     explicitly written up; lowest acquisition cost.

   ⚠️ **Label the epistemic status.** Case 1 is measured ground truth this
   project owns. A Paperclip-calibrated case is literature-derived and inherits
   whatever those papers got wrong. Different status, stated in the README. Do
   not let the easier case dilute the claim that makes the hard one valuable.
6. **Baseline non-agent designs.** Score the as-run design, a naive design, and
   a domain-expert design, so the agent's number means something relative.
7. **Propagate calibration uncertainty.** Score over a distribution of
   `TwinParams` rather than the point estimate. Report bands, not numbers.
   ✅ *Started 2026-08-10* — `score_design` now re-scores at the edges of every
   ASSUMED constant a design actually reaches and sets
   `verdict_sensitive_to_assumption` when the conclusion does not survive the
   span (§9.2). That covers the one constant a design can reach directly,
   `aprotinin_hazard_scale`. The general case — bands over *all* of `TwinParams`,
   including the FITTED lysis shape and scale — is still open.
8. **Second case (qPCR artifact)** — the "hypoxic shift" that turned out to be
   empty tubes. Same shape: an agent handed that data will confidently explain
   an artifact. **Needs the owner's explicit go-ahead before touching that
   data.**

## 4. Deliberately not building

- **A biology oracle.** The twin scores *designs*, not hypotheses. It cannot
  say whether MSC-CM suppresses contraction, and must never be presented as if
  it can.
- **A wet-lab run before the event.** A repeat needs ~10 days from casting plus
  a recipe fix, and the author is travelling. Out of reach; not promised.
- **An LLM-as-judge scorer.** That was the original design and it was replaced
  on purpose. Reintroducing it would give back the thing that makes this
  different.
- **More synthetic cases from an LLM.** Generating fake failed experiments puts
  invented ground truth back at the centre. Extra scenarios come from sweeping
  the *calibrated* twin, or from documented failures via Paperclip — not from a
  model's imagination.
- **A sequence-design tool.** Proto already occupies that layer and does it
  properly. Competing there would be both worse and pointless; the whole
  argument is that the validation layer is the empty one.
- **A virtual cell.** Arc's territory, and a different object: a virtual cell
  predicts what the biology does. This models the apparatus. Keep the
  distinction sharp — see §5.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Extractor mis-parses a design; scored as a design failure | §3 items 1 and 4 — stub test, then adversarial extraction set, before any headline number |
| Judges read "calibrated on one plate" as fatal | Say it first, in the limits section. The alternative on offer is zero plates |
| Aprotinin assumption carries the conclusion | Already swept in tests across 2×/4×/8×; the lysis-rescue claim holds throughout |
| Twin penalises a genuinely clever design it can't model | Stated in README limits; report diagnoses, not just a score |
| Demo needs a live run on stage | `baseline` and `sweep` are instant and need no API key — those are the demo; `run` is the flourish. The twin needs no GPU or sponsor compute, so the demo cannot die on venue infrastructure |
| **"Isn't this just a virtual cell?"** — Arc affiliates two of the seven co-hosts (Arc directly, and Proto via the Lab of Evolutionary Design) | Have the one-liner ready and lead with it: *a virtual cell predicts the biology; this models the apparatus. A perfect virtual cell still will not tell you the fibrin gel dissolves on day 7, that the most-treated arm fails first, or that segmentation noise means you needed 50 wells.* Complementary, not competing |
| Paperclip-derived case 2 dilutes the "unpublished ground truth" claim | Label the two cases' epistemic status separately in the README (§3 item 5). Measured ≠ literature-derived |
| ~~Proto integration turns out to be a dead end mid-build~~ | **Retired 2026-08-04** — checked and it is one. Proto is sequence-typed, so nothing was built on it. The risk cost nothing because the check happened before the architecture |
| **"Why not just build this in BenchFlow?"** — asked by a BenchFlow judge | Agree, and say so first: it probably *should* live there. The harness was never the hard part; a reward signal that is not another model's opinion was. `refute` contributes the scorer, BenchFlow contributes the distribution |
| Track B entry is judged as a literature-mining exercise | Lead with the absence, not the extraction. The dataset's value is which constants are *missing* and the pattern in which ones — a claim about publishing practice that no single paper can support |
| Judged as sitting out the safety conversation the week AI-designed phages hit the news | §8. The architecture already takes a position — generator never verifies itself, fails closed, silence is not evidence — and took it before the news. Reframe, do not pivot; the reasons not to pivot are recorded so they are not re-argued on the day |
| ~~Public presentation is a patent disclosure~~ | ✅ **RETIRED 2026-08-10 — no patent.** Decided deliberately, not defaulted into. The method can be presented, written up and open-sourced without restriction |
| ~~Conflating "no patent" with "the data can go public"~~ | ✅ **RETIRED 2026-08-15 — owner is content to publish the results.** Recorded because the reasoning changed, not just the answer: see §13.4. ~~The remaining gate is authorship, not ethics, and it is not the owner's alone~~ — **cleared by the owner 2026-08-15**, recorded in `cases/exp4/PROVENANCE.md`. No open gate remains on the data or the results. Repository *visibility* is a separate decision and has not been taken |

---

## 6. Calibrating the six tier-1 scaffolds

The `assays/` layer holds one MEASURED protocol (`fibrin_contracture`) and six
SCAFFOLDs that **refuse to be scored** — `require_runnable()` raises
`UncalibratedAssayError`. That refusal is a correctness property with a test
behind it: inventing constants would reintroduce exactly the invented-ground-truth
problem this project exists to criticise. So "calibrate" here can only mean
*find real published values*, tagged `LITERATURE`, never `MEASURED`.

**35 constants are missing across the six.**

### 6.1 What a PubMed-only attempt established (2026-08-04)

Attempted via the PubMed MCP. Worth recording because the *failure pattern* is
itself the result.

| Obstacle | Detail |
|---|---|
| Query over-narrowing | The MCP ANDs every term; precise queries returned 0–2 hits |
| Constants live in methods, not abstracts | Abstract said "~5-fold"; full text gave 4.7-fold, Z′ 0.49–0.51, Ficoll-PM70 37.5 mg/ml, ascorbate 50 µg/ml |
| Full text mostly unavailable | Two of three PMC fetches returned an empty body despite being indexed |

**What was found** — Good et al. 2019, *BMC Biomed Eng*,
[10.1186/s42490-019-0014-z](https://doi.org/10.1186/s42490-019-0014-z)
(scar-in-a-jar): collagen I **4.7×** under TGF-β1 1 ng/ml with macromolecular
crowding, α-SMA 3.2×, collagen IV 3.7×; mean signal:background **4.6**;
Z′ **0.49–0.51**; 72 h endpoint, signal held to 5 days; TGF-β EC50 0.5 ng/ml;
assay success rate **>95%** over 480 IC50 points.

Note a discrepancy that only full text exposes: the abstract reports **CV < 5%**,
the results section **< 15%** — and neither is the well-to-well CV of the
*deposition readout*. It is the inter-assay CV of control-compound potency.
A well-to-well CV can instead be *derived* from Z′ and signal:background, but
that is a derivation and must be tagged as one.

**What was not found, in any protocol: the failure constants.** Delamination
rates, detachment rates, chip rupture per cycle, bleomycin mortality,
contamination over a 10-day culture. Effect sizes and precisions are reported;
what the assay does when it goes wrong is not.

That asymmetry is the survivorship argument the whole project rests on, and
completing this calibration converts it from an assertion into a measurement:
*n* constants findable, *m* not, and a pattern in which ones.

### 6.2 Why Paperclip is the right instrument

Not a hypothetical integration — the need was demonstrated above. Paperclip
indexes 11M+ papers in **full text**, and two of its five tools match the task:

| Tool | Use here |
|---|---|
| `grep` | Regex across full texts, sub-second via trigram index. Searches for the *shape* of a number — "mortality" near "%" near "bleomycin" — rather than hoping an abstract mentions it |
| `map` | ⚠️ **Not available — corrected 2026-08-16.** Gated to GXL testers; it errors on this account. The plan assumed `map` would do the bulk extraction, and it cannot. `grep` carries it instead, which §6.3 argues is the better tool regardless |

Also `search` (hybrid BM25 + vector), `lookup` (DOI/PMID metadata), `sql`
(read-only over the documents table).

Each of the six protocols already carries a `paperclip_query`, written when the
scaffolds were built. They are the shopping list; nothing new needs designing.

### 6.3 Access — ~~user action required~~ **DONE 2026-08-15, verified 2026-08-16**

> ✅ **The credential exists and works.** `paperclip` is on `PATH`,
> `PaperclipSource.available` returns True, and `refute search --key
> bleomycin_lung` returns real hits from PMC. This section stayed on the
> pre-flight list as the last open owner action; it is closed.
>
> **What running it changed, which is the part worth keeping.** The published
> contract was wrong in three places, and only having a key found them:
> `search` **requires** `-s/--source` and errors without it; `--json` is accepted
> and silently ignored, so the output is human text and not the JSON shape the
> parser originally assumed; and `map` — the tool §6.2 below expects to do the
> bulk extraction — is **gated to GXL testers and errors on this account**.
> `grep` is not gated and is the better instrument anyway: a failure rate is
> easier to find by its shape than by its topic. See the comment above
> `DEFAULT_SOURCES` in `assays/sources.py`.
>
> **What it did not change.** A working source is not a calibration.
> `refute calibrate` still replays the recorded findings and says so in its own
> header. Live evidence comes from `refute search`.

The instructions are kept below because they are still how the next person gets
a key. Self-serve, not gated to the hackathon. Per the standing rule, **the
credential is created and exported by the user, never written on their behalf**:

```bash
# either — OAuth, no key handling
paperclip login
# or — key from paperclip.gxl.ai/keys
export PAPERCLIP_API_KEY='gxl_...'
```

Install is `curl -fsSL https://paperclip.gxl.ai/install.sh | bash`, which pipes a
remote script to the shell; downloading and reading it first is the cautious
alternative. There is also an MCP endpoint at `https://paperclip.gxl.ai/mcp`
using an `X-API-Key` header, if calling it as a tool is preferable to shelling
out.

### 6.4 The harness to build (does not need the credential)

✅ **All four built** (§7.1 item 1). Item 3's taxonomy has since gained a sixth
reason, `NOT_SUPPLIED` — see `HANDOFF.md` §2a for why that was a correction and
not an addition. Kept as written because it is the specification the harness was
built against.

1. **Pluggable calibration source.** `assays/sources.py` — an interface with
   Paperclip and PubMed backends, so the protocol's existing `paperclip_query`
   routes to whichever is available. Buildable and testable offline against
   canned responses.
2. **Record what PubMed already gave**, with DOI and provenance, in
   `assays/literature.py`. Tag `LITERATURE`, never `MEASURED`.
3. **Blocked-reason taxonomy** on each unfilled constant, which is the actual
   scientific output:
   - `NOT_REPORTED` — nobody publishes it (the survivorship class)
   - `UNITS_MISMATCH` — literature reports a different quantity (traction
     *stress* in pN/µm, where the protocol needs strain *energy* in pJ/cell)
   - `ASSAY_SPECIFIC` — instrument-relative, not transferable (deposition
     baselines in arbitrary MFI units)
   - `CONTEXT_DEPENDENT` — the constant is ill-posed as a scalar. Marinković
     et al. 2012, [10.1152/ajplung.00108.2012](https://doi.org/10.1152/ajplung.00108.2012),
     show TGF-β1 raises traction on stiff substrates but **not** at
     physiological stiffness — so `tgfb_fold_change` for `traction_force` cannot
     be one number without also specifying substrate modulus
4. **A `calibrate` CLI subcommand** reporting, per protocol, constants filled /
   blocked and the reason split.

### 6.5 Expected outcome — state this before running it

Most of the six will **remain SCAFFOLD**, and that is the correct result rather
than a shortfall. The prediction, recorded in advance so it can be wrong:

- Effect sizes and CVs: mostly findable
- Failure and attrition rates: mostly not
- `bleomycin_lung` is the most likely to calibrate fully, because animal welfare
  reporting forces mortality into the record — the one place the literature is
  obliged to publish its failures
- `fibrosis_on_chip` is the least likely: device failure rates are commercially
  sensitive and n per condition is rarely stated

**Outcome, 2026-08-16, all six scaffolds swept.** The prediction was
directionally right and specifically wrong in one place worth recording rather
than glossing over. The asymmetry holds as a strong tendency, not an absolute:
of the failure/attrition constants across all six scaffolds, four were
recovered rather than zero — `mortality_by_day14` (`bleomycin_lung`, exactly
as predicted — welfare reporting), `p_seeding_failure` (`fibrosis_on_chip`,
the scaffold predicted *least* likely to calibrate, from a stated QC yield
fraction), and `modulus_drift_pct_per_day` plus `drift_depends_on_nominal`
(`stiffness_drift`, from a 42-day rheology time course, Scott 2020,
10.1002/adhm.201901593). `tests/test_calibration_harness.py::
test_the_asymmetry_holds_in_the_current_record` pins the four by name.

The `stiffness_drift` result carries a second finding: the paper that supplied
the drift rate also states the drift depends on the presence of encapsulated
cells, which — if it transfers from that paper's 3D degradable PEG geometry to
this scaffold's 2D polyacrylamide — would mean `stiffness_drift`'s hazard is
coupled to the measured phenotype rather than driven only by time and medium
composition as `HazardSpec` currently declares. Not acted on; flagged in
`refute/assays/findings/stiffness_drift.py` for a human call, because it
crosses material and geometry and should not be absorbed silently.

So the calibration run *is* a result about the literature, and the interesting
part is not that the asymmetry held — it mostly did — but the three specific,
checkable places it did not.

### 6.6 How this scales — tier cases by defect, not by domain

Added 2026-08-10, answering the strongest objection to the whole project:
*hand-crafting a mechanistic twin per case does not scale.* Correct as stated.
The response is not to build twins faster but to notice that **most cases do not
need one**, and to say which do.

§6's own finding is why. *What the assay measures: 2/9 recovered · how the assay
breaks: 0/10.* Zero. Every mechanistic twin needs somebody's unpublished plate,
because the literature does not record how assays fail. That is not a
scaling obstacle to engineer around — it is the finding, and it is the argument
for a contribution format rather than a scraper.

| Tier | Encodes | Needs a mechanistic twin? | Calibration cost |
|---|---|---|---|
| **0** | Underpowering, or infeasibility at the available scale | **No** — arithmetic. Within-arm variance, `Z_80_POWER`, `PLATE_WELLS` | A published effect size and a variance estimate |
| **1** | One dominant failure mechanism coupled to the phenotype | Yes, but a small one: one hazard model plus one readout curve | Someone's raw data. This is what `fibrin_contracture` cost |
| **2** | Interacting failure modes | Yes, and genuinely hard | Not reachable yet |

Three consequences worth acting on:

- **Tier 0 is where volume comes from.** `score.py` already runs a tier-0-only
  path — the `infeasible_as_scoped` branch needs no mechanism at all, and it
  produced the headline verdict (*no design on one plate can answer the
  question*). A tier-0 case is a power model and a citation.
- **The six SCAFFOLDs are tier-1 *candidates*, and the registry already says so.**
  `runnable()` / `scaffolds()` splits on exactly this line, and
  `require_runnable()` is the gate. Six data points for the tiering argument, not
  zero.
- **`out_of_twin_scope` is the tier-2 backlog.** Every design refused for
  proposing something unmodelled is a recorded instance of a mechanism no current
  twin covers. The refusals accumulate into the list of what to build next —
  which makes the fail-closed guard a *source* of dataset signal rather than only
  a safety valve.

**The claim to make, and its limit.** Tiering makes the corpus reachable without
pretending calibration is cheap: many tier-0 cases, few tier-1 anchors, tier 2
honestly empty. What it does *not* do is make a second mechanistic twin cheaper.
It says that most of a useful benchmark does not need one — and that where a
twin genuinely is required, the honest answer is that somebody has to contribute
data that was never published.

---

## 7. Run sheet — 15–16 Aug 2026

The event supplies three things unobtainable at home: Paperclip at corpus
scale, researchers from Arc and the Biohub to argue with, and judges. Anything
needing none of those should be finished before boarding.

### 7.1 Pre-flight (by 14 Aug)

**Closed 2026-08-16.** All six items are done; item 2 was the last one and it was
the only one that needed anybody other than the author.

| # | Item | Why it cannot wait |
|---|---|---|
| 1 | Calibration harness — `evidence.py`, `sources.py`, `literature.py`, `refute calibrate` | ✅ done. Paperclip is now a credential away, not a build |
| 2 | **Paperclip credential, and the six queries run once** | ✅ **DONE 2026-08-15, verified 2026-08-16.** The worry was right: `grep`/`map` did behave unlike the docs — `map` is gated and unusable, `--json` is ignored, `search` requires `-s`. `PaperclipSource.parse` was indeed written against a schema that does not exist and has been rewritten against captured real output. This was the last open owner action on the pre-flight list. See §6.3 |
| 3 | **Adversarial extraction set** — 5 designs, known specs | ✅ **done, 5/5 pass live** (`refute check-extraction`). Probes units, negation, distractor reagents, implicit knowledge, and out-of-scope recording. Extraction is no longer a possible explanation for any number here |
| 4 | **Pre-record an agent run** | ✅ **done** — `cases/exp4/runs/gpt-5.5-high.json`, committed and replayable with no network. Took three attempts and broke four things; see §10. The recording is now a test fixture |
| 5 | Decide the patent question | ✅ **DECIDED 2026-08-10: no patent.** Nothing to protect, so presenting, publishing and open-sourcing the method are all unconstrained. Do not re-open this on the day. ⚠️ This resolves *patents only* — see §5 on the data, which is a separate question |
| 6 | Baselines, so a score has a scale | ✅ done. `refute baselines` — and `EXPERT` at 9% is now the cleanest statement of the finding, with no model in the loop (§9.6) |

### 7.2 Day 1 (Sat) — build the dataset

> **Status 2026-08-16: the sweep is IN PROGRESS, not done.** Five agents are
> searching now. No result is recorded here yet, and none should be quoted until
> one is. The morning item below — credential live, queries run — is done; the
> classification is what is running.
>
> ⚠️ The afternoon item said bulk extraction via `map`. `map` is gated and
> unusable on this account (§6.3), so the sweep runs on `search` + `grep`.

**Scale past the six.** Six assays and 35 constants is a case study. Track B
asks for "the pattern no single paper could show you", which needs a corpus:
sample 50–100 fibrosis assay papers and measure the reporting asymmetry across
all of them.

> Across N papers and M constants: effect sizes recoverable in X%, precision
> estimates in Y%, **failure and attrition rates in Z%.**

The six protocols become worked examples; the sweep becomes the finding.

- **Morning** — credential live, run the queries, bulk extraction via `map`
- **Afternoon** — classify every miss into the taxonomy. The classification
  *is* the dataset. Hold the NOT_REPORTED / NOT_YET_SEARCHED line: the harness
  refuses the first without a recorded query, and that refusal is what makes
  the headline defensible
- **Evening** — wire recovered constants in; check whether any scaffold becomes
  runnable. Standing bet: `bleomycin_lung`, because welfare reporting obliges
  authors to publish deaths

### 7.3 Day 2 (Sun) — make it mean something

- **Morning** — if a second assay calibrated, run the agent loop against it.
  Does the finding replicate on an assay that is not ours? That is the
  difference between "my experiment failed" and "this generalises"
- **Midday** — package as a BenchFlow environment if time allows (§2). Twin →
  environment, `DesignSpec` → action space, `score_design` → reward
- **Afternoon** — freeze. README, rehearse, stop building

### 7.4 The demo — now one command

**`refute demo`.** Built 2026-08-10. Six beats in a fixed order, each carrying the
line to say and the computation behind it, with a pause between. Runs in ~6s of
compute; the rest is talking.

Two reasons it exists rather than a list of commands in this file. Five commands
typed live, with flags, while talking, is five chances to mistype or scroll past
the number that matters. And **the order is load-bearing**: if the agent's refusal
(beat 6) is shown before the one-plate ceiling (beat 3), the refusal reads as the
model failing rather than as the model agreeing with the simulator. A test pins
that ordering.

Each beat delegates to the same `cmd_*` function the CLI exposes, so the demo
cannot drift from what the tool does. Both degradation paths are tested: a missing
recorded run explains itself (and warns against running the agent live), and a
missing CSV says so rather than raising mid-presentation.

The beats, and why in this order:

| # | Beat | Why here |
|---|---|---|
| 1 | The real data | Opens on `6/6` vs `0/4` in the last column. Not a claim — the CSV |
| 2 | Score the as-run design | 0% power, 50% lysed, and it *refuses* to say how many wells were needed |
| 3 | **Is it the design or the apparatus?** | `EXPERT` 9%, `CEILING` 83%. The finding, with no model in the loop |
| 4 | Two separable defects | Neither fix alone is enough |
| 5 | Why it is not in the literature | The asymmetry, as a measurement |
| 6 | **What a frontier model did** | 1% lysis without the reagent, then declined — and the scorer gave that 0% until it was fixed |

`refute check-extraction` stays out of the script — it needs a key, and its result
is a sentence you can just say.

### 7.4-old The demo (superseded by `refute demo`, kept for the reasoning)

1. A real experiment that failed, with the data — 30 s
2. `refute baseline` **live** — 0% power, 50% of wells lysed. Instant, no network
3. `refute baselines` **live** — the ceiling: `EXPERT`, hand-written with full
   hindsight, reaches 9%; `CEILING`, the same design unconstrained, reaches 83%.
   **The constraint is the apparatus, not the agent.** Added 2026-08-10; this is
   now the strongest single screen in the demo, because it makes the finding
   without needing a model at all
4. `refute sweep` **live** — the two defects are separable; neither fix alone works
5. `refute calibrate` **live** — the asymmetry, in one table
6. `refute replay` **live off a recorded file** — 0% → 97% testable, still 9%
   power. Unanswerable on one plate. Re-scored against the current twin rather
   than read back, so it cannot show numbers the code no longer produces

Lead with the absence, not the extraction. Recovered constants read as
literature mining; what the literature systematically omits is a finding.

**Nothing in steps 2–6 needs a network, a key, or sponsor compute.** That now
includes the agent result, which is the step that used to be at risk. The demo
cannot die on venue infrastructure.

Keep `refute check-extraction` in reserve rather than in the script — it needs a
key, and its output is a sentence you can simply say: *5/5, so extraction is not
the explanation for any number here.*

### 7.4a The sixty-second version

The material exists across §8.3 and §1; this is the spoken order, because a
judge's first question is "what is this" and the answer must not start with
architecture.

> A real experiment failed. Anchored fibrin gels, human synovial fibroblasts,
> asking whether MSC-conditioned media blunts TGF-β-driven contraction. The gels
> dissolved before the treatment window closed — cell-mediated fibrinolysis,
> fastest in exactly the arms the comparison needed. It was never published,
> which is the point: nothing like it is in the corpus these agents learned on.
>
> I calibrated a simulator on that plate. Then I asked a frontier model to design
> the experiment, given only what was knowable beforehand. It made the same three
> mistakes — n=3, no antifibrinolytic, no reasoning about the scaffold at all.
>
> When I gave it consequences rather than corrections — *the scaffold was gone
> before your endpoint*, never *add aprotinin* — it went from 0% to 97% of runs
> yielding a testable result, in one turn. So the gap is informational, not a
> capability limit.
>
> And the honest verdict is that it still cannot answer the question, because no
> design on one 12-well plate can. I know that because I hand-wrote the best
> possible plate with full hindsight and scored it too: 9% power. Lift the plate
> limit and the same design reaches 83%.

Three properties of that script worth keeping: the failure is **real and yours**,
the model's error is **specific rather than generic**, and the strongest claim
(*the apparatus, not the agent*) is backed by a command that needs no model, no
key, and no network.

### 7.4b Who the buyer is

Asked directly — "who uses this?" — the answer is not "benchmark authors".

> Anyone about to spend three months and a five-figure budget on a plate that
> cannot answer their question. Experiment 4 cost a term of MPhil work to
> discover something a simulator says in 40 milliseconds: **you needed thirty
> wells per arm and you have three — and until you stop the gel dissolving, you
> cannot even find that out.**

The agentic-science framing is why it is a benchmark today — but the durable
version is a pre-registration check, and that is what §3 item 3 (the optimizer,
returning the *cheapest sufficient design*) turns it into.

### 7.5 Questions to have answered before they are asked

| Question | Answer |
|---|---|
| "Isn't this a virtual cell?" (Arc affiliates two of seven co-hosts) | A virtual cell predicts the biology; this models the apparatus. A perfect virtual cell still will not tell you the gel dissolves on day 7, that the most-treated arm fails first, or that segmentation noise means you needed 50 wells |
| "Why not build it in BenchFlow?" | It probably should live there. The harness was never the hard part — a reward signal that is not another model's opinion was |
| "Why not use Proto?" | Its primitives are sequence-typed (§2). The analogy is worth stating; the dependency is not worth having |
| "One plate is not a benchmark." | Correct, and stated first. The alternative on offer is zero plates. Every literature-built benchmark is trained on survivors; this is calibrated on an experiment that was never published |
| "AI just designed working viruses — why aren't you working on *that*?" | §8 |
| "Won't the agent just overfit to your equations?" | §9.1. Partly, and the scorer now says when a verdict rests on an ASSUMED constant instead of reporting the midpoint. Half the score — power — is arithmetic no agent games by finding a generous mechanism |
| "What if a design is cleverer than your twin?" | §9.2. It refuses to score rather than scoring it wrong; that was a real bug, and it failed permissively. The refusals become the list of mechanisms worth modelling next |
| "One hand-built twin per case doesn't scale." | §6.6. Conceded. Tier 0 needs no mechanism and is where volume comes from; a tier-1 anchor needs somebody's unpublished plate, which is the finding, not the obstacle |

---

## 8. The verification gap — framing, not a pivot

Added 2026-08-07, eight days out, after the Hie lab's generative-phage work
reached mainstream coverage (CNN, Axios, 6 Aug). The preprint is from Sept 2025;
the *attention* is this week. Arc co-hosts this event, so the question will be
in the room whether or not it is asked out loud.

**The result:** Evo 1 + Evo 2, fine-tuned on Microviridae and prompted with
ΦX174, produced ~300 whole-genome designs; 16 were viable phages that infect and
kill *E. coli*. Human- and animal-infecting viruses were excluded from training,
and the work was run under containment beyond the standard requirement.

**The criticism that matters** is not "they made a virus". It is the specific
one from Johns Hopkins biosecurity: existing synthetic-DNA order screening
**cannot detect sequences of this kind**. The generator moved; the verifier did
not. That is a claim about who checks the output, and it is the same claim this
project makes.

### 8.1 Why this is not a pivot

Recorded so the decision is not re-litigated on the day:

- **Wrong layer.** The gap identified is nucleotide-similarity screening. The
  twin is a mechanistic model of a fibrin gel. There is no bridge — the same
  reasoning that retired the Proto integration in §2.
- **It would require inventing ground truth.** There is no calibration set for
  a biosecurity classifier reachable in eight days. Building one would mean
  switching off `UncalibratedAssayError` first — i.e. abandoning §6's central
  correctness property to build the thing §6 exists to criticise.
- **Well-resourced incumbents.** SecureDNA, IBBIS, NTI\|bio, the IGSC screening
  consortium. A two-day build loses, and loses in public.
- **It reads badly.** A hastily-assembled biosecurity project at Arc's own
  hackathon, days after their work drew criticism, is either opportunism or an
  implied rebuke of the hosts. The framing below is neither.

### 8.2 What is already true and should be said

`refute`'s architecture is a position on exactly this question, and it was
taken before the news:

| Property | Where it lives | Why it is the point |
|---|---|---|
| The generator is never its own verifier | "the LLM extracts, the simulator judges" (§1) | The separation that failed in the phage case |
| It fails closed | `UncalibratedAssayError`, tested | Refuses to score what it cannot vouch for, instead of returning a confident number |
| Silence is not evidence | `BlockedReason.is_a_claim_about_the_literature` | `NOT_REPORTED` requires a recorded query, or it raises |
| "No" is a valid verdict | the infeasibility diagnosis in `score.py` | *the question cannot be answered at this scale — a legitimate answer, not a failure* |

A verification layer that cannot decline to vouch for something is not one.

### 8.3 The line worth having ready

> The conversation is about **malicious** AI-designed biology. The far more
> common failure is **incompetent** AI-designed biology — an agent proposing an
> experiment that cannot answer its own question, and nobody catching it because
> there is no simulator in the loop. That failure is measurable, and this
> measures it against primary data.

The headline result is the evidence, unchanged: gpt-5.5 reproduced both defects
of a real experiment; consequence-feedback took it 0% → 97% testable; and the
honest verdict was still that **no design available on one plate can answer the
question.** A capable model confidently proposed an experiment that could not
work — the same shape as the phage story, at a scale where the answer is
checkable.

### 8.4 The asymmetry, read a second way

§6's finding — *what the assay measures: 2/9 recovered · how the assay breaks:
0/10* — is a biosecurity-shaped result in disguise. The literature records
capability and omits failure modes. That is precisely why verification lagged
generation: the corpus training everyone's intuitions about what goes wrong is
thin by construction. Worth one sentence in the Track B pitch; it costs nothing
and it generalises the finding past fibrosis assays.

### 8.5 One thing to say about this project's own errors

Both scorer bugs found on 2026-08-05 were **false negatives** — the harness
called a design broken when it was not. A verifier wrong in the permissive
direction is the dangerous one. Ours was wrong in the conservative direction,
which is why the tests missed it and why it was safe to ship. Name the
asymmetry rather than hiding the bugs; it is the more credible position.

**Scope: nothing in §8 changes code.** Track B, §6 and §7 are unaffected.

---

## 9. Hardening the scorer — answers to three critiques

Built 2026-08-10 in response to three objections raised against the design, all
of which landed. Recorded here because two of them are the sort of thing a judge
will ask, and the answer is better as a property of the code than as a rebuttal.

### 9.1 Goodhart — the twin's equations become the target

**The objection.** An agent iterating against feedback optimises the equations in
`twin.py`, not biology. It will learn to throw aprotinin at the problem.

**The sharp form, which is worse.** `DesignSpec.antifibrinolytic` is a **`bool`**,
and flipping it multiplies the Weibull scale by `aprotinin_hazard_scale` — a
constant `calibration.py` tags **ASSUMED, not measured**. One bit, uncalibrated
effect size, unlocks the entire failure mode the case is built around. That is a
cheat code in the input schema.

**Two things that already limited it.** The brief is pre-registration only and
never says "fibrinolysis"; feedback reports consequences, never corrections. And
half the score — power — is arithmetic no agent games by finding a generous
corner of a mechanism. The headline finding came entirely from that half.

**What changed.** `score_design` now re-scores at both ends of every ASSUMED
constant a design actually reaches, and sets
`verdict_sensitive_to_assumption` when the categorical verdict does not survive
the span. The point estimate is still reported; it is reported with a warning
above it. Costs nothing for designs that never touch an assumed constant, which
is most of them.

**The limit, stated.** This covers `aprotinin_hazard_scale`, the only ASSUMED
constant a design reaches directly. The FITTED lysis shape and scale are not
swept — §3 item 7 remains open. And Goodhart applies in full the moment the
optimizer in §3 item 3 lands: a benchmark is not an environment, but a search
over designs is.

### 9.2 Out-of-distribution designs — the permissive failure

**The objection.** A clever design that sidesteps lysis by changing the matrix
will be misscored, because the physics are not in `twin.py`.

**Right, and the behaviour was worse than misscoring.** `DesignSpec` had no field
for a matrix change, and the extractor is correctly instructed not to improve a
design — so the feature was silently **dropped**, and the twin returned a
confident number for a plate nobody proposed. Unlike both 2026-08-05 bugs, that
fails in the **permissive** direction, the one §8.5 names as dangerous. It was a
correctness bug, not a known limit.

**What changed.** `out_of_twin_scope: list[str]` on `DesignSpec`, the extractor
instructed to populate it, and `OutOfTwinScopeError` raised rather than a score
returned. The message says *this is a limit of the twin, not a defect in the
design*, because the wording is what stops the refusal teaching the wrong lesson.
Wired through every surface: the library raises, `RefuteEnv` ends the episode
unscored (an RL loop cannot take an exception mid-episode), the API returns a
`422` carrying `error: "out_of_twin_scope"` to distinguish it from a schema
`422`, and the CLI exits `2` printing no score at all.

**The dividend.** Refusals accumulate into a record of mechanisms no twin covers
— the tier-2 backlog in §6.6. The guard is a source of dataset signal, not only a
safety valve.

### 9.3 Scaling the twins

Answered in **§6.6**: tier cases by the defect they encode. Tier 0 needs no
mechanism and is where volume comes from; tier 1 needs somebody's unpublished
plate; tier 2 is honestly empty. The objection is conceded rather than argued —
a second mechanistic twin is not cheaper, most of a useful benchmark just does
not need one.

### 9.4 The interface question — agent, API, or both

All three, now built, and the ordering was deliberate: the layer that needs no
new infrastructure first.

| Surface | What it is | Keys on server |
|---|---|---|
| `RefuteEnv` | `reset`/`step`; `DesignSpec` is the action, `power` the reward | none — a `DesignSpec` action calls no model |
| `Agent` Protocol | two methods, `propose`/`revise`; `ChatModelAgent` is the reference | n/a |
| `POST /score` | pure simulation over HTTP | none |
| `POST /score/text` | extract prose, then score | extractor only |
| `POST /run` | the full loop | **yes — 403 unless `REFUTE_ENABLE_RUN=1`** |

Two decisions worth defending out loud:

- **The reward is `power` alone, not a composite.** A composite would bury a
  scientific judgement — how much a lost baseline is worth against a dissolved
  scaffold — inside a constant nothing in Experiment 4 constrains. The full score
  is in `info["design_score"]`; a different objective is the caller's to build.
- **`ChatModelAgent` is deliberately thin.** A richer scaffold would raise scores
  and make the result a measurement of the scaffold rather than of the model —
  the same confound the extractor is held constant to avoid.

**One bug found at the wire boundary.** `DesignScore` reports "not estimable" as
`float("nan")` and `-1`. `NaN` is not valid JSON, and a client not knowing the
convention would read `-1` as a real well count. Both now serialise as `null`.
The same investigation exposed that `infeasible_as_scoped` is `False` in two
opposite situations — a design that fits one plate, and one too destroyed to
estimate — so `feasibility` is now tri-state: `feasible` / `infeasible` /
`unestimable`.

### 9.5 The estimator bug the baselines set found

Worth recording in full, because it is the third scorer bug in this project and
the first that was **not** conservative.

**How it surfaced.** `refute baselines` scored `CEILING` — the expert design with
the plate limit lifted, n=60 — and reported **82% power alongside "8272 wells per
arm needed"**. Those cannot both be true: a design with more replicates than it
needs has high power by definition. The contradiction was the only symptom.

**The cause.** A per-well endpoint ratio is a *quotient*. Its distribution has a
heavy right tail, because a baseline that happens to be measured small inflates
the ratio without limit. `_pooled_spread` used `np.var`, which gives every point
equal leverage — so **20 wells in 33,829**, worst case a measured baseline of
0.005 giving a ratio of **847**, moved the pooled within-arm SD from **0.21 to
4.61**. That SD is the denominator of both `min_detectable_ratio_diff` and
`replicates_needed`, so both were roughly doubled.

Invisible until now for a structural reason: the tail is ~0.06% of wells, so a
12-well design samples it about once and a 120-well design samples it ten times
and hits a worse one. Every design scored before the baselines set existed was
too small to expose it.

**The fix I got wrong first.** My initial guard thresholded the denominator at 3×
measurement noise (5.1 fill-points) — the conventional detection threshold. That
was wrong on this apparatus: the TGF-β arms plateau near 10.8 with a lognormal
well effect, so a legitimately *strong* contractor sits close enough to 5.1 to be
clipped. It would have discarded the largest responders preferentially and biased
the estimate toward the null — **the exact failure mode `assays/tier1.py`
documents for traction force microscopy, reintroduced into the twin by its own
guard.** Caught by measuring how many wells it discarded (3%, not the ~20
expected) before trusting it.

**The fix.** Two parts. A physical floor of 1% well area, far below any plateau
the model produces, removing only division artifacts; and — the real defence —
robust estimation in `_pooled_spread`: MAD for the spread, median for the centre.
On clean data MAD×1.4826 reproduces the ordinary SD, so nothing changes except
where the naive estimate was being driven by its tail.

**What moved.** Power, testability and lysis: **unchanged** — those come from
per-plate t-tests, not the pooled spread. Required replication roughly halved:
expert **44 → 29**, ceiling **8272 → 32** (and 32 < 60, so the contradiction is
gone). Every qualitative conclusion survives.

**And then a second, worse defect underneath it.** Checking whether the fixed
number was *stable* — rather than assuming a plausible figure was correct —
showed it was not:

```
as_run    n_sims=100  reps= 75 | 130     (two seeds)
          n_sims=400  reps= 20 |  12
          n_sims=800  reps= 17 |  38     <- not converging
expert    n_sims=800  reps= 29 |  33     <- stable
```

The effect gap is estimated from wells that **survived to the endpoint**, and
fibrinolysis takes the most contractile wells first — so for a design losing half
its wells, the survivors are systematically missing the largest effects. The
estimate is survivorship-biased, and no amount of simulation fixes it because the
bias is in the sample, not the noise.

**That is this project's own thesis, pointed at its own scorer.** The response is
the one `UncalibratedAssayError` already established: refuse the number.
`MAX_LYSIS_FOR_EFFECT_ESTIMATE = 0.2` — above 20% loss, `replicates_needed` and
`min_detectable_ratio_diff` return unestimable with a diagnosis explaining why,
instead of a confident figure derived from survivors.

Consequence for the pitch: **the as-run design's required replication is now
`unestimable`, and the quotable number is `EXPERT`'s ~29** (stable within ±5).
That is a better claim anyway — it says *even with the scaffold protected you
needed ten times the wells you had*, which is the finding, rather than a figure
computed from the wreckage.

**Two lessons worth saying out loud.**

1. **The direction was permissive.** The scorer over-stated how many wells an
   experiment needs — it would have told a researcher a feasible experiment was
   infeasible. Unlike the two 2026-08-05 bugs, that is not the safe direction.
2. **A number you cannot recompute is a number you can only quote.** The first
   live run's revised design was never serialised, so its `~57 wells/arm` could
   not be recalculated — it became unquotable rather than merely stale. That is
   what `refute.record` and `refute replay` now exist to prevent, and it is the
   concrete cost of §7.1 item 4 having stayed open.

### 9.6 Baselines — what "97% testable" is 97% of

Built 2026-08-10. `0% → 97%` had no scale attached: the only comparator in the
repo was the design that scored zero, so any agent looked good. Four hand-written
references now supply one, and none of them is model output.

```
  design  wells   power  testable   lysed  n/arm needed      verdict
  as_run     12     0%        0%     50%             -  unestimable
   naive     12     0%        0%     50%             -  unestimable
  expert     12     9%       98%      0%            29   infeasible
 ceiling    120    83%      100%      0%            32   infeasible
```

`EXPERT` is the load-bearing row. It is written with hindsight the agent is
denied — narrow to the headline contrast, spend all twelve wells on it, aprotinin
in the mix, endpoint inside the observed survival window, sample densely before
24 h, normalise per well. **It reaches 9%.** `CEILING` is the identical design
with the plate limit lifted and reaches **83%**, which is what rules out "the
design is bad" and leaves "one plate is not enough".

Three consequences:

- **The finding no longer depends on an agent run.** `refute baselines` states it
  with no model, no key and no network — which is why it is now step 3 of the demo
  (§7.4) rather than an appendix.
- **The correct comparison is against `EXPERT`, not `AS_RUN`.** Say this before
  anyone asks, because "0% → 97%" invites the weaker reading. The agent's revised
  design converged on the same shape as `EXPERT` — 2 arms, n=6, aprotinin, Day 7 —
  and landed at the same 9% power. *The agent matched a hand-written expert
  design*, which is a stronger and more specific claim than the delta.
- **`AS_RUN` and `NAIVE` are `unestimable`, not merely bad.** Both lose half their
  wells, so the twin refuses to say what they would need — the surviving sample is
  biased against the effect (§9.5). That is a distinct verdict from `infeasible`,
  and it is why `feasibility` had to become tri-state (§9.4). It also means the
  right sequencing advice falls out of the scorer rather than being asserted:
  *fix the scaffold loss first; the replication requirement is only answerable
  once wells survive.*

`sanity_check()` guards the properties the set exists to have — `EXPERT` fits
exactly one plate, `CEILING` must not, `NAIVE` must be worse on every axis the
twin can see. A baseline set that silently drifted would make every comparison
against it meaningless without any test failing.

---

## 10. The first recorded run — and the four things it broke

2026-08-10. `refute run --agent openai:gpt-5.5 --agent-effort high --record`.
Three attempts were needed; two of the failures were mine. Recorded in full
because the run is now a committed fixture
(`cases/exp4/runs/gpt-5.5-high.json`) and because §10.3 changes what this
project claims.

### 10.1 Attempt 1 — the fail-closed guard was a fail-always guard

Refused a score. The extractor had listed seven items in `out_of_twin_scope`,
including *"primary human synovial fibroblasts seeded in anchored fibrin
constructs"* and *"projected gel area measured in mm²"* — **the twin's own assay
and the twin's own readout.** Also the formulation, the media, the medium change,
the analysis plan and the exclusion criteria.

It did exactly what §9.2's field description said: *"anything the fields above
cannot represent."* Every real design carries protocol detail no schema has a slot
for, so the guard fired on everything.

The field is now scoped to **substitutions that change the apparatus being
simulated** — a non-fibrin matrix, a readout that is not gel area, a different
vessel, an agent that alters degradation without being an antifibrinolytic — with
an explicit negative list and the line *a design that merely specifies the fibrin
assay in detail belongs here NOT AT ALL.*

**The lesson, and it is not a small one.** §9.2 had a true-positive test (collagen
is refused) and no false-positive test. With one side pinned, *refuse everything*
passes the suite — maximally safe, completely useless. A fail-closed guard needs
both sides or it is not tested. The regression case (`detailed_but_in_scope`) uses
the real prose that broke it.

Only findable by running a real model: every hand-written fixture was terse, and
nothing resembled the dense prose gpt-5.5 produces at high reasoning effort. The
fixtures were testing a distribution the system never sees.

### 10.2 Attempt 2 — the guard was right and the brief was wrong

Refused again, but with **one** item, not seven: *"gel width narrowing instead of
gel area."* A genuine readout substitution — the twin's measurement model is
calibrated for area segmentation specifically (±2–3 fill-points on `fill_pct`),
and it cannot simulate a width readout.

So the refusal was correct and the **brief** was at fault. It constrained the
plate count and the camera but never said what the apparatus *quantifies*, so the
design was rejected for using the equipment differently than the twin assumes.
That measures conformance to an unstated convention, not design quality.

One line added to `AVAILABLE`: projected gel area as a percentage of well area,
the only quantity the setup measures. **This leaks nothing** — it is the standard
readout of the Roberts 2022 model and a property of the equipment, in the same
class as "ONE 12-well plate". Neither defect the agent must rediscover is hinted
at by naming the units.

`EXPERIMENT_4_BRIEF` had **no test at all**, which is alarming for the single
assumption the whole benchmark rests on. It is now pinned both ways: it must name
the readout and the plate limit, and must not contain `fibrinolysis`,
`aprotinin`, `tranexamic`, `plasmin`, `lysis`, `dissolv`, `half-time` or `5.8`.

### 10.3 Attempt 3 — the agent declined, and the scorer punished it

Round 1 scored, and did something neither Experiment 4 nor `EXPERT` did:

| | power | testable | lysed | n/arm |
|---|---|---|---|---|
| as-run | 0% | 0% | 50% | unestimable |
| `EXPERT` (hand-written, full hindsight) | 9% | 98% | 0% | ~29 |
| **gpt-5.5 round 1** | **2%** | 58% | **1%** | ~50 |

It drove lysis to **1% with no antifibrinolytic at all**, by treating at 1 h and
ending at 72 h — finishing before the fibrinolysis window opens (Weibull scale
183.7 h) rather than spending a reagent to survive to 168 h. A strategy neither
baseline used, and a *cleaner* isolation of the second defect than my own
`EXPERT`: with scaffold loss gone, 2% power is measurement precision alone.

It also found a better normalisation than Experiment 4 used. Baselining at 1 h,
when the gel is still near-full, gives a within-arm ratio SD of **~0.03** against
`EXPERT`'s ~0.19 — a large denominator dilutes the measurement noise. The effect
gap in those units shrinks too, so it still needs tens of wells, but the design is
genuinely more precise per well.

**Then round 2 declined to run the experiment:**

> *"No-go for the biological question. There is no one-12-well-plate design that
> will actually answer whether MSC-conditioned medium suppresses TGF-β1-driven
> contraction... Total required scale: approximately 130–140 cast wells, not 12."*

That is **this project's own headline finding, reached independently** — and
`score.py`'s own diagnosis text already said *"to report that the question cannot
be answered at this scale — the last is a legitimate answer, not a failure."*

**The scorer gave it 0% power.** The worst score available. The extraction was
correct (`conditions: []` faithfully records "no plate should be cast"); the
scorer was wrong. It was penalising, maximally, the exact epistemic behaviour the
benchmark exists to reward — and simulating an empty plate to do it.

Fixed: `DesignSpec.assigns_wells`, `DesignScore.declined`, `feasibility ==
"declined"`, nothing simulated, and a `summary()` that refuses to print power at
all rather than showing a placeholder that reads as data. `feedback_for_agent`
no longer tells a correct refusal that it recovered 0% of runs — which would push
the agent to propose a plate it had just correctly argued cannot work. The CLI
and `replay` print an OUTCOME block instead of a `2% -> 0%` delta, because those
rounds are not on the same scale.

**What is deliberately NOT resolved.** A declined design still carries reward
`0.0` in `RefuteEnv`, flagged by `info["declined"]`. What a correct refusal is
worth against a 9% plate is a research question, not a coding one, and inventing a
number would be exactly the kind of invented ground truth this project objects to.
So it is reported and left open — **and a caller optimising on reward alone will
penalise correct refusals.** That is stated in the code, not buried here.

### 10.4 What this does to the pitch

Stronger, and different from what §0 records.

The old story was *0% → 97% testable*. The new one is better:

> A frontier model reproduced the experiment's defects, then — given consequences
> rather than corrections — worked out a strategy neither the original researcher
> nor I had used, got the scaffold failure to 1% without the reagent, and then
> **refused to run the experiment**, correctly, for the same reason the simulator
> gives. My own benchmark scored that refusal zero until I fixed it.

That last clause is the most credible thing in the project. The demo should show
it: `refute replay` prints the OUTCOME block, and `refute baselines` establishes
that declining was right.

### 10.5 One number not to quote precisely

`replicates_needed` for a design far from powered is **order-of-magnitude only**.
For the agent's round 1 it ranges **28–79** across seeds and simulation counts and
does not converge at `n_sims=1600`, while `power` (2%) and `testable_rate` (~60%)
are stable to a point or two. It scales as (SD/gap)², so a 20% error in the gap
becomes 44% in the requirement.

Not a defect — the informative content is *tens of wells, not three* — but say
"tens of wells" or "~50", never "49". Pinned by a test so it is not mistaken for
precision later.

---

## 11. The harness, made a variable

Built 2026-08-10. Reverses a position taken earlier in this file, so the reasoning
matters more than the code.

**What §9.4 said.** `ChatModelAgent` is deliberately thin — one completion per turn
— because "a richer scaffold would raise scores and make the result a measurement
of the scaffold rather than of the model." That is true.

**Why it was still wrong.** The conclusion drawn from it was to keep the harness
thin *and singular*, which does not remove the confound — it hides it. A single
harness is not a controlled variable, it is an **unreported** one. Every number in
this project has silently been a (model × harness) result while being quoted as a
model result.

**The fix is the same discipline used for the extractor**, applied one level up:
name the thing, hold it constant when comparing models, and vary it deliberately
when that is the question. `refute/harness.py` provides three, each declaring what
it adds, and both the CLI and `RecordedRun` now print and store which was used.

| harness | calls/turn | adds |
|---|---|---|
| `single-shot` | 1 | nothing — the control, identical to `ChatModelAgent` |
| `self-critique` | 3 | draft → hostile self-review → final |
| `checklist` | 1 | a forced quantitative pre-design worksheet |

### 11.1 The boundary that must not move

**No harness is given the twin.** A harness may restructure the model's own
reasoning; it may not consult the scorer. Handing it the simulator turns the
benchmark into a search against `twin.py` — §9.1's Goodhart failure, arriving
through the harness rather than through the optimizer.

**No harness prompt may name the answers.** This is easier to violate than the
brief, because a "helpful" checklist item is exactly where a hint goes. A test
asserts that neither `CRITIQUE_PROMPT` nor `CHECKLIST_PROMPT` contains
fibrinolysis, an antifibrinolytic, a well count, or even the word *fibrin* — they
ask only the questions a methods reviewer asks of any experiment.

`self-critique` also does **not** add a review pass on the revision turn: the
simulator's feedback already is an external critique, and a stronger one. Stacking
self-review on top would make "responded to consequences" and "reviewed itself"
indistinguishable.

### 11.2 The experiment this makes possible

Sharper than "can scores be raised". Experiment 4's central defect was n=3 — a
**computable** error, not an exotic one.

- If `checklist` fixes it, the deficiency was an **un-done calculation**: the model
  always knew how, and nobody made it stop and multiply.
- If `checklist` does *not* fix it, the deficiency is **knowledge of what goes
  wrong**, which is precisely the survivorship claim this project rests on.

Either outcome is a result, and the single-shot harness cannot distinguish them.
That is the strongest reason to have built this rather than a UI.

**Not yet run** — three harnesses × one model is three paid runs, and §10 showed
what happens when those are spent before the checks are in place. `refute run
--harness self-critique` is one command when there is budget for it. The recorded
`gpt-5.5-high.json` is `single-shot`, correctly labelled, so it stays comparable.

### 11.3 What was NOT built, and why

**Tool use.** A function-calling harness with a power calculator was the obvious
next step and is deliberately absent. The tool a design most needs is a variance
estimate, and the only calibrated variance in this repo is the twin's — so a power
tool is the twin wearing a hat. Building it would cross §11.1's boundary while
looking like a capability improvement. If it is built later, the variance must come
from the agent's own stated assumptions, not from `calibration.py`.

---

## 12. Where this goes next — two leads, one strong

Recorded 2026-08-15. Neither is built. Both came out of asking how this scales
past one assay, and the second is the better idea in the project.

### 12.1 The coupled/exogenous split IS the scaling rule

§6.6 tiers cases by the defect they encode. The sharper cut is *what drives the
dropout*, and `tests/test_hazard_classes.py` now pins it:

| dropout driven by | scaffolds | needs a twin? |
|---|---|---|
| the phenotype being measured | traction_force, scar_in_a_jar, cell_derived_matrix, bleomycin_lung | **yes** |
| an applied parameter or elapsed time | fibrosis_on_chip, stiffness_drift | **no** |

Exogenous dropout is roughly non-differential: it is set identically across arms,
so it costs you *n* and nothing else. Tier 0 already prices lost *n* — or will,
once it accepts an expected attrition rate and reports an effective *n* rather
than taking the designed *n* as delivered. That is a small addition and it is the
honest way to demote those two.

Only phenotype-coupled dropout needs tier 1, because only there are the survivors
a biased sample of the units you cared about. So the scaling claim for fibrosis
is: **two of six demote to tier 0; four need constants nobody publishes.**

### 12.2 CONSORT — the strong lead

The general name for the coupled case already exists: **informative censoring**,
or MNAR. This project's contribution is not a new statistical category but a
*mechanistic, calibrated, refusable* instance of one, against the generic
delta-adjustment sensitivity analysis the field does instead. Naming it that way
is what makes it portable, because the shape recurs everywhere — sicker patients
withdraw from trials, bad surgical results are lost to follow-up, partial
verification bias in diagnostics, informative observation times in EHR cohorts.

**And here is the asymmetry worth building on.** Preclinical papers publish the
readout and hide the failures — that is §6's 0/10. Clinical trials publish the
failures, because **CONSORT mandates a flow diagram**: enrolled, allocated, lost
to follow-up with reasons, analysed — *per arm*.

Per-arm attrition with reasons is exactly the format `cases/TEMPLATE/` asks a
contributor for, and exactly what §6 could not find in bench literature. It is
mandated, structured, and present in thousands of papers.

So, counterintuitively: **tier 1 scales more easily into clinical trials than
into the bench assays it was born in.** The input that is unobtainable in vitro
is a reporting requirement in RCTs.

It also supplies the coupling the same way Experiment 4 did. Per-patient coupling
is circular — a patient who dropped out has no outcome — but *differential*
dropout between arms is visible at arm level, and arm membership stands in for
the phenotype. That is the identical trick, one domain up.

**Probed against the live corpus, 2026-08-15.** Partially confirmed, and the
decisive number is still missing.

*Established:*

- Paperclip indexes trial records with a **first-class `Participant_flow`
  section**, line-numbered and therefore citable in the same way a paper is.
  This is better than parsing a PDF diagram — it is already sectioned text.
- Per-arm allocation appears in prose and is directly readable, e.g.
  `L494: A total of 502 screened participants were randomly assigned to receive
  either AVT05 (251 participants) or EU-Simponi (251 participants).`
- The path form is `/trials/tri_<id>/sections/<Name>.lines`. A `/papers/<uuid>/`
  path taken from grep output does **not** resolve, and `cat` on it fails.

*Not established, and the reason this stays a lead rather than a plan:*

- **Prevalence is unmeasured.** `grep -c` returns a capped, approximate figure,
  so "how many trial records carry a usable flow section" is still unknown. That
  single number decides whether this is a research programme or a footnote.
- The disposition detail is frequently referenced as **"Figure 6"** — so the
  per-arm *reasons* for loss may be an image even when the allocation prose is
  text. Allocation without reasons gives a rate and not a mechanism, which is
  precisely the half tier 1 already has trouble with.
- It unblocks the *data*, not the *modelling*. A twin still has to exist per
  clinical domain, and nothing here says that is cheap.

*Contract note for whoever picks this up:* `grep --from <id>` appears to be
ignored — a scoped grep over a 3-paper result set returned matches across 50
papers. Scope by path (`/trials/`) rather than trusting `--from`.

The next step is unchanged and still small: sample twenty records with a
`Participant_flow` section and count how many give per-arm loss **with reasons**
as text rather than as a figure.

### 12.4 Build order for the event — sweep first, then build

Written 2026-08-15, before the hack starts. The order matters: **the sweep
decides what tier 1 can contain**, so building tier 1 before running it means
guessing at which assays are reachable. Everything below is sequenced so the
data arrives before the decision it informs.

#### Phase 1 — the sweep (do this first, ~1 hour, no code)

> **Status 2026-08-16: IN PROGRESS.** Five agents are searching. Neither of the
> two numbers below exists yet. Do not present the sweep as a result until it
> is one.

Run `refute search` and `refute infer` across the ~~five~~ **six uncalibrated
scaffolds** — *corrected 2026-08-16: there are six, and the 35 constants below
are their sum (6 + 7 + 6 + 6 + 6 + 4). The "four" in Phase 3 is a different and
correct count: the phenotype-coupled subset.* For every one of the 35 missing
constants, record one of:

| outcome | meaning |
|---|---|
| `FOUND` | stated in full text, with the sentence |
| `INFERRED` | recoverable by arithmetic (§11 rules), with the derivation |
| `NOT_REPORTED` | searched, genuinely absent — requires a recorded query |
| `NOT_YET_SEARCHED` | not looked for; asserts nothing |

Two numbers come out, and they are the Track B result:

- **readout vs failure recovery** — the asymmetry, now measured on full text
  rather than abstracts, which is the thing §6's 0/10 could not establish
- **stated vs inferred** — how much of the gap `refute infer` closes. If
  inference recovers a large share, that is the scalable lever; if it recovers
  none, the contribution format is the only route and that is worth knowing
  before building for it.

The sweep is also the honest test of my own correction: §6's 0/10 measured
abstracts. Anything above zero here changes the pitch.

#### Phase 2 — tier 0 (small, certain, do regardless)

Already built and cross-validated. Two gaps, both known:

1. **Effective *n* under attrition.** `tier0` takes the designed *n* as
   delivered. For an assay with known exogenous loss it should accept an
   attrition rate and report the *n* you actually analyse. This is what makes
   demoting `fibrosis_on_chip` and `stiffness_drift` (§12.1) truthful rather
   than convenient — they lose units, that loss is non-differential, and pricing
   it is exactly what tier 0 is for.
2. **Deploy the browser form.** Built, cross-checked against `tier0.py` at build
   time, not yet live.

#### Phase 3 — tier 1 (gated on Phase 1)

For each of the four *phenotype-coupled* uncalibrated scaffolds — `traction_force`,
`scar_in_a_jar`, `cell_derived_matrix`, `bleomycin_lung` — the decision rule is
already in the code and should not be softened: `require_runnable()` passes only
when **every** constant has a value and the status admits it.

So Phase 3 is not "calibrate the scaffolds". It is: **fill what the sweep found,
then see which (if any) clear the gate.** The expected outcome, recorded in
advance in §6.5, is that most stay SCAFFOLD. `bleomycin_lung` is the standing
bet, and today's live evidence already put its mortality rate within reach.

If a scaffold clears, the immediate follow-on is the one that matters: **run the
agent loop against it** and see whether the finding replicates on an assay that
is not ours. That is the difference between "my experiment failed" and "this
generalises".

#### Phase 4 — tier 2 (not a build target)

Empty by construction, and it stays empty until tier 1 has several members.
Nothing to build: the backlog populates itself from `out_of_twin_scope`
refusals. Listed only so that "why is tier 2 empty" has an answer other than
"we ran out of time".

#### Phase 5 — the chat, with the Paperclip fallback

`refute chat` is built and keyless. The version worth having connects the
literature path: when someone asks about an assay with no twin, the chat should
search rather than refuse —

> *"No twin for scratch-wound assays. Effect sizes are reported in 6 of 8
> papers; no delamination rate anywhere. So I can tell you whether you are
> underpowered, and I cannot tell you whether the assay survives."*

That turns a dead end into the useful answer, and it makes the chat a **funnel
that accumulates the Track B dataset from real questions** — which is the one
way this collects data that cannot be scraped.

Gated like `/run`: the computed path stays keyless and public; the literature
path needs an explicit enable and a per-session cap, because a public endpoint
spending the owner's Paperclip budget per message is not something to ship first
and gate afterwards.

#### What "done" looks like

In order of how much it would cost to lose:

1. The sweep's two numbers, with the queries recorded
2. Tier 0 deployed and honest about attrition
3. Whatever tier 1 the evidence actually supports — including none
4. The chat, keyless path live
5. The Paperclip fallback, gated

### 12.3 What survives contact with any domain

Not the fibrin physics. The **refusal gate**: `runnable()` splitting the registry
so the catalogue can grow without the claims growing. Fifty scaffolds can be
added and still only what is calibrated is asserted. That property is what makes
this portable at all.

## 13. Two APIs — Benchling and BenchFlow

### 13.1 Benchling — the denominator

The 35 constants `tier1.py` marks missing across its six scaffolds are not one
kind of thing. They come in three shapes, and the distinction decides what any
given source can supply:

| Shape | Examples | Who can supply it |
|---|---|---|
| Effect size and variance | `baseline_*`, `*_fold_change`, `*_cv` | papers report these — Paperclip's job |
| Phenotype-coupled hazards | `p_detach_baseline_per_h`, `detach_force_coupling`, `mortality_severity_coupling` | `NOT_REPORTED` |
| Exogenous nuisance | `p_field_unusable`, `p_seeding_failure`, `p_contamination_10d`, `p_bubble_per_day` | never published; every lab knows them to two significant figures |

Benchling is useless for the first group and is the only realistic source for
the third. State the fit that precisely and do not inflate it:

> **Benchling does not help with the constants papers report. It helps with the
> ones papers omit — which are the ones this whole argument rests on.**

The reason is structural, and it is the same reason §6.1 found 0/10 abstracts
carrying a per-unit failure rate: papers are the *surviving subset* of
experiments. The plate that delaminated on day 3 never became a figure. **The
ELN sits upstream of the publication filter.** Every plate ever cast is in it,
including the abandoned ones. That is the denominator, and no corpus can supply
it at any size.

**What the API actually returns.** Benchling's v2 REST API (tenant-scoped,
Python `benchling-sdk`, App client-credentials or a per-user key) exposes
roughly four things that matter here:

- **Entries** — ELN pages: free prose plus tables. A failed run reads *"gel
  detached overnight, discarded"*. Same extraction problem as a paper, minus the
  survivorship filter.
- **Assay Results** — schematised numeric rows against a result schema.
  Per-well numbers, *if* the lab defined a schema.
- **Containers / Plates** — registered inventory. Well-level identity, *if* the
  lab registers plates.
- **Warehouse** — a Postgres read replica, the only sane way to do this in
  bulk. Paid add-on; assume it is not available.

So the yield is bounded by how the lab uses the product, not by the API.
Structured registry plus result schemas and the constants fall out as a
`GROUP BY`. Notebook-only and you are back to LLM extraction — which is fine,
because "the LLM extracts, the simulator judges" already holds, and a notebook
sentence is an easier extraction target than a methods section.

**Do not assume a tenant exists.** Benchling is enterprise-priced; UK academic
groups more often run OneNote or paper. Whether the group has one, and whether
the fibrin work is in it, is a five-minute question that gates everything below.

**Governance, and the escape hatch already in the data model.** Colleagues'
unpublished runs entering a shared benchmark is a priority-and-authorship
conversation, not a donor-consent one — the IRAS covers the tissue and says
nothing about this. But refute does not need anyone's notebook. It needs
`p_detach_baseline_per_h`, which is a scalar. *"27 of 40 gels detached before
day 7"* is one number, and shipping that number is categorically different from
shipping the notebook.

That has a code consequence, and it is the one thing here worth doing early.
`Evidence` currently **requires** a `quote` — the sentence the number came from
— and `provenance` tags every non-derived value `LITERATURE`. Both are wrong for
this source:

- The quote is the leak. A notebook sentence carries the experiment, the date,
  and often the person.
- The tag is an understatement. A number counted off primary records is
  *stronger* evidence than one read out of a paper, not weaker.

A `BenchlingSource` therefore needs a third provenance tag (`PRIMARY`), an
opaque tenant-local identifier in place of a DOI, and a quote field that is a
**count statement** (`"27/40 before 168 h"`) rather than a transcript. Make that
change before any adapter exists, not after — otherwise the first working query
is also the first leak.

**The better product is write-back, not read.** Reading Benchling calibrates the
twin once. *Writing* to Benchling puts the power calculation into the entry
**before the plate is cast**, as a result row against the protocol. That makes
refute part of the experimental record rather than a website someone visits —
pre-registration by default, inside the tool the lab already opens every
morning. It is also the only version of this a PI has an obvious reason to
approve.

### 13.2 BenchFlow — the collision §2 did not see

§2 has the strategy right: BenchFlow is the harness layer, refute contributes
the scorer, and being an environment is distribution. What §2 missed was a
constraint that has since been **lifted** — see §13.4. Everything below now
ships, including the twin:

| Ships | Why |
|---|---|
| `tier0` | arithmetic over caller-supplied numbers; no constant of ours in it |
| The blocked-constant dataset | claims about what the literature omits — that *is* the Track B deliverable |
| `RefuteEnv` + `baselines` | code, not calibration |
| The exp4 twin | ✅ owner is content to publish the results (2026-08-15) |

**The architecture recommendation does not change, and why it does not is worth
being precise about.** This section originally rested the
host-behind-an-endpoint design on confidentiality: if entrants **download** the
environment they have the constants, if they **call** it they do not. That leg
is now gone. The other leg is untouched:

> An agent that can read `twin.py` and `calibration.py` can overfit to the
> equations instead of designing a good experiment. That is §9.1, and
> publication permission does nothing to it.

So keep the hosted endpoint — `api.py` exists and `/score` is keyless — but
keep it **for Goodhart, not for secrecy**. Two independent arguments happened to
want the same design; one has been retired and the design stands on the other.
Do not carry the retired argument forward, and do not let "confidential" creep
back into the pitch as a justification for something now justified differently.

### 13.4 What "publishing the results" settles, and what it does not

Owner decision, 2026-08-15: content to publish the results. Recorded with its
reasoning, because the previous version of this plan got the *category* wrong.

**What was wrong.** §5 treated this as governed by "the ethics approval and by
publication priority". But look at what is actually in `cases/exp4/data/`:
eighteen rows of per-well gel-area percentages by day. There is no
donor-identifiable information in a fill-percentage timecourse, and the REC
approval governs *use* of the waste tissue — which already happened, lawfully.
Publishing this file was never an ethics question, and framing it as one
overstated the constraint for eleven days.

**What is actually left**, and it is one thing:

- ~~**Authorship and priority.** This is MPhil work supervised in the McCaskie
  group. Publishing the constants and the 6/6 vs 0/4 split *is* publishing the
  result, and the owner is not the only person with a stake in when and where
  that happens. "I don't mind" settles one of the required yeses. Flag it to the
  PI; this section does not do that for you.~~

  ✅ **CLEARED by the owner 2026-08-15**, recorded in `cases/exp4/PROVENANCE.md`
  and reflected here 2026-08-16. The data may be used and the results published.
  **No open gate remains on the data or the results.** The paragraph above is
  kept struck through rather than deleted, because it took two corrections to
  arrive here — first the category was wrong (ethics, when it was never an
  ethics question), then the residue was cleared — and the sequence is the
  useful record.

**Unblocked immediately:** the BenchFlow environment can carry the twin; the
demo can quote the numbers without hedging; and the calibration becomes
*checkable* by a third party — which materially strengthens a Track B "Build
the Dataset" entry, since a dataset nobody can obtain is a weak dataset.

**NOT authorised by this:** flipping the repository to public. That is a
separate and irreversible action the owner has not asked for, and it releases
far more than the results — this plan, the recorded agent runs, and every
internal argument in it. Publishing findings and publishing a working
repository are different releases. Ask before touching visibility.

### 13.3 What this changes about the order

Nothing, this weekend. Benchling gates on a tenant that may not exist and a
permissions conversation that cannot be had at a hackathon. BenchFlow packaging
is interface work worth nothing until the sweep says what the twin can honestly
assert. Both are post-event.

One exception, because it is ~15 lines and it is a correctness fix whether or
not Benchling ever happens: the `PRIMARY` provenance tag and the count-statement
quote. An evidence model that cannot express *"counted off primary records"* has
a gap in it, and the fix is cheap while nothing depends on it yet.

Sequence otherwise unchanged: **sweep first** (§12.4).
