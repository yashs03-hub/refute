"""The layer-1 handoff, and the four ways a crossing between teams goes wrong.

`refute/handoff.py` is the only place the two layers touch. Everything upstream
of it is another team's process and everything downstream is a power
calculation, which means a defect here is a wrong number wearing the clothes of
a calculation - so the tests are shaped around the ways it could be quietly
wrong rather than around the cases that obviously work.

**By matching the wrong thing.** A `Finding` is a sentence about biology and a
`Resolution` is keyed to a named constant. Every match is a guess, and the two
errors are not symmetric: an unmatched finding costs coverage, a wrongly matched
one feeds a wrong number into a power calculation and nothing downstream can
tell. So the mismatches are pinned individually - wrong units, two keys in one
statement, two findings for one key, an effect and a spread in different units -
and each of them must produce a blocked key rather than a number.

**By claiming a search nobody ran.** "Looked and it is not there" and "have not
looked" support opposite designs. `OpenItem` refuses to be constructed with the
strong claim and no query, and the adapter never invents one.

**By losing a provenance tier.** DERIVED without its assumption is a
calculation presenting as a measurement; ASSUMED without a range is a stand-in
that cannot be swept. Both are refused, and the refusal is checked to be a
refusal rather than a silent downgrade to a tier that converts cleanly.

**By being satisfied with nothing.** Every test above passes for an adapter that
answers NOT_YET_SEARCHED to everything - it would be total, it would invent no
queries, and it would never be wrong out loud. Two tests exist to fail that
adapter: a handoff of reported quantities has to reach TIER0 through the real
gate, and a handoff that covers a protocol has to reach TIER1. The first is the
one that matters, because it is the proof that the contract gap in §5.2 - layer
1 "does not estimate an effect size", and effect size is a tier-0 need - is
closed rather than papered over.
"""

from __future__ import annotations

import dataclasses
import inspect

import pytest

from refute import handoff as handoff_module
from refute.assays import get
from refute.design import EXPERIMENT_4_AS_RUN
from refute.gate import Route, route_design
from refute.handoff import (
    HANDOFF_FILLABLE_TIER0,
    PROVENANCE_TIERS,
    Finding,
    GapReason,
    Handoff,
    OpenItem,
    crosses_as_report,
    resolution_set_from_handoff,
    resolutions_from_findings,
    tier0_needs_a_handoff_can_fill,
)
from refute.requirements import requirement_version, tier0_needs, tier1_needs
from refute.resolve import (
    TIER0_NEEDS,
    BlockedReason,
    Provenance,
    Requirement,
    Resolution,
)

QUERY = "fibrin gel lysis Weibull shape methods"

# One residual, reused. Every legal `Handoff` needs one - a handoff without a
# residual is the terminal state that does not hand off - and none of the
# matching tests are about the residual itself.
RESIDUAL = (
    OpenItem(
        statement="whether aprotinin preserves the contracture window at 96 h",
        why="needs_new_data",
    ),
)


def _req(key: str, units: str = "-", tier: str = "tier1") -> Requirement:
    return Requirement(key=key, units=units, what="a quantity", tier=tier)


def _finding(statement: str, **kw) -> Finding:
    fields = {
        "kind": "measures",
        "provenance": "literature",
        "source": "10.1186/s42490-019-0014-z",
        "quote": "the sentence the number came from",
    }
    fields.update(kw)
    return Finding(statement=statement, **fields)


def _handoff(**kw) -> Handoff:
    fields = {
        "question": "are these gels dying by fibrinolysis?",
        "hypothesis": "contraction is lost to lysis before the endpoint",
        "residual": RESIDUAL,
    }
    fields.update(kw)
    return Handoff(**fields)


# --- the shared types --------------------------------------------------------


