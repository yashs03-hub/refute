# Resolve loop → assay gate: the handoff

Two builders, one seam. This is what crosses it, in both directions, and the
four things that will silently break if they are not agreed first.

---

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

---

## 3. Gate → resolver: the other direction

Frozen by you, before they start:

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

---

## 5. The four things that will silently break

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

Hand-write these and you can finish the gate today:

| fixture | expected route |
|---|---|
| `full_coverage.json` | `TIER1` |
| `tier1_gaps_tier0_ok.json` | `TIER0` |
| `all_blocked.json` | `REFUSE` |
| `one_unsearched.json` | `NOT_READY` — **not** refuse |
| `context_dependent.json` | `TIER1`, verdict flagged sensitive |
| `unmodelled_mention.json` | `OUT_OF_SCOPE` |
| `canonical_in_scope.json` | `TIER1` — the false-positive guard |

Every value in them can be `null` except where the route depends on it. That is
the proof that the gate never dereferences a value.

---

## 7. Order of work

1. **Together, 20 minutes:** freeze `Requirement` keys per assay, `tier1_needs`
   and `tier0_needs`, and the `Resolution` / `ResolutionSet` shapes.
2. **You:** write the seven fixtures. Hand them over — they are also the
   resolver's output spec, so this is the same artefact serving both sides.
3. **Split.** They fill `ResolutionSet`; you build gate, simulate, advise and
   the terminal.
4. **Integrate** by replacing one fixture at a time with real resolver output.

The seam is one type in each direction, and the fixtures are the second type's
documentation. Nothing else should cross.
