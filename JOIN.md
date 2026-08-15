# Want to work on this?

Read this in five minutes, pick something, start. You do not need to read
`PLAN.md` and you do not need to know any biology.

## The 30-second version

A real experiment failed. Anchored fibrin gels, asking whether MSC-conditioned
media blunts TGF-β-driven contraction in human fibroblasts. The gels **dissolved
before the treatment window closed** — cell-mediated fibrinolysis, fastest in
exactly the arms the comparison needed. It was never published, which is the
point: nothing like it is in the corpus these agents learned on.

That plate calibrates a simulator. Ask a frontier model to design the
experiment, given only what was knowable beforehand, and it makes the same
mistakes. Give it *consequences* rather than corrections and it fixes them — and
then it **declines to run the experiment at all**, correctly, for the same
reason the simulator gives.

Our scorer gave that refusal 0% — the worst score available — until we fixed it.

## See it in 60 seconds

```bash
git clone <repo> && cd refute
pip install -e ".[dev]"
python -m refute.cli demo --no-pause
```

No API key, no network, ~6 seconds. That command **is** the onboarding — it
walks the whole argument in order.

## What you could build in two days

Each of these is self-contained. None requires understanding the twin's
calibration, and none blocks the others.

### 1. The corpus sweep — *data wrangling, API work*
**Biggest impact.** We searched published full text for the constants six other
fibrosis assays would need. Result: what an assay *measures* is partly
recoverable (2/9); **how it breaks is not recoverable at all (0/10)**.

That's currently n=19 constants. Scale it to 50–100 papers and it stops being a
case study and becomes the finding: *across N papers and M constants, failure
rates recoverable in Z%.* The harness exists (`refute calibrate`); it needs a
credential and someone willing to classify a lot of misses into a taxonomy.

Touches: `refute/assays/`. Never touches the simulator.

### 2. The optimizer — *numerical, algorithmic*
`refute sweep` is a grid that prints a table. Turn it into a **search** that
returns the cheapest design hitting a power target — fewest wells, fewest
timepoints, subject to the apparatus constraints.

One catch worth knowing before you start: a search over designs is a search
*against our scorer*, so it needs the assumption-sensitivity flag wired into the
objective rather than bolted on after. See §9.1.

Touches: `refute/score.py`, one new module.

### 3. A front end — *web, no biology at all*
There's a working HTTP API (`refute.api`) and a browser-side power calculator.
What's missing is the thing that makes it usable: paste your design, get told
whether it can answer its own question, iterate.

Routing matters more than the UI — most real experiments aren't the fibrin
assay, so it needs to fall back to tier 0 gracefully rather than refusing.

Touches: `web/`, `scripts/`. Nothing in the simulator.

### 4. Harness experiments — *cheap, high signal*
We have three agent harnesses (single-shot, self-critique, checklist) and have
only ever run the first. The interesting question is sharp:

> The experiment's central defect was n=3 — a **computable** error. If forcing
> the model through a quantitative checklist fixes it, the deficiency was an
> un-done calculation. If it doesn't, the deficiency is *knowing what goes
> wrong* — which is this project's whole claim.

Either result is publishable. Costs a handful of API calls and almost no code.

Touches: `refute/harness.py`, `refute run --harness`.

### 5. A second case — *if you have failed data*
The strongest possible contribution. If you or your lab has an assay that
*fails* — delaminates, ruptures, dies before the endpoint — see
`cases/TEMPLATE/`. The ask is one CSV plus failure counts by condition.

Our entire failure model rests on **ten wells**. It is not much data. It is data
nobody publishes.

### 6. BenchFlow packaging — *integration*
`RefuteEnv` is already a gym-style environment. Porting it to BenchFlow's format
would make this something other people can run rather than a demo. Mostly
interface work.

## What you can't usefully do in two days

Anything requiring the twin's calibration — new mechanisms, new constants,
changing the hazard model. Those need primary data and a lot of context. Pick
from the list above instead.

## The house rules

Three, and they're the whole design philosophy:

1. **The simulator judges, the LLM only extracts.** We never ask a model whether
   a design looks sensible.
2. **Fail closed.** If we can't vouch for a number we refuse to produce one —
   uncalibrated assays raise, out-of-scope designs raise, survivorship-biased
   estimates are withheld. A confident wrong number is worse than no number.
3. **Consequences, not corrections.** Feedback says *the scaffold was gone before
   your endpoint*, never *add aprotinin*. Working out the fix is the thing being
   measured.

If a change would violate one of these, it's probably the wrong change — or
it's a genuinely interesting argument, in which case make it.
