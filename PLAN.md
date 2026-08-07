# refute — build plan and state

Authoritative build state. `README.md` is the pitch; this is what is done, what
is next, and what is deliberately not being built.

Target: **re:AGENT — End to End Agentic Science**, 15–16 Aug 2026, San
Francisco. Confirmed attendance.

**Track B — Build the Dataset** (see §2). Track A was the earlier assumption and
was wrong: `refute` evaluates agents that automate a workflow rather than being
one, whereas Track B's brief — facts that "sit one line at a time across
thousands of papers" — is the §6 calibration almost verbatim.

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
| `tests/` — 88 passing | ✅ done |
| `cli.py` — `baseline` · `sweep` · `assays` · `calibrate` · `providers` · `run` | ✅ done |
| Calibrating the six tier-1 scaffolds | ⬜ harness built; **blocked on Paperclip credential — see §6, §7.1** |
| Optimizer — cheapest design meeting a power target | ⬜ not started; `sweep` is a grid, not a search |
| Adversarial extraction set (5 designs, known specs) | ⬜ not started — **pre-flight item, §7.1** |
| Second case (qPCR artifact) | ⬜ not started — needs owner's go-ahead |
| Uncertainty propagation over calibration params | ⬜ not started |
| Proto integration | ❌ **resolved: do not build** — Proto is sequence-typed (§2) |
| BenchFlow packaging — `refute` as an eval environment | ⬜ not started — likely the right home (§2) |

PRs #1–#3 merged 2026-08-04. The loop runs: propose → extract → simulate →
revise → extract → simulate, against `openai:gpt-5.5`.

**First live result.** gpt-5.5 independently reproduced Experiment 4's two
defects — n=3 per arm, no antifibrinolytic, no reasoning about scaffold loss.
Given consequence-feedback it narrowed to the two arms that matter, filled the
plate (2×6), added a pre-treatment baseline and flagged scaffold failure:
testable 0% → 97%. Power still only reached 9%, with ~57 wells/arm required.
**Even the best design available on one plate cannot answer the question** —
that verdict is the finding.

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
| Public presentation is a patent disclosure | UK/EPO have no grace period — the same trap already hit `versionCTRL`. Make it a conscious decision before the 15th, not a discovery after |

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
| `map` | Parallel AI analysis across many papers: "extract the delamination rate from each of these 200 methods sections" |

Also `search` (hybrid BM25 + vector), `lookup` (DOI/PMID metadata), `sql`
(read-only over the documents table).

Each of the six protocols already carries a `paperclip_query`, written when the
scaffolds were built. They are the shopping list; nothing new needs designing.

### 6.3 Access — user action required

Self-serve, not gated to the hackathon. Per the standing rule, **the credential
is created and exported by the user, never written on their behalf**:

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

If that prediction holds, the calibration run *is* a result about the
literature, not merely a step towards a second case.

---

## 7. Run sheet — 15–16 Aug 2026

The event supplies three things unobtainable at home: Paperclip at corpus
scale, researchers from Arc and the Biohub to argue with, and judges. Anything
needing none of those should be finished before boarding.

### 7.1 Pre-flight (by 14 Aug)

| # | Item | Why it cannot wait |
|---|---|---|
| 1 | Calibration harness — `evidence.py`, `sources.py`, `literature.py`, `refute calibrate` | ✅ done. Paperclip is now a credential away, not a build |
| 2 | **Paperclip credential, and the six queries run once** | If `grep`/`map` behave unlike the docs, find out on the 6th, not the 15th. `PaperclipSource.parse` is written against an unverified schema and is the first thing to suspect |
| 3 | **Adversarial extraction set** — 5 designs, known specs | Extraction is the one unvalidated component. A headline number that might be a parsing bug cannot be presented |
| 4 | **Pre-record an agent run** | 10k TPM on frontier models means a live `run` is a 3-minute silence with a real chance of a 429 on venue wifi |
| 5 | Decide the patent question | Presentation is disclosure; UK/EPO have no grace period. This already caught `versionCTRL` |

### 7.2 Day 1 (Sat) — build the dataset

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

### 7.4 The demo

1. A real experiment that failed, with the data — 30 s
2. `refute baseline` **live** — 0% power, 50% of wells lysed. Instant, no network
3. `refute sweep` **live** — the two defects are separable; neither fix alone works
4. `refute calibrate` **live** — the asymmetry, in one table
5. The agent result, **pre-recorded** — 0% → 97% testable, still 9% power.
   Unanswerable on one plate

Lead with the absence, not the extraction. Recovered constants read as
literature mining; what the literature systematically omits is a finding.

Nothing in steps 2–4 needs a network, a key, or sponsor compute. The demo
cannot die on venue infrastructure.

### 7.5 Questions to have answered before they are asked

| Question | Answer |
|---|---|
| "Isn't this a virtual cell?" (Arc affiliates two of seven co-hosts) | A virtual cell predicts the biology; this models the apparatus. A perfect virtual cell still will not tell you the gel dissolves on day 7, that the most-treated arm fails first, or that segmentation noise means you needed 50 wells |
| "Why not build it in BenchFlow?" | It probably should live there. The harness was never the hard part — a reward signal that is not another model's opinion was |
| "Why not use Proto?" | Its primitives are sequence-typed (§2). The analogy is worth stating; the dependency is not worth having |
| "One plate is not a benchmark." | Correct, and stated first. The alternative on offer is zero plates. Every literature-built benchmark is trained on survivors; this is calibrated on an experiment that was never published |
| "AI just designed working viruses — why aren't you working on *that*?" | §8 |

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
