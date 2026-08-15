"""The join between the two layers, and the two ways it is allowed to say no.

`refute.intake` is the only place in the pipeline where a piece of layer 1's
prose becomes an assay key and a `DesignSpec`. Two failure modes are worth more
attention than everything else it does, and both are failures in the permissive
direction:

  1. **A selector that always picks something.** `refute.gate` records the
     original version of this bug from the other side - a scope guard that
     refused everything and passed the suite, because a test that only checks
     refusals is satisfied by refusing everything. The mirror image is a
     selector with no empty outcome, which maps a zebrafish behavioural readout
     onto a fibrin gel and lets the whole pipeline be confidently about the
     wrong apparatus. So both directions are pinned here: the absurd residual
     must return none-of-these, AND the canonical fibrin residual must come
     through with `out_of_twin_scope` still empty.

  2. **A parse failure reported as a bad design.** That confound is the reason
     this project holds the extractor constant. Every path where extraction
     does not produce a spec is checked for what it says, not just for the fact
     that it stopped.

Nothing here touches the network or needs a credential. The extractor is a
plain callable throughout, which is the point of injecting it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from refute.assays import REGISTRY, get
from refute.design import EXPERIMENT_4_AS_RUN, DesignSpec
from refute.gate import Route, route_design
from refute.intake import (
    EVIDENCE_FLOOR,
    HYPOTHESIS_WEIGHT,
    MIN_MATCHED_TERMS,
    NO_EXTRACTOR_MESSAGE,
    AssayCandidate,
    AssaySelection,
    Extraction,
    ExtractionFailure,
    NoExtractorConfigured,
    brief_for_extractor,
    extract_design,
    intake,
    select_assay,
    terms,
)
from refute.resolve import ResolutionSet

# --- fixtures ---------------------------------------------------------------

FIBRIN_RESIDUAL = (
    "Whether MSC-conditioned media suppresses TGF-b1-driven contraction of "
    "anchored fibrin gel constructs seeded with primary human synovial "
    "fibroblasts, read as projected gel area from per-well images."
)

ZEBRAFISH_RESIDUAL = (
    "Whether the startle-response behaviour of zebrafish larvae at 5 days post "
    "fertilisation is altered by chronic exposure to the compound."
)

COLLAGEN_RESIDUAL = (
    "Whether TGF-b1 increases deposited collagen I under macromolecular "
    "crowding."
)


def fake_extractor(_text: str) -> DesignSpec:
    """A DesignSpec with nothing to complain about. Stands in for the model."""
    return EXPERIMENT_4_AS_RUN.model_copy()


def exploding_extractor(_text: str) -> DesignSpec:
    raise RuntimeError("provider exploded")


@dataclass
class FakeOpenItem:
    """Shaped like §5.4's `OpenItem`. Not imported - see `_residual_text`."""

    statement: str
    why: str = "needs_new_data"
    searched: bool = True
    queries_run: tuple[str, ...] = ()


@dataclass
class FakeHandoff:
    """Shaped like §5.4's `Handoff`, duck-typed on purpose.

    `refute.handoff` is being written concurrently. Importing it here would make
    this module's tests fail for reasons that have nothing to do with this
    module, which is exactly the coupling the seam exists to avoid.
    """

    question: str = ""
    hypothesis: str = ""
    residual: tuple = ()
    findings: tuple = field(default_factory=tuple)
    limits: str = ""


# ===========================================================================
# Job 1 - assay selection
# ===========================================================================


def test_a_fibrin_contracture_residual_routes_to_fibrin_contracture():
    selection = select_assay(FIBRIN_RESIDUAL)
    assert not selection.none_of_these
    assert selection.best.key == "fibrin_contracture"


def test_the_leading_candidate_names_the_terms_it_matched_on():
    """A deterministic selector's whole advantage is that you can argue with it."""
    best = select_assay(FIBRIN_RESIDUAL).best
    assert {"fibrin", "anchored", "contraction"} <= set(best.terms)
    for term in ("fibrin", "anchored"):
        assert term in best.why


def test_every_candidate_carries_a_reason():
    selection = select_assay(FIBRIN_RESIDUAL)
    for candidate in selection.candidates + selection.near_misses:
        assert candidate.why.strip(), f"{candidate.key} was ranked with no reason"


def test_candidates_are_ranked_best_first():
    selection = select_assay(
        "Whether fibroblasts deposit more matrix under crowding, and whether "
        "the deposited matrix survives decellularisation."
    )
    scores = [c.score for c in selection.candidates]
    assert scores == sorted(scores, reverse=True)
    assert len(scores) >= 2


