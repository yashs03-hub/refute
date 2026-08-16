"""Tests for Checkpoint 3 - handoff seam (intake.py and pipeline.py multi-assay integration)."""

from __future__ import annotations

from refute.assays import get as get_protocol
from refute.bleomycin_design import BleomycinDesignSpec, DEFAULT_BLEOMYCIN_DESIGN
from refute.design import DesignSpec, EXPERIMENT_4_AS_RUN
from refute.intake import extract_design, intake
from refute.pipeline import run as run_pipeline
from refute.adapt import RecordedResolver
from refute.resolve import FixtureResolver

from refute.twins import TWINS


def test_intake_picks_bleomycin_and_uses_bleomycin_design_spec():
    text = "whether intratracheal MSC administration reduces Ashcroft fibrosis score in bleomycin mouse lung model"
    result = intake(text)
    assert result.selection.best is not None
    assert result.selection.best.key == "bleomycin_lung"

    # With a custom extractor returning BleomycinDesignSpec
    mock_extractor = lambda _txt: DEFAULT_BLEOMYCIN_DESIGN
    result_with_extractor = intake(text, extractor=mock_extractor)
    assert result_with_extractor.ready
    assert isinstance(result_with_extractor.design, BleomycinDesignSpec)
    assert result_with_extractor.design.msc_route == "IT"


def test_extract_design_type_validation():
    # If the wrong design spec type is returned by extractor, ExtractionFailure is raised
    mock_wrong_extractor = lambda _txt: EXPERIMENT_4_AS_RUN
    result = intake("bleomycin mouse model", extractor=mock_wrong_extractor)
    assert result.extraction.value == "failed"
    assert "not a BleomycinDesignSpec" in result.note


def test_pipeline_run_dispatches_bleomycin_twin():
    protocol = get_protocol("bleomycin_lung")
    resolver = RecordedResolver()
    design = DEFAULT_BLEOMYCIN_DESIGN

    res = run_pipeline(design, protocol, resolver, n_sims=50)
    assert res.decision.route.value in ("tier1", "tier0", "not_ready", "refuse")
    assert len(res.narrative) > 0
