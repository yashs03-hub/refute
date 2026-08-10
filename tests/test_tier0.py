"""Tier 0 - power arithmetic for any assay, and the gate that refuses to guess.

The arithmetic is checked against textbook values rather than against itself: a
power function that agrees with its own inverse can still be wrong, and this is
the one part of `refute` a colleague might use on their own experiment.
"""

from __future__ import annotations

import math

import pytest

from refute.tier0 import (
    MIN_REPLICATES,
    Tier0Design,
    Tier0InputError,
    score_tier0,
)


def _d(**kw) -> Tier0Design:
    base = dict(
        assay="test assay",
        n_arms=2,
        replicates_per_arm=6,
        capacity=12,
        expected_effect=8.0,
        variability_sd=6.0,
    )
    base.update(kw)
    return Tier0Design(**base)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_missing_sd_is_refused_with_what_to_do():
    with pytest.raises(Tier0InputError) as excinfo:
        score_tier0(_d(variability_sd=None))
    msg = str(excinfo.value)
    assert "variability_sd" in msg
    assert "pilot" in msg
    # It must name why guessing is not offered, not just decline.
    assert "looks like a calculation and is not one" in msg


def test_missing_effect_is_refused():
    with pytest.raises(Tier0InputError):
        score_tier0(_d(expected_effect=None))


def test_both_missing_are_reported_together():
    with pytest.raises(Tier0InputError) as excinfo:
        score_tier0(_d(expected_effect=None, variability_sd=None))
    msg = str(excinfo.value)
    assert "expected_effect" in msg and "variability_sd" in msg


def test_zero_effect_is_refused_rather_than_returning_infinite_n():
    with pytest.raises(Tier0InputError) as excinfo:
        score_tier0(_d(expected_effect=0.0))
    assert "smallest difference" in str(excinfo.value)


def test_non_positive_sd_is_refused():
    with pytest.raises(Tier0InputError):
        score_tier0(_d(variability_sd=0.0))


def test_one_arm_is_not_a_comparison():
    with pytest.raises(Tier0InputError):
        score_tier0(_d(n_arms=1))


# ---------------------------------------------------------------------------
# The arithmetic, against known values
# ---------------------------------------------------------------------------


def test_power_matches_the_textbook_cases():
    """Checked against external values, not against this module's own inverse.

    Two canonical points for a two-sided two-sample t-test at alpha=0.05:
    d=0.8 needs ~26 per arm for 80% power, and d=1.0 needs ~16. (I first wrote
    this test asserting 26 for d=1.0, which is the d=0.8 figure - the
    implementation was right and the expectation was wrong.)
    """
    at_26 = score_tier0(
        _d(expected_effect=0.8, variability_sd=1.0, replicates_per_arm=26, capacity=200)
    )
    assert 0.78 <= at_26.power <= 0.82, at_26.power

    for d, expected_n in ((0.8, 26), (1.0, 17), (0.5, 64)):
        needed = score_tier0(
            _d(expected_effect=d, variability_sd=1.0, capacity=1000)
        ).replicates_needed
        assert abs(needed - expected_n) <= 2, f"d={d}: got {needed}, expected ~{expected_n}"


def test_power_and_required_n_are_mutually_consistent():
    """At exactly `replicates_needed`, power must reach the target."""
    score = score_tier0(_d(capacity=1000))
    at_needed = score_tier0(
        _d(capacity=1000, replicates_per_arm=score.replicates_needed)
    )
    assert at_needed.power >= at_needed.design.target_power
    # And one fewer must fall short, or the search overshot.
    if score.replicates_needed > MIN_REPLICATES:
        below = score_tier0(
            _d(capacity=1000, replicates_per_arm=score.replicates_needed - 1)
        )
        assert below.power < below.design.target_power


def test_power_rises_with_replication():
    powers = [
        score_tier0(_d(replicates_per_arm=n, capacity=1000)).power
        for n in (3, 6, 12, 30)
    ]
    assert powers == sorted(powers)


def test_power_rises_with_effect_size():
    small = score_tier0(_d(expected_effect=2.0, capacity=1000)).power
    large = score_tier0(_d(expected_effect=20.0, capacity=1000)).power
    assert large > small


def test_a_larger_sd_needs_more_replication():
    tight = score_tier0(_d(variability_sd=2.0, capacity=1000)).replicates_needed
    loose = score_tier0(_d(variability_sd=12.0, capacity=1000)).replicates_needed
    assert loose > tight


def test_the_mde_is_detectable_and_a_smaller_effect_is_not():
    """The minimum detectable effect must actually be at the target power."""
    score = score_tier0(_d(capacity=1000))
    at_mde = score_tier0(
        _d(expected_effect=score.min_detectable_effect, capacity=1000)
    )
    assert at_mde.power == pytest.approx(at_mde.design.target_power, abs=0.03)


