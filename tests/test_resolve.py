"""The resolution contract, and the fixtures that stand in for a real resolver.

Two things are protected here.

**Silence is unrepresentable.** `Resolution` refuses to exist unless it either
carries a value or says why it does not, and it refuses the reasons that would
be indistinguishable from each other downstream - a derived number with no
stated assumption reads as a measured one, an assumed number with no range
cannot be tested for sensitivity, and NOT_REPORTED without a query is an
assertion about the literature made without listening to it. Each of those is a
`ValueError` rather than a lint, because each would otherwise surface as a
confident verdict rather than as a bug.

**The gate routes on structure, never on numbers.** Every fixture in
`cases/fixtures/` is checked to load, to validate, and - in
`test_route_is_independent_of_every_value` - to route identically when every
value in it is replaced with a different one. That is the property the whole
split rests on: it is what lets the downstream half be finished, and tested,
before any resolver exists to feed it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from refute.assays import get
from refute.assays.evidence import BlockedReason
from refute.requirements import tier0_needs, tier1_needs
from refute.resolve import (
    FixtureResolver,
    Provenance,
    Requirement,
    Resolution,
    ResolutionSet,
    resolution_set_from_dict,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "cases" / "fixtures"
FIXTURES = sorted(FIXTURE_DIR.glob("*.json"))

# The fixtures are all written against the one calibrated protocol, so that the
# keys in them are constants that really exist rather than names invented to
# make a test pass.
ASSAY = "fibrin_contracture"


def _ids(paths):
    return [p.name for p in paths]


# --- Resolution: neither, both, and the three that would read as measured ---


def test_a_resolution_that_says_nothing_is_refused():
    """The type exists to make silence impossible. An entry with no value and
    no reason is silence wearing the shape of an answer."""
    with pytest.raises(ValueError, match="must be resolved or carry a blocked"):
        Resolution(quantity="lysis_shape")


def test_a_resolution_cannot_be_both_resolved_and_blocked():
    """Downstream reads `resolved` and `reason` as a partition. If both can be
    set, every consumer has to pick one to trust, and they will not all pick the
    same one."""
    with pytest.raises(ValueError, match="cannot be both resolved and blocked"):
        Resolution(
            quantity="lysis_shape",
            value=4.1,
            provenance=Provenance.MEASURED,
            source="cases/exp4/PROVENANCE.md",
            reason=BlockedReason.NOT_YET_SEARCHED,
        )


def test_a_value_needs_a_provenance_and_a_source():
    """A number with no origin is worth less than no number, because it will be
    used."""
    with pytest.raises(ValueError, match="needs a provenance"):
        Resolution(quantity="lysis_shape", value=4.1, source="somewhere")
    with pytest.raises(ValueError, match="needs a source"):
        Resolution(
            quantity="lysis_shape", value=4.1, provenance=Provenance.MEASURED
        )


def test_derived_without_an_assumption_is_refused():
    """A derived value is a calculation somebody made. Without the assumption it
    rests on it is indistinguishable from a measurement, which is precisely the
    confusion this project is about."""
    with pytest.raises(ValueError, match="must state its assumption"):
        Resolution(
            quantity="contraction_tau_h",
            value=8.37,
            provenance=Provenance.DERIVED,
            source="cases/exp4/PROVENANCE.md",
        )


def test_derived_with_an_assumption_is_accepted():
    r = Resolution(
        quantity="contraction_tau_h",
        value=8.37,
        provenance=Provenance.DERIVED,
        source="cases/exp4/PROVENANCE.md",
        assumption="single-exponential approach to plateau",
    )
    assert r.resolved
    assert not r.blocks_tier1


def test_assumed_without_a_plausible_range_is_refused():
    """An assumption with no range cannot be swept, so its verdict cannot be
    tested for sensitivity - and an untestable assumption is reported as though
    it were a finding."""
    with pytest.raises(ValueError, match="must carry a plausible"):
        Resolution(
            quantity="aprotinin_hazard_scale",
            value=4.0,
            provenance=Provenance.ASSUMED,
            source="FIXTURE:assumed",
        )


def test_not_reported_without_a_query_is_refused():
    """NOT_REPORTED is the load-bearing claim of this project: that a class of
    constants is systematically absent from the literature. It may only be made
    by something that searched and can show the search."""
    with pytest.raises(ValueError, match="NOT_REPORTED is a claim"):
        Resolution(quantity="lysis_shape", reason=BlockedReason.NOT_REPORTED)


def test_not_yet_searched_needs_no_query():
    """The honest default costs nothing to state, or nobody would state it."""
    r = Resolution(quantity="lysis_shape", reason=BlockedReason.NOT_YET_SEARCHED)
    assert not r.resolved
    assert r.blocks_tier1


def test_assumed_is_not_evidence_but_every_other_provenance_is():
    assert not Provenance.ASSUMED.is_evidence
    for p in Provenance:
        if p is not Provenance.ASSUMED:
            assert p.is_evidence, p


def test_requirement_rejects_an_unknown_tier():
    with pytest.raises(ValueError, match="tier must be"):
        Requirement(key="x", units="-", what="something", tier="tier2")


# --- CONTEXT_DEPENDENT: ill-posed is not absent ----------------------------


def test_context_dependent_does_not_block_tier1():
    """The distinction most likely to be collapsed by accident. An ill-posed
    scalar becomes a swept range and the verdict is reported as sensitive to it.
    An absent one stops the twin. Collapsing them either withholds a verdict
    that could have been given, or gives one that should have been ranged."""
    ill_posed = Resolution(
        quantity="aprotinin_hazard_scale", reason=BlockedReason.CONTEXT_DEPENDENT
    )
    absent = Resolution(
        quantity="aprotinin_hazard_scale",
        reason=BlockedReason.NOT_REPORTED,
        queries_run=("aprotinin fibrin lysis dose response",),
    )
    assert not ill_posed.blocks_tier1
    assert absent.blocks_tier1


def test_context_dependent_is_swept_but_not_missing():
    rs = ResolutionSet(
        assay_key=ASSAY,
        requirement_version="test",
        resolutions={
            "aprotinin_hazard_scale": Resolution(
                quantity="aprotinin_hazard_scale",
                reason=BlockedReason.CONTEXT_DEPENDENT,
            )
        },
    )
    needs = ["aprotinin_hazard_scale"]
    assert rs.missing(needs) == []
    assert rs.covers(needs)
    assert rs.swept(needs) == ["aprotinin_hazard_scale"]


# --- completeness ----------------------------------------------------------


def _set(**resolutions: Resolution) -> ResolutionSet:
    return ResolutionSet(
        assay_key=ASSAY, requirement_version="test", resolutions=resolutions
    )


def test_complete_is_false_exactly_when_something_is_unsearched():
    """Routing an incomplete set emits 'not answerable at this scale' for an
    experiment that is merely unsearched, which is the most damaging wrong
    output this system can produce."""
    searched = _set(
        lysis_shape=Resolution(
            quantity="lysis_shape",
            reason=BlockedReason.NOT_REPORTED,
            queries_run=("fibrin gel lysis Weibull shape",),
        )
    )
    assert searched.complete
    assert searched.unsearched() == []

    unsearched = _set(
        lysis_shape=Resolution(
            quantity="lysis_shape", reason=BlockedReason.NOT_YET_SEARCHED
        )
    )
    assert not unsearched.complete
    assert unsearched.unsearched() == ["lysis_shape"]


def test_every_other_blocked_reason_leaves_the_set_complete():
    for reason in BlockedReason:
        if reason is BlockedReason.NOT_YET_SEARCHED:
            continue
        queries = ("a query",) if reason is BlockedReason.NOT_REPORTED else ()
        rs = _set(
            k=Resolution(quantity="k", reason=reason, queries_run=queries)
        )
        assert rs.complete, reason


def test_an_absent_key_counts_as_missing():
    """Totality is the invariant; `missing` is what catches a set that broke
    it. A key that is not there routes as a gap, never as satisfied."""
    assert _set().missing(["lysis_shape"]) == ["lysis_shape"]


# --- the fixtures ----------------------------------------------------------


def test_there_are_fixtures_to_check():
    """A glob that silently matches nothing turns every test below into a
    no-op that passes."""
    assert FIXTURES, f"no fixtures found in {FIXTURE_DIR}"


@pytest.mark.parametrize("path", FIXTURES, ids=_ids(FIXTURES))
def test_every_fixture_loads_and_validates(path):
    """These files are simultaneously the gate's test inputs and the resolver's
    output specification. A fixture that would not survive the invariants does
    not describe a legal resolver output, and would quietly become a bad input
    for whoever is building the gate against it."""
    rs = resolution_set_from_dict(json.loads(path.read_text()))
    assert rs.assay_key == ASSAY
    assert rs.resolutions, f"{path.name} resolves nothing at all"
    for key, r in rs.resolutions.items():
        assert r.quantity == key
        assert r.resolved or r.reason is not None


@pytest.mark.parametrize("path", FIXTURES, ids=_ids(FIXTURES))
def test_every_fixture_is_total_over_the_registry(path):
    """Partiality is unrepresentable, so a fixture missing a key is not a
    smaller test case - it is an illegal one."""
    rs = FixtureResolver(path).resolve(ASSAY, tier1_needs(get(ASSAY)))
    required = {r.key for r in tier1_needs(get(ASSAY))}
    assert required <= set(rs.resolutions), (
        f"{path.name} is not total: missing "
        f"{sorted(required - set(rs.resolutions))}"
    )
    extra = set(rs.resolutions) - required
    assert extra <= {r.key for r in tier0_needs()}, (
        f"{path.name} answers keys nothing asked for: {sorted(extra)}"
    )


@pytest.mark.parametrize("path", FIXTURES, ids=_ids(FIXTURES))
def test_every_blocked_entry_in_a_fixture_carries_a_null_value(path):
    """The negative half of the same property: a blocked entry must not smuggle
    a number in beside its reason."""
    raw = json.loads(path.read_text())
    for key, entry in raw["resolutions"].items():
        if entry.get("reason"):
            assert entry.get("value") is None, f"{path.name}:{key}"


@pytest.mark.parametrize("path", FIXTURES, ids=_ids(FIXTURES))
def test_route_is_independent_of_every_value(path):
    """The property the whole upstream/downstream split rests on.

    Replace every resolved number with a different one and the routing summary
    must not move. If it ever does, some consumer has started reading a value
    the gate is not entitled to read, and the hand-written test matrix stops
    being a valid description of the system.
    """
    raw = json.loads(path.read_text())
    perturbed = json.loads(json.dumps(raw))
    for entry in perturbed["resolutions"].values():
        if entry.get("value") is not None:
            entry["value"] = entry["value"] * 3.0 + 7.0
        if entry.get("plausible_range"):
            lo, hi = entry["plausible_range"]
            entry["plausible_range"] = [lo * 3.0 + 7.0, hi * 3.0 + 7.0]

    needs = [r.key for r in tier1_needs(get(ASSAY))]
    t0 = [r.key for r in tier0_needs()]

    def route(d):
        rs = resolution_set_from_dict(d)
        return (
            rs.complete,
            rs.missing(needs),
            rs.unsearched(),
            rs.assumed(needs),
            rs.swept(needs),
            rs.over_assumed(needs),
            rs.covers(t0),
            rs.unmodelled_mentions,
        )

    assert route(raw) == route(perturbed)


def test_the_seven_routing_shapes_are_all_present():
    """Each fixture exists to pin one route. If two of them ever collapse onto
    the same routing summary, one of them has stopped testing anything."""
    needs = [r.key for r in tier1_needs(get(ASSAY))]
    t0 = [r.key for r in tier0_needs()]
    shapes = {}
    for path in FIXTURES:
        rs = FixtureResolver(path).resolve(ASSAY, ())
        shapes[path.stem] = (
            rs.complete,
            bool(rs.missing(needs)),
            bool(rs.swept(needs)),
            rs.over_assumed(needs),
            rs.covers(t0),
            bool(rs.unmodelled_mentions),
        )
    assert len(set(shapes.values())) == len(shapes), shapes


def test_full_coverage_fixture_needs_no_sweep_and_no_fallback():
    needs = [r.key for r in tier1_needs(get(ASSAY))]
    rs = FixtureResolver(FIXTURE_DIR / "full_coverage.json").resolve(ASSAY, ())
    assert rs.complete
    assert rs.covers(needs)
    assert rs.swept(needs) == []
    assert not rs.over_assumed(needs)


def test_tier1_gaps_fixture_falls_back_to_tier0():
    """The case the fallback exists for: the failure constants are absent,
    which is the survivorship class, while the four quantities literature
    actually prints are in hand."""
    rs = FixtureResolver(FIXTURE_DIR / "tier1_gaps_tier0_ok.json").resolve(ASSAY, ())
    tier1 = [r.key for r in tier1_needs(get(ASSAY))]
    tier0 = [r.key for r in tier0_needs()]
    assert rs.complete
    assert rs.missing(tier1)
    assert rs.covers(tier0)
    for key in rs.missing(tier1):
        assert rs.resolutions[key].reason is BlockedReason.NOT_REPORTED
        assert rs.resolutions[key].queries_run


def test_all_blocked_fixture_has_no_fallback_either():
    rs = FixtureResolver(FIXTURE_DIR / "all_blocked.json").resolve(ASSAY, ())
    tier1 = [r.key for r in tier1_needs(get(ASSAY))]
    assert rs.complete, "all_blocked asserts a search happened; it is not unsearched"
    assert rs.missing(tier1) == sorted(tier1)
    assert not rs.covers([r.key for r in tier0_needs()])
    assert all(not r.resolved for r in rs.resolutions.values())


def test_one_unsearched_fixture_is_the_only_incomplete_one():
    incomplete = [
        p.stem
        for p in FIXTURES
        if not FixtureResolver(p).resolve(ASSAY, ()).complete
    ]
    assert incomplete == ["one_unsearched"]


def test_over_assumed_fixture_crosses_the_threshold_with_ranges():
    rs = FixtureResolver(FIXTURE_DIR / "over_assumed.json").resolve(ASSAY, ())
    needs = [r.key for r in tier1_needs(get(ASSAY))]
    assert rs.over_assumed(needs)
    for key in rs.assumed(needs):
        assert rs.resolutions[key].plausible_range is not None, key


# --- FixtureResolver -------------------------------------------------------


@pytest.mark.parametrize("path", FIXTURES, ids=_ids(FIXTURES))
def test_fixture_resolver_round_trips(path):
    """Reading through the resolver must give the same object as reading the
    JSON directly, or the resolver is doing something the fixture does not
    describe."""
    direct = resolution_set_from_dict(json.loads(path.read_text()))
    replayed = FixtureResolver(path).resolve(ASSAY, tier1_needs(get(ASSAY)))
    assert replayed == direct


def test_fixture_resolver_refuses_the_wrong_assay():
    """Fixtures share a key space - `measurement_cv` means something different
    in three protocols. Replaying one assay's answers against another would
    validate, and be wrong."""
    resolver = FixtureResolver(FIXTURE_DIR / "full_coverage.json")
    with pytest.raises(ValueError, match="fixture is for assay"):
        resolver.resolve("bleomycin_lung", tier1_needs(get("bleomycin_lung")))


def test_fixture_resolver_ignores_the_requirements_it_is_handed():
    """Deliberate, and worth pinning: a resolver that filtered its output to the
    requirements it was given could never under-answer, and under-answering is
    the thing the gate most needs to see."""
    resolver = FixtureResolver(FIXTURE_DIR / "all_blocked.json")
    with_needs = resolver.resolve(ASSAY, tier1_needs(get(ASSAY)))
    without = resolver.resolve(ASSAY, ())
    assert with_needs == without