def test_each_candidate_is_a_real_registry_key():
    selection = select_assay(FIBRIN_RESIDUAL)
    for candidate in selection.candidates:
        assert candidate.key in REGISTRY


# --- none-of-these, the outcome that must exist -----------------------------


def test_a_readout_this_registry_cannot_measure_is_none_of_these():
    """The load-bearing negative. A behavioural readout in zebrafish is not a
    fibrosis assay, and a selector that always picks something would say it is."""
    selection = select_assay(ZEBRAFISH_RESIDUAL)
    assert selection.none_of_these
    assert selection.candidates == ()
    assert selection.best is None


def test_none_of_these_says_what_the_registry_does_cover():
    """A refusal that does not say what would lift it is indistinguishable from
    the system being broken - the same rule `refute.gate` holds for REFUSE."""
    why = select_assay(ZEBRAFISH_RESIDUAL).why
    assert "No assay in this registry fits" in why
    assert f"{EVIDENCE_FLOOR:.1f}" in why
    assert str(MIN_MATCHED_TERMS) in why
    # It names what the registry does measure, so the gap is legible.
    assert "fill per well" in why
    # And it is a limit, not a verdict on the question.
    assert "limit of the registry" in why


def test_a_near_miss_is_recorded_rather_than_silently_dropped():
    """§6.4: the discarded material is where the improvement lives."""
    selection = select_assay(ZEBRAFISH_RESIDUAL)
    assert selection.near_misses
    for miss in selection.near_misses:
        assert miss.matched
        assert "below the" in miss.why


def test_a_single_incidental_word_cannot_select_an_assay():
    """One shared noun is a coincidence, not evidence about the apparatus."""
    selection = select_assay("Does chronic exposure change anything at all?")
    assert selection.none_of_these


def test_an_empty_residual_selects_nothing():
    selection = select_assay("")
    assert selection.none_of_these
    assert selection.near_misses == ()


def test_an_empty_registry_is_none_of_these_rather_than_a_crash():
    selection = select_assay(FIBRIN_RESIDUAL, registry={})
    assert selection.none_of_these
    assert selection.considered == ()
    assert "the registry is empty" in selection.why


# --- confidence -------------------------------------------------------------


def test_a_clear_leader_reports_itself_decisive():
    assert select_assay(FIBRIN_RESIDUAL).decisive


def test_a_close_field_does_not_report_itself_decisive():
    """Returning one key with false confidence is the failure the return type is
    shaped to avoid, so a near-tie has to say it is a near-tie."""
    selection = select_assay(
        "Whether fibroblasts deposit more matrix under crowding, and whether "
        "the deposited matrix survives decellularisation."
    )
    assert len(selection.candidates) >= 2
    assert not selection.decisive
    assert selection.runner_up is not None
    assert "close behind" in selection.why


def test_the_selection_says_when_a_candidate_cannot_be_scored():
    """Six of seven protocols are scaffolds. Selecting one is fine; implying it
    would produce a number is not."""
    best = select_assay(COLLAGEN_RESIDUAL).best
    assert best.key == "scar_in_a_jar"
    assert best.runnable is False
    assert "SCAFFOLD" in best.why


def test_the_measured_protocol_is_marked_as_scoreable():
    best = select_assay(FIBRIN_RESIDUAL).best
    assert best.runnable is True
    assert "measured" in best.why


# --- the mechanism ----------------------------------------------------------


def test_selection_is_deterministic():
    """No model call, so two runs are not merely similar."""
    first = select_assay(FIBRIN_RESIDUAL)
    second = select_assay(FIBRIN_RESIDUAL)
    assert [(c.key, c.score) for c in first.candidates] == [
        (c.key, c.score) for c in second.candidates
    ]


def test_the_hypothesis_supports_a_match_at_half_the_weight_of_the_residual():
    """§5.1: the residual is the brief and everything else is context. Context
    may break a tie; it may not decide one on its own."""
    as_residual = select_assay(FIBRIN_RESIDUAL, "")
    as_hypothesis = select_assay("", FIBRIN_RESIDUAL)
    assert as_hypothesis.best is not None
    assert as_hypothesis.best.key == as_residual.best.key
    assert as_hypothesis.best.score == pytest.approx(
        as_residual.best.score * HYPOTHESIS_WEIGHT
    )


def test_terms_folds_the_surface_forms_that_actually_collide():
    assert terms("contractures gels fibroblasts imaged") == {
        "contraction",
        "gel",
        "fibroblast",
        "imaging",
    }


