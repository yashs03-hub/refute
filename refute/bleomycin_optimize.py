"""Search for the cheapest bleomycin design that clears a power target.

`PLAN.md` §9.1 and `optimize.py` state the Goodhart boundary: **"a benchmark is
not an environment, but a search over designs is"**. This module is an
independent optimizer for the bleomycin lung twin apparatus.

THE BOUNDARY THIS MODULE MUST NOT CROSS
----------------------------------------
No harness is given this module. `optimize_bleomycin_design` calls
`score_bleomycin_design` directly in a loop, which is a search against
`bleomycin_twin.py`'s equations rather than against biology. `agent.py`,
`environment.py` and `api.py` must never import this module -
`tests/test_optimize.py` pins that with a tripwire test covering both optimize
modules.

WHAT IS SEARCHED, AND WHAT IS NOT
-----------------------------------
Only `replicates_per_condition` and `msc_dosing_day` are searched.

`msc_route` is deliberately NOT searched and carries NO default. IV vs IT
changes real biology and procedural risk (`P_IV_PROCEDURAL_DEATH`), not a free
search knob - mirroring why `optimize.py`'s `antifibrinolytic` has no default.
The caller must state it explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bleomycin_calibration import (
    DEFAULT_BLEOMYCIN_PARAMS,
    DEFAULT_COHORT_CAPACITY,
    BleomycinTwinParams,
)
from .bleomycin_design import (
    CANONICAL_CONDITIONS,
    BleomycinDesignSpec,
)
from .bleomycin_score import BleomycinScore, score_bleomycin_design

DOSING_DAYS: tuple[float, ...] = (1.0, 3.0, 7.0, 10.0, 14.0)

_REPLICATE_LADDER: tuple[int, ...] = (2, 3, 4, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60)


def _candidate_replicates(n_conditions: int, capacity: int) -> list[int]:
    """Every rung of the ladder that fits within capacity, ascending."""
    room = capacity // max(n_conditions, 1)
    return [r for r in _REPLICATE_LADDER if r <= room]


@dataclass(frozen=True)
class BleomycinTrial:
    """One candidate evaluated during bleomycin design optimization."""

    msc_dosing_day: float
    replicates_per_condition: int
    design: BleomycinDesignSpec
    score: BleomycinScore


@dataclass(frozen=True)
class BleomycinOptimizeResult:
    found: bool
    design: BleomycinDesignSpec | None
    score: BleomycinScore | None
    trials: tuple[BleomycinTrial, ...]
    target_power: float
    target_testable: float
    capacity: int
    allow_assumption_sensitive: bool

    def summary(self) -> str:
        lines: list[str] = [
            f"searched {len(self.trials)} candidate(s), target power "
            f">={self.target_power:.0%}, testable >={self.target_testable:.0%}, "
            f"capacity {self.capacity} animals"
        ]
        lines.append("")
        for t in self.trials:
            arms = len(t.design.conditions)
            total = arms * t.replicates_per_condition
            flag = " ⚠ assumption-sensitive" if t.score.verdict_sensitive_to_assumption else ""
            lines.append(
                f"  day={t.msc_dosing_day:<4.1f} n={t.replicates_per_condition:<4} "
                f"({total} animals)  power {t.score.power:.0%}  "
                f"testable {t.score.testable_rate:.0%}{flag}"
            )
        lines.append("")

        if self.found and self.design is not None and self.score is not None:
            arms = len(self.design.conditions)
            lines.append(
                f"WINNER: {arms} arms x {self.design.replicates_per_condition} "
                f"animals = {self.design.total_animals} animals, "
                f"dosing day {self.design.msc_dosing_day:.1f}, route {self.design.msc_route}"
            )
            lines.append(
                f"  power {self.score.power:.0%}   "
                f"testable {self.score.testable_rate:.0%}"
            )
            if self.score.verdict_sensitive_to_assumption:
                lo, hi = self.score.power_range_under_assumptions or (float("nan"),) * 2
                lines.append(
                    f"  ⚠ this verdict is NOT robust to the twin's assumptions - "
                    f"power spans {lo:.0%}-{hi:.0%} across the plausible range of "
                    f"{', '.join(self.score.assumptions_in_play)}. It is the "
                    f"cheapest design tried that clears the target on a point "
                    f"estimate, not the cheapest design that reliably clears it."
                )
        else:
            lines.append(
                f"NO DESIGN FOUND within {self.capacity} animals that reaches "
                f"{self.target_power:.0%} power and {self.target_testable:.0%} "
                "testability.\n"
                "That is not a failure of the search - it is the same honest "
                "answer tier0/advise give: the question cannot be answered "
                "at this scale. The largest candidate tried is the last row "
                "above."
            )
        return "\n".join(lines)


def optimize_bleomycin_design(
    *,
    msc_route: str,
    target_power: float = 0.8,
    target_testable: float = 0.8,
    capacity: int = DEFAULT_COHORT_CAPACITY,
    conditions: tuple[str, ...] = CANONICAL_CONDITIONS,
    endpoint_day: float = 21.0,
    allow_assumption_sensitive: bool = False,
    params: BleomycinTwinParams = DEFAULT_BLEOMYCIN_PARAMS,
    n_sims: int = 400,
    seed: int | None = 0,
) -> BleomycinOptimizeResult:
    """The fewest total animals, at the best dosing day, that clears targets.

    `msc_route` has no default: the caller states it explicitly ('IT' or 'IV'),
    the search never discovers it.
    """
    if not msc_route:
        raise ValueError("msc_route must be explicitly specified ('IT' or 'IV') - search never decides route")
    if msc_route not in ("IT", "IV"):
        raise ValueError(f"unknown msc_route {msc_route!r}, expected 'IT' or 'IV'")

    trials: list[BleomycinTrial] = []
    winner: BleomycinTrial | None = None

    reps_tried = _candidate_replicates(len(conditions), capacity)

    for day in DOSING_DAYS:
        for reps in reps_tried:
            design = BleomycinDesignSpec(
                conditions=list(conditions),
                replicates_per_condition=reps,
                msc_dosing_day=day,
                msc_route=msc_route,
                endpoint_day=endpoint_day,
            )
            score = score_bleomycin_design(design, params=params, n_sims=n_sims, seed=seed)
            trial = BleomycinTrial(
                msc_dosing_day=day,
                replicates_per_condition=reps,
                design=design,
                score=score,
            )
            trials.append(trial)

            meets = score.power >= target_power and score.testable_rate >= target_testable
            robust = allow_assumption_sensitive or not score.verdict_sensitive_to_assumption
            if meets and robust and winner is None:
                winner = trial
                break
        if winner is not None:
            break

    return BleomycinOptimizeResult(
        found=winner is not None,
        design=winner.design if winner else None,
        score=winner.score if winner else None,
        trials=tuple(trials),
        target_power=target_power,
        target_testable=target_testable,
        capacity=capacity,
        allow_assumption_sensitive=allow_assumption_sensitive,
    )


__all__ = [
    "BleomycinOptimizeResult",
    "BleomycinTrial",
    "DOSING_DAYS",
    "optimize_bleomycin_design",
]
