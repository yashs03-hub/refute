"""The crossing between the two vocabularies, and the three ways it could lie.

`refute/adapt.py` exists because the recorded findings and the machinery that
routes on findings were written in different types and could not meet. A
conversion between two representations of the same fact is the kind of code
that is trivially correct in the cases anybody thinks to check, so the tests
here are shaped around the ways it could be quietly wrong instead:

**By inventing a search.** `queries_run` is what makes NOT_REPORTED a
defensible claim about the literature rather than an assertion. An adapter with
a plausible-looking default for it would manufacture the evidence for the one
claim this project rests on, and every converted set would validate. So the
blank-query case is pinned to raise, and every query that comes out is checked
to be a substring of one that went in.

**By losing a distinction.** CONTEXT_DEPENDENT does not block a twin, DERIVED
must carry its assumption, and NOT_YET_SEARCHED is not NOT_REPORTED. Each of
those collapses into a neighbouring case without any type complaining, and each
collapse fails safe-looking: the pipeline simply refuses more often, or claims
more than it searched.

**By answering only what it can.** A resolver that dropped the keys it had
nothing to say about would report full coverage forever. Totality over the
requirement set is asserted for every protocol in the registry, not just the
three with recorded reports.

There is also a false-positive guard, because the other three tests are all
satisfied by an adapter that returns NOT_YET_SEARCHED for everything: a
synthetic report that covers a protocol in full must reach the simulator and
come back with a score.
"""

from __future__ import annotations

import pytest

from refute.adapt import (
    RecordedResolver,
    resolution_from_blocked,
    resolution_from_evidence,
    resolution_set_from_report,
)
from refute.assays import REGISTRY, get
from refute.assays.evidence import (
    Blocked,
    BlockedReason,
    CalibrationReport,
    Evidence,
    Provenance,
)
from refute.assays.literature import REPORTS
from refute.design import EXPERIMENT_4_AS_RUN
from refute.gate import Route, route_design
from refute.pipeline import NOT_ANSWERABLE, requirements_for, run
from refute.requirements import requirement_version, tier0_needs, tier1_needs
from refute.resolve import Requirement

# Enough plates to exercise the whole tier-1 path without spending the suite's
# runtime on a power figure no assertion reads.
SIMS = 30

QUERY = "fibrin gel lysis Weibull shape methods"


def _req(key: str, tier: str = "tier1") -> Requirement:
    return Requirement(key=key, units="-", what="a quantity", tier=tier)


# --- Evidence -> Resolution --------------------------------------------------


def test_a_literature_value_crosses_with_its_words_intact():
    """The quote and the source are the evidence. A number that arrives without
    them is a number somebody will use and nobody can check."""
    ev = Evidence(
        constant="tgfb_fold_change",
        value=4.7,
        units="x",
        source="10.1186/s42490-019-0014-z",
        quote="a 4.7-fold increase in collagen type I",
    )
    r = resolution_from_evidence(ev)

    assert r.quantity == "tgfb_fold_change"
    assert r.value == 4.7
    assert r.units == "x"
    assert r.provenance is Provenance.LITERATURE
    assert r.source == ev.source
    assert r.quote == ev.quote
    assert r.resolved and not r.blocks_tier1


def test_a_derived_value_arrives_derived_and_carries_its_assumption():
    """`Resolution` rejects a DERIVED value with no assumption, so an adapter
    that dropped the assumption would not fail quietly - it would fail on every
    derived constant in the corpus. Asserted anyway, because the tempting fix
    for that failure is to downgrade the tier to LITERATURE, which converts
    cleanly and reports a calculation as a reading."""
    ev = Evidence(
        constant="well_to_well_cv",
        value=0.107,
        units="fraction",
        source="10.1186/s42490-019-0014-z",
        quote="Z' values of 0.49-0.51",
        derived=True,
        assumption="constant CV across the range, sd proportional to mean",
    )
    r = resolution_from_evidence(ev)

    assert r.provenance is Provenance.DERIVED
    assert r.assumption == ev.assumption


