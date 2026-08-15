# Resolve loop → assay gate: the handoff

Two builders, one seam. This is what crosses it, in both directions, and the
four things that will silently break if they are not agreed first.

> **UPDATED 2026-08-16 — this was written as a plan and the downstream half is
> now built.** The tense has been corrected throughout; the reasoning has not
> been touched, because the reasoning is why the shapes are what they are and it
> is the only thing that will settle the next argument about them. Where a
> decision here was later made differently, both the decision and the change are
> recorded rather than the file being quietly brought into line.
>
> **Built, and tested, in this repository:**
>
> | | |
> |---|---|
> | `refute/resolve.py` | `Requirement`, `Resolution`, `ResolutionSet`, the `Resolver` protocol, JSON load, `FixtureResolver` |
> | `refute/requirements.py` | `tier1_needs()` off the protocol's own constants, `tier0_needs()`, requirement versioning |
> | `refute/gate.py` | `route_design()` → `RouteDecision`, five routes in precedence order |
> | `refute/pipeline.py` | the whole downstream walk: resolve → gate → simulate or tier 0 → advise, with a per-stage narrative |
> | `refute/adapt.py` | `RecordedResolver` — the 2026-08-04 literature findings crossing into a `ResolutionSet` |
> | `refute/handoff.py` | layer 1's `Handoff` / `Finding` / `OpenItem`, and their crossing into a requirement set |
> | `refute/intake.py` | residual prose → assay choice + `DesignSpec`, the step neither layer had picked up |
> | `cases/fixtures/` | seven hand-written resolution sets — see §6 |
> | `refute route` | runs it from a fixture (`--fixture`) or from the recorded findings (`--recorded --assay …`) |
>
> **Not built, and not this side's to build:** a live resolve loop. Both
> resolvers here replay something — a hand-written fixture, or what the
> 2026-08-04 literature pass actually found. Layer 1 owns the real one, and the
> point of the seam is that this half did not have to wait for it.
>
> **Closed while this note was being written:** `Resolution` now carries
> `origin_event`, so a layer-1 trace id survives into the resolution it produces
> rather than dying at the point a number stops being evidence and becomes an
> input the gate routes on. The divergence note in `handoff.py` still describes
> it as open and has not caught up.

## 0. The decision that determines everything else

**Who owns the requirement list — "what quantities does this verdict depend
on?"**

It must be the **assay registry**, not the resolve loop.

If the resolver derives its own requirement list, the system will always report
full coverage, because it only ever asks for what it can answer. The list has to
be **exogenous** to the thing filling it, exactly as `AssayProtocol` already
declares its constants with `value=None` and a `paperclip_query` alongside.

Practical consequence for the split: **you own the requirement sets, they own
filling them.** You can write and test the entire gate before the resolver
exists, and they can build the resolver against a requirement set that is
already frozen.

*2026-08-16 — this held.* `requirements.py` reads every tier-1 requirement off
`AssayProtocol.all_constants()` and invents none, and the entire gate, simulator
and advisor were finished against hand-written fixtures with no resolver in
existence. The prediction is recorded as having been tested, not as having been
made.

---

## 1. What the gate actually needs, and what it does not

The gate routes to one of four exits. Walk the decision and the dependency falls
out:

| Exit | Condition |
|---|---|
| `TIER1` | a calibrated protocol exists, the design is inside what it models, and every `tier1_needs` quantity resolved |
| `TIER0` | tier 1 unavailable, but every `tier0_needs` quantity resolved |
| `OUT_OF_SCOPE` | protocol exists, design proposes something it cannot model |
| `REFUSE` | neither — no twin and no variance estimate |

> **Corrected 2026-08-16 — there are five, and the fifth is a route.** `NOT_READY`
> is a member of `Route`, not an absence of one. §4 below already said *do not
> route at all* on an unsearched set, and building it that way exposed the
> problem with that phrasing: a caller that gets no route has to invent a
> behaviour, and the behaviour it will invent is a refusal. So the "do not
> route" instruction is now itself a route, checked first, before scope and
> before coverage.
>
> The precedence order matters as much as the set, and it is not the order of
> the table above. `gate.py` runs: **`NOT_READY` → `OUT_OF_SCOPE` → `TIER1` →
> `TIER0` → `REFUSE`.** Scope is checked before coverage because full coverage of
> the wrong apparatus is worse than no coverage — it produces a confident number
> about a plate nobody proposed.

**None of those conditions reads a value.** The gate needs *coverage and
provenance*; only `SIMULATE` needs the numbers. So:

> The gate is a function of **which** quantities resolved and **why** the rest
> did not. It never dereferences `value`.

