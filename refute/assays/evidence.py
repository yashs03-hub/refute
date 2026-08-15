"""What was found, what was not, and why not.

The second half is the point. Recovering a constant from the literature is
ordinary; establishing that a constant is *systematically absent* is a claim
about publishing practice, and it is the claim this project rests on.

So a failed lookup is not an empty result here - it is a typed one. The reason
a constant could not be filled distinguishes six quite different situations,
only one of which is about the literature:

    NOT_REPORTED       nobody publishes it. The survivorship class.
    UNITS_MISMATCH     published, but as a different quantity.
    ASSAY_SPECIFIC     published, but instrument-relative and not transferable.
    CONTEXT_DEPENDENT  the constant is ill-posed as a scalar.
    NOT_SUPPLIED       nobody's to publish. The experimenter has not said.
    NOT_YET_SEARCHED   no claim either way. The honest default.

NOT_YET_SEARCHED exists to stop the headline number being inflated by silence.
"We could not find X" and "we did not look for X" support very different
conclusions, and a dataset that conflates them is worthless for the argument it
is meant to support - so `Blocked` refuses to claim NOT_REPORTED without
recording the query that came back empty.

NOT_SUPPLIED was added later, for the tier-0 quantities: effect size, within-arm
SD, alpha, n per arm. None of them is a corpus quantity - no search could
recover them, because they belong to the experimenter rather than to the
literature. Before this existed they were being filed as ASSAY_SPECIFIC, which
is not merely imprecise but false: it asserts something about publishing
practice for a number no paper was ever going to carry. The taxonomy's job is
to route to the right next action, and these three are genuinely different -
NOT_REPORTED means run a pilot, NOT_YET_SEARCHED means go and look, and
NOT_SUPPLIED means simply tell the tool the number. See `the_fix`.

WHY `Provenance` LIVES HERE AND NOT IN `resolve`
------------------------------------------------
It reads as a `resolve.py` concept, and it was defined there. But `resolve`
already imports `BlockedReason` from this module, so an `Evidence` that names a
provenance tier in the other direction is an import cycle - and an
unconditional one rather than a latent one, because both names are needed at
class-definition time in both files. Moving the enum down here is the only
resolution that does not leave a deferred import waiting to fire the first time
somebody imports the two modules in the unlucky order.

`resolve` re-exports it, so `from refute.resolve import Provenance` still reads
the same object and no caller had to move. The dependency now runs strictly one
way: this module knows nothing about requirement sets, routing or the gate,
which is what lets the calibration layer be read on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BlockedReason(Enum):
    NOT_REPORTED = "not_reported"
    UNITS_MISMATCH = "units_mismatch"
    ASSAY_SPECIFIC = "assay_specific"
    CONTEXT_DEPENDENT = "context_dependent"
    NOT_SUPPLIED = "not_supplied"
    NOT_YET_SEARCHED = "not_yet_searched"

    @property
    def is_a_claim_about_the_literature(self) -> bool:
        """True for reasons asserting something about what gets published.

        These require evidence of having searched. The others are properties of
        the constant or the instrument and need no corpus to establish.
        """
        return self is BlockedReason.NOT_REPORTED

    @property
    def the_fix(self) -> str:
        """What the reader should actually do about it.

        The taxonomy earns its keep by routing to different actions, not by
        being a tidy set of labels. If two reasons imply the same next step,
        one of them is redundant.
        """
        return {
            BlockedReason.NOT_REPORTED: "run a pilot - the literature does not have it",
            BlockedReason.UNITS_MISMATCH: "convert it, and state the conversion",
            BlockedReason.ASSAY_SPECIFIC: "measure it on your own rig",
            BlockedReason.CONTEXT_DEPENDENT: "sweep it as a range rather than a point",
            BlockedReason.NOT_SUPPLIED: "tell the tool the number",
            BlockedReason.NOT_YET_SEARCHED: "search for it",
        }[self]


class Provenance(Enum):
    """Where a number came from. Ordered strongest first.

    `PRIMARY` outranks `LITERATURE` deliberately: a value counted off primary
    records - a lab notebook, a robot's execution log - is stronger evidence
    than one read out of a paper, because it has not passed through the
    publication filter that removes the runs that failed.
    """

    MEASURED = "measured"      # fitted to primary data held in this repository
    PRIMARY = "primary"        # counted off primary records (ELN, robot log)
    LITERATURE = "literature"  # extracted from a published methods section
    DERIVED = "derived"        # computed from reported quantities
    ASSUMED = "assumed"        # nobody's measurement; a stand-in with a range

    @property
    def is_evidence(self) -> bool:
        """False for ASSUMED. A twin built mostly of stand-ins is not a twin."""
        return self is not Provenance.ASSUMED


# The two tiers `derived` can express on its own, in the order the flag reads:
# False, then True. Inference uses this rather than an inline conditional so the
# mapping is stated once and can be pointed at from the adapter.
_DERIVED_TIER = {False: Provenance.LITERATURE, True: Provenance.DERIVED}

# Tiers that assert the number was read off something rather than computed. A
# derivation cannot honestly claim one: `derived=True` says a person did
# arithmetic, and these two say a person copied a figure down.
_READ_OFF_TIERS = (Provenance.LITERATURE, Provenance.PRIMARY)


@dataclass(frozen=True)
class Evidence:
    """A constant recovered from a source, with the words that support it.

    TWO WAYS OF SAYING WHERE IT CAME FROM, AND WHY BOTH ARE KEPT
    ------------------------------------------------------------
    `derived` is a two-valued flag, and for the literature pass that produced
    `literature.py` two values were all that could occur: a number was read out
    of a paper or computed from numbers read out of a paper. `provenance`
    renders that distinction as a string several modules read, and it still
    prints exactly what it always printed for anything that leaves `tier` unset.

    `tier` is the same claim in the five-valued vocabulary the resolver routes
    on. It exists because the flag has no way to say MEASURED, PRIMARY or
    ASSUMED, so a value counted off a lab notebook or a robot's execution log
    had to be recorded as though it had been published - which inverts the
    ordering the whole seam depends on, since primary records have not passed
    through the filter that removes the runs that failed.

    Leaving `tier` unset is the normal case and costs nothing: it is inferred
    from `derived` at construction, so every `Evidence` ever written keeps
    exactly the tier the adapter would otherwise have had to guess. Setting it
    is a deliberate refinement, and the two fields may not contradict each
    other - a reader that trusted `tier` and a reader that trusted `provenance`
    would otherwise disagree about the same number.
    """

    constant: str
    value: float
    units: str
    source: str              # DOI, or another stable identifier
    quote: str               # the sentence the number came from
    derived: bool = False    # computed from reported quantities, not read off
    assumption: str = ""     # required when derived
    note: str = ""
    tier: Provenance | None = None  # inferred from `derived` when left unset

    def __post_init__(self) -> None:
        if self.derived and not self.assumption:
            raise ValueError(
                f"{self.constant}: a derived value must state the assumption it "
                "rests on, or it is indistinguishable from a measured one"
            )
        if not self.source:
            raise ValueError(f"{self.constant}: evidence needs a source")

        # Inference, not a default, and it happens here rather than in a
        # property so that `tier` is never None on a constructed Evidence.
        # A field that is sometimes None and sometimes not is a field every
        # consumer has to re-derive, and they will not all re-derive it the
        # same way - which is the failure this whole module is shaped against.
        if self.tier is None:
            object.__setattr__(self, "tier", _DERIVED_TIER[self.derived])
            return

        if self.derived and self.tier in _READ_OFF_TIERS:
            raise ValueError(
                f"{self.constant}: derived=True says this number was computed, "
                f"tier={self.tier.value} says it was read off a source. Both are "
                "readable downstream, so one of them would be believed and the "
                "other would be a lie about the same value."
            )
        if self.tier is Provenance.DERIVED and not self.assumption:
            raise ValueError(
                f"{self.constant}: tier=derived must state the assumption it "
                "rests on - it is the same claim as derived=True and carries "
                "the same obligation"
            )

    @property
    def provenance(self) -> str:
        """The tag and the source, as a line a person can read.

        Unchanged for every `Evidence` that predates `tier`: the tag was
        `DERIVED` when `derived` and `LITERATURE` otherwise, and an inferred
        tier reproduces exactly that pair, so nothing that reads this string
        and matches on its prefix sees anything move. The tag widens only where
        the flag had nothing to say - printing "LITERATURE" over a number
        counted off a robot log would be a false statement about provenance in
        the one field whose job is to prevent them.

        (`tier` is never None after construction; the fallback restates the
        inference rather than relying on a reader to know that.)
        """
        tag = (self.tier or _DERIVED_TIER[self.derived]).name
        detail = f" - {self.assumption}" if self.assumption else ""
        return f"{tag} - {self.source}{detail}"


@dataclass(frozen=True)
class Blocked:
    """A constant that could not be filled, and the reason it could not be."""

    constant: str
    reason: BlockedReason
    detail: str
    searched: str = ""       # the query that came back empty

    def __post_init__(self) -> None:
        if self.reason.is_a_claim_about_the_literature and not self.searched:
            raise ValueError(
                f"{self.constant}: NOT_REPORTED asserts that the literature is "
                "silent, which requires having listened. Record the query, or "
                "use NOT_YET_SEARCHED."
            )


@dataclass(frozen=True)
class CalibrationReport:
    """The outcome of trying to calibrate one protocol."""

    key: str
    found: tuple[Evidence, ...]
    blocked: tuple[Blocked, ...]

    @property
    def total(self) -> int:
        return len(self.found) + len(self.blocked)

    @property
    def recovery_rate(self) -> float:
        return len(self.found) / self.total if self.total else 0.0

    def by_reason(self) -> dict[BlockedReason, int]:
        counts: dict[BlockedReason, int] = {}
        for b in self.blocked:
            counts[b.reason] = counts.get(b.reason, 0) + 1
        return counts

    @property
    def searched_constants(self) -> int:
        """Constants on which a claim can actually be made."""
        return len(self.found) + sum(
            1 for b in self.blocked if b.reason is not BlockedReason.NOT_YET_SEARCHED
        )

    def summary(self) -> str:
        lines = [
            f"{self.key}: {len(self.found)}/{self.total} constants recovered "
            f"({self.searched_constants} searched)"
        ]
        for e in self.found:
            flag = " [derived]" if e.derived else ""
            lines.append(f"  + {e.constant} = {e.value:g} {e.units}{flag}")
            lines.append(f"      {e.source}")
        for b in self.blocked:
            lines.append(f"  - {b.constant}: {b.reason.value}")
            lines.append(f"      {b.detail}")
        return "\n".join(lines)