def test_a_tier_the_old_flag_could_not_express_survives_the_crossing():
    """The reason `Evidence.tier` was added. A value counted off a lab notebook
    is stronger evidence than one read out of a paper, and before the tier field
    existed it had to be recorded as though it had been published - which
    inverts the ordering the resolve layer sorts on."""
    ev = Evidence(
        constant="p_cast_failure",
        value=0.02,
        units="probability",
        source="cases/exp4/PROVENANCE.md",
        quote="2 of 96 gels failed to cast",
        tier=Provenance.PRIMARY,
    )
    assert resolution_from_evidence(ev).provenance is Provenance.PRIMARY


def test_an_assumed_value_is_refused_rather_than_stripped_of_its_range():
    """`Evidence` has no field for a plausible range and `Resolution` requires
    one on an ASSUMED value, so the only way to convert is to drop the sweep -
    which reports a stand-in as a measurement and makes the verdict untestable
    for sensitivity to it. Refusing is the only honest option available."""
    ev = Evidence(
        constant="aprotinin_hazard_scale",
        value=4.0,
        units="x",
        source="FIXTURE:assumed",
        quote="",
        tier=Provenance.ASSUMED,
    )
    with pytest.raises(ValueError, match="plausible range"):
        resolution_from_evidence(ev)


# --- Blocked -> Resolution ---------------------------------------------------


def test_the_single_searched_string_becomes_the_query_tuple():
    """The original defect, reproduced and fixed. `Blocked` records one query as
    a string and `Resolution` requires a tuple, and without the conversion a
    NOT_REPORTED finding could not be expressed at all - the data was there and
    the shape was wrong."""
    b = Blocked(
        constant="lysis_shape",
        reason=BlockedReason.NOT_REPORTED,
        detail="read end to end; never mentioned",
        searched=QUERY,
    )
    r = resolution_from_blocked(b)

    assert r.reason is BlockedReason.NOT_REPORTED
    assert r.queries_run == (QUERY,)
    assert not r.resolved and r.blocks_tier1


def test_a_blank_query_raises_and_no_query_is_invented():
    """The one behaviour that must never be convenient.

    `Blocked` already refuses an empty `searched` on a NOT_REPORTED claim, so
    the reachable case is a query made of whitespace: it passes that check and
    proves nothing. Converting it would either fabricate a search or silently
    rewrite the claim to NOT_YET_SEARCHED with nowhere to record the rewrite,
    and both turn a data defect into a statement about the literature.
    """
    b = Blocked(
        constant="lysis_shape",
        reason=BlockedReason.NOT_REPORTED,
        detail="",
        searched="   ",
    )
    with pytest.raises(ValueError) as exc:
        resolution_from_blocked(b)
    assert "NOT_YET_SEARCHED" in str(exc.value)


def test_not_yet_searched_needs_no_query_and_leaves_the_set_incomplete():
    """The honest default has to cost nothing to record, or nobody records it -
    and it has to keep routing NOT_READY afterwards, or recording it achieves
    nothing."""
    b = Blocked(
        constant="measurement_cv",
        reason=BlockedReason.NOT_YET_SEARCHED,
        detail="Only abstracts screened.",
    )
    r = resolution_from_blocked(b)

    assert r.queries_run == ()
    rs = resolution_set_from_report(
        CalibrationReport(key="a", found=(), blocked=(b,)),
        "a",
        [_req("measurement_cv")],
    )
    assert not rs.complete
    assert rs.unsearched() == ["measurement_cv"]


def test_context_dependent_still_does_not_block_a_twin_after_conversion():
    """The distinction most likely to be collapsed by accident, checked on the
    far side of the seam. An ill-posed scalar becomes a swept range; an absent
    one stops the twin. Collapsing them withholds verdicts that could have been
    given, and every test that only checks refusals still passes."""
    b = Blocked(
        constant="tgfb_fold_change",
        reason=BlockedReason.CONTEXT_DEPENDENT,
        detail="a function of substrate modulus, so not a scalar",
    )
    r = resolution_from_blocked(b)

    assert not r.blocks_tier1
    rs = resolution_set_from_report(
        CalibrationReport(key="a", found=(), blocked=(b,)),
        "a",
        [_req("tgfb_fold_change")],
    )
    assert rs.complete
    assert rs.missing(["tgfb_fold_change"]) == []
    assert rs.swept(["tgfb_fold_change"]) == ["tgfb_fold_change"]


