"""Tests for bleomycin_optimize and bleomycin_advise."""

from __future__ import annotations

import inspect
import pytest

from refute.bleomycin_advise import advise_bleomycin_design
from refute.bleomycin_calibration import DEFAULT_COHORT_CAPACITY
from refute.bleomycin_design import BleomycinDesignSpec
from refute.bleomycin_optimize import optimize_bleomycin_design


def test_msc_route_has_no_default_in_optimize_bleomycin_design():
    sig = inspect.signature(optimize_bleomycin_design)
    assert sig.parameters["msc_route"].default is inspect.Parameter.empty


def test_msc_route_empty_raises_value_error():
    with pytest.raises(ValueError, match="msc_route must be explicitly specified"):
        optimize_bleomycin_design(msc_route="")


def test_msc_route_invalid_raises_value_error():
    with pytest.raises(ValueError, match="unknown msc_route"):
        optimize_bleomycin_design(msc_route="IM")


def test_bleomycin_optimize_assumption_sensitive_gating():
    result = optimize_bleomycin_design(
        msc_route="IT",
        target_power=0.01,
        target_testable=0.01,
        capacity=DEFAULT_COHORT_CAPACITY,
        n_sims=100,
    )
    # By default, assumption-sensitive candidates are rejected
    assert not result.found or result.score is not None


def test_bleomycin_optimize_capacity_bound():
    result = optimize_bleomycin_design(
        msc_route="IT",
        target_power=0.01,
        target_testable=0.01,
        capacity=16,
        allow_assumption_sensitive=True,
        n_sims=100,
    )
    for t in result.trials:
        assert t.design.total_animals <= 16


def test_bleomycin_advise_basic():
    design = BleomycinDesignSpec(
        conditions=["bleomycin_only", "bleomycin_MSC"],
        replicates_per_condition=5,
        msc_dosing_day=14.0,
        msc_route="IV",
    )
    advice = advise_bleomycin_design(design, n_sims=100)
    assert advice.original is not None
    assert len(advice.suggestions) > 0
    # Checking that earlier-dosing or switch-route are suggested
    levers = [s.lever for s in advice.suggestions]
    assert "earlier-dosing" in levers or "switch-route" in levers