def test_the_vocabularies_mirror_the_resolve_layer_exactly():
    """The cost of the type block being importable without `refute`.

    `GapReason` and `PROVENANCE_TIERS` are written out as literals so that half
    of the module depends on nothing. Two copies of an enumeration drift within
    hours and the drift is invisible until something starts failing quietly,
    which is the failure the single-definition rule exists to prevent - so the
    copies are pinned here instead. It has already earned its keep once: the
    resolve layer gained NOT_SUPPLIED while this module was being written, and
    this is what said so, rather than the adapter silently mapping the new
    reason onto the nearest old one.
    """
    assert {r.value for r in GapReason} == {r.value for r in BlockedReason}
    assert PROVENANCE_TIERS == tuple(p.value for p in Provenance)
    for gap in GapReason:
        assert (
            gap.is_a_claim_about_the_literature
            is BlockedReason(gap.value).is_a_claim_about_the_literature
        )


def test_the_shared_types_name_nothing_from_this_package():
    """Property 1: one definition, in one place, imported by both.

    We cannot make layer 1 import this file, so the most we can do is leave
    nothing in the way - a type block that named `Resolution` or `Provenance`
    would drag an assay registry, a design spec and a simulator behind it, and
    the other team would copy the four dataclasses instead. Checked on the
    annotations and on the source above the divider, because the property is
    about what the file imports and not about what it happens to be doing.
    """
    forbidden = (
        "Resolution",
        "ResolutionSet",
        "Requirement",
        "Provenance",
        "BlockedReason",
        "AssayProtocol",
        "DesignSpec",
        "ExperimentTwin",
    )
    for cls in (Finding, OpenItem, Handoff):
        for field in dataclasses.fields(cls):
            assert not any(name in str(field.type) for name in forbidden), (
                f"{cls.__name__}.{field.name} is annotated {field.type!r}, which "
                "ties the shared type block to this package"
            )

    above, divider, below = inspect.getsource(handoff_module).partition(
        "# Below here is layer 2's."
    )
    assert divider and below, "the divider that carries this promise has moved"
    for line in above.splitlines():
        assert not line.startswith(("from .", "from refute", "import refute")), (
            f"{line!r} sits above the divider, so the shared types are no longer "
            "importable by a process that has never heard of refute"
        )


def test_an_open_item_claiming_absence_without_a_query_is_refused():
    """The invariant the spec's `searched: bool` states and does not enforce.

    "We searched and it is not published" is a claim about publishing practice
    and it is the claim this whole project rests on. Made without the query that
    came back empty it is indistinguishable from "nobody has looked", and layer
    2 will design an experiment to answer a question the literature already
    settled. `Resolution` and `Blocked` both refuse it; so does this.
    """
    with pytest.raises(ValueError, match="requires having listened"):
        OpenItem(
            statement="the lysis_shape parameter",
            why="not_in_literature",
            searched=True,
        )

    # The reachable defeat of a naive check: whitespace is truthy and proves
    # nothing. Trimmed away, so the invariant sees an empty query and holds.
    with pytest.raises(ValueError, match="requires having listened"):
        OpenItem(
            statement="the lysis_shape parameter",
            why="not_in_literature",
            searched=True,
            queries_run=("   ",),
        )


def test_a_search_that_never_ran_cannot_claim_the_literature_is_silent():
    """The other direction of the same rule, and scoped the way the resolve
    layer scopes it: only NOT_REPORTED is a claim about what gets published, so
    it is the only reason `searched=False` cannot carry. The others are
    properties of the constant, the instrument or the experimenter, and need no
    corpus to establish - requiring a search for them would push an honest
    record toward a fabricated one."""
    with pytest.raises(ValueError, match="searched=False"):
        OpenItem(
            statement="the lysis_shape parameter",
            why="not_in_literature",
            searched=False,
            queries_run=(QUERY,),
            reason=GapReason.NOT_REPORTED,
        )

    unsearchable = OpenItem(
        statement="within_arm_sd for this plate",
        why="needs_new_data",
        searched=False,
        reason=GapReason.NOT_SUPPLIED,
    )
    assert unsearchable.reason is GapReason.NOT_SUPPLIED


