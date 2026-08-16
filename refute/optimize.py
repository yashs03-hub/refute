"""Search for the cheapest design that clears a power target.

`PLAN.md` names this the one piece of §3 not yet built, and names the reason it
was left until last: **"Goodhart applies in full the moment the optimizer
lands: a benchmark is not an environment, but a search over designs is"**
(§9.1). `advise.py` already walks this line - it caps its own combination
search at `MAX_COMBINE_ROUNDS` "so the combined design remains a short,
readable chain of simulated steps rather than the output of an unbounded
search against the twin." This module is a real search rather than a bounded
handful of hand-picked levers, so the discipline has to be stricter, not
looser.

THE BOUNDARY THIS MODULE MUST NOT CROSS
----------------------------------------
**No harness is given this module.** `PLAN.md` §11.1 states the rule this
extends: "A harness may restructure the model's own reasoning; it may not
consult the scorer." `optimize_design` calls `score_design` directly, in a
loop, which is exactly a search against `twin.py`'s equations rather than
against biology - the failure §9.1 describes. That is acceptable for a human
planning a real plate (which is what every other CLI command in this project
already is: `tier0`, `advise`, `sweep` all consult the scorer on the human's
behalf). It is NOT acceptable for the agent under test, ever, by any route.
`agent.py`, `environment.py` and `api.py` must never import this module -
`tests/test_optimize.py` pins that with a tripwire.

WHAT IS SEARCHED, AND WHAT IS NOT
-----------------------------------
Only `replicates_per_condition` and the imaging schedule are searched. Both
are free in the sense that varying them costs nothing until wells are actually
spent - there is no ASSUMED constant either one touches.

`antifibrinolytic` is deliberately NOT searched. §9.1's sharp form names it by
name: flipping that one bool multiplies a Weibull scale by
`aprotinin_hazard_scale`, a constant tagged ASSUMED, not measured - "a cheat
code in the input schema." An optimizer that could silently discover "turn
this bit on" and report a clean win would be finding the cheat code
automatically instead of a human doing it by hand, which is a worse version of
the same failure, not a different one. The caller must state it explicitly,
and if the winning design still turns out to be `verdict_sensitive_to_
assumption`, that is surfaced, never smoothed away by the search.

`conditions` is a caller-supplied fixed set, not searched. `HEADLINE_CONTRAST`
in `score.py` is a hard-coded pair (`N-T`, `N-CM+T`) - the scorer only ever
tests that one contrast, regardless of what else is on the plate. Searching
over which arms to include would silently do nothing unless both contrast
members are present, and would look like a bug rather than a result (this was
found the hard way earlier this session: a two-arm design missing `N-CM+T`
scored a flat 0% at every replicate count tried, for a reason that had nothing
to do with sample size). Pass the four canonical conditions unless you have
a specific reason to narrow to the headline pair.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .calibration import DEFAULT_PARAMS, PLATE_WELLS, TwinParams
from .design import DesignSpec
from .score import DesignScore, score_design

# The four conditions Experiment 4 actually ran. Anything narrower has to be
# an explicit caller choice, not a default - see the module docstring on why
# dropping to two arms is not free the way it looks.
CANONICAL_CONDITIONS: tuple[str, ...] = ("N-SS", "N-T", "N-CM", "N-CM+T")

# Two schedules, not a continuum: sparse (what Experiment 4 actually imaged)
# and with early frames (what `advise.py` already knows fixes kinetics
# identifiability - see `EARLY_TIMEPOINTS` there). A real search over
# arbitrary timepoint sets would be a much larger space for a benefit this
# project has only ever needed two points of.
SPARSE_SCHEDULE: tuple[float, ...] = (24.0, 120.0, 168.0)
WITH_EARLY_FRAMES: tuple[float, ...] = (2.0, 6.0, 12.0, 24.0, 120.0, 144.0, 168.0)

# Ascending, so the search reports the FIRST (cheapest) replicate count that
# clears the target rather than the largest one tried. Stops being generated
# past whatever `capacity` allows - see `_candidate_replicates`.
_REPLICATE_LADDER: tuple[int, ...] = (2, 3, 4, 6, 8, 10, 15, 20, 30, 44, 60, 90, 120)


def _candidate_replicates(n_conditions: int, capacity: int) -> list[int]:
    """Every rung of the ladder that still fits the plate, ascending."""
    room = capacity // max(n_conditions, 1)
    return [r for r in _REPLICATE_LADDER if r <= room]


@dataclass(frozen=True)
class Trial:
    """One candidate evaluated, kept whether or not it won.

    Nothing here is hidden after the fact - `OptimizeResult.trials` is the
    complete record of what the search tried, in the same spirit as `advise
    --all` and `sweep`: a search that only shows its winner is not
    distinguishable from one that never looked at anything else.
    """

    schedule_name: str
    replicates_per_condition: int
    design: DesignSpec
    score: DesignScore


@dataclass(frozen=True)
class OptimizeResult:
    found: bool
    design: DesignSpec | None
    score: DesignScore | None
    trials: tuple[Trial, ...]
    target_power: float
    target_testable: float
    capacity: int
    allow_assumption_sensitive: bool

    def summary(self) -> str:
        lines: list[str] = [
            f"searched {len(self.trials)} candidate(s), target power "
            f">={self.target_power:.0%}, testable >={self.target_testable:.0%}, "
            f"capacity {self.capacity} wells"
        ]
        lines.append("")
        for t in self.trials:
            arms = len(t.design.conditions)
            total = arms * t.replicates_per_condition
            flag = " ⚠ assumption-sensitive" if t.score.verdict_sensitive_to_assumption else ""
            lines.append(
                f"  {t.schedule_name:<14} n={t.replicates_per_condition:<4} "
                f"({total} wells)  power {t.score.power:.0%}  "
                f"testable {t.score.testable_rate:.0%}{flag}"
            )
        lines.append("")

        if self.found and self.design is not None and self.score is not None:
            arms = len(self.design.conditions)
            lines.append(
                f"WINNER: {arms} arms x {self.design.replicates_per_condition} "
                f"wells = {self.design.total_wells} wells, "
                f"{self.design.imaging_times_h}"
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
                f"NO DESIGN FOUND within {self.capacity} wells that reaches "
                f"{self.target_power:.0%} power and {self.target_testable:.0%} "
                "testability.\n"
                "That is not a failure of the search - it is the same honest "
                "answer `tier0`/`advise` give: the question cannot be answered "
                "at this scale. The largest candidate tried is the last row "
                "above."
            )
        return "\n".join(lines)


def optimize_design(
    *,
    antifibrinolytic: bool,
    target_power: float = 0.8,
    target_testable: float = 0.8,
    capacity: int = PLATE_WELLS,
    conditions: tuple[str, ...] = CANONICAL_CONDITIONS,
    treatment_time_h: float = 120.0,
    endpoint_time_h: float = 168.0,
    allow_assumption_sensitive: bool = False,
    params: TwinParams = DEFAULT_PARAMS,
    n_sims: int = 400,
    seed: int | None = 0,
) -> OptimizeResult:
    """The fewest total wells, at the sparsest schedule, that clears both
    targets - or, honestly, that none tried did.

    `antifibrinolytic` has no default: the caller states it, the search never
    discovers it. See the module docstring for why that is load-bearing rather
    than an oversight.

    Ascends the replicate ladder for the sparse schedule first (it is what
    Experiment 4 actually imaged, so it is what a real plate would cost least
    to run), then the early-frame schedule, and returns the first candidate,
    across both, that meets the targets - preferring fewer total wells, and
    breaking a tie on well count in favour of the sparse schedule since it
    costs no extra imaging time either. A candidate whose verdict is
    `verdict_sensitive_to_assumption` is skipped unless
    `allow_assumption_sensitive=True`, in which case it may win but the flag
    travels with it into `OptimizeResult` rather than being dropped.
    """
    schedules = (("sparse", SPARSE_SCHEDULE), ("early-frames", WITH_EARLY_FRAMES))
    trials: list[Trial] = []
    winner: Trial | None = None

    for name, schedule in schedules:
        reps_tried = _candidate_replicates(len(conditions), capacity)
        for reps in reps_tried:
            design = DesignSpec(
                conditions=list(conditions),
                replicates_per_condition=reps,
                imaging_times_h=list(schedule),
                treatment_time_h=treatment_time_h,
                endpoint_time_h=endpoint_time_h,
                antifibrinolytic=antifibrinolytic,
                antifibrinolytic_agent="aprotinin" if antifibrinolytic else None,
                normalise_to_own_baseline=True,
                locked_imaging_protocol=True,
                anticipates_scaffold_failure=antifibrinolytic,
            )
            score = score_design(design, params=params, n_sims=n_sims, seed=seed)
            trial = Trial(schedule_name=name, replicates_per_condition=reps,
                           design=design, score=score)
            trials.append(trial)

            meets = score.power >= target_power and score.testable_rate >= target_testable
            robust = allow_assumption_sensitive or not score.verdict_sensitive_to_assumption
            if meets and robust and winner is None:
                winner = trial
                break  # ladder is ascending - first hit on this schedule is cheapest on it
        if winner is not None:
            break  # sparse schedule won; no need to try early-frames at all

    return OptimizeResult(
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
    "CANONICAL_CONDITIONS",
    "SPARSE_SCHEDULE",
    "WITH_EARLY_FRAMES",
    "OptimizeResult",
    "Trial",
    "optimize_design",
]
