"""Two contracts that are enforced in one place and relied on in several.

Both were found the same way: a thing that has to agree exactly, agreeing today
for reasons nobody had written a test for.

  1. **The requirement-version digest.** Three modules compute it -
     `requirements` from a protocol, `adapt` from the requirement list it was
     handed, `handoff` from the same - and they must agree exactly, or
     `pipeline._version_warning` reports a drift that is not there. Each was
     written as its own copy for a locally sound reason, and each reason is now
     recorded next to the shared function in `digest.py` instead. These tests
     pin all three together so that a fourth copy, or an edit to the one that is
     left, fails here rather than in an intermittent warning.

  2. **The unit strings.** `handoff.resolutions_from_findings` matches a finding
     to a requirement only when the units agree after normalisation, and it has
     no synonym table on purpose. That refusal is only payable by layer 1 if
     they are told what to emit, so `vocabulary.units_contract_report` publishes
     it. A published contract that can disagree with the code enforcing it is
     worse than none, because it will be trusted - so these tests check that the
     published strings are read from the registry, and that findings carrying
     them actually resolve.

The second half deliberately goes through the matcher rather than comparing
strings to strings. The failure this guards against is not an exception: it is a
`ResolutionSet` reporting zero coverage, which reads exactly like a literature
search that came back empty.
"""

from __future__ import annotations

import dataclasses

import pytest

from refute import digest
from refute import handoff as handoff_module
from refute.adapt import RecordedResolver
from refute.assays import REGISTRY, get
from refute.assays.base import AssayProtocol, Constant
from refute.digest import VERSION_CHARS, requirement_digest
from refute.handoff import (
    Finding,
    Handoff,
    OpenItem,
    normalise_units,
    resolution_set_from_handoff,
    resolutions_from_findings,
)
from refute.pipeline import requirements_for
from refute.requirements import requirement_version, tier0_needs, tier1_needs
from refute.resolve import BlockedReason, Requirement
from refute.vocabulary import UnitContract, unit_contract, units_contract_report

KEYS = sorted(REGISTRY)


def _handoff() -> Handoff:
    """The smallest legal handoff. It carries nothing, on purpose.

    The digest is a statement about the requirement set, never about what came
    back against it, so the emptiest possible handoff is the cleanest probe.
    """
    return Handoff(
        question="does it hold",
        hypothesis="it holds",
        residual=(OpenItem(statement="unsettled", why="needs_new_data", searched=False),),
    )


def _requirement(key: str, units: str = "-", tier: str = "tier1") -> Requirement:
    return Requirement(key=key, units=units, what=key, tier=tier)


def _digest_via_adapt(assay_key: str, requirements) -> str:
    return RecordedResolver().resolve(assay_key, requirements).requirement_version


def _digest_via_handoff(assay_key: str, requirements) -> str:
    return resolution_set_from_handoff(
        _handoff(), assay_key, requirements
    ).requirement_version


# --- 1. one digest, three callers --------------------------------------------


def test_the_three_callers_share_one_implementation():
    """The cheapest form of the check, and the one that catches a re-divergence
    at the moment it is written rather than at the moment it matters.

    A fourth copy would still be caught by the tests below, but only for key
    lists those tests happen to try. This one fails as soon as any of the three
    stops importing the shared function."""
    assert handoff_module.requirement_digest is requirement_digest
    from refute import adapt, requirements

    assert adapt.requirement_digest is requirement_digest
    assert requirements.requirement_digest is requirement_digest
    assert requirements.VERSION_CHARS == digest.VERSION_CHARS


@pytest.mark.parametrize("key", KEYS)
def test_all_three_digest_paths_agree_for_one_key_list(key: str):
    """The property that actually has to hold. Same protocol, same requirement
    set, three routes to the version recorded on the answer - and any two of
    them disagreeing makes the pipeline report every fresh run as stale."""
    protocol = get(key)
    reqs = requirements_for(protocol)

    from_registry = requirement_version(protocol)
    assert _digest_via_adapt(key, reqs) == from_registry
    assert _digest_via_handoff(key, reqs) == from_registry
    assert from_registry == requirement_digest(
        c.name for c in protocol.all_constants()
    )
    assert len(from_registry) == VERSION_CHARS


