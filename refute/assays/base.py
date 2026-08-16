"""Assay protocols — the part of a twin that changes between assays.

The twin's engine does not change from assay to assay: units evolve over time,
some fail before the endpoint, some are lost to attrition, and what survives is
measured imperfectly. What changes is four things:

  1. the experimental unit      (well / gel / chip / animal)
  2. the readout                (area fraction / force / collagen / fibrosis score)
  3. the hazard                 (what removes a unit, and what drives it)
  4. the measurement model      (precision, and what protocol it depends on)

An `AssayProtocol` declares those four. Everything else is shared.

THE RULE THIS FILE ENFORCES
---------------------------
A protocol whose constants are not calibrated **cannot produce a score**.
`score_design` refuses. This is not defensive programming; it is the whole
premise. The argument for this project is that its ground truth is measured
rather than invented, and a scaffold that quietly emitted plausible numbers
would be exactly the thing it criticises.

Scaffolds therefore declare their STRUCTURE — what fails, what drives it, what
is measured — while leaving every number `None`, alongside an explicit list of
what would have to be extracted to calibrate them, and the Paperclip query that
would find it.

WHAT THE PROTOCOL IS ABOUT
--------------------------
A protocol also declares its biological scope — species, tissue, cell type —
because the other layer's scope check needs something to check against. Most
apparent contradictions in biology are not contradictions; they are two findings
about two systems. A finding scoped to human lung cannot be matched to, or
excluded from, a protocol that says nothing about either.

Those three are `ScopeTerm`s rather than strings, and the reason is the same
reason the constants are not floats: the field has to be able to say how it
knows. A `ScopeTerm` carries a public identifier so the two sides never have to
agree on a spelling, and it distinguishes "this protocol does not commit to a
cell type" from "nobody has filled this in", which a bare string cannot.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType


class CalibrationStatus(Enum):
    """How much this protocol's numbers can be trusted."""

    MEASURED = "measured"
    """Constants fitted to primary data held in this repository. Case 1 only."""

    LITERATURE = "literature"
    """Constants extracted from published methods/troubleshooting sections.
    Weaker than MEASURED: inherits whatever those papers got wrong, and
    published failure rates are the ones authors chose to report."""

    SCAFFOLD = "scaffold"
    """Structure declared, numbers absent. Cannot be scored."""


@dataclass(frozen=True)
class Constant:
    """A numeric constant that knows whether it is real."""

    name: str
    value: float | None
    units: str
    provenance: str

    @property
    def missing(self) -> bool:
        return self.value is None


@dataclass(frozen=True)
class HazardSpec:
    """What removes an experimental unit before the endpoint.

    `driver` is the field that matters most. The assays worth twinning are the
    ones where the driver is the phenotype being measured - where succeeding at
    the biology is what destroys the readout. A hazard that is merely a function
    of time is real but ordinary, and a plain power calculation loses less by
    ignoring it.
    """

    mechanism: str
    driver: str
    driver_is_the_measured_phenotype: bool
    mitigation: str | None = None
    constants: tuple[Constant, ...] = ()


@dataclass(frozen=True)
class ReadoutSpec:
    """What is measured, and how well."""

    name: str
    units: str
    direction: str  # "decreases" | "increases" with the fibrotic phenotype
    destructive: bool  # True => one measurement per unit, no time course
    constants: tuple[Constant, ...] = ()


# ---------------------------------------------------------------------------
# Biological scope
# ---------------------------------------------------------------------------

# The ontology each scope field must draw its identifier from, and what that
# ontology is for. Three, deliberately: an identifier is only worth carrying if
# the other side can resolve it without asking us, and these three are the ones
# every group in this field already reads. A fourth prefix should be added here
# with the same test, not passed through as a free string.
ONTOLOGY_PREFIXES: Mapping[str, str] = MappingProxyType(
    {
        "NCBITaxon": "species — NCBI Taxonomy",
        "UBERON": "anatomical structure — Uberon",
        "CL": "cell type — Cell Ontology",
    }
)


