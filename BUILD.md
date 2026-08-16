# Build plan — grounding system, 2 people, 11 hours

> ## ⚠️ PARTLY SUPERSEDED 2026-08-16 — reconcile against the SPEC before using
>
> **This is layer 1's build plan, and layer 1's plan now lives in
> `15 - SPEC - the whole system.md` §8**, which explicitly *"consolidates the
> system design and the layer 1 build plan"*. This document predates that
> consolidation. It is kept because its lane discipline and its cut list are
> better than the SPEC's, and because two of its calls were made for reasons the
> SPEC does not record. But four things below were settled differently, and one
> is a straight omission.
>
> **Settled differently by the SPEC:**
>
> 1. **The frozen-contracts file is `types.py`, not `contracts.py`, and its
>    contents are SPEC §4.2.** Same idea, different types. The SPEC's `Claim`
>    carries `status` and `origin_event`; this file's carries `kind`, `context`
>    and `made_at_step` and neither of the first two. Do not freeze both.
> 2. **The verdict vocabulary is five categories, not seven** — `contradicted` ·
>    `unsupported` · `supported` · `context_dependent` · `no_evidence` (SPEC §4,
>    under the verdict format locked in §3). `Label` below splits `scope-mismatch` out of `context-dependent`
>    and `not-in-literature` out of `not-searched`. The second of those
>    distinctions is right and survives, but it lives on the **handoff** — SPEC
>    §5.3 property 5, and `OpenItem.searched` / `queries_run` in
>    `refute/handoff.py` — rather than as a verdict label. The first is not in
>    the locked set at all.
> 3. **The lane split is A spine / B grounding / C data check / D evaluation**
>    (SPEC §8.3), not A runtime / B epistemics. The SPEC also says which lanes to
>    hand to helpers — A and D, because they need no API key and no prompt work.
>    The hour-by-hour table below assigns the same work differently.
> 4. **Step order is fixed and the viewer is second.** SPEC §8.2: spine → viewer
>    and replay → data check → grounding → analysis agent → handoff. This
>    document puts rendering at hours 6–8 and never builds a replay at all.
>
> **The omission, and it is the significant one: traceability.** SPEC §6 makes it
> *"a requirement, not a feature"* — a run tree, an artifact store, `origin_event`
> on every object, one traced model wrapper that is never bypassed, a record of
> what was retrieved and *not* used, and replay. None of that appears anywhere
> below. The SPEC's never-cut list is *the trace, the ledger, invalidation,
> replay, the two fixtures*; the never-cut list at the end of this file is a
> different four items and does not include a single one of them. Both lists are
> defensible and they are not the same list. Reconcile explicitly rather than
> taking whichever file you opened first.
>
> **Two smaller notes.** The SPEC ends layer 1 with a **handoff** (§5, §8.2 step
> 6) and there is no handoff step below — which matters, because the handoff is
> the entire reason layer 2 exists. And this file's third descope, *"the
> controller ships advisory"*, sits against a locked decision that consequence is
> deterministic (SPEC §3); the SPEC leaves *how hard the interrupt is by severity*
> open (§4), so advisory-first is arguable, but it is arguable against a lock and
> should be raised rather than assumed.
>
> **Still good, and not in the SPEC:** the one-rule import ban and the boundary
> test in §7; the three descopes; hand-scoring ledger fidelity at first
> integration; the carry-on control as the arm to keep if only one fits; and the
> ordered cut list. Those are the reason to keep this file.
>
> **On the schedule.** The eleven hours are 15–16 August and have largely
> elapsed. Read the hour markers as an ordering, not as a clock.

Companion to the module plan. That document says *what* and *why*; this one says
*who touches which file, in what order, and what unblocks what.*

*2026-08-16: "the module plan" is the document the SPEC consolidated. The SPEC
is now both — read it first, then this for the sequencing.*

**Move this into the shared repo root.** It is written for that repo, not for
refute — refute is not a dependency of anything here.

---

## The one rule that makes this parallel

> **You may never import from the other person's package.**
> You import from `contracts.py`, and you read from `fixtures/`.

Both people build against **frozen types and fake data** from hour one.
Integration is then progressive replacement of fixtures with real modules,
rather than a big-bang merge at hour nine. If a module is not finished, the
demo still runs on its fixture and you say which one.

