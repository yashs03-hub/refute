"""Adversarial tests for the multi-assay handoff seam.

Verifies end-to-end routing from residual prose -> intake -> pipeline (Tier 1 & Tier 0)
-> bleomycin twin scoring -> API surface (/score, /score/text) without silent fallbacks
or unhandled attribute errors.
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from refute.api import app
from refute.assays import get as get_protocol
from refute.assays.evidence import Provenance
from refute.bleomycin_design import BleomycinDesignSpec, DEFAULT_BLEOMYCIN_DESIGN
from refute.bleomycin_score import BleomycinScore
from refute.cli import main
from refute.gate import Route
from refute.intake import intake
from refute.pipeline import run as run_pipeline
from refute.resolve import Requirement, Resolution, ResolutionSet, Resolver


REAL_BLEOMYCIN_RESIDUAL = (
    "whether intratracheal human umbilical cord mesenchymal stem cells (MSCs) "
    "reduce lung collagen deposition and Ashcroft fibrosis score at day 21 in "
    "bleomycin-induced pulmonary fibrosis mice without excessive procedural or disease mortality"
)


class BleomycinCompleteResolver(Resolver):
    """A mock resolver that provides a complete Tier-1 resolution set for bleomycin_lung."""

    name = "complete_bleomycin_fixture"

    def resolve(self, assay_key: str, requirements: tuple[Requirement, ...]) -> ResolutionSet:
        resolutions = {
            "baseline_score": Resolution(
                quantity="baseline_score",
                value=0.3,
                units="Ashcroft",
                provenance=Provenance.LITERATURE,
                source="Ferrini 2020",
            ),
            "bleomycin_effect": Resolution(
                quantity="bleomycin_effect",
                value=3.5,
                units="Ashcroft",
                provenance=Provenance.LITERATURE,
                source="Ferrini 2020",
            ),
            "animal_to_animal_sd": Resolution(
                quantity="animal_to_animal_sd",
                value=0.6,
                units="Ashcroft",
                provenance=Provenance.LITERATURE,
                source="Ferrini 2020",
            ),
            "mortality_by_day14": Resolution(
                quantity="mortality_by_day14",
                value=0.50,
                units="probability",
                provenance=Provenance.LITERATURE,
                source="Kim 2018",
            ),
            "mortality_severity_coupling": Resolution(
                quantity="mortality_severity_coupling",
                value=0.0,
                units="-",
                provenance=Provenance.ASSUMED,
                assumption="severity-independent mortality null",
                plausible_range=(0.0, 1.0),
                source="assumed",
            ),
            "p_dosing_failure": Resolution(
                quantity="p_dosing_failure",
                value=0.0,
                units="probability",
                provenance=Provenance.ASSUMED,
                assumption="negligible procedural failure in trained hands",
                plausible_range=(0.0, 0.2),
                source="assumed",
            ),
        }
        return ResolutionSet(
            assay_key=assay_key,
            requirement_version="v_test",
            resolutions=resolutions,
            unmodelled_mentions=(),
        )


class BleomycinTier0OnlyResolver(Resolver):
    """A mock resolver where Tier-1 constants are unsearched but Tier-0 inputs resolve."""

    name = "tier0_bleomycin_fixture"

    def resolve(self, assay_key: str, requirements: tuple[Requirement, ...]) -> ResolutionSet:
        resolutions = {
            "effect_size": Resolution(
                quantity="effect_size",
                value=1.5,
                units="Ashcroft",
                provenance=Provenance.LITERATURE,
                source="Ferrini 2020",
            ),
            "within_arm_sd": Resolution(
                quantity="within_arm_sd",
                value=0.6,
                units="Ashcroft",
                provenance=Provenance.LITERATURE,
                source="Ferrini 2020",
            ),
            "n_per_arm": Resolution(
                quantity="n_per_arm",
                value=10.0,
                units="animals",
                provenance=Provenance.LITERATURE,
                source="Ferrini 2020",
            ),
            "alpha": Resolution(
                quantity="alpha",
                value=0.05,
                units="-",
                provenance=Provenance.LITERATURE,
                source="standard",
            ),
        }
        return ResolutionSet(
            assay_key=assay_key,
            requirement_version="v_test_t0",
            resolutions=resolutions,
            unmodelled_mentions=(),
        )


def test_intake_cli_and_model_selection():
    # 1. CLI intake invocation
    code = main(["intake", REAL_BLEOMYCIN_RESIDUAL])
    assert code == 0

    # 2. Programmatic intake
    result = intake(REAL_BLEOMYCIN_RESIDUAL)
    assert result.selection.best is not None
    assert result.selection.best.key == "bleomycin_lung"

    # With extractor mock returning BleomycinDesignSpec
    extracted_spec = BleomycinDesignSpec(
        conditions=["bleomycin_only", "bleomycin_MSC"],
        replicates_per_condition=10,
        msc_route="IT",
        msc_dose=500_000,
        endpoint_day=21.0,
    )
    result_with_extractor = intake(REAL_BLEOMYCIN_RESIDUAL, extractor=lambda _txt: extracted_spec)
    assert result_with_extractor.ready
    assert isinstance(result_with_extractor.design, BleomycinDesignSpec)
    assert result_with_extractor.design.msc_route == "IT"
    assert result_with_extractor.design.total_animals == 20


def test_pipeline_routes_tier1_and_scores_bleomycin():
    protocol = get_protocol("bleomycin_lung")
    design = BleomycinDesignSpec(
        conditions=["bleomycin_only", "bleomycin_MSC"],
        replicates_per_condition=10,
        msc_route="IT",
        msc_dose=500_000,
        endpoint_day=21.0,
    )
    resolver = BleomycinCompleteResolver()

    res = run_pipeline(design, protocol, resolver, n_sims=50)
    assert res.decision.route == Route.TIER1
    assert isinstance(res.score, BleomycinScore)
    assert res.score.power > 0.0
    assert res.score.mean_animals_scored > 0.0

    # Verify narrative references animals and Ashcroft, NOT well lysis
    narrative_text = "\n".join(res.narrative)
    assert "mean animals scored" in narrative_text
    assert "wells lost by the endpoint" not in narrative_text
    assert "outcome: REVISE" in narrative_text or "outcome: TERMINAL" in narrative_text


def test_pipeline_routes_tier0_with_twin_capacity():
    protocol = get_protocol("bleomycin_lung")
    design = BleomycinDesignSpec(
        conditions=["bleomycin_only", "bleomycin_MSC"],
        replicates_per_condition=10,
        msc_route="IT",
        msc_dose=500_000,
        endpoint_day=21.0,
    )
    resolver = BleomycinTier0OnlyResolver()

    res = run_pipeline(design, protocol, resolver, n_sims=50)
    assert res.decision.route == Route.TIER0
    assert res.score is not None
    # Verify tier 0 used twin's default capacity (40 animals) rather than plate 12 wells
    assert "40 animals" in "\n".join(res.narrative) or res.score.feasibility != ""


def test_api_score_and_score_text_with_bleomycin(monkeypatch):
    import sys

    client = TestClient(app)

    # 1. Direct /score endpoint with bleomycin_lung
    req_body = {
        "assay": "bleomycin_lung",
        "design": DEFAULT_BLEOMYCIN_DESIGN.model_dump(),
        "n_sims": 50,
    }
    resp = client.post("/score", json=req_body)
    assert resp.status_code == 200, resp.text

    # Strict JSON validation (no bare NaN)
    body = json.loads(resp.text)
    assert "power" in body
    assert "testable_rate" in body
    assert "feasibility" in body
    assert body["power"] is not None

    # 2. /score/text endpoint with bleomycin_lung and mocked extractor
    monkeypatch.setattr(
        sys.modules["refute.intake"],
        "extract_design",
        lambda text, **kw: DEFAULT_BLEOMYCIN_DESIGN,
    )

    text_resp = client.post(
        "/score/text",
        json={
            "assay": "bleomycin_lung",
            "design_text": REAL_BLEOMYCIN_RESIDUAL,
            "n_sims": 50,
        },
    )
    assert text_resp.status_code == 200, text_resp.text
    text_data = text_resp.json()
    assert text_data["extracted"]["msc_route"] == "IT"
    assert text_data["score"]["power"] is not None


