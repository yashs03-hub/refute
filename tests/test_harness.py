"""Harnesses as an explicit variable.

`ChatModelAgent` being thin was right, but keeping it the ONLY option makes the
harness an invisible constant. A score belongs to a (model x harness) pair, and
these tests pin the properties that make the pair interpretable.

No model is called; every provider is stubbed.
"""

from __future__ import annotations

import pytest

from refute.agent import Agent
from refute.harness import (
    CHECKLIST_PROMPT,
    CRITIQUE_PROMPT,
    HARNESSES,
    Checklist,
    SelfCritique,
    SingleShot,
    describe,
    get_harness,
)
from refute.providers import DEFAULT_AGENT, ModelSpec


class FakeProvider:
    """Records every message list it is handed."""

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages, spec, max_tokens):
        self.calls.append([dict(m) for m in messages])
        return f"reply-{len(self.calls)}"

    def parse(self, *_a, **_k):  # pragma: no cover
        raise AssertionError("a harness must not parse")


@pytest.fixture
def provider(monkeypatch):
    p = FakeProvider()
    import refute.harness as harness_mod

    monkeypatch.setattr(harness_mod, "get_provider", lambda _name: p)
    return p


def test_every_harness_satisfies_the_agent_protocol():
    for name in HARNESSES:
        assert isinstance(get_harness(name), Agent), name


def test_every_harness_names_itself_and_what_it_adds():
    for name, cls in HARNESSES.items():
        assert cls.name == name
        assert cls.adds, f"{name} must say what it adds"


def test_unknown_harness_lists_the_known_ones():
    with pytest.raises(KeyError) as excinfo:
        get_harness("magic")
    assert "self-critique" in str(excinfo.value)


def test_single_shot_is_one_call(monkeypatch):
    calls = []
    import refute.agent as agent_mod

    monkeypatch.setattr(
        agent_mod, "propose_design", lambda brief, spec: calls.append(brief) or "design"
    )
    out = SingleShot().propose("the brief")
    assert out == "design"
    assert len(calls) == 1


def test_self_critique_is_draft_then_critique_then_final(provider):
    result = SelfCritique().propose_verbose("the brief")

    assert len(provider.calls) == 3
    assert [stage for stage, _ in result.transcript] == ["draft", "critique", "final"]
    assert result.design_text == "reply-3", "the FINAL answer is the design"

    # The critique must see the draft it is reviewing.
    second = provider.calls[1]
    assert second[-1]["content"] == CRITIQUE_PROMPT
    assert any(m["role"] == "assistant" and m["content"] == "reply-1" for m in second)

    # And the final answer must see the critique.
    third = provider.calls[2]
    assert any(m["role"] == "assistant" and m["content"] == "reply-2" for m in third)


def test_no_harness_prompt_leaks_the_answers():
    """A harness that named the mechanism would smuggle in what the brief withholds.

    This is the same integrity property as the brief's own test - and easier to
    violate here, because a 'helpful' checklist item is exactly where a hint goes.
    """
    for text in (CRITIQUE_PROMPT, CHECKLIST_PROMPT):
        lowered = text.lower()
        for leak in (
            "fibrinolysis",
            "fibrinolytic",
            "aprotinin",
            "tranexamic",
            "plasmin",
            "lysis",
            "dissolv",
            "n=3",
            "12-well",
            "fibrin",
        ):
            assert leak not in lowered, f"harness prompt leaks '{leak}'"


def test_the_checklist_demands_arithmetic_not_just_consideration():
    """The point is to test whether n=3 is an un-done calculation."""
    lowered = CHECKLIST_PROMPT.lower()
    assert "compute it" in lowered
    assert "arithmetic" in lowered
    # And it must license declining, or it pushes toward a plate regardless.
    assert "not answerable" in lowered


def test_the_critique_prompt_forbids_defending_the_design():
    # Whitespace-normalised: the prompt is hard-wrapped, so phrases straddle
    # newlines and a naive substring check tests the line breaks, not the text.
    flat = " ".join(CRITIQUE_PROMPT.lower().split())
    assert "do not defend it" in flat
    # It must not rewrite yet, or the critique collapses into a revision.
    assert "do not rewrite the design yet" in flat


def test_revise_does_not_add_a_second_critique(provider, monkeypatch):
    """After simulator feedback, self-review would confound two effects.

    The feedback already IS an external critique, and a stronger one. Stacking a
    self-review on top makes 'responded to consequences' and 'reviewed itself'
    indistinguishable.
    """
    import refute.harness as harness_mod

    seen = {}
    monkeypatch.setattr(
        harness_mod,
        "revise_design",
        lambda brief, prev, fb, spec: seen.update(fb=fb) or "revised",
    )
    out = SelfCritique().revise("brief", "prev", "the scaffold was gone")
    assert out == "revised"
    assert seen["fb"] == "the scaffold was gone"
    assert provider.calls == [], "revise must not run the critique loop"


def test_harnesses_carry_the_model_spec_through():
    spec = ModelSpec("openai", "gpt-5.5", "high")
    for cls in (SingleShot, SelfCritique, Checklist):
        h = cls(spec)
        assert h.spec is spec
        assert "gpt-5.5" in str(h)
        assert h.name in str(h)


def test_default_spec_is_the_benchmarked_model():
    assert SingleShot().spec == DEFAULT_AGENT


def test_describe_states_that_the_pair_is_the_unit():
    text = describe()
    assert "(model x harness) pair" in text
    # And that no harness gets the scorer - the Goodhart boundary.
    assert "may not consult the scorer" in text
    for name in HARNESSES:
        assert name in text


def test_recorded_runs_carry_the_harness():
    from refute.record import RecordedRun

    run = RecordedRun(agent="a", extractor="b", brief="c", harness="self-critique")
    assert RecordedRun.from_dict(run.to_dict()).harness == "self-critique"


def test_runs_recorded_before_harnesses_existed_default_to_single_shot():
    """Those runs WERE single-shot, so the default is a true statement."""
    from refute.record import SCHEMA_VERSION, RecordedRun

    legacy = {
        "schema_version": SCHEMA_VERSION,
        "agent": "openai:gpt-5.5:high",
        "extractor": "openai:gpt-5.4-mini:low",
        "brief": "b",
        "rounds": [],
    }
    assert RecordedRun.from_dict(legacy).harness == "single-shot"
