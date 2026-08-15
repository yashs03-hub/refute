"""What `refute.vocabulary` may and may not claim.

The module exists because SPEC 5.3 property 4 requires one agreed vocabulary and
SPEC 12 item 2 says agree it early, before either side hardcodes anything. It
cannot deliver the agreement on its own, so what it delivers instead is a claim
about this side: these terms, from these fields, and nothing else. These tests
protect the two halves of that claim.

  1. Nothing is invented. Every declared term is checked back against the
     protocol field it says it came from, by a walk over the registry written
     here rather than by asking the module to confirm itself.

  2. Nothing unknown passes through. An unmapped term returns `None`, never the
     string it was given. The failure mode 5.3 is about is silent: a raw name
     carried onward as though it were understood produces a finding matched to
     the wrong protocol, and nothing in the output says so.

The rest cover the report - which is the deliverable, since "we have not agreed
a vocabulary" needs to be runnable rather than filed - and the alias map, which
has to accept the agreement without any other behaviour moving.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import pytest

from refute.assays import REGISTRY
from refute.assays.base import AssayProtocol
from refute.vocabulary import (
    ALIASES,
    FACETS,
    VOCABULARY,
    Derivation,
    Facet,
    Term,
    UnboundTermError,
    Vocabulary,
    _perturbation_prefix,
    coverage_report,
    normalise,
    require_term,
    terms,
    translate,
    unbound_terms,
)

# Terms a layer 1 finding might plausibly carry. None of them is declared here,
# and none of them should resolve until somebody agrees a binding.
LAYER_1_SHAPED = (
    "TGF-β1",
    "TGF-beta1",
    "fibroblast",
    "myofibroblast",
    "human",
    "lung",
    "synovium",
    "alpha-SMA",
    "collagen I",
    "Ashcroft score",
)


def _field_values(protocol: AssayProtocol, source_field: str) -> set[str]:
    """Everything `source_field` holds for one protocol, read off the registry.

    Deliberately a second implementation. A traceability check that calls the
    extractor it is checking only proves the extractor is deterministic.
    """
    if source_field == "AssayProtocol.unit":
        return {protocol.unit}
    if source_field == "ReadoutSpec.name":
        return {protocol.readout.name}
    if source_field == "Constant.name":
        return {c.name for c in protocol.all_constants()}
    if source_field.startswith("AssayProtocol."):
        value = getattr(protocol, source_field.split(".", 1)[1], None)
        return {value} if isinstance(value, str) and value else set()
    raise AssertionError(f"no independent reader for {source_field!r}")


# --- 1. derived, not invented ------------------------------------------------


@pytest.mark.parametrize("term", VOCABULARY.terms, ids=lambda t: f"{t.facet.value}:{t.text}")
def test_every_declared_term_traces_to_a_protocol_field(term: Term):
    """Each term names its protocols, and each of them really does hold it."""
    assert term.protocols, f"{term.text!r} is declared by no protocol"
    assert term.raw, f"{term.text!r} records no source string"
    for key in term.protocols:
        assert key in REGISTRY, f"{term.text!r} cites unknown protocol {key!r}"
        available = _field_values(REGISTRY[key], term.source_field)
        assert set(term.raw) & available, (
            f"{term.text!r} claims to come from {term.source_field} of {key}, "
            f"which holds {sorted(available)}"
        )


def test_a_field_derived_term_is_its_source_string_and_nothing_else():
    """FIELD means no judgement was applied - only case and whitespace."""
    for term in VOCABULARY.terms:
        if term.derivation is Derivation.FIELD:
            assert {normalise(r) for r in term.raw} == {term.text}


def test_every_protocol_contributes_its_unit_and_its_readout():
    """The other direction: nothing declared in the registry is quietly dropped.

    A term list that omits a protocol looks complete and answers wrongly for the
    assay it forgot, which is harder to notice than an extra term.
    """
    units = {t.text for t in terms(Facet.EXPERIMENTAL_UNIT)}
    readouts = {t.text for t in terms(Facet.READOUT)}
    for protocol in REGISTRY.values():
        assert normalise(protocol.unit) in units, protocol.key
        assert normalise(protocol.readout.name) in readouts, protocol.key


def test_every_protocol_is_represented_somewhere():
    covered = {key for term in VOCABULARY.terms for key in term.protocols}
    assert covered == set(REGISTRY)


def test_the_perturbation_rule_is_syntactic_and_fails_closed():
    """It reads this repository's constant-naming convention, not biology.

    A crude rule has to reject rather than guess: `mortality_severity_coupling`
    yielding "mortality_severity" would put a term in the registry that names
    no perturbation, and it would be indexed, reported and eventually agreed.
    """
    assert _perturbation_prefix("tgfb_fold_change") == "tgfb"
    assert _perturbation_prefix("bleomycin_effect") == "bleomycin"
    assert _perturbation_prefix("mortality_severity_coupling") is None
    assert _perturbation_prefix("measurement_cv") is None
    for protocol in REGISTRY.values():
        for constant in protocol.all_constants():
            prefix = _perturbation_prefix(constant.name)
            assert prefix is None or "_" not in prefix, constant.name


# --- 2. an unbound term is None ----------------------------------------------


@pytest.mark.parametrize("term", LAYER_1_SHAPED)
def test_an_unbound_term_returns_none(term: str):
    assert translate(term) is None


@pytest.mark.parametrize("term", LAYER_1_SHAPED)
def test_an_unbound_term_is_never_handed_back_as_itself(term: str):
    """The passthrough that would make this module dangerous."""
    result = translate(term)
    assert result is None or isinstance(result, Term)
    assert result != term


def test_translate_resolves_a_declared_term_to_its_own_record():
    found = translate("well")
    assert found is not None
    assert found.facet is Facet.EXPERIMENTAL_UNIT
    assert "fibrin_contracture" in found.protocols


def test_translate_is_case_and_whitespace_insensitive_and_nothing_more():
    assert translate("  WELL ") is translate("well")
    assert translate("strain energy") is None, (
        "folding underscores would decide, invisibly, that two names mean the "
        "same thing - which is the alias map's job"
    )


def test_normalise_does_not_invent_equivalences():
    assert normalise(" Well\t") == "well"
    assert normalise("TGF-β1") != "tgfb"


def test_require_term_raises_and_says_what_to_do_next():
    with pytest.raises(UnboundTermError, match="coverage_report"):
        require_term("TGF-β1")
    assert require_term("well").text == "well"


def test_unbound_terms_returns_the_spellings_it_was_given():
    given = ["Well", "TGF-β1", "fill", "human lung fibroblast"]
    assert unbound_terms(given) == ["TGF-β1", "human lung fibroblast"]


def test_unbound_terms_keeps_input_order_and_collapses_repeats():
    given = ["myofibroblast", "well", "MYOFIBROBLAST", "alpha-SMA", "myofibroblast"]
    assert unbound_terms(given) == ["myofibroblast", "alpha-SMA"]


def test_unbound_terms_is_empty_when_everything_is_declared():
    assert unbound_terms([t.text for t in VOCABULARY.terms]) == []


# --- 3. the report -----------------------------------------------------------

HEADINGS = (
    "WHAT THIS SIDE DECLARES",
    "WHAT THIS SIDE CANNOT DECLARE",
    "DECLARED BUT NOT YET A CONTROLLED TERM",
    "BOUND FROM LAYER 1",
    "TO OPEN THE CONVERSATION, ASK",
)


def _section(report: str, heading: str) -> str:
    """One section of the report, without the ones after it.

    The sections say different things about the same terms - declared here,
    missing there - so a test that greps the whole report cannot tell which one
    it found the word in.
    """
    assert heading in report, f"the report dropped {heading!r}"
    _, _, tail = report.partition(heading)
    for later in HEADINGS[HEADINGS.index(heading) + 1:]:
        tail = tail.partition(later)[0]
    return tail


def test_the_report_names_every_declared_term():
    report = coverage_report()
    for term in VOCABULARY.terms:
        assert term.text in report, term.text


def test_the_report_names_the_facets_this_side_cannot_declare():
    """The absence is the finding. It has to survive into the output."""
    report = coverage_report()
    missing = _section(report, "WHAT THIS SIDE CANNOT DECLARE")
    for facet in (Facet.SPECIES, Facet.TISSUE, Facet.CELL_TYPE):
        assert not VOCABULARY.by_facet(facet), f"{facet.value} became declared"
        assert facet.value in missing, facet.value
    assert "AssayProtocol.species" in missing
    assert Facet.READOUT.value in _section(report, "WHAT THIS SIDE DECLARES")


def test_the_report_says_the_alias_map_is_empty():
    report = coverage_report()
    assert "0 aliases bound" in report
    assert "BOUND FROM LAYER 1" in report


def test_the_report_names_the_terms_that_are_not_yet_controlled_terms():
    """Field values that are phrases. Honest, and unusable until decided."""
    loose = VOCABULARY.uncontrolled()
    assert loose, "expected at least the disjunctive readout names"
    section = _section(coverage_report(), "DECLARED BUT NOT YET A CONTROLLED TERM")
    for term in loose:
        assert term.text in section, term.text


def test_the_report_shows_where_a_derived_term_came_from():
    """A NAME-derived term is weaker, so the report prints the identifier."""
    assert "tgfb_fold_change" in coverage_report()


def test_the_report_states_it_is_not_agreed():
    assert "NOT AGREED" in coverage_report()


# --- 4. no two spellings of one term -----------------------------------------


def _fingerprints(vocabulary: Vocabulary) -> dict[str, list[str]]:
    seen: dict[str, list[str]] = {}
    for term in vocabulary.terms:
        key = "".join(c for c in term.text if c.isalnum())
        seen.setdefault(key, []).append(f"{term.facet.value}:{term.text}")
    return seen


def test_no_two_declared_terms_are_one_term_under_different_spellings():
    clashes = {k: v for k, v in _fingerprints(VOCABULARY).items() if len(v) > 1}
    assert not clashes, f"same term, two spellings: {clashes}"


def test_a_duplicate_spelling_is_rejected_at_construction():
    """Loudly, at build time. A silent duplicate is the drift 5.3 describes."""
    made_up = (
        Term("strain_energy", Facet.READOUT, Derivation.FIELD,
             "ReadoutSpec.name", ("traction_force",), ("strain_energy",)),
        Term("strain energy", Facet.PERTURBATION, Derivation.NAME,
             "Constant.name", ("traction_force",), ("strain energy",)),
    )
    with pytest.raises(ValueError, match="two"):
        Vocabulary(terms=made_up)


# --- 5. the alias map --------------------------------------------------------


def test_the_shipped_alias_map_is_empty():
    """Not an oversight. Half these terms are layer 1's to name."""
    assert dict(ALIASES) == {}
    assert dict(VOCABULARY.aliases) == {}


