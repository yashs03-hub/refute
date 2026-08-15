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
"""

from __future__ import annotations

import json
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
from refute.resolve import FixtureResolver  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "cases" / "fixtures"

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
