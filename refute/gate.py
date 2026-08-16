"""Which kind of answer is available for this design, and which is not.

Between "we resolved the constants" and "here is a verdict" there is a decision
nobody else can make: what sort of claim this system is entitled to make about
this design at all. A mechanistic twin, the assay-blind arithmetic, a refusal, a
statement that the twin models a different apparatus, or - the one most easily
lost - "we have not looked yet". This module is that decision and nothing else.

THE PROPERTY
------------
**The gate routes on which quantities resolved and why the rest did not. It
never reads `Resolution.value`.** Only the simulator dereferences a number.

That is not tidiness. Coverage is a property of the requirement set, and the
moment a router consults a number it starts making judgements the numbers cannot
support - "this rate looks too high to be real", "that variance must be a typo" -
and those judgements are precisely the model-opinion this project exists to keep
out of the loop. Keeping the gate value-blind makes the whole class
unrepresentable rather than merely discouraged.

The consequence worth relying on: a `ResolutionSet` whose every `value` is None
still fully determines a route, so the gate's entire test matrix can be written
by hand. `tests/test_gate.py` pins that with a resolution set built from objects
that raise on any attempt to read `.value`.

FIVE ROUTES, IN PRECEDENCE ORDER
--------------------------------
The order is the whole design; each rule exists to stop the one below it from
firing on a case it would answer wrongly.

  1. NOT_READY      something is still unsearched. Checked first because routing
                    an unsearched set as a refusal emits "not answerable at this
                    scale" for an experiment nobody has looked into yet. That is
                    the most damaging wrong output available here - it is the
                    sentence people quote - and it is indistinguishable, in the
                    output, from the finding this project actually made.
  2. OUT_OF_SCOPE   the design specifies an apparatus this protocol does not
                    model. Checked before coverage because full coverage of the
                    wrong apparatus is worse than no coverage: it produces a
                    confident number about a plate nobody proposed.
  3. TIER1          every tier-1 constant is covered and the twin is not mostly
                    made of stand-ins.
  4. TIER0          the twin cannot be built, but the arithmetic can be done.
  5. REFUSE         neither. The gaps are named, so the refusal is actionable.

WHY OUT_OF_SCOPE IS NOT A KEYWORD SEARCH
----------------------------------------
An earlier out-of-scope guard in this repository was a fail-ALWAYS guard: it
flagged the twin's own assay and its own readout as unmodelled, so every design
was refused. It passed the whole test suite, because there was a test that a
genuinely out-of-scope design is refused and no test that a legitimate design is
not. "Refuse everything" satisfies every test that only checks refusals.

So the authority here is `design.out_of_twin_scope`, a field the extractor is
instructed to leave empty for ordinary protocol detail, plus one structural
comparison against the protocol that cannot fire on the apparatus the protocol
declares. `ResolutionSet.unmodelled_mentions` is a hint - it can corroborate a
scope violation the design already declares, and it can never create one on its
own. A hint that could route by itself is a keyword search with extra steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .assays.base import AssayProtocol
from .design import DesignSpec
from .requirements import tier0_needs, tier1_needs
from .resolve import Requirement, ResolutionSet


class Route(Enum):
    """The kinds of answer this system can give about a design."""

    TIER1 = "tier1"
    """Build the mechanistic twin and simulate the design."""

    TIER0 = "tier0"
    """No twin, but the assay-blind power arithmetic is available."""

    OUT_OF_SCOPE = "out_of_scope"
    """The protocol models a different apparatus than the one proposed."""

    REFUSE = "refuse"
    """Not enough resolved to say anything, and the gaps are named."""

    NOT_READY = "not_ready"
    """Not a refusal. The requirement set has not been fully searched."""


@dataclass(frozen=True)
class RouteDecision:
    """A route, and everything a caller needs to explain or act on it.

    The three tuples are deliberately separate rather than one bag of strings:
    `missing` is a work list, `unmodelled` is a limit of the twin, and `sweep` is
    an instruction to the simulator. Collapsing them would leave the caller
    guessing which of the three a given string was.
    """

    route: Route
    why: str
    missing: tuple[str, ...] = ()
    """Required keys with no usable value.

    On NOT_READY these are the unsearched keys - the work still to do. On TIER0
    they are the tier-1 gaps that forced the fallback, which is the only place
    the reason for the downgrade is recorded. On REFUSE they are the tier-0
    gaps, which is what makes the refusal actionable rather than a shrug.
    """

    unmodelled: tuple[str, ...] = ()
    """What put the design out of scope, in the design's own words."""

    sweep: tuple[str, ...] = ()
    """Keys the simulator must sweep rather than fix.

    Assumed constants and ill-posed ones. A verdict that is reported as a single
    number over one of these is reporting a choice of prior as a measurement.
    """


def _keys(requirements: Iterable[Requirement]) -> tuple[str, ...]:
    return tuple(r.key for r in requirements)


