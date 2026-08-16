"""The join between layer 1 and layer 2 — residual prose in, assay and spec out.

WHAT IS MISSING WITHOUT THIS MODULE
-----------------------------------
Layer 1 hands over a `Handoff` whose residual is prose: *"what could not be
settled without new data."* The gate in `refute.gate` needs two things that
prose is not — an `AssayProtocol` and a `DesignSpec`. §5.2 of the system spec is
explicit that layer 1 does not pick the assay, and it is right to be: layer 1
does not know what the protocols can measure. But nothing on layer 2's side
picked it either. This module is that step and nothing else.

    Handoff.residual (prose)
        │
        ├── select_assay()    → which protocol, ranked, or none of these
        └── extract_design()  → DesignSpec, or an honest extraction failure
        │
        └── intake()          → both, plus a narrative of what it did

TWO JOBS, TWO DIFFERENT KINDS OF MACHINERY, ON PURPOSE
------------------------------------------------------
**Assay selection is deterministic.** No model call. The registry is seven
protocols that each declare a `unit`, a `readout`, a `summary` and a
`why_it_matters`, so choosing between them is a keyword and entity match over
those declarations. That is genuinely the better instrument here, not a
concession: it is free, it runs with no credential, it is identical on every
run, and a wrong answer is a line of a table you can read rather than a mood you
have to re-roll. The weights, the vocabulary and the evidence floor are all
module constants, and `AssaySelection` reports which terms matched which fields.

**Extraction is a model call, and it is the only one.** Prose to structured
fields is what models are reliable at; deciding whether the resulting design is
any good is what they are not, and that half stays with the simulator. This
module therefore takes the extractor by injection - the same shape as
`refute.chat.Session` - so every path through it is testable with no credential,
and so the one model-dependent step is visible in the signature.

"NONE OF THESE" IS A RESULT
---------------------------
A selector that always returns a key is the fail-always guard in a new costume.
`refute.gate` documents the original: an out-of-scope guard that flagged the
twin's own assay as unmodelled, refused every design, and passed the whole
suite, because a test that only checks refusals is satisfied by refusing
everything. The mirror image is just as bad and much easier to ship - a selector
with no empty outcome will map a zebrafish behavioural assay onto a fibrin gel,
and everything downstream will then be confidently about the wrong apparatus.

So a candidate has to clear an explicit evidence floor, `EVIDENCE_FLOOR` points
across at least `MIN_MATCHED_TERMS` distinct discriminative terms. Below that,
`AssaySelection.none_of_these` is True, and `intake` records the reason in
`DesignSpec.out_of_twin_scope` so the gate routes OUT_OF_SCOPE rather than
scoring a plate nobody proposed.

AN EXTRACTION FAILURE IS NOT A BAD DESIGN
-----------------------------------------
The confound this whole project holds the extractor constant to avoid is
parsing fidelity read as design quality. A provider timeout, a malformed
response, a missing credential - none of those are facts about the experiment,
and none of them may be reported as one. They raise typed errors here, and
`intake` reports them in the register `refute.chat._handle_design` already uses:
*that is a parsing failure on our side, not a judgement about your experiment.*

NOTE ON THE NAME
----------------
`refute.agent.extract_design` is a different function: it holds a `ModelSpec`
and calls a provider. This one takes any callable and is the seam that makes the
module testable. They are not interchangeable, and this one is deliberately the
one with no default provider - see `extract_design` below.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Sequence

from .assays import REGISTRY
from .assays.base import AssayProtocol, CalibrationStatus
from .design import DesignSpec
from .twins import TWINS

# ---------------------------------------------------------------------------
# Tuning constants. Every number a selection depends on lives here, in one
# block, because the argument for a deterministic selector is that you can read
# why it did what it did - and that argument fails the moment a weight is buried
# in a function body.
# ---------------------------------------------------------------------------

FIELD_WEIGHTS: dict[str, float] = {
    "key": 3.0,
    "name": 3.0,
    "readout": 3.0,
    "unit": 2.0,
    "summary": 2.0,
    "hazard": 1.5,
    "why_it_matters": 1.0,
}
"""How much a term is worth for appearing in each declared field.

The ordering is the claim: what a protocol *is* (its key, its name, what it
measures) identifies it far more sharply than what it is *for*. `why_it_matters`
is argued prose written for a human reader, so it is the widest net and the
weakest evidence, and it sits last.

