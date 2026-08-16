"""What a verdict depends on, declared by the registry rather than the resolver.

`resolve.py` states the rule this module implements: **the registry owns the
requirement list, never the resolver.** A resolver that derives its own
requirements will always report full coverage, because it only ever asks for
what it can answer - and "we found everything we looked for" is a statement
about the search, not about the literature. The list has to be exogenous to the
thing filling it.

So nothing here invents a requirement. Every tier-1 requirement is read off a
declaration a protocol already makes: `AssayProtocol.all_constants()` names the
numbers the twin cannot run without, and it names them with `value=None` for
exactly this reason - the structure is asserted before any search decides what
mattered. If a constant is not in the protocol, it is not required; if it is in
the protocol, no resolver may quietly drop it.

TIER 0 IS ASSAY-BLIND
---------------------
`tier0_needs()` takes no protocol, because tier 0 is the arithmetic of a
two-sample comparison and has no mechanism in it. That is the whole reason it is
a usable fallback: its four quantities are the shape literature actually prints,
whereas the failure constants tier 1 needs are the ones nobody publishes.

VERSIONING
----------
`requirement_version` lets a `ResolutionSet` record which revision of the
registry it answers. It is a `hashlib` digest and not Python's `hash()`, which
is salted per process: a version that changed between two runs of the same code
would mark every stored resolution set stale on a restart, which is worse than
having no version at all because it would be discovered late and intermittently.

The digest itself lives in `digest.py`, which holds nothing but the algorithm
and imports nothing but `hashlib`. `adapt` and `handoff` compute the same digest
over the key lists they were actually handed, and until that module existed all
three carried their own copy of it. This one is the definition - it is the
registry's answer - and the other two must agree with it exactly or the pipeline
reports a version drift that is not there.
"""

from __future__ import annotations

import re

from .assays.base import AssayProtocol, Constant

# `VERSION_CHARS` is imported rather than declared, and stays importable from
# here for the callers that already read it off this module. The length is part
# of the digest contract, so it belongs next to the function that applies it.
from .digest import VERSION_CHARS, requirement_digest  # noqa: F401  (re-export)
from .resolve import TIER0_NEEDS, Requirement

# Provenance strings on a `Constant` are written "TAG - what it is". The tag
# describes the state of calibration, not the quantity, so it is stripped when
# the string is reused as a requirement description.
_PROVENANCE_TAGS = (
    "UNCALIBRATED",
    "FITTED",
    "MEASURED",
    "LITERATURE",
    "DERIVED",
    "PRIMARY",
    "ASSUMED",
)

# Tokens that carry no discriminating information when matching a constant name
# against a calibration need. Units and cardinality prefixes ("p_", "_h",
# "_pct") appear on almost every constant, and connectives appear in almost
# every sentence, so leaving them in would make everything match everything.
_UNINFORMATIVE = frozenset(
    {
        "a", "an", "and", "any", "are", "as", "at", "b", "be", "by", "d", "for",
        "failure", "from", "h", "in", "is", "it", "its", "n", "of", "on",
        "only", "or",
        "over", "p", "per", "pct", "rate", "report", "reported", "study",
        "studies", "that", "the", "this", "to", "typical", "value", "values",
        "vs", "whether", "which", "with", "x",
    }
)

# Crude stemming: compare the first six characters of anything long enough to
# have six. It is enough to fuse the pairs that actually occur here
# ("delaminate"/"delamination", "measurement"/"measured") without a dependency,
# and a wrong match only ever produces a less apt description - never a wrong
# requirement, because the key and units come from the constant itself.
_STEM_CHARS = 6


def tier1_needs(protocol: AssayProtocol) -> tuple[Requirement, ...]:
    """The quantities a mechanistic twin of `protocol` cannot run without.

    One requirement per declared constant, in declaration order (readout, then
    hazard, then attrition). Order is stable so that a diff between two versions
    of a protocol reads as an insertion rather than a reshuffle.

    Duplicate constant names raise. Two constants sharing a name would collapse
    into one entry in `ResolutionSet.resolutions`, which is keyed by name, and
    the totality guarantee - every required key has an entry - would silently
    become a lie about one of them.
    """
    needs: list[Requirement] = []
    seen: set[str] = set()
    for constant in protocol.all_constants():
        if constant.name in seen:
            raise ValueError(
                f"{protocol.key}: constant {constant.name!r} is declared twice. "
                "Resolutions are keyed by name, so a duplicate cannot be "
                "answered separately."
            )
        seen.add(constant.name)
        needs.append(
            Requirement(
                key=constant.name,
                units=constant.units,
                what=_what(constant, protocol.calibration_needs),
                tier="tier1",
                query_hint=protocol.paperclip_query or "",
            )
        )
    return tuple(needs)