def test_terms_does_not_mangle_words_ending_in_is_or_ss():
    """'fibrin' and 'fibrosis' differ by two characters and by a whole
    apparatus, which is why the morphology here is deliberately timid."""
    folded = terms("fibrosis lysis stress analysis")
    assert "fibrosis" in folded and "lysis" in folded
    assert "stress" in folded and "analysis" in folded


def test_terms_drops_ordinary_english():
    assert terms("the and of with because however") == set()


# ===========================================================================
# Job 2 - prose to DesignSpec
# ===========================================================================


def test_without_an_extractor_it_says_so_rather_than_guessing():
    with pytest.raises(NoExtractorConfigured) as excinfo:
        extract_design("four arms of three wells", extractor=None)
    assert "No extractor is configured" in str(excinfo.value)


def test_an_extractor_that_raises_is_a_parsing_failure_not_a_bad_design():
    """The confound the whole project holds the extractor constant to avoid."""
    with pytest.raises(ExtractionFailure) as excinfo:
        extract_design("some prose", exploding_extractor)
    message = str(excinfo.value)
    assert "parsing failure on our side" in message
    assert "not a judgement about your experiment" in message
    # Nothing in it is a claim about the experiment.
    for verdict_word in ("underpowered", "infeasible", "bad", "flawed"):
        assert verdict_word not in message.lower()


def test_an_extraction_failure_keeps_the_original_cause():
    """The wording is non-judgemental; the traceback still has to be debuggable."""
    with pytest.raises(ExtractionFailure) as excinfo:
        extract_design("some prose", exploding_extractor)
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert "provider exploded" in str(excinfo.value.__cause__)


def test_an_extractor_returning_the_wrong_type_is_also_a_parsing_failure():
    """A duck-typed object reaching the simulator is a worse error one step on."""
    with pytest.raises(ExtractionFailure) as excinfo:
        extract_design("prose", lambda _t: {"conditions": ["N-T"]})
    assert "not a DesignSpec" in str(excinfo.value)
    assert "not a judgement about your experiment" in str(excinfo.value)


def test_a_clean_spec_comes_through_untouched():
    """The false-positive direction: nothing here invents a scope violation."""
    spec = extract_design("prose", fake_extractor)
    assert spec.out_of_twin_scope == []
    assert spec.conditions == EXPERIMENT_4_AS_RUN.conditions


def test_the_extractors_own_scope_declaration_is_preserved():
    declared = EXPERIMENT_4_AS_RUN.model_copy(
        update={"out_of_twin_scope": ["collagen I matrix"]}
    )
    spec = extract_design("prose", lambda _t: declared)
    assert spec.unmodelled() == ["collagen I matrix"]


def test_unmodelled_reasons_are_merged_without_duplicating():
    declared = EXPERIMENT_4_AS_RUN.model_copy(
        update={"out_of_twin_scope": ["collagen I matrix"]}
    )
    spec = extract_design(
        "prose",
        lambda _t: declared,
        unmodelled=["collagen I matrix", "no protocol fits"],
    )
    assert spec.out_of_twin_scope == ["collagen I matrix", "no protocol fits"]


def test_blank_unmodelled_entries_do_not_block_a_scoreable_design():
    """`DesignSpec.unmodelled` already discards blanks; this makes sure nothing
    upstream turns one into a refusal first."""
    spec = extract_design("prose", fake_extractor, unmodelled=["", "   "])
    assert spec.out_of_twin_scope == []


def test_the_source_object_is_not_mutated():
    """`EXPERIMENT_4_AS_RUN` is a module-level singleton and the calibration
    target. Writing scope reasons into it would poison every other test."""
    extract_design("prose", lambda _t: EXPERIMENT_4_AS_RUN, unmodelled=["something"])
    assert EXPERIMENT_4_AS_RUN.out_of_twin_scope == []


def test_the_brief_leads_with_the_residual_and_carries_the_hypothesis():
    brief = brief_for_extractor("the residual sentence", "the hypothesis sentence")
    assert "the residual sentence" in brief
    assert "the hypothesis sentence" in brief
    assert brief.index("HYPOTHESIS") < brief.index("RESIDUAL")


def test_the_brief_says_when_no_hypothesis_was_supplied():
    brief = brief_for_extractor("the residual sentence")
    assert "(not supplied)" in brief


# ===========================================================================
# Job 3 - the seam
# ===========================================================================


def test_intake_accepts_a_plain_residual_string():
    result = intake(FIBRIN_RESIDUAL, fake_extractor)
    assert result.residual == FIBRIN_RESIDUAL
    assert result.selection.best.key == "fibrin_contracture"
    assert result.design is not None
    assert result.ready


