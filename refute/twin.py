"""Digital twin of the Experiment 4 fibrin gel contracture assay.

Simulates a plate well-by-well: contraction, fibrinolytic scaffold failure,
between-well heterogeneity, attrition, and whether a well is measurable at all
under the design's imaging protocol.

What this is
------------
A *design* simulator, not a biology oracle. It cannot tell you whether MSC
conditioned media suppresses fibroblast contraction - Experiment 4 never
measured that, because the scaffold dissolved before the treatment window
closed. What it can tell you is whether a proposed plate would have *detected*
an effect of a given size. The effect is injected as ground truth; the question
is whether the design recovers it.

That is the useful question for benchmarking an experiment-designing agent, and
it is answerable from what Experiment 4 did measure.

Known limits (state these alongside any result)
-----------------------------------------------
1. Calibrated on ONE plate, n=10 evaluable wells, one cell source.
2. The contraction curve rests on a single pre-plateau timepoint. Contraction
   was already ~94% complete at first imaging, so tau is extrapolated.
3. The lysis model rests on one endpoint (6/6 vs 0/4 at Day 10) plus a
   qualitative Day 7. Enough to fit a hazard with a contractility term; not
   enough to pin its shape.
4. Aprotinin's effect is ASSUMED, not measured - see calibration.py.
5. The twin cannot reward a design that exploits a mechanism it does not model.
   A genuinely clever design can score badly here for a reason that is the
   twin's fault, not the design's.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .calibration import (
    DEFAULT_PARAMS,
    INITIAL_FILL_PCT,
    P_MEASURE_OK_LOCKED_PROTOCOL,
    P_MEASURE_OK_UNCONTROLLED,
    TwinParams,
)
from .design import DesignSpec

# Arms carrying TGF-b1 are the contractile ones, and contractility is what
# drives fibrinolytic scaffold loss. This is the mechanism the Day 10 split
# (6/6 vs 0/4, Fisher p=0.0048) actually establishes.
TGFB_ARMS = {"N-T", "N-CM+T"}
MSC_CM_ARMS = {"N-CM", "N-CM+T"}

# ASSUMED - how fast a treatment effect develops once applied. Experiment 4
# never observed one, so nothing constrains this. It only matters for designs
# whose endpoint sits close to t0; a Day-7 or Day-10 endpoint is many multiples
# of this away and is insensitive to it.
TREATMENT_TAU_H = 24.0


@dataclass
class WellResult:
    """One simulated well."""

    condition: str
    replicate: int
    excluded_reason: str | None            # cast_failure | contamination | None
    lysis_time_h: float | None             # None if the scaffold survived the run
    fill_by_time: dict[float, float | None]   # None = scheduled but unmeasurable

    @property
    def evaluable(self) -> bool:
        return self.excluded_reason is None

    def endpoint_ratio(self, endpoint_h: float, baseline_h: float) -> float | None:
        """Endpoint fill normalised to this well's own pre-treatment fill."""
        if not self.evaluable:
            return None
        end = self.fill_by_time.get(endpoint_h)
        base = self.fill_by_time.get(baseline_h)
        if end is None or base is None or base <= 0:
            return None
        return end / base


@dataclass
class PlateResult:
    """One simulated plate."""

    wells: list[WellResult]
    design: DesignSpec

    @property
    def usable_wells(self) -> list[WellResult]:
        """Wells that survived, were not excluded, and yielded an endpoint."""
        base = self._baseline_time()
        return [
            w
            for w in self.wells
            if w.endpoint_ratio(self.design.endpoint_time_h, base) is not None
        ]

    def _baseline_time(self) -> float:
        """Latest scheduled imaging at or before treatment - the per-well baseline."""
        pre = [t for t in self.design.imaging_times_h if t <= self.design.treatment_time_h]
        return max(pre) if pre else self.design.treatment_time_h

    def ratios_by_condition(self) -> dict[str, list[float]]:
        base = self._baseline_time()
        out: dict[str, list[float]] = {}
        for w in self.wells:
            r = w.endpoint_ratio(self.design.endpoint_time_h, base)
            if r is not None:
                out.setdefault(w.condition, []).append(r)
        return out

    @property
    def lysed_fraction(self) -> dict[str, float]:
        """Fraction of evaluable wells whose scaffold failed before the endpoint."""
        out: dict[str, float] = {}
        for cond in {w.condition for w in self.wells}:
            ws = [w for w in self.wells if w.condition == cond and w.evaluable]
            if not ws:
                continue
            lysed = sum(
                1
                for w in ws
                if w.lysis_time_h is not None
                and w.lysis_time_h <= self.design.endpoint_time_h
            )
            out[cond] = lysed / len(ws)
        return out


