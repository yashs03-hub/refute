"""The place the shared vocabulary will land. Not the shared vocabulary.

SPEC 5.3 property 4 requires one vocabulary for biological entities and systems
- cell types, tissues, perturbations, readouts - because that is how layer 1's
findings get mapped onto what layer 2's protocols can actually model. SPEC 12
lists it second and says agree it in the first thirty minutes. The reason it is
that urgent is stated in the same sentence: it has to be agreed **before either
side hardcodes anything**, and both sides hardcoding first is the failure mode.

Half the terms in that agreement are layer 1's. This module therefore does not
attempt the agreement. It does the part that can be done unilaterally and
honestly:

  1. state, explicitly, the terms **this side already commits to** - every one
     of them read off a field of an `AssayProtocol` that already exists,
  2. leave an **empty alias map** as the single place layer 1's terms get bound
     to ours, so the agreement is a data change rather than a refactor,
  3. make the size of the gap **runnable** - `coverage_report()` prints what is
     declared, what is bound, and what this side cannot say at all.

WHAT THIS IS NOT
----------------
It is not a finished vocabulary and it must not be cited as one. Nothing here
has been agreed with layer 1; the alias map is empty; three of the six facets
are entirely undeclared. A module that overstated its own completeness would be
worse than not having one, because the next person would build against it.

NONE IS A REAL OUTCOME
----------------------
`translate` returns `None` for a term it does not hold, and never the raw string
back. A raw string flowing on as though it had been understood is exactly the
drift 5.3 exists to prevent: it is invisible at the call site, invisible in the
output, and only shows up as a finding matched to the wrong protocol. Callers
handle `None`, or call `require_term` and take the exception.

DERIVED, NOT INVENTED
---------------------
Every declared term traces to a protocol field, and each `Term` records which
field, which protocols, and the exact source string. Three facets - species,
tissue, cell type - are absent, because `AssayProtocol` has no field for any of
them. They are reported as absent rather than filled with plausible guesses.
`bleomycin_lung` is obviously murine and `fibrin_contracture` obviously uses
human synovial fibroblasts, but that knowledge lives in a `name` and a `summary`
sentence, and a vocabulary assembled by reading prose is a vocabulary that
disagrees with the code it claims to describe. An absence that is visible in a
report is worth more than a guess that looks like a field.

Those three facets read their value with `getattr`, from the field name they
*would* use. If the agreement adds `AssayProtocol.species`, this module needs no
edit: the facet populates and the report changes on the next run.

ON EXTERNAL ONTOLOGIES
----------------------
Deliberately none. No MeSH, no Cell Ontology, no network call, no dependency.
Pulling one in now would decide, unilaterally, the question 5.3 says both sides
must decide together, and it would bury the decision under thousands of terms
nobody in this repository chose.

The recommendation, for when the agreement happens: bind the agreed terms to
public identifiers rather than to strings - NCBI Taxonomy for species, UBERON
for tissue, Cell Ontology for cell type, ChEBI for small-molecule perturbations.
Identifiers survive renaming and translate across groups, which strings do not.
That is a decision for both layers, and the alias map is the right shape to hold
it: `Mapping[str, str]` becomes `Mapping[str, Term]` with an id on the `Term`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

from .assays import REGISTRY
from .assays.base import AssayProtocol


class Facet(Enum):
    """The kinds of thing a term can name.

    Named after 5.3's list - cell types, tissues, perturbations, readouts - plus
    the experimental unit, which 5.3 does not name but which this side cannot do
    without: a finding about cells and a protocol whose unit is an animal are not
    talking about the same thing, and the unit is the field that says so.
    """

    EXPERIMENTAL_UNIT = "experimental_unit"
    READOUT = "readout"
    PERTURBATION = "perturbation"
    SPECIES = "species"
    TISSUE = "tissue"
    CELL_TYPE = "cell_type"


class Derivation(Enum):
    """How far a term is from a field, which is how far it is from being solid."""

    FIELD = "field"
    """The verbatim value of a typed field, normalised for case and whitespace.
    No judgement was applied. If the field is wrong the term is wrong, and that
    is the only way it can be wrong."""

    NAME = "name"
    """Lifted out of a structured identifier by a stated syntactic rule. Weaker
    than FIELD: the rule is a naming convention of this repository, not a
    declaration, and a protocol that names its constants differently will
    contribute nothing rather than contribute something wrong."""


# Constants whose name ends in one of these quantify the effect of something,
# and the something is the prefix. This is a naming convention observed across
# `refute.assays`, not a statement about biology - which is the point. It
# recovers the perturbations from identifiers this side already committed to,
# instead of importing a list of profibrotic stimuli from somewhere and calling
# it derived.
_PERTURBATION_SUFFIXES = (
    "_dose_response",
    "_effect",
    "_fold_change",
    "_hazard_scale",
    "_response_curve",
)

# The prefix has to be a single token. `mortality_severity_coupling` would
# otherwise contribute "mortality_severity", which names no perturbation. A rule
# this crude has to fail closed, because a wrong term here would be indexed,
# reported, and eventually agreed.
_PERTURBATION_PREFIX_TOKENS = 1

# A term containing any of these is a phrase, not a term. Field values are
# honest - they say what the protocol says - but a disjunction cannot be matched
# against anything, so the report calls them out as needing a decision rather
# than passing them off as controlled terms.
_UNCONTROLLED_MARKERS = ("(", ")", "/", ",", "_or_", " or ")


@dataclass(frozen=True)
class Term:
    """One term this side commits to, and the evidence that it is not invented.

    `protocols` and `raw` are what make the claim checkable. A term that cannot
    name the protocols declaring it, and the exact strings it came from, is an
    assertion about the registry rather than a reading of it.
    """

    text: str
    """Canonical form: the source string, casefolded, whitespace collapsed."""

    facet: Facet
    derivation: Derivation

    source_field: str
    """Dotted path of the field the term was read from, e.g. `ReadoutSpec.name`."""

    protocols: tuple[str, ...]
    """Registry keys of every protocol declaring it, sorted."""

    raw: tuple[str, ...]
    """The exact source strings, before normalisation. Usually one."""

    @property
    def controlled(self) -> bool:
        """False when the term is really a phrase and still needs a decision."""
        return not any(m in self.text for m in _UNCONTROLLED_MARKERS)


@dataclass(frozen=True)
class FacetSpec:
    """Where one facet's terms come from, including when the answer is nowhere.

    A facet with no source is still declared. Dropping it would remove the only
    record that this side was asked for a species and had none, and 5.3 property
    5 - "looked and it is not there" must be distinguishable from "have not
    looked" - applies to the vocabulary as much as to the findings.
    """

    facet: Facet
    source_field: str
    derivation: Derivation
    extract: Callable[[AssayProtocol], tuple[str, ...]]
    """Every candidate source string this facet can see in one protocol. These
    are field values, unaltered, so `Term.raw` can be checked against the field
    it claims to come from."""

    note: str
    refine: Callable[[str], str | None] | None = None
    """Turns one source string into a term, or `None` to reject it. Absent means
    the source string is the term. Only the NAME derivation uses it, and keeping
    it separate from `extract` is what lets a `Term` record both the identifier
    it was found in and the term taken out of it."""

    context_field: str | None = None
    context: Callable[[AssayProtocol], str] | None = None
    """Free text to print next to a facet whose terms are derived or absent, so
    a reader can see what the extraction did not capture."""


def _unit(protocol: AssayProtocol) -> tuple[str, ...]:
    return (protocol.unit,)


def _readout(protocol: AssayProtocol) -> tuple[str, ...]:
    return (protocol.readout.name,)


def _constant_names(protocol: AssayProtocol) -> tuple[str, ...]:
    return tuple(c.name for c in protocol.all_constants())


def _perturbation_prefix(name: str) -> str | None:
    for suffix in _PERTURBATION_SUFFIXES:
        if not name.endswith(suffix):
            continue
        prefix = name[: -len(suffix)]
        if prefix and prefix.count("_") + 1 == _PERTURBATION_PREFIX_TOKENS:
            return prefix
    return None


def _optional(attribute: str) -> Callable[[AssayProtocol], tuple[str, ...]]:
    """Read a field `AssayProtocol` does not have yet.

    Written with `getattr` on purpose. The day the agreement adds the field, the
    facet fills itself and the report stops saying it is missing - without an
    edit here, which is the only version of this that will actually happen.
    """

    def read(protocol: AssayProtocol) -> tuple[str, ...]:
        value = getattr(protocol, attribute, None)
        if value is None or isinstance(value, str) and not value.strip():
            return ()
        if isinstance(value, str):
            return (value,)
        return tuple(str(v) for v in value)

    return read


FACETS: tuple[FacetSpec, ...] = (
    FacetSpec(
        facet=Facet.EXPERIMENTAL_UNIT,
        source_field="AssayProtocol.unit",
        derivation=Derivation.FIELD,
        extract=_unit,
        note=(
            "The thing that is replicated, and the thing an n counts. Verbatim; "
            "one protocol states two units in one string, which the report flags."
        ),
    ),
    FacetSpec(
        facet=Facet.READOUT,
        source_field="ReadoutSpec.name",
        derivation=Derivation.FIELD,
        extract=_readout,
        note=(
            "What is measured. `ReadoutSpec.units` is deliberately not a term - "
            "units are a separate 5.3 property and belong on the quantity."
        ),
    ),
    FacetSpec(
        facet=Facet.PERTURBATION,
        source_field="Constant.name",
        derivation=Derivation.NAME,
        extract=_constant_names,
        refine=_perturbation_prefix,
        note=(
            "No protocol declares a perturbation. These are recovered from "
            "constant names ending in "
            + ", ".join(_PERTURBATION_SUFFIXES)
            + " - a naming convention, so a protocol that does not follow it "
            "contributes nothing."
        ),
        context_field="HazardSpec.driver",
        context=lambda p: p.hazard.driver,
    ),
    FacetSpec(
        facet=Facet.SPECIES,
        source_field="AssayProtocol.species",
        derivation=Derivation.FIELD,
        extract=_optional("species"),
        note=(
            "No such field. Species appears only inside `name` and "
            "`paperclip_query` prose, which is not parsed. A finding scoped to a "
            "species cannot currently be matched to a protocol."
        ),
    ),
    FacetSpec(
        facet=Facet.TISSUE,
        source_field="AssayProtocol.tissue",
        derivation=Derivation.FIELD,
        extract=_optional("tissue"),
        note=(
            "No such field. Tissue is implied by the assay - lung for bleomycin, "
            "synovium for case 1 - and implied is not declared."
        ),
    ),
    FacetSpec(
        facet=Facet.CELL_TYPE,
        source_field="AssayProtocol.cell_type",
        derivation=Derivation.FIELD,
        extract=_optional("cell_type"),
        note=(
            "No such field. Cell identity appears only in `summary` prose "
            "(\"primary human synovial fibroblasts\"), which is not parsed."
        ),
    ),
)

_SPEC_BY_FACET: Mapping[Facet, FacetSpec] = MappingProxyType(
    {spec.facet: spec for spec in FACETS}
)


def normalise(text: str) -> str:
    """Canonical form of a term: casefolded, stripped, whitespace collapsed.

    Nothing else, and the restraint is the design. It is tempting to also fold
    underscores to spaces, strip hyphens, or drop Greek letters so that "TGF-b1"
    and "tgfb" meet in the middle - and every one of those is a claim that two
    names mean the same thing. Those claims belong in the alias map, where they
    are visible, reviewable and attributable to whoever agreed them. Hidden in a
    normaliser they become the private ontology that 5.3 property 4 forbids.
    """
    return " ".join(text.split()).casefold()


def _fingerprint(text: str) -> str:
    """Aggressive form, used only to detect two spellings of one term.

    Never used for lookup. `translate` must not match "strain energy" to
    `strain_energy`, because deciding they are the same term is the agreement's
    job - but the registry containing both, in different facets, unnoticed, is a
    bug, and this catches it at construction.
    """
    return "".join(c for c in normalise(text) if c.isalnum())


class UnboundTermError(KeyError):
    """Raised by `require_term` for a term the vocabulary does not hold."""


@dataclass(frozen=True)
class Vocabulary:
    """Declared terms plus the bindings from someone else's terms to them.

    Immutable, and `with_alias` returns a new one. An agreement reached in
    conversation is a fact about a moment; a vocabulary that can be mutated from
    anywhere makes "which terms were bound when this ran" unanswerable, and 6.1
    wants every verdict walkable backwards.
    """

    terms: tuple[Term, ...]
    aliases: Mapping[str, str] = MappingProxyType({})
    _index: Mapping[str, Term] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        index: dict[str, Term] = {}
        fingerprints: dict[str, Term] = {}
        for term in self.terms:
            if term.text in index:
                raise ValueError(f"term {term.text!r} is declared twice")
            print_fp = _fingerprint(term.text)
            clash = fingerprints.get(print_fp)
            if clash is not None:
                raise ValueError(
                    f"{term.text!r} ({term.facet.value}, from {term.source_field}) "
                    f"and {clash.text!r} ({clash.facet.value}, from "
                    f"{clash.source_field}) are the same term under two "
                    "spellings. Two spellings of one term is the drift 5.3 "
                    "property 4 is about; agree one spelling in the registry "
                    "rather than relaxing this check."
                )
            index[term.text] = term
            fingerprints[print_fp] = term

        bound: dict[str, str] = {}
        for alias, target in self.aliases.items():
            key = normalise(alias)
            goes_to = normalise(target)
            if not key:
                raise ValueError("an empty alias binds nothing")
            if key in index:
                raise ValueError(
                    f"alias {alias!r} shadows a declared term. An alias that "
                    "hides one of our own terms makes a lookup depend on which "
                    "map was consulted first."
                )
            if goes_to not in index:
                raise ValueError(
                    f"alias {alias!r} binds to {target!r}, which this side does "
                    "not declare. Aliases bind layer 1's terms TO ours; run "
                    "coverage_report() for the terms available."
                )
            if bound.get(key, goes_to) != goes_to:
                raise ValueError(
                    f"{alias!r} is bound to both {bound[key]!r} and {goes_to!r}"
                )
            bound[key] = goes_to

        # Both maps are rebuilt canonically here rather than trusted from the
        # caller, so the invariant `translate` relies on - every alias key and
        # every alias target is a canonical string already in the index - holds
        # however the vocabulary was constructed, not only via `with_alias`.
        object.__setattr__(self, "aliases", MappingProxyType(bound))
        object.__setattr__(self, "_index", MappingProxyType(index))

    # -- construction ------------------------------------------------------

    @classmethod
    def from_protocols(cls, protocols: Iterable[AssayProtocol]) -> Vocabulary:
        """Read every term off the protocols. There is no other source.

        There is no way to add a term that is not in a protocol, which is the
        one property this module has to keep: a vocabulary that can be extended
        by hand stops being a description of what the code models and becomes a
        second thing to keep in sync.
        """
        collected: dict[tuple[Facet, str], dict[str, list[str]]] = {}
        for protocol in protocols:
            for spec in FACETS:
                for raw in spec.extract(protocol):
                    refined = raw if spec.refine is None else spec.refine(raw)
                    if refined is None:
                        continue
                    text = normalise(refined)
                    if not text:
                        continue
                    entry = collected.setdefault((spec.facet, text), {})
                    entry.setdefault("protocols", []).append(protocol.key)
                    if raw not in entry.setdefault("raw", []):
                        entry["raw"].append(raw)

        terms = tuple(
            Term(
                text=text,
                facet=facet,
                derivation=_SPEC_BY_FACET[facet].derivation,
                source_field=_SPEC_BY_FACET[facet].source_field,
                protocols=tuple(sorted(set(entry["protocols"]))),
                raw=tuple(entry["raw"]),
            )
            for (facet, text), entry in sorted(
                collected.items(), key=lambda kv: (kv[0][0].value, kv[0][1])
            )
        )
        return cls(terms=terms)

    def with_alias(self, alias: str, term: str) -> Vocabulary:
        """A copy with one of layer 1's terms bound to one of ours.

        Returns a new vocabulary; the receiver is unchanged. Binding is the only
        operation the agreement needs, and keeping it to one call means the
        thirty-minute conversation ends in a list of `with_alias` arguments
        rather than a patch to this file.
        """
        key = normalise(alias)
        if not key:
            raise ValueError("an empty alias binds nothing")
        if key in self.aliases:
            raise ValueError(
                f"alias {key!r} is already bound to {self.aliases[key]!r}. "
                "Rebinding a term silently is how two sides end up disagreeing "
                "about what was agreed; drop the old binding explicitly."
            )
        return Vocabulary(terms=self.terms, aliases={**self.aliases, key: term})

    # -- lookup ------------------------------------------------------------

    def translate(self, term: str) -> Term | None:
        """The `Term` this side holds for `term`, or `None` if it holds none.

        `None` means the vocabulary has not been agreed for this term. It does
        not mean the entity does not exist, and it is never the input string
        handed back - a caller that treats an unrecognised name as understood
        produces output that looks correct and is not.
        """
        key = normalise(term)
        if not key:
            return None
        found = self._index.get(key)
        if found is not None:
            return found
        target = self.aliases.get(key)
        if target is None:
            return None
        return self._index[target]

    def require_term(self, term: str) -> Term:
        """`translate`, but raises. For callers that cannot proceed unmapped.

        The same shape as `AssayProtocol.require_runnable`: the permissive call
        and the strict call sit side by side, and the choice of which to use is
        made at the call site by whoever knows whether an unmapped term is
        survivable there.
        """
        found = self.translate(term)
        if found is None:
            raise UnboundTermError(
                f"{term!r} is not in this side's vocabulary and no alias binds "
                f"it. {len(self.terms)} terms are declared and "
                f"{len(self.aliases)} aliases are bound; run coverage_report() "
                "to see them. Bind it with Vocabulary.with_alias once both "
                "sides agree what it maps to."
            )
        return found

    def unbound_terms(self, terms: Iterable[str]) -> list[str]:
        """Which of `terms` this side cannot map, in the order given.

        The list is the useful artifact: handed to layer 1 it is the exact
        agenda for the thirty-minute conversation, and it is shorter than a
        discussion of the whole vocabulary. Original spellings are returned, not
        normalised ones, because the person who has to recognise them wrote them
        that way. Repeats collapse to their first occurrence.
        """
        missing: list[str] = []
        seen: set[str] = set()
        for term in terms:
            key = normalise(term)
            if key in seen:
                continue
            seen.add(key)
            if self.translate(term) is None:
                missing.append(term)
        return missing

    def by_facet(self, facet: Facet) -> tuple[Term, ...]:
        return tuple(t for t in self.terms if t.facet is facet)

    def uncontrolled(self) -> tuple[Term, ...]:
        """Declared terms that are still phrases. Honest, but not yet usable."""
        return tuple(t for t in self.terms if not t.controlled)

    # -- the report --------------------------------------------------------

    def report(self, protocols: Iterable[AssayProtocol] | None = None) -> str:
        """Everything this side declares, everything it cannot, in one string.

        Written to be pasted into the conversation with layer 1. It states the
        counts, names the terms, names the facets that are empty and why, and
        ends in three questions - because the output that closes this gap is
        their answers, not a longer document on this side.
        """
        protocols = tuple(protocols if protocols is not None else REGISTRY.values())
        lines: list[str] = []
        out = lines.append

        out("REFUTE - LAYER 2 VOCABULARY (NOT AGREED)")
        out("=" * 72)
        out(
            f"{len(protocols)} protocols, {len(self.terms)} terms declared, "
            f"{len(self.aliases)} aliases bound."
        )
        out("")
        out(_wrap(
            "SPEC 5.3 property 4 requires ONE vocabulary for biological entities "
            "and systems, agreed explicitly before either side hardcodes "
            "anything. SPEC 12 item 2 says agree it in the first thirty minutes. "
            "This is the layer 2 half: every term below is read off a protocol "
            "field, and none of it is agreed."
        ))

        declared = [s for s in FACETS if self.by_facet(s.facet)]
        empty = [s for s in FACETS if not self.by_facet(s.facet)]

        out("")
        out("WHAT THIS SIDE DECLARES")
        out("-" * 72)
        for spec in declared:
            terms = self.by_facet(spec.facet)
            out(
                f"{spec.facet.value}  ({len(terms)} terms, {spec.derivation.value} "
                f"<- {spec.source_field})"
            )
            width = max(len(t.text) for t in terms)
            for term in terms:
                line = f"    {term.text:<{width}}   {', '.join(term.protocols)}"
                if spec.derivation is Derivation.NAME:
                    line += f"   <- {', '.join(term.raw)}"
                out(line)
            out(_wrap(spec.note, indent="    "))
            if spec.context is not None:
                out(
                    f"    what each protocol actually says in {spec.context_field}, "
                    "unparsed:"
                )
                for protocol in sorted(protocols, key=lambda p: p.key):
                    out(f"      {protocol.key:<20} {spec.context(protocol)}")
            out("")

        out("WHAT THIS SIDE CANNOT DECLARE")
        out("-" * 72)
        if not empty:
            out("    (nothing - every facet has at least one term)")
        for spec in empty:
            out(f"{spec.facet.value}  (0 terms, would read {spec.source_field})")
            out(_wrap(spec.note, indent="    "))
            out(f"    undeclared by all {len(protocols)} protocols.")
            out("")

        loose = self.uncontrolled()
        out("DECLARED BUT NOT YET A CONTROLLED TERM")
        out("-" * 72)
        if not loose:
            out("    (none)")
        else:
            out(_wrap(
                f"{len(loose)} of {len(self.terms)} declared terms are phrases - "
                "a disjunction or a parenthetical. They are accurate, because "
                "they are what the field says, and they cannot be matched "
                "against anything. Each needs one decision.",
                indent="    ",
            ))
            out("")
            width = max(len(t.text) for t in loose)
            facet_width = max(len(t.facet.value) for t in loose)
            for term in loose:
                out(
                    f"    {term.text:<{width}}   {term.facet.value:<{facet_width}}   "
                    f"{', '.join(term.protocols)}"
                )
        out("")

        out("BOUND FROM LAYER 1")
        out("-" * 72)
        if not self.aliases:
            out(_wrap(
                "Nothing. The alias map is empty, and that is the state of the "
                "agreement rather than an omission: half of these terms are "
                "layer 1's to name, and binding them unilaterally is precisely "
                "the failure SPEC 12 item 2 warns about.",
                indent="    ",
            ))
        else:
            width = max(len(a) for a in self.aliases)
            for alias in sorted(self.aliases):
                out(f"    {alias:<{width}} -> {self.aliases[alias]}")
        out("")

        out("TO OPEN THE CONVERSATION, ASK")
        out("-" * 72)
        out(_wrap(
            f"1. Which of these {len(self.terms)} terms does your side already "
            "have a name for? Send the pairs and they become aliases. Nothing "
            "here has to be renamed for that to work.",
            indent="    ", hang="       ",
        ))
        if empty:
            out(_wrap(
                "2. Do your findings carry "
                + ", ".join(s.facet.value for s in empty)
                + " as fields? This side declares none of them, so a finding "
                "scoped to \"human lung\" cannot be matched to any protocol held "
                "here. If you carry them, we add the fields; if you do not "
                "either, the scope check is not happening and both sides should "
                "know that now.",
                indent="    ", hang="       ",
            ))
        else:
            out(_wrap(
                "2. Every facet this side declares now has terms in it, so the "
                "scope of a finding can be checked against a protocol. Confirm "
                "your side carries the same facets.",
                indent="    ", hang="       ",
            ))
        out(_wrap(
            "3. Perturbations: this side has "
            f"{len(self.by_facet(Facet.PERTURBATION))}, and they are lifted out "
            "of variable names rather than declared. If your side names "
            "perturbations properly, yours should be the canonical ones.",
            indent="    ", hang="       ",
        ))
        return "\n".join(lines)


def _wrap(text: str, indent: str = "", hang: str | None = None, width: int = 72) -> str:
    """Fold prose to `width`, with an optional deeper indent after line one.

    Local rather than `textwrap` so the report's shape is visible here next to
    the report. It is a paste-into-chat artifact; its formatting is content.
    """
    hang = indent if hang is None else hang
    words = text.split()
    lines: list[str] = []
    current = indent
    prefix = indent
    for word in words:
        candidate = f"{current} {word}" if current.strip() else f"{prefix}{word}"
        if len(candidate) > width and current.strip():
            lines.append(current)
            prefix = hang
            current = f"{hang}{word}"
        else:
            current = candidate
    if current.strip():
        lines.append(current)
    return "\n".join(lines)


VOCABULARY = Vocabulary.from_protocols(REGISTRY.values())
"""The vocabulary this side declares, built from the assay registry at import.

