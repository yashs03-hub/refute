"""Which twin scores which assay - the dispatch layer `optimize`/`baseline`
and (per the approved plan) `chat`/`advise`/`api`/`pipeline` all read.

Each assay owns its own `DesignSpec` type and its own score function -
`fibrin_contracture` keeps `design.DesignSpec`/`score.score_design` exactly
as they were (no refactor of shipped, heavily-tested code);
`bleomycin_lung` registers `bleomycin_design.BleomycinDesignSpec`/
`bleomycin_score.score_bleomycin_design`. They are unified only by a minimal
structural surface - `.power`, `.testable_rate`, `.summary()`,
`.verdict_sensitive_to_assumption` - not a forced shared base class. This
matches the codebase's existing preference for duck typing over premature
unification (see `assays/base.py`'s `ScopeTerm.__iter__`, which lets
`vocabulary.py` treat it as "a string or an iterable of them" without a
shared type).

Adding a THIRD twin means: write its own calibration/design/twin/score
modules (following either existing pair as a template), then add one line
here. Nothing that already dispatches through `TWINS` needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .bleomycin_calibration import DEFAULT_COHORT_CAPACITY
from .bleomycin_design import BleomycinDesignSpec
from .bleomycin_score import score_bleomycin_design
from .calibration import PLATE_WELLS
from .design import DesignSpec
from .score import score_design


@dataclass(frozen=True)
class AssayTwin:
    """One assay's design type, scorer, and default capacity."""

    key: str
    design_spec_type: type
    score_fn: Callable[..., Any]
    default_capacity: int


TWINS: dict[str, AssayTwin] = {
    "fibrin_contracture": AssayTwin(
        key="fibrin_contracture",
        design_spec_type=DesignSpec,
        score_fn=score_design,
        default_capacity=PLATE_WELLS,
    ),
    "bleomycin_lung": AssayTwin(
        key="bleomycin_lung",
        design_spec_type=BleomycinDesignSpec,
        score_fn=score_bleomycin_design,
        default_capacity=DEFAULT_COHORT_CAPACITY,
    ),
}

DEFAULT_ASSAY = "fibrin_contracture"


def get_twin(assay: str) -> AssayTwin:
    try:
        return TWINS[assay]
    except KeyError:
        raise KeyError(
            f"unknown assay {assay!r} for the twin registry. Registered: "
            f"{', '.join(sorted(TWINS))}. Note this is a SEPARATE list from "
            f"assays.REGISTRY - only assays with a working simulator are "
            f"here; a LITERATURE-tier registry entry does not imply one "
            f"exists yet, see that protocol's module docstring."
        ) from None


__all__ = ["DEFAULT_ASSAY", "TWINS", "AssayTwin", "get_twin"]
