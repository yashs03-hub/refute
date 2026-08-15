"""The benchmark as an environment, for harnesses that expect one.

`refute` is already an environment internally - the twin is the dynamics, a
`DesignSpec` is an action, and `score_design` is the reward. This module is the
interface that makes that explicit, so an agent framework can drive the
benchmark without importing the CLI or knowing anything about fibrin.

    env = RefuteEnv()
    obs = env.reset()                      # the brief
    obs, reward, done, info = env.step(design_text_or_spec)

The tuple unpacking is the widely-understood convention rather than any
specific framework's API; `StepResult` is a dataclass that also unpacks, so
adapting it to a particular harness is a field rename, not a rewrite.

Two things here are deliberate and worth reading before using it.

**The reward is `power`, one number, and the rest of the score is in `info`.**
Not a weighted composite. A composite would bury a scientific judgement -
how much a lost baseline is worth against a dissolved scaffold - inside a
constant that nothing in Experiment 4 constrains. Callers who want a different
objective can build it from `info["design_score"]`, where every component is
reported separately.

**No model is called unless the action is prose.** Passing a `DesignSpec`
scores it with no network and no credential: `step` only reaches for the
extractor when handed text, which is the one place a key is required. That
keeps the pure-simulation path - the part this project can actually vouch for -
free of any dependency on a provider being up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from .calibration import DEFAULT_PARAMS, TwinParams
from .design import DesignSpec, OutOfTwinScopeError
from .score import DesignScore, feedback_for_agent, score_design

# The brief lives in `agent.py` next to the model calls it is sent with, but it
# is pre-registration text and depends on nothing - importing it costs nothing,
# because `providers` only demands a credential when a provider is constructed.
from .agent import EXPERIMENT_4_BRIEF

# An episode ends early once the design is good enough that further revision is
# not the interesting behaviour. 0.8 is the conventional power target and the
# same threshold `score.py` uses to derive `replicates_needed`, so a run that
# terminates here has met the standard the scorer is built around.
DEFAULT_TARGET_POWER = 0.8

# Revision rounds per episode. `cmd_run` does exactly one revision; three
# leaves room for an agent that needs more than one look without letting a
# loop run indefinitely against a paid API.
DEFAULT_MAX_ROUNDS = 3


@dataclass
class StepResult:
    """One environment transition.

    Unpacks as `(observation, reward, done, info)` for harnesses that expect a
    tuple, while keeping named access for everything else.
    """

    observation: str | None
    reward: float
    done: bool
    info: dict[str, Any] = field(default_factory=dict)

    def __iter__(self) -> Iterator[Any]:
        return iter((self.observation, self.reward, self.done, self.info))


class EpisodeError(RuntimeError):
    """Raised when the environment is driven out of order."""


class RefuteEnv:
    """Experiment 4 as a scored environment.

    Observation : the brief (on reset), then the simulator's consequence report
    Action      : a design, as prose or as an extracted `DesignSpec`
    Reward      : `DesignScore.power` - P(recover the injected effect)
    Termination : power >= `target_power`, or `max_rounds` actions taken
    """

    def __init__(
        self,
        brief: str = EXPERIMENT_4_BRIEF,
        params: TwinParams = DEFAULT_PARAMS,
        n_sims: int = 400,
        seed: int | None = 0,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        target_power: float = DEFAULT_TARGET_POWER,
        extractor: Any = None,
    ):
        self.brief = brief
        self.params = params
        self.n_sims = n_sims
        self.seed = seed
        self.max_rounds = max_rounds
        self.target_power = target_power
        # A `ModelSpec`, or None for the module default. Typed loosely so that
        # constructing an env never imports `providers`, which would demand a
        # credential from callers who only ever pass a DesignSpec.
        self.extractor = extractor

        self.round = 0
        self.done = True  # nothing may be stepped before reset()
        self.history: list[dict[str, Any]] = []

    # -- lifecycle ---------------------------------------------------------

    def reset(self) -> str:
        """Start an episode. Returns the brief the agent designs against."""
        self.round = 0
        self.done = False
        self.history = []
        return self.brief

    def step(self, action: str | DesignSpec) -> StepResult:
        """Score one design. `action` is free text or an extracted spec."""
        if self.done:
            raise EpisodeError(
                "step() called on a finished episode; call reset() first"
            )

        spec, extraction_error = self._to_spec(action)
        self.round += 1

        if spec is None:
            # Extraction failed. This is a harness fault, not a design fault,
            # so it must not be reported as a zero-power design - that would
            # record a parsing failure as a scientific one, the exact
            # confound `agent.py` keeps the extractor constant to avoid.
            self.done = True
            return self._result(
                observation=None,
                reward=0.0,
                info={
                    "round": self.round,
                    "error": "extraction_failed",
                    "detail": extraction_error,
                    "scored": False,
                },
            )

        try:
            score = score_design(
                spec, params=self.params, n_sims=self.n_sims, seed=self.seed
            )
        except OutOfTwinScopeError as exc:
            # The library raises, which is right for a caller expecting a
            # number. An episode must not die on it: the design may be fine and
            # the twin simply cannot speak to it, so this ends the episode as
            # unscored rather than propagating out of `step`.
            self.done = True
            return self._result(
                observation=None,
                reward=0.0,
                info={
                    "round": self.round,
                    "scored": False,
                    "error": "out_of_twin_scope",
                    "out_of_scope": list(exc.reasons),
                    "detail": str(exc),
                },
            )

        self.done = self.round >= self.max_rounds or score.power >= self.target_power

        info: dict[str, Any] = {
            "round": self.round,
            "scored": True,
            "design_score": score,
            "extracted": spec,
            "power": score.power,
            "testable_rate": score.testable_rate,
            "mean_lysed_fraction": score.mean_lysed_fraction,
            "infeasible_as_scoped": score.infeasible_as_scoped,
            "over_plate_capacity": score.over_plate_capacity,
            "diagnoses": list(score.diagnoses),
            "verdict_sensitive_to_assumption": score.verdict_sensitive_to_assumption,
            # A declined design carries reward 0.0 like a failed one, because
            # there is no defensible number to give it: what a correct refusal is
            # worth against a 9% plate is a research question, not a coding one.
            # So it is FLAGGED rather than scored, and a caller optimising on
            # reward alone will penalise correct refusals. Read this key.
            "declined": score.declined,
            "terminated_reason": self._reason(score),
        }
        self.history.append(info)

        # The consequence report is the next observation - the same text the
        # CLI feeds a revision turn. Withheld once the episode is over so a
        # harness cannot accidentally train on feedback it may not act upon.
        observation = None if self.done else feedback_for_agent(score)
        return self._result(observation=observation, reward=score.power, info=info)

    # -- internals ---------------------------------------------------------

    def _to_spec(self, action: str | DesignSpec) -> tuple[DesignSpec | None, str | None]:
        """Coerce an action to a spec. Prose costs a model call; a spec is free."""
        if isinstance(action, DesignSpec):
            return action, None
        if not isinstance(action, str):
            raise TypeError(
                f"action must be a DesignSpec or prose, got {type(action).__name__}"
            )
        if not action.strip():
            return None, "empty design text"
        # Imported here, not at module scope: this is the only path that needs
        # a provider credential, and constructing the env must not require one.
        from .agent import extract_design
        from .providers import DEFAULT_EXTRACTOR

        try:
            spec = extract_design(action, extractor=self.extractor or DEFAULT_EXTRACTOR)
        except Exception as exc:  # provider error, refusal, schema mismatch
            return None, f"{type(exc).__name__}: {exc}"
        return spec, None

    def _reason(self, score: DesignScore) -> str | None:
        if not self.done:
            return None
        if score.power >= self.target_power:
            return "target_power_reached"
        return "max_rounds"

    def _result(
        self, observation: str | None, reward: float, info: dict[str, Any]
    ) -> StepResult:
        return StepResult(
            observation=observation, reward=reward, done=self.done, info=info
        )

    # -- reporting ---------------------------------------------------------

    @property
    def best_power(self) -> float:
        """Highest power achieved this episode. 0.0 before any scored step."""
        return max((h["power"] for h in self.history), default=0.0)

    def transcript(self) -> str:
        """Human-readable episode summary, for logs and demo output."""
        if not self.history:
            return "no scored steps"
        lines = []
        for h in self.history:
            lines.append(
                f"round {h['round']}: power {h['power']:.0%}  "
                f"testable {h['testable_rate']:.0%}  "
                f"lysed {h['mean_lysed_fraction']:.0%}  "
                f"({len(h['diagnoses'])} diagnoses)"
            )
        return "\n".join(lines)
