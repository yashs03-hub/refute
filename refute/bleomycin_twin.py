"""Digital twin of the bleomycin-induced pulmonary fibrosis assay (murine).

Simulates a cohort animal-by-animal: mortality, Ashcroft severity among
survivors, dosing failure, and - the one mechanism this twin adds that
`twin.py` has no equivalent of - a tunable link between an animal's latent
severity and its probability of dying before the endpoint.

WHY A SHARED LATENT VARIABLE, NOT TWO INDEPENDENT DRAWS
---------------------------------------------------------
Each animal gets one standard-normal draw, `z`. Its Ashcroft score is always
`mean + sd * z` - severity is genuinely continuous, and z is exactly the
quantile that score sits at. Its hazard rate is
`base_hazard * exp(coupling * z)`.

At `coupling = 0` (this twin's default, inherited from
`bleomycin_calibration.MORTALITY_SEVERITY_COUPLING`), the hazard term is 1
for every animal regardless of z - death is independent of the severity that
animal would have shown, so the survivors are an UNBIASED sample of the
population's z distribution, and their mean Ashcroft score equals the true
population mean up to sampling noise. No SURVIVORSHIP bias is baked in by
default.

KNOWN RESIDUAL AT coupling=0
------------------------------
`_sample_ashcroft` floors the score at 0 (Ashcroft cannot go negative - real
biology, not an artifact). When the injected MSC effect pushes a treated
arm's mean close to that floor, the clip asymmetrically raises the arm's
observed mean above what the unclipped normal would give, which shows up as
a small positive `survivorship_bias_ashcroft` even at `coupling=0`
(observed ~0.1 of ~2.9 true effect points at this file's default
parameters) - a floor effect, not the coupling mechanism. The scorer's
diagnostic text is gated on `coupling > 0` specifically so this residual
never gets reported as evidence of the mechanism it is not; see
`bleomycin_score.py`.

At `coupling > 0`, high-z (more severe) animals carry higher hazard and
preferentially die, so survivors skew toward low z, and their mean Ashcroft
score UNDERSTATES the population effect. This is the survivorship-bias
mechanism the whole project is about, and it is now a number a sensitivity
sweep can show rather than a warning asserted in prose - see
`bleomycin_score.py`'s explicit true-effect-vs-measured-effect diagnostic.

Because nobody has ever measured this coupling (see
`assays/bleomycin_lung.py`'s BLOCKED/mortality_severity_coupling), the
twin's own default produces NO bias. Sweeping the constant is what reveals
what a real, nonzero coupling would do - not a hardcoded assumption baked
into every run.

Known limits (state these alongside any result)
-------------------------------------------------
1. Every non-baseline number is either DERIVED by a stated transform or
   ASSUMED - see `bleomycin_calibration.py`. This twin has no primary data
   of its own; it is calibrated entirely from published methods sections and
   inherits whatever those papers got wrong.
2. The timing regime is a two-value step function (early/late), not a fitted
   curve - the corpus disagrees about the SIGN of the late-dosing effect
   depending on route, and fitting a curve to that disagreement would
   manufacture precision nobody has.
3. Mortality is modelled as a single exponential hazard, not a fitted
   Weibull - unlike `fibrin_contracture`'s lysis model, nothing in the
   bleomycin corpus constrains a shape parameter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm

from .bleomycin_calibration import DEFAULT_BLEOMYCIN_PARAMS, BleomycinTwinParams
from .bleomycin_design import BLEOMYCIN_MSC, BleomycinDesignSpec


@dataclass
class AnimalResult:
    """One simulated animal."""

    condition: str
    replicate: int
    excluded_reason: str | None       # dosing_failure | None
    died: bool
    death_day: float | None           # None if it survived to the endpoint
    ashcroft_score: float | None      # None if excluded or died before scoring

    @property
    def evaluable(self) -> bool:
        return self.excluded_reason is None

    @property
    def scored(self) -> bool:
        """Contributed a real Ashcroft measurement - alive at the endpoint,
        not excluded. Mirrors `WellResult.endpoint_ratio` returning `None`
        for a well with nothing coherent to measure."""
        return self.evaluable and not self.died and self.ashcroft_score is not None


@dataclass
class CohortResult:
    """One simulated cohort."""

    animals: list[AnimalResult]
    design: BleomycinDesignSpec

    def scored_by_condition(self) -> dict[str, list[float]]:
        out: dict[str, list[float]] = {}
        for a in self.animals:
            if a.scored:
                out.setdefault(a.condition, []).append(a.ashcroft_score)
        return out

    @property
    def mortality_by_condition(self) -> dict[str, float]:
        """Fraction of evaluable animals dead by the endpoint, per arm."""
        out: dict[str, float] = {}
        for cond in {a.condition for a in self.animals}:
            evaluable = [a for a in self.animals if a.condition == cond and a.evaluable]
            if not evaluable:
                continue
            dead = sum(1 for a in evaluable if a.died)
            out[cond] = dead / len(evaluable)
        return out

    @property
    def excluded_fraction(self) -> float:
        if not self.animals:
            return 0.0
        return sum(1 for a in self.animals if not a.evaluable) / len(self.animals)


class BleomycinTwin:
    """Simulates cohorts under a given calibration."""

    def __init__(
        self, params: BleomycinTwinParams = DEFAULT_BLEOMYCIN_PARAMS,
        seed: int | None = None,
    ):
        self.p = params
        self.rng = np.random.default_rng(seed)

    # -- component models ---------------------------------------------------

    def _regime_multiplier(self, condition: str, design: BleomycinDesignSpec) -> float:
        """1.0 for an early MSC dose, `late_dosing_effect_multiplier`
        otherwise. 1.0 (unused) for the untreated arm."""
        if condition != BLEOMYCIN_MSC:
            return 0.0
        if design.msc_dosing_day <= self.p.early_dosing_cutoff_day:
            return 1.0
        return self.p.late_dosing_effect_multiplier

    def _hazard_rate(self, condition: str, z: float, design: BleomycinDesignSpec) -> float:
        """Per-day exponential hazard, severity-coupled and MSC-modulated."""
        rate = self.p.mortality_hazard_per_day * math.exp(
            self.p.mortality_severity_coupling * z
        )
        if condition == BLEOMYCIN_MSC:
            regime = self._regime_multiplier(condition, design)
            ratio = 1.0 + (self.p.msc_mortality_hazard_ratio - 1.0) * regime
            rate *= ratio
        return rate

    def _sample_death(
        self, condition: str, z: float, design: BleomycinDesignSpec
    ) -> tuple[bool, float | None]:
        """(died_by_endpoint, death_day). Disease-driven hazard is a
        continuous exponential draw; IV procedural mortality (if any) is a
        separate one-time Bernoulli check at the moment of dosing, not a
        modulation of the same rate - it is a distinct mechanism (embolism
        at injection), not disease progression."""
        rate = self._hazard_rate(condition, z, design)
        u = self.rng.random()
        disease_death_day = -math.log(1 - u) / rate if rate > 0 else float("inf")

        if condition == BLEOMYCIN_MSC and design.msc_route == "IV":
            if self.rng.random() < self.p.p_iv_procedural_death:
                procedural_day = design.msc_dosing_day
                death_day = min(disease_death_day, procedural_day)
                if death_day <= design.endpoint_day:
                    return True, float(death_day)

        if disease_death_day <= design.endpoint_day:
            return True, float(disease_death_day)
        return False, None

    def _sample_ashcroft(
        self, condition: str, z: float, design: BleomycinDesignSpec
    ) -> float:
        mean = self.p.baseline_ashcroft_mean
        sd = self.p.baseline_ashcroft_sd
        if condition == BLEOMYCIN_MSC:
            regime = self._regime_multiplier(condition, design)
            mean = mean - self.p.msc_ashcroft_effect * regime
            sd = self.p.msc_treated_arm_sd
        score = mean + sd * z
        return max(score, 0.0)   # Ashcroft is a bounded, non-negative scale

    # -- cohort simulation ---------------------------------------------------

    def simulate_cohort(self, design: BleomycinDesignSpec) -> CohortResult:
        animals: list[AnimalResult] = []
        for condition in design.conditions:
            for rep in range(design.replicates_per_condition):
                excluded = None
                if self.rng.random() < self.p.p_dosing_failure:
                    excluded = "dosing_failure"

                z = float(norm.ppf(self.rng.random()))

                if excluded is not None:
                    animals.append(AnimalResult(
                        condition=condition, replicate=rep,
                        excluded_reason=excluded, died=False,
                        death_day=None, ashcroft_score=None,
                    ))
                    continue

                died, death_day = self._sample_death(condition, z, design)
                score = None if died else self._sample_ashcroft(condition, z, design)

                animals.append(AnimalResult(
                    condition=condition, replicate=rep,
                    excluded_reason=None, died=died,
                    death_day=death_day, ashcroft_score=score,
                ))
        return CohortResult(animals=animals, design=design)

    def simulate_many(self, design: BleomycinDesignSpec, n: int) -> list[CohortResult]:
        return [self.simulate_cohort(design) for _ in range(n)]