def _scope_violations(design: Any, protocol: AssayProtocol) -> tuple[str, ...]:
    """What this design proposes that this protocol cannot represent.

    Two sources, and neither is a text match against the protocol's vocabulary.

    The first is `design.unmodelled()` - the extractor's own declaration, with
    blanks discarded. It is authoritative because it is produced by the half of
    the pipeline that read the design, and because the extraction prompt defines
    it by exclusion: gel formulation, seeding density, media, doses and the
    analysis plan are explicitly NOT deviations. A design that merely specifies
    the assay in detail therefore arrives here with an empty list.

    The second is one structural mismatch that only the protocol knows about. A
    destructive readout is measured once per unit, so a design that normalises
    each unit to that same unit's earlier measurement is describing an apparatus
    that does not exist - not a worse experiment, an unrepresentable one. It is
    checked here rather than left to the simulator because the simulator would
    have to invent the missing baseline to produce any number at all.

    Both are exact. Neither can fire on the apparatus the protocol declares,
    which is the failure mode this function is shaped around.
    """
    violations = list(design.unmodelled())

    if protocol.readout.destructive and getattr(design, "normalise_to_own_baseline", False):
        violations.append(
            f"each {protocol.unit} is normalised to its own pre-treatment "
            f"measurement, but '{protocol.readout.name}' is a destructive "
            f"readout - one measurement per {protocol.unit}, so no "
            f"{protocol.unit} has an earlier measurement of itself"
        )

    return tuple(violations)



def route_design(
    design: Any,
    protocol: AssayProtocol,
    resolutions: ResolutionSet,
) -> RouteDecision:
    """Decide what kind of answer is available for this design.

    Reads which quantities resolved, why the rest did not, and what the design
    proposes. Never reads a value; see the module docstring for why that matters
    more than it looks like it should.
    """
    # 1. Unsearched beats everything, including out-of-scope. A design might well
    #    be out of scope too, but saying so on the strength of a set nobody has
    #    finished filling is a guess that happens to be dressed as a finding.
    if not resolutions.complete:
        unsearched = tuple(resolutions.unsearched())
        return RouteDecision(
            route=Route.NOT_READY,
            why=(
                f"{len(unsearched)} of this requirement set's quantities have not "
                f"been searched yet, so there is nothing to route on - this is an "
                f"unfinished search, not a finding about the design."
            ),
            missing=unsearched,
        )

    # 2. Coverage of the wrong apparatus is not coverage.
    violations = _scope_violations(design, protocol)
    if violations:
        # The hint corroborates and is reported as corroboration. It is never
        # the thing that got us here, so an over-eager resolver cannot refuse a
        # design on its own authority.
        corroboration = (
            f" ({len(resolutions.unmodelled_mentions)} corroborating mention(s) "
            f"in the resolution set)"
            if resolutions.unmodelled_mentions
            else ""
        )
        return RouteDecision(
            route=Route.OUT_OF_SCOPE,
            why=(
                f"'{protocol.key}' does not model {len(violations)} thing(s) this "
                f"design specifies, so any score would be about a different "
                f"apparatus{corroboration} - a limit of the twin, not a defect in "
                f"the design."
            ),
            unmodelled=violations,
        )

    tier1_keys = _keys(tier1_needs(protocol))
    tier0_keys = _keys(tier0_needs())

    # 3. A twin, if the constants are there and are mostly somebody's measurements.
    #
    #    `tier1_keys` being empty is not full coverage. `covers(())` is vacuously
    #    true, and a protocol that declares no requirements has failed to declare
    #    them rather than proved it needs none - which is the registry-side form
    #    of the resolver that only asks for what it can answer. Falling through
    #    costs a correctly-declared protocol nothing.
    if tier1_keys and resolutions.covers(tier1_keys):
        if not resolutions.over_assumed(tier1_keys):
            sweep = tuple(resolutions.swept(tier1_keys))
            detail = (
                f"; {len(sweep)} of them must be swept rather than fixed"
                if sweep
                else ""
            )
            return RouteDecision(
                route=Route.TIER1,
                why=(
                    f"every tier-1 constant for '{protocol.key}' resolved, so the "
                    f"mechanistic twin can be built{detail}."
                ),
                sweep=sweep,
            )
        over_assumed = True
    else:
        over_assumed = False

    # 4. No twin. The arithmetic is assay-blind, so it survives a great deal that
    #    the twin does not - which is the whole reason it is the fallback.
    if resolutions.covers(tier0_keys):
        tier1_gaps = tuple(resolutions.missing(tier1_keys))
        if over_assumed:
            cause = (
                f"more than half the tier-1 constants for '{protocol.key}' are "
                f"stand-ins, so a twin would report its own priors rather than a "
                f"measurement"
            )
        elif tier1_keys:
            cause = (
                f"{len(tier1_gaps)} tier-1 constant(s) for '{protocol.key}' are "
                f"unavailable, so no twin can be built"
            )
        else:
            cause = f"'{protocol.key}' declares no tier-1 requirements to build a twin from"
        return RouteDecision(
            route=Route.TIER0,
            why=f"{cause}, but every tier-0 input is present, so the assay-blind arithmetic stands.",
            missing=tier1_gaps,
            sweep=tuple(resolutions.swept(tier0_keys)),
        )

    # 5. Nothing to say. Name the gaps: a refusal that does not say what would
    #    lift it is indistinguishable from the system being broken.
    tier0_gaps = tuple(resolutions.missing(tier0_keys))
    return RouteDecision(
        route=Route.REFUSE,
        why=(
            f"neither a twin for '{protocol.key}' nor the tier-0 arithmetic is "
            f"available: {', '.join(tier0_gaps)} could not be resolved."
        ),
        missing=tier0_gaps,
    )