def test_adding_an_alias_resolves_exactly_one_more_term():
    probe = [t.text for t in VOCABULARY.terms] + list(LAYER_1_SHAPED)
    before = {p for p in probe if VOCABULARY.translate(p) is not None}

    after_vocab = VOCABULARY.with_alias("TGF-β1", "tgfb")
    after = {p for p in probe if after_vocab.translate(p) is not None}

    assert after - before == {"TGF-β1"}
    assert before - after == set()
    assert after_vocab.translate("TGF-β1") == VOCABULARY.translate("tgfb")


def test_adding_an_alias_changes_nothing_else():
    after_vocab = VOCABULARY.with_alias("TGF-β1", "tgfb")
    assert after_vocab.terms == VOCABULARY.terms
    assert dict(VOCABULARY.aliases) == {}, "the default vocabulary was mutated"
    assert translate("TGF-β1") is None, "the module-level default moved"
    assert dict(after_vocab.aliases) == {"tgf-β1": "tgfb"}


def test_an_alias_is_shown_in_the_report():
    report = VOCABULARY.with_alias("TGF-β1", "tgfb").report()
    assert "1 aliases bound" in report
    assert "tgf-β1 -> tgfb" in report


def test_an_alias_must_bind_to_a_term_this_side_declares():
    """Aliases bind their terms to ours. The other direction invents a term."""
    with pytest.raises(ValueError, match="does not declare"):
        VOCABULARY.with_alias("TGF-β1", "transforming_growth_factor_beta_1")


