"""Model access, behind one interface, so the agent under test can be swapped.

Why this exists
---------------
The thing being benchmarked is *an agent designing an experiment*. If that agent
can only ever be one model, the result is an anecdote about that model. With two
families behind one interface the same twin scores both, and the output becomes
a comparison rather than a demonstration.

The asymmetry that matters
--------------------------
There are two model calls in the loop and they are NOT interchangeable:

  propose / revise   the SUBJECT. Varies across runs. This is the measurement.
  extract            INFRASTRUCTURE. Must be held CONSTANT across every run.

If the extractor varies with the proposer, a difference in score confounds
design quality with extraction fidelity and you cannot tell which one moved.
`ModelSpec` therefore appears twice in the call signatures on purpose - see
`agent.propose_design` and `agent.extract_design`.

Nothing here decides whether a design is good. These are transport only.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from pydantic import BaseModel

Effort = str  # "low" | "medium" | "high"


@dataclass(frozen=True)
class ModelSpec:
    """Which model, at what reasoning effort. Recorded with every result."""

    provider: str  # "openai" | "anthropic"
    model: str
    effort: Effort = "high"

    def __str__(self) -> str:  # appears in result tables
        return f"{self.provider}:{self.model}@{self.effort}"


# Defaults. The agent default is deliberately a strong general model; the
# extractor default is fixed and should not be varied casually - see module docs.
#
# The extractor sits on a DIFFERENT model from the agent on purpose, and it is
# not only a cost decision. Rate limits are per-model pools: gpt-5.5 allows
# 10k tokens/min on this account while gpt-5.4-mini allows 100k. Sharing one
# model between proposal and extraction means the proposal exhausts the minute
# and the extraction 429s immediately - which is exactly what happened on the
# first working run. Separate models, separate pools.
#
# CAVEAT: a smaller extractor is only acceptable if it parses faithfully.
# That is not yet established - it is what the adversarial extraction set
# (PLAN item 4) exists to test. Until that passes, treat extraction fidelity
# as the leading suspect for any surprising score.
DEFAULT_AGENT = ModelSpec("openai", "gpt-5.5", "high")
DEFAULT_EXTRACTOR = ModelSpec("openai", "gpt-5.4-mini", "low")

# Observed 2026-08-04. Not authoritative - the API headers are - but enough to
# explain why a benchmark run is slow rather than broken.
KNOWN_TPM = {
    "gpt-5.5": 10_000,
    "gpt-5.4": 10_000,
    "gpt-5.2": 10_000,
    "gpt-5.4-mini": 100_000,
    "o4-mini": 100_000,
    "gpt-5.4-nano": 60_000,
    "gpt-5-nano": 40_000,
}

ANTHROPIC_AGENT = ModelSpec("anthropic", "claude-opus-5", "high")

# OpenAI reasoning families take `reasoning_effort` and `max_completion_tokens`
# rather than `max_tokens`; sending the wrong one is a 400.
_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _is_reasoning_model(model: str) -> bool:
    return model.startswith(_REASONING_PREFIXES)


class ProviderError(RuntimeError):
    """Transport failed, or the model declined. Never a scoring outcome."""


@dataclass
class Usage:
    """Tokens spent. Reasoning tokens are the surprising term.

    On the first live run, gpt-5.5 at high effort consumed a 16k budget
    entirely on reasoning and returned no visible text at all - reported as
    `finish_reason=length` with empty content, which reads like a refusal
    unless you are counting. Hence this ledger: the benchmark reports what it
    cost rather than assuming.
    """

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.calls += other.calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.reasoning_tokens += other.reasoning_tokens


_RETRY_HINT = re.compile(r"try again in ([\d.]+)s")


def _suggested_wait(message: str) -> float | None:
    """The 429 body states how long to wait. Prefer it over guessing."""
    m = _RETRY_HINT.search(message)
    return float(m.group(1)) if m else None


def with_retry(fn: Callable[[], Any], attempts: int = 6, verbose: bool = True) -> Any:
    """Retry on rate limits, honouring the wait the API asks for.

    A 10k TPM ceiling means one high-effort proposal can consume an entire
    minute's budget, so 429s here are the normal operating regime rather than
    an error condition - the benchmark is throughput-bound, not broken.
    """
    try:
        from openai import RateLimitError
    except ImportError:  # pragma: no cover
        return fn()

    for attempt in range(attempts):
        try:
            return fn()
        except RateLimitError as exc:
            if attempt == attempts - 1:
                raise ProviderError(
                    f"rate limited after {attempts} attempts: {exc}"
                ) from exc
            wait = _suggested_wait(str(exc)) or min(60.0, 5.0 * 2**attempt)
            if verbose:
                print(f"  [rate limited, waiting {wait + 1:.0f}s]", flush=True)
            time.sleep(wait + 1.0)
    raise ProviderError("unreachable")  # pragma: no cover


LEDGER: dict[str, Usage] = {}


def _record(spec: ModelSpec, usage: Usage) -> None:
    LEDGER.setdefault(str(spec), Usage()).add(usage)


def reset_ledger() -> None:
    LEDGER.clear()


def ledger_summary() -> str:
    if not LEDGER:
        return "no model calls recorded"
    rows = [f"{'model':<28} {'calls':>5} {'in':>9} {'out':>9} {'reasoning':>10}"]
    for name, u in LEDGER.items():
        rows.append(
            f"{name:<28} {u.calls:>5} {u.input_tokens:>9,} "
            f"{u.output_tokens:>9,} {u.reasoning_tokens:>10,}"
        )
    return "\n".join(rows)


class Provider(Protocol):
    def complete(
        self, messages: list[dict[str, str]], spec: ModelSpec, max_tokens: int
    ) -> str: ...

    def parse(
        self,
        messages: list[dict[str, str]],
        spec: ModelSpec,
        max_tokens: int,
        output_format: type[BaseModel],
    ) -> BaseModel: ...


class OpenAIProvider:
    """GPT-5.x / o-series via the chat completions API."""

    name = "openai"

    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("pip install openai") from exc
        if not os.environ.get("OPENAI_API_KEY"):
            raise ProviderError("OPENAI_API_KEY is not set")
        self._client = OpenAI()

    def _kwargs(self, spec: ModelSpec, max_tokens: int) -> dict[str, Any]:
        if _is_reasoning_model(spec.model):
            # Reasoning tokens are charged against this budget, so it must be
            # generous - a design that runs out mid-thought returns empty text,
            # which would otherwise look like a refusal.
            return {
                "max_completion_tokens": max_tokens,
                "reasoning_effort": spec.effort,
            }
        return {"max_tokens": max_tokens}

    @staticmethod
    def _usage(r: Any) -> Usage:
        u = getattr(r, "usage", None)
        if u is None:
            return Usage(calls=1)
        details = getattr(u, "completion_tokens_details", None)
        return Usage(
            calls=1,
            input_tokens=getattr(u, "prompt_tokens", 0) or 0,
            output_tokens=getattr(u, "completion_tokens", 0) or 0,
            reasoning_tokens=getattr(details, "reasoning_tokens", 0) or 0,
        )

    def complete(
        self, messages: list[dict[str, str]], spec: ModelSpec, max_tokens: int
    ) -> str:
        r = with_retry(
            lambda: self._client.chat.completions.create(
                model=spec.model, messages=messages, **self._kwargs(spec, max_tokens)
            )
        )
        usage = self._usage(r)
        _record(spec, usage)
        choice = r.choices[0]
        if getattr(choice.message, "refusal", None):
            raise ProviderError(f"model declined: {choice.message.refusal}")
        text = choice.message.content or ""
        if not text.strip():
            raise ProviderError(
                f"empty response (finish_reason={choice.finish_reason}); "
                f"{usage.reasoning_tokens:,} of {max_tokens:,} tokens went to "
                "reasoning before any visible text. Raise the budget."
            )
        return text

    def parse(
        self,
        messages: list[dict[str, str]],
        spec: ModelSpec,
        max_tokens: int,
        output_format: type[BaseModel],
    ) -> BaseModel:
        r = with_retry(
            lambda: self._client.chat.completions.parse(
                model=spec.model,
                messages=messages,
                response_format=output_format,
                **self._kwargs(spec, max_tokens),
            )
        )
        usage = self._usage(r)
        _record(spec, usage)
        choice = r.choices[0]
        if getattr(choice.message, "refusal", None):
            raise ProviderError(f"model declined: {choice.message.refusal}")
        parsed = choice.message.parsed
        if parsed is None:
            raise ProviderError(
                f"structured output returned nothing "
                f"(finish_reason={choice.finish_reason}, "
                f"{usage.reasoning_tokens:,} reasoning tokens)"
            )
        return parsed


class AnthropicProvider:
    """Claude via the messages API."""

    name = "anthropic"

    @staticmethod
    def _usage(r: Any) -> Usage:
        u = getattr(r, "usage", None)
        if u is None:
            return Usage(calls=1)
        return Usage(
            calls=1,
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
        )

    def __init__(self) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("pip install anthropic") from exc
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic()

    def complete(
        self, messages: list[dict[str, str]], spec: ModelSpec, max_tokens: int
    ) -> str:
        r = self._client.messages.create(
            model=spec.model,
            max_tokens=max_tokens,
            output_config={"effort": spec.effort},
            messages=messages,
        )
        _record(spec, self._usage(r))
        if r.stop_reason == "refusal":
            raise ProviderError(f"model declined: {r.stop_details}")
        text = "".join(b.text for b in r.content if b.type == "text")
        if not text.strip():
            raise ProviderError(f"empty response (stop_reason={r.stop_reason})")
        return text

    def parse(
        self,
        messages: list[dict[str, str]],
        spec: ModelSpec,
        max_tokens: int,
        output_format: type[BaseModel],
    ) -> BaseModel:
        r = self._client.messages.parse(
            model=spec.model,
            max_tokens=max_tokens,
            output_config={"effort": spec.effort},
            messages=messages,
            output_format=output_format,
        )
        parsed = r.parsed_output
        if parsed is None:
            raise ProviderError("structured output returned nothing")
        return parsed


_BUILDERS = {"openai": OpenAIProvider, "anthropic": AnthropicProvider}
_CACHE: dict[str, Provider] = {}


def get_provider(name: str) -> Provider:
    """Build (and memoise) a provider. Raises ProviderError if unusable."""
    if name not in _BUILDERS:
        raise ProviderError(
            f"unknown provider '{name}'. Known: {', '.join(sorted(_BUILDERS))}"
        )
    if name not in _CACHE:
        _CACHE[name] = _BUILDERS[name]()
    return _CACHE[name]


def available() -> dict[str, str]:
    """Which providers are usable right now, and why not if they aren't.

    Used by the CLI so a missing key is reported as configuration rather than
    surfacing as a stack trace halfway through a benchmark run.
    """
    status = {}
    for name, builder in _BUILDERS.items():
        try:
            builder()
            status[name] = "ready"
        except ProviderError as exc:
            status[name] = str(exc)
    return status


def spec_from_string(text: str, default_effort: Effort = "high") -> ModelSpec:
    """Parse 'openai:gpt-5.5@high' / 'openai:gpt-5.5' / 'gpt-5.5'.

    A bare model name is resolved by prefix, so the common case stays short.
    """
    effort = default_effort
    if "@" in text:
        text, effort = text.rsplit("@", 1)
    if ":" in text:
        provider, model = text.split(":", 1)
    else:
        model = text
        provider = "anthropic" if model.startswith("claude") else "openai"
    if provider not in _BUILDERS:
        raise ProviderError(
            f"unknown provider '{provider}' in '{text}'. "
            f"Known: {', '.join(sorted(_BUILDERS))}"
        )
    return ModelSpec(provider, model, effort)
