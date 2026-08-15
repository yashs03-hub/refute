"""What layer 1 hands over, defined once, and its crossing into a requirement set.

Two layers meet here. Layer 1 answers everything about a hypothesis that can be
answered without a bench - it works the data, it works the literature, and it
rules out what can be ruled out. What it cannot settle crosses to layer 2, which
designs the experiment that would settle it. This module is that crossing, in
the direction it actually runs: `Finding` and `OpenItem` in, `Resolution` and
`ResolutionSet` out.

WHY THE TYPES LIVE HERE AND NOT IN TWO PLACES
---------------------------------------------
Property 1 of the handoff spec: **one definition, in one place, imported by
both.** Two copies of the same structure drift within hours and the drift is
invisible until something starts failing quietly. We cannot make layer 1 import
this file, so the next best thing is to make it the obvious candidate:

* Everything above the divider is stdlib. No `AssayProtocol`, no `DesignSpec`,
  no twin, no simulator, nothing that presumes an assay registry exists. A
  process that has never heard of `refute` can import - or vendor - the type
  block and lose nothing.
* The two enumerated vocabularies (`PROVENANCE_TIERS`, `GapReason`) are written
  out as literals rather than derived from `Provenance` and `BlockedReason`,
  because deriving them would put a `refute` import in the middle of the
  portable half. `tests/test_handoff.py` pins each literal against the enum it
  mirrors, so the two cannot drift apart without the suite saying so.
* Below the divider, the only intra-package import is `resolve`, which is itself
  stdlib plus one dataclass module.

DIVERGENCES FROM THE SPEC'S STARTING SHAPE - RAISE THESE WITH LAYER 1
---------------------------------------------------------------------
**1. `searched: bool` is too weak, so there is a typed reason beside it.**
A boolean can say "we looked" and "we did not look" and nothing else, and the
distinction that matters downstream is finer than that: six reasons a quantity
is missing route six different ways, because each implies a different next
action. Not searched is NOT a refusal and must never be rendered as one;
published-as-a-different-quantity is recoverable by one derivation;
ill-posed-as-a-scalar does not block a twin at all; and nobody's-to-publish
means ask the experimenter rather than run another search. `searched`
is kept, because layer 1 may already be emitting it, and `reason: GapReason` is
inferred from it when nobody sets it - so nothing on their side has to change on
the day, and anything that wants the finer answer can give it.

The invariant is made real rather than documented: **a claim that the literature
lacks something must carry the query that came back empty.** `OpenItem` refuses
to be constructed with NOT_REPORTED and no query, exactly as `Resolution` and
`Blocked` already refuse it. Without that, "we found nothing" and "we ran no
search" collapse into one record, and layer 2 designs an experiment to answer a
question the literature already settled.

**2. `origin_event: str = ""` on all three types.** Trace ids are
non-negotiable on layer 1's side - every artifact carries the id of the event
that produced it, and that is what makes the walk backwards possible from
whatever object you happen to be holding. A handoff that dropped them would end
the chain at exactly the point where two teams' code meets, which is where a
wrong answer is hardest to attribute. **Note the gap this does not close:**
`Resolution` has no trace field, so a finding's `origin_event` does not survive
into the resolution it produces. Either `Resolution` grows one or `source`
doubles as the join key; it needs deciding rather than leaving.

**3. `Finding.assumption` and `Finding.plausible_range`.** The spec's `Finding`
enumerates five provenance tiers and then gives two of them nowhere to live.
`Resolution` requires an assumption on a DERIVED value - otherwise a calculation
is indistinguishable from a measurement - and a plausible range on an ASSUMED
one - otherwise a stand-in presents as a measurement and the verdict cannot be
tested for sensitivity to it. With the spec's fields alone, every derived and
every assumed finding would be refused at this seam, which is a silent loss of
whole provenance tiers rather than a stated one. Both fields default to the
spec's behaviour, so a layer-1 emitter that ignores them is unaffected; a
finding that needs one and does not carry it is refused here rather than
coerced. Inventing a range is not on the table - it would manufacture the
evidence for the claim the range exists to test.

**4. The spec contradicts itself about provenance, and this follows §5.4.**
`Evidence.provenance` in the layer-1 internals lists four values
(measured | literature | derived | assumed); `Finding.provenance` in the handoff
lists five, adding `primary`. Ours has five and matches §5.4 exactly, which is
also the right way round: a value counted off primary records - a lab notebook,
a robot's execution log - is stronger evidence than one read out of a paper,
because it has not passed through the publication filter that removes the runs
that failed. Collapsing `primary` into `literature` inverts the ordering the
whole resolve layer sorts on. Layer 1's four-value list is the one to fix.

**5. `OpenItem.why` and `GapReason` are two vocabularies, and only one of them
routes.** `why` is the spec's (not_in_literature | not_computable | contested |
needs_new_data); `GapReason` is the resolve layer's. They line up on the two
that are claims about the literature and not at all on the other two, so `why`
is kept verbatim and only `not_in_literature` and `needs_new_data` infer a
positive reason. `contested` and `not_computable` infer NOT_YET_SEARCHED, which
deliberately under-claims: it routes "not ready", never a refusal, and the
reader still sees the `why` in `unmodelled_mentions`. Guessing CONTEXT_DEPENDENT
for `contested` would be worse than useless - that reason does not block a twin,
so the design would route as though the quantity were fine and the simulator
would reach for a number that is not there. This is the shared-vocabulary
question, and it has to be agreed rather than inferred by whichever side wrote
its mapping first.

MATCHING IS CONSERVATIVE, AND THAT IS THE WHOLE DESIGN
-------------------------------------------------------
A `Finding` is a statement about biology. A `Resolution` is keyed to a named
constant like `p_delaminate_by_endpoint`. Bridging them is a guess, and the two
kinds of wrong answer are not symmetric: **an unmatched finding costs coverage,
a wrongly matched one feeds a wrong number into a power calculation and the
output still looks like a calculation.** So a match requires all of:

* the requirement's key named as a whole term in the finding's `statement` -
  not in `quote`, which is the source's own words and would never contain our
  variable names, and not in `scope`, which describes conditions. "Whole term"
  reads prose as well as identifiers, so `effect_size`, "effect size" and
  "effect-size" are one name, while `effect_size_ci` and `alpha-SMA` are not
  `effect_size` and `alpha`;
* exactly one key named, because a statement naming two is ambiguous about
  which quantity its value belongs to;
* units that agree exactly after normalisation, with one declared exception
  below;
* no other finding claiming the same key with a different value or units.

There is no synonym table. A units check with a synonym table is where a units
check goes to die: every entry is a small judgement about equivalence made once,
in the abstract, by whoever was writing the table, and a wrong one is
undetectable downstream. The shared vocabulary for entities, readouts and units
is a thing for both teams to agree explicitly before either side hardcodes it,
not something to approximate here.

The cost of that refusal falls on layer 1, so the strings it has to emit are
published rather than left to be discovered: `vocabulary.units_contract_report`
prints the exact unit string for every requirement key, tier 1 and tier 0, and
the normalisation applied before comparison. Without it the failure mode is not
an error - it is a `ResolutionSet` reporting zero coverage, which reads exactly
like a search that found nothing.

The one exception is not a synonym. `tier0_needs()` declares `effect_size` and
`within_arm_sd` in "readout units", which is a placeholder rather than a unit -
the arithmetic only ever uses their ratio, so neither is pinned absolutely.
Requirements whose units begin that way accept any units, and in exchange the
findings that fill them must agree with *each other*: a difference in microns
over a spread in pascals is not a standardised effect size.

Everything unmatched stays NOT_YET_SEARCHED, and the result is total over the
requirement set - every required key has an entry, always, for the reasons
`resolve.py` gives. Not NOT_SUPPLIED, tempting as that is for the tier-0
quartet, which no search could ever recover: NOT_SUPPLIED asserts that the
experimenter has not said, and a handoff is not the experimenter. Claiming it
here would turn "we have not been told yet" into a refusal, one layer too early
to know. Layer 1 may state it explicitly if it knows; this module will not infer
it. A finding with `value=None` is not a resolution at all. It
is prose, and prose belongs in `unmodelled_mentions`, where the pipeline prints
it and the gate is not allowed to route on it.

TWO KINDS OF FAILURE, TWO DIFFERENT BLOCKED REASONS
----------------------------------------------------
A **defect in the record** - a derived value with no assumption, two findings
that disagree, a statement naming two keys - leaves the key NOT_YET_SEARCHED.
Nothing can be claimed until a person fixes the record, and NOT_YET_SEARCHED is
the only reason that routes "not ready" rather than "no". A **well-formed
finding of the wrong quantity** - the units do not match - blocks with
UNITS_MISMATCH, because that is a real claim about what layer 1 found, and the
gate already knows what to do with it: hand it back for one derivation attempt
before treating it as missing.

Neither raises. `adapt.py` refuses a malformed record loudly because every
record it converts is a literal in this repository and a raise there fails the
test suite of the person who wrote it. A `Handoff` arrives from another process
at run time, so the same loudness would take down a run over one bad finding out
of thirty. The types raise at construction, where the fix is; the matcher never
does, and records every refusal as a mention instead.

THE §5.2 BOUNDARY, AND WHY TIER 0 IS REACHABLE AT ALL
-------------------------------------------------------
The spec says layer 1 does not "estimate an effect size" or "propose a sample
size". Two of the four tier-0 requirements are `effect_size` and
`within_arm_sd`. Read literally, no quantity crosses, tier 0 is unreachable,
every design routes REFUSE, and it looks like a defect in layer 2 when it is a
gap in the contract.

The resolution is that **a reported quantity is a finding; an estimated one is
an estimate.** Layer 1 reporting that a published study saw a 4.7-fold change
with an SD of 0.9 at n=6 is reporting - it is item 3 of what crosses, "each
finding with its source, the sentence that carries it, and the conditions it
holds under". Layer 1 asserting that the effect here will probably be about 4.7
is estimating, and that is layer 2's call to make. The line between them is
already in the type system: it is `ASSUMED`, the tier defined as nobody's
measurement. `crosses_as_report` is that rule, and the matcher enforces it, so
an assumed tier-0 quantity is refused however plausible its range.
`HANDOFF_FILLABLE_TIER0` records which of the four may cross and on what
grounds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

__all__ = [
    "FINDING_KINDS",
    "HANDOFF_FILLABLE_TIER0",
    "OPEN_ITEM_WHY",
    "PROVENANCE_TIERS",
    "READOUT_RELATIVE_UNITS",
    "Finding",
    "GapReason",
    "Handoff",
    "OpenItem",
    "accepts_any_units",
    "crosses_as_report",
    "normalise_units",
    "resolution_set_from_handoff",
    "resolutions_from_findings",
    "tier0_needs_a_handoff_can_fill",
]


# =============================================================================
# The shared types. Stdlib only - see the module docstring on why that matters.
# =============================================================================

# What a finding says about the hypothesis. Not a statement about whether its
# number is usable: a quantity reported inside a finding that contradicts the
# hypothesis is still a quantity, and dropping it would lose the measurements
# that most deserve to reach a design.
FINDING_KINDS: tuple[str, ...] = ("supports", "contradicts", "rules_out", "measures")

# Where a number came from, strongest first. Mirrors `resolve.Provenance` value
# for value; written out rather than derived so this half of the module imports
# nothing. `tests/test_handoff.py` pins the two together.
PROVENANCE_TIERS: tuple[str, ...] = (
    "measured",    # computed from data layer 1 holds
    "primary",     # counted off primary records (ELN, robot log)
    "literature",  # read out of a published source
    "derived",     # computed from reported quantities
    "assumed",     # nobody's measurement; a stand-in
)

# Why an item is open, in the spec's vocabulary. Kept verbatim and mapped
# conservatively - see divergence 5 in the module docstring.
OPEN_ITEM_WHY: tuple[str, ...] = (
    "not_in_literature",
    "not_computable",
    "contested",
    "needs_new_data",
)


class GapReason(Enum):
    """Why a quantity is missing, in the values that route differently.

    Mirrors `resolve.BlockedReason` exactly, value for value, and is defined
    here so the type block stays importable by a process that has no `refute`.
    The correspondence is one-to-one by `.value` and is pinned by a test; when
    the resolve layer gains a reason - it gained NOT_SUPPLIED after this module
    was written - that test fails rather than this module silently mapping the
    new one onto the nearest old one.

    Each reason implies a different next action, which is the only reason to
    have six instead of a boolean: run a pilot, convert it, measure it on your
    own rig, sweep it, tell the tool the number, go and look.
    """

    NOT_REPORTED = "not_reported"            # searched, and it is not there
    UNITS_MISMATCH = "units_mismatch"        # published as a different quantity
    ASSAY_SPECIFIC = "assay_specific"        # instrument-relative, not transferable
    CONTEXT_DEPENDENT = "context_dependent"  # ill-posed as a scalar
    NOT_SUPPLIED = "not_supplied"            # nobody's to publish; ask the experimenter
    NOT_YET_SEARCHED = "not_yet_searched"    # no claim either way

    @property
    def is_a_claim_about_the_literature(self) -> bool:
        """True for the reason that asserts something about what gets published.

        That claim requires having listened. The others are properties of the
        constant, the instrument or the experimenter, and need no corpus to
        establish - so requiring a query for them would push an honest record
        toward a fabricated one.
        """
        return self is GapReason.NOT_REPORTED


# Inference from the spec's `why` when nobody set a `GapReason`, and only for a
# search that actually ran. Two of the four `why` values are claims about the
# literature and map cleanly; the other two are not, and under-claim on purpose.
_WHY_TO_REASON: Mapping[str, GapReason] = {
    "not_in_literature": GapReason.NOT_REPORTED,
    "needs_new_data": GapReason.NOT_REPORTED,
    "contested": GapReason.NOT_YET_SEARCHED,
    "not_computable": GapReason.NOT_YET_SEARCHED,
}


@dataclass(frozen=True)
class Finding:
    """One thing layer 1 established, with what supports it.

    `value` is optional because most of what layer 1 finds is not a number - a
    mechanism, a scope restriction, a contradiction between two papers. Those
    are findings and they must cross; they are simply not resolutions, and the
    matcher carries them as mentions rather than pretending they are quantities.

    `units` is mandatory the moment `value` is not None. Property 3 of the
    handoff spec, and it is stated as an invariant rather than a convention
    because a number whose units are implied is a number that will be misread -
    once, quietly, by an arithmetic that has no way to notice.
    """

    statement: str                 # what was found
    kind: str                      # supports | contradicts | rules_out | measures
    provenance: str                # measured | primary | literature | derived | assumed
    source: str                    # DOI, dataset id, analysis id
    quote: str = ""                # the sentence, or what was computed
    scope: str = ""                # species, tissue, assay, conditions
    value: float | None = None     # when the finding is a quantity
    units: str = ""                # mandatory when `value` is set
    assumption: str = ""           # divergence 3: required to cross as DERIVED
    plausible_range: tuple[float, float] | None = None  # required to cross as ASSUMED
    origin_event: str = ""         # divergence 2: the trace id that produced it

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("a finding with no statement carries nothing")
        if self.kind not in FINDING_KINDS:
            raise ValueError(
                f"{self.statement[:40]!r}: kind must be one of {FINDING_KINDS}, "
                f"got {self.kind!r}"
            )
        if self.provenance not in PROVENANCE_TIERS:
            raise ValueError(
                f"{self.statement[:40]!r}: provenance must be one of "
                f"{PROVENANCE_TIERS}, got {self.provenance!r} - hand over a bare "
                "statement and layer 2 cannot tell a measurement from a guess"
            )
        if not self.source.strip():
            raise ValueError(
                f"{self.statement[:40]!r}: a finding needs a source, or nothing "
                "downstream can be checked against what it came from"
            )
        if self.value is not None and not self.units.strip():
            raise ValueError(
                f"{self.statement[:40]!r}: a quantity needs units. They are a "
                "field on every quantity, not a convention."
            )
        if self.plausible_range is not None:
            lo, hi = self.plausible_range
            if lo > hi:
                raise ValueError(
                    f"{self.statement[:40]!r}: plausible range {self.plausible_range} "
                    "is inverted"
                )

    @property
    def is_quantity(self) -> bool:
        """Whether this finding could become a `Resolution` at all."""
        return self.value is not None


@dataclass(frozen=True)
class OpenItem:
    """One thing layer 1 could not settle, and which kind of gap it is.

    Property 5 of the handoff spec, and the one that matters most: **"looked and
    it is not there" must be distinguishable from "have not looked."** If layer 1
    reports nothing found for something it never searched, layer 2 designs an
    experiment to answer a question the literature already settled - and the
    design will look perfectly reasonable.

    So the reason is typed, and the type refuses to let the strong claim be made
    for free. `searched` is retained from the spec's shape and infers a reason
    when none is given.
    """

    statement: str                 # what could not be settled
    why: str                       # not_in_literature | not_computable
                                   # | contested | needs_new_data
    searched: bool = False         # False means never looked, not absent
    queries_run: tuple[str, ...] = ()
    reason: GapReason | None = None  # divergence 1; inferred when left unset
    origin_event: str = ""           # divergence 2

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("an open item with no statement carries nothing")
        if self.why not in OPEN_ITEM_WHY:
            raise ValueError(
                f"{self.statement[:40]!r}: why must be one of {OPEN_ITEM_WHY}, "
                f"got {self.why!r}"
            )

        # Inference, not a default, and done here rather than in a property so
        # that `reason` is never None on a constructed item. A field that is
        # sometimes None is a field every consumer re-derives, and they will not
        # all re-derive it the same way.
        if self.reason is None:
            inferred = (
                _WHY_TO_REASON[self.why] if self.searched
                else GapReason.NOT_YET_SEARCHED
            )
            object.__setattr__(self, "reason", inferred)

        if not self.searched and self.reason.is_a_claim_about_the_literature:
            raise ValueError(
                f"{self.statement[:40]!r}: searched=False says no search ran, and "
                f"{self.reason.value} is a claim about what gets published, which "
                "requires one. Only NOT_YET_SEARCHED claims nothing."
            )
        if self.reason.is_a_claim_about_the_literature and not self.queries():
            raise ValueError(
                f"{self.statement[:40]!r}: {self.reason.value} asserts that the "
                "literature is silent, which requires having listened. Record the "
                "query that came back empty, or use NOT_YET_SEARCHED, which "
                "claims nothing."
            )

    def queries(self) -> tuple[str, ...]:
        """The recorded queries, trimmed, with the blanks dropped.

        Blanks are dropped rather than kept because a whitespace query is
        truthy enough to satisfy a naive check and proves nothing - which is
        exactly how an invariant of this kind is usually defeated.
        """
        return tuple(q.strip() for q in self.queries_run if q.strip())


@dataclass(frozen=True)
class Handoff:
    """Everything layer 1 found, everything it ruled out, and what remains.

    `residual` may not be empty. Layer 1 has two terminal states: the question
    is answered or the hypothesis is dead, in which case it reports and stops
    and there is no handoff at all; or something remains that only new data can
    settle, and that residual is what layer 2 designs against. A handoff with no
    residual is the first state wearing the second's clothes, and the only thing
    layer 2 could do with it is invent a question.

    Note what is *not* here: no assay, no effect-size estimate, no proposed n.
    Layer 1 does not design the experiment, so there is nothing to check a
    handoff's assay key against - which is why `resolution_set_from_handoff`
    takes the assay key from its caller and cannot detect a mismatch the way
    `adapt.resolution_set_from_report` can.
    """

    question: str                  # the original question, in plain language
    hypothesis: str                # as it now stands: refined, narrowed, partly answered
    findings: tuple[Finding, ...] = ()
    ruled_out: tuple[str, ...] = ()
    residual: tuple[OpenItem, ...] = ()
    limits: str = ""               # what was not looked at, and why
    origin_event: str = ""         # divergence 2

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError("a handoff with no question cannot be designed against")
        if not self.hypothesis.strip():
            raise ValueError(
                "a handoff with no hypothesis has nothing for layer 2 to design "
                "against - the hypothesis as it now stands is item 2 of what crosses"
            )
        if not self.residual:
            raise ValueError(
                "a handoff with no residual is the resolved terminal state, which "
                "does not hand off. The residual is the brief; everything else is "
                "context."
            )

    @property
    def quantities(self) -> tuple[Finding, ...]:
        """The findings that carry a number. The rest are prose."""
        return tuple(f for f in self.findings if f.is_quantity)


# =============================================================================
# Below here is layer 2's. Two intra-package imports: `resolve`, which is itself
# stdlib plus one dataclass module, and `digest`, which is six lines over
# `hashlib` - nothing reaches a protocol or the twin.
# =============================================================================

from .digest import requirement_digest  # noqa: E402  (see the divider above)
from .resolve import (  # noqa: E402  (deliberate: see the divider above)
    TIER0_NEEDS,
    BlockedReason,
    Provenance,
    Requirement,
    Resolution,
    ResolutionSet,
)

# Requirement units that name the readout rather than a unit. Written by
# `requirements.tier0_needs`, where the reason is stated: the arithmetic only
# uses the ratio of effect to spread, so neither is pinned absolutely.
#
# Public, because it is part of what layer 1 has to be told: two of the four
# tier-0 requirements accept any units, and `vocabulary.units_contract_report`
# says so by reading this rather than by restating it.
READOUT_RELATIVE_UNITS = "readout units"

# Which of the four tier-0 needs a handoff may legitimately fill, and on what
# grounds. Every entry is a report of something already done, never a proposal
# about the experiment being designed - which is the whole content of the
# division of labour in §5.2.
HANDOFF_FILLABLE_TIER0: Mapping[str, str] = {
    "effect_size": (
        "a reported effect size is a finding, not an estimate. Layer 1 may say "
        "what a study measured; only layer 2 may say what to power against."
    ),
    "within_arm_sd": (
        "replicate spread is printed in methods sections and computable from "
        "the data layer 1 already holds. It is the one quantity layer 2 must "
        "never invent, so a reported one is worth more here than anywhere else."
    ),
    "alpha": (
        "reportable, not proposable: the threshold a prior study tested at. "
        "Layer 2 remains free to set its own, and usually should."
    ),
    "n_per_arm": (
        "what a prior study used per arm. 'Does not propose a sample size' is "
        "about the experiment being designed; reporting an old one is reporting."
    ),
}


def tier0_needs_a_handoff_can_fill() -> tuple[str, ...]:
    """The tier-0 keys a handoff may legitimately fill, in requirement order.

    All four, which is the point: read literally, §5.2's "layer 1 does not
    estimate an effect size or propose a sample size" would leave tier 0
    permanently unreachable, every design routing REFUSE, and the contract gap
    presenting as a failure of the design layer. The condition is on provenance
    rather than on the key - see `crosses_as_report` - so the boundary is
    enforced without closing the path.

    Raises if `TIER0_NEEDS` gains a key with no entry here. A quantity nobody
    decided the ownership of is a quantity both layers will assume the other is
    supplying.
    """
    missing = set(TIER0_NEEDS) - set(HANDOFF_FILLABLE_TIER0)
    if missing:
        raise ValueError(
            f"TIER0_NEEDS gained {sorted(missing)} without a ruling here on "
            "whether a handoff may fill it. Decide it explicitly: an undecided "
            "quantity is one both layers will expect the other to supply."
        )
    return tuple(k for k in TIER0_NEEDS if k in HANDOFF_FILLABLE_TIER0)


def crosses_as_report(finding: Finding, requirement: Requirement) -> bool:
    """Whether `finding` may fill `requirement` under §5.2's division of labour.

    A quantity crosses when it is *reported* - measured in the data, counted off
    primary records, read out of a paper, or computed from numbers read out of
    one. It does not cross when it is ASSUMED, because an assumed tier-0
    quantity is precisely the estimate the spec reserves for layer 2: a
    stand-in effect size is an effect size somebody guessed, however carefully,
    and it would arrive at a power calculation indistinguishable from one that
    was measured.

    The restriction is deliberately confined to tier 0. A tier-1 constant is a
    property of an apparatus rather than a claim about the experiment being
    designed, and a stand-in for one - with the range that makes it sweepable -
    is honest and useful. Tier 0 is where an assumption becomes the answer.
    """
    if finding.value is None:
        return False
    if requirement.tier == "tier0" and finding.provenance == "assumed":
        return False
    return True


def resolutions_from_findings(
    findings: Iterable[Finding],
    requirements: Iterable[Requirement],
) -> dict[str, Resolution]:
    """Layer 1's quantities against a requirement set, total over that set.

    Every required key gets an entry. A key nothing matched is NOT_YET_SEARCHED
    rather than absent, because a missing key and a blocked key route
    differently and only one of them reads as work still to do.

    Nothing here raises. The refusals - a wrong-units finding, two findings that
    disagree, a derived value with no assumption - are recorded as blocked
    resolutions and are visible in full through `resolution_set_from_handoff`,
    which carries the explanation for each one as a mention.
    """
    return _match(tuple(findings), _requirements(requirements)).resolutions


def resolution_set_from_handoff(
    handoff: Handoff,
    assay_key: str,
    requirements: Iterable[Requirement],
) -> ResolutionSet:
    """A whole handoff as a total answer to one requirement set.

    Three passes, in this order, and the order is the precedence:

    1. **Findings**, which are the only source of values.
    2. **Open items**, which can only turn a key that no finding claimed into a
       typed gap. This is how "we searched and it is not published" reaches the
       gate as NOT_REPORTED instead of being indistinguishable from silence. An
       open item that names a key a finding already reported a value for is a
       contradiction - reported and unsettled at once - and downgrades that key
       to NOT_YET_SEARCHED, because nobody can route on a set that says both.
    3. **Everything that did not fit**, into `unmodelled_mentions`: prose
       findings, residual items this requirement set has no term for, what layer
       1 ruled out, its stated limits, and every refusal above with the reason
       for it. Nothing that crossed is dropped. The gate may not route on any of
       it, and the pipeline prints all of it.

    `assay_key` comes from the caller because a handoff does not name an assay -
    picking one is layer 2's job. So unlike `adapt.resolution_set_from_report`,
    this cannot detect that it has been handed the wrong assay's findings; the
    protection is that requirement keys are the contract and a finding that
    names none of them matches nothing.
    """
    reqs = _requirements(requirements)
    matched = _match(handoff.findings, reqs)

    resolutions = dict(matched.resolutions)
    mentions = list(matched.mentions)
    by_key = {r.key: r for r in reqs}
    applied: dict[str, OpenItem] = {}

    for item in handoff.residual:
        named = _keys_named(item.statement, by_key)

        if not named:
            # The residual is the brief. One that names no requirement key is
            # not noise - it is the thing layer 2 was asked to design against,
            # and it has to reach a reader even though no gate can route on it.
            mentions.append(
                f"residual this requirement set has no term for "
                f"({item.why}, {item.reason.value}): {item.statement!r}"
            )
            continue

        if len(named) > 1:
            mentions.append(
                f"open item names {len(named)} requirement keys "
                f"({', '.join(named)}), so which one it is open about is "
                f"undecidable: {item.statement!r}"
            )
            continue

        key = named[0]

        if key in matched.claimed:
            if resolutions[key].resolved:
                resolutions[key] = _unsearched(key)
                mentions.append(
                    f"{key!r}: a finding reports a value for it and an open item "
                    f"says it is unsettled. Both cannot be true, so neither is "
                    f"used: {item.statement!r}"
                )
            else:
                mentions.append(
                    f"{key!r}: an open item repeats a key whose finding could not "
                    f"be used, so the finding's blocked reason stands: "
                    f"{item.statement!r}"
                )
            continue

        earlier = applied.get(key)
        if earlier is not None:
            if earlier.reason is not item.reason:
                resolutions[key] = _unsearched(key)
                mentions.append(
                    f"{key!r}: two open items give different reasons "
                    f"({earlier.reason.value}, {item.reason.value}), so neither "
                    f"is used"
                )
            continue

        applied[key] = item
        # NOT_REPORTED with nothing behind it is unrepresentable: `OpenItem`
        # refuses to be constructed that way, so no query is ever invented here.
        resolutions[key] = Resolution(
            quantity=key,
            reason=BlockedReason(item.reason.value),
            queries_run=item.queries(),
        )

    mentions.extend(f"ruled out by layer 1: {s}" for s in handoff.ruled_out if s.strip())
    if handoff.limits.strip():
        mentions.append(f"layer 1's stated limits: {handoff.limits.strip()}")

    return ResolutionSet(
        assay_key=assay_key,
        requirement_version=_version_of(reqs),
        resolutions=resolutions,
        unmodelled_mentions=tuple(mentions),
    )


# --- internals ---------------------------------------------------------------


@dataclass(frozen=True)
class _Matched:
    """What one pass over the findings produced.

    `claimed` is the third thing, and it is not derivable from the other two: a
    key whose only finding was refused looks identical to a key nothing
    mentioned, and the open-item pass has to be able to tell them apart.
    """

    resolutions: dict[str, Resolution]
    mentions: tuple[str, ...]
    claimed: frozenset[str]


def _match(
    findings: tuple[Finding, ...],
    requirements: tuple[Requirement, ...],
) -> _Matched:
    by_key = {r.key: r for r in requirements}
    candidates: dict[str, list[Finding]] = {k: [] for k in by_key}
    claimed: set[str] = set()
    mentions: list[str] = []

    for finding in findings:
        if not finding.is_quantity:
            mentions.append(
                f"finding with no quantity in it ({finding.kind}, "
                f"{finding.provenance}): {finding.statement!r}"
            )
            continue

        named = _keys_named(finding.statement, by_key)
        if not named:
            mentions.append(
                f"quantity finding that names no requirement key: "
                f"{finding.statement!r} = {finding.value:g} {finding.units}"
            )
            continue
        if len(named) > 1:
            mentions.append(
                f"quantity finding names {len(named)} requirement keys "
                f"({', '.join(named)}), so which one its value belongs to is "
                f"undecidable: {finding.statement!r}"
            )
            continue

        claimed.add(named[0])
        candidates[named[0]].append(finding)

    resolutions = {
        key: _resolve_one(by_key[key], candidates[key], mentions) for key in by_key
    }
    _enforce_readout_agreement(by_key, resolutions, mentions)

    return _Matched(
        resolutions=resolutions,
        mentions=tuple(mentions),
        claimed=frozenset(claimed),
    )


def _resolve_one(
    req: Requirement,
    candidates: list[Finding],
    mentions: list[str],
) -> Resolution:
    """One requirement, given every finding that named it.

    Refusals are recorded against the individual finding rather than the key, so
    one unusable finding does not suppress a usable one beside it.
    """
    usable: list[Finding] = []
    mismatched: list[Finding] = []

    for finding in candidates:
        problem = _unusable(finding, req)
        if problem is not None:
            mentions.append(f"{req.key!r}: a finding was refused - {problem}")
        elif _units_agree(req, finding):
            usable.append(finding)
        else:
            mismatched.append(finding)

    if not usable:
        if mismatched:
            # A well-formed finding of a different quantity. That is a claim,
            # not a defect, and UNITS_MISMATCH is the reason the gate can hand
            # back for one derivation attempt before treating it as missing.
            seen = ", ".join(sorted({f.units for f in mismatched}))
            mentions.append(
                f"{req.key!r}: reported in {seen}, and the requirement is in "
                f"{req.units!r}. Not converted - a units guess here would put a "
                f"wrong number into a power calculation, and it would still "
                f"print as a calculation."
            )
            return Resolution(quantity=req.key, reason=BlockedReason.UNITS_MISMATCH)
        return _unsearched(req.key)

    distinct = {(f.value, normalise_units(f.units)) for f in usable}
    if len(distinct) > 1:
        mentions.append(
            f"{req.key!r}: {len(usable)} findings give "
            f"{len(distinct)} different values "
            f"({', '.join(f'{v:g} {u}' for v, u in sorted(distinct))}), so none "
            f"is used. Picking one would be arbitrary and would look like a "
            f"measurement."
        )
        return _unsearched(req.key)

    return _as_resolution(req, usable[0])


def _unusable(finding: Finding, req: Requirement) -> str | None:
    """Why this finding cannot become a resolution, or None if it can.

    Everything here is a defect in the record or a boundary violation, and both
    are stated rather than repaired. `Resolution` would refuse the first two
    anyway; catching them here turns a raise that would end the run into one
    blocked key and one sentence a person can act on.
    """
    if not crosses_as_report(finding, req):
        return (
            f"an assumed value for the tier-0 quantity {req.key!r} is layer 1 "
            f"estimating, which is layer 2's call to make: {finding.statement!r}"
        )
    if finding.provenance == "derived" and not finding.assumption.strip():
        return (
            f"derived, with no assumption stated, which makes it "
            f"indistinguishable from a measurement: {finding.statement!r}"
        )
    if finding.provenance == "assumed" and finding.plausible_range is None:
        return (
            f"assumed, with no plausible range, so the verdict could not be "
            f"tested for sensitivity to it - and inventing a range would "
            f"manufacture the evidence the range exists to test: "
            f"{finding.statement!r}"
        )
    return None


def _as_resolution(req: Requirement, finding: Finding) -> Resolution:
    """One finding in the vocabulary the gate routes on.

    The units recorded are the finding's, never the requirement's. For a
    readout-relative requirement the finding's are the only real ones, and for
    any other they are equal after normalisation - so taking the requirement's
    would at best be a no-op and at worst would overwrite the evidence with the
    expectation.

    `origin_event` has nowhere to go. See divergence 2: this is where the trace
    chain currently ends.
    """
    return Resolution(
        quantity=req.key,
        value=finding.value,
        units=finding.units,
        provenance=Provenance(finding.provenance),
        source=finding.source,
        quote=finding.quote,
        assumption=finding.assumption,
        plausible_range=finding.plausible_range,
    )


def _enforce_readout_agreement(
    by_key: Mapping[str, Requirement],
    resolutions: dict[str, Resolution],
    mentions: list[str],
) -> None:
    """Readout-relative quantities must agree with each other or none stands.

    `effect_size` and `within_arm_sd` are declared in "readout units", which is
    a placeholder: the arithmetic uses only their ratio, so neither is pinned
    absolutely and each on its own accepts any units. That licence is only
    sound while they are in the *same* units. A difference in microns over a
    spread in pascals is not a standardised effect size, and the power figure it
    produces is a number with no meaning that is indistinguishable from one with
    a meaning.
    """
    relative = {
        key for key, req in by_key.items()
        if accepts_any_units(req.units) and resolutions[key].resolved
    }
    seen = {normalise_units(resolutions[key].units) for key in relative}
    if len(seen) <= 1:
        return

    for key in sorted(relative):
        resolutions[key] = Resolution(
            quantity=key, reason=BlockedReason.UNITS_MISMATCH
        )
    mentions.append(
        f"{', '.join(sorted(relative))} are stated in terms of the readout and "
        f"arrived in different units ({', '.join(sorted(seen))}), so their ratio "
        f"is not a standardised effect size and none of them is used."
    )


def _keys_named(text: str, by_key: Mapping[str, Requirement]) -> list[str]:
    """Every requirement key named as a whole term in `text`, sorted.

    Sorted so the ambiguity message reads the same on every run - the order
    findings happen to arrive in must not change what a refusal says.
    """
    lowered = text.lower()
    return sorted(key for key in by_key if _names(key, lowered))


# Characters that continue a name. A key is named only where neither side is one
# of these, which is what stops `alpha` being found inside `alpha-SMA` and
# `effect_size` inside `effect_size_ci`. The hyphen is in here for the first of
# those: biological names are full of hyphenated qualifiers, and a key that
# matched one of them would resolve a requirement against a completely different
# measurement.
_NAME_CHAR = r"[a-z0-9_\-]"

# What may sit between the parts of a key where it appears in prose. Layer 1
# writes sentences, not identifiers, so "effect size" and "effect_size" are the
# same name - but only as the same sequence of parts, in order.
_PART_GAP = r"[\s_\-]+"


def _names(key: str, lowered: str) -> bool:
    parts = _PART_GAP.join(re.escape(p) for p in key.lower().split("_") if p)
    pattern = rf"(?<!{_NAME_CHAR}){parts}(?!{_NAME_CHAR})"
    return re.search(pattern, lowered) is not None


def _units_agree(req: Requirement, finding: Finding) -> bool:
    """Exact after normalisation, or the requirement declares no absolute units.

    No synonym table. See the module docstring: an equivalence decided in the
    abstract, by whoever was writing the table, is undetectable when it is wrong
    - and the failure it produces is a confident number rather than a gap.
    """
    if accepts_any_units(req.units):
        return True
    return normalise_units(req.units) == normalise_units(finding.units)


def accepts_any_units(requirement_units: str) -> bool:
    """Whether a requirement declares its units relative to the readout.

    Public because layer 1 needs to know which requirements it cannot get the
    units wrong on. It is not a loophole: the two that qualify are `effect_size`
    and `within_arm_sd`, and `_enforce_readout_agreement` still requires them to
    agree with each other.
    """
    return normalise_units(requirement_units).startswith(READOUT_RELATIVE_UNITS)


def normalise_units(units: str) -> str:
    """The only thing done to a unit string before the two are compared.

    Lowercased, stripped, and internal runs of whitespace collapsed to a single
    space. Nothing else, and the restraint is the contract rather than an
    unfinished implementation: every further fold - "um" to "µm", "%" to
    "percent", "fraction" to "probability" - is a claim that two units mean the
    same thing, and that is the synonym table the module docstring refuses.

    Published, and published as this function rather than as a description of
    it, because "the strings must match exactly" is only checkable by whoever
    has to emit them if they also know what is normalised away.
    `vocabulary.units_contract_report` prints the contract and calls this.
    """
    return " ".join(units.lower().split())


def _unsearched(key: str) -> Resolution:
    return Resolution(quantity=key, reason=BlockedReason.NOT_YET_SEARCHED)


def _requirements(requirements: Iterable[Requirement]) -> tuple[Requirement, ...]:
    """The requirement set, de-duplicated, first declaration winning.

    `pipeline.requirements_for` already unions tier 1 and tier 0 and can hand
    over a repeated key when a protocol declares a constant tier 0 also names.
    Resolutions are keyed by name, so a duplicate would answer once and count
    twice.
    """
    seen: set[str] = set()
    out: list[Requirement] = []
    for req in requirements:
        if req.key in seen:
            continue
        seen.add(req.key)
        out.append(req)
    return tuple(out)


def _version_of(requirements: tuple[Requirement, ...]) -> str:
    """The digest `requirements.requirement_version` would produce.

    Over the tier-1 keys of the set actually answered. Tier 0 is assay-blind and
    belongs to no protocol's version, and computing it from the set handed over
    rather than from the registry is what lets the pipeline notice that an
    answer is total over a stale requirement list.

    The algorithm comes from `digest.py`, which is `hashlib` and nothing else -
    so it can be imported here without importing `requirements`, and with it
    `AssayProtocol`, which this module deliberately knows nothing about. That
    import was the reason the hash was copied here in the first place; the copy
    is gone and the reason still holds. `tests/test_contract.py` pins this
    against the other two paths.
    """
    return requirement_digest(r.key for r in requirements if r.tier == "tier1")
