"""What was found, what was not, and why not.

The second half is the point. Recovering a constant from the literature is
ordinary; establishing that a constant is *systematically absent* is a claim
about publishing practice, and it is the claim this project rests on.

So a failed lookup is not an empty result here - it is a typed one. The reason
a constant could not be filled distinguishes four quite different situations,
only one of which is about the literature:

    NOT_REPORTED       nobody publishes it. The survivorship class.
    UNITS_MISMATCH     published, but as a different quantity.
    ASSAY_SPECIFIC     published, but instrument-relative and not transferable.
    CONTEXT_DEPENDENT  the constant is ill-posed as a scalar.
    NOT_YET_SEARCHED   no claim either way. The honest default.

NOT_YET_SEARCHED exists to stop the headline number being inflated by silence.
"We could not find X" and "we did not look for X" support very different
conclusions, and a dataset that conflates them is worthless for the argument it
is meant to support - so `Blocked` refuses to claim NOT_REPORTED without
recording the query that came back empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BlockedReason(Enum):
    NOT_REPORTED = "not_reported"
    UNITS_MISMATCH = "units_mismatch"
    ASSAY_SPECIFIC = "assay_specific"
    CONTEXT_DEPENDENT = "context_dependent"
    NOT_YET_SEARCHED = "not_yet_searched"

    @property
    def is_a_claim_about_the_literature(self) -> bool:
        """True for reasons asserting something about what gets published.

        These require evidence of having searched. The others are properties of
        the constant or the instrument and need no corpus to establish.
        """
        return self is BlockedReason.NOT_REPORTED


@dataclass(frozen=True)
class Evidence:
    """A constant recovered from a source, with the words that support it."""

    constant: str
    value: float
    units: str
    source: str              # DOI, or another stable identifier
    quote: str               # the sentence the number came from
    derived: bool = False    # computed from reported quantities, not read off
    assumption: str = ""     # required when derived
    note: str = ""

    def __post_init__(self) -> None:
        if self.derived and not self.assumption:
            raise ValueError(
                f"{self.constant}: a derived value must state the assumption it "
                "rests on, or it is indistinguishable from a measured one"
            )
        if not self.source:
            raise ValueError(f"{self.constant}: evidence needs a source")

    @property
    def provenance(self) -> str:
        tag = "DERIVED" if self.derived else "LITERATURE"
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
