"""What happened, in what order, and what caused what.

SPEC §3 locks traceability for the whole system - "every load-bearing action
traced, with causal links, non-negotiable" - and §8.4 puts it in the never-cut
list, because "cutting the trace saves an hour tonight and costs three
tomorrow, since every subsequent bug becomes a guess."

The argument is §6.1, and it transfers to this layer exactly. A REFUSE printed
by the pipeline could be a requirement set that was never filled, a resolver
that never searched, a gate rule firing on coverage, a tier-0 input that
arrived with no value, or a question that genuinely cannot be answered at this
scale. **From the printed route those five are indistinguishable.** They all
read as "it would not answer". Only a walk backwards - to the requirement set
that was built, the resolutions that came back, the route considered and
rejected - tells them apart, and that walk is the difference between fixing the
system and guessing at it.

THE SHAPE (§6.2)
----------------
    runs/<timestamp>/
      trace.jsonl        ordered spine, one line per action
      artifacts/         the big things, named by event id

**`trace.jsonl` stays small and greppable. Anything large goes to `artifacts/`
and is referenced by path. Nothing is truncated.** That is the one property
that makes the file usable by eye, and it is the easy one to lose: the first
time somebody inlines a narrative or a resolution dump, the spine stops being
scannable and nobody notices, because it still parses.

So the rule is enforced rather than documented. Every value that reaches the
spine - a note, a field, an exception message - goes through one gate: scalars
and short strings are inlined, everything else is written to `artifacts/` and
replaced by `see artifacts/ev_00N.<name>.<ext>`. Nothing is cut short, and the
line stays a line.

A DISABLED TRACE IS FREE
------------------------
Default off, and off means a singleton whose `step()` allocates nothing and
whose `artifact()` and `note()` do nothing. That is what lets the wiring be
unconditional: `pipeline.run` never asks whether tracing is on, so there is no
branch to get wrong and no code path that only executes under tracing. An
artifact payload may be given as a zero-argument callable, which is never
called when the trace is off - so building the payload costs nothing either.

THE ERROR PATH WRITES ARTIFACTS
-------------------------------
§8.3 lists "artifact writes on the error path" among the connectors that are
easy to forget, and it is the path you most need traced: an exception is the
one case where nobody can reconstruct what happened from the output, because
there is no output. So a step that raises emits an `error` event carrying the
full traceback as an artifact, and re-raises unchanged.

It emits `error` rather than its own kind on purpose. The stage did not happen;
writing a `resolved` line for a resolve that blew up would put an action in the
spine that never completed, and the spine is read as a list of things that did.
`failed_kind` records which stage it was.

TIMESTAMPS ARE INJECTED
-----------------------
`clock` is a parameter. A module that reads the wall clock cannot be tested
deterministically, which is the same reason `record.RecordedRun` takes its
`recorded_at` from the caller.
"""

from __future__ import annotations

import json
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Protocol

TRACE_FILE = "trace.jsonl"
ARTIFACTS_DIR = "artifacts"

# The event vocabulary, from §6.2, narrowed to the actions this layer performs.
# Fixed rather than open: a viewer groups by kind, and a typo'd kind is an event
# that silently disappears from every view built on the spine. An unknown kind
# therefore raises at the call site, where it is one character to fix, instead of
# being discovered as a hole in a tree three hours later.
KINDS: frozenset[str] = frozenset(
    {
        "requirements_built",
        "resolved",
        "routed",
        "simulated",
        "advised",
        "outcome",
        "error",
    }
)

# The keys §6.2 fixes. Extra fields are welcome beside them - `route`, `tier`,
# `n_sims` - but not on top of them, so a caller cannot quietly redefine `id`.
SPINE_FIELDS: frozenset[str] = frozenset(
    {"id", "parent_id", "kind", "t", "ms", "summary", "artifacts", "inputs"}
)

