"""What the bleomycin twin says about a cohort design.

Mirrors `score.py`'s structure and its central discipline: report
consequences, flag every number that rests on an assumption, and never
average an ASSUMED constant's plausible range into a false point estimate.

THE ONE DIAGNOSTIC THIS SCORER ADDS THAT `score.py` HAS NO EQUIVALENT OF
--------------------------------------------------------------------------
Because the twin injects a KNOWN true MSC effect (`params.msc_ashcroft_effect`)
and then removes some animals to death before they can be scored, the gap
between that injected truth and what the design's SURVIVORS actually show is
directly computable - not just describable. `survivorship_bias_ashcroft`
reports exactly that gap, averaged over simulated cohorts. At the twin's
default `mortality_severity_coupling=0` this number is small but not exactly
0 - see `bleomycin_twin.py`'s "KNOWN RESIDUAL" note, a floor effect from
Ashcroft's own boundedness, not survivorship. The diagnostic TEXT below is
gated on `coupling > 0` for exactly this reason: the field is always
computed, but only read as evidence of the mechanism once the mechanism is
actually switched on. Sweeping the coupling constant upward makes the true
bias move, and the direction is always toward
UNDERSTATING the effect: the untreated arm loses more of its severe animals
than the treated arm does (its hazard is higher), so its survivor mean is
pulled down further, which SHRINKS the observed gap between arms relative to
the true one. This is the project's own headline finding, produced as a
number from a second, independently-built apparatus rather than asserted
again in prose.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from dataclasses import replace as _replace

import numpy as np
from scipy import stats

from .bleomycin_calibration import (
    ASSUMED_RANGES,
    DEFAULT_BLEOMYCIN_PARAMS,
    BleomycinTwinParams,
)
from .bleomycin_design import BLEOMYCIN_MSC, BLEOMYCIN_ONLY, BleomycinDesignSpec
from .bleomycin_twin import BleomycinTwin, CohortResult

ALPHA = 0.05
MIN_ANIMALS_PER_ARM = 2          # below this, no test is possible
Z_80_POWER = 2.8

# The one contrast this scorer tests, mirroring `score.py`'s
# `HEADLINE_CONTRAST`. A design missing either arm scores a flat 0%, for a
# reason unrelated to sample size - see `optimize.py`'s module docstring for
# the fibrin-side version of this exact footgun, found the hard way earlier
# this session.
HEADLINE_CONTRAST = (BLEOMYCIN_ONLY, BLEOMYCIN_MSC)


@dataclass
class BleomycinScore:
    """What the twin says about a cohort design."""

    power: float                        # P(recover the injected MSC effect)
    testable_rate: float                # P(enough survivors to run any test)
    mean_animals_scored: float
    mean_mortality_by_condition: dict[str, float]
    n_conditions: int = 0
    diagnoses: list[str] = field(default_factory=list)

    # The mechanism this file adds - see module docstring.
    survivorship_bias_ashcroft: float = float("nan")

    replicates_needed: int = -1

    verdict_sensitive_to_assumption: bool = False
    assumptions_in_play: list[str] = field(default_factory=list)
    power_range_under_assumptions: tuple[float, float] | None = None

    declined: bool = False

    @property
    def failed(self) -> bool:
        return self.power < 0.5

    @property
    def verdict(self) -> tuple[bool, bool]:
        return (self.failed, self.testable_rate < 0.5)

    @property
    def feasibility(self) -> str:
        if self.declined:
            return "declined"
        if self.replicates_needed <= 0:
            return "unestimable"
        n_conds = self.n_conditions or 2
        if self.replicates_needed * n_conds > 40:
            return "infeasible"
        return "feasible"

    @property
    def infeasible_as_scoped(self) -> bool:
        return self.feasibility == "infeasible"


    def summary(self) -> str:
        if self.declined:
            return (
                "DECLINED - this design assigns no animals.\n\n"
                "It is not a failed design; it is the claim that no cohort "
                "at this scale would resolve the effect.\n\n"
                + "\n".join(f"  - {d}" for d in self.diagnoses)
            )
        lines: list[str] = []
        if self.verdict_sensitive_to_assumption:
            lo, hi = self.power_range_under_assumptions or (float("nan"),) * 2
            lines.append(
                f"!! this verdict is NOT robust to the twin's assumptions - "
                f"power spans {lo:.0%}-{hi:.0%} across the plausible range of "
                f"{', '.join(self.assumptions_in_play)}. Read the single "
                f"number below as one point inside that span."
            )
        reps = "not estimable" if self.replicates_needed <= 0 else str(self.replicates_needed)
        lines += [
            f"power to recover injected MSC effect : {self.power:.0%}",
            f"cohorts yielding a testable result    : {self.testable_rate:.0%}",
            f"mean animals scored per cohort         : {self.mean_animals_scored:.1f}",
            f"animals per arm actually needed        : {reps}",
        ]
        for cond, m in sorted(self.mean_mortality_by_condition.items()):
            lines.append(f"  mortality, {cond:<16}: {m:.0%}")
        if not math.isnan(self.survivorship_bias_ashcroft):
            lines.append(
                f"survivorship bias (true - measured effect): "
                f"{self.survivorship_bias_ashcroft:+.2f} Ashcroft points"
            )
        if self.diagnoses:
            lines.append("")
            lines.append("why:")
            lines.extend(f"  - {d}" for d in self.diagnoses)
        return "\n".join(lines)


def _test_one_cohort(cohort: CohortResult) -> tuple[bool, bool]:
    """(testable, recovered) for a single simulated cohort."""
    scored = cohort.scored_by_condition()
    a, b = HEADLINE_CONTRAST
    xs, ys = scored.get(a, []), scored.get(b, [])
    if len(xs) < MIN_ANIMALS_PER_ARM or len(ys) < MIN_ANIMALS_PER_ARM:
        return False, False
    result = stats.ttest_ind(xs, ys, equal_var=False)
    # MSC reduces Ashcroft score, so the MSC arm should read LOWER.
    recovered = bool(result.pvalue < ALPHA and np.mean(ys) < np.mean(xs))
    return True, recovered


def score_bleomycin_design(
    design: BleomycinDesignSpec,
    params: BleomycinTwinParams = DEFAULT_BLEOMYCIN_PARAMS,
    n_sims: int = 400,
    seed: int | None = 0,
    check_assumptions: bool = True,
) -> BleomycinScore:
    """Simulate a cohort design and report what the twin can say about it.

    Raises `OutOfTwinScopeError` if the design does something the twin does
    not model. `check_assumptions` re-scores at the edges of every ASSUMED
    constant the design actually reaches; set False to skip (the recursive
    sweep call does, to terminate).
    """
    from .bleomycin_design import OutOfTwinScopeError

    unmodelled = design.unmodelled()
    if unmodelled:
        raise OutOfTwinScopeError(unmodelled)

    if not design.assigns_animals:
        return BleomycinScore(
            power=0.0, testable_rate=0.0, mean_animals_scored=0.0,
            mean_mortality_by_condition={}, n_conditions=len(design.conditions),
            declined=True,
            diagnoses=[
                "this design declines to run the experiment - no animals are "
                "assigned. Power and testability below are placeholders, not "
                "measurements."
            ],
        )

    twin = BleomycinTwin(params=params, seed=seed)
    cohorts = twin.simulate_many(design, n_sims)

    outcomes = [_test_one_cohort(c) for c in cohorts]
    testable_rate = float(np.mean([t for t, _ in outcomes]))
    power = float(np.mean([r for _, r in outcomes]))

    mean_scored = float(np.mean([len(c.scored_by_condition().get(BLEOMYCIN_ONLY, []))
                                  + len(c.scored_by_condition().get(BLEOMYCIN_MSC, []))
                                  for c in cohorts]))

    mortality_by_cond: dict[str, list[float]] = {}
    for c in cohorts:
        for cond, m in c.mortality_by_condition.items():
            mortality_by_cond.setdefault(cond, []).append(m)
    mean_mortality = {c: float(np.mean(v)) for c, v in mortality_by_cond.items()}

    diagnoses: list[str] = []

    # -- the survivorship-bias diagnostic ------------------------------------
    survivorship_bias = float("nan")
    if BLEOMYCIN_MSC in design.conditions and BLEOMYCIN_ONLY in design.conditions:
        gaps = []
        for c in cohorts:
            scored = c.scored_by_condition()
            xs, ys = scored.get(BLEOMYCIN_ONLY, []), scored.get(BLEOMYCIN_MSC, [])
            if xs and ys:
                gaps.append(float(np.mean(xs)) - float(np.mean(ys)))
        if gaps:
            measured_gap = float(np.mean(gaps))
            regime = 1.0 if design.msc_dosing_day <= params.early_dosing_cutoff_day \
                else params.late_dosing_effect_multiplier
            true_gap = params.msc_ashcroft_effect * regime
            survivorship_bias = true_gap - measured_gap
            if params.mortality_severity_coupling > 0 and abs(survivorship_bias) > 0.1:
                diagnoses.append(
                    f"survivorship bias detected: the injected true effect is "
                    f"{true_gap:.2f} Ashcroft points, but surviving animals show "
                    f"only {measured_gap:.2f} - a gap of {survivorship_bias:+.2f}. "
                    f"The untreated arm's higher mortality removes more of its "
                    f"severe animals than the treated arm's lower mortality "
                    f"removes from its own, so the measured effect understates "
                    f"the true one. This is at "
                    f"mortality_severity_coupling={params.mortality_severity_coupling:g}, "
                    f"not the twin's own default of 0 - see "
                    f"bleomycin_calibration.py."
                )

    # -- replication requirement (arithmetic, not survival) ------------------
    all_scored: list[float] = []
    for c in cohorts:
        scored = c.scored_by_condition()
        all_scored += scored.get(BLEOMYCIN_ONLY, []) + scored.get(BLEOMYCIN_MSC, [])
    within_arm_sd = float(np.std(all_scored, ddof=1)) if len(all_scored) > 2 else float("nan")
    reps_needed = -1
    if not math.isnan(within_arm_sd) and within_arm_sd > 0:
        gap_for_power = params.msc_ashcroft_effect
        reps_needed = int(np.ceil(2.0 * (Z_80_POWER * within_arm_sd / gap_for_power) ** 2))

    if reps_needed > design.replicates_per_condition > 0:
        diagnoses.append(
            f"underpowered on the effect alone: resolving "
            f"{params.msc_ashcroft_effect:.2f} Ashcroft points at "
            f"~{within_arm_sd:.2f} within-arm SD needs ~{reps_needed} animals "
            f"per arm, not {design.replicates_per_condition}."
        )

    if testable_rate < 0.9:
        diagnoses.append(
            f"only {testable_rate:.0%} of cohorts retained "
            f">= {MIN_ANIMALS_PER_ARM} scored animals per arm; mortality and "
            f"dosing failure leave too little to test."
        )

    for cond, m in mean_mortality.items():
        if m > 0.3:
            diagnoses.append(f"{m:.0%} mortality in '{cond}' before the endpoint.")

    score = BleomycinScore(
        power=power,
        testable_rate=testable_rate,
        mean_animals_scored=mean_scored,
        mean_mortality_by_condition=mean_mortality,
        n_conditions=len(design.conditions),
        diagnoses=diagnoses,
        survivorship_bias_ashcroft=survivorship_bias,
        replicates_needed=reps_needed,
    )

    if check_assumptions:
        _annotate_assumption_sensitivity(score, design, params, n_sims, seed)
    return score


# ---------------------------------------------------------------------------
# Assumption sensitivity - generalizes `score._annotate_assumption_sensitivity`
# from one hardcoded constant (aprotinin) to the list in
# `bleomycin_calibration.ASSUMED_RANGES`. One-at-a-time sweeps, not a full
# factorial cross-product: simpler, and consistent with how the fibrin
# scorer already does it for its single constant.
# ---------------------------------------------------------------------------

# Which field each ASSUMED constant reaches through, and the guard that
# decides whether a given design touches it at all - a design that never
# uses IV, for instance, is untouched by the IV-procedural-death constant.
def _reaches(name: str, design: BleomycinDesignSpec, params: BleomycinTwinParams) -> bool:
    if name in ("mortality_severity_coupling", "p_dosing_failure"):
        return True   # every design reaches these
    if name == "late_dosing_effect_multiplier":
        return (BLEOMYCIN_MSC in design.conditions
                and design.msc_dosing_day > params.early_dosing_cutoff_day)
    if name == "p_iv_procedural_death":
        return BLEOMYCIN_MSC in design.conditions and design.msc_route == "IV"
    return False


def _annotate_assumption_sensitivity(
    score: BleomycinScore,
    design: BleomycinDesignSpec,
    params: BleomycinTwinParams,
    n_sims: int,
    seed: int | None,
) -> None:
    """Re-score at the edges of each ASSUMED constant this design reaches."""
    touched = [name for name in ASSUMED_RANGES if _reaches(name, design, params)]
    if not touched:
        return

    all_powers = [score.power]
    any_verdict_change = False
    for name in touched:
        score.assumptions_in_play.append(name)
        lo, hi = ASSUMED_RANGES[name]
        edges = [
            score_bleomycin_design(
                design, params=_replace(params, **{name: value}),
                n_sims=n_sims, seed=seed, check_assumptions=False,
            )
            for value in (lo, hi)
        ]
        all_powers += [e.power for e in edges]
        if edges[0].verdict != edges[1].verdict:
            any_verdict_change = True

    score.power_range_under_assumptions = (min(all_powers), max(all_powers))
    if any_verdict_change:
        score.verdict_sensitive_to_assumption = True
        score.diagnoses.append(
            f"this verdict depends on ASSUMED constants "
            f"({', '.join(score.assumptions_in_play)}) that no source "
            f"measures. Power ranges {min(all_powers):.0%}-{max(all_powers):.0%} "
            f"across their plausible spans and the conclusion itself changes."
        )