A term appearing in several fields scores its highest field, not the sum. Summing
would let a verbose `why_it_matters` outvote a readout, which is the wrong way
round.
"""

RESIDUAL_WEIGHT = 1.0
"""The residual is the brief. §5.1: 'Item 6 is load-bearing.'"""

HYPOTHESIS_WEIGHT = 0.5
"""The hypothesis is context. It may name the biology without naming the
apparatus, so it can break a tie and should not decide one on its own."""

EVIDENCE_FLOOR = 3.0
"""Score a protocol must reach to be offered as a candidate at all.

Set so that a single incidental word - a residual that happens to say 'exposure'
or 'stimulus' - cannot select an assay. An assay is a claim about what apparatus
would settle the question, and one shared noun is not evidence for that claim.
"""

MIN_MATCHED_TERMS = 2
"""Distinct discriminative terms a candidate must match.

Independent of the score on purpose. One heavily-weighted term can clear
`EVIDENCE_FLOOR` by itself, and a match resting on one word is exactly the kind
of coincidence this floor exists to catch.
"""

DECISIVE_MARGIN = 1.5
"""How far ahead the leader must be for the selection to call itself decisive.

Below this the selection still ranks, and still says which it prefers, but
reports that the field is close. Returning one key with false confidence is the
failure this whole return type is shaped to avoid.
"""

MIN_TERM_LENGTH = 3
"""Shorter tokens are almost all noise. `b1` and `cm` are the exceptions, and
they are handled by keeping any token that contains a digit."""


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset("""
a about above after again against all almost along also although always among an
and another any anything are around as at away back be became because been before
being below best better between both but by came can cannot could criterion did
do does doing done down due during each either else enough etc even ever every
few first for form from full further get give given goes going got had has have
having here how however if in inside instead into is it its itself just keep kept
last least less let like likely made make making many may maybe me might more
most much must my need needs neither never new next no none nor not nothing now
of off often on once one only onto or other others otherwise our out over own per
perhaps put quite rather really same say see seem seen several shall she should
show shown since so some something still such take taken than that the their them
then there therefore these they thing things this those though three through thus
to together too toward two under until up upon us use used using usually very via
want was way we well were what when where whether which while who whom whose why
will with within without would yet you your
""".split())
"""Ordinary English, plus the connectives that show up in every protocol summary.

Deliberately not a list of *scientific* stopwords. Terms that are common across
the registry - 'cell', 'assay', 'culture' - are neutralised by document
frequency instead, which is measured from the registry rather than guessed at,
and which stays correct when a protocol is added.
"""

_ALIASES: dict[str, str] = {
    # Contraction, under five surface forms that mean one phenomenon.
    "contracture": "contraction",
    "contractures": "contraction",
    "contractile": "contraction",
    "contractility": "contraction",
    "contract": "contraction",
    "contracts": "contraction",
    "contracted": "contraction",
    "contracting": "contraction",
    # Cells.
    "fibroblasts": "fibroblast",
    "myofibroblast": "fibroblast",
    "myofibroblasts": "fibroblast",
    # Scaffolds.
    "gels": "gel",
    "hydrogel": "gel",
    "hydrogels": "gel",
    "matrices": "matrix",
    # Deposition.
    "deposit": "deposition",
    "deposits": "deposition",
    "deposited": "deposition",
    "depositing": "deposition",
    # Fibrosis.
    "fibrotic": "fibrosis",
    "profibrotic": "fibrosis",
    # Scaffold loss.
    "fibrinolytic": "fibrinolysis",
    "lysed": "lysis",
    "lyses": "lysis",
    "lysing": "lysis",
    "dissolves": "dissolution",
    "dissolving": "dissolution",
    "detach": "detachment",
    "detaches": "detachment",
    "detached": "detachment",
    "detaching": "detachment",
    "delaminate": "delamination",
    "delaminates": "delamination",
    "delaminated": "delamination",
    "delaminating": "delamination",
    # Mechanics.
    "stiff": "stiffness",
    "stiffer": "stiffness",
    "moduli": "modulus",
    "stretched": "stretch",
    "stretching": "stretch",
    # Measurement.
    "image": "imaging",
    "images": "imaging",
    "imaged": "imaging",
    "measure": "measurement",
    "measures": "measurement",
    "measured": "measurement",
    "measuring": "measurement",
    # Animals.
    "mice": "mouse",
    "mouses": "mouse",
    "murine": "mouse",
}
"""Surface forms folded onto one canonical term.