That is the property that makes this parallelisable — build and test the gate
against a coverage map with every value set to `None`.

---

## 2. Resolver → gate: the payload

```python
Provenance = Literal["MEASURED", "PRIMARY", "LITERATURE", "DERIVED", "ASSUMED"]

class BlockedReason(Enum):
    NOT_REPORTED      = "not_reported"       # searched, and it is not there
    UNITS_MISMATCH    = "units_mismatch"     # published as a different quantity
    ASSAY_SPECIFIC    = "assay_specific"     # instrument-relative, not transferable
    CONTEXT_DEPENDENT = "context_dependent"  # ill-posed as a scalar
    NOT_YET_SEARCHED  = "not_yet_searched"   # no claim either way

@dataclass(frozen=True)
class Resolution:
    quantity: str                       # MUST match a registry key exactly
    # --- resolved ---
    value: float | None = None
    units: str = ""
    provenance: Provenance | None = None
    source: str = ""                    # DOI, tenant-local id, log id
    quote: str = ""                     # sentence, or a count statement
    assumption: str = ""                # REQUIRED when provenance == DERIVED
    plausible_range: tuple[float, float] | None = None
                                        # REQUIRED when ASSUMED
    # --- blocked ---
    reason: BlockedReason | None = None
    queries_run: tuple[str, ...] = ()   # REQUIRED to claim NOT_REPORTED

    @property
    def resolved(self) -> bool:
        return self.value is not None

@dataclass(frozen=True)
class ResolutionSet:
    assay_key: str
    requirement_version: str            # which registry revision this answers
    resolutions: Mapping[str, Resolution]   # TOTAL over the requirement set
    unmodelled_mentions: tuple[str, ...] = ()   # scope hints; the gate decides

    @property
    def complete(self) -> bool:
        """False while anything is NOT_YET_SEARCHED. The gate must not route."""
        return not any(r.reason is BlockedReason.NOT_YET_SEARCHED
                       for r in self.resolutions.values())

    def missing(self, needs: Iterable[str]) -> list[str]: ...
    def assumed(self, needs: Iterable[str]) -> list[str]: ...
```

**`resolutions` is total over the requirement set.** Every required key has an
entry, always. Partiality is then impossible by construction, and "we haven't
got to it" is `NOT_YET_SEARCHED` rather than a missing key. A missing key and a
blocked key route differently, and if partiality is representable you will
eventually ship the bug where they are confused.

### 2a. What shipped, and the three changes to the block above

*Recorded 2026-08-16. The block above is the proposal; `refute/resolve.py` is
the thing. It is close, and the differences are the interesting part.*

**1. A sixth blocked reason: `NOT_SUPPLIED`.** Added 2026-08-15, and it is a
correction rather than an extension. The tier-0 quantities — effect size,
within-arm SD, alpha, *n* per arm — were being filed as `ASSAY_SPECIFIC` when
blocked. That is not merely imprecise: it asserts something about publishing
practice for numbers no paper was ever going to carry. They are not corpus
quantities at all; they belong to the experimenter. Filing them under a
literature reason is this project's own criticism, committed in its own
taxonomy. No route moved — `NOT_SUPPLIED` blocks exactly as `ASSAY_SPECIFIC`
did — so the change is to what the tool *says*, not to what it decides.

The test of whether a reason earns its place is whether it routes to a different
*action*, and that is now explicit as `BlockedReason.the_fix`: `NOT_REPORTED`
means run a pilot, `NOT_YET_SEARCHED` means go and look, `NOT_SUPPLIED` means
tell the tool the number. Three different next steps that were collapsing into
one label.

**2. The invariants are enforced in `__post_init__`, not documented.** A
`Resolution` refuses to construct if it is both resolved and blocked, if it is
neither, if a value arrives with no provenance or no source, if a `DERIVED`
value states no assumption, if an `ASSUMED` value carries no `plausible_range`,
or if `NOT_REPORTED` arrives without the query that came back empty. Silence is
the one thing the type exists to prevent, so silence is the one thing it will
not represent.

**3. More accessors than proposed, because the gate needed to say why.**
`missing`, `assumed` and `complete` as above, plus `covers`, `unsearched`,
`swept` (assumed *or* ill-posed — the keys the simulator must sweep rather than
fix) and `over_assumed`. `Resolution.blocks_tier1` carries the
`CONTEXT_DEPENDENT` exception described in §4 so that no caller has to remember
it.

---

## 3. Gate → resolver: the other direction

Frozen by you, before they start — and frozen as written, 2026-08-15. Two
details settled since:

- `tier0_needs()` takes **no protocol**. Tier 0 is the arithmetic of a two-sample
  comparison and has no mechanism in it, so its four keys live in one place as
  `resolve.TIER0_NEEDS`. That is exactly why it is a usable fallback.
- `requirement_version` is real and is checked. It is a digest of the key list
  (`requirements.requirement_version`), and the pipeline **warns** rather than
  refuses on a skew, because a hand-written fixture legitimately carries a
  placeholder. The warning exists because a version skew presents as an honest
  refusal — every quantity reports missing because the keys moved — which is §5's
  first trap arriving by a different door.

```python
@dataclass(frozen=True)
class Requirement:
    key: str                      # THE contract. See §5.
    units: str
    what: str                     # human description, drives the query
    tier: Literal["tier1", "tier0"]
    query_hint: str = ""
```

Each protocol exposes `tier1_needs` and `tier0_needs`.

**Keep `tier0_needs` deliberately tiny and literature-shaped** — effect size,
variance estimate, alpha, n. That subset is *reliably* recoverable, whereas the
tier-1 hazard constants are the ones nobody publishes. The whole point of the
ladder is that the fallback rests on the kind of number the literature actually
prints, so the system degrades to something honest rather than to nothing.

---

## 4. The five reasons route differently — this is the load-bearing part

A boolean `blocked` flag is not enough. Each reason implies a different exit:

| Reason | What the gate does |
|---|---|
| `NOT_YET_SEARCHED` | **do not route at all.** `NOT_READY`, not a refusal. Routing here manufactures a premature "not answerable" |
| `NOT_REPORTED` | genuinely unfillable → tier 1 impossible → fall through to tier 0 |
| `UNITS_MISMATCH` | potentially recoverable by derivation. Hand back for one derivation attempt before treating as missing |
| `ASSAY_SPECIFIC` | not transferable → same as missing for tier 1 |
| `CONTEXT_DEPENDENT` | **does not block tier 1.** Converts a point value into a swept range. Requires `plausible_range` |

That fifth row is the one most likely to be got wrong. An ill-posed scalar is
not an absent one — it becomes a sensitivity sweep, and the verdict is reported
as sensitive-to-assumption rather than withheld.

Provenance matters to routing too: a tier-1 twin where most constants are
`ASSUMED` is not a twin. Set a threshold, and pass `plausible_range` through so
`SIMULATE` can sweep them and flag a verdict that does not survive the range.

**Sixth row, added 2026-08-15** — see §2a for why it is a correction rather than
an addition:

| Reason | What the gate does |
|---|---|
| `NOT_SUPPLIED` | the experimenter has not said. Blocks exactly as `ASSAY_SPECIFIC` does; the difference is that it claims nothing about the literature |

**The threshold is set.** `resolve.MAX_ASSUMED_FRACTION = 0.5`: above half the
tier-1 requirement set `ASSUMED`, the twin is reporting its own priors and the
gate routes `REFUSE` rather than `TIER1`. `over_assumed.json` pins it. The
sweep list reaches the simulator as `RouteDecision.sweep`, which carries the
assumed keys *and* the ill-posed ones, so the caller never has to reconstruct
the `CONTEXT_DEPENDENT` exception by hand.

---

## 5. The four things that will silently break

*Unchanged 2026-08-16, deliberately. All four are still live — each is now
guarded somewhere, and a guard is not the same as the problem going away. Where
they are pinned: key skew by `pipeline._version_warning` and the fixture
totality tests; the scope false positive by `test_gate.py`, which asserts a
canonical in-scope design routes `TIER1` as well as asserting the refusals; the
hint's non-authority by a test that a resolution set full of
`unmodelled_mentions` does **not** produce `OUT_OF_SCOPE` on its own;
`complete` by `NOT_READY` sitting first in the precedence order.*

**Key names are the real contract.** Freeze the exact strings before either of
you writes code. If they emit `p_detach_per_hour` and you expect
`p_detach_baseline_per_h`, every quantity reports missing and the gate refuses
everything — and it will look like an honest refusal, which is why nobody will
notice for hours.

**Write a false-positive test for the scope check.** This one is from
experience: refute's out-of-scope guard was once a fail-*always* guard — it
flagged the twin's own assay and its own readout as out of scope, and it passed
the suite, because there was a true-positive test and no test that a canonical
in-scope design routes to `TIER1`. "Refuse everything" satisfies every test that
only checks refusals. Pin both directions.

**Scope is yours, not theirs.** `OUT_OF_SCOPE` is a comparison between the
`DesignSpec` and the `AssayProtocol` — the resolver cannot see the design's
mechanism claims. `unmodelled_mentions` is a *hint* they may pass up; the gate
decides. Do not let that field become authoritative.