def test_the_reason_is_inferred_so_nothing_upstream_has_to_change():
    """`searched` is kept from the spec's shape and infers the typed reason, so
    a layer-1 emitter that has never heard of `GapReason` still produces records
    that route correctly. The two `why` values that are not claims about the
    literature under-claim deliberately: NOT_YET_SEARCHED routes "not ready",
    never a refusal, and guessing CONTEXT_DEPENDENT for a contested quantity
    would be worse than useless, because that reason does not block a twin.
    """
    never = OpenItem(statement="p_cast_failure", why="not_in_literature")
    assert never.reason is GapReason.NOT_YET_SEARCHED

    looked = OpenItem(
        statement="p_cast_failure",
        why="not_in_literature",
        searched=True,
        queries_run=(QUERY,),
    )
    assert looked.reason is GapReason.NOT_REPORTED

    contested = OpenItem(
        statement="p_cast_failure",
        why="contested",
        searched=True,
        queries_run=(QUERY,),
    )
    assert contested.reason is GapReason.NOT_YET_SEARCHED


def test_a_quantity_without_units_is_refused_at_construction():
    """Property 3: units are a field on every quantity, not a convention. A
    number whose units are implied is a number that will be misread, once,
    quietly, by an arithmetic with no way to notice - so it is not
    representable. Prose carries no number and needs none."""
    with pytest.raises(ValueError, match="units"):
        _finding("effect_size was 4.7", value=4.7)

    assert _finding("cluster 4 is not macrophages", kind="rules_out").units == ""


def test_a_handoff_with_no_residual_is_not_a_handoff():
    """Layer 1 has two terminal states: the question is answered, in which case
    it stops and hands nothing over; or something remains that only new data can
    settle, and that residual is the brief. A handoff with an empty residual is
    the first wearing the second's clothes, and the only thing layer 2 could do
    with it is invent a question."""
    with pytest.raises(ValueError, match="residual"):
        Handoff(question="q", hypothesis="h", residual=())


# --- Finding -> Resolution ---------------------------------------------------


def test_a_reported_quantity_round_trips_with_its_words_intact():
    """The source and the sentence are what make the number checkable. A value
    that arrives without them is a value somebody will use and nobody can
    audit, which is the same defect as no provenance at all."""
    finding = _finding(
        "tgfb_fold_change of 4.7 in the TGF-beta arm",
        scope="human dermal fibroblasts, 2D, 72 h",
        value=4.7,
        units="x",
        origin_event="ev_012",
    )
    resolved = resolutions_from_findings([finding], [_req("tgfb_fold_change", "x")])

    r = resolved["tgfb_fold_change"]
    assert r.value == 4.7
    assert r.units == "x"
    assert r.provenance is Provenance.LITERATURE
    assert r.source == finding.source
    assert r.quote == finding.quote
    assert r.resolved and not r.blocks_tier1


def test_the_set_is_total_over_the_requirements():
    """Partiality is unrepresentable, for the reason `resolve.py` gives: a
    missing key and a blocked key route differently, and only one of them reads
    as work still to do. A key no finding mentions is NOT_YET_SEARCHED, which is
    also the honest answer - a handoff that never named it did not look."""
    requirements = [
        _req("tgfb_fold_change", "x"),
        _req("p_cast_failure", "probability"),
        _req("lysis_shape", "-"),
    ]
    resolved = resolutions_from_findings(
        [_finding("tgfb_fold_change of 4.7", value=4.7, units="x")], requirements
    )

    assert set(resolved) == {r.key for r in requirements}
    for key, r in resolved.items():
        assert r.quantity == key
        assert r.resolved or r.reason is not None
    assert resolved["lysis_shape"].reason is BlockedReason.NOT_YET_SEARCHED


