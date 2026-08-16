"""The calibration gate is the contract these tests protect.

The premise of this project is that its ground truth is measured rather than
invented. A scaffold that quietly produced plausible numbers would reintroduce
exactly what the project criticises - so 'scaffolds cannot be scored' is a
correctness property, not a nicety.
"""

from __future__ import annotations

import pytest

from refute.assays import (
    REGISTRY,
    CalibrationStatus,
    UncalibratedAssayError,
    get,
    runnable,
    scaffolds,
)
from refute.assays.tier1 import TIER1


def test_exactly_one_protocol_is_measured():
    """Only case 1 has primary data behind it. If this count grows, something
    was promoted without measurements to justify it."""
    measured = [p for p in REGISTRY.values() if p.status is CalibrationStatus.MEASURED]
    assert [p.key for p in measured] == ["fibrin_contracture"]


def test_the_measured_protocol_is_runnable():
    assert get("fibrin_contracture").runnable
    get("fibrin_contracture").require_runnable()   # must not raise


@pytest.mark.parametrize("protocol", TIER1, ids=lambda p: p.key)
def test_scaffolds_refuse_to_be_scored(protocol):
    assert not protocol.runnable
    with pytest.raises(UncalibratedAssayError):
        protocol.require_runnable()


@pytest.mark.parametrize("protocol", TIER1, ids=lambda p: p.key)
def test_scaffolds_say_what_would_calibrate_them(protocol):
    """A scaffold that cannot tell you how to fill it in is just a stub."""
    assert protocol.missing_constants(), "a scaffold must have missing constants"
    assert protocol.calibration_needs, f"{protocol.key} lists nothing to obtain"
    assert protocol.paperclip_query, f"{protocol.key} has no search to run"
    for c in protocol.missing_constants():
        assert c.provenance.startswith("UNCALIBRATED"), c.name


@pytest.mark.parametrize("protocol", TIER1, ids=lambda p: p.key)
def test_every_protocol_names_its_failure_mechanism_and_driver(protocol):
    assert protocol.hazard.mechanism
    assert protocol.hazard.driver
    assert protocol.why_it_matters


def test_tier1_selection_criterion_holds():
    """Tier 1 exists because the measured phenotype drives the failure.

    Exactly one member is exempt: fibrosis_on_chip, driven by an applied
    strain you set, not by the phenotype being measured. `stiffness_drift`
    moved OUT of the exempt set 2026-08-16 - owner call that its drift
    depends on encapsulated cells (see tier1.py's STIFFNESS_DRIFT.hazard for
    the evidence and its stated limits). If another exemption appears
    besides fibrosis_on_chip, the tier has lost its selection criterion.
    """
    exempt = [p.key for p in TIER1 if not p.hazard.driver_is_the_measured_phenotype]
    assert exempt == ["fibrosis_on_chip"], (
        f"unexpected tier-1 members whose failure is not phenotype-driven: {exempt}"
    )


def test_registry_partitions_cleanly():
    assert len(runnable()) + len(scaffolds()) == len(REGISTRY)
    assert set(runnable()).isdisjoint(scaffolds())


def test_unknown_key_lists_the_alternatives():
    with pytest.raises(KeyError, match="scar_in_a_jar"):
        get("nope")