**`complete` must gate routing.** If you route on an incomplete set you will
emit "not answerable at this scale" for an experiment that is fine and merely
unsearched. That is the most damaging wrong output the system can produce,
because it is the one people will quote.

---

## 6. Fixtures — the whole gate test matrix, none needing the resolver

Written, and they live in `cases/fixtures/`. Seven of them, all against
`fibrin_contracture` — the one calibrated protocol — and all total over both
requirement sets. `tests/test_pipeline.py` holds the expected route for each and
`tests/test_resolve.py` checks that each one is a legal resolver output, which
is the same artefact serving both sides exactly as §7 intended.

| fixture | expected route |
|---|---|
| `full_coverage.json` | `TIER1` |
| `tier1_gaps_tier0_ok.json` | `TIER0` |
| `all_blocked.json` | `REFUSE` |
| `one_unsearched.json` | `NOT_READY` — **not** refuse |
| `context_dependent.json` | `TIER1`, verdict flagged sensitive |
| `unmodelled_mention.json` | `TIER1` — **corrected.** An earlier draft of this table said `OUT_OF_SCOPE`, which contradicted §5: a mention from a resolver that never saw the design cannot put a design out of scope. Scope must come from the `DesignSpec`. Drive the `OUT_OF_SCOPE` case from `design.out_of_twin_scope` instead |
| ~~`canonical_in_scope.json`~~ `over_assumed.json` | `REFUSE` — **changed 2026-08-16**, see below |

**Why the seventh fixture is not the one planned.** `canonical_in_scope.json`
was to be the false-positive guard against the fail-always story in §5. It was
not written, because a fixture is the wrong instrument for that guard: it would
have proved a *hand-written coverage map* routes `TIER1`, and the guard needs to
prove that **the real Experiment 4 design against the real protocol** does. That
lives in `test_gate.py`, where `EXPERIMENT_4_AS_RUN` is asserted to route
`TIER1`. `full_coverage.json` covers the fixture-shaped half. The guard is
stronger than planned, not weaker, but it is in a different place and the
original table would have sent you looking in the wrong one.

The slot went instead to `over_assumed.json`, which pins the threshold §4 only
said to *set*: a set whose tier-1 constants are more than half `ASSUMED` routes
`REFUSE`. That case did not exist in the plan and is the one a resolver is most
likely to produce by accident, because assuming is the cheapest way to fill a
requirement.

Every value in them can be `null` except where the route depends on it. That is
the proof that the gate never dereferences a value — and it is two tests, not a
convention. `test_resolve.py` re-routes every fixture with each number replaced
by a different number and asserts the routing summary does not move.
`test_gate.py` goes further and routes a set whose values are tripwire objects
that raise on any attempt to read them.

---

## 7. Order of work — and where it got to

1. ~~**Together, 20 minutes:** freeze `Requirement` keys per assay, `tier1_needs`
   and `tier0_needs`, and the `Resolution` / `ResolutionSet` shapes.~~
   **Done.** Frozen unilaterally rather than together, which is the one departure
   worth flagging: the keys are read off `AssayProtocol`, so they were already
   determined by the registry and there was nothing for layer 1 to negotiate. The
   *biological vocabulary* is a different question and it is **not** settled —
   `refute/vocabulary.py` declares this side's terms, leaves an empty alias map,
   and prints the size of the gap. It must not be cited as an agreement.
2. ~~**You:** write the seven fixtures.~~ **Done** — seven, §6, one of them not
   the one planned.
3. ~~**Split.**~~ **Done on this side.** Gate, simulate, advise and the terminal
   all exist, and `pipeline.py` walks them in order with a narrative. The other
   side of the split is layer 1's and is not in this repository.
4. **Integrate** — *in progress, and it started before a real resolver existed.*
   `adapt.RecordedResolver` crosses the recorded 2026-08-04 literature findings
   into a `ResolutionSet`, so the downstream half is already exercised on real
   recovery rates rather than on a description of them. `refute route --recorded
   --assay <key>` runs it. Replacing that with live resolver output is the step
   that remains.

The seam is one type in each direction, and the fixtures are the second type's
documentation. Nothing else should cross.

**One thing crossed that this plan did not anticipate.** The seam above starts
at a `ResolutionSet`, which presumes somebody has already chosen the assay and
turned the residual question into a `DesignSpec`. Layer 1 does not do that — its
spec says so explicitly, and it is right, because it does not know what the
protocols can measure. Nothing on this side did it either. `refute/intake.py` is
that missing step: residual prose in, a ranked assay choice and a `DesignSpec`
out, with assay selection deterministic and no model call. A seam described as
"one type in each direction" turned out to have a gap on the near side of it.
