"""The environment interface.

Every test here passes a `DesignSpec` rather than prose, which is the point:
the pure-simulation path must be exercisable with no credential and no network.
The one test that touches extraction stubs it out.
"""

from __future__ import annotations

import pytest

from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec
from refute.environment import (
    DEFAULT_MAX_ROUNDS,
    EpisodeError,
    RefuteEnv,
    StepResult,
)

# A design with room to be wrong: two arms, the plate filled, but no
# antifibrinolytic and a Day-10 endpoint, so the scaffold is gone first.
UNDERPOWERED = DesignSpec(
    conditions=["N-T", "N-CM+T"],
    replicates_per_condition=6,
    imaging_times_h=[6, 24, 120, 240],
    treatment_time_h=120.0,
    endpoint_time_h=240.0,
    antifibrinolytic=False,
    normalise_to_own_baseline=True,
    locked_imaging_protocol=True,
)


def test_reset_returns_the_brief():
    env = RefuteEnv()
    obs = env.reset()
    assert isinstance(obs, str)
    # The brief must state the resource limit, or an agent cannot know the
    # plate is the whole experiment and every score is unfair.
    assert "12-well" in obs


def test_step_before_reset_is_refused():
    env = RefuteEnv()
    with pytest.raises(EpisodeError):
        env.step(EXPERIMENT_4_AS_RUN)


def test_step_after_episode_end_is_refused():
    env = RefuteEnv(max_rounds=1)
    env.reset()
    env.step(EXPERIMENT_4_AS_RUN)
    with pytest.raises(EpisodeError):
        env.step(EXPERIMENT_4_AS_RUN)


def test_spec_action_needs_no_credential(monkeypatch):
    """Scoring a DesignSpec must not reach for a provider.

    Enforced by making any provider lookup raise: if `step` calls a model when
    handed a spec, this test fails rather than silently costing money.
    """
    import refute.providers as providers

    def explode(*_a, **_k):
        raise AssertionError("step() called a model provider for a DesignSpec action")

    monkeypatch.setattr(providers, "get_provider", explode)

    env = RefuteEnv(n_sims=50)
    env.reset()
    result = env.step(EXPERIMENT_4_AS_RUN)
    assert result.info["scored"] is True


def test_reward_is_power_and_nothing_else():
    env = RefuteEnv(n_sims=200)
    env.reset()
    result = env.step(UNDERPOWERED)
    # The reward must be the reported power exactly - not a composite, not
    # rescaled. A caller building a different objective from `info` depends on
    # this being the raw number.
    assert result.reward == result.info["design_score"].power
    assert result.reward == result.info["power"]


def test_step_result_unpacks_as_a_tuple():
    env = RefuteEnv(n_sims=50)
    env.reset()
    result = env.step(EXPERIMENT_4_AS_RUN)
    obs, reward, done, info = result
    assert isinstance(result, StepResult)
    assert reward == result.reward
    assert done == result.done
    assert info is result.info
    assert obs == result.observation


def test_experiment_4_as_run_scores_zero_and_reports_why():
    """The calibration case is the environment's own regression pin."""
    env = RefuteEnv(n_sims=200)
    env.reset()
    obs, reward, done, info = env.step(EXPERIMENT_4_AS_RUN)

    assert reward == 0.0  # the design that was actually run recovers nothing
    assert info["diagnoses"], "a 0% design must say what went wrong"
    # Its defining failure: the scaffold dissolved before the endpoint.
    assert info["mean_lysed_fraction"] > 0.3
    # Not terminal by power, so feedback must be offered for a revision turn.
    assert done is False
    assert isinstance(obs, str) and obs


def test_feedback_is_withheld_once_the_episode_ends():
    env = RefuteEnv(max_rounds=1, n_sims=50)
    env.reset()
    obs, _reward, done, info = env.step(EXPERIMENT_4_AS_RUN)
    assert done is True
    assert obs is None, "a finished episode must not hand back actionable feedback"
    assert info["terminated_reason"] == "max_rounds"


def test_episode_ends_at_max_rounds():
    env = RefuteEnv(max_rounds=DEFAULT_MAX_ROUNDS, n_sims=50)
    env.reset()
    for i in range(DEFAULT_MAX_ROUNDS):
        result = env.step(EXPERIMENT_4_AS_RUN)
        assert result.info["round"] == i + 1
    assert result.done is True
    assert len(env.history) == DEFAULT_MAX_ROUNDS


def test_target_power_terminates_early():
    """A trivially reachable target must end the episode as target_power_reached."""
    env = RefuteEnv(max_rounds=5, target_power=0.0, n_sims=50)
    env.reset()
    result = env.step(EXPERIMENT_4_AS_RUN)
    assert result.done is True
    assert result.info["terminated_reason"] == "target_power_reached"


def test_extraction_failure_is_not_recorded_as_a_bad_design(monkeypatch):
    """A parsing failure must not enter the record as a zero-power design.

    This is the confound `agent.py` holds the extractor constant to avoid: if
    extraction errors were scored, a provider outage would look like the agent
    designing badly.
    """
    import refute.agent as agent_mod

    def boom(*_a, **_k):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(agent_mod, "extract_design", boom)

    env = RefuteEnv()
    env.reset()
    result = env.step("some prose describing a plate")

    assert result.info["scored"] is False
    assert result.info["error"] == "extraction_failed"
    assert "provider exploded" in result.info["detail"]
    assert result.done is True
    assert env.history == [], "an unscored step must not enter the episode record"


def test_empty_prose_fails_without_calling_a_model(monkeypatch):
    import refute.agent as agent_mod

    monkeypatch.setattr(
        agent_mod,
        "extract_design",
        lambda *_a, **_k: pytest.fail("empty text should not reach the extractor"),
    )

    env = RefuteEnv()
    env.reset()
    result = env.step("   ")
    assert result.info["error"] == "extraction_failed"
    assert result.info["detail"] == "empty design text"


def test_prose_action_is_scored_when_extraction_succeeds(monkeypatch):
    import refute.agent as agent_mod

    monkeypatch.setattr(
        agent_mod, "extract_design", lambda *_a, **_k: EXPERIMENT_4_AS_RUN
    )

    env = RefuteEnv(n_sims=50)
    env.reset()
    result = env.step("prose that the stub will turn into the as-run design")
    assert result.info["scored"] is True
    assert result.info["extracted"] == EXPERIMENT_4_AS_RUN


def test_non_string_non_spec_action_is_a_type_error():
    env = RefuteEnv()
    env.reset()
    with pytest.raises(TypeError):
        env.step(42)


def test_reset_clears_the_previous_episode():
    env = RefuteEnv(max_rounds=1, n_sims=50)
    env.reset()
    env.step(EXPERIMENT_4_AS_RUN)
    assert len(env.history) == 1
    env.reset()
    assert env.history == []
    assert env.round == 0
    assert env.best_power == 0.0


def test_transcript_and_best_power_report_the_episode():
    env = RefuteEnv(max_rounds=2, n_sims=100)
    env.reset()
    assert env.transcript() == "no scored steps"
    env.step(EXPERIMENT_4_AS_RUN)
    env.step(UNDERPOWERED)
    lines = env.transcript().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("round 1:")
    assert env.best_power == max(h["power"] for h in env.history)


def test_determinism_same_seed_same_reward():
    a = RefuteEnv(seed=7, n_sims=100)
    a.reset()
    b = RefuteEnv(seed=7, n_sims=100)
    b.reset()
    assert a.step(UNDERPOWERED).reward == b.step(UNDERPOWERED).reward
