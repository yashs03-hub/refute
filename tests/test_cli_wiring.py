"""The commands that reach the modules that had no way to be reached.

`adapt`, `intake` and `vocabulary` all landed with tests of their own and no
entry point, which is a specific kind of half-finished: a module nobody can run
is a module whose behaviour is only ever asserted by the person who wrote it.
This file pins the wiring itself - that each command parses, runs, and says
something - rather than re-testing what those modules do.

THE EXIT CODES ARE THE POINT
----------------------------
Three of the outcomes here are refusals: NOT_READY from a resolve loop that is
not finished, REFUSE from one that is finished and short, and none-of-these from
an assay registry that has no protocol for the question. Every one of them is
the product working. `cmd_route` says why in its docstring and `test_pipeline`
already pins it for `--fixture`; the same discipline has to hold for the paths
added here, because the pressure to exit non-zero on a refusal comes back every
time somebody wraps the command in a shell script.

So: a stop exits 0, and only a broken invocation - an unknown assay, `--recorded`
with nothing to say which assay, both sources at once - exits non-zero.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from refute.cli import main

FIXTURE = str(
    Path(__file__).resolve().parent.parent / "cases" / "fixtures" / "all_blocked.json"
)

# The recorded literature pass covers three assays; this is the one the brief
# names, and the one whose recovered constants are effect sizes while its
# blocked ones are failure rates - the asymmetry the project is about.
RECORDED_ASSAY = "scar_in_a_jar"

SIMS = 30


# --- refute route --recorded -------------------------------------------------


def test_route_recorded_runs_the_whole_downstream_path(capsys):
    """Real recorded findings, not a hand-written description of them.

    The distinction `adapt.RecordedResolver` exists for: a fixture states what a
    resolver's output should look like, so a pipeline tested only on fixtures
    has never met a real recovery rate.
    """
    code = main(["route", "--recorded", "--assay", RECORDED_ASSAY, "--sims", str(SIMS)])
    out = capsys.readouterr().out

    assert code == 0
    assert "ROUTE:" in out
    assert "resolver recorded" in out
    assert RECORDED_ASSAY in out
    assert "resolve:" in out and "gate:" in out


def test_a_stop_on_the_recorded_path_still_exits_zero(capsys):
    """The recorded pass has not searched tier 0, so this stops - at exit 0.

    NOT_READY is the pipeline reporting that the requirement set is unfinished,
    which is a fact about the search and not about the design. A non-zero exit
    would mark it as a malfunction in anything that wrapped the command, and the
    wording of that stop is written specifically to avoid being read as a
    verdict.
    """
    code = main(["route", "--recorded", "--assay", RECORDED_ASSAY, "--sims", str(SIMS)])
    out = capsys.readouterr().out

    assert code == 0
    assert "not_ready" in out
    assert "NOT a verdict" in out


def test_route_refuses_both_sources_at_once():
    """--fixture and --recorded are two different claims about provenance.

    Accepting both would mean the header says one thing and the numbers came
    from the other, which is the invented-provenance failure in miniature.
    argparse exits rather than returning, so the SystemExit is the assertion.
    """
    with pytest.raises(SystemExit) as exit_info:
        main(["route", "--fixture", FIXTURE, "--recorded"])

    assert exit_info.value.code == 2


def test_route_requires_a_source():
    """Neither source named is still a broken invocation, not a default."""
    with pytest.raises(SystemExit) as exit_info:
        main(["route"])

    assert exit_info.value.code == 2


def test_recorded_without_an_assay_says_so_rather_than_guessing(capsys):
    """A silent default would replay a different assay's findings.

    Unlike a fixture, which declares the assay it answers and is refused against
    any other, every assay key resolves to something on the recorded path - an
    unattempted one resolves to all-NOT_YET_SEARCHED. So a wrong default here
    produces a route rather than a stop, and the route is about the wrong assay.
    """
    code = main(["route", "--recorded"])
    out = capsys.readouterr().out

    assert code == 2
    assert "--assay" in out
    assert "refute assays" in out


def test_recorded_with_an_unknown_assay_names_the_known_ones(capsys):
    """An unknown key is a typo, and a typo should print the alternatives."""
    code = main(["route", "--recorded", "--assay", "no_such_assay"])
    out = capsys.readouterr().out

    assert code == 2
    assert "UNKNOWN" in out
    assert "no_such_assay" in out
    assert "fibrin_contracture" in out  # the list of keys that do exist


def test_the_fixture_path_still_defaults_its_assay(capsys):
    """Regression: adding --recorded must not make --assay mandatory.

    `--assay` lost its argparse default so that "not supplied" is distinguishable
    on the recorded path. The fixture path keeps the old behaviour, and this is
    the test that says so.
    """
    code = main(["route", "--fixture", FIXTURE, "--sims", str(SIMS)])
    out = capsys.readouterr().out

    assert code == 0
    assert "assay    fibrin_contracture" in out
    assert "resolver fixture" in out


# --- refute intake -----------------------------------------------------------


def test_intake_ranks_the_candidates_with_their_scores(capsys):
    """The selection is deterministic, so the ranking is the whole output.

    A selector you cannot argue with is a selector you have to trust. Printing
    the score and the matched terms is what makes a wrong answer a line of a
    table rather than a mood.
    """
    code = main(
        [
            "intake",
            "whether fibroblast-mediated contraction of the fibrin gel survives "
            "to the 168 h endpoint",
        ]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert "SELECTED: fibrin_contracture" in out
    assert "ranked candidates:" in out
    assert "below the floor" in out  # the near misses, recorded not dropped


def test_intake_says_plainly_that_no_extractor_is_configured(capsys):
    """No default provider, and the command reports that instead of guessing.

    `intake.extract_design` refuses to invent a design, because a guessed design
    scored by the twin is a confident number about a plate nobody proposed. The
    note is printed verbatim: it is worded to make no claim about the
    experiment, and paraphrasing it is how that guarantee gets lost.
    """
    code = main(["intake", "whether the fibrin gel lyses before the endpoint"])
    out = capsys.readouterr().out

    assert code == 0
    assert "extraction: no_extractor" in out
    assert "No extractor is configured" in out
    assert "ready for the gate: no" in out


def test_none_of_these_is_reported_with_its_near_misses_and_exits_zero(capsys):
    """A registry that cannot model the question is a limit, not a failure.

    Exit 0 for the same reason the refusals do. A selector under pressure to
    return a key will map a question about animals onto whatever assay is
    closest, and everything downstream is then confidently about the wrong
    apparatus - so the empty outcome has to be as cheap to emit as any other.
    """
    code = main(["intake", "does the animal survive dosing"])
    out = capsys.readouterr().out

    assert code == 0
    assert "SELECTED: none of these" in out
    assert "below the floor" in out
    assert "bleomycin_lung" in out  # the near miss, named rather than silently dropped


# --- refute vocabulary -------------------------------------------------------


def test_vocabulary_prints_the_report_raw(capsys):
    """No banner. The report is a document, and a banner would travel with it.

    It is written to be pasted into the conversation with layer 1, wraps itself
    to a fixed width and heads its own sections. Anything this command added
    would read as part of the artifact.
    """
    code = main(["vocabulary"])
    out = capsys.readouterr().out

    assert code == 0
    assert out.startswith("REFUTE - LAYER 2 VOCABULARY (NOT AGREED)")
    assert "WHAT THIS SIDE CANNOT DECLARE" in out
    assert "BOUND FROM LAYER 1" in out


# --- the help ----------------------------------------------------------------


def test_help_lists_every_new_command(capsys):
    """A command absent from --help is a command nobody will find."""
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    out = capsys.readouterr().out

    assert exit_info.value.code == 0
    for command in ("route", "intake", "vocabulary"):
        assert f"    {command} " in out or f"    {command}\n" in out


def test_route_help_documents_both_sources(capsys):
    with pytest.raises(SystemExit):
        main(["route", "--help"])
    out = capsys.readouterr().out

    assert "--fixture" in out
    assert "--recorded" in out
    assert "--assay" in out


# --- the package surface -----------------------------------------------------


def test_the_package_exports_what_a_caller_would_reach_for():
    """One import, and the layers above the twin are all reachable."""
    import refute

    for name in (
        "run_pipeline",       # the pipeline entry point
        "PipelineResult",
        "Route",              # the routes
        "RouteDecision",
        "FixtureResolver",    # the resolver types
        "RecordedResolver",
        "Resolver",
        "Resolution",
        "ResolutionSet",
        "Requirement",
        "Handoff",            # the handoff types
        "Finding",
        "OpenItem",
        "GapReason",
        "intake",
        "Intake",
    ):
        assert name in refute.__all__, f"{name} is not exported"
        assert hasattr(refute, name), f"{name} is in __all__ but not bound"


def test_the_pipeline_entry_point_is_not_exported_as_bare_run():
    """`refute run` on the command line is the agent loop, not this.

    Two different things called `run` in one project is a trap worth one rename.
    """
    import refute

    from refute.pipeline import run

    assert refute.run_pipeline is run
    assert not hasattr(refute, "run")


def test_a_module_that_has_not_landed_is_skipped(monkeypatch):
    """These layers land one at a time, so importing `refute` must not need all
    of them. A missing module costs its names, not the package."""
    import refute

    monkeypatch.setattr(refute, "__all__", list(refute.__all__))
    monkeypatch.setattr(
        refute, "_LAYERED", (("not_a_module_that_exists", ("Nothing",)),)
    )

    refute._export_layers()

    assert "Nothing" not in refute.__all__


def test_a_real_import_error_is_not_swallowed(monkeypatch):
    """The one that matters. A missing dependency inside `pipeline` raises the
    same exception type as a missing `pipeline`, and swallowing it would leave a
    package that imports cleanly and is quietly missing half its names."""
    import refute

    def explode(name, package=None):
        raise ModuleNotFoundError("No module named 'numpy'", name="numpy")

    monkeypatch.setattr(refute, "__all__", list(refute.__all__))
    monkeypatch.setattr(refute, "importlib", _stub_importlib(explode))

    with pytest.raises(ModuleNotFoundError, match="numpy"):
        refute._export_layers()


def _stub_importlib(import_module):
    """An `importlib` whose `import_module` is the one thing under test."""
    stub = type(importlib)("importlib_stub")
    stub.import_module = import_module
    return stub


# --- multi-assay twin CLI wiring ---------------------------------------------


def test_baseline_with_fibrin_default(capsys):
    code = main(["baseline", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "12-well design" in out
    assert "power" in out


def test_baseline_with_fibrin_explicit(capsys):
    code = main(["baseline", "--assay", "fibrin_contracture", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "12-well design" in out


def test_baseline_with_bleomycin_assay(capsys):
    code = main(["baseline", "--assay", "bleomycin_lung", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "20-animal design" in out
    assert "power to recover injected MSC effect" in out


def test_baseline_with_custom_design_files(tmp_path, capsys):
    from refute.bleomycin_design import DEFAULT_BLEOMYCIN_DESIGN
    from refute.design import EXPERIMENT_4_AS_RUN

    fibrin_path = tmp_path / "fibrin.json"
    fibrin_path.write_text(EXPERIMENT_4_AS_RUN.model_dump_json())
    code = main(["baseline", "--design", str(fibrin_path), "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "12-well design" in out

    bleo_path = tmp_path / "bleo.json"
    bleo_path.write_text(DEFAULT_BLEOMYCIN_DESIGN.model_dump_json())
    code = main([
        "baseline", "--assay", "bleomycin_lung",
        "--design", str(bleo_path), "--sims", str(SIMS)
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "20-animal design" in out


def test_optimize_fibrin(capsys):
    code = main([
        "optimize", "--assay", "fibrin_contracture", "--antifibrinolytic",
        "--power", "0.01", "--testable", "0.01", "--allow-assumption-sensitive",
        "--sims", str(SIMS)
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "OPTIMIZE" in out


def test_optimize_bleomycin_requires_msc_route(capsys):
    code = main(["optimize", "--assay", "bleomycin_lung", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 2
    assert "ROUTE REQUIRED" in out


def test_optimize_bleomycin_with_route(capsys):
    code = main([
        "optimize", "--assay", "bleomycin_lung", "--msc-route", "IT",
        "--power", "0.01", "--testable", "0.01", "--allow-assumption-sensitive",
        "--sims", str(SIMS)
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "WINNER" in out or "OPTIMIZE" in out


def test_advise_with_fibrin_assay(capsys):
    code = main(["advise", "--assay", "fibrin_contracture", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "ADVICE" in out


def test_advise_with_bleomycin_assay(capsys):
    code = main(["advise", "--assay", "bleomycin_lung", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "ADVICE" in out


def test_advise_with_custom_design_files(tmp_path, capsys):
    from refute.bleomycin_design import DEFAULT_BLEOMYCIN_DESIGN
    from refute.design import EXPERIMENT_4_AS_RUN

    fibrin_path = tmp_path / "fibrin.json"
    fibrin_path.write_text(EXPERIMENT_4_AS_RUN.model_dump_json())
    code = main(["advise", "--design", str(fibrin_path), "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "ADVICE" in out

    bleo_path = tmp_path / "bleo.json"
    bleo_path.write_text(DEFAULT_BLEOMYCIN_DESIGN.model_dump_json())
    code = main([
        "advise", "--assay", "bleomycin_lung",
        "--design", str(bleo_path), "--sims", str(SIMS)
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "ADVICE" in out


def test_chat_starts_with_default_assay(capsys, monkeypatch):
    """Regression: `cmd_chat` referenced `assay`/`twin` before either was
    ever assigned - a hard NameError on every invocation, caught only
    because `test_checkpoint4.py` tests `chat.Session` directly and never
    goes through this CLI entry point. Every other multi-assay command in
    this file got exactly this kind of smoke test; chat did not."""
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(EOFError))
    code = main(["chat", "--no-model", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "refute chat (fibrin_contracture)" in out


def test_chat_with_fibrin_assay(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt="": "quit")
    code = main(["chat", "--assay", "fibrin_contracture", "--no-model", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "refute chat (fibrin_contracture)" in out


def test_chat_with_bleomycin_assay(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt="": "quit")
    code = main(["chat", "--assay", "bleomycin_lung", "--no-model", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "refute chat (bleomycin_lung)" in out


def test_chat_with_design_file(tmp_path, monkeypatch, capsys):
    from refute.bleomycin_design import DEFAULT_BLEOMYCIN_DESIGN
    bleo_path = tmp_path / "bleo.json"
    bleo_path.write_text(DEFAULT_BLEOMYCIN_DESIGN.model_dump_json())

    monkeypatch.setattr("builtins.input", lambda _prompt="": "quit")
    code = main([
        "chat", "--assay", "bleomycin_lung", "--design", str(bleo_path),
        "--no-model", "--sims", str(SIMS)
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "refute chat (bleomycin_lung)" in out
    assert "computed from:" in out


def test_tier0_with_both_assays(capsys):
    code_fib = main([
        "tier0", "--assay", "fibrin_contracture", "--arms", "4", "--n", "3",
        "--capacity", "12", "--effect", "10", "--sd", "2"
    ])
    out_fib = capsys.readouterr().out
    assert code_fib == 0
    assert "TIER 0 - fibrin_contracture" in out_fib

    code_bleo = main([
        "tier0", "--assay", "bleomycin_lung", "--arms", "2", "--n", "10",
        "--capacity", "40", "--effect", "3", "--sd", "0.6", "--unit", "animal"
    ])
    out_bleo = capsys.readouterr().out
    assert code_bleo == 0
    assert "TIER 0 - bleomycin_lung" in out_bleo


def test_route_with_bleomycin_assay(capsys):
    code = main(["route", "--recorded", "--assay", "bleomycin_lung", "--sims", str(SIMS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "ROUTE:" in out
    assert "bleomycin_lung" in out