def test_an_alias_may_not_shadow_a_declared_term():
    with pytest.raises(ValueError, match="shadows"):
        VOCABULARY.with_alias("well", "chip")


def test_aliases_are_canonicalised_however_the_vocabulary_was_built():
    """`with_alias` is not the only door, so the invariant cannot live there.

    Constructed directly, an alias whose key or target is a stray spelling must
    still resolve - otherwise a vocabulary loaded from an agreed list of pairs
    would raise on lookup rather than at construction, which is the wrong end.
    """
    direct = Vocabulary(terms=VOCABULARY.terms, aliases={"  TGF-Beta ": "  WELL "})
    assert dict(direct.aliases) == {"tgf-beta": "well"}
    assert direct.translate("TGF-Beta") == VOCABULARY.translate("well")


def test_aliases_accumulate():
    bound = VOCABULARY.with_alias("TGF-β1", "tgfb").with_alias("murine", "animal")
    assert bound.translate("TGF-β1").text == "tgfb"
    assert bound.translate("murine").text == "animal"
    assert len(bound.aliases) == 2


def test_an_alias_may_not_be_rebound_silently():
    bound = VOCABULARY.with_alias("TGF-β1", "tgfb")
    with pytest.raises(ValueError, match="already bound"):
        bound.with_alias("TGF-β1", "strain")


