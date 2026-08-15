"""The gate must route in both directions, and must never read a value.

BOTH DIRECTIONS. This repository has already shipped an out-of-scope guard that
was a fail-ALWAYS guard - it flagged the twin's own assay and its own readout as
unmodelled - and it passed the entire test suite, because there was a test that a
genuinely out-of-scope design is refused and no test that a legitimate design is
not. "Refuse everything" satisfies every test that only checks refusals. So the
first test in this file is the false-positive guard, and every routing test below
it names the route it must NOT take as well as the one it must.

NEVER READS A VALUE. `route_design` decides on which quantities resolved and why
the rest did not. The last two tests pin that: one routes a set whose every
`value` is None, the other routes a set of objects that raise on any attempt to
read `.value` at all.

Every resolution set here is built from `tier1_needs(protocol)` and
`tier0_needs()` rather than from hard-coded constant names, so these tests pin the
gate's behaviour and not the registry's current vocabulary.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from refute.assays.evidence import BlockedReason
from refute.assays.fibrin_contracture import PROTOCOL
from refute.design import EXPERIMENT_4_AS_RUN
from refute.gate import Route, RouteDecision, route_design
from refute.requirements import tier0_needs, tier1_needs
from refute.resolve import Provenance, Resolution, ResolutionSet

TIER1_KEYS = tuple(r.key for r in tier1_needs(PROTOCOL))
TIER0_KEYS = tuple(r.key for r in tier0_needs())
ALL_KEYS = tuple(dict.fromkeys(TIER1_KEYS + TIER0_KEYS))

# Blocking a key that both tiers need cannot demonstrate a fallback to tier 0,
# because it takes tier 0 down with it. The registry is free to share keys
# between the tiers, so the tests that exercise the ladder pick from here.
TIER1_ONLY = tuple(k for k in TIER1_KEYS if k not in TIER0_KEYS)


# --- builders ---------------------------------------------------------------
# Inline Python, deliberately. Fixture files are owned by another builder, and a
# routing test that fails because a JSON file moved is a test about the file.


def found(key: str, provenance: Provenance = Provenance.LITERATURE) -> Resolution:
    """A resolution carrying a usable value."""
    extra: dict = {}
    if provenance is Provenance.ASSUMED:
        extra["plausible_range"] = (0.5, 2.0)
    if provenance is Provenance.DERIVED:
        extra["assumption"] = "reported as a half-time; converted assuming first order"
    return Resolution(
        quantity=key,
        value=1.0,
        units="-",
        provenance=provenance,
        source="10.0000/test",
        quote="the sentence the number came from",
        **extra,
    )


def blocked(key: str, reason: BlockedReason) -> Resolution:
    """A resolution carrying a typed reason instead of a value."""
    queries = ("methods AND aprotinin",) if reason is BlockedReason.NOT_REPORTED else ()
    return Resolution(quantity=key, reason=reason, queries_run=queries)


def resolution_set(overrides: dict[str, Resolution] | None = None, **kwargs) -> ResolutionSet:
    """Everything resolved from the literature, then the named keys replaced.

    Totality is the point: every key in the requirement set gets an entry, so a
    test that wants one gap has to say which gap, and cannot produce one by
    omission.
    """
    resolutions = {k: found(k) for k in ALL_KEYS}
    resolutions.update(overrides or {})
    return ResolutionSet(
        assay_key=PROTOCOL.key,
        requirement_version="test",
        resolutions=resolutions,
        **kwargs,
    )


COLLAGEN = EXPERIMENT_4_AS_RUN.model_copy(
    update={
        "out_of_twin_scope": [
            "matrix changed from fibrin to rat-tail collagen I at 2 mg/mL",
        ]
    }
)


# --- the false-positive guard -----------------------------------------------


def test_a_canonical_covered_in_scope_design_routes_to_tier1():
    """The test whose absence let a fail-always guard ship.

    Nothing about this design or this resolution set is unusual: it is the
    experiment the twin was calibrated on, with every constant resolved. If it
    does not route to TIER1 then the gate is refusing its own apparatus, and no
    quantity of passing refusal tests means anything.
    """
    decision = route_design(EXPERIMENT_4_AS_RUN, PROTOCOL, resolution_set())

    assert decision.route is Route.TIER1
    assert decision.missing == ()
    assert decision.unmodelled == ()
    assert decision.why


def test_ordinary_protocol_detail_is_not_a_scope_violation():
    """Blank entries must not refuse a design the twin handles perfectly well.

    An extractor emitting a stray empty string is the cheapest possible way to
    turn the guard back into a fail-always guard.
    """
    noisy = EXPERIMENT_4_AS_RUN.model_copy(update={"out_of_twin_scope": ["", "   "]})
    assert route_design(noisy, PROTOCOL, resolution_set()).route is Route.TIER1


# --- the tier ladder --------------------------------------------------------


def test_tier1_gaps_with_tier0_covered_falls_back_to_tier0():
    gap = TIER1_ONLY[0]
    decision = route_design(
        EXPERIMENT_4_AS_RUN,
        PROTOCOL,
        resolution_set({gap: blocked(gap, BlockedReason.ASSAY_SPECIFIC)}),
    )

    assert decision.route is Route.TIER0
    # The downgrade has to say what caused it, or the caller cannot tell a
    # fallback from a design that never needed a twin.
    assert gap in decision.missing


def test_everything_blocked_refuses_and_names_the_tier0_gaps():
    decision = route_design(
        EXPERIMENT_4_AS_RUN,
        PROTOCOL,
        resolution_set({k: blocked(k, BlockedReason.ASSAY_SPECIFIC) for k in ALL_KEYS}),
    )

    assert decision.route is Route.REFUSE
    assert set(decision.missing) == set(TIER0_KEYS)
    # A refusal that does not say what would lift it is indistinguishable from
    # the system being broken.
    for key in TIER0_KEYS:
        assert key in decision.why


def test_a_single_tier0_gap_is_enough_to_refuse():
    """Tier 0 is four numbers. Three of four is not an arithmetic result."""
    gap = TIER0_KEYS[0]
    decision = route_design(
        EXPERIMENT_4_AS_RUN,
        PROTOCOL,
        resolution_set(
            {k: blocked(k, BlockedReason.NOT_REPORTED) for k in (*TIER1_KEYS, gap)}
        ),
    )

    assert decision.route is Route.REFUSE
    assert decision.missing == (gap,)


# --- unsearched is not a refusal --------------------------------------------


def test_one_unsearched_key_is_not_ready_and_is_not_a_refusal():
    """The most damaging wrong output this system can produce.

    Routing an unsearched set as REFUSE emits "not answerable at this scale" for
    an experiment nobody has looked into - which is word for word the finding
    this project actually made about a real experiment, attached to a design
    about which nothing whatsoever is known.
    """
    key = TIER1_KEYS[0]
    decision = route_design(
        EXPERIMENT_4_AS_RUN,
        PROTOCOL,
        resolution_set({key: blocked(key, BlockedReason.NOT_YET_SEARCHED)}),
    )

    assert decision.route is Route.NOT_READY
    assert decision.route is not Route.REFUSE
    assert decision.missing == (key,)


def test_unsearched_outranks_a_scope_violation():
    """Precedence, not preference.

    The design may well be out of scope, but saying so on the strength of a set
    nobody has finished filling is a guess dressed as a finding.
    """
    key = TIER1_KEYS[0]
    decision = route_design(
        COLLAGEN,
        PROTOCOL,
        resolution_set({key: blocked(key, BlockedReason.NOT_YET_SEARCHED)}),
    )

    assert decision.route is Route.NOT_READY


def test_a_fully_searched_set_with_typed_blocks_is_ready_to_route():
    """NOT_YET_SEARCHED is the only reason that stops routing.

    Guards the opposite error: treating any blocked constant as "not ready" would
    make the gate never refuse and never fall back.
    """
    rs = resolution_set({k: blocked(k, BlockedReason.NOT_REPORTED) for k in TIER1_ONLY})
    assert rs.complete
    assert route_design(EXPERIMENT_4_AS_RUN, PROTOCOL, rs).route is Route.TIER0


# --- context-dependent is swept, not missing --------------------------------


def test_a_context_dependent_constant_is_swept_and_still_tier1():
    """The distinction most likely to be collapsed by accident.

    An ill-posed scalar is not an absent one. It becomes a swept range and the
    verdict is reported as sensitive to it, rather than withheld.
    """
    key = TIER1_KEYS[0]
    decision = route_design(
        EXPERIMENT_4_AS_RUN,
        PROTOCOL,
        resolution_set({key: blocked(key, BlockedReason.CONTEXT_DEPENDENT)}),
    )

    assert decision.route is Route.TIER1
    assert key in decision.sweep
    assert key not in decision.missing


def test_an_assumed_constant_is_swept_rather_than_fixed():
    key = TIER1_KEYS[0]
    decision = route_design(
        EXPERIMENT_4_AS_RUN,
        PROTOCOL,
        resolution_set({key: found(key, Provenance.ASSUMED)}),
    )

    assert decision.route is Route.TIER1
    assert key in decision.sweep


def test_a_twin_made_mostly_of_stand_ins_is_not_tier1():
    """Above half assumed, a twin reports its own priors, not a measurement."""
    decision = route_design(
        EXPERIMENT_4_AS_RUN,
        PROTOCOL,
        resolution_set({k: found(k, Provenance.ASSUMED) for k in TIER1_KEYS}),
    )

    assert decision.route is not Route.TIER1
    assert decision.route is Route.TIER0
    # Every tier-1 constant resolved, so the fallback is not about gaps and must
    # not be reported as though it were.
    assert decision.missing == ()
    assert "stand-ins" in decision.why


# --- scope ------------------------------------------------------------------


def test_a_genuinely_out_of_scope_design_routes_out_of_scope():
    decision = route_design(COLLAGEN, PROTOCOL, resolution_set())

    assert decision.route is Route.OUT_OF_SCOPE
    assert len(decision.unmodelled) == 1
    assert "collagen" in decision.unmodelled[0]
    # It is a limit of the twin, not a verdict on the design, and it is not a
    # gap in the evidence either.
    assert decision.missing == ()


def test_scope_is_checked_before_coverage():
    """Full coverage of the wrong apparatus is worse than no coverage.

    It produces a confident number about a plate nobody proposed - an error in
    the permissive direction, which for a verifier is the one that matters.
    """
    decision = route_design(COLLAGEN, PROTOCOL, resolution_set())
    assert decision.route is not Route.TIER1


def test_an_unmodelled_mention_cannot_route_out_of_scope_by_itself():
    """The resolution set's mentions are a hint and never an authority.

    A resolver that could refuse a design on its own say-so is a keyword search
    with extra steps, and keyword searches are how the last out-of-scope guard
    came to flag the twin's own readout.
    """
    rs = resolution_set(unmodelled_mentions=("collagen", "gene expression"))
    decision = route_design(EXPERIMENT_4_AS_RUN, PROTOCOL, rs)

    assert decision.route is Route.TIER1
    assert decision.unmodelled == ()


def test_the_mention_corroborates_a_violation_the_design_declares():
    rs = resolution_set(unmodelled_mentions=("collagen",))
    decision = route_design(COLLAGEN, PROTOCOL, rs)

    assert decision.route is Route.OUT_OF_SCOPE
    assert "corroborating" in decision.why


def test_a_destructive_readout_cannot_support_per_unit_normalisation():
    """The protocol side of the comparison, and it is structural, not textual.

    One measurement per unit means no unit has an earlier measurement of itself,
    so normalising to it describes an apparatus that does not exist. The
    simulator would have to invent the baseline to return any number at all.
    """
    destructive = replace(
        PROTOCOL, readout=replace(PROTOCOL.readout, destructive=True)
    )
    decision = route_design(EXPERIMENT_4_AS_RUN, destructive, resolution_set())

    assert decision.route is Route.OUT_OF_SCOPE
    assert "destructive" in decision.unmodelled[0]


def test_the_destructive_check_does_not_fire_on_the_real_protocol():
    """The other half of that check, and the half a fail-always guard fails."""
    assert not PROTOCOL.readout.destructive
    assert route_design(EXPERIMENT_4_AS_RUN, PROTOCOL, resolution_set()).route is Route.TIER1


# --- the gate never reads a value -------------------------------------------


def test_a_set_with_no_values_at_all_still_routes():
    """Every value None, every route still determined.

    This is the property that let the gate be built before the resolver existed,
    and it is worth a test rather than a comment because it is invisible until
    it is broken.
    """
    rs = resolution_set(
        {
            k: Resolution(
                quantity=k,
                value=None,
                provenance=Provenance.LITERATURE,
                reason=BlockedReason.CONTEXT_DEPENDENT,
            )
            for k in ALL_KEYS
        }
    )
    assert all(r.value is None for r in rs.resolutions.values())

    decision = route_design(EXPERIMENT_4_AS_RUN, PROTOCOL, rs)

    assert decision.route is Route.TIER1
    assert set(decision.sweep) == set(TIER1_KEYS)


class ValueTripwire:
    """Looks like a `Resolution`, detonates if anything reads `.value`.

    A duck type rather than a subclass: `Resolution` is a frozen dataclass, so
    its generated `__init__` would collide with a property of the same name.
    Everything the gate is allowed to touch is here; everything it is not, is not.
    """

    def __init__(self, quantity: str, reason: BlockedReason | None = None):
        self.quantity = quantity
        self.provenance = Provenance.LITERATURE
        self.reason = reason
        self.resolved = reason is None
        self.blocks_tier1 = reason is not None and (
            reason is not BlockedReason.CONTEXT_DEPENDENT
        )

    @property
    def value(self) -> float:
        raise AssertionError(
            f"the gate read {self.quantity}.value - it routes on what resolved and "
            "why the rest did not, and the moment it consults a number it starts "
            "making judgements the numbers cannot support"
        )


def test_routing_a_tripwire_set_never_touches_a_value():
    rs = ResolutionSet(
        assay_key=PROTOCOL.key,
        requirement_version="test",
        resolutions={k: ValueTripwire(k) for k in ALL_KEYS},
    )

    # The tripwire is armed: prove it fires, or this test proves nothing.
    with pytest.raises(AssertionError):
        _ = rs.resolutions[ALL_KEYS[0]].value

    assert route_design(EXPERIMENT_4_AS_RUN, PROTOCOL, rs).route is Route.TIER1


def test_every_route_is_reachable_without_reading_a_value():
    """One tripwire set per route. The router is value-blind on all five paths.

    Pinned as one test because the property is about the gate, not about any
    single branch of it - a value read on the refusal path is the same defect as
    one on the happy path, and would be just as easy to add later.
    """
    key = TIER1_ONLY[0]

    def tripwire_set(overrides: dict[str, ValueTripwire], **kwargs) -> ResolutionSet:
        resolutions: dict[str, ValueTripwire] = {k: ValueTripwire(k) for k in ALL_KEYS}
        resolutions.update(overrides)
        return ResolutionSet(
            assay_key=PROTOCOL.key,
            requirement_version="test",
            resolutions=resolutions,
            **kwargs,
        )

    cases = {
        Route.TIER1: (EXPERIMENT_4_AS_RUN, tripwire_set({})),
        Route.NOT_READY: (
            EXPERIMENT_4_AS_RUN,
            tripwire_set({key: ValueTripwire(key, BlockedReason.NOT_YET_SEARCHED)}),
        ),
        Route.OUT_OF_SCOPE: (COLLAGEN, tripwire_set({})),
        Route.TIER0: (
            EXPERIMENT_4_AS_RUN,
            tripwire_set({key: ValueTripwire(key, BlockedReason.ASSAY_SPECIFIC)}),
        ),
        Route.REFUSE: (
            EXPERIMENT_4_AS_RUN,
            tripwire_set(
                {k: ValueTripwire(k, BlockedReason.ASSAY_SPECIFIC) for k in ALL_KEYS}
            ),
        ),
    }

    for expected, (design, rs) in cases.items():
        assert route_design(design, PROTOCOL, rs).route is expected


# --- the decision itself ----------------------------------------------------


def test_the_decision_is_immutable_and_defaults_to_empty():
    decision = RouteDecision(route=Route.TIER1, why="because")

    assert (decision.missing, decision.unmodelled, decision.sweep) == ((), (), ())
    with pytest.raises(Exception):
        decision.route = Route.REFUSE  # type: ignore[misc]
