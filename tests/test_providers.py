"""Provider plumbing, tested without touching the network.

PLAN item 1: verify the code path offline so that when a live run fails, the
failure is attributable to the model rather than to argument marshalling. The
GPT-5 families reject `max_tokens` and the Claude families reject
`max_completion_tokens`, so getting that branch wrong is a 400 that would
otherwise only surface mid-benchmark.
"""

from __future__ import annotations

import pytest

from refute.providers import (
    DEFAULT_AGENT,
    DEFAULT_EXTRACTOR,
    ModelSpec,
    OpenAIProvider,
    ProviderError,
    Usage,
    _is_reasoning_model,
    _record,
    ledger_summary,
    reset_ledger,
    spec_from_string,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("openai:gpt-5.5@high", ModelSpec("openai", "gpt-5.5", "high")),
        ("openai:gpt-5.5", ModelSpec("openai", "gpt-5.5", "high")),
        ("gpt-5.5", ModelSpec("openai", "gpt-5.5", "high")),
        ("claude-opus-5", ModelSpec("anthropic", "claude-opus-5", "high")),
        ("anthropic:claude-opus-5@low", ModelSpec("anthropic", "claude-opus-5", "low")),
        ("o4-mini@medium", ModelSpec("openai", "o4-mini", "medium")),
    ],
)
def test_spec_parsing(text, expected):
    assert spec_from_string(text) == expected


def test_bare_claude_name_routes_to_anthropic():
    """The shorthand has to guess. Getting this wrong sends a Claude model name
    to OpenAI, which 404s with a confusing message."""
    assert spec_from_string("claude-opus-5").provider == "anthropic"
    assert spec_from_string("gpt-5.5").provider == "openai"


def test_unknown_provider_is_rejected_early():
    with pytest.raises(ProviderError, match="unknown provider"):
        spec_from_string("gemini:gemini-3-pro")


@pytest.mark.parametrize(
    "model,reasoning",
    [
        ("gpt-5.5", True),
        ("gpt-5.4-mini", True),
        ("o3", True),
        ("o4-mini", True),
        ("gpt-4o", False),
        ("gpt-4.1", False),
    ],
)
def test_reasoning_family_detection(model, reasoning):
    assert _is_reasoning_model(model) is reasoning


def test_reasoning_models_get_the_right_token_argument():
    """max_tokens vs max_completion_tokens is a 400, not a soft failure."""
    p = OpenAIProvider.__new__(OpenAIProvider)  # no client, no key needed

    reasoning = p._kwargs(ModelSpec("openai", "gpt-5.5", "high"), 16000)
    assert reasoning == {"max_completion_tokens": 16000, "reasoning_effort": "high"}

    legacy = p._kwargs(ModelSpec("openai", "gpt-4o", "high"), 16000)
    assert legacy == {"max_tokens": 16000}
    assert "reasoning_effort" not in legacy


def test_extractor_default_is_cheap_and_the_agent_default_is_not():
    """The extractor is infrastructure run on every design; the agent is the
    measurement. If these ever converge on the same effort, someone has
    forgotten which one is being benchmarked."""
    assert DEFAULT_EXTRACTOR.effort == "low"
    assert DEFAULT_AGENT.effort == "high"


def test_ledger_accumulates_per_model():
    """Cost has to be attributable per model, or a cross-model comparison
    cannot report what each arm actually cost to produce."""
    reset_ledger()
    a = ModelSpec("openai", "gpt-5.5", "high")
    b = ModelSpec("openai", "gpt-5.5", "low")
    _record(a, Usage(calls=1, input_tokens=100, output_tokens=50, reasoning_tokens=40))
    _record(a, Usage(calls=1, input_tokens=200, output_tokens=60, reasoning_tokens=10))
    _record(b, Usage(calls=1, input_tokens=10, output_tokens=5))

    summary = ledger_summary()
    assert "gpt-5.5@high" in summary and "gpt-5.5@low" in summary

    from refute.providers import LEDGER

    assert LEDGER[str(a)].calls == 2
    assert LEDGER[str(a)].input_tokens == 300
    assert LEDGER[str(a)].reasoning_tokens == 50
    # Different effort is a different arm, so it must not be merged.
    assert LEDGER[str(b)].calls == 1
    reset_ledger()


def test_empty_ledger_says_so_rather_than_printing_a_bare_header():
    reset_ledger()
    assert "no model calls" in ledger_summary()


def test_modelspec_is_hashable_and_prints_legibly():
    """Specs are dict keys in the cross-model results table and are printed
    into it, so both properties are load-bearing."""
    assert {DEFAULT_AGENT: 1}[ModelSpec("openai", "gpt-5.5", "high")] == 1
    assert str(DEFAULT_AGENT) == "openai:gpt-5.5@high"
