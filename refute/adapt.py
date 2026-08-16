"""The crossing between the calibration layer and the resolve layer.

Two vocabularies for the same facts grew on either side of a seam that was
never built. `assays/evidence.py` records what a literature pass found and what
it could not, as `Evidence` and `Blocked`, and `assays/literature.py` holds the
findings themselves. `resolve.py` consumes `Resolution` and `ResolutionSet`,
and everything downstream of it - the gate, the pipeline, the CLI - speaks only
that. Nothing converted between them, so the recorded findings could not reach
the machinery built to route on findings, and the whole downstream half could
only ever be run on hand-written fixtures.

This module is that conversion, and it goes one way only.

WHY A SEPARATE MODULE, AND NOT A METHOD ON `Evidence`
-----------------------------------------------------
Because the dependency has to run downhill. `resolve` imports `BlockedReason`
from the calibration layer; if the calibration layer imported `Resolution` back,
the two would be a cycle, and the cycle is not hypothetical - see the note in
`assays/evidence.py` about where `Provenance` had to be moved to. Keeping the
adapter in its own module above both means `literature.py` stays readable, and
testable, without importing a requirement set, a gate or a simulator.

WHAT SURVIVES THE CROSSING, AND WHAT DOES NOT
---------------------------------------------
The value, its units, its source, its quote, its assumption, its provenance
tier, the blocked reason and the query all survive. Two things do not, because
`Resolution` has no field for them: `Blocked.detail` and `Evidence.note`.

That loss is deliberate rather than tolerated. Both are prose written for a
person - `detail` is the substantive content of a blocked entry and `note` is
the caveat on a found one - and the gate routes on which quantities resolved
and why the rest did not, never on prose. A `Resolution` that carried a
paragraph would invite something downstream to read it, and a router that reads
prose is a keyword search with extra steps. The prose stays where a person can
find it: `CalibrationReport.summary()` prints all of it.

WHY THE MAPPINGS ARE THE WAY THEY ARE
-------------------------------------
`Blocked.searched` is one query string; `Resolution.queries_run` is a tuple,
because a resolver that ran three searches should be able to show three. One
string becomes a one-tuple, and a blank one becomes a refusal - see below.

`Evidence.derived` is a two-valued flag and `Resolution.provenance` is a
five-valued enum. `Evidence.tier` already carries the wider vocabulary and
already infers LITERATURE/DERIVED from the flag when nobody set it, so this
module reads the tier and does not re-derive the mapping. One place to get it
wrong is better than two.

WHY A BLANK QUERY RAISES RATHER THAN DOWNGRADING
------------------------------------------------
`Blocked.__post_init__` already refuses NOT_REPORTED with an empty `searched`,
so the only way to arrive here with a NOT_REPORTED claim and nothing behind it
is a query string made of whitespace: truthy enough to pass that check, empty
enough to prove nothing. Two honest treatments were available - downgrade the
reason to NOT_YET_SEARCHED, or refuse the record.

It refuses. `Resolution` has no field for a note, so a downgrade could only be
recorded in a field meant for something else, which makes it a silent rewrite
of somebody's claim about the literature: the conflation of "we did not find
it" with "we did not look for it" that `literature.py` keeps scrupulously, run
backwards. And refusing costs no researcher anything, because every `Blocked`
in this repository is a literal in a source file and `tests/test_adapt.py`
converts all of them - so a blank query fails the test suite of the person who
wrote it, long before it can reach a command line.

The third option, inventing a query to satisfy the invariant, is not an option.
It would manufacture the evidence for the one claim the project rests on.

TOTALITY IS THE POINT OF `resolution_set_from_report`
------------------------------------------------------
The registry owns the requirement list, never the resolver (`resolve.py` says
why). So the conversion is driven by the requirements it is handed, not by what
the report happens to contain: every required key gets an entry, and a key the
report says nothing about becomes NOT_YET_SEARCHED rather than being absent. A
missing key and an unsearched key route differently, and only one of them is
representable.

That is the opposite of filtering the output down to the requirements, which is
the failure `test_fixture_resolver_ignores_the_requirements_it_is_handed` pins:
a resolver that dropped what it could not answer would report full coverage
forever. Nothing is dropped here. Findings for quantities the requirement set
has no term for are carried as `unmodelled_mentions`, which the pipeline prints
as a caveat and the gate is not allowed to route on.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from .assays.evidence import (
    Blocked,
    BlockedReason,
    CalibrationReport,
    Evidence,
    Provenance,
)
from .assays.literature import REPORTS
from .digest import requirement_digest
from .resolve import Requirement, Resolution, ResolutionSet

__all__ = [
    "RecordedResolver",
    "resolution_from_blocked",
    "resolution_from_evidence",
    "resolution_set_from_report",
]


def resolution_from_evidence(ev: Evidence) -> Resolution:
    """One recovered constant, in the vocabulary the gate routes on.

    The tier is read off `Evidence.tier`, which is LITERATURE or DERIVED unless
    somebody deliberately said otherwise, and the assumption is carried across
    with it - a DERIVED resolution without one is rejected by `Resolution`, for
    the same reason a derived `Evidence` without one is rejected: a calculation
    that does not say what it assumed is indistinguishable from a measurement.

    ASSUMED is refused rather than converted. `Resolution` requires a plausible
    range on an assumed value so the verdict can be swept and reported as
    sensitive to it, and `Evidence` has nowhere to record a range - it is a type
    for numbers that came from somewhere. Passing the point value through with
    no range would produce a stand-in that presents as a measurement and cannot
    be tested for sensitivity, which is the exact failure the range exists to
    prevent. An assumed constant belongs in the resolver that can state its
    range, not in a calibration report.
    """
    tier = ev.tier  # never None: `Evidence` infers it from `derived` if unset
    if tier is Provenance.ASSUMED:
        raise ValueError(
            f"{ev.constant}: an assumed value needs a plausible range and "
            f"`Evidence` has no field for one, so it cannot cross this seam. "
            f"Without a range the sweep cannot run and the verdict is reported "
            f"as though the stand-in were a measurement."
        )
    return Resolution(
        quantity=ev.constant,
        value=ev.value,
        units=ev.units,
        provenance=tier,
        source=ev.source,
        quote=ev.quote,
        assumption=ev.assumption,
    )


def resolution_from_blocked(b: Blocked) -> Resolution:
    """One constant that could not be filled, with the search behind the claim.

    The single `searched` string becomes a one-tuple, whitespace-trimmed: the
    surrounding blanks are formatting, and two records of the same query should
    compare equal. A reason that is not a claim about the literature keeps its
    query too when it has one - recording a search is never wrong, and it is
    what distinguishes "published as a different quantity" from "we assumed so".

    Raises when a NOT_REPORTED record has no query behind it. See the module
    docstring: the alternatives are a silent downgrade with nowhere to record
    itself, or an invented query, and both are worse than a loud stop.
    """
    query = b.searched.strip()
    if b.reason.is_a_claim_about_the_literature and not query:
        raise ValueError(
            f"{b.constant}: {b.reason.value} asserts that the literature is "
            f"silent, and the recorded query is blank. This cannot be converted "
            f"into a legal Resolution, and it must not be converted by "
            f"inventing one - fix the record: give it the query that came back "
            f"empty, or state NOT_YET_SEARCHED, which claims nothing."
        )
    return Resolution(
        quantity=b.constant,
        reason=b.reason,
        queries_run=(query,) if query else (),
    )


def resolution_set_from_report(
    report: CalibrationReport | None,
    assay_key: str,
    requirements: Iterable[Requirement],
) -> ResolutionSet:
    """A recorded calibration report as a total answer to a requirement set.

    `report` may be None. An assay nobody has attempted is not an error and not
    an empty answer: it is a set in which every required quantity is
    NOT_YET_SEARCHED, which routes NOT_READY and claims nothing about the
    design. `literature.NOT_ATTEMPTED` exists to keep exactly that denominator
    honest, and this is the behaviour that agrees with it.

    A report answering a different assay raises. Constant names are shared
    across protocols - `measurement_cv` and `tgfb_fold_change` each mean
    something different in three of them - so a mismatched report would convert
    cleanly, validate, and be wrong. `FixtureResolver` refuses the same thing
    for the same reason.

    A constant that appears twice in one report also raises. Resolutions are
    keyed by name, so one of the two would silently win, and if the pair is a
    found/blocked contradiction the winner decides whether the constant exists.
    """
    requirements = tuple(requirements)
    if report is not None and report.key != assay_key:
        raise ValueError(
            f"report is for assay {report.key!r}, asked for {assay_key!r}. "
            f"Constant names are shared between protocols, so this would "
            f"convert without complaining and answer the wrong question."
        )

    recorded = _index(report)
    resolutions: dict[str, Resolution] = {}
    for req in requirements:
        if req.key in resolutions:
            continue
        entry = recorded.pop(req.key, None)
        resolutions[req.key] = (
            Resolution(quantity=req.key, reason=BlockedReason.NOT_YET_SEARCHED)
            if entry is None
            else _convert(entry)
        )

    # Whatever the report recorded that nothing asked for. Kept, because a
    # finding this requirement set has no term for is a real limit on how much
    # of the experiment the verdict covers, and the reader is the only one who
    # can weigh it. The gate may not route on these.
    mentions = tuple(
        f"{'recorded value' if isinstance(e, Evidence) else 'recorded block'} "
        f"for {name!r}, which this requirement set has no term for"
        for name, e in sorted(recorded.items())
    )

    return ResolutionSet(
        assay_key=assay_key,
        requirement_version=_version_of(requirements),
        resolutions=resolutions,
        unmodelled_mentions=mentions,
    )


class RecordedResolver:
    """A `Resolver` backed by the findings recorded in `literature.py`.

    The counterpart to `FixtureResolver`, and the reason both exist: a fixture
    is a hand-written statement of what a resolver's output should look like,
    whereas this replays what a literature pass actually found on 2026-08-04.
    Running the pipeline on it is the first time the downstream half is
    exercised against real recovery rates rather than against a description of
    them - and what it demonstrates is the asymmetry the project is about, since
    the constants that resolve are effect sizes and precisions and the ones that
    come back NOT_REPORTED are the failure rates.

    It is still offline and still deterministic. The reports are literals in a
    source file, so a test that uses this resolver does not depend on what a
    corpus contained on the day it ran.

    An assay with no recorded report resolves to an all-NOT_YET_SEARCHED set
    rather than raising. That is not leniency: three of the six tier-1
    scaffolds have never been attempted, and "we have not looked" is a true
    statement about them that the gate knows how to route. Raising would force
    every caller to keep its own list of which assays have been attempted, and
    those lists go stale.

    The requirement list is never derived from the report. It arrives from the
    registry, and every key in it is answered - see the module docstring on
    totality, and `resolve.py` on why a resolver that chooses its own
    requirements always reports full coverage.
    """

    name = "recorded"

    def __init__(self, reports: Mapping[str, CalibrationReport] | None = None):
        """`reports` is injectable so a test can pin behaviour on a small,
        stable set rather than on whatever the literature pass last recorded."""
        self.reports: Mapping[str, CalibrationReport] = (
            REPORTS if reports is None else reports
        )

    def resolve(
        self, assay_key: str, requirements: Iterable[Requirement]
    ) -> ResolutionSet:
        return resolution_set_from_report(
            self.reports.get(assay_key), assay_key, requirements
        )


# --- internals ---------------------------------------------------------------


def _convert(entry: Evidence | Blocked) -> Resolution:
    return (
        resolution_from_evidence(entry)
        if isinstance(entry, Evidence)
        else resolution_from_blocked(entry)
    )


def _index(report: CalibrationReport | None) -> dict[str, Evidence | Blocked]:
    """Every recorded entry by constant name, refusing any name twice.

    Both halves of the report share one namespace because `Resolution` is keyed
    by name. A constant listed as both found and blocked is a contradiction
    about whether the number exists, and silently preferring either half would
    settle it by accident.
    """
    index: dict[str, Evidence | Blocked] = {}
    if report is None:
        return index
    for entry in (*report.found, *report.blocked):
        name = entry.constant
        if name in index:
            raise ValueError(
                f"{report.key}: {name!r} is recorded twice. Resolutions are "
                f"keyed by constant name, so one of the two entries would be "
                f"dropped without anything saying which."
            )
        index[name] = entry
    return index


def _version_of(requirements: tuple[Requirement, ...]) -> str:
    """The digest `requirements.requirement_version` would produce.

    Computed from the tier-1 keys of the set actually answered rather than by
    looking the protocol up in the registry, and the difference matters: the
    version records which requirement set this answer is total over, so a caller
    that answered a doctored or stale list must produce a version that differs
    from the registry's. That skew is what `pipeline._version_warning` exists to
    surface, and reading the registry here would hide it.

    Tier-0 keys are excluded because `requirement_version` hashes a protocol's
    declared constants, which are tier 1 by construction. Tier 0 is assay-blind
    and belongs to no protocol's version.

    The algorithm is `digest.requirement_digest`, shared with `requirements` and
    `handoff`; it used to be a third copy of the same six lines here, because
    the function in `requirements.py` takes an `AssayProtocol` and this has only
    the list. Sharing the hash does not reintroduce that coupling - what is
    shared is how a key list becomes a digest, and *which* keys are hashed stays
    the caller's, which is the part that had to stay separate.
    `tests/test_adapt.py` still pins this against the registry for every
    protocol, and `tests/test_contract.py` pins all three paths together.
    """
    return requirement_digest(r.key for r in requirements if r.tier == "tier1")
