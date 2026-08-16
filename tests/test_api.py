"""The HTTP surface.

Nothing here calls a model. `/score` genuinely does not need one; the endpoints
that do have their extractor and agent stubbed, so the suite stays free to run
and cannot bill anyone by accident.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from refute.api import MAX_N_SIMS, RUN_ENABLED_ENV, app  # noqa: E402
from refute.design import EXPERIMENT_4_AS_RUN  # noqa: E402

client = TestClient(app)

AS_RUN = EXPERIMENT_4_AS_RUN.model_dump()


def test_healthz_reports_whether_run_is_enabled(monkeypatch):
    monkeypatch.delenv(RUN_ENABLED_ENV, raising=False)
    body = client.get("/healthz").json()
    assert body["ok"] is True
    assert body["run_enabled"] is False


def test_score_needs_no_credential(monkeypatch):
    """The pure path must not touch a provider.

    Enforced rather than asserted: any provider lookup raises, so a regression
    that starts calling a model on /score fails here.
    """
    import refute.providers as providers

    monkeypatch.setattr(
        providers,
        "get_provider",
        lambda *_a, **_k: pytest.fail("/score called a model provider"),
    )

    r = client.post("/score", json={"design": AS_RUN, "n_sims": 100})
    assert r.status_code == 200
    body = r.json()
    # The calibration case: the design that was actually run recovers nothing.
    assert body["power"] == 0.0
    assert body["failed"] is True
    assert body["diagnoses"]


def test_score_response_is_valid_json_not_nan():
    """NaN and the -1 sentinel are not representable in JSON.

    `DesignScore` uses both for 'not estimable'. If they leaked through, a
    strict JSON client would fail to parse the response, or would read -1 as a
    real well count. Both must arrive as null.
    """
    # One condition, one replicate: too little to estimate spread, so the twin
    # returns NaN for the MDE and -1 for replicates_needed.
    thin = dict(AS_RUN, conditions=["N-T"], replicates_per_condition=1)
    r = client.post("/score", json={"design": thin, "n_sims": 50})
    assert r.status_code == 200

    import json

    # Strict parse: json.loads rejects bare NaN unless it is allowed explicitly.
    body = json.loads(r.text, parse_constant=_reject_constant)
    assert body["min_detectable_ratio_diff"] is None
    assert body["replicates_needed"] is None


def _reject_constant(name: str):
    raise AssertionError(f"non-JSON constant {name!r} in response")


def test_score_is_reproducible_by_default():
    a = client.post("/score", json={"design": AS_RUN, "n_sims": 100}).json()
    b = client.post("/score", json={"design": AS_RUN, "n_sims": 100}).json()
    assert a["power"] == b["power"]
    assert a["mean_lysed_fraction"] == b["mean_lysed_fraction"]


def test_n_sims_is_capped():
    r = client.post("/score", json={"design": AS_RUN, "n_sims": MAX_N_SIMS + 1})
    assert r.status_code == 422, "an unbounded simulation request must be refused"


def test_malformed_design_is_a_422():
    r = client.post("/score", json={"design": {"conditions": ["N-T"]}})
    assert r.status_code == 422


def test_score_text_returns_what_it_read(monkeypatch):
    """A caller must be able to tell a misread design from a bad one."""
    import refute.agent as agent_mod

    monkeypatch.setattr(
        agent_mod, "extract_design", lambda *_a, **_k: EXPERIMENT_4_AS_RUN
    )

    r = client.post(
        "/score/text", json={"design_text": "four arms, n=3, day 10 endpoint", "n_sims": 50}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["extracted"]["replicates_per_condition"] == 3
    assert body["score"]["power"] == 0.0


def test_score_text_rejects_empty_prose():
    r = client.post("/score/text", json={"design_text": ""})
    assert r.status_code == 422


def test_missing_credential_is_503_not_500(monkeypatch):
    """A server that is not configured should say so, not look broken."""
    import refute.agent as agent_mod

    def no_key(*_a, **_k):
        raise RuntimeError("OPENAI_API_KEY is not set")

    monkeypatch.setattr(agent_mod, "extract_design", no_key)

    r = client.post("/score/text", json={"design_text": "a plate"})
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_upstream_provider_failure_is_502(monkeypatch):
    import refute.agent as agent_mod

    def rate_limited(*_a, **_k):
        raise RuntimeError("429 rate limit exceeded")

    monkeypatch.setattr(agent_mod, "extract_design", rate_limited)

    r = client.post("/score/text", json={"design_text": "a plate"})
    assert r.status_code == 502
    assert "429" in r.json()["detail"]


def test_run_is_disabled_by_default(monkeypatch):
    """An endpoint that spends money must not be on by default."""
    monkeypatch.delenv(RUN_ENABLED_ENV, raising=False)
    r = client.post("/run", json={})
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert RUN_ENABLED_ENV in detail
    # The refusal should point at the endpoint that costs nothing.
    assert "/score" in detail


def test_run_stays_disabled_for_other_env_values(monkeypatch):
    for value in ("0", "true", "yes", "", " "):
        monkeypatch.setenv(RUN_ENABLED_ENV, value)
        assert client.post("/run", json={}).status_code == 403


def test_run_when_enabled_returns_both_rounds(monkeypatch):
    monkeypatch.setenv(RUN_ENABLED_ENV, "1")

    import refute.agent as agent_mod

    monkeypatch.setattr(agent_mod, "propose_design", lambda **_k: "first design")
    monkeypatch.setattr(agent_mod, "revise_design", lambda *_a, **_k: "revised design")
    monkeypatch.setattr(
        agent_mod, "extract_design", lambda *_a, **_k: EXPERIMENT_4_AS_RUN
    )

    r = client.post("/run", json={"n_sims": 50})
    assert r.status_code == 200
    body = r.json()
    assert len(body["rounds"]) == 2
    assert body["rounds"][0]["design_text"] == "first design"
    assert body["rounds"][1]["design_text"] == "revised design"
    assert "tokens" in body


def test_run_without_revision_returns_one_round(monkeypatch):
    monkeypatch.setenv(RUN_ENABLED_ENV, "1")

    import refute.agent as agent_mod

    monkeypatch.setattr(agent_mod, "propose_design", lambda **_k: "only design")
    monkeypatch.setattr(
        agent_mod, "revise_design", lambda *_a, **_k: pytest.fail("must not revise")
    )
    monkeypatch.setattr(
        agent_mod, "extract_design", lambda *_a, **_k: EXPERIMENT_4_AS_RUN
    )

    r = client.post("/run", json={"n_sims": 50, "revise": False})
    assert r.status_code == 200
    assert len(r.json()["rounds"]) == 1


def test_run_bad_model_spec_is_400(monkeypatch):
    monkeypatch.setenv(RUN_ENABLED_ENV, "1")
    r = client.post("/run", json={"agent": "not-a-real-spec-format:::"})
    assert r.status_code == 400


def test_assays_reports_two_runnable_and_six_scaffolds():
    """Was one runnable (Experiment 4 only); `bleomycin_lung` promoted to
    LITERATURE tier 2026-08-16. `runnable` here means the registry's
    constants are real, not that `/score` can do anything sensible with a
    bleomycin_lung design - `twin.py` still models only the fibrin
    apparatus. See `bleomycin_lung.py`'s module docstring. Scaffold count is
    six, not five, since `apoptosis_resistance` landed the same day as a
    brand-new candidate third twin, still SCAFFOLD (see tier1.py)."""
    r = client.get("/assays")
    assert r.status_code == 200
    body = r.json()
    runnable = [a for a in body if a["runnable"]]
    scaffolds = [a for a in body if not a["runnable"]]

    assert len(runnable) == 2, "Experiment 4 (MEASURED) + bleomycin_lung (LITERATURE)"
    assert {a["key"] for a in runnable} == {"fibrin_contracture", "bleomycin_lung"}
    assert len(scaffolds) == 6
    # A scaffold must name what it lacks, or the refusal is not actionable.
    assert all(a["missing_constants"] for a in scaffolds)


def test_openapi_schema_is_generated():
    """The schema is the contract a judge or another team reads first."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert {"/score", "/score/text", "/run", "/assays", "/healthz"} <= set(paths)