# Where "small enough to scan by eye" stops. One long sentence - the gate's
# `why` is the live case - stays in the spine, because that is exactly what you
# want to see while scrolling. A narrative, a resolution dump or a traceback
# does not, and goes to `artifacts/` whole.
MAX_INLINE_CHARS = 400

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(when: datetime) -> str:
    """§6.2's timestamp format: `2026-08-15T21:41:03.221Z`.

    A naive datetime is read as UTC rather than as local time. A test clock is
    almost always naive, and interpreting it locally would make the recorded
    timestamp depend on the machine the suite runs on.
    """
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    when = when.astimezone(timezone.utc)
    return f"{when.strftime('%Y-%m-%dT%H:%M:%S')}.{when.microsecond // 1000:03d}Z"


class Step:
    """One event, while it is still open.

    Handed to the body of `with trace.step(...)`. The id exists from the moment
    the step begins, which is what lets an artifact be named after the event
    that produced it before that event has finished.
    """

    def __init__(
        self,
        trace: "RunTrace",
        event_id: str,
        kind: str,
        parent_id: str | None,
        inputs: tuple[str, ...],
        started: datetime,
        fields: dict[str, Any],
    ) -> None:
        self.id = event_id
        self.kind = kind
        self.parent_id = parent_id
        self.inputs = inputs
        self.started = started
        self._trace = trace
        self._fields = fields
        self._notes: list[str] = []
        self._artifacts: dict[str, str] = {}

    # -- the two verbs from §6.3 ---------------------------------------------

    def artifact(self, name: str, payload: Any) -> str:
        """Write something large, and reference it from the spine by path.

        `payload` may be a str, bytes, anything JSON-serialisable, or a
        zero-argument callable returning one of those. The callable form is
        what makes a disabled trace free: the payload is never built when
        nothing is going to be written.

        An unserialisable payload is stringified rather than raised on. A trace
        that crashes the run it is recording is worse than a trace that records
        a repr, and the repr is still the walk backwards.
        """
        if callable(payload):
            payload = payload()
        rel = self._trace._write_artifact(self.id, name, payload)
        self._artifacts[name] = rel
        return rel

    def note(self, text: str) -> None:
        """Add a phrase to this event's summary.

        Notes join with '; '. A summary that outgrows `MAX_INLINE_CHARS` is
        moved to an artifact whole and replaced by a pointer - not shortened.
        Truncation is the failure mode §6.2 rules out explicitly, and a summary
        cut off mid-clause is worse than a summary that says where to look.
        """
        self._notes.append(text)


class _NullStep:
    """The disabled step. Every method is a no-op that allocates nothing."""

    __slots__ = ()

    id: str | None = None

    def artifact(self, name: str, payload: Any = None) -> None:
        return None

    def note(self, text: str) -> None:
        return None


class _NullContext:
    """A reusable context manager, so a disabled step allocates nothing at all.

    `@contextmanager` would be correct and would allocate a generator and a
    wrapper per call. This is the same thing for free, which is the point: "off"
    has to cost nothing, or callers will start branching on it and the wiring
    stops being unconditional.
    """

    __slots__ = ()

    def __enter__(self) -> _NullStep:
        return _NULL_STEP

    def __exit__(self, *exc: object) -> bool:
        return False


_NULL_STEP = _NullStep()
_NULL_CONTEXT = _NullContext()


class Trace(Protocol):
    """What a caller may rely on, whether the trace is on or off."""

    enabled: bool

    @property
    def last(self) -> str | None:
        """The id of the most recently finished event, or None."""

    def step(
        self,
        kind: str,
        *,
        parent: "Step | str | None" = None,
        inputs: Iterable["Step | str"] = (),
        **fields: Any,
    ) -> Any: ...


class NullTrace:
    """A trace that records nothing, and costs nothing to call.

    The default. It exists so that `pipeline.run` can be wired once, with no
    `if trace:` anywhere, and so that turning the trace off cannot change what
    the pipeline does - only what it writes down.
    """

    enabled = False
    dir: Path | None = None

    @property
    def last(self) -> str | None:
        return None

    def step(
        self,
        kind: str,
        *,
        parent: Step | str | None = None,
        inputs: Iterable[Step | str] = (),
        **fields: Any,
    ) -> _NullContext:
        return _NULL_CONTEXT


