"""The conversation layer.

Modelled on Paperclip's chat and on the discipline that makes it trustworthy:
cite from what you actually read. Paperclip cites a line number; refute cites the
simulation. So the property under test throughout is that **every claim about a
design carries the computed evidence that produced it**, and that the model is
never asked for a judgement.

A chat interface is exactly where that boundary erodes, because letting the
assistant just answer feels natural. These tests are the boundary.
"""

from __future__ import annotations

import pytest

from refute.chat import INTENT_PATTERNS, Session, Turn
from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec

SIMS = 200


def _session(**kw) -> Session:
    s = Session(extractor=lambda _t: EXPERIMENT_4_AS_RUN, n_sims=SIMS, **kw)
    return s


# --- the boundary -----------------------------------------------------------

def test_the_model_is_only_ever_asked_to_extract():
    """The whole architecture in one test.

    The extractor is called exactly once, for the first prose message. Every
    follow-up - what to change, what if, why, how many - is computed.
    """
    calls = []

    def extractor(text):
        calls.append(text)
        return EXPERIMENT_4_AS_RUN

    s = Session(extractor=extractor, n_sims=SIMS)
    s.ask("four arms, three wells each, treat at day 5, endpoint day 10")
    assert len(calls) == 1

    for follow_up in (
        "what should I change?",
        "what if I add aprotinin?",
        "why did it fail?",
        "how many wells do I need?",
    ):
        s.ask(follow_up)
    assert len(calls) == 1, f"a follow-up called the model: {calls[1:]}"


def test_every_substantive_answer_carries_its_evidence():
    s = _session()
    s.ask("a design")
    for follow_up in ("what should I change?", "why?", "how many wells do I need?"):
        turn = s.ask(follow_up)
        assert turn.evidence, f"'{follow_up}' answered with no computed evidence"


def test_the_evidence_names_the_number_of_simulations():
    """A number without its provenance is not a citation."""
    s = _session()
    turn = s.ask("a design")
    assert any(str(SIMS) in e for e in turn.evidence)


# --- routing ----------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("what should I change?", "advise"),
        ("how do I fix this", "advise"),
        ("what if I add aprotinin", "whatif"),
        ("why did that happen", "why"),
        ("explain that", "why"),
        ("how many wells do I need", "scale"),
        ("what sample size", "scale"),
        ("four arms of three wells, day 10 endpoint", "design"),
    ],
)
def test_intent_routing_is_inspectable(text, expected):
    """Keyword routing rather than a model call: a wrong answer is a bug that
    can be read, not a mood."""
    assert Session.classify(text) == expected


def test_every_intent_has_a_handler():
    s = _session()
    s.ask("a design")
    for intent, _patterns in INTENT_PATTERNS:
        assert intent in {"advise", "whatif", "why", "scale"}


def test_a_follow_up_before_any_design_asks_for_one():
    s = _session()
    turn = s.ask("what should I change?")
    assert "Describe the experiment first" in turn.answer
    assert turn.evidence == []


# --- the honest answers -----------------------------------------------------

def test_it_reports_the_as_run_design_as_losing_units_first():
    """Experiment 4's problem is not power, it is that nothing survives."""
    s = _session()
    turn = s.ask("four arms, three wells each, treat day 5, endpoint day 10")
    assert "testable" in turn.answer.lower() or "losing units" in turn.answer.lower()
    assert turn.score.power == 0.0


def test_how_many_wells_refuses_when_survivors_are_biased():
    """The refusal is the answer, and it says why."""
    s = _session()
    s.ask("a design")
    turn = s.ask("how many wells do I need?")
    assert "cannot tell you" in turn.answer
    assert "largest effect" in turn.answer
    assert turn.evidence


def test_what_if_only_simulates_levers_it_can_actually_run():
    s = _session()
    s.ask("a design")
    turn = s.ask("what if I switch to a collagen gel?")
    assert "do not guess" in turn.answer
    assert turn.evidence == []


def test_what_if_aprotinin_returns_a_simulated_comparison():
    s = _session()
    s.ask("a design")
    turn = s.ask("what if I add aprotinin?")
    assert turn.score is not None
    assert any("power" in e for e in turn.evidence)
    assert any("wells lost" in e for e in turn.evidence)


def test_advice_marks_what_rests_on_an_assumption():
    s = _session()
    s.ask("a design")
    turn = s.ask("what should I change?")
    assert any("ASSUMED" in e for e in turn.evidence)


# --- failure modes ----------------------------------------------------------

def test_an_extraction_failure_is_not_reported_as_a_bad_design():
    """The confound the whole project holds the extractor constant to avoid."""
    def boom(_text):
        raise RuntimeError("provider exploded")

    s = Session(extractor=boom, n_sims=SIMS)
    turn = s.ask("some prose")
    assert "parsing failure on our side" in turn.answer
    assert "not a judgement" in turn.answer
    assert turn.score is None


def test_an_out_of_scope_design_is_a_limit_of_the_twin_not_a_verdict():
    oos = EXPERIMENT_4_AS_RUN.model_copy(
        update={"out_of_twin_scope": ["collagen I matrix"]}
    )
    s = Session(extractor=lambda _t: oos, n_sims=SIMS)
    turn = s.ask("a collagen design")
    assert "limit of the simulator" in turn.answer
    assert "collagen I matrix" in turn.answer
    # It must point at what still works rather than dead-ending.
    assert "tier0" in turn.answer


def test_a_declined_design_is_not_scored():
    declined = DesignSpec(
        conditions=[], replicates_per_condition=0, imaging_times_h=[1.0, 72.0],
        treatment_time_h=1.0, endpoint_time_h=72.0, antifibrinolytic=False,
        normalise_to_own_baseline=True, locked_imaging_protocol=True,
    )
    s = Session(extractor=lambda _t: declined, n_sims=SIMS)
    turn = s.ask("no plate should be cast")
    assert "declines to run" in turn.answer
    assert "baselines" in turn.answer


def test_without_an_extractor_it_says_so_rather_than_guessing():
    s = Session(extractor=None, n_sims=SIMS)
    turn = s.ask("four arms of three")
    assert "No extractor is configured" in turn.answer


# --- shape ------------------------------------------------------------------

def test_render_puts_the_evidence_under_the_answer():
    turn = Turn(intent="x", answer="A claim.", evidence=["a number"])
    text = turn.render()
    assert text.index("A claim.") < text.index("computed from")
    assert "a number" in text


def test_history_accumulates():
    s = _session()
    s.ask("a design")
    s.ask("why?")
    assert len(s.history) == 2
    assert [t.intent for t in s.history] == ["design", "why"]