def test_a_units_mismatch_does_not_match():
    """The conservative half of the design, and the one with teeth. A gel that
    reports its contraction in millimetres does not answer a requirement stated
    as a percentage, and converting between them is a judgement nobody made.
    UNITS_MISMATCH rather than NOT_YET_SEARCHED, because layer 1 did look and
    did report something - the gate can hand that back for one derivation
    attempt, which it cannot do with silence.
    """
    resolved = resolutions_from_findings(
        [_finding("plateau_fill_pct reached 2.4", value=2.4, units="mm")],
        [_req("plateau_fill_pct", "%")],
    )

    r = resolved["plateau_fill_pct"]
    assert not r.resolved
    assert r.value is None, "a mismatched number must not reach a calculation"
    assert r.reason is BlockedReason.UNITS_MISMATCH


def test_a_finding_with_no_value_is_prose_and_goes_to_the_mentions():
    """Most of what layer 1 finds is not a number - a mechanism, a scope
    restriction, a contradiction between two papers. Those findings must cross,
    and they are not resolutions: reading a value off prose is the one thing
    that would let a sentence become a power calculation."""
    prose = _finding(
        "plateau_fill_pct depends on crowder concentration, which this "
        "protocol does not vary",
        kind="contradicts",
    )
    rs = resolution_set_from_handoff(
        _handoff(findings=(prose,)), "fibrin_contracture", [_req("plateau_fill_pct", "%")]
    )

    assert rs.resolutions["plateau_fill_pct"].reason is BlockedReason.NOT_YET_SEARCHED
    assert any("crowder concentration" in m for m in rs.unmodelled_mentions)


def test_a_derived_finding_without_its_assumption_is_refused_not_coerced():
    """`Resolution` rejects a DERIVED value with no assumption, because a
    calculation that does not say what it assumed is indistinguishable from a
    measurement. The tempting repair is to relabel it LITERATURE, which converts
    cleanly and reports arithmetic as a reading - so the refusal is pinned, and
    so is the fact that the same finding crosses once it carries the assumption.
    """
    bare = _finding(
        "well_to_well_cv of 0.107",
        provenance="derived",
        value=0.107,
        units="fraction",
    )
    resolved = resolutions_from_findings([bare], [_req("well_to_well_cv", "fraction")])
    r = resolved["well_to_well_cv"]
    assert not r.resolved
    assert r.provenance is None, "a refused derivation must not be relabelled"
    assert r.reason is BlockedReason.NOT_YET_SEARCHED

    stated = dataclasses.replace(
        bare, assumption="constant CV across the range, sd proportional to mean"
    )
    crossed = resolutions_from_findings([stated], [_req("well_to_well_cv", "fraction")])[
        "well_to_well_cv"
    ]
    assert crossed.provenance is Provenance.DERIVED
    assert crossed.assumption == stated.assumption


def test_an_assumed_finding_without_a_range_is_refused_and_no_range_is_invented():
    """A stand-in with no range is a stand-in that presents as a measurement and
    whose verdict cannot be tested for sensitivity to it. The only two honest
    options are to refuse it or to invent a range, and inventing one would
    manufacture the evidence the range exists to test."""
    bare = _finding(
        "aprotinin_hazard_scale of about 4",
        provenance="assumed",
        source="FIXTURE:assumed",
        value=4.0,
        units="x",
    )
    resolved = resolutions_from_findings([bare], [_req("aprotinin_hazard_scale", "x")])
    assert not resolved["aprotinin_hazard_scale"].resolved
    assert resolved["aprotinin_hazard_scale"].plausible_range is None

    ranged = dataclasses.replace(bare, plausible_range=(2.0, 8.0))
    crossed = resolutions_from_findings(
        [ranged], [_req("aprotinin_hazard_scale", "x")]
    )["aprotinin_hazard_scale"]
    assert crossed.provenance is Provenance.ASSUMED
    assert crossed.plausible_range == (2.0, 8.0)


def test_a_statement_naming_two_keys_matches_neither():
    """"The effect_size exceeded the within_arm_sd" carries one number and two
    names, and nothing in the record says which the number belongs to. Half the
    time a guess would be right, which is exactly what makes it dangerous: the
    wrong half arrives at the power calculation looking identical to the right
    half."""
    ambiguous = _finding(
        "the effect_size was three times the within_arm_sd",
        value=3.0,
        units="mm",
    )
    resolved = resolutions_from_findings(
        [ambiguous],
        [_req("effect_size", "mm", "tier0"), _req("within_arm_sd", "mm", "tier0")],
    )

    assert all(not r.resolved for r in resolved.values())
    assert all(
        r.reason is BlockedReason.NOT_YET_SEARCHED for r in resolved.values()
    )