_DISABLED = NullTrace()


def disabled() -> NullTrace:
    """The off switch, as an object. One instance, shared."""
    return _DISABLED


class RunTrace:
    """One run directory: `trace.jsonl` beside `artifacts/`.

    Each event is appended and flushed as it finishes rather than buffered to
    the end, so a run that dies mid-way still leaves a readable spine. That is
    not a nicety - the run that dies is the one you need the trace for.
    """

    enabled = True

    def __init__(self, directory: str | Path, *, clock: Clock = _utc_now) -> None:
        self.dir = Path(directory)
        self.clock = clock
        self.path = self.dir / TRACE_FILE
        self.artifacts_dir = self.dir / ARTIFACTS_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._n = 0
        self._last: str | None = None
        self._ids: set[str] = set()

    @property
    def last(self) -> str | None:
        """The most recently finished event.

        Meaningful because this layer's spine is a chain: requirements, then
        resolve, then route, then score, then advise, then the outcome. For
        anything that nests, name the parent explicitly - `last` would give the
        sibling that just closed rather than the step that encloses it.
        """
        return self._last

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(self._ids)

    # -- the context manager from §6.3 ---------------------------------------

    @contextmanager
    def step(
        self,
        kind: str,
        *,
        parent: Step | str | None = None,
        inputs: Iterable[Step | str] = (),
        **fields: Any,
    ) -> Iterator[Step]:
        """Run a stage and record it as one event.

        On success the event carries the stage's kind, its duration, its
        summary and its artifacts. On an exception it carries kind `error`, the
        traceback as an artifact, and whatever artifacts the stage had already
        written - then the exception is re-raised untouched. A trace that
        swallowed an exception would be a trace that changed the program.
        """
        if kind not in KINDS:
            raise ValueError(
                f"unknown trace kind {kind!r}. The vocabulary is fixed by SPEC "
                f"§6.2 so that a viewer can group by it: {sorted(KINDS)}"
            )
        clash = SPINE_FIELDS & set(fields)
        if clash:
            raise ValueError(
                f"{sorted(clash)} are the spine's own fields and cannot be "
                "reused for extra detail"
            )

        self._n += 1
        step = Step(
            trace=self,
            event_id=f"ev_{self._n:03d}",
            kind=kind,
            parent_id=_event_id(parent),
            inputs=tuple(i for i in (_event_id(x) for x in inputs) if i),
            started=self.clock(),
            fields=fields,
        )
        try:
            yield step
        except BaseException as exc:
            step.artifact("traceback", "".join(traceback.format_exception(exc)))
            self._emit(
                step,
                kind="error",
                summary=self._inline(
                    step, "message", f"{type(exc).__name__}: {exc}"
                ),
                extra={"failed_kind": kind, **step._fields},
            )
            raise
        self._emit(
            step,
            kind=kind,
            summary=self._inline(step, "summary", "; ".join(step._notes)),
            extra=step._fields,
        )

    # -- writing --------------------------------------------------------------

    def _emit(
        self, step: Step, *, kind: str, summary: str, extra: dict[str, Any]
    ) -> None:
        """Append one line. Field order follows §6.2's example."""
        event: dict[str, Any] = {
            "id": step.id,
            "parent_id": step.parent_id,
            "kind": kind,
            # The start, not the finish: with `ms` beside it the pair says when
            # the action began and how long it took, which is what you need to
            # line two stages up against each other.
            "t": _stamp(step.started),
            "ms": int((self.clock() - step.started).total_seconds() * 1000),
            "summary": summary,
            "artifacts": dict(step._artifacts),
            "inputs": list(step.inputs),
        }
        for name, value in extra.items():
            event[name] = self._inline(step, name, value)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, default=str) + "\n")
        self._last = step.id
        self._ids.add(step.id)

    def _inline(self, step: Step, name: str, value: Any) -> Any:
        """The one gate every spine value passes through.

        Scalars and short strings stay. Everything else - a long string, a
        list, a mapping, an object - is written whole to `artifacts/` and
        replaced by a path. This is the enforcement of §6.2's "nothing large
        inline, nothing truncated", and it is a single function so that there
        is exactly one place the rule can be true.
        """
        if isinstance(value, Enum):
            value = value.value
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str) and len(value) <= MAX_INLINE_CHARS:
            return value
        return f"see {step.artifact(name, value)}"

    def _write_artifact(self, event_id: str, name: str, payload: Any) -> str:
        """Write one artifact and return its path relative to the run directory.

        Relative, because the whole run directory is the unit that gets copied,
        zipped or served, and an absolute path would break the moment it moved.
        """
        if isinstance(payload, bytes):
            suffix, data = "bin", payload
        elif isinstance(payload, str):
            suffix, data = "txt", payload.encode("utf-8")
        else:
            suffix = "json"
            data = (json.dumps(payload, indent=2, default=str) + "\n").encode("utf-8")
        rel = f"{ARTIFACTS_DIR}/{event_id}.{name}.{suffix}"
        (self.dir / rel).write_bytes(data)
        return rel


