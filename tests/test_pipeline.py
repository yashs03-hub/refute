"""One test per exit, and one test per sentence the exits are recognised by.

The pipeline's job is not only to route correctly - it is to say which of five
things happened in words a researcher will read the right way. Three of the five
exits are stops that have nothing to do with the quality of the design, and the
default reading of a stop emitted by a scorer is "your experiment is bad". So
the wording is asserted here alongside the route, and the two assertions are not
redundant: a pipeline that routes perfectly and phrases NOT_READY as a verdict
has failed at the thing it exists for.

The fixtures are hand-written `ResolutionSet` JSON, which is what makes this
suite offline and deterministic. The gate routes on coverage and provenance and
never dereferences a value, so a test that depends on a number is a test that
has misunderstood the seam.

Note the sharper form of that claim, because an earlier draft of this docstring
got it wrong: a *resolved* entry cannot carry `value: null`, since
`Resolution.__post_init__` rejects an entry that is neither resolved nor
blocked. Null values are legal only on blocked entries. The property is
therefore proved by substitution rather than by absence - see
`test_route_is_independent_of_every_value` in `tests/test_resolve.py`, which
perturbs every number in every fixture and asserts the routing summary does not
move. The one consumer that genuinely needs numbers is tier 0, which does the
arithmetic; that path is asserted to degrade to a refusal rather than invent
them.

Each test skips rather than fails when its fixture, or the gate itself, has not
landed yet. These are three parallel builds against one frozen contract, and a
red suite in the middle of that says nothing about whether anybody's half works.

THE FIXTURE CONVENTION
----------------------
Every fixture in `cases/fixtures/` is total over BOTH requirement sets: the
protocol's tier-1 constants and the four tier-0 keys, each one either resolved
or carrying a blocked reason. Five of them used to carry no tier-0 key at all,
which was not a smaller test case but a differently-shaped one - the pipeline
counts an absent key as missing, so a file that was total over tier 1 and silent
on tier 0 reported as partially resolved and read as though the search had
stalled. Totality over one set and not the other is also the trap the next
fixture author falls into, since nothing about the file says which set it
answers.

The counts are therefore per tier, and `test_the_resolve_line_reports_each_tier`
pins that. Coverage of one set is enough to route: tier 1 builds the twin, tier
0 is the fallback, and neither is a fraction of the other.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# The gate and the requirement registry are built in parallel with this module.
# Skipping is correct while they are in flight: importing them is what proves
# the contract holds, so there is nothing to assert until they exist.
pytest.importorskip("refute.gate", reason="refute/gate.py not written yet")
pytest.importorskip("refute.requirements", reason="refute/requirements.py not written yet")

from refute.assays import get  # noqa: E402
from refute.baselines import EXPERT  # noqa: E402
from refute.cli import main  # noqa: E402
from refute.design import EXPERIMENT_4_AS_RUN  # noqa: E402
from refute.gate import Route  # noqa: E402
from refute.pipeline import NOT_ANSWERABLE, run  # noqa: E402
from refute.requirements import tier0_needs, tier1_needs  # noqa: E402
from refute.resolve import FixtureResolver  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "cases" / "fixtures"

# What each fixture is for, as a route. The table is the point: it is the only
# place the seven cases are asserted to be seven different cases, so a fixture
# edit that quietly collapses two of them onto the same route fails here rather
# than in a demo. Read against EXPERIMENT_4_AS_RUN, which is the design the CLI
# uses, so these are literally the routes `refute route --fixture ...` prints.
EXPECTED_ROUTES = {
    "full_coverage": Route.TIER1,
    "context_dependent": Route.TIER1,
    "unmodelled_mention": Route.TIER1,
    "tier1_gaps_tier0_ok": Route.TIER0,
    "all_blocked": Route.REFUSE,
    "over_assumed": Route.REFUSE,
    "one_unsearched": Route.NOT_READY,
}

# Small, because none of these tests is about a power figure - but not as small
# as it could be. Below roughly 80 plates the advisor's endpoint lever on EXPERT
# flips sign on simulation noise alone, which would make the terminal test pass
# or fail on the seed rather than on the property it is asserting. Scoring is
# deterministic for a fixed count, so this is a floor rather than a tolerance.
SIMS = 120


def _case(name: str):
    """`(protocol, resolver)` for a named fixture, or skip.

    The protocol comes from the fixture's own `assay_key` rather than being
    hard-coded, so a fixture written against a different assay is exercised
    rather than silently compared to the wrong requirement set.
    """
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        pytest.skip(f"fixture {name}.json not written yet")
    key = json.loads(path.read_text()).get("assay_key", "")
    try:
        protocol = get(key)
    except KeyError:
        pytest.skip(f"{name}.json answers unregistered assay {key!r}")
    return protocol, FixtureResolver(path)


def _text(result) -> str:
    """The narrative, lowercased and unwrapped.

    Assertions are on sentences, and a sentence that happens to wrap across two
    narrative lines is the same sentence. Normalising here keeps the tests from
    pinning the line breaks, which are formatting rather than contract.
    """
    return " ".join(result.render().lower().split())


# The two fractions on the resolve line. The detail in brackets after a count is
# optional and deliberately not captured: it is prose about why a number reads
# the way it does, and pinning it here would make every wording change a test
# failure. The fractions are the contract.
_COVERAGE = re.compile(
    r"resolve: tier-1 (\d+)/(\d+) covered(?: \([^)]*\))?, "
    r"tier-0 (\d+)/(\d+) covered"
)


def _coverage(result) -> tuple[tuple[int, int], tuple[int, int]]:
    """`((tier-1 covered, tier-1 needed), (tier-0 covered, tier-0 needed))`.

    Parsed out of the rendered narrative rather than read off the result object,
    because the thing under test is what a reader sees. A pipeline that computed
    the split correctly and printed one combined fraction would pass every
    assertion made against its internals and still be the bug this fixes.
    """
    match = _COVERAGE.search(result.render())
    assert match is not None, f"no per-tier resolve line in:\n{result.render()}"
    a, b, c, d = (int(g) for g in match.groups())
    return (a, b), (c, d)


# --- one test per exit ------------------------------------------------------


def test_full_coverage_reaches_the_twin():
    """The false-positive guard.

    A gate that refuses everything passes every test that only checks refusals,
    and refute has shipped that bug before - the out-of-scope check once flagged
    the twin's own assay. This is the test that would have caught it: a
    canonical in-scope design, on a fully covered requirement set, must actually
    reach the simulator and come back with a score.
    """
    protocol, resolver = _case("full_coverage")
    result = run(EXPERT, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is Route.TIER1
    assert result.score is not None
    assert 0.0 <= result.score.power <= 1.0
    assert any("simulate:" in line for line in result.narrative)


def test_tier1_gaps_fall_through_to_tier0():
    """Tier 1 unavailable is not the end of the ladder.

    The route may legitimately arrive as REFUSE rather than TIER0: the gate
    routes on which keys resolved, and a hand-written fixture that resolves them
    all to `null` is covered without being computable. Both are correct
    outcomes, and the assertion is that whichever one happens is *stated* -
    silently reporting a power figure derived from an absent variance is the one
    thing this path must never do.
    """
    protocol, resolver = _case("tier1_gaps_tier0_ok")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=SIMS)

    assert result.decision.route in (Route.TIER0, Route.REFUSE)
    if result.decision.route is Route.TIER0:
        assert result.score is not None
        # Non-negotiable on every tier-0 output: no mechanism was modelled.
        assert "arithmetic, not simulation" in _text(result)
    else:
        assert result.score is None
        assert "guessed variance" in _text(result)


def test_all_blocked_refuses_and_says_what_it_lacks():
    """A refusal that does not name its gap is indistinguishable from a crash."""
    protocol, resolver = _case("all_blocked")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is Route.REFUSE
    assert result.score is None
    text = _text(result)
    assert "refused" in text
    # The missing tier-0 keys, by name. Either the gate listed them or the
    # pipeline recomputed them; a caller cannot act on "something was missing".
    named = result.decision.missing or ()
    for key in named:
        assert key in text


def test_one_unsearched_is_not_ready_and_not_a_verdict():
    """The most damaging wrong output this system can produce.

    An unsearched requirement set routed as though it were searched emits "not
    answerable at this scale" for an experiment that is merely unfinished - and
    that is the sentence people quote. So NOT_READY must produce no score at
    all, and must not contain the phrase.
    """
    protocol, resolver = _case("one_unsearched")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is Route.NOT_READY
    assert result.score is None
    assert result.advice is None
    assert not result.terminal

    text = _text(result)
    assert NOT_ANSWERABLE not in text
    assert "not a verdict on the design" in text
    assert "not been searched" in text or "not yet searched" in text


def test_a_design_that_leaves_the_apparatus_is_out_of_scope_and_points_at_tier_0():
    """Out of scope is a limit of the simulator, and a dead end only if unsaid.

    Tier 0 is assay-blind, so it still has something to say about a design the
    twin cannot represent. Omitting that turns a partial answer into no answer.

    The design carries the scope violation, not the fixture. Scope is a
    comparison between the `DesignSpec` and the protocol; the resolver never saw
    the design, so its mentions cannot be what puts a design out of scope. See
    the test below.
    """
    protocol, resolver = _case("unmodelled_mention")
    collagen = EXPERIMENT_4_AS_RUN.model_copy(
        update={
            "out_of_twin_scope": [
                "matrix changed from fibrin to rat-tail collagen I at 2 mg/mL"
            ]
        }
    )
    result = run(collagen, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is Route.OUT_OF_SCOPE
    assert result.score is None
    assert result.advice is None
    text = _text(result)
    assert "tier 0" in text
    assert "limit of the simulator" in text
    assert "not a problem with the design" in text
    assert "collagen" in text


def test_resolver_hints_are_carried_as_a_caveat_and_never_route():
    """A hint that could refuse a design on its own authority is a keyword search.

    `unmodelled_mentions` comes from a half of the pipeline that never saw the
    design, so it must not be able to produce a stop. It must also not vanish: a
    verdict computed while three unmodelled effects sat in the resolution set is
    narrower than it looks, and the reader is the only one who can weigh that.
    """
    protocol, resolver = _case("unmodelled_mention")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is not Route.OUT_OF_SCOPE
    assert "caveat:" in _text(result)
    assert "no term for" in _text(result)


# --- the two routes that are about how a value is treated -------------------


def test_context_dependent_sweeps_rather_than_withholds():
    """An ill-posed scalar is not an absent one.

    `CONTEXT_DEPENDENT` converts a point value into a swept range, so the design
    still reaches the twin and the verdict is reported as sensitive to it. The
    collapse of this distinction into "blocked" is the single most likely error
    in the whole seam, and it fails safe-looking: everything simply refuses.
    """
    protocol, resolver = _case("context_dependent")
    result = run(EXPERT, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is Route.TIER1
    assert result.score is not None
    assert result.decision.sweep, "a context-dependent key must be swept, not dropped"
    assert "swept rather than fixed" in _text(result)


def test_over_assumed_does_not_pass_as_a_twin():
    """A tier-1 twin built mostly of stand-ins is reporting its own priors."""
    protocol, resolver = _case("over_assumed")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is not Route.TIER1


# --- the terminal state -----------------------------------------------------


def test_the_terminal_state_is_reachable_and_says_so():
    """The output this whole pipeline exists to be able to produce.

    EXPERT is the best plate available on this apparatus, written with hindsight
    the agent under test is denied. Every single-lever change to it is simulated
    and none of them helps, so the honest answer is that the question cannot be
    answered at this scale. A pipeline that cannot reach this state will polish
    a doomed design forever, and the wording matters as much as the flag: this
    is a fact about the apparatus, not a failure of the search.
    """
    protocol, resolver = _case("full_coverage")
    result = run(EXPERT, protocol, resolver, n_sims=SIMS)

    assert result.decision.route is Route.TIER1
    assert result.terminal, "no single change improves EXPERT - this must terminate"
    assert result.advice is None, "advice is reported only when something helps"

    text = _text(result)
    assert NOT_ANSWERABLE in text
    assert "not a failure of the search" in text


def test_terminal_holds_when_there_is_nothing_left_to_try():
    """The same state arrived at by exhausting the advisor rather than by losing.

    EXPERT still has one lever the advisor will try and reject. This design has
    none at all: it is already antifibrinolytic, already two arms filling the
    plate, already normalised and locked, already imaging early and before
    treatment, and its endpoint sits between two candidates so there is no
    earlier one to move to. It pins the terminal machinery independently of any
    calibration constant, so a future change to the twin cannot quietly make the
    terminal state unreachable while this suite stays green.
    """
    protocol, resolver = _case("full_coverage")
    exhausted = EXPERT.model_copy(
        update={"endpoint_time_h": 144.0, "imaging_times_h": [2, 6, 12, 24, 48, 120, 144]}
    )
    result = run(exhausted, protocol, resolver, n_sims=SIMS)

    if result.decision.route is not Route.TIER1:
        pytest.skip("full_coverage does not route to tier 1 for this design")
    assert result.advice is None
    assert result.terminal
    assert "no single change left to try" in _text(result)
    assert NOT_ANSWERABLE in _text(result)


def test_a_design_with_room_to_improve_does_not_terminate():
    """The complement, or `terminal` could be a constant and still pass above.

    Experiment 4 as run has obvious levers - it has no antifibrinolytic and its
    endpoint sits well past the scaffold's survival - so the advisor must find
    them and the pipeline must not declare a terminal state.
    """
    protocol, resolver = _case("full_coverage")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=SIMS)

    if result.decision.route is not Route.TIER1:
        pytest.skip("full_coverage does not route to tier 1 for this design")
    assert not result.terminal
    assert result.advice is not None
    assert NOT_ANSWERABLE not in _text(result)


# --- the resolve line -------------------------------------------------------
# The route below it is correct on every fixture. What was wrong was the sentence
# introducing it: one fraction over the union of both requirement sets, which
# made a fully-answered tier-1 set read as two thirds answered and then routed
# tier 1 with full confidence. A reader resolves that contradiction by deciding
# the tool is confused, and they are right to - the two statements cannot both be
# true of one requirement list. They are true of two.

# The route is decided by the gate before anything is simulated, so a fixture's
# route does not depend on this at all. Small purely to keep the table below
# cheap; anything asserting on a power figure must use SIMS.
ROUTE_ONLY_SIMS = 20


def test_the_resolve_line_reports_each_tier():
    """Two fractions, one per requirement set, against the registry's own counts.

    Hard-coding 10 and 4 would pin the fibrin protocol rather than the property,
    and the property is that each denominator is the size of the set the gate
    routes on. If a constant is added to the protocol, this must still pass and
    the fixtures must fail - which is the split of responsibility the
    requirement version exists to enforce.
    """
    protocol, resolver = _case("full_coverage")
    result = run(EXPERT, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    (t1_covered, t1_needed), (t0_covered, t0_needed) = _coverage(result)
    assert t1_needed == len(tier1_needs(protocol))
    assert t0_needed == len(tier0_needs())
    assert (t1_covered, t0_covered) == (t1_needed, t0_needed)

    text = _text(result)
    assert "tier-1" in text and "tier-0" in text


@pytest.mark.parametrize("name", sorted(EXPECTED_ROUTES))
def test_a_covered_tier_never_renders_as_partial(name):
    """The specific misreading this format exists to prevent.

    No fraction anywhere in the narrative may be denominated in the union of the
    two sets, because there is no question whose answer is fourteen quantities.
    And a design that routes tier 1 must show tier 1 fully covered: those two
    statements appear two lines apart, and a reader who sees them disagree
    concludes the routing is broken rather than that the denominator was.
    """
    protocol, resolver = _case(name)
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    (t1_covered, t1_needed), (_, t0_needed) = _coverage(result)
    union = t1_needed + t0_needed
    assert not re.search(rf"\b\d+/{union}\b", result.render()), (
        f"{name} still reports a fraction of the union, which is the reading "
        f"that made a covered set look partial"
    )
    if result.decision.route is Route.TIER1:
        assert t1_covered == t1_needed, (
            f"{name} routed tier 1 while reporting tier-1 coverage as "
            f"{t1_covered}/{t1_needed}"
        )


def test_coverage_is_counted_the_way_the_gate_counts_it():
    """Covered is not the same as carrying a number, and the line says covered.

    `context_dependent` resolves nine of ten tier-1 keys to a value; the tenth is
    ill-posed as a scalar, has no value, and does not block - it is swept. The
    gate calls that set complete and builds the twin. A resolve line that counted
    values would print 9/10 directly above a gate line saying every tier-1
    constant resolved, which is the original bug in a smaller font.
    """
    protocol, resolver = _case("context_dependent")
    result = run(EXPERT, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    (t1_covered, t1_needed), _ = _coverage(result)
    assert result.decision.route is Route.TIER1
    assert t1_covered == t1_needed
    # And the reader is told why the count is not a count of numbers.
    assert "ill-posed as a scalar" in _text(result)


def test_a_covered_tier_1_that_still_refuses_says_which_condition_it_failed():
    """The one refusal that reads as a contradiction unless it is explained.

    `over_assumed` covers every tier-1 constant and is refused anyway, because
    seven of the ten are stand-ins. Printed per tier that shows up as "tier-1
    10/10 covered" two lines above a refusal, and the gate's own `why` names
    only the tier-0 gaps - so nothing on the page says coverage was necessary
    rather than sufficient. Without this line the honest reading available to a
    viewer is that the router is broken.
    """
    protocol, resolver = _case("over_assumed")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    (t1_covered, t1_needed), _ = _coverage(result)
    assert result.decision.route is Route.REFUSE
    assert t1_covered == t1_needed
    assert "stand-ins rather than anybody's measurement" in _text(result)


def test_an_ordinary_refusal_does_not_claim_an_over_assumed_twin():
    """The complement, or the line above could be unconditional and still pass.

    `all_blocked` covers nothing, so there is no covered-but-unusable tier-1 set
    to explain. Saying there was would invent a reason for the refusal that the
    resolution set does not support - the opposite failure, and the harder one
    to notice, because the sentence is reassuring.
    """
    protocol, resolver = _case("all_blocked")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    assert result.decision.route is Route.REFUSE
    assert "stand-ins rather than anybody's measurement" not in _text(result)


def test_a_tier_with_nothing_in_it_reports_zero_rather_than_vanishing():
    """A refusal must show both sets empty, not omit the set it could not use.

    The REFUSE path names the tier-0 gaps in its own words further down. The
    resolve line still has to carry the counts, because a line that printed only
    the tier that had something in it would make the refusal look like a failure
    to search rather than a search that came back empty.
    """
    protocol, resolver = _case("all_blocked")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    (t1_covered, t1_needed), (t0_covered, t0_needed) = _coverage(result)
    assert result.decision.route is Route.REFUSE
    assert (t1_covered, t0_covered) == (0, 0)
    assert t1_needed and t0_needed


def test_not_ready_names_the_unsearched_key_on_the_tier_that_owns_it():
    """The unfinished search has to be attributable, or NOT_READY reads as a gap.

    `one_unsearched` covers tier 0 completely and would route to the fallback on
    coverage alone. It must not, and the resolve line has to show why: the
    shortfall is in tier 1 and it is one key nobody has looked for, which is a
    different statement from one key nobody could find.
    """
    protocol, resolver = _case("one_unsearched")
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    (t1_covered, t1_needed), (t0_covered, t0_needed) = _coverage(result)
    assert result.decision.route is Route.NOT_READY
    assert t1_covered == t1_needed - 1
    assert t0_covered == t0_needed
    assert "not yet searched" in _text(result)
    assert NOT_ANSWERABLE not in _text(result)


# --- the fixtures, as a set -------------------------------------------------


@pytest.mark.parametrize("name", sorted(EXPECTED_ROUTES))
def test_every_fixture_round_trips_to_the_route_it_was_written_for(name):
    """The guard on the fixtures themselves, which are edited more than the code.

    Each file exists to exercise one route. Adding a key to one of them - which
    is exactly what making them total over both requirement sets required - can
    silently move it onto another route, and the two that would move first are
    the two the demo rests on: `full_coverage` must reach the twin and
    `all_blocked` must refuse. Nothing else in the suite asserts all seven at
    once, so nothing else would notice two of them collapsing onto one case.
    """
    protocol, resolver = _case(name)
    result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=ROUTE_ONLY_SIMS)

    assert result.decision.route is EXPECTED_ROUTES[name]
    # Every route, including the stops, opens with the same two stages. A
    # narrative that skips one of them has routed without saying on what.
    assert result.narrative[0].startswith("resolve: ")
    assert any(line.startswith("gate: ") for line in result.narrative)


@pytest.mark.parametrize("name", sorted(EXPECTED_ROUTES))
def test_every_fixture_answers_both_requirement_sets(name):
    """Totality over the union, which is what makes the two counts comparable.

    A fixture silent on tier 0 is not answering a smaller question - the
    pipeline counts an absent key as missing, so it reports as a set that failed
    to resolve rather than one that was never asked. Blocked and absent route
    the same way today and read completely differently, and the reading is what
    this module is for.
    """
    protocol, resolver = _case(name)
    resolutions = resolver.resolve(protocol.key, ())
    required = {r.key for r in tier1_needs(protocol)} | {
        r.key for r in tier0_needs()
    }
    assert required <= set(resolutions.resolutions), (
        f"{name} is silent on {sorted(required - set(resolutions.resolutions))}"
    )


# --- the CLI ----------------------------------------------------------------


def test_cli_route_runs_end_to_end(tmp_path, capsys):
    """Exit 0 for a stop as well as for a score.

    A route is the pipeline's product, including when the route is a refusal.
    Exiting non-zero on a refusal would mark the system's most considered
    outputs as malfunctions in anything that wrapped the command.
    """
    fixture = FIXTURES / "all_blocked.json"
    if not fixture.exists():
        # Enough to exercise the whole command without depending on a fixture
        # that has not landed. An empty resolution set is complete (nothing is
        # unsearched) and covers nothing, which is a legitimate refusal.
        fixture = tmp_path / "empty.json"
        fixture.write_text(
            json.dumps(
                {
                    "assay_key": "fibrin_contracture",
                    "requirement_version": "hand-written",
                    "resolutions": {},
                }
            )
        )

    code = main(["route", "--fixture", str(fixture), "--sims", str(SIMS)])
    out = capsys.readouterr().out

    assert code == 0
    assert "ROUTE:" in out
    assert "why" in out
    assert "resolve:" in out and "gate:" in out


def test_cli_route_reports_an_unusable_fixture_rather_than_crashing(tmp_path, capsys):
    """A fixture written for another assay must be a message, not a traceback."""
    fixture = tmp_path / "wrong_assay.json"
    fixture.write_text(
        json.dumps(
            {
                "assay_key": "some_other_assay",
                "requirement_version": "hand-written",
                "resolutions": {},
            }
        )
    )

    code = main(["route", "--fixture", str(fixture), "--sims", str(SIMS)])

    assert code == 2
    assert "FIXTURE NOT USABLE" in capsys.readouterr().out
