"""A proposed cohort, in the terms the bleomycin twin can simulate.

Mirrors `design.py`'s `DesignSpec` in spirit - a typed, validated shape a
design has to fit before the twin will touch it - but the free variables are
different because the apparatus is different. `DesignSpec` describes a
fibrin gel plate (imaging schedule, antifibrinolytic). This describes a
mouse cohort (dosing day, route, endpoint day). Trying to force one shared
schema to cover both would produce a type with fields that are meaningless
for whichever apparatus didn't originate them - exactly the kind of
premature unification this codebase avoids elsewhere (see `ScopeTerm`'s
duck-typed `__iter__` rather than a forced common base).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Canonical condition names this twin understands. A design naming anything
# else has left the twin's scope - see `out_of_twin_scope` below.
BLEOMYCIN_ONLY = "bleomycin_only"
BLEOMYCIN_MSC = "bleomycin_MSC"
CANONICAL_CONDITIONS = (BLEOMYCIN_ONLY, BLEOMYCIN_MSC)


class BleomycinDesignSpec(BaseModel):
    """A proposed cohort - arms, dosing, route, endpoint."""

    conditions: list[str] = Field(
        description=(
            "Cohort arms. Use the canonical names: 'bleomycin_only' "
            "(no MSC), 'bleomycin_MSC' (MSC administered after bleomycin)."
        )
    )
    replicates_per_condition: int = Field(
        description="Animals per arm, as designed (before any attrition)."
    )

    msc_dosing_day: float = Field(
        default=3.0,
        description=(
            "Days post-bleomycin MSC is administered. Only meaningful for "
            "arms named bleomycin_MSC. See bleomycin_calibration.py's "
            "EARLY_DOSING_CUTOFF_DAY for why this field, not a categorical "
            "early/late label, is what the twin actually consumes."
        ),
    )
    msc_route: str = Field(
        default="IT",
        description=(
            "'IT' (intratracheal) or 'IV' (intravenous). IV carries an "
            "added procedural-mortality term this twin models and IT does "
            "not - see bleomycin_calibration.py's P_IV_PROCEDURAL_DEATH."
        ),
    )

    endpoint_day: float = Field(
        default=21.0,
        description="Day post-bleomycin the cohort is scored and euthanised.",
    )

    out_of_twin_scope: list[str] = Field(
        default_factory=list,
        description=(
            "ONLY substitutions that change the apparatus being simulated: "
            "a drug other than MSC (no calibrated effect exists for it - "
            "see the tocilizumab/bevacizumab/verteporfin sweeps, none of "
            "which reached a usable number for this or any assay); a "
            "readout other than Ashcroft score; a species other than "
            "mouse. Leave EMPTY for ordinary protocol detail the simulator "
            "does not need: bleomycin dose/strain, MSC cell count, "
            "euthanasia criteria beyond the endpoint day, housing."
        ),
    )
    rationale: str = Field(
        default="", description="One or two sentences on why this design."
    )

    @property
    def total_animals(self) -> int:
        return len(self.conditions) * self.replicates_per_condition

    def fits_cohort(self, capacity: int) -> bool:
        return self.total_animals <= capacity

    @property
    def assigns_animals(self) -> bool:
        """False when the design declines to run the experiment at all.

        Same property `DesignSpec.assigns_wells` protects: a design that
        correctly concludes no cohort at this scale would work has to be
        distinguishable from one that simply performs badly.
        """
        return bool(self.conditions) and self.replicates_per_condition > 0

    def unmodelled(self) -> list[str]:
        """Scope violations worth refusing over, blanks discarded."""
        return [r for r in self.out_of_twin_scope if r and r.strip()]


class OutOfTwinScopeError(ValueError):
    """Raised when a design specifies something this twin does not model."""

    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__(
            "design specifies something outside this twin's scope:\n"
            + "\n".join(f"  - {r}" for r in reasons)
        )


DEFAULT_BLEOMYCIN_DESIGN = BleomycinDesignSpec(
    conditions=[BLEOMYCIN_ONLY, BLEOMYCIN_MSC],
    replicates_per_condition=10,
    msc_dosing_day=3.0,
    msc_route="IT",
    endpoint_day=21.0,
)


__all__ = [
    "BLEOMYCIN_MSC",
    "BLEOMYCIN_ONLY",
    "CANONICAL_CONDITIONS",
    "BleomycinDesignSpec",
    "DEFAULT_BLEOMYCIN_DESIGN",
    "OutOfTwinScopeError",
]

