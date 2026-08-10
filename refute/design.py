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
    out_of_twin_scope: list[str] = Field(
        default_factory=list,
        description=(
            "ONLY substitutions that change the apparatus being simulated. The "
            "simulator models an anchored FIBRIN gel, contracted by fibroblasts, "
            "measured as GEL AREA from images, failing by FIBRINOLYSIS.\n"
            "Record here only: a different matrix material (collagen, PEG, "
            "Matrigel); a readout that is not gel area (gene expression, "
            "stiffness, immunostaining); a different vessel or anchoring scheme; "
            "or an added intervention that changes scaffold degradation and is "
            "not an antifibrinolytic.\n"
            "Leave this EMPTY for ordinary protocol detail, which the simulator "
            "does not need and which is not a deviation: gel formulation and "
            "concentrations, cell seeding density, media composition, serum, "
            "antibiotics, growth factor doses, medium changes, the units the "
            "area is reported in, the statistical analysis plan, and "
            "well-exclusion or QC criteria. A design that merely SPECIFIES the "
            "fibrin assay in detail belongs here NOT AT ALL."
        ),
    )
    rationale: str = Field(
        default="", description="One or two sentences on why this design."
    )

    @property
    def total_wells(self) -> int:
        return len(self.conditions) * self.replicates_per_condition

    def fits_plate(self, plate_wells: int) -> bool:
        return self.total_wells <= plate_wells

    @property
    def assigns_wells(self) -> bool:
        """False when the design declines to run the experiment at all.

        Not a malformed spec. An agent told that the apparatus cannot resolve the
        effect may answer that no plate should be cast - which is the verdict this
        project itself reports, so the scorer must be able to tell it apart from a
        design that simply performs badly. See `score_design`.
        """
        return bool(self.conditions) and self.replicates_per_condition > 0

    def unmodelled(self) -> list[str]:
        """Scope violations worth refusing over, blanks discarded.

        An extractor emitting a stray empty string must not block a design the
        twin can handle perfectly well. That error would be conservative rather
        than permissive, but a verifier that cries wolf gets switched off, so it
        is still worth not making.
        """
        return [r for r in self.out_of_twin_scope if r and r.strip()]


class OutOfTwinScopeError(RuntimeError):
    """Raised when a design does something the twin cannot represent.

    The twin models one apparatus: an anchored fibrin gel, imaged for area,
    failing by fibrinolysis. A design that changes the matrix, the seeding
    density, or the readout is not a worse design - it is a design about which
    this twin has nothing to say.

    Scoring it anyway is the dangerous case, and the reason this raises rather
    than warns. The extractor is instructed not to improve a design, so an
    unrepresentable feature would simply be dropped, and the twin would return a
    confident number for a plate nobody proposed. That is an error in the
    permissive direction - the one direction a verifier must not fail in.
    """

    def __init__(self, reasons: list[str]):
        self.reasons = list(reasons)
        detail = "\n".join(f"    - {r}" for r in self.reasons)
        super().__init__(
            "this design specifies something the twin does not model, so no "
            "score would be about the design that was proposed:\n"
            f"{detail}\n"
            "  The twin covers: anchored fibrin gel, area readout, "
            "fibrinolytic scaffold loss, imaging schedule, replication.\n"
            "  This is a limit of the twin, not a defect in the design."
        )


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