class ScopeBasis(Enum):
    """How a protocol's biological scope was established.

    The same distinction the rest of this file makes about numbers, applied to
    terms: what the protocol says, what someone read into it, and what it does
    not say at all are three different claims, and collapsing them is how a
    guess ends up indistinguishable from a declaration.
    """

    STATED = "stated"
    """The protocol's own text names this entity. A scientific name standing in
    for a common one is still STATED — `Homo sapiens` for a summary that says
    "primary human synovial fibroblasts" names the same thing."""

    INFERRED = "inferred"
    """One step past the text, and recorded as a step: "murine" narrowed to a
    species, or a tissue of origin read off the name of a cell. Weaker than
    STATED. The comment at the declaration says which words it came from."""

    UNSPECIFIED = "unspecified"
    """The protocol does not commit to one. A scaffold that would run the same
    with fibroblasts from any tissue HAS no cell type, and that is a fact about
    the protocol rather than a hole in the record — which is why it is not the
    same as leaving the field `None`."""


@dataclass(frozen=True)
class ScopeTerm:
    """One biological entity a protocol is scoped to, plus how it is known.

    WHY AN IDENTIFIER AND NOT A STRING
    ----------------------------------
    `NCBITaxon:9606` is unambiguous where "human" is not. The other layer never
    has to agree with this side's spelling; it resolves its own term to the same
    ontology and the two meet at the identifier. Strings meet only if somebody
    maintains a synonym list, and nobody does.

    WHY THE IDENTIFIER IS OPTIONAL
    ------------------------------
    Because a wrong CURIE is worse than an absent one. An absent identifier
    fails to match and someone notices; a plausible wrong one matches the wrong
    thing silently, forever, and nothing downstream can detect it. So `term` is
    always recorded and `ontology_id` is `None` whenever the mapping was not
    verified — with `note` saying why, so that the gap is a finding rather than
    an oversight.

    ITERATION
    ---------
    A `ScopeTerm` iterates as the terms it contributes: one when it declares
    something, none when the scope is unspecified. That is what lets
    `refute.vocabulary` read these fields with `getattr` and fill its species,
    tissue and cell-type facets without an edit to a module this side does not
    own — the shape it already expected was "a string or an iterable of them".
    """

    term: str
    """The plain term, as a person would write it. Empty iff UNSPECIFIED."""

    ontology_id: str | None = None
    """CURIE from `ONTOLOGY_PREFIXES`, e.g. `NCBITaxon:9606`. `None` means the
    mapping was not verified, never that no identifier exists."""

    basis: ScopeBasis = ScopeBasis.STATED

    note: str = ""
    """Why the scope is unspecified, or why there is no identifier. Required in
    both cases: an unexplained absence reads as nobody having looked."""

    @classmethod
    def unspecified(cls, why: str) -> ScopeTerm:
        """Record that the protocol genuinely does not commit to one.

        `why` is not decoration. "This scaffold could be run with fibroblasts
        from any tissue" and "the summary never says" are different states of
        knowledge, and the person who reads this next cannot recover which.
        """
        return cls(term="", ontology_id=None, basis=ScopeBasis.UNSPECIFIED, note=why)

    def __post_init__(self) -> None:
        if self.basis is ScopeBasis.UNSPECIFIED:
            if self.term or self.ontology_id:
                raise ValueError(
                    f"an UNSPECIFIED scope carries no term and no id, got "
                    f"term={self.term!r} ontology_id={self.ontology_id!r}"
                )
            if not self.note.strip():
                raise ValueError(
                    "an UNSPECIFIED scope must say why the protocol does not "
                    "commit to one, or it cannot be told from an oversight"
                )
            return

        if not self.term.strip():
            raise ValueError(
                f"a {self.basis.value} scope needs a term; use "
                "ScopeTerm.unspecified(why) when the protocol declares none"
            )
        if self.ontology_id is None:
            if not self.note.strip():
                raise ValueError(
                    f"{self.term!r} has no ontology id and no note saying why. "
                    "An unexplained missing id is indistinguishable from one "
                    "nobody tried to look up."
                )
            return

        prefix, sep, local = self.ontology_id.partition(":")
        if not sep or prefix not in ONTOLOGY_PREFIXES or not local.isdigit():
            raise ValueError(
                f"{self.ontology_id!r} is not a well-formed identifier. Expected "
                f"PREFIX:digits with PREFIX in {sorted(ONTOLOGY_PREFIXES)}."
            )

    @property
    def declared(self) -> bool:
        return self.basis is not ScopeBasis.UNSPECIFIED

    def __bool__(self) -> bool:
        """Falsy when unspecified, so it agrees with what iterating it yields."""
        return self.declared

    def __iter__(self) -> Iterator[str]:
        if self.term:
            yield self.term

    def __str__(self) -> str:
        return self.term or "unspecified"


