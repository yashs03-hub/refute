"""Designs the twin cannot represent must not be scored.

The twin models one apparatus. A design that changes the matrix, the seeding
density or the readout is not worse - it is a design this twin has nothing to
say about. Returning a number anyway is an error in the permissive direction,
which for a verifier is the one that matters.
"""

from __future__ import annotations

import pytest

from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec, OutOfTwinScopeError
from refute.environment import RefuteEnv
from refute.score import score_design

COLLAGEN = EXPERIMENT_4_AS_RUN.model_copy(
    update={
        "out_of_twin_scope": [
            "matrix changed from fibrin to rat-tail collagen I at 2 mg/mL",
            "seeding density raised from 5e5 to 1e6 cells/mL",
        ]
    }
)


def test_the_field_defaults_to_empty():
    """Existing designs must be unaffected - the guard is opt-in by content."""
    assert EXPERIMENT_4_AS_RUN.out_of_twin_scope == []
    score_design(EXPERIMENT_4_AS_RUN, n_sims=50)  # must not raise


def test_out_of_scope_design_raises_rather_than_scoring():
    with pytest.raises(OutOfTwinScopeError) as excinfo:
        score_design(COLLAGEN, n_sims=50)
    # The reasons must survive onto the exception, or a caller cannot report
    # what was unmodelled.
    assert len(excinfo.value.reasons) == 2
    assert "collagen" in excinfo.value.reasons[0]


def test_the_message_blames_the_twin_not_the_design():
    """The wording is load-bearing: this is a limit, not a verdict."""
    exc = OutOfTwinScopeError(["a different matrix"])
    text = str(exc)
    assert "limit of the twin" in text
    assert "not a defect in the design" in text
    # It should also say what the twin DOES cover, or the message is a dead end.
    assert "fibrin" in text


def test_scoring_the_same_design_without_the_field_still_works():
    """Proves the guard fires on the field, not on anything else about the design."""
    stripped = COLLAGEN.model_copy(update={"out_of_twin_scope": []})
    score = score_design(stripped, n_sims=50)
    assert score.power == 0.0  # it is the as-run design underneath


def test_environment_ends_the_episode_instead_of_propagating():
    """An RL loop cannot handle an exception mid-episode.

    The library raises, which is right for a caller expecting a number; the
    environment must translate that into an unscored terminal step.
    """
    env = RefuteEnv(n_sims=50)
    env.reset()
    result = env.step(COLLAGEN)  # must not raise

    assert result.info["scored"] is False
    assert result.info["error"] == "out_of_twin_scope"
    assert len(result.info["out_of_scope"]) == 2
    assert result.done is True
    assert result.observation is None
    assert env.history == [], "an unscored step must not enter the episode record"


def test_api_returns_a_distinguishable_422():
    """422 is shared with schema validation, so the body must disambiguate."""
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from refute.api import app

    client = TestClient(app)
    r = client.post("/score", json={"design": COLLAGEN.model_dump(), "n_sims": 50})

    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "out_of_twin_scope"
    assert len(body["out_of_scope"]) == 2
    # A schema-validation 422 has no `error` key, which is how a client tells
    # "your JSON is wrong" from "the twin cannot model this".
    bad_schema = client.post("/score", json={"design": {"conditions": ["N-T"]}})
    assert bad_schema.status_code == 422
    assert "error" not in bad_schema.json()


def test_cli_baseline_reports_it_and_exits_nonzero(tmp_path, capsys):
    from refute.cli import main

    path = tmp_path / "design.json"
    path.write_text(COLLAGEN.model_dump_json())

    code = main(["baseline", "--design", str(path)])
    out = capsys.readouterr().out

    assert code == 2, "an unscored design must not exit 0"
    assert "NOT SCORED" in out
    assert "collagen" in out
    # It must not print a score of any kind alongside the refusal.
    assert "power to recover" not in out


def test_a_single_unmodelled_feature_is_enough():
    one = EXPERIMENT_4_AS_RUN.model_copy(
        update={"out_of_twin_scope": ["readout changed to hydroxyproline assay"]}
    )
    with pytest.raises(OutOfTwinScopeError):
        score_design(one, n_sims=50)


def test_whitespace_only_entries_are_not_treated_as_scope_violations():
    """An extractor emitting a stray empty string must not block a valid design.

    Otherwise the guard becomes a source of false refusals, which is the
    conservative direction but still wrong.
    """
    noisy = EXPERIMENT_4_AS_RUN.model_copy(update={"out_of_twin_scope": ["", "  "]})
    score_design(noisy, n_sims=50)  # must not raise
