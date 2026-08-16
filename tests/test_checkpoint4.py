"""Tests for Checkpoint 4 - chat.py and api.py multi-assay integration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from refute.api import app
from refute.bleomycin_design import DEFAULT_BLEOMYCIN_DESIGN
from refute.chat import Session
from refute.design import EXPERIMENT_4_AS_RUN


def test_chat_session_with_bleomycin_twin():
    session = Session(assay="bleomycin_lung", n_sims=50)
    session.design = DEFAULT_BLEOMYCIN_DESIGN
    session.score = session.twin.score_fn(DEFAULT_BLEOMYCIN_DESIGN, n_sims=50)

    # Test 'advise' turn
    turn_adv = session.ask("what should I change")
    assert turn_adv.intent == "advise"
    assert "change(s) help" in turn_adv.answer or "No single change" in turn_adv.answer

    # Test 'scale' turn
    turn_scale = session.ask("how many animals do I need")
    assert turn_scale.intent == "scale"
    assert "in total across" in turn_scale.answer or "NOT estimable" in turn_scale.answer

    # Test 'whatif' turn
    turn_whatif = session.ask("what if I try earlier endpoint")
    assert turn_whatif.intent == "whatif"


def test_api_score_bleomycin_design():
    client = TestClient(app)
    req_body = {
        "assay": "bleomycin_lung",
        "design": DEFAULT_BLEOMYCIN_DESIGN.model_dump(),
        "n_sims": 50,
    }
    resp = client.post("/score", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "power" in data
    assert "testable_rate" in data
    assert "feasibility" in data


def test_api_score_fibrin_default():
    client = TestClient(app)
    req_body = {
        "design": EXPERIMENT_4_AS_RUN.model_dump(),
        "n_sims": 50,
    }
    resp = client.post("/score", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["power"] < 0.5
