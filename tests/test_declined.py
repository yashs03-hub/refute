"""A design that declines to run must not be scored as a failed design.

Found on 2026-08-10 by a real run. gpt-5.5, told the apparatus could not resolve
the effect, answered: "no-go for the biological question - there is no
one-12-well-plate design that will actually answer this", and specified ~130-140
wells as what would be needed. That is the verdict this benchmark reports as its
own headline finding, and the scorer gave it 0% power - the worst score available.

The benchmark was penalising, maximally, the exact epistemic behaviour it exists
to reward.
"""

from __future__ import annotations

import pytest

from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec
from refute.environment import RefuteEnv
from refute.score import feedback_for_agent, score_design

DECLINED = DesignSpec(
    conditions=[],
    replicates_per_condition=0,
    imaging_times_h=[1.0, 24.0, 48.0, 72.0],
    treatment_time_h=1.0,
    endpoint_time_h=72.0,
    antifibrinolytic=False,
    normalise_to_own_baseline=True,
    locked_imaging_protocol=True,
    rationale="No plate should be cast; the question is unanswerable at this scale.",
)


def test_a_normal_design_assigns_wells():
    assert EXPERIMENT_4_AS_RUN.assigns_wells is True


def test_no_conditions_or_no_replicates_is_declining():
    assert DECLINED.assigns_wells is False
    assert EXPERIMENT_4_AS_RUN.model_copy(
        update={"replicates_per_condition": 0}
    ).assigns_wells is False
    assert EXPERIMENT_4_AS_RUN.model_copy(
        update={"conditions": []}
    ).assigns_wells is False


def test_declining_is_reported_as_its_own_verdict():
    score = score_design(DECLINED, n_sims=50)
    assert score.declined is True
    assert score.feasibility == "declined"
    # Distinct from a design that performs badly.
    as_run = score_design(EXPERIMENT_4_AS_RUN, n_sims=50)
    assert as_run.declined is False
    assert as_run.feasibility != "declined"


def test_the_summary_refuses_to_present_numbers():
    """0% power next to a refusal reads as 'your refusal failed'."""
    summary = score_design(DECLINED, n_sims=50).summary()
    assert "DECLINED" in summary
    assert "not a failed design" in summary
    # It must NOT show the power line, which would be a placeholder read as data.
    assert "power to recover" not in summary
    # And it must say how to judge whether declining was right.
    assert "baselines" in summary


def test_the_diagnosis_says_the_numbers_are_placeholders():
    score = score_design(DECLINED, n_sims=50)
    joined = " ".join(score.diagnoses)
    assert "placeholders" in joined
    assert "NOT measurements" in joined


def test_feedback_does_not_push_the_agent_off_a_correct_refusal():
    """Telling it '0% of runs recovered the effect' would push it to propose a
    plate it has just correctly argued cannot work."""
    feedback = feedback_for_agent(score_design(DECLINED, n_sims=50))
    assert "declined" in feedback.lower()
    assert "not a failure" in feedback.lower()
    assert "0%" not in feedback
    # It must leave standing by the refusal open as an option.
    assert "stand by it" in feedback


def test_nothing_is_simulated_for_a_declined_design(monkeypatch):
    """Simulating an empty plate would return a number about no experiment."""
    import refute.twin as twin_mod

    monkeypatch.setattr(
        twin_mod.ExperimentTwin,
        "simulate_many",
        lambda *_a, **_k: pytest.fail("a declined design must not be simulated"),
    )
    score_design(DECLINED, n_sims=50)


def test_the_environment_flags_it_rather_than_hiding_it():
    """Reward is 0.0 because no defensible number exists - so the flag is the
    only thing distinguishing a correct refusal from a broken plate."""
    env = RefuteEnv(n_sims=50)
    env.reset()
    result = env.step(DECLINED)
    assert result.info["declined"] is True
    assert result.info["scored"] is True  # it WAS evaluated, just not simulated


def test_api_exposes_declined():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from refute.api import app

    client = TestClient(app)
    r = client.post("/score", json={"design": DECLINED.model_dump(), "n_sims": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["declined"] is True
    assert body["feasibility"] == "declined"


def test_the_recorded_run_that_found_this_still_reproduces_it():
    """The regression is the run itself, if it has been committed."""
    from pathlib import Path

    from refute.record import RecordedRun

    path = Path("cases/exp4/runs/gpt-5.5-high.json")
    if not path.exists():
        pytest.skip("recorded run not present")

    run = RecordedRun.load(path)
    if len(run.rounds) < 2:
        pytest.skip("run has no revision round")

    revised = run.rounds[-1].extracted
    if revised.assigns_wells:
        pytest.skip("this recorded run's revision did not decline")

    score = score_design(revised, n_sims=50)
    assert score.declined is True, (
        "the run that exposed this bug must keep exercising the fix"
    )