def test_the_reasons_that_are_not_about_the_literature_convert_without_a_query():
    """UNITS_MISMATCH and ASSAY_SPECIFIC are properties of the constant or the
    instrument. They need no corpus to establish, so requiring a query for them
    would push an honest record toward a fabricated one."""
    for reason in (BlockedReason.UNITS_MISMATCH, BlockedReason.ASSAY_SPECIFIC):
        r = resolution_from_blocked(
            Blocked(constant="baseline", reason=reason, detail="d")
        )
        assert r.reason is reason
        assert r.queries_run == ()
        assert r.blocks_tier1


# --- totality ----------------------------------------------------------------


@pytest.mark.parametrize("key", sorted(REGISTRY))
def test_the_set_is_total_over_the_requirements_for_every_protocol(key):
    """Partiality is unrepresentable, so this holds for the protocols with no
    recorded report as strongly as for the three with one. A key that is absent
    and a key that is blocked route differently, and only one of them can be
    read as work still to do."""
    protocol = get(key)
    requirements = requirements_for(protocol)
    rs = RecordedResolver().resolve(key, requirements)

    assert set(rs.resolutions) == {r.key for r in requirements}
    for name, r in rs.resolutions.items():
        assert r.quantity == name
        assert r.resolved or r.reason is not None


def test_a_quantity_the_report_never_mentions_is_unsearched_not_absent():
    """The totality rule doing the work it exists for. `bleomycin_lung` has a
    recorded report and it says nothing at all about the tier-0 quartet, which
    is a different situation from a report that looked and found nothing."""
    protocol = get("bleomycin_lung")
    rs = RecordedResolver().resolve("bleomycin_lung", requirements_for(protocol))

    for req in tier0_needs():
        assert rs.resolutions[req.key].reason is BlockedReason.NOT_YET_SEARCHED


def test_a_recorded_finding_nothing_asked_for_is_carried_not_dropped():
    """A finding the requirement set has no term for is a real limit on how much
    of the experiment a verdict covers. It must not enter `resolutions`, where
    it would inflate the denominator, and it must not vanish either - the reader
    is the only one who can weigh it."""
    report = CalibrationReport(
        key="a",
        found=(
            Evidence(
                constant="crowder_concentration",
                value=37.5,
                units="mg/ml",
                source="10.1/x",
                quote="Ficoll 70 at 37.5 mg/ml",
            ),
        ),
        blocked=(),
    )
    rs = resolution_set_from_report(report, "a", [_req("tgfb_fold_change")])

    assert set(rs.resolutions) == {"tgfb_fold_change"}
    assert len(rs.unmodelled_mentions) == 1
    assert "crowder_concentration" in rs.unmodelled_mentions[0]


def test_a_report_for_another_assay_is_refused():
    """`measurement_cv` and `tgfb_fold_change` each mean something different in
    three protocols, so a mismatched report converts cleanly and answers the
    wrong question. `FixtureResolver` refuses the same thing."""
    with pytest.raises(ValueError, match="report is for assay"):
        resolution_set_from_report(REPORTS["scar_in_a_jar"], "traction_force", ())


def test_a_constant_recorded_twice_is_refused():
    """Resolutions are keyed by name. A constant listed as both found and
    blocked is a contradiction about whether the number exists, and whichever
    half won would settle it silently."""
    report = CalibrationReport(
        key="a",
        found=(Evidence("x", 1.0, "u", "10.1/x", "q"),),
        blocked=(
            Blocked(
                constant="x",
                reason=BlockedReason.NOT_REPORTED,
                detail="",
                searched=QUERY,
            ),
        ),
    )
    with pytest.raises(ValueError, match="recorded twice"):
        resolution_set_from_report(report, "a", [_req("x")])


@pytest.mark.parametrize("key", sorted(REGISTRY))
def test_the_requirement_version_matches_the_registry(key):
    """The version records which requirement set an answer is total over, and
    the pipeline warns when it disagrees with the registry. `adapt` computes the
    digest from the requirements it was handed rather than by looking the
    protocol up - so this is the test that keeps the two hashes in step, and
    without it the warning would fire on every recorded run."""
    protocol = get(key)
    rs = RecordedResolver().resolve(key, requirements_for(protocol))
    assert rs.requirement_version == requirement_version(protocol)