There is a test that enforces this (§7). It takes two minutes to write and it
will save an argument.

---

## Three descopes to take before starting

These are not cuts you make when time runs out. They are cuts you make now,
because they remove the flakiest components from the critical path.

**1. Module 1 is fixtures first, live agent last.**
You do not need a live analysis agent to demo a critic — you need a *trajectory*
with a wrong assumption in it. Module 11 requires you to author 5–8 seeded-error
trajectories anyway, so **the eval corpus is the demo input.** Author them as
realistic transcripts, run the real ledger over them, and wire a live agent only
if hours 9–11 are free. This removes a long-running stochastic process from the
demo path.

**2. The sandbox is a subprocess, not a security boundary.**
Your data, your generated code, your machine. You need a timeout, a fixed import
list, and captured stdout — not isolation. Say so in the limitations slide.
45 minutes, not four hours.

**3. The controller ships advisory, and hardens only if the critic earns it.**
Deterministic invalidation with dependency propagation is real engineering, and
a hard interrupt driven by a mediocre critic is worse than no interrupt. Build
advisory first. Promote to blocking only for verdicts the data corroborated.

---

## Hour 0 to 0.5 — freeze the contracts, together, before any code

One file. Both people in it. Nobody edits it afterwards without saying so out
loud, because every other file depends on its shape.

> *2026-08-16 — superseded as the file to freeze. SPEC §8.1 names it `types.py`
> and SPEC §4.2 gives its contents, including `origin_event` on every object,
> which is absent here. Freeze one of the two, not both.*

```python
# contracts.py — FROZEN at 00:30. Changing this blocks both people.
from dataclasses import dataclass
from typing import Literal

ClaimID = str

@dataclass(frozen=True)
class Claim:
    id: ClaimID
    text: str                        # "Treating cluster 4 as macrophages"
    kind: Literal["annotation", "threshold", "assumption", "conclusion"]
    depends_on: tuple[ClaimID, ...]  # invalidation propagates along these
    context: dict[str, str]          # organism, tissue, assay
    made_at_step: int                # index into the trajectory

@dataclass(frozen=True)
class Passage:
    id: str
    source: str                      # DOI or stable identifier
    sentence: str                    # the sentence that carries the claim
    surrounding: str

@dataclass(frozen=True)
class EvidenceRecord:
    passage: Passage
    says: str
    conditions: dict[str, str]       # species, in_vitro, timepoint, dose, donor
    relevance: Literal["bears", "adjacent", "irrelevant"]              # 6a
    scope: Literal["same", "narrower", "wider", "mismatched", "unstated"]  # 6b
    mechanism: str                   # 6d — the causal chain; "" if none stated

@dataclass(frozen=True)
class Dossier:
    claim: Claim
    records: tuple[EvidenceRecord, ...]
    conflicts: tuple[tuple[str, str], ...]   # passage-id pairs that disagree
    queries_run: tuple[str, ...]             # REQUIRED — see note below

Label = Literal[
    "contradicted", "unsupported", "supported",
    "scope-mismatch",        # distinct from context-dependent, deliberately
    "context-dependent",
    "not-in-literature",     # searched, and it is not there
    "not-searched",          # no claim either way
]

@dataclass(frozen=True)
class Predicate:
    """7a. Falsifiable, and written BEFORE any code exists."""
    statement: str                   # "fraction of cluster-4 cells with R>0 exceeds 0.3"
    quantity: str
    comparator: Literal[">", ">=", "<", "<=", "~="]
    threshold: float

@dataclass(frozen=True)
class CheckSpec:
    predicate: Predicate
    code: str                        # reads DATA, assigns VALUE
    rationale: str

@dataclass(frozen=True)
class CheckResult:
    spec: CheckSpec
    outcome: Literal["corroborated", "refuted", "inconclusive"]
    value: float | None
    plot_path: str | None
    stderr: str
    placebo_outcome: str | None      # same check on shuffled labels
    sensitive_to_threshold: bool     # flips if threshold moves ±20%

@dataclass(frozen=True)
class Verdict:
    claim: ClaimID
    label: Label
    mechanism: str
    citations: tuple[str, ...]
    check: CheckResult | None

    @property
    def severity(self) -> Literal["fatal", "material", "advisory", "suppressed"]:
        """Derived from the data, never asserted by a model."""
        if self.check is None:
            return "advisory"
        if self.check.outcome == "refuted":
            return "suppressed"
        if self.check.outcome == "inconclusive":
            return "advisory"
        if self.check.sensitive_to_threshold:
            return "advisory"
        return "material"
```

