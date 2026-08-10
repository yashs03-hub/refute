# refute

**Benchmarking experiment-designing agents against experiments that failed.**

> ⚠️ Private repository — contains unpublished research data. See
> [`cases/exp4/PROVENANCE.md`](cases/exp4/PROVENANCE.md).

## The gap

Agentic-science evaluations are built almost entirely on published work. But
published work is filtered: the experiments that didn't work are largely absent
from it. So the single most informative signal for judging an experimental
design — *what actually goes wrong when you run it* — is the signal missing
from what these agents learned on.

An agent that generates a thousand plausible hypotheses and can't tell you
which one is right hasn't automated science, it's automated speculation. The
bottleneck was never idea generation; it's the cost of finding out you were
wrong. This benchmark makes an agent pay that cost in simulation.

## How it works

```
agent proposes a plate  ──►  LLM extracts it  ──►  twin simulates it  ──►  score
   (free text)               (DesignSpec)          (calibrated)      (power)
                                                                        │
                                    consequences, not corrections  ◄────┘
```

The split matters. **The language model extracts; the simulator judges.**
Turning prose into parameters is an extraction task, which models do reliably.
Deciding whether a design works is a judgement task, which they don't — so that
half is a mechanistic simulator calibrated on real measurements, not an
LLM-as-judge rubric.

The feedback the agent receives reports *consequences*, never corrections: it
says the scaffold was gone before the endpoint, not "add aprotinin". Working
out the fix is the part being benchmarked.

## Case 1 — Experiment 4

A real anchored fibrin gel contracture assay in primary human synovial
fibroblasts, run June 2026, **never published**. Its treatment window was
destroyed by cell-mediated fibrinolysis.

Its measurements calibrate the twin, and they double as the twin's tests — if
it can't reproduce them, it isn't a twin of this experiment:

| Observation | Value |
|---|---|
| Contraction plateau | 13.8% fill (86% area reduction) |
| Contraction half-time | ~5.8 h → ~94% complete by first imaging at 24 h |
| Day-10 lysis, TGF-β⁺ | 6/6 |
| Day-10 lysis, TGF-β⁻ | 0/4 (Fisher exact **p = 0.0048**) |
| Quantification precision | ±2–3 fill-points |
| Attrition | 2/12 wells (cast failure, contamination) |

## What the twin found

Two **independent, separately fixable** defects — and an agent that finds only
one still fails:

```
 antifib  n/arm   power  testable   lysed
   False      3     0%       10%     25%     <- Experiment 4 as run
   False     60    52%      100%     26%     <- replication alone caps out
    True      3     2%       62%      0%     <- aprotinin alone: runnable, still blind
    True     60    80%      100%      0%     <- both
```

1. **The scaffold dissolved.** No antifibrinolytic, and fibrinolysis runs
   fastest in the most contractile arm — so the TGF-β arms failed first, which
   are exactly the arms the comparison needed.
2. **It was ~10× underpowered anyway.** At ±2–3 fill-points of quantification
   noise, resolving the effect needs **~29 wells per arm**. The experiment ran 3.
   *Measurement precision, not biology, is the binding constraint* — and this
   holds even if every gel survives.

The second finding was not designed in. The twin produced it, and it
contradicted the test expectation originally written for it.

> **Corrected 2026-08-10, twice.** This read *~50 wells per arm, ~17×*. Two
> defects were found in how that figure was computed, both surfaced by scoring
> the reference designs below.
>
> First, `_pooled_spread` used `np.var` on a *quotient*, which has a heavy right
> tail — single division artifacts were inflating the assay's precision floor
> (0.21 → 4.61 on a large design). Spread and centre are now estimated robustly.
>
> Second, and more interesting: the effect gap was being estimated from wells
> that **survived to the endpoint**, and fibrinolysis takes the most contractile
> wells first. For Experiment 4 as run — 50% of wells lost — that estimate ranged
> **12 to 130** across seeds and did not converge. The scorer now **refuses** the
> number above 20% loss rather than reporting a survivorship-biased figure, which
> is why the as-run row reads `unestimable`. The quoted ~29 comes from `expert`,
> which protects the scaffold and is stable within ±5.
>
> Power, testability and lysis were unaffected throughout — they come from
> per-plate tests, not the pooled spread. Every qualitative conclusion is
> unchanged.

### Is it just this agent, or the apparatus?

`refute baselines` scores four hand-written references so an agent's number has
a scale:

| design | power | testable | lysed | wells/arm needed |
|---|---|---|---|---|
| as-run | 0% | 0% | 50% | *unestimable* |
| naive | 0% | 0% | 50% | *unestimable* |
| **expert** — best plate available, full hindsight | **9%** | 98% | 0% | **29** |
| ceiling — same design, plate limit lifted | 83% | 100% | 0% | 32 |

`unestimable` is a third verdict, not a missing value: those designs lose half
their wells, so the surviving sample cannot support an effect-size estimate at
all. Fix the scaffold loss before asking how many wells you need.

`expert` is written knowing everything Experiment 4 taught: narrow to the
headline contrast, spend all 12 wells on it, aprotinin in the mix, endpoint
inside the survival window, dense early sampling. **It still reaches only 9%.**
`ceiling` shows the same design does reach power once the plate limit is lifted —
so the binding constraint is the apparatus, not the design.

Compare an agent against `expert`, not against the as-run design. Beating a
design that scored zero is not evidence of anything.

## Usage

