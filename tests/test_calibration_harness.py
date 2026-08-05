"""The calibration record has to be honest before it is useful.

The headline claim this harness produces is "the literature reports what an
assay measures and not how it breaks". That claim is only worth making if a
failed lookup cannot quietly become evidence of absence, so most of these tests
guard the bookkeeping rather than the numbers.
"""

from __future__ import annotations

import pytest

from refute.assays import REGISTRY
from refute.assays.evidence import Blocked, BlockedReason, CalibrationReport, Evidence
from refute.assays.literature import NOT_ATTEMPTED, REPORTS, SCAR_IN_A_JAR
from refute.assays.sources import (
    PaperclipSource,
    RecordedSource,
    get_source,
)


# -- the integrity rules ----------------------------------------------------

def test_not_reported_requires_a_recorded_search():
    """'Nobody publishes it' asserts something about the corpus. Asserting it
    without having looked is how a silence becomes a finding."""
    with pytest.raises(ValueError, match="requires having listened"):
        Blocked(
            constant="p_delaminate",
            reason=BlockedReason.NOT_REPORTED,
            detail="never seen it",
        )


def test_reasons_that_are_not_corpus_claims_need_no_search():
    """UNITS_MISMATCH and friends are properties of the constant, not the
    literature, so they are establishable without a query."""
    for reason in (
        BlockedReason.UNITS_MISMATCH,
        BlockedReason.ASSAY_SPECIFIC,
        BlockedReason.CONTEXT_DEPENDENT,
        BlockedReason.NOT_YET_SEARCHED,
    ):
        Blocked(constant="x", reason=reason, detail="because")  # must not raise
        assert not reason.is_a_claim_about_the_literature


def test_every_not_reported_claim_in_the_record_names_its_query():
    for report in REPORTS.values():
        for b in report.blocked:
            if b.reason is BlockedReason.NOT_REPORTED:
                assert b.searched, f"{report.key}/{b.constant}"


def test_derived_values_must_state_their_assumption():
    """A derived number that hides its derivation is indistinguishable from a
    measured one, which is the exact confusion this project exists to avoid."""
    with pytest.raises(ValueError, match="assumption"):
        Evidence(
            constant="cv", value=0.1, units="fraction",
            source="10.0000/x", quote="...", derived=True,
        )


def test_the_one_derived_constant_declares_its_uncertainty():
    """well_to_well_cv comes from Z' and signal:background, and the answer moves
    by ~1.6x depending on whether SD or CV is held constant. If that caveat is
    ever dropped, the number reads as firmer than it is."""
    cv = next(e for e in SCAR_IN_A_JAR.found if e.constant == "well_to_well_cv")
    assert cv.derived
    assert "swept" in cv.assumption
    assert "0.065" in cv.assumption  # the competing assumption, stated


def test_evidence_requires_a_source():
    with pytest.raises(ValueError, match="source"):
        Evidence(constant="x", value=1.0, units="x", source="", quote="q")


# -- the record itself ------------------------------------------------------

def test_recorded_constants_exist_on_their_protocols():
    """A typo in a constant name would silently inflate the blocked count and
    deflate recovery, since nothing else cross-checks the two files."""
    for key, report in REPORTS.items():
        known = {c.name for c in REGISTRY[key].all_constants()}
        for item in [*report.found, *report.blocked]:
            assert item.constant in known, f"{key}: unknown constant {item.constant}"


def test_no_constant_is_both_found_and_blocked():
    for report in REPORTS.values():
        found = {e.constant for e in report.found}
        blocked = {b.constant for b in report.blocked}
        assert not (found & blocked), f"{report.key}: {found & blocked}"


def test_attempted_protocols_account_for_every_constant():
    """Partial accounting would make recovery rates meaningless."""
    for key, report in REPORTS.items():
        assert report.total == len(REGISTRY[key].all_constants()), key


def test_not_attempted_list_does_not_overlap_the_attempted_ones():
    assert not (set(NOT_ATTEMPTED) & set(REPORTS))


