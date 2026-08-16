# Handoff to Google Antigravity: multi-assay twins, checkpoints 2–4

**Do not confuse this with `HANDOFF.md`** — that file is a different, older
document about the layer-1/layer-2 SPEC seam (a two-builder architecture
agreement). This handoff is scoped to one in-flight task: continuing the
multi-assay-twin build that a Claude Code session started and got one
checkpoint into.

Repo: `yashs03-hub/refute` (private). Work from `main` — everything below is
merged there already.

## Context in one paragraph

`refute` is a benchmark that scores AI-designed experiments against a
mechanistic digital twin. Until today it had exactly one twin — a fibrin gel
contracture assay (`twin.py`/`score.py`/`design.py`), calibrated on real
MPhil data. The user's stated intent is that **every calibrated assay gets
its own stochastic twin**, and `optimize`/`baseline`/`chat`/`advise`/`api`/
`pipeline` all dispatch to whichever one a request names, through a shared
registry rather than each tool assuming there is only one apparatus.

A second twin (`bleomycin_lung` — murine bleomycin-induced pulmonary
fibrosis, with an MSC-treatment arm) was built as the first real test of
that pattern. **Checkpoint 1 is done and merged. Checkpoints 2–4 are not.**

## What's done (checkpoint 1 — PR #13, merged)

New files, all on `main`:

- `refute/twins.py` — the registry. `AssayTwin` frozen dataclass (key,
  design spec type, score function, default capacity), `TWINS: dict[str,
  AssayTwin]`. `fibrin_contracture` registers the existing, untouched
  `DesignSpec`/`score_design`/`PLATE_WELLS`. `bleomycin_lung` registers the
  new pieces below. **Read this file's module docstring before adding
  anything** — it states why there's no forced shared base class (duck
  typing over premature unification, matching `ScopeTerm.__iter__`
  elsewhere in this codebase).
