"""The registry owns the requirement list, and the version that names it.

Two claims are under test.

**Requirements are exogenous to the resolver.** Every tier-1 requirement is a
constant the protocol already declared, and `tier1_needs` may neither add one
nor drop one. That is the property that keeps a coverage figure meaningful: a
resolver allowed to decide what was required would report full coverage forever,
because it would only ever ask for what it could answer.

**The version is stable across processes.** `requirement_version` exists so a
stored `ResolutionSet` can say which revision of the registry it answers. Built
on Python's `hash()` it would be salted per interpreter, so the same code would
produce a different version on every run and mark every stored answer stale on a
restart - a failure that only appears across process boundaries and would
therefore be found late, in production, intermittently. So it is asserted across
a real subprocess with a deliberately hostile PYTHONHASHSEED, not just twice in
this one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from refute.assays import REGISTRY, get
from refute.assays.base import AssayProtocol
from refute.assays.tier1 import TIER1
from refute.requirements import requirement_version, tier0_needs, tier1_needs
from refute.resolve import TIER0_NEEDS

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "cases" / "fixtures"

PROTOCOLS = sorted(REGISTRY.values(), key=lambda p: p.key)


# --- tier 1: derived from the protocol, never from the search ---------------


@pytest.mark.parametrize("protocol", TIER1, ids=lambda p: p.key)
def test_every_scaffold_declares_something_to_resolve(protocol):
    """A scaffold with no requirements is not an uncalibrated protocol, it is an
    empty one - and it would report 100% coverage against any resolver."""
    assert tier1_needs(protocol)


@pytest.mark.parametrize("protocol", PROTOCOLS, ids=lambda p: p.key)
def test_requirements_are_exactly_the_declared_constants(protocol):
    """Nothing added, nothing dropped, order preserved. This is the whole of
    'the registry owns the list' expressed as an equality."""
    assert [r.key for r in tier1_needs(protocol)] == [
        c.name for c in protocol.all_constants()
    ]
    assert [r.units for r in tier1_needs(protocol)] == [
        c.units for c in protocol.all_constants()
    ]


@pytest.mark.parametrize("protocol", PROTOCOLS, ids=lambda p: p.key)
def test_requirement_keys_are_unique(protocol):
    """`ResolutionSet.resolutions` is keyed by name, so two constants sharing
    one would collapse into a single entry and the totality guarantee would be
    a lie about whichever of them lost."""
    keys = [r.key for r in tier1_needs(protocol)]
    assert len(keys) == len(set(keys)), sorted(keys)


@pytest.mark.parametrize("protocol", PROTOCOLS, ids=lambda p: p.key)
def test_every_requirement_is_searchable(protocol):
    """Units and a description on every one. A requirement nobody can read is a
    requirement nobody can fill."""
    for r in tier1_needs(protocol):
        assert r.tier == "tier1"
        assert r.units, r.key
        assert r.what, r.key
        assert not r.what.startswith("UNCALIBRATED"), (
            f"{r.key}: the calibration tag describes provenance, not the "
            "quantity, and should have been stripped"
        )


@pytest.mark.parametrize("protocol", TIER1, ids=lambda p: p.key)
def test_scaffolds_carry_their_search_forward(protocol):
    """The Paperclip query is the protocol's own, so a resolver does not have to
    invent one - inventing it is how a resolver ends up defining the
    requirement."""
    for r in tier1_needs(protocol):
        assert r.query_hint == protocol.paperclip_query


def test_a_calibrated_protocol_has_no_query_hint_to_give():
    """fibrin_contracture is already fitted to primary data, so it lists no
    outstanding needs and no query. Its requirements still exist - a resolver
    may be asked to re-derive them from literature - but there is nothing to
    search for on the protocol's authority."""
    for r in tier1_needs(get("fibrin_contracture")):
        assert r.query_hint == ""
        assert r.what


@pytest.mark.parametrize("protocol", TIER1, ids=lambda p: p.key)
def test_calibration_needs_reach_the_requirements(protocol):
    """Every scaffold writes its calibration needs for a person doing the
    extraction, and at least some of them should end up on the requirement they
    describe rather than being left in a docstring nobody reads."""
    described = {r.what for r in tier1_needs(protocol)}
    assert described & set(protocol.calibration_needs), protocol.key


def test_a_duplicate_constant_is_refused():
    protocol = get("fibrin_contracture")
    readout = protocol.readout
    doubled = type(protocol)(
        **{
            **protocol.__dict__,
            "readout": type(readout)(
                **{
                    **readout.__dict__,
                    "constants": readout.constants + (readout.constants[0],),
                }
            ),
        }
    )
    with pytest.raises(ValueError, match="declared twice"):
        tier1_needs(doubled)