def test_two_findings_that_disagree_resolve_neither():
    """Two papers, two numbers, one requirement key. Taking the first is
    arbitrary and taking the mean is a weighting scheme nobody agreed to, and
    both produce a single number that reads as settled. The honest output is
    that the quantity is not settled yet."""
    resolved = resolutions_from_findings(
        [
            _finding("contraction_tau_h of 12", value=12.0, units="h"),
            _finding("contraction_tau_h of 30", value=30.0, units="h", source="10.2/y"),
        ],
        [_req("contraction_tau_h", "h")],
    )

    r = resolved["contraction_tau_h"]
    assert not r.resolved
    assert r.reason is BlockedReason.NOT_YET_SEARCHED


def test_the_readout_relative_pair_must_agree_with_each_other():
    """`effect_size` and `within_arm_sd` are declared in "readout units", which
    is a placeholder rather than a unit: the arithmetic uses only their ratio,
    so neither is pinned absolutely. That licence holds only while they are in
    the same units. A difference in microns over a spread in percentage points
    is not a standardised effect size, and the power figure it produces is
    indistinguishable from one that means something.
    """
    findings = (
        _finding("effect_size of 12", value=12.0, units="um"),
        _finding("within_arm_sd of 4", value=4.0, units="% area"),
    )
    resolved = resolutions_from_findings(
        findings, [r for r in tier0_needs() if r.key in ("effect_size", "within_arm_sd")]
    )

    assert all(
        r.reason is BlockedReason.UNITS_MISMATCH for r in resolved.values()
    ), "a ratio of two different units is not a standardised effect size"

    agreeing = (
        findings[0],
        dataclasses.replace(findings[1], units="um"),
    )
    both = resolutions_from_findings(
        agreeing, [r for r in tier0_needs() if r.key in ("effect_size", "within_arm_sd")]
    )
    assert all(r.resolved for r in both.values())


def test_an_assumed_tier0_quantity_is_layer_1_doing_layer_2s_job():
    """The §5.2 boundary, enforced rather than described. A reported effect size
    is a finding; an assumed one is an estimate, and estimating the effect size
    is the thing layer 1 explicitly does not do. The line is already in the type
    system - ASSUMED is defined as nobody's measurement - so the restriction
    costs nothing except the case it exists to stop, and it is confined to tier
    0: a swept stand-in for a mechanistic constant is honest and useful.
    """
    guess = _finding(
        "effect_size is probably about 8",
        provenance="assumed",
        source="FIXTURE:assumed",
        value=8.0,
        units="% area",
        plausible_range=(4.0, 12.0),
    )
    tier0 = _req("effect_size", "readout units", "tier0")
    tier1 = _req("aprotinin_hazard_scale", "x")

    assert not crosses_as_report(guess, tier0)
    assert crosses_as_report(
        dataclasses.replace(guess, statement="aprotinin_hazard_scale is about 8", units="x"),
        tier1,
    )
    assert not resolutions_from_findings([guess], [tier0])["effect_size"].resolved


# --- OpenItem -> Resolution --------------------------------------------------


def test_an_open_item_carries_not_reported_across_with_its_query():
    """Property 5, the one that matters more than anything else in the handoff:
    "looked and it is not there" reaching the gate as something other than
    silence. NOT_REPORTED means the tier-1 constant is genuinely unfillable and
    the design should fall through to tier 0; NOT_YET_SEARCHED means nobody has
    finished, and routing on it manufactures a premature refusal.
    """
    item = OpenItem(
        statement="lysis_shape is never given",
        why="not_in_literature",
        searched=True,
        queries_run=(QUERY, "  "),
    )
    rs = resolution_set_from_handoff(
        _handoff(residual=(item,)), "fibrin_contracture", [_req("lysis_shape", "-")]
    )

    r = rs.resolutions["lysis_shape"]
    assert r.reason is BlockedReason.NOT_REPORTED
    assert r.queries_run == (QUERY,), "every query out must have gone in"
    assert rs.complete, "a searched set is routable; it is not unfinished"