Small and hand-checked on purpose. A real stemmer would fold more, and would
also fold things that should stay apart - 'fibrin' and 'fibrosis' differ by two
characters and by an entire apparatus. Every entry here was added because two
forms of the same word appear on opposite sides of the match: in the registry's
prose on one side and in a plausible residual on the other.
"""

_TOKEN = re.compile(r"[a-z0-9]+")


def _canonical(token: str) -> str:
    """One token to its canonical term. Aliases first, then a cautious plural.

    The plural rule refuses to touch anything ending `-is` or `-ss`, which is
    what keeps 'fibrosis', 'lysis' and 'stress' intact. It is the only
    morphology applied; anything subtler belongs in `_ALIASES`, where it can be
    read.
    """
    if token in _ALIASES:
        return _ALIASES[token]
    base = token
    if not token.endswith(("is", "ss", "us")):
        if len(token) > 4 and token.endswith("ies"):
            base = token[:-3] + "y"
        elif len(token) > 4 and token.endswith(("sses", "shes", "ches", "xes")):
            base = token[:-2]
        elif len(token) > 3 and token.endswith("s"):
            base = token[:-1]
    return _ALIASES.get(base, base)


def terms(text: str) -> set[str]:
    """The canonical terms in a piece of text. Order-free, duplicate-free.

    Public because the selection is only inspectable if you can see what it read
    out of your sentence.
    """
    out: set[str] = set()
    for raw in _TOKEN.findall(text.lower()):
        if raw in _STOPWORDS:
            continue
        if len(raw) < MIN_TERM_LENGTH and not any(c.isdigit() for c in raw):
            continue
        canonical = _canonical(raw)
        if canonical in _STOPWORDS:
            continue
        out.add(canonical)
    return out


def _declared_text(protocol: AssayProtocol) -> dict[str, str]:
    """The protocol's own declarations, per field, as text to be matched.

    `readout.direction` and `readout.destructive` are excluded. They are
    controlled values from a two-item vocabulary, so 'increases' would match any
    residual that used the ordinary English word and would tell you nothing.
    """
    return {
        "key": protocol.key.replace("_", " "),
        "name": protocol.name,
        "unit": protocol.unit,
        "readout": f"{protocol.readout.name.replace('_', ' ')} {protocol.readout.units}",
        "summary": protocol.summary,
        "hazard": " ".join(
            part
            for part in (
                protocol.hazard.mechanism,
                protocol.hazard.driver,
                protocol.hazard.mitigation or "",
            )
            if part
        ),
        "why_it_matters": protocol.why_it_matters,
    }


@dataclass(frozen=True)
class _VocabEntry:
    weight: float
    fields: tuple[str, ...]


def _vocabulary(protocol: AssayProtocol) -> dict[str, _VocabEntry]:
    """Term to (best field weight, every field it appeared in)."""
    best: dict[str, float] = {}
    where: dict[str, list[str]] = {}
    for field, text in _declared_text(protocol).items():
        weight = FIELD_WEIGHTS[field]
        for term in terms(text):
            if weight > best.get(term, 0.0):
                best[term] = weight
            where.setdefault(term, []).append(field)
    return {t: _VocabEntry(best[t], tuple(where[t])) for t in best}


def _discriminativeness(
    vocabularies: Mapping[str, Mapping[str, _VocabEntry]]
) -> dict[str, float]:
    """How much a term narrows the registry down. Measured, not assumed.

    A term every protocol declares - 'fibrosis' across a fibrosis registry -
    separates nothing, so it is worth zero. Otherwise a term is worth `1/df`:
    unique to one protocol is full weight, shared by two is half.

    The all-protocols rule is suspended below three protocols, where 'every
    protocol' is not yet evidence of anything and would zero the vocabulary of a
    single-entry registry.
    """
    total = len(vocabularies)
    counts: dict[str, int] = {}
    for vocab in vocabularies.values():
        for term in vocab:
            counts[term] = counts.get(term, 0) + 1
    return {
        term: 0.0 if (total >= 3 and df >= total) else 1.0 / df
        for term, df in counts.items()
    }


# ---------------------------------------------------------------------------
# Job 1 — assay selection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TermMatch:
    """One term of the residual, found in one protocol's declarations."""

    term: str
    contribution: float
    fields: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.term} ({'/'.join(self.fields)}, {self.contribution:.2f})"