# Which ontology each scope field has to use. Checked at construction, because a
# UBERON id sitting in `species` would be a term that resolves, matches nothing,
# and looks correct in every report that prints it.
SCOPE_ONTOLOGIES: Mapping[str, str] = MappingProxyType(
    {
        "species": "NCBITaxon",
        "tissue": "UBERON",
        "cell_type": "CL",
    }
)


@dataclass(frozen=True)
class AssayProtocol:
    key: str
    name: str
    unit: str
    status: CalibrationStatus
    readout: ReadoutSpec
    hazard: HazardSpec
    summary: str
    why_it_matters: str
    calibration_needs: tuple[str, ...] = ()
    paperclip_query: str | None = None
    attrition_constants: tuple[Constant, ...] = ()
    notes: str = ""
    references: tuple[str, ...] = field(default_factory=tuple)

    # -- biological scope --------------------------------------------------
    #
    # What system this protocol is about, for the scope check that decides
    # whether somebody else's finding applies here at all. `None` is the
    # honest default for a protocol nobody has been through: it means the
    # question was never asked, which is why declining to commit has its own
    # value (`ScopeTerm.unspecified`) rather than reusing this one.
    #
    # `tissue` is the anatomical structure the protocol is about — the organ
    # measured in vivo, or the tissue the cells were taken from in vitro.

    species: ScopeTerm | None = None
    tissue: ScopeTerm | None = None
    cell_type: ScopeTerm | None = None

    def __post_init__(self) -> None:
        for name, prefix in SCOPE_ONTOLOGIES.items():
            scope = getattr(self, name)
            if scope is None or scope.ontology_id is None:
                continue
            if not scope.ontology_id.startswith(f"{prefix}:"):
                raise ValueError(
                    f"{self.key}.{name} is {scope.ontology_id!r}, which is not "
                    f"a {prefix} identifier ({ONTOLOGY_PREFIXES[prefix]})"
                )

    def biological_scope(self) -> dict[str, ScopeTerm | None]:
        """The three scope fields by name, `None`s included.

        The `None`s are the point: a caller checking whether this protocol can
        take part in a scope check needs to see the fields nobody filled in.
        """
        return {name: getattr(self, name) for name in SCOPE_ONTOLOGIES}

    # -- calibration gate --------------------------------------------------

    def all_constants(self) -> tuple[Constant, ...]:
        return (
            self.readout.constants
            + self.hazard.constants
            + self.attrition_constants
        )

    def missing_constants(self) -> list[Constant]:
        return [c for c in self.all_constants() if c.missing]

    @property
    def runnable(self) -> bool:
        """True only if every constant has a value AND the status admits it."""
        return (
            self.status is not CalibrationStatus.SCAFFOLD
            and not self.missing_constants()
        )

    def require_runnable(self) -> None:
        """Raise unless this protocol may legitimately produce a score."""
        if self.runnable:
            return
        missing = self.missing_constants()
        detail = (
            "\n".join(f"    - {c.name} ({c.units}): {c.provenance}" for c in missing)
            or "    (none missing, but status is SCAFFOLD)"
        )
        raise UncalibratedAssayError(
            f"'{self.key}' is a {self.status.value} protocol and cannot be scored.\n"
            f"  Missing constants:\n{detail}\n"
            f"  To calibrate, obtain:\n"
            + "\n".join(f"    - {n}" for n in self.calibration_needs)
            + (
                f"\n  Suggested Paperclip query:\n    {self.paperclip_query}"
                if self.paperclip_query
                else ""
            )
        )


class UncalibratedAssayError(RuntimeError):
    """Raised when something tries to score a scaffold."""
