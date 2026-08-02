"""Score a design by simulating it, not by judging it.

The score is the probability that the design recovers an injected treatment
effect. A design whose scaffold dissolves before its endpoint recovers nothing,
however well written its rationale is.

The headline contrast follows Experiment 4's own analysis plan: N-T vs N-CM+T
(does MSC-conditioned media blunt TGF-b1-driven contraction), tested with
Welch's t-test on per-well endpoint ratios, because n=3 does not support a
per-well curve fit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from .calibration import DEFAULT_PARAMS, PLATE_WELLS, TwinParams
from .design import DesignSpec
from .twin import ExperimentTwin, PlateResult

ALPHA = 0.05
MIN_WELLS_PER_ARM = 2          # below this, no test is possible
HEADLINE_CONTRAST = ("N-T", "N-CM+T")
Z_80_POWER = 2.8               # z(1-a/2) + z(power) for a=0.05, power=0.80


def _pooled_spread(plates: list[PlateResult]) -> tuple[float, float]:
    """(within-arm SD of endpoint ratios, |gap between the contrasted arms|)."""
    a, b = HEADLINE_CONTRAST
    xs: list[float] = []
    ys: list[float] = []
    for p in plates:
        ratios = p.ratios_by_condition()
        xs += ratios.get(a, [])
        ys += ratios.get(b, [])
    if len(xs) < 2 or len(ys) < 2:
        return float("nan"), 0.0
    sd = float(np.sqrt((np.var(xs, ddof=1) + np.var(ys, ddof=1)) / 2.0))
    return sd, float(abs(np.mean(ys) - np.mean(xs)))


@dataclass
class DesignScore:
    """What the twin says about a design."""

    power: float                      # P(recover the injected effect)
    testable_rate: float              # P(enough surviving wells to run any test)
    mean_usable_wells: float
    mean_lysed_fraction: float
    over_plate_capacity: bool
    identifies_contraction_kinetics: bool
    # Smallest endpoint-ratio difference this design could detect at 80% power,
    # and the replicates per arm the injected effect would actually need.
    min_detectable_ratio_diff: float = float("nan")
    replicates_needed: int = -1
    diagnoses: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.power < 0.5

    def summary(self) -> str:
        lines = [
            f"power to recover injected effect : {self.power:.0%}",
            f"plates yielding a testable result: {self.testable_rate:.0%}",
            f"mean usable wells per plate      : {self.mean_usable_wells:.1f}",
            f"mean fraction lysed by endpoint  : {self.mean_lysed_fraction:.0%}",
            f"min detectable ratio difference  : {self.min_detectable_ratio_diff:.3f}",
            f"replicates per arm actually needed: {self.replicates_needed}",
        ]
        if self.diagnoses:
            lines.append("")
            lines.append("why:")
            lines.extend(f"  - {d}" for d in self.diagnoses)
        return "\n".join(lines)


def _test_one_plate(plate: PlateResult) -> tuple[bool, bool]:
    """(testable, recovered) for a single simulated plate."""
    ratios = plate.ratios_by_condition()
    a, b = HEADLINE_CONTRAST
    xs, ys = ratios.get(a, []), ratios.get(b, [])
    if len(xs) < MIN_WELLS_PER_ARM or len(ys) < MIN_WELLS_PER_ARM:
        return False, False
    result = stats.ttest_ind(xs, ys, equal_var=False)
    # MSC-CM opposes TGF-b contraction, so N-CM+T should retain MORE area.
    recovered = bool(result.pvalue < ALPHA and np.mean(ys) > np.mean(xs))
    return True, recovered


def score_design(
    design: DesignSpec,
    params: TwinParams = DEFAULT_PARAMS,
    n_sims: int = 400,
    seed: int | None = 0,
) -> DesignScore:
    twin = ExperimentTwin(params=params, seed=seed)
    plates = twin.simulate_many(design, n_sims)

    outcomes = [_test_one_plate(p) for p in plates]
    testable_rate = float(np.mean([t for t, _ in outcomes]))
    power = float(np.mean([r for _, r in outcomes]))

    mean_usable = float(np.mean([len(p.usable_wells) for p in plates]))
    lysed = [
        np.mean(list(p.lysed_fraction.values())) if p.lysed_fraction else 0.0
        for p in plates
    ]
    mean_lysed = float(np.mean(lysed))

    # How precisely can this design measure a single arm, and what would it
    # take to resolve the effect that was injected? This is independent of
    # whether the scaffold survived - it is the assay's precision floor.
    within_arm_sd, observed_gap = _pooled_spread(plates)
    mde = float("nan")
    reps_needed = -1
    if not np.isnan(within_arm_sd) and within_arm_sd > 0:
        n = max(design.replicates_per_condition, 1)
        mde = float(Z_80_POWER * within_arm_sd * np.sqrt(2.0 / n))
        if observed_gap > 0:
            reps_needed = int(
                np.ceil(2.0 * (Z_80_POWER * within_arm_sd / observed_gap) ** 2)
            )

    diagnoses: list[str] = []

    if reps_needed > design.replicates_per_condition > 0 and reps_needed > 0:
        diagnoses.append(
            f"underpowered independently of scaffold survival: the endpoint "
            f"ratio carries ~{within_arm_sd:.2f} within-arm SD, so resolving the "
            f"true effect needs ~{reps_needed} wells per arm, not "
            f"{design.replicates_per_condition}. Measurement precision "
            f"(+/-2-3 fill-points on diffuse gel edges), not biology, is the "
            f"binding constraint."
        )

    if mean_lysed > 0.3:
        agent = "no antifibrinolytic in the formulation" if not design.antifibrinolytic \
            else "endpoint sits beyond scaffold survival even with an antifibrinolytic"
        diagnoses.append(
            f"{mean_lysed:.0%} of wells lost the scaffold before the "
            f"{design.endpoint_time_h:.0f} h endpoint ({agent}). "
            "Fibrinolysis is fastest in the most contractile arm, so the "
            "TGF-b arms fail first - exactly the arms the contrast needs."
        )

    pre_t0 = [t for t in design.imaging_times_h if t <= design.treatment_time_h]
    if not pre_t0:
        diagnoses.append(
            "no imaging before t0, so no per-well pre-treatment baseline exists; "
            "between-well heterogeneity (observed ratio spread 0.60-0.96) then "
            "swamps the treatment signal."
        )
    if not design.normalise_to_own_baseline:
        diagnoses.append(
            "endpoint not normalised to each well's own pre-treatment area; "
            "baseline heterogeneity alone spans a wider range than the effect."
        )

    early = [t for t in design.imaging_times_h if t <= 12]
    identifies_kinetics = len(early) >= 1
    if not identifies_kinetics:
        diagnoses.append(
            "first imaging is too late to characterise contraction: it was "
            "~94% complete by 24 h (half-time 5.8 h), so t0 and slope are "
            "unidentifiable and only an endpoint comparison is possible."
        )

    if not design.locked_imaging_protocol:
        diagnoses.append(
            "imaging protocol not controlled; uncontrolled frames segmented in "
            "roughly 1 of 10 attempts in the real experiment."
        )

    over_capacity = not design.fits_plate(PLATE_WELLS)
    if over_capacity:
        diagnoses.append(
            f"design needs {design.total_wells} wells; the assay as calibrated "
            f"is a single {PLATE_WELLS}-well plate."
        )

    if testable_rate < 0.9:
        diagnoses.append(
            f"only {testable_rate:.0%} of plates retained >= {MIN_WELLS_PER_ARM} "
            "wells per arm; attrition (cast failure, contamination) and lysis "
            "leave too little to test."
        )

    return DesignScore(
        power=power,
        testable_rate=testable_rate,
        mean_usable_wells=mean_usable,
        mean_lysed_fraction=mean_lysed,
        over_plate_capacity=over_capacity,
        identifies_contraction_kinetics=identifies_kinetics,
        min_detectable_ratio_diff=mde,
        replicates_needed=reps_needed,
        diagnoses=diagnoses,
    )


def feedback_for_agent(score: DesignScore) -> str:
    """The simulator's verdict, phrased for the agent's revision turn.

    Deliberately reports consequences, not corrections: it says the scaffold
    was gone before the endpoint, never 'add aprotinin'. The agent has to work
    out the fix - that is the part being benchmarked.
    """
    head = (
        f"Your design was simulated {'many times' if score.power else 'many times'}. "
        f"It recovered the true treatment effect in {score.power:.0%} of runs."
    )
    if not score.diagnoses:
        return head + " No structural failure modes were detected."
    body = "\n".join(f"- {d}" for d in score.diagnoses)
    return f"{head}\n\nWhat went wrong:\n{body}"