@dataclass(frozen=True)
class AssayCandidate:
    """One protocol, and exactly why it was or was not offered."""

    key: str
    name: str
    score: float
    matched: tuple[TermMatch, ...]
    status: CalibrationStatus
    runnable: bool
    why: str

    @property
    def terms(self) -> tuple[str, ...]:
        return tuple(m.term for m in self.matched)


@dataclass(frozen=True)
class AssaySelection:
    """Ranked candidates, the ones that fell short, and no single answer.

    `candidates` is ordered best first and may be empty, which is the point.
    `near_misses` holds the protocols that matched something and did not clear
    the floor - recorded because §6.4 of the spec is right that the discarded
    material is where the improvement lives, and because a selection that fails
    silently is one you cannot debug.
    """

    residual: str
    hypothesis: str
    candidates: tuple[AssayCandidate, ...]
    near_misses: tuple[AssayCandidate, ...]
    considered: tuple[str, ...]
    why: str

    @property
    def none_of_these(self) -> bool:
        """True when no protocol in the registry fits.

        A first-class outcome. It routes to the same honest place as
        OUT_OF_SCOPE: the registry has nothing to say about this residual, which
        is a limit of the registry rather than a verdict on the question.
        """
        return not self.candidates

    @property
    def best(self) -> AssayCandidate | None:
        return self.candidates[0] if self.candidates else None

    @property
    def runner_up(self) -> AssayCandidate | None:
        return self.candidates[1] if len(self.candidates) > 1 else None

    @property
    def decisive(self) -> bool:
        """True when the leader is clear of the field by `DECISIVE_MARGIN`.

        False does not mean the selection is wrong. It means a caller acting on
        `best` alone is discarding a live alternative, and should say so.
        """
        if not self.candidates:
            return False
        second = self.runner_up
        if second is None:
            return True
        return self.candidates[0].score >= second.score * DECISIVE_MARGIN

    def render(self) -> str:
        lines = [self.why]
        for i, c in enumerate(self.candidates, 1):
            lines.append(f"  {i}. {c.key} ({c.score:.1f}) — {c.why}")
        if self.near_misses:
            lines.append("  below the floor, recorded so the miss is readable:")
            for c in self.near_misses:
                lines.append(f"    - {c.key} ({c.score:.1f}) — {c.why}")
        return "\n".join(lines)


def _status_note(protocol: AssayProtocol) -> str:
    if protocol.status is CalibrationStatus.MEASURED:
        return "Its constants are measured, so it can produce a score."
    if protocol.status is CalibrationStatus.LITERATURE:
        return (
            "Its constants come from published methods, which is weaker than "
            "measured and inherits whatever those papers got wrong."
        )
    return (
        "It is a SCAFFOLD - structure declared, constants absent - so it will "
        "refuse to produce a score until it is calibrated."
    )


