"""What to change in a bleomycin cohort design, and what changing it would do.

Mirrors `advise.py` for the bleomycin lung twin apparatus: each suggestion
carries its own simulated consequence score and delta, bounded by
MAX_COMBINE_ROUNDS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .bleomycin_calibration import (
    DEFAULT_BLEOMYCIN_PARAMS,
    DEFAULT_COHORT_CAPACITY,
    BleomycinTwinParams,
)
from .bleomycin_design import (
    BLEOMYCIN_MSC,
    BLEOMYCIN_ONLY,
    BleomycinDesignSpec,
    OutOfTwinScopeError,
)
from .bleomycin_score import BleomycinScore, score_bleomycin_design

MAX_COMBINE_ROUNDS = 5


@dataclass
class Suggestion:
    """One change to a bleomycin design, and what the twin says it would do."""

    lever: str
    change: str
    before: BleomycinScore
    after: BleomycinScore
    caveat: str = ""
    assumption_sensitive: bool = False

    @property
    def delta_power(self) -> float:
        return self.after.power - self.before.power

    @property
    def delta_testable(self) -> float:
        return self.after.testable_rate - self.before.testable_rate

    @property
    def helps(self) -> bool:
        return self.delta_power > 0.01 or self.delta_testable > 0.05

    def line(self) -> str:
        arrow = (
            f"power {self.before.power:.0%} -> {self.after.power:.0%}"
            f"   testable {self.before.testable_rate:.0%} -> "
            f"{self.after.testable_rate:.0%}"
        )
        out = [f"{self.change}", f"    {arrow}"]
        if self.assumption_sensitive:
            out.append(
                "    ⚠ rests on an ASSUMED constant"
            )
        if self.caveat:
            out.append(f"    {self.caveat}")
        return "\n".join(out)


@dataclass
class BleomycinAdvice:
    """Every change tried on a bleomycin design, whether or not it helped."""

    original: BleomycinScore
    suggestions: list[Suggestion] = field(default_factory=list)
    best_combined: tuple[BleomycinDesignSpec, BleomycinScore] | None = None
    combination_order: list[str] = field(default_factory=list)

    @property
    def helpful(self) -> list[Suggestion]:
        return sorted(
            (s for s in self.suggestions if s.helps),
            key=lambda s: (s.delta_power, s.delta_testable),
            reverse=True,
        )

    def summary(self, target_power: float = 0.8) -> str:
        lines: list[str] = []
        if self.original.declined:
            return (
                "This design declines to run the experiment (assigns 0 animals), "
                "so there is nothing to improve."
            )

        lines.append(
            f"starting point: power {self.original.power:.0%}, testable "
            f"{self.original.testable_rate:.0%}"
        )
        lines.append("")

        helpful = self.helpful
        if not helpful:
            lines.append("No single change to this design improves it.")
        else:
            lines.append(f"{len(helpful)} change(s) help, best first:")
            lines.append("")
            for i, s in enumerate(helpful, 1):
                lines.append(f"  {i}. {s.line()}")
                lines.append("")

        tried = len(self.suggestions)
        useless = tried - len(helpful)
        if useless:
            lines.append(
                f"({useless} of {tried} changes tried made no difference or made "
                "it worse - listed with --all)"
            )
            lines.append("")

        if self.best_combined is not None:
            spec, score = self.best_combined
            lines.append("EVERYTHING AT ONCE")
            if self.combination_order:
                lines.append(
                    f"  applied in order: {' -> '.join(self.combination_order)}"
                )
            lines.append(
                f"  {len(spec.conditions)} arms x {spec.replicates_per_condition} "
                f"animals, dosing day {spec.msc_dosing_day:.1f}, route {spec.msc_route}"
            )
            lines.append(
                f"  power {score.power:.0%}   testable {score.testable_rate:.0%}"
            )
            if score.power < target_power:
                need = (
                    f"~{score.replicates_needed} animals per arm"
                    if score.replicates_needed > 0
                    else "an unestimable number of animals"
                )
                lines.append("")
                lines.append(
                    f"  Even applying every improvement, this reaches "
                    f"{score.power:.0%}, not {target_power:.0%}.\n"
                    f"  It needs {need}.\n\n"
                    "  That is not a failure of the search. The honest conclusion "
                    "is that the\n  question cannot be answered at this scale."
                )
        return "\n".join(lines)


def _score(design: BleomycinDesignSpec, params: BleomycinTwinParams, n_sims: int, seed: int | None):
    return score_bleomycin_design(design, params=params, n_sims=n_sims, seed=seed)


def _variants(
    design: BleomycinDesignSpec, capacity: int = DEFAULT_COHORT_CAPACITY
) -> list[tuple[str, str, BleomycinDesignSpec, str]]:
    out: list[tuple[str, str, BleomycinDesignSpec, str]] = []

    # 1. Add MSC arm if missing
    if BLEOMYCIN_MSC not in design.conditions:
        conds = list(design.conditions) + [BLEOMYCIN_MSC]
        out.append((
            "add-msc",
            "Add a bleomycin_MSC treatment arm",
            design.model_copy(update={"conditions": conds}),
            "Comparing against bleomycin_only is required to test efficacy.",
        ))

    # 2. Move dosing day earlier
    if design.msc_dosing_day > 7.0:
        out.append((
            "earlier-dosing",
            f"Move MSC dosing earlier from day {design.msc_dosing_day:.1f} to day 3.0",
            design.model_copy(update={"msc_dosing_day": 3.0}),
            "Early dosing (day <= 7) delivers full therapeutic rescue.",
        ))
    elif design.msc_dosing_day > 1.0:
        out.append((
            "earlier-dosing",
            f"Move MSC dosing earlier from day {design.msc_dosing_day:.1f} to day 1.0",
            design.model_copy(update={"msc_dosing_day": 1.0}),
            "",
        ))

    # 3. Switch route IV -> IT
    if design.msc_route == "IV":
        out.append((
            "switch-route",
            "Switch MSC delivery route from IV (intravenous) to IT (intratracheal)",
            design.model_copy(update={"msc_route": "IT"}),
            "IT route avoids IV procedural mortality hazard.",
        ))

    # 4. Fill cohort capacity / increase replicates
    arms = max(len(design.conditions), 1)
    room = capacity // arms
    if room > design.replicates_per_condition:
        out.append((
            "replicates",
            f"Fill cohort capacity: {room} animals per arm instead of {design.replicates_per_condition}",
            design.model_copy(update={"replicates_per_condition": room}),
            "",
        ))

    return out


def advise_bleomycin_design(
    design: BleomycinDesignSpec,
    params: BleomycinTwinParams = DEFAULT_BLEOMYCIN_PARAMS,
    n_sims: int = 400,
    seed: int | None = 0,
    capacity: int = DEFAULT_COHORT_CAPACITY,
) -> BleomycinAdvice:
    """Try one change at a time, then all helpful ones together."""
    base = _score(design, params, n_sims, seed)
    result = BleomycinAdvice(original=base)
    if base.declined:
        return result

    for lever, change, variant, caveat in _variants(design, capacity=capacity):
        try:
            after = _score(variant, params, n_sims, seed)
        except OutOfTwinScopeError:
            continue
        result.suggestions.append(
            Suggestion(
                lever=lever,
                change=change,
                before=base,
                after=after,
                caveat=caveat,
                assumption_sensitive=after.verdict_sensitive_to_assumption,
            )
        )

    combined = design
    combined_score = base
    for _round in range(MAX_COMBINE_ROUNDS):
        best: tuple[float, float, BleomycinDesignSpec, BleomycinScore, str] | None = None
        for lever, _change, variant, _caveat in _variants(combined, capacity=capacity):
            try:
                cand = _score(variant, params, n_sims, seed)
            except OutOfTwinScopeError:
                continue
            gain = cand.power - combined_score.power
            testable_gain = cand.testable_rate - combined_score.testable_rate
            if gain <= 0.005 and testable_gain <= 0.02:
                continue
            key = (gain, testable_gain)
            if best is None or key > (best[0], best[1]):
                best = (gain, testable_gain, variant, cand, lever)
        if best is None:
            break
        _g, _t, combined, combined_score, lever = best
        result.combination_order.append(lever)

    if combined != design:
        result.best_combined = (combined, combined_score)
    return result


__all__ = [
    "BleomycinAdvice",
    "Suggestion",
    "advise_bleomycin_design",
]