Four things in there are deliberate and worth not losing:

- **`Dossier.queries_run` is required.** `not-in-literature` is a claim about the
  literature and cannot be made without evidence of having searched.
  `not-searched` is the honest default. Conflating them makes 6g's abstention
  unmeasurable — you cannot tell abstaining-after-looking from never-trying.
- **`Predicate` exists separately from `CheckSpec.code`.** The expectation is
  stated numerically before the code is generated, so a check that computes the
  wrong quantity is visible rather than merely well-shaped.
- **`placebo_outcome`** is the module-7 analogue of your placebo critic. Run the
  same check on shuffled labels; anything other than `refuted` means the check
  is broken, not that the critique is right.
- **`severity` is a property, not a field.** No model can assert it.

---

## Hour 0.5 to 1 — the walking skeleton, together

Build the end-to-end path with every module faked. It must run and print a
verdict before you split up.

```
trajectory fixture → fake ledger → fake dossier → fake verdict → fake check → print
```

This is the highest-leverage hour of the day. From here there is always a
running system, and every subsequent commit replaces one fake with one real
module.

Create the fixture directory at the same time, with **one hand-written example
of every contract type**. These are what the other person builds against.

```
fixtures/
  trajectories/traj_01.json      # B authors — a transcript with a seeded error
  claims/claims_01.json          # A authors — what the ledger should produce
  passages/passages_01.json      # B authors — retrieved passages for traj_01
  dossiers/dossier_01.json       # B authors — A builds the check runner on this
  verdicts/verdict_01.json       # B authors — A builds the controller on this
  checkspecs/spec_01.json        # B authors — A builds the executor on this
```

**A authors `claims/`; B authors everything else.** That way each person hands
the other exactly the input they need and nobody blocks.

---

## Hours 1 to 5 — parallel lanes

Split by **skill shape**, not module number. A owns stateful runtime; B owns
prompts and schemas. Neither directory is ever touched by the other person.

| | **Person A — the runtime** | **Person B — the epistemics** |
|---|---|---|
| owns | `runtime/`, `checks/run.py`, `eval/score.py`, `demo/` | `evidence/`, `checks/predicate.py`, `checks/generate.py`, `eval/corpus.py` |
| 1–2 | `ledger.py` — trajectory → `Claim` list with `depends_on` | `query.py` — claim → queries. **Get Paperclip authenticating in this hour or fall back to `fixtures/passages/` and say so.** |
| 2–3 | `executor.py` — subprocess, timeout, fixed imports, capture `VALUE` | `typing.py` — passage → `EvidenceRecord`. 6a relevance + 6b scope + 6d mechanism |
| 3–4 | `checks/run.py` — `CheckSpec` → `CheckResult`, including the placebo run and the ±20% threshold sweep | `dossier.py` — `EvidenceRecord[]` → `Dossier`, conflicts paired and scope-tagged |
| 4–5 | `controller.py` — advisory verdicts, invalidation along `depends_on`, one checkpoint/rollback | `adjudicate.py` — one reasoning pass over the dossier → `Verdict`. Plus `predicate.py`: mechanism → `Predicate` |

**6c polarity and 6e context are fields in `EvidenceRecord`, not modules.**
6a, 6b and 6d are load-bearing — 6d because module 7's expectation is derived
from the mechanism, so a missing mechanism means no check.

---

## Hour 5 to 6 — first integration, together

Replace fakes with real modules one at a time, in this order, running the
skeleton after each swap:

1. ledger (A) — check it against `fixtures/claims/`, **hand-score fidelity now**
2. retrieval + typing (B)
3. dossier + adjudication (B)
4. predicate + generate (B)
5. executor + check runner (A)
6. controller (A)