def _event_id(ref: Step | str | None) -> str | None:
    if ref is None:
        return None
    if isinstance(ref, str):
        return ref or None
    return getattr(ref, "id", None)


def open_run(
    root: str | Path = "runs", *, clock: Clock | None = None, name: str | None = None
) -> RunTrace:
    """Start a run directory under `root`, named for the time it started.

    A suffix is added rather than an existing directory reused. Two runs a
    second apart - or two runs under a frozen test clock - must not interleave
    their events in one spine, because the causal links would then be between
    events from different runs and every walk backwards would be wrong.
    """
    clock = clock or _utc_now
    label = name or clock().strftime("%Y-%m-%dT%H%M%S")
    base = Path(root)
    directory = base / label
    n = 2
    while directory.exists():
        directory = base / f"{label}-{n}"
        n += 1
    return RunTrace(directory, clock=clock)


# --- reading ------------------------------------------------------------------
# The spine is JSON lines precisely so that it can be read with `grep`, but the
# walk in §6.1 is the operation the whole module exists for, so it is here as
# code rather than left to every caller to rewrite.


def read_events(run_dir: str | Path) -> list[dict]:
    """Every event in one run, in the order it was written.

    Accepts the run directory or the `trace.jsonl` itself, because both are
    what somebody has to hand.
    """
    path = Path(run_dir)
    if path.is_dir():
        path = path / TRACE_FILE
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def walk_back(events: Iterable[dict], event_id: str) -> list[dict]:
    """The causal chain from one event to the root, that event first.

    This is §6.1's walk. Given the outcome you get the advice that produced it,
    the score under that, the route under that, and the requirement set at the
    bottom - which is how a REFUSE is told apart from an unfinished search
    rather than guessed at.

    A cycle raises. The spine is written by a context manager that can only
    name an already-open ancestor, so a cycle means the file has been edited or
    two runs have been concatenated, and silently returning a partial chain
    would hide both.
    """
    by_id = {e["id"]: e for e in events}
    chain: list[dict] = []
    seen: set[str] = set()
    current: str | None = event_id
    while current is not None:
        if current in seen:
            raise ValueError(f"trace has a cycle through {current!r}")
        seen.add(current)
        event = by_id.get(current)
        if event is None:
            raise KeyError(f"{current!r} is referenced but not in this trace")
        chain.append(event)
        current = event.get("parent_id")
    return chain


__all__ = [
    "ARTIFACTS_DIR",
    "KINDS",
    "MAX_INLINE_CHARS",
    "NullTrace",
    "RunTrace",
    "SPINE_FIELDS",
    "TRACE_FILE",
    "Step",
    "Trace",
    "disabled",
    "open_run",
    "read_events",
    "walk_back",
]