def test_intake_accepts_a_handoff_shaped_object():
    handoff = FakeHandoff(
        question="Does MSC-CM suppress contraction?",
        hypothesis="MSC-CM suppresses TGF-b1-driven contraction in synovial fibroblasts.",
        residual=(
            FakeOpenItem("Whether the effect survives to a Day 10 endpoint."),
            FakeOpenItem(
                "Whether anchored fibrin gel area is still measurable at that point."
            ),
        ),
    )
    result = intake(handoff, fake_extractor)
    assert "anchored fibrin gel area" in result.residual
    assert "Day 10 endpoint" in result.residual
    assert result.hypothesis == handoff.hypothesis
    assert result.selection.best.key == "fibrin_contracture"


def test_intake_accepts_a_residual_that_is_already_a_string_attribute():
    result = intake(FakeHandoff(residual=FIBRIN_RESIDUAL), fake_extractor)
    assert result.residual == FIBRIN_RESIDUAL


def test_intake_falls_back_to_the_question_when_there_is_no_hypothesis():
    handoff = FakeHandoff(question="Does MSC-CM suppress contraction?", residual=FIBRIN_RESIDUAL)
    assert intake(handoff, fake_extractor).hypothesis == handoff.question


def test_intake_refuses_an_object_with_no_residual():
    """Stringifying the object instead would match on its class name, which is
    the kind of quiet nonsense that is very hard to find later."""
    with pytest.raises(TypeError) as excinfo:
        intake(object(), fake_extractor)
    assert "residual" in str(excinfo.value)


# --- the two honest stops ---------------------------------------------------


def test_intake_without_an_extractor_still_selects_an_assay():
    """Selection needs no credential, so a missing model must not cost it."""
    result = intake(FIBRIN_RESIDUAL, extractor=None)
    assert result.extraction is Extraction.NO_EXTRACTOR
    assert result.design is None
    assert result.note == NO_EXTRACTOR_MESSAGE
    assert result.selection.best.key == "fibrin_contracture"
    assert not result.ready


def test_intake_reports_an_extraction_failure_without_judging_the_design():
    result = intake(FIBRIN_RESIDUAL, exploding_extractor)
    assert result.extraction is Extraction.FAILED
    assert result.design is None
    assert "parsing failure on our side" in result.note
    assert "not a judgement about your experiment" in result.note
    assert not result.ready
    assert any("says nothing about the experiment" in line for line in result.narrative)


def test_the_three_reasons_ready_is_false_are_distinguishable():
    """No assay, no extractor, and a failed extractor are not the same problem,
    and two of them are not problems with the design at all."""
    no_assay = intake(ZEBRAFISH_RESIDUAL, fake_extractor)
    no_model = intake(FIBRIN_RESIDUAL, extractor=None)
    failed = intake(FIBRIN_RESIDUAL, exploding_extractor)

    assert not no_assay.ready and no_assay.extraction is Extraction.EXTRACTED
    assert no_assay.selection.none_of_these
    assert not no_model.ready and no_model.extraction is Extraction.NO_EXTRACTOR
    assert not failed.ready and failed.extraction is Extraction.FAILED
    assert not no_model.selection.none_of_these
    assert not failed.selection.none_of_these


# --- scope ------------------------------------------------------------------


def test_a_residual_no_protocol_models_populates_out_of_twin_scope():
    """The join. The registry having nothing for this residual is a fact only
    this module knows, and the gate can only act on it through this field."""
    result = intake(ZEBRAFISH_RESIDUAL, fake_extractor)
    assert result.selection.none_of_these
    assert result.design is not None
    reasons = result.design.unmodelled()
    assert reasons
    assert "no protocol in the assay registry models this residual" in reasons[0]


def test_an_in_scope_residual_leaves_out_of_twin_scope_empty():
    """The false-positive guard, and the more important half of the pair.

    A guard that fires on the registry's own reference assay is a fail-always
    guard, and it passes every test that only checks refusals.
    """
    result = intake(FIBRIN_RESIDUAL, fake_extractor)
    assert result.design.out_of_twin_scope == []
    assert result.design.unmodelled() == []


def test_the_out_of_scope_reason_reaches_the_gate_as_out_of_scope():
    """End to end through the real gate: an unmodellable residual must not be
    handed to a protocol as though it were an ordinary design."""
    result = intake(ZEBRAFISH_RESIDUAL, fake_extractor)
    decision = route_design(
        result.design,
        get("fibrin_contracture"),
        ResolutionSet(assay_key="fibrin_contracture", requirement_version="test"),
    )
    assert decision.route is Route.OUT_OF_SCOPE
    assert decision.unmodelled