def tier0_needs() -> tuple[Requirement, ...]:
    """The four quantities a two-sample power statement needs. No protocol.

    Deliberately not derived from an assay: tier 0 makes no mechanistic claim,
    which is what lets it answer for a comparison `refute` has never seen. The
    units are given in terms of the readout rather than absolutely, because the
    arithmetic only ever uses the ratio of effect to spread.

    There is no `query_hint`. These are not recovered from a corpus - they are
    supplied by the experimenter or taken off a pilot plate. `tier0.py` refuses
    to invent the variance estimate for the same reason this module refuses to
    suggest where to search for it.
    """
    described = {
        "effect_size": (
            "readout units",
            "The absolute difference between arms the experiment is intended to "
            "resolve. Not the difference hoped for - the smallest one that would "
            "change a decision.",
        ),
        "within_arm_sd": (
            "readout units (SD)",
            "Within-arm standard deviation of the readout, from a pilot, prior "
            "plates, or published replicates. Never a guess: an invented SD "
            "produces a confident power figure that looks like a calculation.",
        ),
        "alpha": (
            "probability",
            "Two-sided significance threshold. Conventionally 0.05, but it is "
            "stated rather than assumed so a design that moved it is visible.",
        ),
        "n_per_arm": (
            "units per arm",
            "Replicates per arm the design proposes, in whatever the "
            "experimental unit is (well, chip, animal).",
        ),
    }
    missing = set(TIER0_NEEDS) - set(described)
    if missing:
        raise ValueError(
            f"TIER0_NEEDS gained {sorted(missing)} without a description here. "
            "A requirement with no description cannot be searched for."
        )
    return tuple(
        Requirement(
            key=key,
            units=described[key][0],
            what=described[key][1],
            tier="tier0",
            query_hint="",
        )
        for key in TIER0_NEEDS
    )


def requirement_version(protocol: AssayProtocol) -> str:
    """A short stable identifier for `protocol`'s tier-1 requirement set.

    Over the declared constant names only - `digest.requirement_digest` states
    why the units and descriptions are left out of it, and why it sorts.

    This is the registry's answer, and therefore the one the others are checked
    against: `adapt` and `handoff` run the same digest over the keys they were
    handed, and `pipeline._version_warning` reports the difference when a stored
    answer is total over some other list than this one.
    """
    return requirement_digest(c.name for c in protocol.all_constants())


# --- description matching ---------------------------------------------------
# Cosmetic, and kept that way on purpose. The key and the units are read
# straight off the constant; only the human-readable `what` is guessed at. A bad
# guess here degrades a search prompt. It cannot produce a requirement that does
# not exist, or drop one that does.


def _what(constant: Constant, calibration_needs: tuple[str, ...]) -> str:
    """The best available description of one constant.

    Prefers the protocol's own `calibration_needs` sentence when one clearly
    refers to this constant, because those sentences are written for a person
    doing the extraction and say what would count as an answer. Falls back to
    the constant's declared provenance detail, which is terser but always
    present - and is the only thing available for a protocol that is already
    calibrated and therefore lists no outstanding needs.
    """
    matched = _match_need(constant.name, calibration_needs)
    return matched if matched is not None else _detail(constant.provenance)


def _detail(provenance: str) -> str:
    """Strip the leading calibration tag from a provenance string."""
    for tag in _PROVENANCE_TAGS:
        prefix = f"{tag} - "
        if provenance.startswith(prefix):
            return provenance[len(prefix):]
    return provenance


def _match_need(name: str, calibration_needs: tuple[str, ...]) -> str | None:
    """The calibration need sharing the most word stems with `name`, if any.

    Ties break toward the earliest declared need. Protocols list their needs
    roughly in order of importance, and an arbitrary tiebreak would make the
    output depend on set iteration order, which is exactly the kind of thing
    that makes a version hash unstable later.
    """
    wanted = _stems(name)
    if not wanted:
        return None
    best: tuple[int, str] | None = None
    for need in calibration_needs:
        score = len(wanted & _stems(need))
        if score and (best is None or score > best[0]):
            best = (score, need)
    return best[1] if best else None


def _stems(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return frozenset(
        w[:_STEM_CHARS] for w in words if w not in _UNINFORMATIVE
    )


__all__ = ["requirement_version", "tier0_needs", "tier1_needs"]