def select_assay(
    residual: str,
    hypothesis: str = "",
    *,
    registry: Mapping[str, AssayProtocol] | None = None,
) -> AssaySelection:
    """Which registry protocols could settle this residual, ranked, with reasons.

    Deterministic. No model call, no credential, no network. Every protocol is
    scored by matching the canonical terms of the residual (and, at half weight,
    of the hypothesis) against the terms the protocol itself declares, weighted
    by which field they appeared in and by how far the term narrows the registry
    down.

    Returns every protocol that clears the evidence floor, best first, and an
    empty `candidates` when none does. The empty case is not an error and is not
    a fallback to the first entry: see `AssaySelection.none_of_these`.

    `registry` is injectable so the floor can be exercised against a registry
    whose contents are known, rather than against whatever the real one happens
    to contain today.
    """
    protocols = dict(REGISTRY if registry is None else registry)
    vocabularies = {key: _vocabulary(p) for key, p in protocols.items()}
    weight_of = _discriminativeness(vocabularies)

    sought: dict[str, float] = {}
    for term in terms(hypothesis):
        sought[term] = HYPOTHESIS_WEIGHT
    for term in terms(residual):
        sought[term] = RESIDUAL_WEIGHT

    scored: list[AssayCandidate] = []
    for key, protocol in protocols.items():
        vocab = vocabularies[key]
        matches: list[TermMatch] = []
        for term, source_weight in sought.items():
            entry = vocab.get(term)
            if entry is None:
                continue
            discriminative = weight_of.get(term, 0.0)
            if discriminative <= 0.0:
                continue
            matches.append(
                TermMatch(
                    term=term,
                    contribution=entry.weight * discriminative * source_weight,
                    fields=entry.fields,
                )
            )
        matches.sort(key=lambda m: (-m.contribution, m.term))
        total = sum(m.contribution for m in matches)
        scored.append(
            AssayCandidate(
                key=key,
                name=protocol.name,
                score=total,
                matched=tuple(matches),
                status=protocol.status,
                runnable=protocol.runnable,
                why=_candidate_why(protocol, matches, total),
            )
        )

    scored.sort(key=lambda c: (-c.score, c.key))
    candidates = tuple(
        c
        for c in scored
        if c.score >= EVIDENCE_FLOOR and len(c.matched) >= MIN_MATCHED_TERMS
    )
    offered = {c.key for c in candidates}
    near_misses = tuple(c for c in scored if c.key not in offered and c.matched)

    return AssaySelection(
        residual=residual,
        hypothesis=hypothesis,
        candidates=candidates,
        near_misses=near_misses,
        considered=tuple(sorted(protocols)),
        why=_selection_why(candidates, near_misses, protocols),
    )


def _candidate_why(
    protocol: AssayProtocol, matches: Sequence[TermMatch], total: float
) -> str:
    """The per-candidate reason. Names the terms, so the match can be argued with."""
    if not matches:
        return (
            "Nothing in the residual matched anything this protocol declares "
            "about its unit, readout, summary or hazard."
        )
    shown = ", ".join(m.term for m in matches[:6])
    more = f" (+{len(matches) - 6} more)" if len(matches) > 6 else ""
    fields = sorted({f for m in matches for f in m.fields})
    if total >= EVIDENCE_FLOOR and len(matches) >= MIN_MATCHED_TERMS:
        head = (
            f"Matched {len(matches)} term(s) — {shown}{more} — across its "
            f"{', '.join(fields)}."
        )
        return f"{head} {_status_note(protocol)}"
    shortfall = (
        f"only {len(matches)} distinct term(s), below the {MIN_MATCHED_TERMS} "
        f"required"
        if len(matches) < MIN_MATCHED_TERMS
        else f"score {total:.1f}, below the floor of {EVIDENCE_FLOOR:.1f}"
    )
    return (
        f"Matched {shown}{more}, but {shortfall} — an incidental word is not "
        f"evidence that this apparatus would settle the question."
    )


def _selection_why(
    candidates: Sequence[AssayCandidate],
    near_misses: Sequence[AssayCandidate],
    protocols: Mapping[str, AssayProtocol],
) -> str:
    """The selection-level narrative, including the honest empty case."""
    if not candidates:
        covered = ", ".join(
            f"{p.readout.name} per {p.unit}" for p in protocols.values()
        ) or "nothing - the registry is empty"
        touched = (
            f" {len(near_misses)} protocol(s) matched something and fell short; "
            f"they are recorded in `near_misses`."
            if near_misses
            else ""
        )
        return (
            f"No assay in this registry fits. None of the {len(protocols)} "
            f"protocol(s) reached {EVIDENCE_FLOOR:.1f} points across at least "
            f"{MIN_MATCHED_TERMS} distinct terms of the residual.{touched} The "
            f"registry measures: {covered}. This is a limit of the registry, "
            f"not a verdict on the question - it routes the same way "
            f"OUT_OF_SCOPE does."
        )
    best = candidates[0]
    if len(candidates) == 1:
        return (
            f"One protocol fits: '{best.key}', on {len(best.matched)} matched "
            f"term(s)."
        )
    second = candidates[1]
    if best.score >= second.score * DECISIVE_MARGIN:
        return (
            f"'{best.key}' leads {len(candidates)} candidate(s) at "
            f"{best.score:.1f} against {second.score:.1f} for '{second.key}' - "
            f"clear of the field."
        )
    return (
        f"'{best.key}' leads at {best.score:.1f}, but '{second.key}' is close "
        f"behind at {second.score:.1f}. Treating the leader as the answer would "
        f"discard a live alternative; both are returned."
    )