def test_the_version_moves_when_the_requirement_set_does():
    """The complement: a version that never changed would suppress the warning
    instead of raising it, which is worse than having no version at all."""
    protocol = get("scar_in_a_jar")
    base = requirements_for(protocol)
    doctored = base + (_req("a_key_nobody_declared"),)

    resolver = RecordedResolver()
    assert (
        resolver.resolve("scar_in_a_jar", doctored).requirement_version
        != resolver.resolve("scar_in_a_jar", base).requirement_version
    )


def test_tier0_keys_do_not_enter_the_version():
    """Tier 0 is assay-blind and belongs to no protocol's requirement set, so
    asking for it alongside tier 1 must not change which set the answer claims
    to be total over."""
    protocol = get("traction_force")
    resolver = RecordedResolver()
    with_tier0 = resolver.resolve("traction_force", requirements_for(protocol))
    tier1_only = resolver.resolve("traction_force", tier1_needs(protocol))
    assert with_tier0.requirement_version == tier1_only.requirement_version


# --- RecordedResolver --------------------------------------------------------


def test_an_assay_with_no_recorded_report_is_not_an_error():
    """Three of the six tier-1 scaffolds have never been attempted, and
    `literature.NOT_ATTEMPTED` lists them rather than omitting them so the
    denominator stays honest. The resolver agrees: nobody looked, which is a
    true statement the gate knows how to route."""
    protocol = get("fibrosis_on_chip")
    requirements = requirements_for(protocol)
    rs = RecordedResolver().resolve("fibrosis_on_chip", requirements)

    assert rs.unsearched() == sorted(r.key for r in requirements)
    assert not rs.complete
    decision = route_design(EXPERIMENT_4_AS_RUN, protocol, rs)
    assert decision.route is Route.NOT_READY


@pytest.mark.parametrize("key", sorted(REGISTRY))
def test_every_protocol_in_the_registry_routes_without_raising(key):
    """The claim Job 2 is for: the downstream half runs on recorded findings
    rather than on hand-written fixtures, for every protocol and not only the
    three that have been attempted. No route is asserted here - which route the
    corpus earns is a fact about the corpus and will change as it grows - only
    that every protocol produces one instead of an exception."""
    protocol = get(key)
    rs = RecordedResolver().resolve(key, requirements_for(protocol))
    assert route_design(EXPERIMENT_4_AS_RUN, protocol, rs).route in set(Route)


def test_the_resolver_is_named_and_the_reports_are_injectable():
    """The name is printed in the narrative beside the coverage count, which is
    the only place a reader learns whether a run came from recorded findings or
    from a hand-written fixture."""
    assert RecordedResolver.name == "recorded"
    empty = RecordedResolver(reports={})
    assert empty.resolve("scar_in_a_jar", [_req("x")]).unsearched() == ["x"]


@pytest.mark.parametrize("key", sorted(REPORTS))
def test_every_recorded_report_converts(key):
    """What makes the blank-query refusal a build-time gate rather than a
    crash in front of a researcher. Every `Blocked` in this repository is a
    literal in a source file, and this test converts all of them, so a record
    that cannot be expressed fails here first."""
    report = REPORTS[key]
    rs = RecordedResolver().resolve(key, requirements_for(get(key)))
    converted = {
        name for name, r in rs.resolutions.items()
        if r.reason is not BlockedReason.NOT_YET_SEARCHED or r.resolved
    }
    recorded = {e.constant for e in report.found} | {
        b.constant for b in report.blocked
        if b.reason is not BlockedReason.NOT_YET_SEARCHED
    }
    assert recorded <= converted


@pytest.mark.parametrize("key", sorted(REPORTS))
def test_no_query_is_invented_anywhere_in_the_corpus(key):
    """The fabrication guard, over the real data rather than a constructed case.
    Every query that comes out of the adapter has to have gone into it, and
    every NOT_REPORTED claim has to have one."""
    report = REPORTS[key]
    searched = {b.constant: b.searched.strip() for b in report.blocked}
    rs = RecordedResolver().resolve(key, requirements_for(get(key)))

    for name, r in rs.resolutions.items():
        for query in r.queries_run:
            assert query == searched.get(name), f"{name}: query not in the record"
        if r.reason is BlockedReason.NOT_REPORTED:
            assert r.queries_run, f"{name}: NOT_REPORTED with nothing behind it"