def test_an_in_scope_residual_is_not_routed_out_of_scope():
    """The mirror of the test above, and the one that catches refuse-everything."""
    result = intake(FIBRIN_RESIDUAL, fake_extractor)
    decision = route_design(
        result.design,
        get("fibrin_contracture"),
        ResolutionSet(assay_key="fibrin_contracture", requirement_version="test"),
    )
    assert decision.route is not Route.OUT_OF_SCOPE
    assert decision.unmodelled == ()
    # It falls through for want of resolved constants, which is a different
    # thing entirely and is the resolver's problem, not intake's.
    assert decision.route is Route.REFUSE


# --- what it hands the model, and how often -------------------------------


def test_the_extractor_is_called_exactly_once_and_shown_the_residual():
    seen: list[str] = []

    def recording(text: str) -> DesignSpec:
        seen.append(text)
        return EXPERIMENT_4_AS_RUN.model_copy()

    intake(
        FakeHandoff(hypothesis="MSC-CM suppresses contraction.", residual=FIBRIN_RESIDUAL),
        recording,
    )
    assert len(seen) == 1
    assert FIBRIN_RESIDUAL in seen[0]
    assert "MSC-CM suppresses contraction." in seen[0]


def test_selection_happens_before_the_model_is_asked_for_anything():
    """Selection is free and offline; it must not be conditional on a model call
    that may never succeed."""
    result = intake(FIBRIN_RESIDUAL, exploding_extractor)
    assert result.selection.best.key == "fibrin_contracture"


# --- the narrative ----------------------------------------------------------


def test_the_narrative_records_that_selection_needed_no_model():
    result = intake(FIBRIN_RESIDUAL, fake_extractor)
    assert result.narrative
    assert any("no model call" in line for line in result.narrative)
    assert result.render() == "\n".join(result.narrative)


def test_the_narrative_names_the_arms_it_extracted():
    result = intake(FIBRIN_RESIDUAL, fake_extractor)
    assert any("4 arm(s), 3 per arm" in line for line in result.narrative)


def test_a_design_that_declines_to_run_is_described_as_a_position():
    """`assigns_wells` is False for a design that says no plate should be cast.
    That is the verdict this project itself reports, so it is not malformed."""
    declining = DesignSpec(
        conditions=[],
        replicates_per_condition=0,
        imaging_times_h=[1.0, 72.0],
        treatment_time_h=1.0,
        endpoint_time_h=72.0,
        antifibrinolytic=False,
        normalise_to_own_baseline=True,
        locked_imaging_protocol=True,
    )
    result = intake(FIBRIN_RESIDUAL, lambda _t: declining)
    assert any("declines to run" in line for line in result.narrative)
    assert result.extraction is Extraction.EXTRACTED


def test_intake_exposes_the_selected_protocol_object():
    result = intake(FIBRIN_RESIDUAL, fake_extractor)
    assert result.protocol is get("fibrin_contracture")


def test_no_protocol_is_exposed_when_nothing_fits():
    assert intake(ZEBRAFISH_RESIDUAL, fake_extractor).protocol is None


# --- shape ------------------------------------------------------------------


def test_the_selection_renders_its_candidates_and_its_misses():
    selection = select_assay(FIBRIN_RESIDUAL)
    lines = selection.render().splitlines()
    assert lines[0] == selection.why
    assert lines[1].startswith("  1. fibrin_contracture")
    assert any("below the floor" in line for line in lines)
    for miss in selection.near_misses:
        assert any(miss.key in line for line in lines)


def test_an_empty_selection_is_falsey_in_the_way_that_matters():
    empty = AssaySelection(
        residual="",
        hypothesis="",
        candidates=(),
        near_misses=(),
        considered=(),
        why="nothing",
    )
    assert empty.none_of_these
    assert empty.best is None
    assert empty.runner_up is None
    assert not empty.decisive


def test_a_lone_candidate_is_decisive():
    lone = AssaySelection(
        residual="",
        hypothesis="",
        candidates=(
            AssayCandidate(
                key="k",
                name="n",
                score=9.0,
                matched=(),
                status=get("fibrin_contracture").status,
                runnable=True,
                why="because",
            ),
        ),
        near_misses=(),
        considered=("k",),
        why="one fits",
    )
    assert lone.decisive
    assert lone.runner_up is None
