"""Serialise an agent run, so a result can be shown without calling a model.

Two reasons, and the second is the one that bit.

**The demo cannot depend on the network.** A live `refute run` is a multi-minute
silence against a 10k TPM limit on venue wifi, with a real chance of a 429. The
strongest result in the project should not be one rate-limit away from not
existing.

**A result you cannot recompute is a result you can only quote.** When the
non-robust variance estimator was fixed on 2026-08-10, every
required-replication figure changed - and the first live run's revised design had
never been serialised, so its number could not be recalculated. The headline
`~57 wells/arm` became unquotable rather than merely wrong. Recording the run
would have made it a one-command re-score.

A recorded run stores the *prose and the extracted specs*, not the scores.
Scores are derived, so replaying re-simulates them against the current twin - which
means a recorded run stays honest across a calibration change instead of
preserving numbers the code no longer produces.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .design import DesignSpec

# Bumped when the stored shape changes incompatibly, so an old file fails loudly
# rather than being half-read into a plausible-looking run.
SCHEMA_VERSION = 1


@dataclass
class RecordedRound:
    """One turn of the loop, as the agent produced it."""

    design_text: str
    extracted: DesignSpec
    feedback_given: str | None = None  # what prompted the NEXT round, if any

    def to_dict(self) -> dict[str, Any]:
        return {
            "design_text": self.design_text,
            "extracted": self.extracted.model_dump(),
            "feedback_given": self.feedback_given,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RecordedRound":
        return cls(
            design_text=d["design_text"],
            extracted=DesignSpec.model_validate(d["extracted"]),
            feedback_given=d.get("feedback_given"),
        )


@dataclass
class RecordedRun:
    """A complete agent run, replayable without a credential.

    `recorded_at` is passed in rather than stamped here: a module that reads the
    clock cannot be tested deterministically, and the caller always knows the
    time anyway.
    """

    agent: str
    extractor: str
    brief: str
    rounds: list[RecordedRound] = field(default_factory=list)
    recorded_at: str | None = None
    notes: str = ""
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "agent": self.agent,
            "extractor": self.extractor,
            "brief": self.brief,
            "recorded_at": self.recorded_at,
            "notes": self.notes,
            "rounds": [r.to_dict() for r in self.rounds],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RecordedRun":
        version = d.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"recorded run is schema version {version!r}, this build reads "
                f"{SCHEMA_VERSION}. Re-record it rather than editing the file - a "
                "partially-read run would look plausible and be wrong."
            )
        return cls(
            agent=d["agent"],
            extractor=d["extractor"],
            brief=d["brief"],
            rounds=[RecordedRound.from_dict(r) for r in d["rounds"]],
            recorded_at=d.get("recorded_at"),
            notes=d.get("notes", ""),
        )

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return p

    @classmethod
    def load(cls, path: str | Path) -> "RecordedRun":
        return cls.from_dict(json.loads(Path(path).read_text()))


def replay(run: RecordedRun, n_sims: int = 400, seed: int | None = 0) -> list[Any]:
    """Re-score every round of a recorded run against the CURRENT twin.

    Scores are recomputed rather than read back, so a recorded run reflects the
    calibration in force now. If a constant changes, the replay changes with it -
    which is the property that was missing when the estimator fix orphaned the
    first live result.
    """
    from .score import score_design

    return [
        score_design(r.extracted, n_sims=n_sims, seed=seed) for r in run.rounds
    ]