def test_the_recorded_asymmetry_survives_the_crossing():
    """The finding the corpus exists to demonstrate, asserted on the resolved
    form rather than on the source. Everything `scar_in_a_jar` recovered is an
    effect size or a precision estimate, and everything it recorded as absent
    from the literature is a failure constant. If a conversion ever flattened
    the reasons, this is the claim that would quietly stop being true."""
    rs = RecordedResolver().resolve(
        "scar_in_a_jar", requirements_for(get("scar_in_a_jar"))
    )
    resolved = {k for k, r in rs.resolutions.items() if r.resolved}
    not_reported = {
        k for k, r in rs.resolutions.items()
        if r.reason is BlockedReason.NOT_REPORTED
    }

    assert resolved == {"tgfb_fold_change", "well_to_well_cv"}
    assert not_reported and all(
        k.startswith("p_") or k.endswith(("_time_h", "_halflife_h"))
        for k in not_reported
    )


# --- end to end --------------------------------------------------------------


def test_the_pipeline_runs_end_to_end_on_a_recorded_scaffold():
    """A stop is a product, and this is the one the recorded data produces.

    `scar_in_a_jar` is the only protocol whose full text was retrievable, so its
    tier-1 half is completely searched - two constants found and five recorded
    as absent. The tier-0 quartet was never searched for, because effect sizes
    and variances come from the experimenter rather than from a corpus, so the
    honest route is NOT_READY. The phrase that must not appear is the one people
    quote: an unsearched set is not a finding about the design.
    """
    protocol = get("scar_in_a_jar")
    result = run(EXPERIMENT_4_AS_RUN, protocol, RecordedResolver(), n_sims=SIMS)
    text = " ".join(result.render().lower().split())

    assert result.route is Route.NOT_READY
    assert result.score is None and result.advice is None
    assert not result.terminal
    assert NOT_ANSWERABLE not in text
    assert "recorded" in text, "the narrative must name the resolver that answered"
    for req in tier0_needs():
        assert req.key in text


def test_the_tier1_half_of_the_scar_report_is_searched_and_refuses_on_its_own():
    """Asked only what the twin needs, the recorded set is complete: nothing in
    it is unsearched, so the answer stops being "not ready" and becomes a
    refusal that names its gaps. That is the finding - the failure constants
    were searched for and are not published - and it is only visible once the
    unsearched tier-0 quartet is out of the question."""
    protocol = get("scar_in_a_jar")
    rs = RecordedResolver().resolve("scar_in_a_jar", tier1_needs(protocol))
    decision = route_design(EXPERIMENT_4_AS_RUN, protocol, rs)

    assert rs.complete
    assert decision.route is Route.REFUSE
    assert decision.missing, "a refusal that names no gap cannot be acted on"


def test_a_covered_report_reaches_the_simulator():
    """The false-positive guard.

    Every other test here is satisfied by an adapter that answers
    NOT_YET_SEARCHED to everything - it would be total, it would invent no
    queries, and it would route NOT_READY forever without ever being wrong out
    loud. So one report is written to cover a protocol in full, and it has to
    come back with a score.

    The report is built from the protocol's own declared constants rather than a
    hard-coded list, so it stays covering when the protocol gains one.
    """
    protocol = get("fibrin_contracture")
    requirements = requirements_for(protocol)
    report = CalibrationReport(
        key=protocol.key,
        found=tuple(
            Evidence(
                constant=req.key,
                value=1.0,
                units=req.units,
                source="cases/exp4/PROVENANCE.md",
                quote="synthetic; the gate never reads a value",
            )
            for req in requirements
        ),
        blocked=(),
    )
    resolver = RecordedResolver(reports={protocol.key: report})
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=SIMS)

    assert result.route is Route.TIER1
    assert result.score is not None
    assert 0.0 <= result.score.power <= 1.0
