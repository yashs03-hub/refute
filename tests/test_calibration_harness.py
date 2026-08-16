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
    and precision constants are recoverable far more often than failure
    constants are, though the six-scaffold sweep found the asymmetry is not
    absolute. Four failure constants have been recovered, each for a stated,
    checkable reason rather than a relaxed standard:

      - `mortality_by_day14` (bleomycin_lung) - a welfare-reporting number a
        regulator obliges authors to publish. Predicted in the module's own
        header comment before the sweep ran.
      - `p_seeding_failure` (fibrosis_on_chip) - a QC yield stated as a
        fraction in a methods section (Mi 2022, 10.3390/mi13101573).
      - `modulus_drift_pct_per_day` and `drift_depends_on_nominal`
        (stiffness_drift) - a 42-day rheology time course (Scott 2020,
        10.1002/adhm.201901593) that also complicates the registry's own
      - `p_death_quiescent` and `p_death_activated` (apoptosis_resistance) -
        apoptotic death fractions measured under standard challenge (Bühling
        2005, 10.1186/1465-9921-6-37).

    This list is pinned by name, not by count, so an unlisted recovery fails
    loudly with a name to go add rather than a number to bump."""
    readout_hits = 0
    failure_names: set[str] = set()
    RECOVERED_FAILURE_CONSTANTS = {
        "mortality_by_day14",
        "p_seeding_failure",
        "modulus_drift_pct_per_day",
        "drift_depends_on_nominal",
        "p_death_quiescent",
        "p_death_activated",
    }
    for key, report in REPORTS.items():
        readout_names = {c.name for c in REGISTRY[key].readout.constants}
        for e in report.found:
            if e.constant in readout_names:
                readout_hits += 1
            else:
                failure_names.add(e.constant)
    assert readout_hits > 0, "no constants recovered at all - record is empty"
    assert failure_names == RECOVERED_FAILURE_CONSTANTS, (
        "a failure constant was recovered or lost that this test does not "
        "name; update the list here and the claim in PLAN.md §6, do not just "
        "widen the assertion"
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


# --------------------------------------------------------------------------
# Verified against the live CLI on 2026-08-15. These replace three tests
# written against a GUESSED contract, all of which were wrong:
#
#   - `--json` was assumed. It is accepted and silently ignored; the output is
#     human-readable text.
#   - `search` was assumed to need no source. It errors without -s.
#   - the parser was written to "degrade to empty rather than raising", which
#     was actively dangerous: it made a changed output format indistinguishable
#     from "the literature contains nothing" - and that is this project's
#     headline finding. A parser able to manufacture that result silently can
#     invalidate the whole claim.
# --------------------------------------------------------------------------

REAL_SEARCH_OUTPUT = """Found 2 papers  [s_39d543ad]

  1. Harnessing the
Biomimetic Effect of Macromolecular
Crowding in the Cell-Derived Model of Clubfoot Fibrosis
     Martina Doubkova, Jarmila Knitlova, David Vondrasek, Adam Eckhardt, ...
     PMC11480992 · PMC · 2024-08-30
     https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11480992/
     "A biomimetic in vitro model using macromolecular crowding was developed."

  2. A preliminary preclinical assessment of macromolecular crowding
     Kyriakos Spanoudes, Laura Trujillo Cubillo, Stefanie H. Korntner, ...
     PMC12830566 · PMC · 2026-01-21
     https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12830566/
     "Macromolecular crowding was used to culture human mesenchymal cells."

[285ms, saved to s_39d543ad]
"""


def test_parse_reads_the_real_cli_output():
    hits = PaperclipSource.parse(REAL_SEARCH_OUTPUT)
    assert len(hits) == 2
    assert hits[0].source == "PMC11480992"
    assert hits[1].source == "PMC12830566"
    assert "biomimetic in vitro model" in hits[0].snippet


def test_parse_reassembles_titles_that_wrap_across_lines():
    """Real titles wrap, and the continuation lines are not indented like the
    rest of the entry - which is exactly where a naive line-based parser breaks."""
    hits = PaperclipSource.parse(REAL_SEARCH_OUTPUT)
    assert "Macromolecular" in hits[0].title and "Clubfoot" in hits[0].title
    # The author line must NOT end up in the title.
    assert "Doubkova" not in hits[0].title


def test_result_id_is_recoverable_for_chaining_grep():
    assert PaperclipSource.result_id(REAL_SEARCH_OUTPUT) == "s_39d543ad"


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "Error: search requires a source flag (-s).",
        '[{"doi":"10.1/x","title":"T"}]',   # the shape that was WRONGLY assumed
        "",
    ],
)
def test_parse_raises_rather_than_reporting_an_empty_literature(payload):
    """The property that matters most in this file.

    Zero hits must be something the CLI *said*, never something an exception
    handler produced. Reversed deliberately from the original test, which
    asserted the opposite.
    """
    with pytest.raises(ValueError):
        PaperclipSource.parse(payload)


@pytest.mark.parametrize(
    "payload",
    ["No matches for /mortalit/ in s_b5eb83c7", "Found 0 papers  [s_abc123]"],
)
def test_a_genuine_zero_result_is_not_an_error(payload):
    """The other half: the tool saying 'nothing' is data, and must parse."""
    assert PaperclipSource.parse(payload) == []


def test_parse_catches_a_header_that_no_longer_matches_its_body():
    """If the CLI says it found papers and none parse, the format has moved."""
    with pytest.raises(ValueError, match="none could be parsed"):
        PaperclipSource.parse("Found 5 papers  [s_a1b2]\n\n   ??? unexpected")


def test_search_command_carries_a_source():
    """`search` errors without -s/--source. This was the first contract break."""
    cmd = PaperclipSource().command("collagen delamination", limit=5)
    assert "-s" in cmd
    assert cmd[cmd.index("-s") + 1]
    assert "--json" not in cmd, "--json is silently ignored by the real CLI"


def test_grep_command_scopes_to_a_result_set():
    """Failure constants are a SHAPE in a methods section, not a topic - grep
    is the tool, and `map` is gated to GXL testers on this account."""
    cmd = PaperclipSource().grep_command("mortalit", from_id="s_abc", context=2)
    assert cmd[:2] == ["paperclip", "grep"]
    assert "--from" in cmd and "s_abc" in cmd
    assert "-C" in cmd and "2" in cmd


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