# ---------------------------------------------------------------------------
# Job 2 — prose to DesignSpec
# ---------------------------------------------------------------------------


class NoExtractorConfigured(RuntimeError):
    """No extractor was supplied, so prose cannot be read into a design.

    Separate from `ExtractionFailure` because the fixes are different and a
    caller should be able to tell them apart without reading a message. This one
    is configuration: nobody wired up a model. The other is a model call that
    was made and did not work.

    Neither is a statement about the experiment.
    """


class ExtractionFailure(RuntimeError):
    """The extractor was called and did not return a usable `DesignSpec`.

    A provider timeout, a refusal, a malformed structured output, or a callable
    that returned the wrong type. All of them are parsing failures on our side.

    This is the confound the benchmark holds the extractor constant to avoid: if
    a parse failure were reported as a design problem, a design would score
    worse for having been read badly, and the two are indistinguishable after
    the fact. So it raises rather than returning a degraded spec, and `intake`
    reports it in words that make no claim about the design.
    """


NO_EXTRACTOR_MESSAGE = (
    "No extractor is configured, so prose cannot be read into a design. Pass a "
    "DesignSpec directly, or configure one."
)


def _failure_message(exc: BaseException) -> str:
    """The wording register from `refute.chat._handle_design`, verbatim in intent.

    It names the failure, attributes it to us, and explicitly disclaims any
    judgement about the experiment. That third clause is the one that matters
    and it is the one that would quietly go missing.
    """
    return (
        f"Could not read that into a design ({type(exc).__name__}). That is a "
        f"parsing failure on our side, not a judgement about your experiment - "
        f"try describing the arms and timings more plainly."
    )


def extract_design(
    text: str,
    extractor: Callable[[str], Any] | None = None,
    *,
    unmodelled: Iterable[str] = (),
    design_spec_type: type = DesignSpec,
) -> Any:
    """Prose to design spec. The model extracts; nothing here judges.

    `extractor` is injected rather than defaulted to a provider. A default would
    make the honest path - "no extractor is configured" - the path nobody
    exercises, and would make this module untestable without a credential. With
    `extractor=None` this raises `NoExtractorConfigured` and says so; it does not
    guess a design, because a guessed design scored by the twin is a confident
    number about a plate nobody proposed.

    `unmodelled` is merged into `out_of_twin_scope`. It exists for the
    one thing the extractor cannot know: that the *registry* has no protocol for
    this residual at all. `intake` passes the none-of-these reason through here
    so the gate can route OUT_OF_SCOPE honestly rather than being handed a
    design that looks fine. Nothing else adds to that field - in particular there
    is no keyword scan of the prose, which is precisely the fail-always guard
    `refute.gate` documents.
    """
    if extractor is None:
        raise NoExtractorConfigured(NO_EXTRACTOR_MESSAGE)

    try:
        spec = extractor(text)
    except Exception as exc:
        raise ExtractionFailure(_failure_message(exc)) from exc

    if not isinstance(spec, design_spec_type):
        # An extractor returning the wrong type is a parsing failure like any
        # other. Letting it through would put a duck-typed object in front of
        # the simulator, which is a worse error one step later.
        raise ExtractionFailure(
            f"The extractor returned {type(spec).__name__}, not a {design_spec_type.__name__}. "
            f"That is a parsing failure on our side, not a judgement about your "
            f"experiment."
        )

    extra = [r.strip() for r in unmodelled if r and r.strip()]
    if not extra:
        return spec
    merged = list(getattr(spec, "out_of_twin_scope", []))
    for reason in extra:
        if reason not in merged:
            merged.append(reason)
    return spec.model_copy(update={"out_of_twin_scope": merged})


# ---------------------------------------------------------------------------
# Job 3 — the seam
# ---------------------------------------------------------------------------


class Extraction(Enum):
    """How the prose-to-spec step ended. Three outcomes, all reportable."""

    EXTRACTED = "extracted"
    NO_EXTRACTOR = "no_extractor"
    FAILED = "failed"