# --- 6. the facets that are absent today -------------------------------------


@dataclass(frozen=True)
class _ProtocolWithSpecies(AssayProtocol):
    """What `AssayProtocol` would look like once the agreement adds a species."""

    species: str = ""


def _with_species(protocol: AssayProtocol, species: str) -> _ProtocolWithSpecies:
    values = {f.name: getattr(protocol, f.name) for f in fields(protocol)}
    return _ProtocolWithSpecies(**values, species=species)


def test_species_tissue_and_cell_type_are_absent_rather_than_guessed():
    """`bleomycin_lung` is obviously murine. Obvious is not declared.

    Reading it out of the `name` string would produce a vocabulary that
    disagrees with the code it claims to describe, and the disagreement would
    only surface when a finding matched a protocol it should not have.
    """
    for facet in (Facet.SPECIES, Facet.TISSUE, Facet.CELL_TYPE):
        assert terms(facet) == ()
    assert translate("mouse") is None
    assert translate("murine") is None


def test_an_absent_facet_fills_itself_when_the_field_appears():
    """No edit to vocabulary.py when the agreement lands - that is the point."""
    populated = Vocabulary.from_protocols(
        [_with_species(REGISTRY["bleomycin_lung"], "Mus musculus")]
    )
    species = populated.by_facet(Facet.SPECIES)
    assert [t.text for t in species] == ["mus musculus"]
    assert species[0].source_field == "AssayProtocol.species"
    assert species[0].protocols == ("bleomycin_lung",)
    assert populated.translate("Mus musculus") is not None

    report = populated.report([_with_species(REGISTRY["bleomycin_lung"], "Mus musculus")])
    assert "mus musculus" in report
    assert Facet.SPECIES.value not in _section(report, "WHAT THIS SIDE CANNOT DECLARE")
    assert Facet.TISSUE.value in _section(report, "WHAT THIS SIDE CANNOT DECLARE")


def test_every_facet_declares_where_it_would_read_from():
    """Including the empty ones. A facet with no source is still a statement."""
    for spec in FACETS:
        assert spec.source_field
        assert spec.note
        assert spec.facet in set(Facet)