def test_nothing_recorded_is_promoted_to_measured():
    """LITERATURE and DERIVED must never claim the MEASURED tier, which is
    reserved for constants fitted to primary data in this repository."""
    for report in REPORTS.values():
        for e in report.found:
            assert e.provenance.startswith(("LITERATURE", "DERIVED"))


def test_the_asymmetry_holds_in_the_current_record():
    """The project's central claim, as far as the data currently goes: effect
    and precision constants are recoverable, failure constants are not. If a
    failure constant is ever recovered this test should be updated, not deleted
    - the interesting question is which one, and from where."""
    readout_hits = failure_hits = 0
    for key, report in REPORTS.items():
        readout_names = {c.name for c in REGISTRY[key].readout.constants}
        for e in report.found:
            if e.constant in readout_names:
                readout_hits += 1
            else:
                failure_hits += 1
    assert readout_hits > 0, "no constants recovered at all - record is empty"
    assert failure_hits == 0, (
        "a failure constant was recovered; update the claim in PLAN.md §6 "
        "rather than deleting this test"
    )


# -- sources ----------------------------------------------------------------

def test_recorded_source_works_with_no_credential():
    src = RecordedSource()
    assert src.available and not src.why_unavailable()
    assert src.report_for("scar_in_a_jar") is SCAR_IN_A_JAR
    assert src.report_for("nonexistent") is None


def test_auto_falls_back_when_paperclip_is_unavailable():
    src = get_source("auto")
    assert src.name in ("paperclip", "recorded")
    if src.name == "recorded":
        assert PaperclipSource().why_unavailable()


def test_paperclip_explains_itself_rather_than_failing_silently():
    why = PaperclipSource(binary="definitely-not-installed").why_unavailable()
    assert "not on PATH" in why


def test_paperclip_command_shape():
    """Testable without a credential, which is the point of splitting command
    construction from execution."""
    cmd = PaperclipSource().command("collagen delamination", limit=5)
    assert cmd[:2] == ["paperclip", "search"]
    assert "collagen delamination" in cmd
    assert "5" in cmd


def test_unknown_source_is_rejected():
    with pytest.raises(ValueError, match="unknown source"):
        get_source("scholar")


@pytest.mark.parametrize(
    "payload",
    [
        '[{"doi":"10.1/x","title":"T","snippet":"S"}]',
        '{"results":[{"doi":"10.1/x","title":"T","snippet":"S"}]}',
        '{"hits":[{"pmid":"123","title":"T","text":"S"}]}',
    ],
)
def test_parse_tolerates_plausible_response_shapes(payload):
    """The schema is unverified until a credential exists, so the parser accepts
    the shapes it might reasonably meet instead of assuming one."""
    hits = PaperclipSource.parse(payload)
    assert len(hits) == 1 and hits[0].title == "T"


@pytest.mark.parametrize("payload", ["not json", "{}", '{"unexpected": 1}', "[]"])
def test_parse_degrades_to_empty_rather_than_raising(payload):
    """Losing one batch mid-event is recoverable; a crash in the middle of a
    two-day build is not."""
    assert PaperclipSource.parse(payload) == []


def test_parse_skips_unreadable_rows_without_dropping_good_ones():
    hits = PaperclipSource.parse('[{"doi":"10.1/a","title":"A"}, "junk", 42]')
    assert len(hits) == 1 and hits[0].source == "10.1/a"


# -- report arithmetic ------------------------------------------------------

def test_recovery_rate_and_searched_count():
    r = CalibrationReport(
        key="k",
        found=(Evidence("a", 1.0, "x", "10.1/x", "q"),),
        blocked=(
            Blocked("b", BlockedReason.NOT_REPORTED, "d", searched="q"),
            Blocked("c", BlockedReason.NOT_YET_SEARCHED, "d"),
        ),
    )
    assert r.total == 3
    assert r.recovery_rate == pytest.approx(1 / 3)
    # 'c' was never looked for, so it supports no claim either way.
    assert r.searched_constants == 2
