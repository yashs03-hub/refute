# refute — build plan and state

Authoritative build state. `README.md` is the pitch; this is what is done, what
is next, and what is deliberately not being built.

Target: **re:AGENT — End to End Agentic Science**, 15–16 Aug 2026, San
Francisco. Track A (an agent that carries out a defined scientific workflow).
Confirmed attendance.

---

## 0. State

| Component | Status |
|---|---|
| `calibration.py` — constants tagged MEASURED / FITTED / ASSUMED | ✅ done |
| `twin.py` — contraction, lysis, heterogeneity, attrition, measurement | ✅ done |
| `design.py` — `DesignSpec`, plus Experiment 4 as run | ✅ done |
| `score.py` — power, testability, MDE, failure diagnosis | ✅ done |
| `tests/` — 12 calibration tests, all passing | ✅ done |
| `cli.py` — `baseline` · `sweep` · `run` | ✅ done |
| `agent.py` — propose / revise / extract | ⚠️ written, **never run against the API** |
| Optimizer — cheapest design meeting a power target | ⬜ not started; `sweep` is a grid, not a search |
| Second case, Paperclip-calibrated (§3) | ⬜ not started |
| Second case (qPCR artifact) | ⬜ not started — needs owner's go-ahead |
| Uncertainty propagation over calibration params | ⬜ not started |
| Proto integration | ⬜ blocked on a 20-minute check — see §2 |

**The one real gap:** `agent.py` has not made a single live API call. Everything
else is verified. That is the first thing to do next, because extraction
fidelity is the most likely place this breaks — if the extractor mis-reads a
design, the twin scores the wrong plate and the failure looks like the agent's.

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

**Before integrating, check one thing** (20 minutes, from the GitHub repos and
the bioRxiv preprint): are `proto-language`'s primitives generic, or typed to
DNA/RNA/protein sequences? If generic, expressing experiment design as a Proto
program is a real demonstration on the host's framework. If sequence-typed, do
not force it — this design space is small and discrete (antifibrinolytic y/n,
replicates, timepoint schedule, endpoint), so a plain grid or Bayesian search
suffices. Integration would then be positioning, not necessity. Be honest about
which.

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

### The three-layer map

| Layer | Tool | Question it answers |
|---|---|---|
| Knowledge | Paperclip | What is already known? |
| Entity design | Proto | What candidate should I build? |
| **Validation** | **`refute`** | **Can the experiment that tests it actually answer the question?** |

Nobody has built the third. That is the pitch.

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
| Proto integration turns out to be a dead end mid-build | Do the 20-minute sequence-bound check (§2) *before* committing any architecture to it. The optimizer (§3 item 3) is worth building regardless and does not depend on Proto |
| Public presentation is a patent disclosure | UK/EPO have no grace period — the same trap already hit `versionCTRL`. Make it a conscious decision before the 15th, not a discovery after |