def test_a_finding_and_an_open_item_for_the_same_key_cancel():
    """Layer 1 saying both "it is 12 hours" and "it is unsettled" about one
    quantity is a contradiction, not a preference. Taking the number would let a
    stale finding outvote a later search, and taking the gap would discard a
    measurement - so neither is used and the set routes as unfinished, which is
    the only state that asks a person to look."""
    rs = resolution_set_from_handoff(
        _handoff(
            findings=(_finding("contraction_tau_h of 12", value=12.0, units="h"),),
            residual=(
                OpenItem(
                    statement="contraction_tau_h is not transferable between gels",
                    why="contested",
                    searched=True,
                    queries_run=(QUERY,),
                ),
            ),
        ),
        "fibrin_contracture",
        [_req("contraction_tau_h", "h")],
    )

    r = rs.resolutions["contraction_tau_h"]
    assert not r.resolved
    assert r.reason is BlockedReason.NOT_YET_SEARCHED
    assert any("contraction_tau_h" in m and "Both cannot be true" in m
               for m in rs.unmodelled_mentions)


def test_nothing_that_crossed_is_dropped():
    """The residual is the brief, what was ruled out stops layer 2 designing for
    a question already closed, and the limits say what was not looked at. None
    of the three is a quantity and none of them can be routed on, which is
    precisely why they are easy to drop - and dropping them loses the context
    the design is supposed to be for. They are carried as mentions: printed,
    never routed on."""
    rs = resolution_set_from_handoff(
        _handoff(
            ruled_out=("necroptosis: RIPK3 is not expressed in these cells",),
            limits="only human data was searched",
        ),
        "fibrin_contracture",
        [_req("lysis_shape", "-")],
    )
    text = " | ".join(rs.unmodelled_mentions)

    assert "aprotinin preserves the contracture window" in text
    assert "RIPK3" in text
    assert "only human data was searched" in text


# --- the version -------------------------------------------------------------


def test_the_requirement_version_matches_the_registry():
    """The digest itself now lives in `refute.digest`, a stdlib-only module
    both `handoff` and `requirements` import, precisely so this could stop
    being a duplication: `handoff` still cannot import `requirements` without
    pulling `AssayProtocol` in behind it, but it can import six lines over
    `hashlib`. What each caller hashes still differs on purpose -
    `requirements.requirement_version` reads the registry's declared
    constants, `handoff` and `adapt.py` hash whatever key list they were
    actually handed - so this test still earns its keep: it is what proves
    those two paths land on the same digest for the same requirement set."""
    protocol = get("fibrin_contracture")
    rs = resolution_set_from_handoff(
        _handoff(), protocol.key, tier1_needs(protocol) + tier0_needs()
    )
    assert rs.requirement_version == requirement_version(protocol)


# --- the boundary, and the false-positive guards -----------------------------


def test_the_tier0_ownership_is_stated_for_every_quantity():
    """A quantity whose ownership nobody decided is a quantity both layers
    assume the other is supplying, and the symptom is a permanent refusal that
    looks like an honest one. So the table has to be total over `TIER0_NEEDS`,
    and it fails loudly if the quartet ever grows a fifth member."""
    assert tier0_needs_a_handoff_can_fill() == TIER0_NEEDS
    assert set(HANDOFF_FILLABLE_TIER0) == set(TIER0_NEEDS)