def test_the_two_list_paths_agree_on_a_list_no_protocol_declares():
    """The registry cases could agree by both being right about the registry.
    This one has no protocol behind it at all, so the only thing that can make
    the two agree is the same algorithm over the same keys."""
    invented = (
        _requirement("z_last"),
        _requirement("a_first"),
        _requirement("m_middle"),
        _requirement("alpha", "probability", "tier0"),
    )
    expected = requirement_digest(("z_last", "a_first", "m_middle"))

    assert _digest_via_adapt("fibrin_contracture", invented) == expected
    assert _digest_via_handoff("fibrin_contracture", invented) == expected
    assert expected not in {requirement_version(p) for p in REGISTRY.values()}


def test_the_digest_ignores_order_and_units_but_not_keys():
    """What the digest is over, checked on both list paths at once. Reordering a
    declaration or rewording a unit string must not invalidate every stored
    answer; adding a key must."""
    base = (_requirement("b", "um"), _requirement("a", "%"))
    reshuffled = (_requirement("a", "fraction"), _requirement("b", "AU"))
    grown = base + (_requirement("c"),)

    for route in (_digest_via_adapt, _digest_via_handoff):
        assert route("fibrin_contracture", base) == route(
            "fibrin_contracture", reshuffled
        )
        assert route("fibrin_contracture", base) != route("fibrin_contracture", grown)


def test_tier0_is_in_no_protocols_version_on_either_list_path():
    """Tier 0 is assay-blind and belongs to no protocol's requirement set, so
    asking for it alongside tier 1 must not change which set an answer claims to
    be total over. Pinned on both paths because both filter it out themselves."""
    protocol = get("traction_force")
    for route in (_digest_via_adapt, _digest_via_handoff):
        assert route("traction_force", requirements_for(protocol)) == route(
            "traction_force", tier1_needs(protocol)
        )


# --- 2. the published unit strings -------------------------------------------


def _declared_units() -> set[tuple[str, str, str]]:
    """Every (tier, key, units) triple, read off the registry directly.

    Deliberately a second implementation, in the same spirit as
    `tests/test_vocabulary.py`: a traceability check that asks the module to
    confirm itself only proves the module is deterministic.
    """
    declared = {
        ("tier1", c.name, c.units)
        for protocol in REGISTRY.values()
        for c in protocol.all_constants()
    }
    return declared | {("tier0", r.key, r.units) for r in tier0_needs()}


def test_the_contract_covers_every_requirement_key_and_invents_none():
    published = {(c.tier, c.key, c.units) for c in unit_contract()}
    assert published == _declared_units()


def test_every_published_record_names_who_declares_it():
    """A tier-1 string with no protocol behind it would be a string somebody
    typed. Tier 0 is the deliberate exception: it is assay-blind, and an empty
    protocol list is how "every design" is distinguished from "this one"."""
    for record in unit_contract():
        if record.tier == "tier1":
            assert record.protocols, record.key
            for key in record.protocols:
                assert (record.key, record.units) in {
                    (c.name, c.units) for c in get(key).all_constants()
                }
        else:
            assert record.protocols == ()


def _with_units(protocol: AssayProtocol, units: str) -> AssayProtocol:
    """A copy of `protocol` whose readout constants are declared in `units`."""
    readout = dataclasses.replace(
        protocol.readout,
        constants=tuple(
            dataclasses.replace(c, units=units) for c in protocol.readout.constants
        ),
    )
    return dataclasses.replace(protocol, readout=readout)


