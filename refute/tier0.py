"""Tier 0 - can this comparison resolve its effect, for any assay at all.

No mechanism, no twin, no calibration. Just the arithmetic of a two-sample
comparison, given numbers the experimenter supplies. That makes it the one part
of `refute` usable outside the fibrin assay - and PLAN 6.6's scaling claim
("most cases do not need a mechanistic twin") is only demonstrable because this
exists.

WHAT THIS CANNOT DO, and it must be said every time it produces output: it cannot
tell you the preparation fails. Experiment 4's scaffold dissolved before its
endpoint, and no power calculation anywhere would have predicted that. Tier 0
answers "am I underpowered", which is a real and common defect, and is silent on
"will this even survive to be measured" - which needs somebody's raw failure data
and a tier-1 twin.

THE GATE. Power needs a variability estimate, and this module will not invent
one. Refusing is the same property as `UncalibratedAssayError`: a confident power
figure computed from a variance somebody guessed is worse than no figure, because
it looks like a calculation. If you do not have an SD, the honest answers are to
run a pilot, take it from prior plates, or say the design is unassessable - all of
which `Tier0InputError` tells you.

    from refute.tier0 import Tier0Design, score_tier0
    score_tier0(Tier0Design(
        assay="scratch migration", n_arms=2, replicates_per_arm=6, capacity=12,
        expected_effect=8.0, variability_sd=6.0, unit="well",
    ))
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy import stats

# Conventional two-sided significance and the 80% power target, matching
# `score.py` so a tier-0 verdict and a tier-1 verdict mean the same thing.
DEFAULT_ALPHA = 0.05
DEFAULT_TARGET_POWER = 0.80

# Below two per arm no test exists, exactly as in the twin.
MIN_REPLICATES = 2

# Search bound when solving for the required replication. Above this the answer
# is "not at this scale" regardless of the exact number, and reporting 40,000
# would imply a precision the input SD does not support.
MAX_SEARCH_REPLICATES = 10_000


class Tier0InputError(ValueError):
    """Raised when a power claim would rest on a number nobody supplied."""


@dataclass(frozen=True)
class Tier0Design:
    """A comparison, described by the person proposing it.

    Everything here is the experimenter's own estimate. Tier 0 has no
    calibration and does not pretend to - its job is to do the arithmetic
    honestly and to refuse when an input is missing.
    """

    assay: str
    n_arms: int
    replicates_per_arm: int
    capacity: int                      # units available in total
    expected_effect: float | None = None   # difference between the two arms
    variability_sd: float | None = None    # within-arm SD, same units as effect
    unit: str = "well"
    alpha: float = DEFAULT_ALPHA
    target_power: float = DEFAULT_TARGET_POWER
    notes: str = ""

    @property
    def total_units(self) -> int:
        return self.n_arms * self.replicates_per_arm

    @property
    def fits(self) -> bool:
        return self.total_units <= self.capacity

    def require_inputs(self) -> None:
        """Raise unless a power figure would mean anything."""
        missing = []
        if self.expected_effect is None:
            missing.append(
                "expected_effect - the difference you expect between the two arms, "
                "in the units you will report"
            )
        if self.variability_sd is None:
            missing.append(
                "variability_sd - the within-arm SD of that same measurement, from "
                "a pilot, prior runs, or a published estimate for this assay"
            )
        if missing:
            raise Tier0InputError(
                "cannot compute power without:\n"
                + "\n".join(f"    - {m}" for m in missing)
                + "\n  These are not defaults this tool can supply. A power figure "
                "computed from a\n  guessed variance looks like a calculation and "
                "is not one - which is the\n  error this project exists to "
                "criticise. Run a pilot, use prior data, or\n  record the design as "
                "unassessable."
            )
        if self.expected_effect == 0:
            raise Tier0InputError(
                "expected_effect is 0, so no replication resolves it. State the "
                "smallest difference that would change your conclusion."
            )
        if self.variability_sd is not None and self.variability_sd <= 0:
            raise Tier0InputError("variability_sd must be positive")
        if self.n_arms < 2:
            raise Tier0InputError("a comparison needs at least 2 arms")


@dataclass
class Tier0Score:
    """What the arithmetic says. Deliberately not called a simulation."""

    design: Tier0Design
    power: float
    min_detectable_effect: float
    replicates_needed: int          # -1 when above the search bound
    fits_capacity: bool

    @property
    def underpowered(self) -> bool:
        return self.power < self.design.target_power

    @property
    def feasibility(self) -> str:
        """Same vocabulary as tier 1, so verdicts are comparable."""
        if self.replicates_needed <= 0:
            return "beyond-scale"
        if self.replicates_needed * self.design.n_arms > self.design.capacity:
            return "infeasible"
        return "feasible"

    def summary(self) -> str:
        d = self.design
        needed = (
            f">{MAX_SEARCH_REPLICATES:,}"
            if self.replicates_needed <= 0
            else str(self.replicates_needed)
        )
        lines = [
            f"assay                            : {d.assay}",
            f"design                           : {d.n_arms} arms x "
            f"{d.replicates_per_arm} {d.unit}s = {d.total_units} of {d.capacity}",
            f"effect / within-arm SD           : {d.expected_effect:g} / "
            f"{d.variability_sd:g}  (Cohen's d = "
            f"{abs(d.expected_effect / d.variability_sd):.2f})",
            "",
            f"power at this replication        : {self.power:.0%}"
            f"   (target {d.target_power:.0%})",
            f"smallest detectable difference   : {self.min_detectable_effect:.3g}",
            f"{d.unit}s per arm actually needed    : {needed}",
            f"verdict                          : {self.feasibility}",
        ]

        why = []
        if self.underpowered:
            why.append(
                f"underpowered: {d.replicates_per_arm} {d.unit}s per arm gives "
                f"{self.power:.0%} power, not {d.target_power:.0%}."
            )
        if not self.fits_capacity:
            why.append(
                f"over capacity as designed: {d.total_units} {d.unit}s requested, "
                f"{d.capacity} available."
            )
        if self.feasibility == "infeasible":
            why.append(
                f"infeasible at this scale: {needed} per arm across {d.n_arms} arms "
                f"exceeds the {d.capacity} {d.unit}s available. Narrow the "
                "comparison, measure more precisely, or report that the question "
                "cannot be answered at this scale - the last is a legitimate "
                "answer, not a failure."
            )
        if why:
            lines += ["", "why:"] + [f"  - {w}" for w in why]

        # Non-negotiable. Tier 0 has no mechanism, and a reader who forgets that
        # will take a green verdict as an assurance the experiment will work.
        lines += [
            "",
            "TIER 0 - arithmetic, not simulation. This says whether the comparison "
            "could",
            "resolve the effect you stated. It says NOTHING about whether the "
            "preparation",
            "survives to be measured: Experiment 4 was destroyed by fibrinolysis, "
            "and no",
            "power calculation would have predicted that. Modelling failure needs a "
            "tier-1",
            "twin, which needs somebody's raw data on how the assay breaks.",
        ]
        return "\n".join(lines)


def _power(d: float, n: int, alpha: float) -> float:
    """Power of a two-sided two-sample t-test, n per arm, effect size d."""
    if n < MIN_REPLICATES:
        return 0.0
    df = 2 * n - 2
    ncp = d * math.sqrt(n / 2.0)
    crit = stats.t.ppf(1 - alpha / 2.0, df)
    # Both tails: with a noncentral t the far tail is negligible but including it
    # keeps the figure right for very small effects.
    upper = float(stats.nct.sf(crit, df, ncp))
    lower = float(stats.nct.cdf(-crit, df, ncp))
    return min(1.0, upper + lower)


def score_tier0(design: Tier0Design) -> Tier0Score:
    """Power, minimum detectable effect and required replication. No mechanism."""
    design.require_inputs()
    assert design.expected_effect is not None
    assert design.variability_sd is not None

    d = abs(design.expected_effect / design.variability_sd)
    n = design.replicates_per_arm
    power = _power(d, n, design.alpha)

    # Smallest difference this replication could detect at the target power.
    if n >= MIN_REPLICATES:
        df = 2 * n - 2
        z = stats.t.ppf(1 - design.alpha / 2.0, df) + stats.t.ppf(design.target_power, df)
        mde = float(z * design.variability_sd * math.sqrt(2.0 / n))
    else:
        mde = float("inf")

    needed = -1
    for candidate in range(MIN_REPLICATES, MAX_SEARCH_REPLICATES + 1):
        if _power(d, candidate, design.alpha) >= design.target_power:
            needed = candidate
            break

    return Tier0Score(
        design=design,
        power=power,
        min_detectable_effect=mde,
        replicates_needed=needed,
        fits_capacity=design.fits,
    )


# ---------------------------------------------------------------------------
# The tier-1 bridge, so the two are not accidentally treated as equivalent.
# ---------------------------------------------------------------------------

TIER_LADDER = """\
Tier 0  underpowering and scale.        Needs: your effect size and SD.
        No mechanism. Works for ANY assay. This module.

Tier 1  one dominant failure mechanism. Needs: somebody's raw data on how the
        assay breaks - which PLAN 6 measured as 0/10 recoverable from published
        literature. `fibrin_contracture` is the only one calibrated.

Tier 2  interacting failure modes.      Not reachable yet. Candidates accumulate
        in the designs `out_of_twin_scope` refuses to score.

Most experiments only ever need tier 0, which is why the ladder scales even
though a tier-1 twin does not get cheaper. What tier 0 cannot do is tell you the
gel dissolves.
"""