class ExperimentTwin:
    """Simulates plates under a given calibration."""

    def __init__(self, params: TwinParams = DEFAULT_PARAMS, seed: int | None = None):
        self.p = params
        self.rng = np.random.default_rng(seed)

    # -- component models ---------------------------------------------------

    def _plateau_for(self, condition: str, well_effect: float) -> float:
        """Post-treatment plateau fill% for an arm.

        The treatment effect is INJECTED ground truth, not a measurement -
        Experiment 4 lost its treatment window to fibrinolysis.
        """
        plateau = self.p.plateau_fill_pct
        if condition in TGFB_ARMS:
            plateau += self.p.tgfb_effect_pct          # negative: contracts further
            if condition in MSC_CM_ARMS:
                plateau -= self.p.tgfb_effect_pct * self.p.msc_cm_rescue_frac
        return plateau * well_effect

    def _fill_at(self, t_h: float, condition: str, well_effect: float) -> float:
        """Fill% at time t: fast exponential contraction, then slow creep.

        Before treatment every arm is identical - which is what Experiment 4
        measured (no condition separation at the Day-5 t0). After t0 the
        plateau moves toward the arm's treated value over TREATMENT_TAU_H,
        rather than stepping instantaneously.
        """
        pre_plateau = self.p.plateau_fill_pct * well_effect
        treated_plateau = self._plateau_for(condition, well_effect)

        if t_h <= self._treatment_time:
            plateau = pre_plateau
        else:
            approach = 1.0 - math.exp(-(t_h - self._treatment_time) / TREATMENT_TAU_H)
            plateau = pre_plateau + (treated_plateau - pre_plateau) * approach

        fill = plateau + (INITIAL_FILL_PCT - plateau) * math.exp(-t_h / self.p.contraction_tau_h)
        fill -= self.p.slow_creep_pct_per_day * (t_h / 24.0)
        return max(fill, 0.0)

    def _sample_lysis_time(self, condition: str, antifibrinolytic: bool) -> float | None:
        """Weibull scaffold-survival draw. None means it outlived the run."""
        scale = (
            self.p.lysis_scale_contractile_h
            if condition in TGFB_ARMS
            else self.p.lysis_scale_quiescent_h
        )
        if antifibrinolytic:
            scale *= self.p.aprotinin_hazard_scale   # ASSUMED, not measured
        u = self.rng.random()
        t = scale * (-math.log(1 - u)) ** (1 / self.p.lysis_shape)
        return float(t)

    # -- plate simulation ---------------------------------------------------

    def simulate_plate(self, design: DesignSpec) -> PlateResult:
        self._treatment_time = design.treatment_time_h
        p_measure = (
            P_MEASURE_OK_LOCKED_PROTOCOL
            if design.locked_imaging_protocol
            else P_MEASURE_OK_UNCONTROLLED
        )

        wells: list[WellResult] = []
        for condition in design.conditions:
            for rep in range(design.replicates_per_condition):
                excluded = None
                if self.rng.random() < self.p.p_cast_failure:
                    excluded = "cast_failure"
                elif self.rng.random() < self.p.p_contamination:
                    excluded = "contamination"

                well_effect = float(
                    self.rng.lognormal(mean=0.0, sigma=self.p.well_effect_log_sd)
                )
                # Fixed per-well segmentation bias. Applied to every frame of
                # this well, so it cancels when the endpoint is normalised to
                # that well's own baseline - which is the point of doing so.
                well_bias = float(self.rng.normal(0.0, self.p.measurement_bias_pct))
                lysis_t = self._sample_lysis_time(condition, design.antifibrinolytic)

                fills: dict[float, float | None] = {}
                for t in design.imaging_times_h:
                    if excluded is not None:
                        fills[t] = None
                    elif lysis_t is not None and t >= lysis_t:
                        fills[t] = None          # no coherent construct to measure
                    elif self.rng.random() > p_measure:
                        fills[t] = None          # segmentation failed on this frame
                    else:
                        true_fill = self._fill_at(t, condition, well_effect)
                        noise = self.rng.normal(0.0, self.p.measurement_noise_pct)
                        fills[t] = max(true_fill + well_bias + noise, 0.0)

                wells.append(
                    WellResult(
                        condition=condition,
                        replicate=rep,
                        excluded_reason=excluded,
                        lysis_time_h=lysis_t,
                        fill_by_time=fills,
                    )
                )
        return PlateResult(wells=wells, design=design)

    def simulate_many(self, design: DesignSpec, n: int) -> list[PlateResult]:
        return [self.simulate_plate(design) for _ in range(n)]