BRIEF_TEMPLATE = """\
HYPOTHESIS AS IT NOW STANDS
---------------------------
{hypothesis}

RESIDUAL - what could not be settled without new data
-----------------------------------------------------
{residual}
"""


def brief_for_extractor(residual: str, hypothesis: str = "") -> str:
    """Exactly what the extractor is shown. Public so it can be pinned in a test.

    The residual leads because it is the brief - §5.1 item 6, *everything else
    is context*. The hypothesis is included because a residual read alone often
    omits the system: "whether the effect survives to the endpoint" says nothing
    about what is being measured or in what.
    """
    return BRIEF_TEMPLATE.format(
        hypothesis=hypothesis.strip() or "(not supplied)",
        residual=residual.strip() or "(not supplied)",
    )


def _residual_text(source: Any) -> str:
    """The residual, out of whatever layer 1 handed over.

    Duck-typed on purpose. `refute.handoff` is being written concurrently, and
    importing it would couple the two halves of a seam whose whole value is that
    each side can be built and tested without the other. The shapes accepted are
    the ones §5.4 makes plausible: a plain string, a `.residual` string, or a
    `.residual` sequence of `OpenItem`-like objects carrying `.statement`.

    An object with no residual raises rather than being stringified. Feeding
    `repr()` to an assay selector would produce a match on the class name, which
    is the kind of quiet nonsense that is very hard to find later.
    """
    if isinstance(source, str):
        return source

    residual = getattr(source, "residual", None)
    if residual is None:
        raise TypeError(
            f"{type(source).__name__} is neither a string nor an object with a "
            f"`.residual`. intake() reads the residual - the one thing layer 1 "
            f"could not settle - and has nothing to work from without it."
        )
    if isinstance(residual, str):
        return residual

    parts: list[str] = []
    for item in residual:
        if isinstance(item, str):
            statement = item
        else:
            statement = getattr(item, "statement", "") or ""
        statement = statement.strip()
        if statement:
            parts.append(statement)
    return "\n".join(parts)


def _hypothesis_text(source: Any) -> str:
    """The hypothesis, if the handover carries one. Falls back to the question.

    §5.1 lists both, and a `Handoff` that has been narrowed carries a hypothesis
    that differs from the question it started as. Either is better context than
    nothing; neither is the brief.
    """
    if isinstance(source, str):
        return ""
    for attribute in ("hypothesis", "question"):
        value = getattr(source, attribute, None)
        if isinstance(value, str) and value.strip():
            return value
    return ""


@dataclass(frozen=True)
class Intake:
    """Everything the gate needs, plus a record of how it was arrived at.

    `design` is None whenever extraction did not produce one, and `extraction`
    says which of the two reasons applies. Neither is a finding about the
    experiment, and `note` is worded so that it cannot be mistaken for one.
    """

    residual: str
    hypothesis: str
    selection: AssaySelection
    design: Any | None
    extraction: Extraction
    note: str
    narrative: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """True when the gate can be called with a protocol and a design.

        False splits three ways - no assay fits, no extractor, extraction failed
        - and the caller has to look at which, because they are not the same
        problem and two of them are not problems with the design.
        """
        return self.design is not None and not self.selection.none_of_these

    @property
    def protocol(self) -> AssayProtocol | None:
        """The leading protocol, or None when nothing fits.

        Reads through to the live registry rather than holding a reference, so
        an `Intake` stays a record of a decision rather than a snapshot of the
        registry at the moment it was made.
        """
        best = self.selection.best
        return REGISTRY.get(best.key) if best else None

    def render(self) -> str:
        return "\n".join(self.narrative)