def test_the_published_strings_follow_the_registry_rather_than_a_list_here():
    """The claim the whole report rests on. If the strings were transcribed they
    would keep saying "Ashcroft" after the protocol stopped saying it, and the
    contract would be a document that quietly disagrees with the matcher."""
    protocol = get("bleomycin_lung")
    doctored = _with_units(protocol, "furlongs per fortnight")

    published = {c.units for c in unit_contract([doctored]) if c.tier == "tier1"}
    assert "furlongs per fortnight" in published
    assert "Ashcroft" not in published
    assert "furlongs per fortnight" in units_contract_report([doctored])
    assert "Ashcroft" in units_contract_report([protocol])


def test_the_report_names_every_key_and_prints_its_string():
    report = units_contract_report()
    for record in unit_contract():
        assert record.key in report, record.key
        assert record.units in report, record.units


# --- 3. the published contract is the enforced one ---------------------------

# Any units at all: what the readout-relative pair is filled with in the tests
# below. The published contract says to emit the readout's real units and the
# same string for both, which is what this stands in for.
_READOUT_STAND_IN = "um"


def _finding_for(record: UnitContract, value: float = 1.0) -> Finding:
    return Finding(
        statement=record.key,
        kind="measures",
        provenance="literature",
        source="10.0000/example",
        quote="as published",
        value=value,
        units=_READOUT_STAND_IN if record.any_units_accepted else record.units,
    )


@pytest.mark.parametrize("key", KEYS)
def test_findings_that_use_the_published_strings_resolve_completely(key: str):
    """The test the contract exists for. Emit exactly what the report says, for
    every key of one protocol, and every key comes back resolved.

    Coverage is what the gate routes on, so a contract that is right about the
    strings and wrong about anything else still shows up here as a gap."""
    protocol = get(key)
    reqs = requirements_for(protocol)
    published = {c.key: c for c in unit_contract([protocol])}

    resolutions = resolutions_from_findings(
        [_finding_for(published[req.key]) for req in reqs], reqs
    )

    unresolved = sorted(k for k, r in resolutions.items() if not r.resolved)
    assert not unresolved, f"{key}: {unresolved} did not resolve"


@pytest.mark.parametrize(
    "declared,emitted",
    [
        ("um", "µm"),
        ("um", "microns"),
        ("%", "percent"),
        ("fraction", "probability"),
        ("h", "hours"),
        ("x", "fold"),
        ("-", "dimensionless"),
        ("-", "unitless"),
    ],
)
def test_a_plausible_synonym_is_a_units_mismatch_and_not_a_match(
    declared: str, emitted: str
):
    """Every pair here is one somebody would have put in a synonym table, and
    the module refuses to hold that table. The published contract is therefore
    exact, and this is what "exact" costs - which is the reason it is published
    rather than left to be discovered one finding at a time."""
    req = _requirement("measurement_cv", declared)
    finding = Finding(
        statement="measurement_cv",
        kind="measures",
        provenance="literature",
        source="10.0000/example",
        value=0.2,
        units=emitted,
    )

    resolved = resolutions_from_findings([finding], [req])["measurement_cv"]
    assert not resolved.resolved
    assert resolved.reason is BlockedReason.UNITS_MISMATCH


def test_the_published_normalisation_is_the_one_the_matcher_applies():
    """Not "matches the one the matcher applies" - is it. The report calls this
    function to produce its own worked examples, so the rule it documents cannot
    drift from the rule enforced."""
    from refute import vocabulary

    assert vocabulary.normalise_units is handoff_module.normalise_units
    assert normalise_units("  Fraction ") == "fraction"
    assert normalise_units("AU  per % strain") == "au per % strain"
    assert normalise_units("um") != normalise_units("µm")


def test_what_the_normalisation_covers_really_is_survivable():
    """The other half of publishing the rule: a difference the report says is
    normalised away has to actually be normalised away, or the contract
    understates what layer 1 has to get right."""
    req = _requirement("measurement_cv", "fraction")
    finding = Finding(
        statement="measurement_cv",
        kind="measures",
        provenance="literature",
        source="10.0000/example",
        value=0.2,
        units="  FRACTION ",
    )
    assert resolutions_from_findings([finding], [req])["measurement_cv"].resolved


