"""The structured form of a proposed experiment.

This is the contract between the two halves of the benchmark:

    free-text design  --(LLM extracts)-->  DesignSpec  --(twin simulates)-->  score

The split matters. Turning prose into these fields is an extraction task, which
language models do reliably. Deciding whether a design works is a judgement
task, which they do not - so that half is a simulator, not a judge.

Nothing here encodes an opinion about what a good design looks like. These are
the knobs the twin can act on; whether a setting is wise is decided by
simulating it, not by a rubric.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DesignSpec(BaseModel):
    """A proposed plate, in the terms the twin can simulate."""

    conditions: list[str] = Field(
        description=(
            "Experimental arms. Use the canonical names where they apply: "
            "'N-SS' (serum-starved control), 'N-T' (TGF-b1), "
            "'N-CM' (MSC-conditioned media), 'N-CM+T' (both)."
        )
    )
    replicates_per_condition: int = Field(
        description="Wells per arm, as designed (before any attrition)."
    )

    imaging_times_h: list[float] = Field(
        description=(
            "Every scheduled imaging timepoint, in HOURS SINCE CAST. "
            "Day 1 = 24, Day 5 = 120, Day 7 = 168, Day 10 = 240."
        )
    )
    treatment_time_h: float = Field(
        default=120.0,
        description="Hours since cast at which treatments are applied (t0).",
    )
    endpoint_time_h: float = Field(
        description="Hours since cast of the timepoint used as the primary endpoint."
    )

    antifibrinolytic: bool = Field(
        description=(
            "True if the fibrin formulation includes an antifibrinolytic "
            "(aprotinin, epsilon-aminocaproic acid, tranexamic acid)."
        )
    )
    antifibrinolytic_agent: str | None = Field(
        default=None, description="Named agent and concentration, if stated."
    )

    normalise_to_own_baseline: bool = Field(
        description=(
            "True if each well's endpoint is normalised to that same well's "
            "own pre-treatment measurement, rather than to a group mean or a "
            "shared baseline."
        )
    )
    locked_imaging_protocol: bool = Field(
        description=(
            "True if the design specifies a controlled imaging setup - fixed "
            "geometry, consistent illumination, per-well framing, an in-frame "
            "scale reference. False for ad-hoc or handheld whole-plate imaging."
        )
    )

    anticipates_scaffold_failure: bool = Field(
        default=False,
        description=(
            "True if the design explicitly reasons about the scaffold "
            "degrading before the endpoint - fibrinolysis, gel dissolution, "
            "constructs detaching from anchors."
        )
    )
    rationale: str = Field(
        default="", description="One or two sentences on why this design."
    )

    @property
    def total_wells(self) -> int:
        return len(self.conditions) * self.replicates_per_condition

    def fits_plate(self, plate_wells: int) -> bool:
        return self.total_wells <= plate_wells


# The design Experiment 4 actually used. The twin must reproduce its observed
# outcome from this spec - that is the calibration test in tests/.
EXPERIMENT_4_AS_RUN = DesignSpec(
    conditions=["N-SS", "N-T", "N-CM", "N-CM+T"],
    replicates_per_condition=3,
    imaging_times_h=[24, 72, 96, 120, 168, 240],
    treatment_time_h=120.0,
    endpoint_time_h=240.0,
    antifibrinolytic=False,
    antifibrinolytic_agent=None,
    normalise_to_own_baseline=True,
    locked_imaging_protocol=True,
    anticipates_scaffold_failure=False,
    rationale=(
        "The design as actually run in June 2026. No antifibrinolytic; first "
        "imaging at 24 h; Day 10 endpoint. Included as the twin's calibration "
        "target, not as a recommendation."
    ),
)