def intake(
    handoff_or_text: Any,
    extractor: Callable[[str], Any] | None = None,
    *,
    registry: Mapping[str, AssayProtocol] | None = None,
) -> Intake:
    """Layer 1's handover to the two things layer 2's gate needs.

    Accepts a plain residual string or anything with a `.residual` - see
    `_residual_text`. Runs the deterministic assay selection first, because it
    costs nothing and works with no credential, then the one model call.

    Never raises for an extraction problem. A missing extractor and a failed
    extractor are both recorded on the result, in words that make no claim about
    the design, because a caller that has to catch an exception to find out its
    experiment could not be parsed will eventually report that as a bad design.

    When no assay fits, the reason is written into
    `out_of_twin_scope`. That is the whole join: a residual the
    registry cannot model arrives at the gate as OUT_OF_SCOPE rather than as a
    design that looks fine and is quietly about the wrong apparatus.
    """
    residual = _residual_text(handoff_or_text)
    hypothesis = _hypothesis_text(handoff_or_text)
    narrative: list[str] = []

    if isinstance(handoff_or_text, str):
        narrative.append("Read the residual as plain text.")
    else:
        narrative.append(
            f"Read the residual off a {type(handoff_or_text).__name__} "
            f"({len(residual.splitlines())} line(s))"
            + (", with its hypothesis as context." if hypothesis else ", no hypothesis given.")
        )

    selection = select_assay(residual, hypothesis, registry=registry)
    narrative.append(
        f"Ranked {len(selection.considered)} registry protocol(s) "
        f"deterministically, no model call. {selection.why}"
    )
    if selection.candidates and not selection.decisive:
        narrative.append(
            "The leader is not clear of the field, so the runner-up is carried "
            "rather than dropped."
        )

    unmodelled: list[str] = []
    if selection.none_of_these:
        unmodelled.append(
            f"no protocol in the assay registry models this residual "
            f"({', '.join(selection.considered) or 'the registry is empty'})"
        )
        narrative.append(
            "Recorded that on the design as out-of-twin-scope, so the gate "
            "routes OUT_OF_SCOPE instead of scoring it against an assay that "
            "does not fit."
        )

    spec_type = DesignSpec
    if selection.best and selection.best.key in TWINS:
        spec_type = TWINS[selection.best.key].design_spec_type

    try:
        design = extract_design(
            brief_for_extractor(residual, hypothesis),
            extractor,
            unmodelled=unmodelled,
            design_spec_type=spec_type,
        )
    except NoExtractorConfigured as exc:
        narrative.append(
            "Did not extract a design: no extractor is configured. The assay "
            "selection above stands - it needs no model."
        )
        return Intake(
            residual=residual,
            hypothesis=hypothesis,
            selection=selection,
            design=None,
            extraction=Extraction.NO_EXTRACTOR,
            note=str(exc),
            narrative=tuple(narrative),
        )
    except ExtractionFailure as exc:
        narrative.append(
            "The extractor failed. That is a parsing failure on our side and "
            "says nothing about the experiment; no design is reported, and no "
            "verdict either."
        )
        return Intake(
            residual=residual,
            hypothesis=hypothesis,
            selection=selection,
            design=None,
            extraction=Extraction.FAILED,
            note=str(exc),
            narrative=tuple(narrative),
        )

    declared = design.unmodelled()
    if declared:
        narrative.append(
            f"The design declares {len(declared)} thing(s) outside what the twin "
            f"models: {'; '.join(declared)}."
        )
    assigns = getattr(design, "assigns_wells", getattr(design, "assigns_animals", False))
    if assigns:
        if hasattr(design, "endpoint_time_h"):
            ep_str = f"endpoint {design.endpoint_time_h:g} h."
        else:
            ep_str = f"endpoint day {design.endpoint_day:g}."
        narrative.append(
            f"Extracted a design: {len(design.conditions)} arm(s), "
            f"{design.replicates_per_condition} per arm, {ep_str}"
        )
    else:
        narrative.append(
            "Extracted a design that assigns no wells/animals - it declines to run the "
            "experiment rather than proposing a cohort, which is a position and "
            "not a malformed spec."
        )
    return Intake(
        residual=residual,
        hypothesis=hypothesis,
        selection=selection,
        design=design,
        extraction=Extraction.EXTRACTED,
        note="",
        narrative=tuple(narrative),
    )



__all__ = [
    "BRIEF_TEMPLATE",
    "DECISIVE_MARGIN",
    "EVIDENCE_FLOOR",
    "FIELD_WEIGHTS",
    "HYPOTHESIS_WEIGHT",
    "MIN_MATCHED_TERMS",
    "NO_EXTRACTOR_MESSAGE",
    "RESIDUAL_WEIGHT",
    "AssayCandidate",
    "AssaySelection",
    "Extraction",
    "ExtractionFailure",
    "Intake",
    "NoExtractorConfigured",
    "TermMatch",
    "brief_for_extractor",
    "extract_design",
    "intake",
    "select_assay",
    "terms",
]
