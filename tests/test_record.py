"""Recording and replaying an agent run.

The demo cannot depend on the network, and - the reason that actually bit - a
result you cannot recompute is a result you can only quote. When the non-robust
variance estimator was fixed, the first live run's revised design had never been
serialised, so its headline `~57 wells/arm` could not be recalculated. It became
unquotable rather than merely stale.

Nothing here calls a model.
"""

from __future__ import annotations

import json

import pytest

from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec
from refute.record import SCHEMA_VERSION, RecordedRound, RecordedRun, replay

REVISED = DesignSpec(
    conditions=["N-T", "N-CM+T"],
    replicates_per_condition=6,
    imaging_times_h=[6, 24, 120, 168],
    treatment_time_h=120.0,
    endpoint_time_h=168.0,
    antifibrinolytic=True,
    antifibrinolytic_agent="aprotinin 200 KIU/mL",
    normalise_to_own_baseline=True,
    locked_imaging_protocol=True,
    anticipates_scaffold_failure=True,
)


def _run() -> RecordedRun:
    return RecordedRun(
        agent="openai:gpt-5.5:high",
        extractor="openai:gpt-5.4-mini:low",
        brief="design a contraction experiment",
        recorded_at="2026-08-10T12:00:00+00:00",
        notes="stub",
        rounds=[
            RecordedRound(
                design_text="four arms, n=3, day 10",
                extracted=EXPERIMENT_4_AS_RUN,
                feedback_given="the scaffold was gone before your endpoint",
            ),
            RecordedRound(design_text="two arms, n=6, aprotinin", extracted=REVISED),
        ],
    )


def test_round_trips_through_json(tmp_path):
    path = _run().save(tmp_path / "runs" / "r.json")
    assert path.exists(), "save must create parent directories"

    loaded = RecordedRun.load(path)
    assert loaded.agent == "openai:gpt-5.5:high"
    assert len(loaded.rounds) == 2
    assert loaded.rounds[0].extracted == EXPERIMENT_4_AS_RUN
    assert loaded.rounds[1].extracted == REVISED
    assert loaded.rounds[0].feedback_given.startswith("the scaffold")


def test_scores_are_not_stored():
    """Scores must be recomputed, not read back.

    A file holding numbers the current code no longer produces would preserve a
    stale result and look authoritative doing it.
    """
    blob = json.dumps(_run().to_dict())
    for forbidden in ("power", "testable_rate", "replicates_needed"):
        assert forbidden not in blob


def test_replay_recomputes_against_the_current_twin():
    run = _run()
    scores = replay(run, n_sims=200)

    assert len(scores) == 2
    # Round 1 is the as-run design and must still score zero.
    assert scores[0].power == 0.0
    # Round 2 protects the scaffold, so it becomes testable without becoming
    # powered - the finding the recorded run exists to preserve.
    assert scores[1].testable_rate > 0.9
    assert scores[1].power < 0.5
    assert scores[1].mean_lysed_fraction < 0.05


def test_replay_reflects_a_calibration_change():
    """The property that makes recording worth doing.

    Replaying under different parameters must give a different answer, or the
    recording would be no better than storing the numbers.
    """
    from dataclasses import replace as dc_replace

    from refute.calibration import DEFAULT_PARAMS
    from refute.score import score_design

    run = _run()
    default = score_design(run.rounds[1].extracted, n_sims=200)
    # Aprotinin doing nothing: the revised design loses its scaffold protection.
    no_benefit = score_design(
        run.rounds[1].extracted,
        params=dc_replace(DEFAULT_PARAMS, aprotinin_hazard_scale=1.0),
        n_sims=200,
    )
    assert no_benefit.mean_lysed_fraction > default.mean_lysed_fraction


def test_a_future_schema_version_is_refused(tmp_path):
    """Half-reading a run would produce something plausible and wrong."""
    d = _run().to_dict()
    d["schema_version"] = SCHEMA_VERSION + 1
    path = tmp_path / "future.json"
    path.write_text(json.dumps(d))

    with pytest.raises(ValueError) as excinfo:
        RecordedRun.load(path)
    assert "Re-record" in str(excinfo.value)


def test_a_missing_schema_version_is_refused(tmp_path):
    d = _run().to_dict()
    del d["schema_version"]
    path = tmp_path / "old.json"
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError):
        RecordedRun.load(path)


def test_recorded_at_is_supplied_not_stamped():
    """A module that reads the clock cannot be tested deterministically."""
    assert RecordedRun(agent="a", extractor="b", brief="c").recorded_at is None


def test_cli_replay_prints_the_delta(tmp_path, capsys):
    from refute.cli import main

    path = _run().save(tmp_path / "r.json")
    code = main(["replay", str(path), "--sims", "200"])
    out = capsys.readouterr().out

    assert code == 0
    assert "RECORDED RUN" in out
    assert "DELTA" in out
    assert "n/arm needed" in out
    # Prose is withheld unless asked for, so the demo output stays readable.
    assert "four arms, n=3, day 10" not in out


def test_cli_replay_verbose_shows_the_prose(tmp_path, capsys):
    from refute.cli import main

    path = _run().save(tmp_path / "r.json")
    main(["replay", str(path), "--sims", "50", "--verbose"])
    assert "four arms, n=3, day 10" in capsys.readouterr().out


def test_any_committed_run_still_replays():
    """Recorded runs in the repo must stay replayable as the twin changes.

    A recorded run is primary data - re-running costs money and a model does not
    repeat itself - so it is version-controlled rather than regenerated. That
    makes it a fixture the code must keep honouring: if a `DesignSpec` field is
    renamed or the schema version moves, this fails here rather than during a
    demo. Skips cleanly until the first run is recorded.
    """
    from pathlib import Path

    runs = sorted(Path("cases").glob("*/runs/*.json"))
    if not runs:
        pytest.skip("no recorded runs yet (refute run --record)")

    for path in runs:
        run = RecordedRun.load(path)
        assert run.rounds, f"{path} records no rounds"
        assert run.agent, f"{path} does not say which model produced it"
        scores = replay(run, n_sims=100)
        assert len(scores) == len(run.rounds)


def test_cli_replay_refuses_an_out_of_scope_round(tmp_path, capsys):
    from refute.cli import main

    run = _run()
    run.rounds[1] = RecordedRound(
        design_text="switch to collagen",
        extracted=REVISED.model_copy(
            update={"out_of_twin_scope": ["collagen I matrix"]}
        ),
    )
    path = run.save(tmp_path / "oos.json")

    code = main(["replay", str(path), "--sims", "50"])
    assert code == 2
    assert "NOT SCORED" in capsys.readouterr().out