**Hand-scoring ledger fidelity at step 1 is not optional.** If the ledger
mis-extracts a claim, everything downstream critiques something the agent never
said — and the data check will faithfully test the mis-stated claim and be
correct about the wrong thing. Module 7 cannot catch this. One number, scored by
eye over 5–8 trajectories: *of the claims in the ledger, how many did the agent
actually make?* Without it a bad detection rate is uninterpretable, because you
cannot tell whether the ledger or the critic failed.

---

## Hours 6 to 8 — parallel again

| **Person A** | **Person B** |
|---|---|
| `eval/score.py` — the three numbers | `eval/corpus.py` — finish 5–8 seeded trajectories |
| **The carry-on control**: trajectories with no seeded error, where the right output is silence | **The placebo critic** — matched length, tone, citation format, wrong content |
| `demo/render.py` — split screen, generated code visible | **The ablation arm** — one run with 6a/6b disabled |
| Rollback path working end to end | Tighten the reasoning-pass system prompt |

Three arms, and each answers a different question:

- **placebo critic** → is revision grounding, or agreeableness?
- **carry-on control** → does the critic fire when it should not? Without this,
  precision is unmeasurable and "refuse everything" scores perfectly.
- **ablation (6a/6b off)** → is the structure actually the mitigation? Your whole
  6f decision rests on this being true and nothing currently tests it.

If only one fits, keep the **carry-on control**. A critic that always objects is
the failure mode most likely to be caught by a judge.

---

## Hours 8 to 9 — full run, then record

Full pipeline over the whole corpus. Produce the three numbers.

**At hour nine, pre-record the demo. Not at hour ten.** Live model loops fail in
front of an audience, and a recording you did not need costs nothing. Say it is
a recording if you fall back to it — nobody minds, and everybody notices a
silent one.

---

## Hours 9 to 11 — slides, and the live agent only if everything else is done

Slides are B (they hold the argument). Second recording and any remaining
polish is A.

Wire the live analysis agent **only** if the recording is safely in hand. It is
the nicest-to-have thing in the build and the most likely to break.

---

## §7. The test that keeps the lanes apart

```python
# tests/test_boundaries.py
import pathlib, re

LANES = ("runtime", "evidence")   # the two owned packages

def test_no_cross_package_imports():
    for pkg in LANES:
        for f in pathlib.Path(pkg).rglob("*.py"):
            src = f.read_text()
            for other in LANES:
                if other == pkg:
                    continue
                assert not re.search(rf"^\s*(from|import)\s+{other}\b", src, re.M), (
                    f"{f} imports {other} — the lanes may only meet at contracts.py"
                )
```

Two minutes to write, and it converts a merge argument into a failing test.

---

## The cut list, in the order to cut

Decide this now so it is not decided at hour nine under pressure.

1. Live analysis agent → fixtures **(already cut, §descopes)**
2. Ablation arm → state as untested assumption
3. 6e surrounding context → drop the field
4. Deterministic rollback → advisory verdicts only
5. Check refinement loop → one attempt, then `inconclusive`
6. Multi-claim triage → check exactly three claims per trajectory, chosen by
   depth in the dependency graph

**Never cut:** the predicate-before-code split, the placebo check, the carry-on
control, `queries_run`. Each of those is what stops a specific, likely, visible
failure — and each is under thirty lines.

> *2026-08-16 — the SPEC has a different never-cut list and the two do not
> overlap at all.* SPEC §8.4: **the trace, the ledger, invalidation, replay, the
> two fixtures** — *"cutting the trace saves an hour tonight and costs three
> tomorrow, because every subsequent bug becomes a guess."* Nothing in this
> file's list is in that one and nothing in that one is here. That is not a
> disagreement anybody had; it is two lists written for two different failures,
> and it needs to become one list before either is used as a cut order.

---

## What "done" looks like

> On N trajectories seeded with a known-wrong premise, the system detected the
> premise in **k of N**, the agent's final claim corrected in **j of N**, against
> a placebo critic at **j′ of N** — and on M correct trajectories it stayed
> silent in **m of M**.

N of 5–8. That fourth number is the one most people will not have.

**State the limitations rather than hiding them:** no weighting of evidence, a
fixed iteration count rather than a convergence criterion, one question shape,
one dataset, and a sandbox that is a timeout rather than an isolation boundary.
A stated limit reads as competence. A manufactured result reads as a demo.
