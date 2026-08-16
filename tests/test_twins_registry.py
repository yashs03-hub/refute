"""The dispatch layer `optimize`/`baseline`/`chat`/`advise`/`api`/`pipeline`
all read to decide which twin scores which assay."""

from __future__ import annotations

from refute.bleomycin_design import BleomycinDesignSpec
from refute.bleomycin_score import score_bleomycin_design
from refute.design import DesignSpec
from refute.score import score_design
from refute.twins import DEFAULT_ASSAY, TWINS, get_twin


def test_both_assays_are_registered():
    assert set(TWINS) == {"fibrin_contracture", "bleomycin_lung"}


def test_fibrin_contracture_registers_the_existing_unmodified_pieces():
    """No refactor of shipped code - the registry entry points at exactly
    the objects `design.py`/`score.py` already define."""
    twin = TWINS["fibrin_contracture"]
    assert twin.design_spec_type is DesignSpec
    assert twin.score_fn is score_design
    assert twin.default_capacity == 12


def test_bleomycin_lung_registers_the_new_pieces():
    twin = TWINS["bleomycin_lung"]
    assert twin.design_spec_type is BleomycinDesignSpec
    assert twin.score_fn is score_bleomycin_design
    assert twin.default_capacity > 0


def test_get_twin_matches_dict_lookup():
    for key in TWINS:
        assert get_twin(key) is TWINS[key]


def test_get_twin_raises_a_readable_error_for_an_unknown_assay():
    try:
        get_twin("not_a_real_assay")
        assert False, "expected KeyError"
    except KeyError as exc:
        msg = str(exc)
        assert "fibrin_contracture" in msg
        assert "bleomycin_lung" in msg


def test_default_assay_is_fibrin_contracture():
    """Backward compatibility: every existing `--assay`-less CLI invocation
    must keep behaving exactly as it did before this registry existed."""
    assert DEFAULT_ASSAY == "fibrin_contracture"


def test_both_score_functions_share_the_minimal_structural_surface():
    """No forced shared base class (see twins.py's module docstring), but
    both score objects must support the same handful of attributes/methods
    the dispatch layer relies on."""
    from refute.bleomycin_design import BLEOMYCIN_MSC, BLEOMYCIN_ONLY

    fibrin_score = score_design(
        DesignSpec(
            conditions=["N-SS", "N-T"], replicates_per_condition=3,
            imaging_times_h=[24, 120, 168], treatment_time_h=120.0,
            endpoint_time_h=168.0, antifibrinolytic=True,
            normalise_to_own_baseline=True, locked_imaging_protocol=True,
        ),
        n_sims=20,
    )
    bleo_score = score_bleomycin_design(
        BleomycinDesignSpec(
            conditions=[BLEOMYCIN_ONLY, BLEOMYCIN_MSC], replicates_per_condition=3,
        ),
        n_sims=20,
    )
    for obj in (fibrin_score, bleo_score):
        assert hasattr(obj, "power")
        assert hasattr(obj, "testable_rate")
        assert hasattr(obj, "verdict_sensitive_to_assumption")
        assert callable(obj.summary)
        assert isinstance(obj.summary(), str)