- `refute/bleomycin_calibration.py` — every numeric constant, each tagged
  LITERATURE / DERIVED / ASSUMED (this assay has no MEASURED tier — nothing
  is this project's own primary data). Sourced from `assays/bleomycin_lung.py`
  (already-promoted registry constants) plus a 2026-08-16 literature sweep
  memo on MSC therapy. **Read the module docstring in full** — it documents
  six specific judgment calls (mortality→hazard-rate conversion, the MSC
  effect size range, the timing-regime step function, the IV-procedural-
  mortality import-by-analogy, and why `mortality_severity_coupling`
  defaults to exactly 0.0) that a continuation must not silently redo or
  contradict.
- `refute/bleomycin_design.py` — `BleomycinDesignSpec` (pydantic): arms
  (`bleomycin_only`, `bleomycin_MSC`), `replicates_per_condition`,
  `msc_dosing_day`, `msc_route` (`IT`|`IV`), `endpoint_day`,
  `out_of_twin_scope` (same discipline as the fibrin `DesignSpec` — a
  design naming an uncalibrated drug must refuse to score, not silently
  drop it).
- `refute/bleomycin_twin.py` — `AnimalResult`/`CohortResult`/
  `BleomycinTwin`. The one mechanism worth understanding before touching
  this file: each animal gets **one shared latent normal draw `z`** that
  determines both its Ashcroft severity (`mean + sd*z`) and — only when
  `mortality_severity_coupling > 0` — its hazard rate
  (`base_hazard * exp(coupling*z)`). At the twin's default coupling=0,
  death is independent of z, so survivors are an unbiased sample of the
  population. This is deliberate: the survivorship-bias mechanism the whole
  project is about should be something a sensitivity sweep REVEALS, not
  something a hardcoded default manufactures. **Known residual, documented
  in the file**: a small nonzero bias appears even at coupling=0 because
  Ashcroft score is floored at 0 (can't go negative) — a real biology
  effect, not a bug, and the scorer's diagnostic text is gated on
  `coupling > 0` specifically so this residual is never misreported as
  evidence of the coupling mechanism.
- `refute/bleomycin_score.py` — `BleomycinScore`/`score_bleomycin_design`.
  Compares Ashcroft among **survivors** between arms (t-test). Reports
  `survivorship_bias_ashcroft` — the gap between the twin's injected true
  MSC effect and what survivors actually show, the one diagnostic
  `score.py` has no equivalent of. Generalizes `score.py`'s single hardcoded
  aprotinin sensitivity check to a list (`bleomycin_calibration.ASSUMED_RANGES`),
  swept one-at-a-time, only for constants a given design actually reaches
  (see `_reaches()`).
- Tests: `tests/test_bleomycin_twin.py`, `tests/test_bleomycin_score.py`,
  `tests/test_twins_registry.py` — 28 tests, all passing. The load-bearing
  one is `test_survivorship_bias_diagnostic_fires_once_coupling_is_swept_positive`
  — if you change the coupling mechanism, this must still pass.

Full suite at merge: **785 passed, 6 skipped.**

Also merged earlier the same session, for context if needed:
PR #9 (six-scaffold literature calibration), #10 (vocabulary scope fields),
#11 (`refute optimize` — the design optimizer, human-facing only, tripwire-
tested to never be importable by `agent.py`/`environment.py`/`api.py`, see
`optimize.py`'s module docstring for the full Goodhart reasoning — the
bleomycin twin's future optimizer must follow the exact same discipline),
#12 (promoted `bleomycin_lung` to LITERATURE tier in the assay registry —
distinct from the twin; that promotion made the registry honest, this
checkpoint made it scoreable).

## What's NOT done — checkpoints 2, 3, 4

These were explicitly scoped and approved in the plan this session worked
from (the plan file itself lived at `~/.claude/plans/structured-nibbling-glade.md`
on the Claude Code side — **that path is local to that session and Antigravity
will not have access to it**, which is the whole reason this handoff exists
as a self-contained document instead of just pointing there).

### Checkpoint 2 — CLI dispatch + bleomycin's own optimize/advise
- `cmd_baseline`/`cmd_optimize` in `cli.py` gain `--assay` (default
  `fibrin_contracture`, so every existing invocation keeps working
  unchanged), dispatching design-file parsing and scoring through
  `twins.TWINS`.
- `refute/bleomycin_optimize.py` — a second, **independent**
  `optimize_bleomycin_design()`, NOT a generalized `optimize.py`. The
  search space is genuinely different (dosing day + route + n, not
  imaging schedule + n) — two parallel, independently-tested functions
  unified only at the registry/CLI layer, matching the design decision
  already made for the twin/score split. Same Goodhart discipline as
  `optimize.py`: **`msc_route` must have no default** (IV vs IT changes
  real biology and procedural risk, not a free search knob — mirrors why
  `optimize.py`'s `antifibrinolytic` has no default), a winner that only
  clears its target via an ASSUMED constant must be rejected unless the
  caller explicitly opts in, and `agent.py`/`environment.py`/`api.py` need
  a tripwire test proving they never import it (extend the existing
  parametrized tripwire test in `tests/test_optimize.py` to cover both
  files rather than writing a second copy).
- `refute/bleomycin_advise.py` — mirrors `advise.py`'s lever-generator
  pattern (add MSC arm / move dosing earlier / switch IT↔IV / increase n).
  Same `MAX_COMBINE_ROUNDS`-style bound `advise.py` already uses, for the
  same stated reason (a bounded, readable chain of simulated steps, not an
  unbounded search against the twin).

### Checkpoint 3 — the handoff seam
- `intake.py` — `extract_design()`'s return type is currently hardcoded to
  the fibrin `DesignSpec`. Make it assay-dependent: once assay selection
  (already generic — reads `AssayProtocol` fields off the registry, no
  model call involved) picks a key, extraction should build
  `twins.TWINS[key].design_spec_type` instead of assuming `DesignSpec`.
  Assay-selection logic itself needs no change.
- `pipeline.py` — the `TIER1` route's `score = score_design(design,
  n_sims=n_sims)` becomes `score = twins.TWINS[protocol.key].score_fn(design,
  n_sims=n_sims)`. `protocol.key` already flows through
  `resolver.resolve(protocol.key, requirements)` at the point this call
  happens, so this should be close to a one-line change — `resolve.py`/
  `gate.py`/`requirements.py` are already assay-generic (they read
  `protocol.all_constants()`, not fibrin-specific fields) and should not
  need touching.

### Checkpoint 4 — chat and the API
- `chat.py` — gains `--assay`; picks `design_spec_type`/`score_fn` from the
  registry for its per-turn simulation calls. The conversational loop
  itself (ask → apply delta → re-simulate → report) should stay as-is —
  only the two dispatch points change.
- `api.py` — `/score` and `/score/text` gain an `assay` field (default
  `fibrin_contracture`), dispatching request parsing and scoring through
  the registry. `/assays` needs no change — it already reads the registry
  generically. **`/run` is explicitly out of scope, on purpose, not an
  oversight**: it's the agent-under-test benchmark loop, and generalizing
  "design Experiment 4" into "design an experiment for any calibrated
  assay" is a real reframing of what the project measures, not a plumbing
  change. Leave it fibrin-only unless the user says otherwise.

## Build order and verification

Same discipline as checkpoint 1 — don't batch checkpoints 2–4 into one PR.
Per checkpoint: implement, write/extend tests, run the full suite, commit,
push, open a PR, merge, delete the branch. This session's git flow for
reference (all four checkpoints so far followed it):

```
git checkout -b <branch-name>
# ... implement, test ...
python -m pytest -q          # must show 0 failed before committing
git add -A && git commit -m "..."
git push -u origin <branch-name>
gh pr create --base main --head <branch-name> --title "..." --body "..."
gh pr merge <N> --merge
git push origin --delete <branch-name>
```

Never push to `main` directly. Never force-push.

## The one thing to get right that isn't in the code

Every number in this codebase that isn't primary data carries an explicit
LITERATURE/DERIVED/ASSUMED tag and a stated reason. If checkpoint 2's
`bleomycin_optimize.py` or checkpoint 4's `api.py` wiring surfaces a
judgment call that isn't already covered by an existing tag or docstring —
don't invent a number silently. Flag it in the PR description the way this
session flagged the `mortality_severity_coupling` default, the MSC
effect-size range, and the `/run`-stays-fibrin-only scoping decision. The
project's own thesis is that silently-resolved uncertainty is the failure
mode worth catching; the build should not reintroduce it in its own
architecture.

---

## Where to put this file

This file belongs at the **repo root**, alongside `PLAN.md`/`HANDOFF.md`/
`BUILD.md` (i.e. exactly where it already is if you're reading it from the
checkout — `ANTIGRAVITY_HANDOFF.md`, not inside `refute/` or `tests/`).
Keep the name distinct from `HANDOFF.md` so the two are never confused —
that file is a different, still-relevant document about a different seam.
Once checkpoints 2–4 are merged, this file has served its purpose and can
be deleted (or folded into `PLAN.md`'s own status table, which is where the
rest of the project's build history lives) — it is a task-scoped handoff,
not a permanent project doc.
