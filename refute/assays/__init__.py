"""Assay registry.

One protocol is MEASURED (case 1). One is LITERATURE (bleomycin_lung, promoted
2026-08-16 - see that module's docstring for what promotion does and does not
mean; `runnable()` being true is not the same as `baseline`/`optimize` working,
since the simulator is still fibrin-gel-only). The rest are SCAFFOLDs:
structure declared, constants absent, and they will refuse to be scored until
calibrated.

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
from .bleomycin_lung import PROTOCOL as BLEOMYCIN_LUNG
from .fibrin_contracture import PROTOCOL as FIBRIN_CONTRACTURE
from .tier1 import TIER1

REGISTRY: dict[str, AssayProtocol] = {
    p.key: p for p in (FIBRIN_CONTRACTURE, BLEOMYCIN_LUNG, *TIER1)
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
    "BLEOMYCIN_LUNG",
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