def test_a_handoff_of_reported_quantities_reaches_tier_0():
    """The test that proves the two layers can connect.

    §5.2 says layer 1 does not estimate an effect size or propose a sample size.
    Two of the four tier-0 requirements are the effect size and the spread.
    Taken literally that leaves tier 0 permanently unreachable, every design
    routing REFUSE, and a gap in the contract presenting as a failure of the
    design layer - which is the most damaging wrong output this system has,
    because it is the one people quote.

    The resolution is that a *reported* quantity is a finding and an assumed one
    is an estimate. Here is a handoff carrying four reported quantities, and it
    has to come out the far side of the real gate as TIER0: not ready is wrong,
    refuse is wrong, and a twin is not available because none of the fibrin
    protocol's mechanistic constants crossed.
    """
    protocol = get("fibrin_contracture")
    reported = (
        _finding(
            "the published effect_size between arms was 9 percentage points of fill",
            value=9.0,
            units="% fill",
        ),
        _finding(
            "within_arm_sd across replicate gels was 6 percentage points",
            value=6.0,
            units="% fill",
        ),
        _finding("the study tested at alpha 0.05", value=0.05, units="probability"),
        _finding("n_per_arm was 6 gels", value=6.0, units="units per arm"),
    )
    rs = resolution_set_from_handoff(
        _handoff(findings=reported), protocol.key, tier0_needs()
    )

    assert rs.covers(TIER0_NEEDS), rs.missing(TIER0_NEEDS)
    assert rs.complete
    assert not rs.assumed(TIER0_NEEDS), "a reported quantity is not a stand-in"

    decision = route_design(EXPERIMENT_4_AS_RUN, protocol, rs)
    assert decision.route is Route.TIER0


def test_a_handoff_that_covers_a_protocol_reaches_the_twin():
    """The second false-positive guard, on the tier-1 path.

    Everything else here is satisfied by a matcher that answers
    NOT_YET_SEARCHED to everything: it would be total, it would invent no
    queries and it would never be wrong out loud. So one handoff is written to
    cover a protocol in full - from the protocol's own declared constants, so it
    stays covering when the protocol gains one - and it has to reach TIER1.
    """
    protocol = get("fibrin_contracture")
    requirements = tier1_needs(protocol)
    covered = tuple(
        _finding(
            f"{req.key} was reported as 1.0",
            value=1.0,
            units=req.units,
        )
        for req in requirements
    )
    rs = resolution_set_from_handoff(
        _handoff(findings=covered), protocol.key, requirements
    )

    assert rs.covers(r.key for r in requirements), rs.missing(
        r.key for r in requirements
    )
    assert route_design(EXPERIMENT_4_AS_RUN, protocol, rs).route is Route.TIER1


def test_a_handoff_that_settled_nothing_is_not_ready_rather_than_refused():
    """The complement, and the distinction §7 asks for by name: "not enough has
    been looked at yet to say" is not a refusal and must not be routed as one.
    A handoff whose residual names nothing the requirement set has a term for
    leaves every key unsearched, and the gate has to say so."""
    protocol = get("fibrin_contracture")
    rs = resolution_set_from_handoff(
        _handoff(), protocol.key, tier1_needs(protocol) + tier0_needs()
    )

    assert not rs.complete
    assert rs.unsearched()
    assert route_design(EXPERIMENT_4_AS_RUN, protocol, rs).route is Route.NOT_READY


def test_a_resolution_built_here_survives_its_own_invariants():
    """A cheap belt-and-braces pass over the whole crossing: every entry the
    matcher produces has to be a legal `Resolution`, which means resolved with a
    provenance and a source, or blocked with a reason, and never both or
    neither. `Resolution.__post_init__` enforces it at construction, so this
    only fails if something here stops going through the constructor."""
    protocol = get("fibrin_contracture")
    rs = resolution_set_from_handoff(
        _handoff(
            findings=(
                _finding("plateau_fill_pct of 62", value=62.0, units="%"),
                _finding("lysis_shape is not a scalar", kind="contradicts"),
            )
        ),
        protocol.key,
        tier1_needs(protocol) + tier0_needs(),
    )

    for key, r in rs.resolutions.items():
        assert isinstance(r, Resolution)
        assert r.quantity == key
        assert (r.value is None) != (r.reason is None)
