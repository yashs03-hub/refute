"""Assay registry.

One protocol is MEASURED (case 1). The rest are SCAFFOLDs: structure declared,
constants absent, and they will refuse to be scored until calibrated.

    from refute.assays import REGISTRY, get
    get("scar_in_a_jar").require_runnable()   # raises UncalibratedAssayError
"""

from __future__ import annotations

from .base import (
    AssayProtocol,
    CalibrationStatus,
    Constant,
    HazardSpec,
    ReadoutSpec,
    UncalibratedAssayError,
)
from .fibrin_contracture import PROTOCOL as FIBRIN_CONTRACTURE
from .tier1 import TIER1

REGISTRY: dict[str, AssayProtocol] = {
    p.key: p for p in (FIBRIN_CONTRACTURE, *TIER1)
}


def get(key: str) -> AssayProtocol:
    try:
        return REGISTRY[key]
    except KeyError:
        raise KeyError(
            f"unknown assay '{key}'. Known: {', '.join(sorted(REGISTRY))}"
        ) from None


def runnable() -> list[AssayProtocol]:
    """Protocols that may legitimately produce a score."""
    return [p for p in REGISTRY.values() if p.runnable]


def scaffolds() -> list[AssayProtocol]:
    """Protocols awaiting calibration."""
    return [p for p in REGISTRY.values() if not p.runnable]


__all__ = [
    "FIBRIN_CONTRACTURE",
    "REGISTRY",
    "AssayProtocol",
    "CalibrationStatus",
    "Constant",
    "HazardSpec",
    "ReadoutSpec",
    "UncalibratedAssayError",
    "get",
    "runnable",
    "scaffolds",
]