def test_the_readout_relative_pair_is_flagged_as_such_and_nothing_else_is():
    """The one exception in the contract, and it is not a synonym: `effect_size`
    and `within_arm_sd` are declared relative to the readout because the
    arithmetic uses only their ratio. Anything else claiming that licence would
    be a requirement whose units nobody checks."""
    unpinned = {c.key for c in unit_contract() if c.any_units_accepted}
    assert unpinned == {"effect_size", "within_arm_sd"}


def test_the_report_states_that_the_unpinned_pair_must_still_agree():
    """The licence is about absolute units, not about consistency. A report that
    published the first half without the second would license a difference in
    microns over a spread in pascals, which is not a standardised effect size
    and produces a power figure that looks like a calculation."""
    report = units_contract_report()
    assert "any units accepted" in report
    assert "agree with each other" in report

    reqs = tuple(r for r in tier0_needs() if r.key in {"effect_size", "within_arm_sd"})
    findings = [
        Finding(
            statement="effect_size",
            kind="measures",
            provenance="literature",
            source="10.0000/example",
            value=2.0,
            units="um",
        ),
        Finding(
            statement="within_arm_sd",
            kind="measures",
            provenance="literature",
            source="10.0000/example",
            value=1.0,
            units="pJ",
        ),
    ]
    resolutions = resolutions_from_findings(findings, reqs)
    assert not any(r.resolved for r in resolutions.values())


def test_a_key_declared_with_two_unit_strings_is_reported_as_two_lines():
    """Constant names are shared across protocols, so one name meaning two
    quantities is a live possibility rather than a hypothetical. Collapsing it
    to one line would publish whichever protocol was read first."""
    protocol = get("traction_force")
    doctored = _with_units(protocol, "furlongs per fortnight")
    doctored = dataclasses.replace(doctored, key="traction_force_metric")

    records = [
        c for c in unit_contract([protocol, doctored]) if c.key == "baseline_strain_energy"
    ]
    assert {c.units for c in records} == {"pJ", "furlongs per fortnight"}

    report = units_contract_report([protocol, doctored])
    assert "TWO UNIT STRINGS" in report


def test_the_two_reports_are_not_the_same_document():
    """`coverage_report` reports an agreement that has not happened;
    `units_contract_report` reports a rule already being enforced. Reading the
    second as unagreed would be reason enough not to comply with it."""
    from refute.vocabulary import coverage_report

    assert "NOT AGREED" in coverage_report()
    assert "ENFORCED" in units_contract_report()


def test_the_registry_declares_no_unit_string_that_is_only_whitespace():
    """A requirement whose units normalise to nothing cannot be matched by
    anything a `Finding` may legally carry, because `Finding` refuses a value
    with blank units. It would be a key with a permanent, silent zero."""
    for record in unit_contract():
        assert normalise_units(record.units), record.key


def test_every_constant_in_the_registry_reaches_the_contract():
    """The other direction: a protocol the report forgot looks complete and
    answers wrongly for the assay it omitted, which is harder to notice than an
    extra line."""
    covered = {c.key for c in unit_contract() if c.tier == "tier1"}
    for protocol in REGISTRY.values():
        for constant in protocol.all_constants():
            assert constant.name in covered, f"{protocol.key}:{constant.name}"
    assert {c.key for c in unit_contract() if c.tier == "tier0"} == {
        r.key for r in tier0_needs()
    }


def test_a_constant_is_a_frozen_record_so_the_doctored_protocols_are_copies():
    """Guard on the tests above rather than on the module: `dataclasses.replace`
    on a mutable protocol would edit the registry other tests read."""
    assert Constant.__dataclass_params__.frozen
    assert get("bleomycin_lung").readout.constants[0].units == "Ashcroft"
