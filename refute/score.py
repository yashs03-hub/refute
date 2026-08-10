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

from dataclasses import dataclass, field, replace

import numpy as np
from scipy import stats

from .calibration import (
    APROTININ_HAZARD_SCALE_RANGE,
    DEFAULT_PARAMS,
    PLATE_WELLS,
    TwinParams,
)
from .design import DesignSpec, OutOfTwinScopeError
from .twin import ExperimentTwin, PlateResult, baseline_tolerance_h

ALPHA = 0.05
MIN_WELLS_PER_ARM = 2          # below this, no test is possible
HEADLINE_CONTRAST = ("N-T", "N-CM+T")
Z_80_POWER = 2.8               # z(1-a/2) + z(power) for a=0.05, power=0.80

# Above this fraction of wells lost, the effect gap can no longer be estimated:
# the survivors are a biased sample of their own arm. 20% rather than a round
# half because the loss is not random - it is concentrated in the most
# contractile wells, so a modest overall rate already removes a large share of
# the signal. Empirically, designs below this bound give a stable requirement
# (+/-4 wells per arm across seeds); Experiment 4 as run, at 50%, ranged 12-130.
MAX_LYSIS_FOR_EFFECT_ESTIMATE = 0.2


# A per-well endpoint ratio is a quotient, so its distribution has a heavy right
# tail: a baseline that happens to be measured small inflates the ratio without
# limit. `np.var` gives every point equal leverage, so one such well in tens of
# thousands dominates the estimate - measured at 0.21 robust versus 4.61 naive on
# a 120-well design, which then propagated straight into
# `min_detectable_ratio_diff` and `replicates_needed`.
#
# The scale factor makes MAD a consistent estimator of SD for Gaussian data, so
# on well-behaved arms this returns what `np.var` returned and nothing changes.
# It only differs where the naive estimate was being driven by its tail.
MAD_TO_SD = 1.4826


def _robust_sd(values: list[float]) -> float:
    """SD estimated via median absolute deviation.

    Falls back to the ordinary SD if the MAD is zero, which happens only for
    degenerate arms (every well identical) where there is no tail to guard
    against anyway.
    """
    arr = np.asarray(values, dtype=float)
    mad = float(np.median(np.abs(arr - np.median(arr))))
    if mad == 0.0:
        return float(np.std(arr, ddof=1))
    return MAD_TO_SD * mad


