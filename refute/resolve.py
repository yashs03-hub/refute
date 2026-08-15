"""The seam between finding quantities and deciding what can be simulated.

Two builders meet here: one fills a requirement set from sources, the other
routes on what came back. This module is the contract, and it is written so the
downstream half can be finished before the upstream half exists.

THE PROPERTY THAT MAKES THAT POSSIBLE
-------------------------------------
**The gate routes on which quantities resolved and why the rest did not. It
never reads a value.** Only the simulator dereferences a number. So a
`ResolutionSet` whose every `value` is None still fully determines a route, and
the gate's entire test matrix can be hand-written JSON.

WHO OWNS THE REQUIREMENT LIST
-----------------------------
The registry, never the resolver. A resolver that derives its own requirements
will always report full coverage, because it only ever asks for what it can
answer. The list has to be exogenous to the thing filling it - which is why
`AssayProtocol` already declares its constants with `value=None` rather than
letting a search decide what mattered.

TOTALITY
--------
`ResolutionSet.resolutions` is total over the requirement set: every required
key has an entry, always. Partiality is therefore unrepresentable, and "we have
not got to it yet" is `NOT_YET_SEARCHED` rather than an absent key. A missing
key and a blocked key route differently, and if partiality were representable
the confusion between them would eventually ship.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Protocol

# `Provenance` is defined in `assays.evidence` and re-exported here, which is
# the reverse of where it looks like it belongs. This module already imports
# `BlockedReason` from there, and `Evidence` needs to name a provenance tier, so
# defining it here would be an unconditional import cycle rather than a latent
# one. Re-exporting keeps `from refute.resolve import Provenance` working: it is
# the same object, and this is still the module that routes on it.
from .assays.evidence import BlockedReason, Provenance


# Tier 0 is assay-blind arithmetic, so its requirements are not per-protocol.
# Deliberately tiny, and deliberately the shape literature actually prints:
# effect sizes and precisions get published, failure constants do not. That
# asymmetry is why the fallback is reliable when the primary path is not.
TIER0_NEEDS: tuple[str, ...] = ("effect_size", "within_arm_sd", "alpha", "n_per_arm")

# Above this fraction of ASSUMED constants, a tier-1 twin is not reporting a
# measurement any more, it is reporting its own priors.
MAX_ASSUMED_FRACTION = 0.5


@dataclass(frozen=True)
class Requirement:
    """One quantity a verdict depends on, declared by the registry."""

    key: str
    units: str
    what: str
    tier: str = "tier1"       # "tier1" | "tier0"
    query_hint: str = ""

    def __post_init__(self) -> None:
        if self.tier not in {"tier1", "tier0"}:
            raise ValueError(f"{self.key}: tier must be tier1 or tier0")


@dataclass(frozen=True)
class Resolution:
    """One quantity, either found or typed-blocked. Never both, never neither."""

    quantity: str
    # -- resolved --
    value: float | None = None
    units: str = ""
    provenance: Provenance | None = None
    source: str = ""
    quote: str = ""
    assumption: str = ""
    plausible_range: tuple[float, float] | None = None
    # -- blocked --
    reason: BlockedReason | None = None
    queries_run: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.value is not None and self.reason is not None:
            raise ValueError(f"{self.quantity}: cannot be both resolved and blocked")
        if self.value is None and self.reason is None:
            raise ValueError(
                f"{self.quantity}: must be resolved or carry a blocked reason - "
                "silence is the one thing this type exists to prevent"
            )
        if self.value is not None:
            if self.provenance is None:
                raise ValueError(f"{self.quantity}: a value needs a provenance")
            if not self.source:
                raise ValueError(f"{self.quantity}: a value needs a source")
            if self.provenance is Provenance.DERIVED and not self.assumption:
                raise ValueError(
                    f"{self.quantity}: a derived value must state its assumption, "
                    "or it is indistinguishable from a measured one"
                )
            if self.provenance is Provenance.ASSUMED and self.plausible_range is None:
                raise ValueError(
                    f"{self.quantity}: an assumed value must carry a plausible "
                    "range, or its verdict cannot be tested for sensitivity"
                )
        if self.reason is BlockedReason.NOT_REPORTED and not self.queries_run:
            raise ValueError(
                f"{self.quantity}: NOT_REPORTED is a claim about the literature "
                "and needs the query that came back empty. Use NOT_YET_SEARCHED."
            )

    @property
    def resolved(self) -> bool:
        return self.value is not None

    @property
    def blocks_tier1(self) -> bool:
        """Whether this stops a mechanistic twin being built.

        CONTEXT_DEPENDENT does NOT block. An ill-posed scalar is not an absent
        one - it becomes a swept range, and the verdict is reported as
        sensitive to it rather than withheld. That distinction is the one most
        likely to be collapsed by accident.
        """
        if self.resolved:
            return False
        return self.reason is not BlockedReason.CONTEXT_DEPENDENT


@dataclass(frozen=True)
class ResolutionSet:
    """A total answer to one requirement set."""

    assay_key: str
    requirement_version: str
    resolutions: Mapping[str, Resolution] = field(default_factory=dict)
    unmodelled_mentions: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """False while anything is unsearched, and the gate must not route.

        Routing on an incomplete set emits "not answerable at this scale" for an
        experiment that is merely unsearched. That is the most damaging wrong
        output this system can produce, because it is the one people quote.
        """
        return not any(
            r.reason is BlockedReason.NOT_YET_SEARCHED
            for r in self.resolutions.values()
        )

    def covers(self, needs: Iterable[str]) -> bool:
        return not self.missing(needs)

    def missing(self, needs: Iterable[str]) -> list[str]:
        """Required keys with no usable value. An absent key counts as missing."""
        out = []
        for k in needs:
            r = self.resolutions.get(k)
            if r is None or r.blocks_tier1:
                out.append(k)
        return sorted(out)

    def unsearched(self) -> list[str]:
        return sorted(
            k for k, r in self.resolutions.items()
            if r.reason is BlockedReason.NOT_YET_SEARCHED
        )

    def assumed(self, needs: Iterable[str]) -> list[str]:
        return sorted(
            k for k in needs
            if (r := self.resolutions.get(k)) is not None
            and r.provenance is Provenance.ASSUMED
        )

    def swept(self, needs: Iterable[str]) -> list[str]:
        """Keys that must be swept rather than fixed: assumed, or ill-posed."""
        out = set(self.assumed(needs))
        out |= {
            k for k in needs
            if (r := self.resolutions.get(k)) is not None
            and r.reason is BlockedReason.CONTEXT_DEPENDENT
        }
        return sorted(out)

    def over_assumed(self, needs: Iterable[str]) -> bool:
        needs = list(needs)
        if not needs:
            return False
        return len(self.assumed(needs)) / len(needs) > MAX_ASSUMED_FRACTION


class Resolver(Protocol):
    """Anything that can answer a requirement set. One method, deliberately."""

    name: str

    def resolve(
        self, assay_key: str, requirements: Iterable[Requirement]
    ) -> ResolutionSet: ...


# --- serialisation ----------------------------------------------------------
# Fixtures are JSON so they can be written by hand. They are simultaneously the
# gate's test inputs and the resolver's output specification, which is why the
# reader is strict: a fixture that would not survive the invariants is a fixture
# that does not describe a legal resolver output.

def resolution_from_dict(key: str, d: dict) -> Resolution:
    rng = d.get("plausible_range")
    return Resolution(
        quantity=key,
        value=d.get("value"),
        units=d.get("units", ""),
        provenance=Provenance(d["provenance"]) if d.get("provenance") else None,
        source=d.get("source", ""),
        quote=d.get("quote", ""),
        assumption=d.get("assumption", ""),
        plausible_range=tuple(rng) if rng else None,
        reason=BlockedReason(d["reason"]) if d.get("reason") else None,
        queries_run=tuple(d.get("queries_run", ())),
    )


def resolution_set_from_dict(d: dict) -> ResolutionSet:
    return ResolutionSet(
        assay_key=d["assay_key"],
        requirement_version=d.get("requirement_version", "unversioned"),
        resolutions={
            k: resolution_from_dict(k, v) for k, v in d.get("resolutions", {}).items()
        },
        unmodelled_mentions=tuple(d.get("unmodelled_mentions", ())),
    )


class FixtureResolver:
    """Replays a hand-written `ResolutionSet` from JSON.

    Not a stand-in to be deleted once the real resolver lands. It is what keeps
    the downstream half testable offline forever, exactly as `RecordedSource`
    does for `PaperclipSource` - and it is the only resolver that can be used in
    a test, because a live one would make the gate's behaviour depend on what a
    corpus happened to contain that day.
    """

    name = "fixture"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def resolve(
        self, assay_key: str, requirements: Iterable[Requirement]
    ) -> ResolutionSet:
        raw = json.loads(self.path.read_text())
        rs = resolution_set_from_dict(raw)
        if rs.assay_key != assay_key:
            raise ValueError(
                f"fixture is for assay {rs.assay_key!r}, asked for {assay_key!r}"
            )
        return rs