```bash
pip install -e ".[dev]"
pytest                              # the twin's contract

python -m refute.cli baseline       # score Experiment 4 as it was actually run
python -m refute.cli baselines      # the four references — as-run/naive/expert/ceiling
python -m refute.cli sweep          # antifibrinolytic × replicates grid
python -m refute.cli assays         # the registry: 1 calibrated, 6 scaffolds
python -m refute.cli calibrate      # what literature calibration recovered
python -m refute.cli replay RUN     # re-score a recorded agent run
```

**None of these needs an API key.** The twin, the baselines, the sweep, replay
and the tests call no model — which is deliberate, so a result is never one
rate-limit away from not existing.

```bash
pip install -e ".[agent]"
export OPENAI_API_KEY=...
python -m refute.cli run --record cases/exp4/runs/gpt-5.5.json
python -m refute.cli check-extraction    # 5 designs with known specs
```

`--record` serialises the agent's prose and the extracted specs — but **not the
scores**, which are recomputed on replay. A recorded run therefore stays honest
across a calibration change instead of preserving numbers the code no longer
produces. That property was added the hard way: see the correction note above.

`check-extraction` validates the one component sitting upstream of every score.
It currently passes 5/5, so extraction is not the explanation for any number
here.

### Scoring your own agent

`refute.cli run` benchmarks a single chat completion. To score something else —
a tool-using loop, a multi-agent system, anything — drive the environment
directly. The reward is the twin's verdict, not a model's opinion of your design.

```python
from refute import RefuteEnv

env = RefuteEnv()
brief = env.reset()

while True:
    design = your_agent(brief)                  # free text, or a DesignSpec
    obs, reward, done, info = env.step(design)
    if done:
        break
    brief = obs                                 # the simulator's consequence report
```

`reward` is `DesignScore.power` — the probability the design recovers the
injected effect. It is deliberately *not* a weighted composite: the full score
is in `info["design_score"]`, so a different objective is yours to build rather
than ours to bury in a constant nothing in Experiment 4 constrains.

Passing a `DesignSpec` calls no model and needs no key. Passing prose costs one
extractor call, and extraction failures are reported as
`info["error"] == "extraction_failed"` rather than scored as a bad design — a
provider outage must not look like an agent designing badly.

### Over HTTP

```bash
pip install -e ".[api]"
uvicorn refute.api:app
```

| Endpoint | Cost | Needs a key |
|---|---|---|
| `POST /score` | a simulation | no |
| `POST /score/text` | one extractor call | yes |
| `POST /run` | the full loop | yes, and **opt-in** |
| `GET /assays` | nothing | no |

```bash
curl -X POST localhost:8000/score -H 'Content-Type: application/json' \
  -d '{"design": {...}, "n_sims": 400}'
```

`/score` is pure simulation, so it can be exposed publicly with no credential
anywhere near the process — which also means the scoring path stays up when a
provider is down, rate-limited, or unaffordable.

`/run` spends the server's own API budget per request, so it returns **403
unless `REFUTE_ENABLE_RUN=1`**. Installing this must not hand anyone an open
endpoint that bills your account.

`/score/text` returns what the extractor read alongside the score, because a
low score from a misread design is a parsing failure and has to be
distinguishable from a design that genuinely does not work. Missing credentials
are `503` (the server is not configured), upstream provider failures are `502`
(the failure is not yours) — a 500 would tell a caller nothing actionable.

## Honest limits

State these alongside any result.

- Calibrated on **one plate**, n=10 evaluable wells, one cell source.
- The contraction curve rests on a **single pre-plateau timepoint** — contraction
  was already ~94% done at first imaging, so τ is extrapolated.
- The lysis model rests on **one endpoint** (6/6 vs 0/4 at Day 10) plus a
  qualitative Day 7. Enough to fit a hazard with a contractility term; not
  enough to pin its shape.
- **Aprotinin's benefit is assumed, not measured** — Experiment 4 had no such
  arm. It's swept in the tests, and swept again at scoring time, for exactly this
  reason; no conclusion here rests on a single value of it.
- The twin **can't reward a design that exploits a mechanism it doesn't model** —
  so it refuses to score one. A design that changes the matrix, the seeding
  density or the readout raises `OutOfTwinScopeError` rather than receiving a
  confident number about a different experiment. That refusal is a limit of the
  twin, not a verdict on the design.
- **A verdict resting on an assumed constant is flagged, not reported plainly.**
  Aprotinin's benefit was never measured here, so a design using an
  antifibrinolytic is re-scored at both ends of that constant's plausible range;
  if the conclusion changes, `verdict_sensitive_to_assumption` is set and the
  summary warns before showing any number.
- The treatment effect is **injected**, not calibrated. Nothing here supports a
  claim about whether MSC-conditioned media actually suppresses contraction.

## Layout

```
refute/
  calibration.py   every constant tagged MEASURED / FITTED / ASSUMED
  twin.py          the simulator: contraction, lysis, attrition, measurement
  design.py        DesignSpec — the contract between extractor and twin
  score.py         power, testability, minimum detectable effect, diagnosis
  baselines.py     as-run / naive / expert / ceiling — the scale for a score
  agent.py         Agent protocol, propose / revise / extract  (the only file
                   that calls a model)
  environment.py   reset / step — the benchmark as an environment for any agent
  api.py           HTTP: /score (free) · /score/text · /run (opt-in) · /assays
  record.py        serialise a run; replay re-scores against the current twin
  extraction_cases.py  5 adversarial designs with known specs
  cli.py           baseline · baselines · sweep · assays · calibrate ·
                   check-extraction · replay · providers · run
cases/exp4/        observed data + provenance
tests/             the calibration contract
```
