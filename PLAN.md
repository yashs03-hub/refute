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
| Second case (qPCR artifact) | ⬜ not started — needs owner's go-ahead |
| Uncertainty propagation over calibration params | ⬜ not started |

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

## 2. Next, in order

1. **Run `agent.py` end to end once.** Verify extraction fidelity on a real
   proposal before trusting any delta number.
2. **Extraction adversarial check.** Hand-write 5 designs with known specs;
   confirm the extractor recovers them. Extraction failure must not be
   scoreable as design failure.
3. **Propagate calibration uncertainty.** Score over a distribution of
   `TwinParams` rather than the point estimate. Report bands, not numbers.
4. **Baseline non-agent designs.** Score the as-run design, a naive design, and
   a domain-expert design, so the agent's number means something relative.
5. **Second case** — the qPCR "hypoxic shift" that turned out to be empty tubes.
   Same shape: an agent handed that data will confidently explain an artifact.
   Two cases makes it a benchmark rather than an anecdote. **Needs the owner's
   explicit go-ahead before touching that data.**

## 3. Deliberately not building

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
  the *calibrated* twin, not from a model's imagination.

## 4. Risks

| Risk | Mitigation |
|---|---|
| Extractor mis-parses a design; scored as a design failure | Item 2 above — adversarial extraction set, before any headline number |
| Judges read "calibrated on one plate" as fatal | Say it first, in the limits section. The alternative on offer is zero plates |
| Aprotinin assumption carries the conclusion | Already swept in tests across 2×/4×/8×; the lysis-rescue claim holds throughout |
| Twin penalises a genuinely clever design it can't model | Stated in README limits; report diagnoses, not just a score |
| Demo needs a live run on stage | `baseline` and `sweep` are instant and need no API key — those are the demo; `run` is the flourish |