# --- tier 0: assay-blind --------------------------------------------------


def test_tier0_needs_match_the_contract():
    """`TIER0_NEEDS` in resolve.py is what the gate routes on. If this module
    described a different four, the fallback would be answering a question the
    gate never asked."""
    assert tuple(r.key for r in tier0_needs()) == TIER0_NEEDS


def test_tier0_requirements_are_complete_and_assay_blind():
    for r in tier0_needs():
        assert r.tier == "tier0"
        assert r.units, r.key
        assert r.what, r.key
        assert r.query_hint == "", (
            f"{r.key}: tier 0 quantities come from the experimenter or a pilot, "
            "not from a corpus"
        )


def test_tier0_takes_no_protocol():
    """Stated as a test because it is the reason tier 0 scales: it answers for
    a comparison `refute` has never seen."""
    assert tier0_needs() == tier0_needs()


def test_tier0_and_tier1_key_spaces_do_not_collide():
    """A shared key would make one requirement answer for both tiers, and the
    fallback would inherit the primary path's gap."""
    tier0 = {r.key for r in tier0_needs()}
    for protocol in PROTOCOLS:
        assert not tier0 & {r.key for r in tier1_needs(protocol)}, protocol.key


# --- versioning: the salted-hash trap --------------------------------------

_PROBE = (
    "from refute.assays import REGISTRY;"
    "from refute.requirements import requirement_version;"
    "print(' '.join("
    "requirement_version(p) for _, p in sorted(REGISTRY.items())))"
)


def _versions_from_a_fresh_interpreter(hash_seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONPATH=str(ROOT))
    done = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def test_requirement_version_is_stable_within_a_process():
    protocol = get("fibrin_contracture")
    assert requirement_version(protocol) == requirement_version(protocol)


def test_requirement_version_survives_a_hostile_hash_seed():
    """The actual trap. `hash()` is randomised per interpreter unless
    PYTHONHASHSEED is pinned, so a version built on it agrees with itself all
    day inside one process and disagrees on every restart. Two subprocesses with
    different seeds, compared against this process, is the only assertion that
    catches it."""
    here = " ".join(
        requirement_version(p) for _, p in sorted(REGISTRY.items())
    )
    for seed in ("0", "1", "12345", "random"):
        assert _versions_from_a_fresh_interpreter(seed) == here, seed


def test_requirement_version_distinguishes_protocols():
    """A version that ignored its input would be perfectly stable and
    completely useless."""
    versions = {p.key: requirement_version(p) for p in PROTOCOLS}
    assert len(set(versions.values())) == len(versions), versions


def test_requirement_version_ignores_declaration_order():
    """Reordering constants does not change what is required, so it must not
    invalidate answers that are still total over the same key set."""
    protocol = get("fibrin_contracture")
    readout = protocol.readout
    reordered = _replace_readout_constants(
        protocol, tuple(reversed(readout.constants))
    )
    assert requirement_version(reordered) == requirement_version(protocol)
    assert [r.key for r in tier1_needs(reordered)] != [
        r.key for r in tier1_needs(protocol)
    ], "the reordering under test did not actually reorder anything"


def test_requirement_version_changes_when_a_key_is_added():
    """Adding a requirement genuinely does make an old answer non-total, and
    that is exactly what the version is for."""
    protocol = get("fibrin_contracture")
    extra = type(protocol.readout.constants[0])(
        name="a_new_thing", value=None, units="-", provenance="UNCALIBRATED - new"
    )
    grown = _replace_readout_constants(
        protocol, protocol.readout.constants + (extra,)
    )
    assert requirement_version(grown) != requirement_version(protocol)


def _replace_readout_constants(protocol: AssayProtocol, constants) -> AssayProtocol:
    readout = type(protocol.readout)(**{**protocol.readout.__dict__,
                                        "constants": constants})
    return type(protocol)(**{**protocol.__dict__, "readout": readout})


# --- the fixtures answer this registry, not an older one -------------------


def test_fixtures_declare_the_current_requirement_version():
    """If a constant is ever added to fibrin_contracture, these files stop being
    total over its requirement set. Failing here is the intended outcome: it
    says the fixtures need revising, not that the registry is wrong."""
    expected = requirement_version(get("fibrin_contracture"))
    paths = sorted(FIXTURE_DIR.glob("*.json"))
    assert paths, f"no fixtures found in {FIXTURE_DIR}"
    for path in paths:
        raw = json.loads(path.read_text())
        assert raw["requirement_version"] == expected, (
            f"{path.name} answers requirement set "
            f"{raw['requirement_version']!r}, registry is now {expected!r}"
        )