def test_effect_sign_does_not_matter():
    up = score_tier0(_d(expected_effect=8.0, capacity=1000))
    down = score_tier0(_d(expected_effect=-8.0, capacity=1000))
    assert up.power == pytest.approx(down.power)


# ---------------------------------------------------------------------------
# Verdicts, in the same vocabulary as tier 1
# ---------------------------------------------------------------------------


def test_feasible_when_the_requirement_fits():
    score = score_tier0(_d(expected_effect=30.0, variability_sd=6.0, capacity=100))
    assert score.feasibility == "feasible"
    assert not score.underpowered


def test_infeasible_when_the_requirement_exceeds_capacity():
    score = score_tier0(_d(expected_effect=2.0, variability_sd=6.0, capacity=12))
    assert score.feasibility == "infeasible"


def test_beyond_scale_when_the_effect_is_hopeless():
    """A tiny effect must not return a huge precise-looking number."""
    score = score_tier0(
        _d(expected_effect=0.0001, variability_sd=6.0, capacity=12)
    )
    assert score.replicates_needed == -1
    assert score.feasibility == "beyond-scale"
    assert ">" in score.summary(), "it must show a bound, not a false precision"


def test_over_capacity_as_designed_is_reported():
    score = score_tier0(_d(replicates_per_arm=50, capacity=12))
    assert score.fits_capacity is False
    assert "over capacity as designed" in score.summary()


def test_the_vocabulary_matches_tier_one():
    """A tier-0 and a tier-1 verdict must mean the same thing."""
    from refute.score import ALPHA

    assert score_tier0(_d(capacity=1000)).design.alpha == ALPHA
    verdicts = {
        score_tier0(_d(expected_effect=e, variability_sd=6.0, capacity=12)).feasibility
        for e in (0.0001, 2.0, 30.0)
    }
    assert verdicts <= {"feasible", "infeasible", "beyond-scale"}


# ---------------------------------------------------------------------------
# The standing caveat
# ---------------------------------------------------------------------------


def test_every_summary_says_it_cannot_model_failure():
    """The one thing a reader must not forget.

    A green tier-0 verdict says the comparison could resolve the effect. It says
    nothing about the preparation surviving - and Experiment 4 is the proof.
    """
    for kw in ({}, {"expected_effect": 30.0, "capacity": 100}, {"capacity": 1000}):
        summary = score_tier0(_d(**kw)).summary()
        assert "arithmetic, not simulation" in summary
        assert "NOTHING about whether the preparation" in summary
        assert "fibrinolysis" in summary, "name the concrete example, not a warning"


def test_the_summary_reports_cohens_d():
    """So a reader can sanity-check the inputs against their own intuition."""
    assert "Cohen's d = 1.33" in score_tier0(_d()).summary()


def test_the_ladder_states_what_each_tier_needs():
    from refute.tier0 import TIER_LADDER

    assert "0/10 recoverable" in TIER_LADDER
    assert "fibrin_contracture" in TIER_LADDER
    # It must say plainly what tier 0 cannot do. Whitespace-normalised: the text
    # is hard-wrapped, so a naive substring check tests the line breaks.
    flat = " ".join(TIER_LADDER.split())
    assert "cannot do is tell you the gel dissolves" in flat


def test_cli_reports_and_fails_closed(capsys):
    from refute.cli import main

    assert main(["tier0", "--effect", "8", "--sd", "6", "--n", "6"]) == 0
    assert "TIER 0" in capsys.readouterr().out

    # Missing SD must exit non-zero rather than printing a number.
    assert main(["tier0", "--effect", "8"]) == 2
    out = capsys.readouterr().out
    assert "CANNOT ASSESS" in out
    assert "power at this replication" not in out


def test_tier0_needs_no_credential_and_no_twin(monkeypatch):
    import refute.providers as providers
    import refute.twin as twin_mod

    monkeypatch.setattr(
        providers, "get_provider", lambda *_a, **_k: pytest.fail("called a model")
    )
    monkeypatch.setattr(
        twin_mod.ExperimentTwin,
        "simulate_many",
        lambda *_a, **_k: pytest.fail("tier 0 must not run the fibrin twin"),
    )
    score_tier0(_d())


def test_total_units_and_fits():
    d = _d(n_arms=3, replicates_per_arm=4, capacity=12)
    assert d.total_units == 12
    assert d.fits is True
    assert _d(n_arms=3, replicates_per_arm=5, capacity=12).fits is False


def test_below_two_per_arm_has_no_power():
    assert score_tier0(_d(replicates_per_arm=1)).power == 0.0
    assert math.isinf(score_tier0(_d(replicates_per_arm=1)).min_detectable_effect)
