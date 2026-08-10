"""The `Agent` interface.

`propose_design`/`revise_design` are one implementation - a single chat
completion. The benchmark is about design quality, not about that scaffold, so
anything satisfying `Agent` must be scoreable without editing `agent.py`.

Nothing here calls a model.
"""

from __future__ import annotations

from refute.agent import Agent, ChatModelAgent
from refute.design import EXPERIMENT_4_AS_RUN
from refute.environment import RefuteEnv
from refute.providers import DEFAULT_AGENT, ModelSpec


class ScriptedAgent:
    """A subject with no model behind it at all."""

    def __init__(self) -> None:
        self.briefs: list[str] = []
        self.feedback_seen: list[str] = []

    def propose(self, brief: str) -> str:
        self.briefs.append(brief)
        return "four arms, n=3, day 10 endpoint, no antifibrinolytic"

    def revise(self, brief: str, previous_design: str, feedback: str) -> str:
        self.feedback_seen.append(feedback)
        return "two arms, n=6, aprotinin, day 7 endpoint"


def test_a_model_free_agent_satisfies_the_protocol():
    """The Protocol must be structural - no inheritance, no registration."""
    assert isinstance(ScriptedAgent(), Agent)


def test_the_reference_agent_satisfies_it_too():
    assert isinstance(ChatModelAgent(), Agent)


def test_something_missing_revise_is_not_an_agent():
    class ProposeOnly:
        def propose(self, brief: str) -> str:
            return "a design"

    assert not isinstance(ProposeOnly(), Agent)


def test_the_reference_agent_defaults_to_the_benchmarked_model():
    assert ChatModelAgent().spec == DEFAULT_AGENT


def test_the_reference_agent_passes_its_spec_through(monkeypatch):
    """The model under test must reach the provider unchanged.

    A wrapper that quietly substituted a different model would invalidate every
    result attributed to it.
    """
    import refute.agent as agent_mod

    seen: dict[str, object] = {}

    def fake_propose(brief, spec):
        seen["brief"], seen["spec"] = brief, spec
        return "a design"

    monkeypatch.setattr(agent_mod, "propose_design", fake_propose)

    spec = ModelSpec("openai", "gpt-5.5", "high")
    out = ChatModelAgent(spec=spec).propose("the brief")

    assert out == "a design"
    assert seen["spec"] is spec
    assert seen["brief"] == "the brief"


def test_revise_passes_all_three_arguments_through(monkeypatch):
    import refute.agent as agent_mod

    seen: dict[str, object] = {}

    def fake_revise(brief, previous, feedback, spec):
        seen.update(brief=brief, previous=previous, feedback=feedback, spec=spec)
        return "revised"

    monkeypatch.setattr(agent_mod, "revise_design", fake_revise)

    out = ChatModelAgent().revise("brief", "old design", "the scaffold was gone")
    assert out == "revised"
    assert seen["feedback"] == "the scaffold was gone"
    assert seen["previous"] == "old design"


def test_a_scripted_agent_can_be_driven_through_the_environment(monkeypatch):
    """The end-to-end claim: bring your own agent, get scored by the twin."""
    import refute.agent as agent_mod

    # Stub extraction so the loop needs no credential; the point under test is
    # the interface, not the extractor.
    monkeypatch.setattr(
        agent_mod, "extract_design", lambda *_a, **_k: EXPERIMENT_4_AS_RUN
    )

    agent = ScriptedAgent()
    env = RefuteEnv(max_rounds=2, n_sims=50)

    brief = env.reset()
    obs, reward, done, _info = env.step(agent.propose(brief))
    assert done is False
    assert reward == 0.0

    revised = agent.revise(brief, "previous", obs)
    _obs2, _reward2, done2, _info2 = env.step(revised)

    assert done2 is True
    assert agent.briefs == [brief]
    # The agent must have been handed consequences, not corrections.
    assert len(agent.feedback_seen) == 1
    assert "aprotinin" not in agent.feedback_seen[0].lower()


def test_the_brief_does_not_leak_the_answers():
    """Pre-registration integrity - the property the whole benchmark rests on.

    If the brief mentions fibrinolysis or an antifibrinolytic, the agent is being
    told the answer and every score afterwards is meaningless. This had no test,
    which is alarming for the single assumption everything else depends on.
    """
    from refute.agent import EXPERIMENT_4_BRIEF

    lowered = EXPERIMENT_4_BRIEF.lower()
    for leak in (
        "fibrinolysis",
        "fibrinolytic",
        "aprotinin",
        "tranexamic",
        "aminocaproic",
        "plasmin",
        "dissolv",       # "the gels dissolve"
        "lysis",
        "half-time",
        "5.8",           # the fitted contraction half-time
    ):
        assert leak not in lowered, f"the brief leaks '{leak}'"


def test_the_brief_states_what_the_apparatus_can_measure():
    """Added after two live runs were refused a score.

    The brief constrained the plate count and the camera but not the readout, so
    gpt-5.5 proposed neck-width narrowing - which the twin cannot simulate, its
    measurement model being calibrated for area segmentation. Rejecting a design
    for using the equipment differently than assumed measures conformance to an
    unstated convention rather than design quality.
    """
    from refute.agent import EXPERIMENT_4_BRIEF

    lowered = EXPERIMENT_4_BRIEF.lower()
    assert "area" in lowered, "the brief must name the quantity that is measured"
    assert "12-well" in lowered, "and the resource limit"


def test_feedback_never_names_the_fix(monkeypatch):
    """The scaffold-failure diagnosis must describe what happened, not what to add."""
    from refute.score import feedback_for_agent, score_design

    score = score_design(EXPERIMENT_4_AS_RUN, n_sims=200)
    text = feedback_for_agent(score).lower()

    assert "scaffold" in text  # the consequence is stated
    # The named remedies must not be. "no antifibrinolytic in the formulation"
    # reports an absence in the design as extracted, so the generic word is
    # allowed; naming an actual agent would be a correction.
    for remedy in ("aprotinin", "tranexamic", "aminocaproic"):
        assert remedy not in text
