"""The advisor: what to change, and what changing it would do.

`feedback_for_agent` gives consequences and never corrections, because for a
benchmarked agent working out the fix is the measurement. A person asking for
help is not under test, so this module names the fix - but every suggestion has
to carry its own simulated consequence, or it is an opinion.

No model is called anywhere in this file.
"""

from __future__ import annotations

import pytest

from refute.advise import MAX_COMBINE_ROUNDS, advise
from refute.baselines import EXPERT
from refute.calibration import PLATE_WELLS
from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec

SIMS = 300


def test_suggestions_come_with_a_simulated_before_and_after():
    """The property that separates this from an opinion."""
    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    assert result.suggestions
    for s in result.suggestions:
        assert s.before.power is not None
        assert s.after.power is not None
        assert s.change, "a suggestion must say what to do at the bench"


def test_no_suggestion_exceeds_the_apparatus():
    """An early scorer bug pushed an agent to 288 wells across 24 plates by
    naming a requirement without naming the limit. Making the same mistake here
    would send a researcher to spend money on it."""
    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    for s in result.suggestions:
        assert not s.after.over_plate_capacity, s.change
    if result.best_combined:
        spec, _score = result.best_combined
        assert spec.total_wells <= PLATE_WELLS


def test_the_aprotinin_suggestion_is_flagged_as_resting_on_an_assumption():
    """Recommending it is recommending a number nobody measured."""
    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    anti = [s for s in result.suggestions if s.lever == "antifibrinolytic"]
    assert anti, "adding an antifibrinolytic must be offered for the as-run design"
    assert anti[0].assumption_sensitive
    assert "ASSUMED" in anti[0].line()


def test_protecting_the_scaffold_is_the_biggest_single_win():
    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    best = result.helpful[0]
    assert best.lever == "antifibrinolytic"
    assert best.after.mean_lysed_fraction < 0.05


def test_narrowing_alone_does_not_help_but_helps_in_combination():
    """The interaction that broke the first implementation.

    Dropping to the two arms that answer the question does nothing on its own -
    both surviving arms are the most contractile ones, so both still dissolve.
    It becomes the largest remaining gain once the scaffold is protected. A
    combiner that only applies individually-helpful levers never finds it, and
    produced a worse plate than a competent human writes.
    """
    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    narrow = [s for s in result.suggestions if s.lever == "narrow"]
    assert narrow, "narrowing must be offered"
    assert not narrow[0].helps, "narrowing alone should not help on this design"

    assert result.best_combined is not None
    assert "narrow" in result.combination_order
    assert result.combination_order.index("antifibrinolytic") < result.combination_order.index("narrow")


def test_the_combined_design_beats_every_single_change():
    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    _spec, combined = result.best_combined
    best_single = max(s.after.power for s in result.suggestions)
    assert combined.power > best_single


def test_the_advisor_matches_or_beats_a_hand_written_expert():
    """It recommends worse than a person, or it is not worth shipping."""
    from refute.score import score_design

    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    _spec, combined = result.best_combined
    expert = score_design(EXPERT, n_sims=SIMS)
    assert combined.power >= expert.power - 0.02, (
        f"advisor reached {combined.power:.0%}, expert reached {expert.power:.0%}"
    )


def test_it_says_when_nothing_is_enough():
    """The honest ending, and the project's headline. An advisor that always
    produces an encouraging next step will encourage you into a doomed plate."""
    summary = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS).summary()
    assert "cannot be answered at this scale" in summary
    assert "legitimate" in summary


def test_a_declined_design_gets_no_advice():
    declined = DesignSpec(
        conditions=[], replicates_per_condition=0,
        imaging_times_h=[1.0, 72.0], treatment_time_h=1.0, endpoint_time_h=72.0,
        antifibrinolytic=False, normalise_to_own_baseline=True,
        locked_imaging_protocol=True,
    )
    result = advise(declined, n_sims=50)
    assert result.suggestions == []
    assert "nothing to improve" in result.summary()


def test_an_out_of_scope_design_raises_rather_than_being_advised():
    from refute.design import OutOfTwinScopeError

    oos = EXPERIMENT_4_AS_RUN.model_copy(
        update={"out_of_twin_scope": ["collagen I matrix"]}
    )
    with pytest.raises(OutOfTwinScopeError):
        advise(oos, n_sims=50)


def test_an_already_good_design_gets_few_or_no_suggestions():
    """It must not manufacture advice for a design that is already sound."""
    result = advise(EXPERT, n_sims=SIMS)
    for s in result.helpful:
        assert s.delta_power > 0.01 or s.delta_testable > 0.05


def test_combination_is_bounded():
    result = advise(EXPERIMENT_4_AS_RUN, n_sims=SIMS)
    assert len(result.combination_order) <= MAX_COMBINE_ROUNDS


def test_analysis_only_changes_are_marked_as_costing_nothing():
    """A researcher should know which fixes are free."""
    sloppy = EXPERIMENT_4_AS_RUN.model_copy(
        update={"normalise_to_own_baseline": False, "locked_imaging_protocol": False}
    )
    result = advise(sloppy, n_sims=SIMS)
    free = [s for s in result.suggestions if s.lever in ("normalise", "imaging")]
    assert free
    assert any("Costs nothing" in s.caveat for s in free)


def test_cli_advise_runs_and_reports(capsys):
    from refute.cli import main

    assert main(["advise", "--sims", "100"]) == 0
    out = capsys.readouterr().out
    assert "ADVICE" in out
    assert "EVERYTHING AT ONCE" in out


def test_cli_advise_all_lists_the_changes_that_did_not_help(capsys):
    from refute.cli import main

    main(["advise", "--sims", "100", "--all"])
    out = capsys.readouterr().out
    assert "CHANGES THAT DID NOT HELP" in out