Built once, from `REGISTRY`, so there is one definition in one place - 5.3
property 1 - and so that the terms cannot drift from the protocols they describe
without a test noticing.
"""

ALIASES: Mapping[str, str] = VOCABULARY.aliases
"""Empty, and left empty on purpose.

This is the whole point of the module. When layer 1 says what it calls a
fibroblast, a well, or TGF-b1, those bindings land here - one line each, no
change to any protocol, no change to any caller. Until then it is empty, and
`coverage_report()` says so in as many words.

Do not populate it by guessing at layer 1's terms. A guessed binding is worse
than an unbound term: an unbound term returns `None` and stops the caller, and a
wrong binding returns a `Term` and does not.
"""


def terms(facet: Facet | None = None) -> tuple[Term, ...]:
    """Every declared term, or every term of one facet."""
    if facet is None:
        return VOCABULARY.terms
    return VOCABULARY.by_facet(facet)


def translate(term: str) -> Term | None:
    """Module-level `Vocabulary.translate` over the default vocabulary."""
    return VOCABULARY.translate(term)


def require_term(term: str) -> Term:
    """Module-level `Vocabulary.require_term` over the default vocabulary."""
    return VOCABULARY.require_term(term)


def unbound_terms(terms: Iterable[str]) -> list[str]:
    """Module-level `Vocabulary.unbound_terms` over the default vocabulary."""
    return VOCABULARY.unbound_terms(terms)


def coverage_report() -> str:
    """Module-level `Vocabulary.report` over the default vocabulary."""
    return VOCABULARY.report()


__all__ = [
    "ALIASES",
    "FACETS",
    "VOCABULARY",
    "Derivation",
    "Facet",
    "FacetSpec",
    "Term",
    "UnboundTermError",
    "Vocabulary",
    "coverage_report",
    "normalise",
    "require_term",
    "terms",
    "translate",
    "unbound_terms",
]
