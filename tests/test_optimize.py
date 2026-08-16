"""The optimizer is a search against the twin, and PLAN §9.1 says that is only
safe as long as the agent under test never gets to run it. These tests protect
that boundary first and the arithmetic second - a correct search reachable
from `agent.py` would be a worse outcome than an incorrect one that stays out
of reach.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from refute.calibration import PLATE_WELLS
from refute.optimize import (
    CANONICAL_CONDITIONS,
    SPARSE_SCHEDULE,
    optimize_design,
)
from refute.score import HEADLINE_CONTRAST

REPO_ROOT = Path(__file__).resolve().parent.parent


# -- the boundary that must not move -----------------------------------------


@pytest.mark.parametrize("module", ["agent.py", "environment.py", "api.py"])
def test_the_agent_facing_surface_never_imports_optimize(module: str):
    """§9.1: handing the optimizer to the harness turns the benchmark into a
    search against `twin.py`. A source-text check rather than a runtime import
    check on purpose - this must fail on a lazy `from .optimize import ...`
    buried inside a function body too, not only on a module-level import."""
    text = (REPO_ROOT / "refute" / module).read_text()
    assert "optimize" not in text, (
        f"{module} references `optimize` - the CLI is the only place this "
        "module may be reachable from. See optimize.py's module docstring."
    )


def test_optimize_module_states_the_boundary_in_its_own_docstring():
    """The invariant has to be legible at the point it could be violated, not
    only in a test file nobody reads while adding a feature."""
    import refute.optimize as optimize_module

    doc = optimize_module.__doc__ or ""
    assert "agent.py" in doc
    assert "environment.py" in doc
    assert "api.py" in doc


# -- antifibrinolytic is never discovered, only stated -----------------------


def test_antifibrinolytic_has_no_default_the_search_could_fall_back_to():
    """§9.1's sharp form, by name: flipping this one bool is a cheat code
    because its effect size is ASSUMED, not measured. `optimize_design` must
    require the caller to state it - a search that could quietly try both and
    keep whichever scores better would be finding the cheat code
    automatically."""
    import inspect

    sig = inspect.signature(optimize_design)
    assert sig.parameters["antifibrinolytic"].default is inspect.Parameter.empty


def test_a_winner_that_only_wins_via_the_assumed_constant_is_rejected_by_default():
    """Every candidate this search can build with antifibrinolytic=True
    reaches the assumed constant, so with a low enough bar every candidate
    technically clears power - but none of them should be handed back as a
    clean winner while `allow_assumption_sensitive` is left at its default."""
    result = optimize_design(
        antifibrinolytic=True,
        target_power=0.01,   # trivially low - would win immediately if allowed to
        target_testable=0.01,
        capacity=PLATE_WELLS,
        n_sims=150,
    )
    assert not result.found, (
        "an assumption-sensitive design won without the caller opting in"
    )
    assert all(t.score.verdict_sensitive_to_assumption for t in result.trials)


def test_the_same_low_bar_wins_once_assumption_sensitivity_is_allowed():
    """The other half of the same property: nothing is broken, the gate is
    just closed by default and opens on request."""
    result = optimize_design(
        antifibrinolytic=True,
        target_power=0.01,
        target_testable=0.01,
        capacity=PLATE_WELLS,
        allow_assumption_sensitive=True,
        n_sims=150,
    )
    assert result.found
    assert result.score is not None
    assert result.score.power >= 0.01
    assert result.score.testable_rate >= 0.01


# -- the search itself --------------------------------------------------------


def test_an_unreachable_target_is_reported_honestly_not_forced():
    """Mirrors `advise`'s and `tier0`'s own house style: 'the question cannot
    be answered at this scale' is a legitimate result, not a bug to work
    around by returning the best-effort candidate as though it had won."""
    result = optimize_design(
        antifibrinolytic=True,
        target_power=0.999,
        target_testable=0.999,
        capacity=PLATE_WELLS,
        allow_assumption_sensitive=True,
        n_sims=150,
    )
    assert not result.found
    assert result.design is None
    assert result.score is None
    assert len(result.trials) > 0, "a failed search still has to show its work"


def test_the_search_never_exceeds_the_stated_capacity():
    result = optimize_design(
        antifibrinolytic=True,
        target_power=0.01,
        target_testable=0.01,
        capacity=24,
        allow_assumption_sensitive=True,
        n_sims=150,
    )
    for t in result.trials:
        assert t.design.total_wells <= 24, t.design.total_wells


def test_winner_uses_the_conditions_the_caller_asked_for():
    result = optimize_design(
        antifibrinolytic=True,
        target_power=0.01,
        target_testable=0.01,
        capacity=PLATE_WELLS,
        conditions=CANONICAL_CONDITIONS,
        allow_assumption_sensitive=True,
        n_sims=150,
    )
    assert result.design is not None
    assert set(result.design.conditions) == set(CANONICAL_CONDITIONS)
    assert set(HEADLINE_CONTRAST) <= set(CANONICAL_CONDITIONS), (
        "the headline contrast the scorer actually tests must be a subset of "
        "the default conditions, or every search against the default would "
        "silently score nothing - see the module docstring's story about the "
        "two-arm design that scored a flat 0%"
    )


def test_summary_names_every_trial_and_the_winner():
    result = optimize_design(
        antifibrinolytic=True,
        target_power=0.01,
        target_testable=0.01,
        capacity=PLATE_WELLS,
        allow_assumption_sensitive=True,
        n_sims=150,
    )
    out = result.summary()
    assert "WINNER" in out
    assert str(len(result.trials)) in out


def test_a_failed_search_summary_says_so_without_a_winner_section():
    result = optimize_design(
        antifibrinolytic=True,
        target_power=0.999,
        target_testable=0.999,
        capacity=PLATE_WELLS,
        allow_assumption_sensitive=True,
        n_sims=150,
    )
    out = result.summary()
    assert "NO DESIGN FOUND" in out
    assert "WINNER" not in out


def test_default_schedule_constant_matches_experiment_4s_own_imaging_times():
    """Not an invented default - Experiment 4 actually imaged at these times
    (see `calibration.py`'s `SOURCE` / `OBSERVED_FILL_PCT` keys), so the
    'sparse' schedule this module tries first is what a real plate already
    cost, not a new assumption."""
    assert set(SPARSE_SCHEDULE) <= {24.0, 72.0, 96.0, 120.0, 144.0, 168.0, 240.0}
