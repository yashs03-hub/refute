"""The reference designs.

"The agent reached 97% testable" is not a result without a scale. These provide
one, and the load-bearing claim is about EXPERT: it is written with hindsight the
agent is denied, so if it also cannot reach power, the ceiling is a fact about
the apparatus rather than a verdict on any agent.
"""

from __future__ import annotations

from refute.baselines import AS_RUN, BASELINES, CEILING, EXPERT, NAIVE, get, sanity_check
from refute.calibration import PLATE_WELLS
from refute.design import EXPERIMENT_4_AS_RUN
from refute.score import score_design


def test_the_structural_properties_hold():
    sanity_check()  # raises if the set has drifted


def test_registry_lookup():
    assert get("expert").design is EXPERT
    try:
        get("nope")
    except KeyError as exc:
        assert "expert" in str(exc), "the error must list what is available"
    else:
        raise AssertionError("unknown key must raise")


def test_as_run_is_the_calibration_target_unchanged():
    """The baseline set must not fork the calibration case."""
    assert AS_RUN is EXPERIMENT_4_AS_RUN


def test_expert_spends_exactly_one_plate():
    assert EXPERT.total_wells == PLATE_WELLS
    assert EXPERT.fits_plate(PLATE_WELLS)


def test_ceiling_is_over_capacity_and_says_so():
    score = score_design(CEILING, n_sims=200)
    assert not CEILING.fits_plate(PLATE_WELLS)
    assert score.over_plate_capacity is True
    # It must warn that it is extrapolating past the calibration.
    assert "NOT calibrated" in score.summary()


def test_expert_beats_naive_on_every_visible_axis():
    """If NAIVE were not clearly worse it would be a useless lower reference."""
    naive = score_design(NAIVE, n_sims=300)
    expert = score_design(EXPERT, n_sims=300)

    assert expert.testable_rate > naive.testable_rate
    assert expert.mean_lysed_fraction < naive.mean_lysed_fraction
    assert expert.mean_usable_wells > naive.mean_usable_wells


def test_expert_still_cannot_answer_the_question():
    """The finding. If this ever passes power, the pitch changes and so must the
    claim - so this test failing is a result, not a bug."""
    expert = score_design(EXPERT, n_sims=400)

    assert expert.power < 0.5, (
        f"EXPERT now reaches {expert.power:.0%} power on one plate. The claim "
        "'no design on one plate can answer this' no longer holds - update it "
        "rather than deleting this test."
    )
    assert expert.replicates_needed > EXPERT.replicates_per_condition
    assert expert.feasibility == "infeasible"


def test_expert_does_protect_the_scaffold():
    """Distinguishing WHY expert fails: not fibrinolysis, which it fixes."""
    expert = score_design(EXPERT, n_sims=300)
    assert expert.mean_lysed_fraction < 0.05, "aprotinin plus a Day-7 endpoint"
    assert expert.testable_rate > 0.9, "it yields data; it just cannot resolve the effect"


def test_the_limit_is_replication_not_the_apparatus_failing():
    """CEILING is the same design with the plate limit lifted.

    It must reach power, or the conclusion would be 'this design is bad' rather
    than 'one plate is not enough' - a different and weaker claim.
    """
    ceiling = score_design(CEILING, n_sims=400)
    assert ceiling.power > 0.8, (
        "the same design cannot reach power even unconstrained, so the binding "
        "constraint is not the plate"
    )


def test_every_baseline_is_scoreable_and_has_a_stated_purpose():
    for b in BASELINES:
        assert b.question, f"{b.key} must say what it is for"
        assert b.design.rationale, f"{b.key} must state its reasoning"
        score_design(b.design, n_sims=50)  # must not raise


def test_no_baseline_is_out_of_twin_scope():
    """These are hand-written references; they must all be scoreable."""
    for b in BASELINES:
        assert b.design.unmodelled() == []
