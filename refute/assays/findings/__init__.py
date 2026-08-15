"""Per-scaffold calibration findings, one module each.

Split by protocol rather than kept in `literature.py` because the sweep that
produces them runs one searcher per scaffold, and a single shared file is a
merge conflict by construction.

Each module exports one `REPORT: CalibrationReport`. `literature.py` collects
them; nothing else should import from here directly.

THE RULE FOR EVERYTHING IN THIS PACKAGE
---------------------------------------
A constant recorded as found must carry a real source and the sentence it came
from. A constant recorded as `NOT_REPORTED` must carry the query that came back
empty, because that reason is a claim about publishing practice and an
unevidenced claim is worthless for the argument it supports.

Anything not genuinely searched is `NOT_YET_SEARCHED`. That is the honest
default and it is not a failure - the whole point of the exercise is to measure
which constants the literature carries and which it does not, so a fabricated
find does not flatter the result, it destroys it.
"""

from __future__ import annotations

from . import (
    bleomycin_lung,
    cell_derived_matrix,
    fibrosis_on_chip,
    stiffness_drift,
    traction_force,
)

__all__ = [
    "bleomycin_lung",
    "cell_derived_matrix",
    "fibrosis_on_chip",
    "stiffness_drift",
    "traction_force",
]
