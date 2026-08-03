"""Assay protocols — the part of a twin that changes between assays.

The twin's engine does not change from assay to assay: units evolve over time,
some fail before the endpoint, some are lost to attrition, and what survives is
measured imperfectly. What changes is four things:

  1. the experimental unit      (well / gel / chip / animal)
  2. the readout                (area fraction / force / collagen / fibrosis score)
  3. the hazard                 (what removes a unit, and what drives it)
  4. the measurement model      (precision, and what protocol it depends on)

An `AssayProtocol` declares those four. Everything else is shared.

THE RULE THIS FILE ENFORCES
---------------------------
A protocol whose constants are not calibrated **cannot produce a score**.
`score_design` refuses. This is not defensive programming; it is the whole
premise. The argument for this project is that its ground truth is measured
rather than invented, and a scaffold that quietly emitted plausible numbers
would be exactly the thing it criticises.

Scaffolds therefore declare their STRUCTURE — what fails, what drives it, what
is measured — while leaving every number `None`, alongside an explicit list of
what would have to be extracted to calibrate them, and the Paperclip query that
would find it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CalibrationStatus(Enum):
    """How much this protocol's numbers can be trusted."""

    MEASURED = "measured"
    """Constants fitted to primary data held in this repository. Case 1 only."""

    LITERATURE = "literature"
    """Constants extracted from published methods/troubleshooting sections.
    Weaker than MEASURED: inherits whatever those papers got wrong, and
    published failure rates are the ones authors chose to report."""

    SCAFFOLD = "scaffold"
    """Structure declared, numbers absent. Cannot be scored."""


@dataclass(frozen=True)
class Constant:
    """A numeric constant that knows whether it is real."""

    name: str
    value: float | None
    units: str
    provenance: str

    @property
    def missing(self) -> bool:
        return self.value is None


@dataclass(frozen=True)
class HazardSpec:
    """What removes an experimental unit before the endpoint.

    `driver` is the field that matters most. The assays worth twinning are the
    ones where the driver is the phenotype being measured - where succeeding at
    the biology is what destroys the readout. A hazard that is merely a function
    of time is real but ordinary, and a plain power calculation loses less by
    ignoring it.
    """

    mechanism: str
    driver: str
    driver_is_the_measured_phenotype: bool
    mitigation: str | None = None
    constants: tuple[Constant, ...] = ()


@dataclass(frozen=True)
class ReadoutSpec:
    """What is measured, and how well."""

    name: str
    units: str
    direction: str  # "decreases" | "increases" with the fibrotic phenotype
    destructive: bool  # True => one measurement per unit, no time course
    constants: tuple[Constant, ...] = ()


@dataclass(frozen=True)
class AssayProtocol:
    key: str
    name: str
    unit: str
    status: CalibrationStatus
    readout: ReadoutSpec
    hazard: HazardSpec
    summary: str
    why_it_matters: str
    calibration_needs: tuple[str, ...] = ()
    paperclip_query: str | None = None
    attrition_constants: tuple[Constant, ...] = ()
    notes: str = ""
    references: tuple[str, ...] = field(default_factory=tuple)

    # -- calibration gate --------------------------------------------------

    def all_constants(self) -> tuple[Constant, ...]:
        return (
            self.readout.constants
            + self.hazard.constants
            + self.attrition_constants
        )

    def missing_constants(self) -> list[Constant]:
        return [c for c in self.all_constants() if c.missing]

    @property
    def runnable(self) -> bool:
        """True only if every constant has a value AND the status admits it."""
        return (
            self.status is not CalibrationStatus.SCAFFOLD
            and not self.missing_constants()
        )

    def require_runnable(self) -> None:
        """Raise unless this protocol may legitimately produce a score."""
        if self.runnable:
            return
        missing = self.missing_constants()
        detail = (
            "\n".join(f"    - {c.name} ({c.units}): {c.provenance}" for c in missing)
            or "    (none missing, but status is SCAFFOLD)"
        )
        raise UncalibratedAssayError(
            f"'{self.key}' is a {self.status.value} protocol and cannot be scored.\n"
            f"  Missing constants:\n{detail}\n"
            f"  To calibrate, obtain:\n"
            + "\n".join(f"    - {n}" for n in self.calibration_needs)
            + (
                f"\n  Suggested Paperclip query:\n    {self.paperclip_query}"
                if self.paperclip_query
                else ""
            )
        )


class UncalibratedAssayError(RuntimeError):
    """Raised when something tries to score a scaffold."""