def _pooled_spread(plates: list[PlateResult]) -> tuple[float, float]:
    """(within-arm SD of endpoint ratios, |gap between the contrasted arms|).

    Both estimators are robust: the spread via MAD, the centre via the median.
    A single division artifact must not be able to move either, or the assay's
    precision floor becomes a statement about one anomalous well.
    """
    a, b = HEADLINE_CONTRAST
    xs: list[float] = []
    ys: list[float] = []
    for p in plates:
        ratios = p.ratios_by_condition()
        xs += ratios.get(a, [])
        ys += ratios.get(b, [])
    if len(xs) < 2 or len(ys) < 2:
        return float("nan"), 0.0
    sd = float(np.sqrt((_robust_sd(xs) ** 2 + _robust_sd(ys) ** 2) / 2.0))
    return sd, float(abs(np.median(ys) - np.median(xs)))


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
    n_conditions: int = 0
    diagnoses: list[str] = field(default_factory=list)

    # Whether this verdict survives the twin's own uncalibrated constants. Set
    # only when the design reaches one - most designs never do, so most scores
    # cost nothing extra and report False truthfully.
    verdict_sensitive_to_assumption: bool = False
    assumptions_in_play: list[str] = field(default_factory=list)
    power_range_under_assumptions: tuple[float, float] | None = None

    @property
    def failed(self) -> bool:
        return self.power < 0.5

    @property
    def feasibility(self) -> str:
        """Three distinct states that `infeasible_as_scoped` alone conflates.

        That flag is False both for a design that fits one plate and for one so
        destroyed that the requirement cannot be estimated at all - opposite
        situations. Naming them separately matters for sensitivity: a design
        whose data yield depends on an unmeasured constant is exactly the case
        worth flagging.
        """
        if self.replicates_needed <= 0:
            return "unestimable"
        return "infeasible" if self.infeasible_as_scoped else "feasible"

    @property
    def verdict(self) -> tuple[bool, str]:
        """The categorical claims this score makes.

        Sensitivity is judged on these rather than on power itself: power moving
        from 3% to 6% because of an assumed constant changes nothing anyone would
        act on, whereas crossing from 'this cannot work' to 'this works' does.
        """
        return (self.failed, self.feasibility)

    @property
    def infeasible_as_scoped(self) -> bool:
        """The apparatus cannot hold the replication the effect requires.

        Distinct from 'underpowered': no amount of care with a single plate
        fixes it. The honest verdict is that the question cannot be answered at
        this scale, which is a finding rather than a failure.
        """
        arms = max(self.n_conditions, 1)
        return self.replicates_needed > 0 and self.replicates_needed * arms > PLATE_WELLS

    def summary(self) -> str:
        lines = []
        if self.over_plate_capacity:
            lines.append(
                "!! exceeds the calibrated apparatus - the numbers below assume "
                "the assay scales beyond one plate, which is NOT calibrated "
                "(no data on between-cast or between-plate batch effects)."
            )
        if self.verdict_sensitive_to_assumption:
            lo, hi = self.power_range_under_assumptions or (float("nan"),) * 2
            lines.append(
                f"!! this verdict is NOT robust to the twin's assumptions - "
                f"power spans {lo:.0%}-{hi:.0%} across the plausible range of "
                f"{', '.join(self.assumptions_in_play)}. Read the single number "
                f"below as one point inside that span, not as a result."
            )
        lines += [
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
    check_assumptions: bool = True,
) -> DesignScore:
    """Simulate a design and report what the twin can say about it.

    Raises `OutOfTwinScopeError` if the design does something the twin does not
    model. Returning a number there would be an error in the permissive
    direction, which for a verifier is the one that matters.

    `check_assumptions` re-scores at the edges of every ASSUMED constant the
    design actually reaches, and flags a verdict that does not survive the span.
    Set it False to skip that (the recursive call does, to terminate).
    """
    unmodelled = design.unmodelled()
    if unmodelled:
        raise OutOfTwinScopeError(unmodelled)

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

    # The effect gap is estimated from wells that SURVIVED to the endpoint. When
    # a design loses a large share of them, the survivors are not a
    # representative sample of their arm - fibrinolysis takes the most
    # contractile wells first, so exactly the wells carrying the largest effect
    # are the ones missing. The estimate is then survivorship-biased, and
    # measurably unstable: for Experiment 4 as run (50% lost) it ranged 12 to 130
    # wells per arm across seeds and simulation counts, and did not converge at
    # n_sims=800. Designs that protect the scaffold sit inside +/-4.
    #
    # Refusing the number is the same move as `UncalibratedAssayError`: this is
    # the project's own survivorship argument applied to its own scorer, and a
    # confident figure derived from survivors would be exactly the error it
    # criticises elsewhere.
    if reps_needed > 0 and mean_lysed > MAX_LYSIS_FOR_EFFECT_ESTIMATE:
        diagnoses.append(
            f"cannot estimate the replication this effect needs: {mean_lysed:.0%} "
            f"of wells were lost before the endpoint, and fibrinolysis takes the "
            f"most contractile wells first - so the surviving sample is biased "
            f"against the very effect being measured. Fix the scaffold loss "
            f"first; the requirement is only estimable once wells survive."
        )
        reps_needed = -1
        mde = float("nan")

    if reps_needed > design.replicates_per_condition > 0 and reps_needed > 0:
        diagnoses.append(
            f"underpowered independently of scaffold survival: the endpoint "
            f"ratio carries ~{within_arm_sd:.2f} within-arm SD, so resolving the "
            f"true effect needs ~{reps_needed} wells per arm, not "
            f"{design.replicates_per_condition}. Measurement precision "
            f"(+/-2-3 fill-points on diffuse gel edges), not biology, is the "
            f"binding constraint."
        )

    # Saying "you need 47 per arm" without saying "and you have 12 wells total"
    # invites the agent to scale to 24 plates, which is a different experiment
    # the twin has no calibration for. The resource limit is already stated in
    # the brief, so restating it here reports a violated constraint rather than
    # supplying a fix.
    arms = max(len(design.conditions), 1)
    if reps_needed > 0 and reps_needed * arms > PLATE_WELLS:
        diagnoses.append(
            f"infeasible at this scale: {reps_needed} wells per arm across "
            f"{arms} arms is {reps_needed * arms} wells, and the assay as "
            f"calibrated is ONE {PLATE_WELLS}-well plate. No change to timing or "
            "formulation recovers this. The available moves are to narrow the "
            "contrast to fewer arms, to make the measurement itself more "
            "precise, or to report that the question cannot be answered at this "
            "scale - the last is a legitimate answer, not a failure."
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

    # Must match the twin's own rule, including the derived grace period after
    # t0 - a diagnosis that fires when the twin found a usable baseline anyway
    # would send the agent to fix something that is not broken.
    tol = baseline_tolerance_h(params)
    pre_t0 = [t for t in design.imaging_times_h if t <= design.treatment_time_h + tol]
    if not pre_t0:
        diagnoses.append(
            f"no imaging within {tol:.1f} h of t0, so no per-well pre-treatment "
            "baseline exists; between-well heterogeneity (observed ratio spread "
            "0.60-0.96) then swamps the treatment signal."
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

    score = DesignScore(
        power=power,
        testable_rate=testable_rate,
        mean_usable_wells=mean_usable,
        mean_lysed_fraction=mean_lysed,
        over_plate_capacity=over_capacity,
        identifies_contraction_kinetics=identifies_kinetics,
        min_detectable_ratio_diff=mde,
        replicates_needed=reps_needed,
        n_conditions=len(design.conditions),
        diagnoses=diagnoses,
    )

    if check_assumptions:
        _annotate_assumption_sensitivity(score, design, params, n_sims, seed)
    return score


# ---------------------------------------------------------------------------
# Assumption sensitivity
#
# The twin's soft spots are tagged ASSUMED in calibration.py, and one of them -
# how much an antifibrinolytic extends scaffold survival - is directly reachable
# by a design: setting one boolean multiplies the Weibull scale by a number
# nothing in Experiment 4 constrains.
#
# That makes it the one place a design can score well by finding a generous
# corner of the model rather than by being good. The response is not to remove
# the constant, which would be to pretend antifibrinolytics do nothing, but to
# refuse to present a verdict that depends on its value.
# ---------------------------------------------------------------------------


def _annotate_assumption_sensitivity(
    score: DesignScore,
    design: DesignSpec,
    params: TwinParams,
    n_sims: int,
    seed: int | None,
) -> None:
    """Re-score at the edges of each ASSUMED constant this design reaches."""
    if not design.antifibrinolytic:
        return  # the design never touches the assumed constant

    score.assumptions_in_play.append("aprotinin_hazard_scale")
    lo, hi = APROTININ_HAZARD_SCALE_RANGE

    # Same seed at both ends, so the comparison is paired and a difference is
    # the constant's doing rather than simulation noise.
    edges = [
        score_design(
            design,
            params=replace(params, aprotinin_hazard_scale=value),
            n_sims=n_sims,
            seed=seed,
            check_assumptions=False,
        )
        for value in (lo, hi)
    ]
    powers = [e.power for e in edges]
    score.power_range_under_assumptions = (min(powers), max(powers))

    if edges[0].verdict == edges[1].verdict:
        return  # the verdict holds across the whole plausible span

    score.verdict_sensitive_to_assumption = True
    score.diagnoses.append(
        f"this verdict depends on an ASSUMED constant. Aprotinin's effect on "
        f"scaffold survival was never measured in Experiment 4; across its "
        f"plausible range ({lo:g}x to {hi:g}x) the power of this design runs "
        f"{min(powers):.0%} to {max(powers):.0%} and the conclusion itself "
        f"changes. The design may be sound, but this twin cannot say so - "
        f"calibrating an antifibrinolytic arm is what would settle it."
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
