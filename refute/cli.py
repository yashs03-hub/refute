"""Command line entry point.

    python -m refute.cli baseline          # score Experiment 4 as it was run
    python -m refute.cli sweep             # scan replicates x antifibrinolytic
    python -m refute.cli run               # full loop: propose -> simulate -> revise
    python -m refute.cli run --no-revise   # one pass only

`baseline` and `sweep` need no API key - they exercise the twin alone.
"""

from __future__ import annotations

import argparse
import json
import sys

from .design import EXPERIMENT_4_AS_RUN, DesignSpec, OutOfTwinScopeError
from .score import feedback_for_agent, score_design


def _print(title: str, body: str) -> None:
    print("=" * 68)
    print(title)
    print("=" * 68)
    print(body)
    print()


def _report_out_of_scope(exc: OutOfTwinScopeError) -> None:
    """Report a design the twin cannot speak to, as a twin limit not a verdict.

    Phrased carefully: the design is not being called bad. Saying "unscorable"
    where the truth is "unmodelled" would teach exactly the wrong lesson, and
    the whole point of raising here is to avoid a confident wrong number.
    """
    _print(
        "NOT SCORED - outside the twin",
        f"{exc}\n\n"
        "Nothing is wrong with the design. The twin models one apparatus, and\n"
        "this design leaves it. Scoring it anyway would report a number about a\n"
        "different experiment - the permissive failure a verifier must not make.",
    )


def cmd_baseline(args: argparse.Namespace) -> int:
    from .twins import DEFAULT_ASSAY, get_twin

    assay = getattr(args, "assay", DEFAULT_ASSAY)
    twin = get_twin(assay)

    design = twin.default_design
    if args.design:
        design = twin.design_spec_type.model_validate(json.loads(open(args.design).read()))
    try:
        score = twin.score_fn(design, n_sims=args.sims)
    except (OutOfTwinScopeError, ValueError) as exc:
        if "outside this twin's scope" in str(exc) or isinstance(exc, OutOfTwinScopeError):
            _report_out_of_scope(exc)
            return 2
        raise

    if hasattr(design, "total_wells"):
        unit_str = f"{design.total_wells}-well design"
        ep_str = f"endpoint {design.endpoint_time_h:.0f} h"
    else:
        unit_str = f"{design.total_animals}-animal design"
        ep_str = f"endpoint day {design.endpoint_day:.0f}"

    _print(f"{unit_str}, {ep_str}", score.summary())
    return 0


def cmd_assays(args: argparse.Namespace) -> int:
    """List assay protocols and their calibration status."""
    from .assays import REGISTRY, get

    if args.key:
        p = get(args.key)
        body = [
            f"{p.name}",
            f"status : {p.status.value.upper()}   unit: {p.unit}",
            f"readout: {p.readout.name} ({p.readout.units}), "
            f"{p.readout.direction} with fibrosis",
            "",
            p.summary,
            "",
            "why it matters:",
            f"  {p.why_it_matters}",
            "",
            "failure mechanism:",
            f"  {p.hazard.mechanism}",
            f"  driven by: {p.hazard.driver}"
            + ("  <- the measured phenotype" if p.hazard.driver_is_the_measured_phenotype else ""),
        ]
        if p.hazard.mitigation:
            body.append(f"  mitigation: {p.hazard.mitigation}")
        missing = p.missing_constants()
        if missing:
            body += ["", f"missing constants ({len(missing)}):"]
            body += [f"  - {c.name} ({c.units})" for c in missing]
        if p.calibration_needs:
            body += ["", "to calibrate, obtain:"]
            body += [f"  - {n}" for n in p.calibration_needs]
        if p.paperclip_query:
            body += ["", "paperclip query:", f"  {p.paperclip_query}"]
        if p.notes:
            body += ["", "notes:", f"  {p.notes}"]
        _print(p.key, "\n".join(body))
        return 0

    width = max(len(p.unit) for p in REGISTRY.values()) + 2
    lines = [f"{'key':<22} {'status':<10} {'unit':<{width}} missing"]
    for p in REGISTRY.values():
        lines.append(
            f"{p.key:<22} {p.status.value:<10} {p.unit:<{width}} "
            f"{len(p.missing_constants())}"
        )
    lines += [
        "",
        "Only MEASURED protocols can be scored by `baseline`/`optimize`/`chat`/",
        "`advise` today - those tools model exactly one apparatus (the fibrin",
        "gel). A LITERATURE-tier protocol has real registry constants (no",
        "UncalibratedAssayError) but still has no simulator of its own; see",
        "that protocol's module docstring. Scaffolds raise UncalibratedAssayError",
        "by design: inventing constants would reintroduce exactly the problem",
        "this benchmark exists to avoid.",
        "",
        "Detail: refute assays --key scar_in_a_jar",
    ]
    _print("ASSAY PROTOCOLS", "\n".join(lines))
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    """A conversation about a design, where every claim is computed."""
    from .assays import REGISTRY
    from .chat import Session
    from .design import OutOfTwinScopeError
    from .twins import DEFAULT_ASSAY, get_twin

    assay = getattr(args, "assay", DEFAULT_ASSAY)
    twin = get_twin(assay)

    extractor = None
    if not args.no_model:
        from .agent import extract_design as default_extract

        extractor = default_extract

    session = Session(extractor=extractor, n_sims=args.sims, assay=assay)

    print("=" * 68)
    print(f"refute chat ({twin.key}) — describe your experiment; every answer is simulated")
    print("=" * 68)


    print(
        "\nDescribe the arms, replicates, when you treat, when you measure and\n"
        "the endpoint. Then ask: what should I change · what if I add aprotinin ·\n"
        "why · how many units do I need.   Ctrl-D to leave.\n"
    )

    if args.design:
        session.design = twin.design_spec_type.model_validate(json.loads(open(args.design).read()))
        try:
            session.score = twin.score_fn(session.design, n_sims=args.sims)
        except (OutOfTwinScopeError, ValueError) as exc:
            if "outside this twin's scope" in str(exc) or isinstance(exc, OutOfTwinScopeError):
                _report_out_of_scope(exc)
                return 2
            raise
        print(session._verdict_sentence(session.score))
        print("\n  computed from:")
        from .chat import _cite

        for line in _cite(session.score, args.sims, capacity=twin.default_capacity):
            print(f"    {line}")
        print()

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            continue
        if text in ("exit", "quit"):
            return 0
        turn = session.ask(text)
        print()
        print(turn.render())
        print()



def cmd_infer(args: argparse.Namespace) -> int:
    """Constants papers report without meaning to.

    With --key, runs the search and then greps the result set for the SHAPE of
    each unstated constant. That is the trick: you cannot search for a number
    nobody wrote, but you can search for the pattern it hides in.
    """
    import subprocess

    from .assays import REGISTRY
    from .assays.inference import RULES, patterns_for, summary
    from .assays.sources import PaperclipSource

    if not args.key:
        _print("INFERENCE RULES", summary())
        return 0

    protocol = REGISTRY.get(args.key)
    if protocol is None:
        _print("UNKNOWN", f"no protocol '{args.key}'. Try `refute assays`.")
        return 2

    src = PaperclipSource()
    if reason := src.why_unavailable():
        _print("UNAVAILABLE", reason)
        return 2

    query = protocol.paperclip_query or protocol.name
    proc = subprocess.run(
        src.command(query, limit=args.limit), capture_output=True, text=True, timeout=300
    )
    if proc.returncode != 0:
        _print("SEARCH FAILED", proc.stderr.strip()[:400])
        return 2
    rid = src.result_id(proc.stdout)
    if rid is None:
        _print("SEARCH FAILED", "no result id in the output - contract changed")
        return 2

    lines = [f"protocol : {args.key}", f"query    : {query}", f"papers   : {rid}", ""]
    for rule in RULES:
        if args.rule and rule.key != args.rule:
            continue
        lines.append(f"── {rule.key} → {rule.recovers}")
        hit_any = False
        for pattern in patterns_for(rule.key):
            g = subprocess.run(
                src.grep_command(pattern, from_id=rid, context=args.context),
                capture_output=True, text=True, timeout=300,
            )
            body = g.stdout.strip()
            if g.returncode == 0 and body and "No matches" not in body:
                hit_any = True
                for ln in body.splitlines()[1 : args.show + 1]:
                    lines.append(f"    {ln.strip()[:150]}")
        if not hit_any:
            lines.append("    (nothing matched - the shape is absent from these papers)")
        lines.append("")

    lines.append(
        "These are CANDIDATES, not constants. Each match is a place a number may\n"
        "be recoverable by arithmetic - somebody still has to read the paper and\n"
        "confirm the reading. `refute infer` with no --key explains each rule and\n"
        "what would make it wrong."
    )
    _print("INFERENCE", "\n".join(lines))
    return 0


def cmd_advise(args: argparse.Namespace) -> int:
    """What to change, with what each change would actually do."""
    from .twins import DEFAULT_ASSAY, get_twin

    assay = getattr(args, "assay", DEFAULT_ASSAY)
    twin = get_twin(assay)

    design = twin.default_design
    if args.design:
        design = twin.design_spec_type.model_validate(json.loads(open(args.design).read()))

    try:
        result = twin.advise_fn(design, n_sims=args.sims)
    except (OutOfTwinScopeError, ValueError) as exc:
        if "outside this twin's scope" in str(exc) or isinstance(exc, OutOfTwinScopeError):
            _report_out_of_scope(exc)
            return 2
        raise

    _print("ADVICE", result.summary())

    if args.all:
        rest = [s for s in result.suggestions if not s.helps]
        if rest:
            _print(
                "CHANGES THAT DID NOT HELP",
                "\n\n".join(s.line() for s in rest)
                + "\n\nReported because a change that does nothing is worth "
                "knowing about\nbefore you spend capacity on it.",
            )
    return 0


ROUTE_DEFAULT_ASSAY = "fibrin_contracture"
"""The assay `route --fixture` falls back to when none is named.

A default is safe for a fixture because the fixture declares the assay it
answers and `FixtureResolver` refuses a mismatch, so a wrong default stops the
command rather than answering the wrong question. `--recorded` has no such
check - see `cmd_route`.
"""


def cmd_route(args: argparse.Namespace) -> int:
    """Walk a resolution set through the whole downstream pipeline.

    Two sources of resolutions, and the difference is the point. `--fixture`
    replays a hand-written statement of what a resolver's output should look
    like; `--recorded` replays what the literature pass on 2026-08-04 actually
    found, via `adapt.RecordedResolver`, which is the only way the downstream
    half gets exercised on real recovery rates rather than on a description of
    them. Both are offline and deterministic.

    Exits 0 for every route, including the refusals. A stop is an outcome here,
    not an error: "the requirement set is unfinished" and "the twin cannot model
    this" are things the pipeline is FOR, and a non-zero exit would mark them as
    malfunctions in any script that wrapped this. Only a broken invocation - an
    unreadable fixture, an unknown assay, `--recorded` with no assay named - is
    a failure.
    """
    from .assays import get
    from .design import EXPERIMENT_4_AS_RUN
    from .pipeline import run

    if args.recorded and not args.assay:
        # No default here, unlike the fixture path. A fixture names the assay it
        # answers and is refused against any other, so a wrong default cannot
        # produce an answer; the recorded reports are keyed by assay and every
        # key resolves to something, so a silent default would quietly replay a
        # different assay's findings and route on them without complaint.
        _print(
            "ASSAY REQUIRED",
            "--recorded replays the findings recorded for one assay, and there "
            "is nothing\nin the request that says which. Name it:\n\n"
            "  refute route --recorded --assay scar_in_a_jar\n\n"
            "`refute assays` lists the keys.",
        )
        return 2

    try:
        protocol = get(args.assay or ROUTE_DEFAULT_ASSAY)
    except KeyError as exc:
        _print("UNKNOWN", str(exc))
        return 2

    if args.recorded:
        from .adapt import RecordedResolver

        resolver = RecordedResolver()
        origin = "recorded literature pass (assays/literature.py)"
    else:
        from .resolve import FixtureResolver

        resolver = FixtureResolver(args.fixture)
        origin = args.fixture

    try:
        result = run(EXPERIMENT_4_AS_RUN, protocol, resolver, n_sims=args.sims)
    except (OSError, ValueError) as exc:
        # A fixture that will not load, or one written for a different assay; or
        # a recorded report the adapter refuses to convert. Loud, because a
        # silent fallback here would report a route computed from something
        # other than the source the user named.
        _print(
            "RECORD NOT USABLE" if args.recorded else "FIXTURE NOT USABLE",
            f"{type(exc).__name__}: {exc}",
        )
        return 2

    _print(
        f"ROUTE: {result.decision.route.value}",
        f"design   Experiment 4 as run ({EXPERIMENT_4_AS_RUN.total_wells} wells, "
        f"endpoint {EXPERIMENT_4_AS_RUN.endpoint_time_h:.0f} h)\n"
        f"assay    {protocol.key}\n"
        f"resolver {resolver.name}\n"
        f"source   {origin}\n"
        f"why      {result.decision.why}\n\n"
        + result.render(),
    )
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    """Residual prose in, an assay and a design out - or an honest account of why not.

    Exits 0 for none-of-these. A registry with no protocol for this residual is
    a limit of the registry, reported as one; treating it as a failed run would
    make the honest outcome look like a broken tool, which is the pressure that
    produces a selector that always returns a key.

    Exits 0 with no extractor configured too. `intake` makes exactly one model
    call and there is no default provider, deliberately - see `intake.py`. The
    deterministic half, which is the assay selection, still ran and is still
    the answer to the question the command was asked.
    """
    from .intake import Extraction, intake

    result = intake(args.residual)
    selection = result.selection

    lines = [f"residual  {result.residual}", ""]
    lines += list(result.narrative)
    lines.append("")

    if selection.none_of_these:
        lines.append("SELECTED: none of these")
    else:
        best = selection.best
        lines.append(f"SELECTED: {best.key}  ({best.score:.1f})")
        lines.append(f"  {best.why}")
        if not selection.decisive:
            lines.append(
                "  The leader is not clear of the field. Acting on it alone "
                "discards a live\n  alternative, so read the ranking rather "
                "than the first line."
            )
        lines += ["", "ranked candidates:"]
        for i, c in enumerate(selection.candidates, 1):
            lines.append(f"  {i}. {c.key:<22} {c.score:>5.1f}  {', '.join(c.terms)}")

    if selection.near_misses:
        lines += ["", "below the floor, recorded so the miss is readable:"]
        for c in selection.near_misses:
            lines.append(f"   - {c.key:<22} {c.score:>5.1f}  {', '.join(c.terms)}")
    lines += ["", f"considered: {', '.join(selection.considered)}"]

    lines += ["", f"extraction: {result.extraction.value}"]
    if result.extraction is Extraction.EXTRACTED:
        lines.append(result.design.model_dump_json(indent=2))
    else:
        # Printed verbatim. Both notes are written to make no claim about the
        # experiment, and paraphrasing one here is how that guarantee gets lost.
        lines.append(f"  {result.note}")
    lines += ["", f"ready for the gate: {'yes' if result.ready else 'no'}"]

    _print("INTAKE", "\n".join(lines))
    return 0


def cmd_vocabulary(args: argparse.Namespace) -> int:
    """Print the layer-2 vocabulary coverage report, unwrapped and unheaded.

    Deliberately not run through `_print`. The report is an artifact to be
    pasted into the conversation with layer 1, it wraps and indents itself to a
    fixed width, and a banner this command added would travel with it and read
    as part of the document.
    """
    from .vocabulary import coverage_report

    print(coverage_report())
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Query a live corpus. The one path that actually hits the network.

    Separate from `calibrate` on purpose: calibrate reports what has been
    recorded, this produces new evidence. Conflating them is how a replayed
    result gets presented as a fresh one.
    """
    from .assays import REGISTRY
    from .assays.sources import PaperclipSource

    src = PaperclipSource()
    if reason := src.why_unavailable():
        _print("UNAVAILABLE", reason)
        return 2

    if args.key:
        protocol = REGISTRY.get(args.key)
        if protocol is None:
            _print("UNKNOWN", f"no protocol '{args.key}'. Try `refute assays`.")
            return 2
        query = protocol.paperclip_query or protocol.name
        header = f"{args.key}: {query}"
    else:
        query = args.query
        header = query

    try:
        hits = src.search(query, limit=args.limit)
    except (RuntimeError, ValueError) as exc:
        # A contract break must be loud. Reporting zero hits here would read as
        # "the literature is silent", which is the project's headline claim.
        _print("SEARCH FAILED", f"{type(exc).__name__}: {exc}")
        return 2

    lines = [f"query : {header}", f"hits  : {len(hits)}", ""]
    for h in hits:
        lines.append(f"  {h.source}")
        if h.title:
            lines.append(f"    {h.title[:88]}")
        if h.snippet:
            lines.append(f"    \"{h.snippet[:150]}\"")
        lines.append("")
    lines.append(
        "Hits are papers, NOT constants. A paper on the right topic is not\n"
        "evidence a constant is reported in it - that still needs reading the\n"
        "methods section. Use `paperclip grep --from <id>` for the sentence."
    )
    _print("SEARCH", "\n".join(lines))
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Report what literature calibration recovered, and what it did not.

    The split is computed from the protocol's own structure rather than a
    hand-kept list: readout constants are what the assay measures, hazard and
    attrition constants are how it breaks. If the second column stays empty as
    the corpus grows, that is the result.
    """
    from .assays import REGISTRY
    from .assays.evidence import BlockedReason
    from .assays.literature import NOT_ATTEMPTED, REPORTS
    from .assays.sources import get_source

    src = get_source(args.source)

    # The numbers below come from REPORTS in literature.py - the recorded
    # PubMed attempt - whatever --source says. Selecting a live source does NOT
    # currently regenerate them: nothing here calls src.search().
    #
    # Labelling them with the requested source would attribute a PubMed result
    # to a corpus that never produced it, which is the invented-provenance
    # failure this project exists to criticise. So the header states where the
    # findings actually came from, and says plainly when the requested source
    # was not used.
    lines = ["findings from : recorded PubMed attempt (assays/literature.py)"]
    if src.name != "recorded":
        lines.append(f"requested source: {src.name}  -- NOT used to produce these")
        if reason := src.why_unavailable():
            lines.append(f"  unavailable: {reason}")
        else:
            lines.append(
                "  available, but `calibrate` replays recorded findings; it does\n"
                "  not yet re-run queries. Use `refute search` for live evidence."
            )
    lines.append("")

    if args.key:
        report = REPORTS.get(args.key)
        if report is None:
            lines.append(f"no calibration attempted for '{args.key}'")
        else:
            lines.append(report.summary())
        _print(f"CALIBRATION: {args.key}", "\n".join(lines))
        return 0

    readout_found = readout_total = fail_found = fail_total = 0
    reasons: dict[BlockedReason, int] = {}

    lines.append(f"{'protocol':<22} {'measured':>9} {'failure':>9}  status")
    for p in REGISTRY.values():
        if p.status.value == "measured":
            continue
        readout_names = {c.name for c in p.readout.constants}
        report = REPORTS.get(p.key)
        if report is None:
            lines.append(f"{p.key:<22} {'-':>9} {'-':>9}  not attempted")
            continue
        found = {e.constant for e in report.found}
        r_tot = f_tot = r_hit = f_hit = 0
        for c in p.all_constants():
            is_readout = c.name in readout_names
            hit = c.name in found
            if is_readout:
                r_tot += 1; r_hit += hit
            else:
                f_tot += 1; f_hit += hit
        for b in report.blocked:
            reasons[b.reason] = reasons.get(b.reason, 0) + 1
        readout_found += r_hit; readout_total += r_tot
        fail_found += f_hit; fail_total += f_tot
        lines.append(
            f"{p.key:<22} {f'{r_hit}/{r_tot}':>9} {f'{f_hit}/{f_tot}':>9}"
            f"  {report.recovery_rate:.0%} overall"
        )

    missing = [k for k in NOT_ATTEMPTED if k not in REGISTRY]
    for key in missing:  # listed in literature.py but absent from the registry
        lines.append(f"{key:<22} {'-':>9} {'-':>9}  not attempted (unregistered)")

    lines += ["", "THE ASYMMETRY"]
    lines.append(
        f"  what the assay measures : {readout_found}/{readout_total} recovered"
    )
    lines.append(
        f"  how the assay breaks    : {fail_found}/{fail_total} recovered"
    )
    lines += ["", "why the rest are blocked:"]
    for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {reason.value:<20} {n}")
    lines += [
        "",
        "NOT_YET_SEARCHED is not a claim. Only NOT_REPORTED asserts the",
        "literature is silent, and it is refused without a recorded query.",
    ]
    _print("CALIBRATION", "\n".join(lines))
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    """The two failures are separable - show that they must both be fixed."""
    rows = []
    for antifib in (False, True):
        for reps in (3, 6, 12, 30, 60):
            d = DesignSpec(
                conditions=["N-SS", "N-T", "N-CM", "N-CM+T"],
                replicates_per_condition=reps,
                imaging_times_h=[2, 6, 12, 24, 48, 120, 144, 168],
                treatment_time_h=120.0,
                endpoint_time_h=168.0,
                antifibrinolytic=antifib,
                normalise_to_own_baseline=True,
                locked_imaging_protocol=True,
            )
            s = score_design(d, n_sims=args.sims)
            rows.append((antifib, reps, s.power, s.testable_rate, s.mean_lysed_fraction))

    lines = [f"{'antifib':>8} {'n/arm':>6} {'power':>7} {'testable':>9} {'lysed':>7}"]
    for antifib, reps, power, testable, lysed in rows:
        lines.append(
            f"{str(antifib):>8} {reps:>6} {power:>6.0%} {testable:>9.0%} {lysed:>7.0%}"
        )
    lines.append("")
    lines.append(
        "The two defects are separable and neither fix alone is enough.\n"
        "Without an antifibrinolytic ~25% of wells are lost at every n, which "
        "caps power (52% even at n=60).\nAdding one clears the losses entirely "
        "but still leaves n=3 at ~2%: useful power needs n>=30.\n"
        "At the 12-well scale actually available, both together are still short."
    )
    _print("SWEEP: antifibrinolytic x replicates", "\n".join(lines))
    return 0


def cmd_baselines(args: argparse.Namespace) -> int:
    """Score the reference designs, so an agent's number has a scale."""
    from .baselines import BASELINES, CEILING, sanity_check

    sanity_check()
    CEILING_REPS = CEILING.replicates_per_condition

    rows = []
    for b in BASELINES:
        s = score_design(b.design, n_sims=args.sims)
        rows.append((b, s))

    header = (
        f"{'design':>8} {'wells':>6} {'power':>7} {'testable':>9} "
        f"{'lysed':>7} {'n/arm needed':>13} {'verdict':>12}"
    )
    lines = [header]
    for b, s in rows:
        lines.append(
            f"{b.key:>8} {b.design.total_wells:>6} {s.power:>6.0%} "
            f"{s.testable_rate:>9.0%} {s.mean_lysed_fraction:>7.0%} "
            f"{(s.replicates_needed if s.replicates_needed > 0 else '-'):>13} "
            f"{s.feasibility:>12}"
        )

    expert = next(s for b, s in rows if b.key == "expert")
    ceiling = next(s for b, s in rows if b.key == "ceiling")

    lines += ["", "what each one is for:"]
    lines += [f"  {b.key:<8} {b.question}" for b, _ in rows]

    # The point of the table, stated rather than left for the reader to infer.
    lines += ["", "reading:"]
    if expert.power < 0.8:
        lines.append(
            f"  EXPERT spends the whole plate, protects the scaffold and samples "
            f"the kinetics,\n  and still reaches only {expert.power:.0%} power. It "
            f"was written with hindsight the\n  agent is denied, so the ceiling on "
            f"one plate is a fact about the apparatus,\n  not a verdict on any "
            f"agent."
        )
    else:
        lines.append(
            f"  EXPERT reaches {expert.power:.0%} power on one plate, so the "
            "apparatus is sufficient\n  and a low agent score is the agent's."
        )
    lines.append(
        f"  CEILING is the same design at n={CEILING_REPS}, over capacity by "
        f"design: {ceiling.power:.0%} power.\n  The constraint is the plate, and "
        "that is what it costs. The twin has no\n  between-plate calibration, so "
        "read it as an optimistic bound."
    )
    lines.append(
        "\n  Compare any agent against EXPERT, not against AS_RUN. Beating a "
        "design that\n  scored zero is not evidence of anything."
    )

    _print("BASELINES", "\n".join(lines))
    return 0


def cmd_check_extraction(args: argparse.Namespace) -> int:
    """Validate the extractor against designs whose specs are known.

    Extraction sits directly upstream of every score, so a parsing failure is
    indistinguishable from a design failure after the fact. This is the only
    check that separates them, and it costs one cheap model call per case.
    """
    from .agent import extract_design
    from .extraction_cases import CASES, check
    from .providers import DEFAULT_EXTRACTOR, ledger_summary, spec_from_string

    extractor = (
        spec_from_string(args.extractor, "low") if args.extractor else DEFAULT_EXTRACTOR
    )
    print(f"extractor {extractor}\ncases     {len(CASES)}\n")

    results = []
    for case in CASES:
        try:
            spec = extract_design(case.prose, extractor=extractor)
        except Exception as exc:
            results.append((case, None, f"{type(exc).__name__}: {exc}"))
            print(f"  {case.key:<24} ERROR  {type(exc).__name__}")
            continue
        result = check(case, spec)
        results.append((case, result, None))
        print(f"  {case.key:<24} {'ok' if result.passed else 'FAIL':<6} "
              f"probes: {', '.join(case.probes)}")
        for m in result.mismatches:
            print(f"      - {m}")

    ok = sum(1 for _, r, e in results if e is None and r and r.passed)
    lines = [f"{ok}/{len(CASES)} cases extracted correctly", ""]
    if ok == len(CASES):
        lines.append(
            "Extraction is not the explanation for any score in this repo. State "
            "this\nalongside the headline number - it is the difference between a "
            "result and\na number that might be a parsing bug."
        )
    else:
        lines.append(
            "Extraction is NOT clean. Until these pass, any score could be a "
            "parsing\nfailure rather than a design failure, and the two are "
            "indistinguishable\nafter the fact. Fix the prompt or narrow the "
            "claim; do not quote the\nheadline number as though it were "
            "validated."
        )
    _print("EXTRACTION CHECK", "\n".join(lines))
    _print("TOKENS", ledger_summary())
    return 0 if ok == len(CASES) else 1


def cmd_replay(args: argparse.Namespace) -> int:
    """Re-score a recorded agent run. No credential, no network."""
    from .record import RecordedRun

    run = RecordedRun.load(args.path)
    header = (
        f"agent     {run.agent}\n"
        f"extractor {run.extractor}\n"
        f"recorded  {run.recorded_at or 'unknown'}\n"
        f"rounds    {len(run.rounds)}"
    )
    if run.notes:
        header += f"\nnotes     {run.notes}"
    _print("RECORDED RUN", header)

    scores = []
    for i, rnd in enumerate(run.rounds, start=1):
        try:
            score = score_design(rnd.extracted, n_sims=args.sims)
        except OutOfTwinScopeError as exc:
            _report_out_of_scope(exc)
            return 2
        scores.append(score)
        label = "PROPOSED" if i == 1 else f"REVISED (round {i})"
        if args.verbose:
            _print(f"{label} - DESIGN TEXT", rnd.design_text)
        _print(f"{label} - EXTRACTED", rnd.extracted.model_dump_json(indent=2))
        _print(f"{label} - SIMULATED", score.summary())

    recomputed = (
        "Scores are recomputed against the current twin, not read back from the "
        "file,\nso this reflects the calibration in force now."
    )

    if len(scores) >= 2:
        first, last = scores[0], scores[-1]
        if last.declined:
            # "2% -> 0%" would read as a regression. What happened is the agent
            # stopped and argued the question is unanswerable at this scale, which
            # is not on the same scale as a power figure.
            _print(
                "OUTCOME",
                "The final round DECLINED to run the experiment.\n\n"
                f"Round 1: {first.power:.0%} power, {first.testable_rate:.0%} "
                f"testable, ~{first.replicates_needed} wells per arm needed.\n"
                "Final:   no plate at this scale can resolve the effect.\n\n"
                "This is NOT a regression - the rounds are not comparable. Whether "
                "declining\nwas correct is answered by `refute baselines`.\n\n"
                + recomputed,
            )
        else:
            _print(
                "DELTA",
                f"power      {first.power:.0%} -> {last.power:.0%}\n"
                f"testable   {first.testable_rate:.0%} -> {last.testable_rate:.0%}\n"
                f"lysed      {first.mean_lysed_fraction:.0%} -> "
                f"{last.mean_lysed_fraction:.0%}\n"
                f"n/arm needed {first.replicates_needed} -> "
                f"{last.replicates_needed}\n\n" + recomputed,
            )
    return 0


def cmd_tier0(args: argparse.Namespace) -> int:
    """Power and scale for any assay, from the experimenter's own numbers."""
    from .tier0 import TIER_LADDER, Tier0Design, Tier0InputError, score_tier0

    if args.ladder:
        _print("TIERS", TIER_LADDER)
        return 0

    design = Tier0Design(
        assay=args.assay,
        n_arms=args.arms,
        replicates_per_arm=args.n,
        capacity=args.capacity,
        expected_effect=args.effect,
        variability_sd=args.sd,
        unit=args.unit,
        alpha=args.alpha,
        target_power=args.power,
    )
    try:
        score = score_tier0(design)
    except Tier0InputError as exc:
        # Fail closed, and say what to do about it. The tier-0 analogue of
        # UncalibratedAssayError: a power figure from a guessed variance looks
        # like a calculation and is not one.
        _print("CANNOT ASSESS", str(exc))
        return 2
    _print(f"TIER 0 - {design.assay}", score.summary())
    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    """The cheapest design that clears a power target - a human-facing search
    against the twin. See `optimize.py`'s docstring before wiring this into
    anything the agent under test can reach: it must never be."""
    from .calibration import PLATE_WELLS
    from .twins import DEFAULT_ASSAY, get_twin

    assay = getattr(args, "assay", DEFAULT_ASSAY)
    twin = get_twin(assay)

    if twin.optimize_fn is None:
        _print("CANNOT OPTIMIZE", f"No optimizer registered for assay '{assay}'")
        return 2

    if assay == "bleomycin_lung":

        if not args.msc_route:
            _print(
                "ROUTE REQUIRED",
                "--msc-route ('IT' or 'IV') must be explicitly specified for bleomycin_lung.\n"
                "The search never decides the route for you.",
            )
            return 2
        conditions = (
            tuple(args.conditions.split(","))
            if args.conditions
            else ("bleomycin_only", "bleomycin_MSC")
        )
        try:
            result = twin.optimize_fn(
                msc_route=args.msc_route,
                target_power=args.power,
                target_testable=args.testable,
                capacity=args.capacity if args.capacity != PLATE_WELLS else twin.default_capacity,
                conditions=conditions,
                endpoint_day=args.endpoint if args.endpoint != 168.0 else 21.0,
                allow_assumption_sensitive=args.allow_assumption_sensitive,
                n_sims=args.sims,
            )
        except ValueError as exc:
            _print("CANNOT OPTIMIZE", str(exc))
            return 2
    else:
        conditions = (
            tuple(args.conditions.split(","))
            if args.conditions
            else ("N-SS", "N-T", "N-CM", "N-CM+T")
        )
        result = twin.optimize_fn(
            antifibrinolytic=args.antifibrinolytic,
            target_power=args.power,
            target_testable=args.testable,
            capacity=args.capacity,
            conditions=conditions,
            endpoint_time_h=args.endpoint,
            allow_assumption_sensitive=args.allow_assumption_sensitive,
            n_sims=args.sims,
        )

    _print("OPTIMIZE", result.summary())
    return 0 if result.found else 2


def cmd_harnesses(args: argparse.Namespace) -> int:
    """The harness is a variable, not a constant. Say what each one is."""
    from .harness import describe

    _print("HARNESSES", describe())
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    # Imported lazily: `demo` imports this module back, to delegate to the same
    # cmd_* functions the CLI exposes so the two cannot drift apart.
    from .demo import cmd_demo

    return cmd_demo(args)


def cmd_providers(args: argparse.Namespace) -> int:
    """What can actually be called right now, and why not if it can't."""
    from .providers import DEFAULT_AGENT, DEFAULT_EXTRACTOR, available

    lines = [f"{name:<12} {status}" for name, status in available().items()]
    lines += [
        "",
        f"default agent     {DEFAULT_AGENT}   (the subject - vary this)",
        f"default extractor {DEFAULT_EXTRACTOR}   (infrastructure - hold constant)",
        "",
        "Vary the agent to compare models; keep the extractor fixed, or a",
        "difference in score cannot be attributed to design quality rather than",
        "to how accurately the prose was parsed.",
        "",
        "  refute run --agent openai:gpt-5.5 --agent-effort high",
        "  refute run --agent claude-opus-5",
    ]
    _print("PROVIDERS", "\n".join(lines))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone

    from .agent import EXPERIMENT_4_BRIEF, extract_design, propose_design, revise_design
    from .providers import DEFAULT_EXTRACTOR, ledger_summary, spec_from_string
    from .record import RecordedRound, RecordedRun

    from .harness import get_harness

    agent = spec_from_string(args.agent, args.agent_effort)
    extractor = (
        spec_from_string(args.extractor, "low") if args.extractor else DEFAULT_EXTRACTOR
    )
    try:
        harness = get_harness(args.harness, agent)
    except KeyError as exc:
        print(exc, file=sys.stderr)
        return 2

    # The pair is the unit of measurement, so both are printed and both are
    # recorded. A score attributed to a model alone cannot be interpreted.
    print(
        f"agent     {agent}\n"
        f"harness   {harness.name}  ({harness.adds})\n"
        f"extractor {extractor}  (held constant)\n"
    )

    # Recorded unconditionally. A paid run whose prose is not kept cannot be
    # re-scored after a calibration change, which is how the first live result's
    # headline number became unquotable rather than merely stale.
    record = RecordedRun(
        agent=str(agent),
        extractor=str(extractor),
        brief=EXPERIMENT_4_BRIEF,
        harness=harness.name,
        recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    def save_record() -> None:
        if not args.record:
            return
        path = record.save(args.record)
        print(f"[recorded {len(record.rounds)} round(s) -> {path}]\n")

    design_text = harness.propose(EXPERIMENT_4_BRIEF)
    _print("PROPOSED DESIGN", design_text)

    spec = extract_design(design_text, extractor=extractor)
    _print("EXTRACTED SPEC", spec.model_dump_json(indent=2))
    record.rounds.append(RecordedRound(design_text=design_text, extracted=spec))
    save_record()  # written before scoring, so a scorer crash cannot lose the run

    try:
        score = score_design(spec, n_sims=args.sims)
    except OutOfTwinScopeError as exc:
        # No revision turn: there is no consequence report to give, because the
        # simulator never ran. Inventing feedback here would be the model
        # judging the design, which is the thing this project exists to avoid.
        _report_out_of_scope(exc)
        _print("TOKENS", ledger_summary())
        return 2
    _print("SIMULATED", score.summary())

    if args.no_revise:
        _print("TOKENS", ledger_summary())
        return 0

    feedback = feedback_for_agent(score)
    record.rounds[-1].feedback_given = feedback
    revised_text = harness.revise(EXPERIMENT_4_BRIEF, design_text, feedback)
    _print("REVISED DESIGN", revised_text)

    revised_spec = extract_design(revised_text, extractor=extractor)
    _print("EXTRACTED SPEC (revised)", revised_spec.model_dump_json(indent=2))
    record.rounds.append(
        RecordedRound(design_text=revised_text, extracted=revised_spec)
    )
    save_record()

    try:
        revised_score = score_design(revised_spec, n_sims=args.sims)
    except OutOfTwinScopeError as exc:
        # A common and interesting case: told the scaffold dissolved, an agent
        # may reasonably switch matrix material. That is a good instinct and the
        # twin still cannot score it, so the first-round score stands alone.
        _report_out_of_scope(exc)
        _print("TOKENS", ledger_summary())
        return 2
    _print("SIMULATED (revised)", revised_score.summary())

    if revised_score.declined:
        # A delta table here would read as 2% -> 0%, i.e. the revision made
        # things worse, when what happened is that the agent stopped and argued
        # the question is unanswerable at this scale. Those are not comparable.
        _print(
            "OUTCOME",
            "The revision DECLINED to run the experiment rather than proposing a "
            "worse plate.\n\n"
            f"Round 1 scored {score.power:.0%} power, {score.testable_rate:.0%} "
            f"testable, needing ~{score.replicates_needed} wells per arm.\n"
            "Round 2 concluded no plate at this scale can resolve the effect.\n\n"
            "Do NOT read this as a regression - the two rounds are not on the same "
            "scale.\nWhether declining was correct is answered by `refute "
            "baselines`, which scores\nthe best design available on one plate.",
        )
        _print("TOKENS", ledger_summary())
        return 0

    _print(
        "DELTA",
        f"power      {score.power:.0%} -> {revised_score.power:.0%}\n"
        f"testable   {score.testable_rate:.0%} -> {revised_score.testable_rate:.0%}\n"
        f"lysed      {score.mean_lysed_fraction:.0%} -> "
        f"{revised_score.mean_lysed_fraction:.0%}",
    )
    _print("TOKENS", ledger_summary())
    return 0


def main(argv: list[str] | None = None) -> int:
    # Shared options, accepted either before or after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--sims", type=int, default=400, help="plates per design")

    parser = argparse.ArgumentParser(prog="refute", parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    p_base = sub.add_parser(
        "baseline", parents=[common], help="score a design (default: Experiment 4)"
    )
    p_base.add_argument("--design", help="path to a DesignSpec JSON file")
    p_base.add_argument(
        "--assay", default="fibrin_contracture", help="assay twin key (default: fibrin_contracture)"
    )
    p_base.set_defaults(func=cmd_baseline)

    sub.add_parser(
        "sweep", parents=[common], help="antifibrinolytic x replicates grid"
    ).set_defaults(func=cmd_sweep)

    sub.add_parser(
        "baselines",
        parents=[common],
        help="score the reference designs, so an agent's number has a scale",
    ).set_defaults(func=cmd_baselines)

    p_t0 = sub.add_parser(
        "tier0",
        parents=[common],
        help="power and scale for ANY assay, from your own effect size and SD",
    )
    p_t0.add_argument("--assay", default="unnamed assay")
    p_t0.add_argument("--arms", type=int, default=2, help="number of arms")
    p_t0.add_argument("--n", type=int, default=3, help="replicates per arm")
    p_t0.add_argument("--capacity", type=int, default=12, help="units available")
    p_t0.add_argument("--effect", type=float, help="difference you expect")
    p_t0.add_argument("--sd", type=float, help="within-arm SD of that measurement")
    p_t0.add_argument("--unit", default="well", help="well | animal | sample | field")
    p_t0.add_argument("--alpha", type=float, default=0.05)
    p_t0.add_argument("--power", type=float, default=0.80, help="target power")
    p_t0.add_argument(
        "--ladder", action="store_true", help="explain the tiers and stop"
    )
    p_t0.set_defaults(func=cmd_tier0)

    p_opt = sub.add_parser(
        "optimize",
        parents=[common],
        help="cheapest design that clears a power target (human-facing only)",
    )
    p_opt.add_argument(
        "--assay", default="fibrin_contracture", help="assay twin key (default: fibrin_contracture)"
    )
    p_opt.add_argument(
        "--antifibrinolytic", action="store_true",
        help="required for fibrin_contracture - search never decides this",
    )
    p_opt.add_argument(
        "--msc-route", choices=("IT", "IV"), default=None,
        help="required for bleomycin_lung ('IT' or 'IV') - search never decides this",
    )
    p_opt.add_argument("--power", type=float, default=0.80, help="target power")
    p_opt.add_argument("--testable", type=float, default=0.80, help="target testable rate")
    p_opt.add_argument("--capacity", type=int, default=12, help="wells/units available")
    p_opt.add_argument("--conditions", default="", help="comma-separated, default canonical arms")
    p_opt.add_argument("--endpoint", type=float, default=168.0, help="endpoint hours/days")
    p_opt.add_argument(
        "--allow-assumption-sensitive", action="store_true",
        help="let a winner stand even if its verdict depends on an ASSUMED constant",
    )
    p_opt.set_defaults(func=cmd_optimize)

    sub.add_parser(
        "harnesses",
        parents=[common],
        help="what each harness adds, and why the pair is the unit",
    ).set_defaults(func=cmd_harnesses)

    p_demo = sub.add_parser(
        "demo", parents=[common], help="the pitch, in order, with nothing to type"
    )
    p_demo.add_argument(
        "--no-pause", action="store_true", help="do not wait between beats"
    )
    p_demo.add_argument("--beat", type=int, help="run a single beat")
    p_demo.set_defaults(func=_cmd_demo)

    p_check = sub.add_parser(
        "check-extraction",
        parents=[common],
        help="validate the extractor against designs with known specs",
    )
    p_check.add_argument("--extractor", help="override the extractor model")
    p_check.set_defaults(func=cmd_check_extraction)

    p_replay = sub.add_parser(
        "replay", parents=[common], help="re-score a recorded run (no API key needed)"
    )
    p_replay.add_argument("path", help="path to a recorded run JSON file")
    p_replay.add_argument(
        "--verbose", action="store_true", help="also print the agent's prose"
    )
    p_replay.set_defaults(func=cmd_replay)

    p_assays = sub.add_parser(
        "assays", parents=[common], help="list assay protocols and calibration status"
    )
    p_assays.add_argument("--key", help="show one protocol in detail")
    p_assays.set_defaults(func=cmd_assays)

    p_chat = sub.add_parser(
        "chat",
        parents=[common],
        help="talk about a design; every answer is a simulation",
    )
    p_chat.add_argument("--design", help="start from a DesignSpec JSON file")
    p_chat.add_argument(
        "--assay", default="fibrin_contracture", help="assay twin key (default: fibrin_contracture)"
    )
    p_chat.add_argument("--extractor", help="override the extractor model")
    p_chat.add_argument(
        "--no-model",
        action="store_true",
        help="offline: needs --design, follow-ups still work",
    )
    p_chat.set_defaults(func=cmd_chat)


    p_inf = sub.add_parser(
        "infer",
        parents=[common],
        help="constants papers report without meaning to",
    )
    p_inf.add_argument("--key", help="run the rules against a protocol's corpus")
    p_inf.add_argument("--rule", help="only one rule")
    p_inf.add_argument("--limit", type=int, default=12, help="papers to search")
    p_inf.add_argument("--show", type=int, default=6, help="matches per pattern")
    p_inf.add_argument("--context", type=int, default=0)
    p_inf.set_defaults(func=cmd_infer)

    p_adv = sub.add_parser(
        "advise",
        parents=[common],
        help="what to change, and what each change would do",
    )
    p_adv.add_argument("--design", help="path to a DesignSpec JSON file")
    p_adv.add_argument(
        "--assay", default="fibrin_contracture", help="assay twin key (default: fibrin_contracture)"
    )
    p_adv.add_argument(
        "--all", action="store_true", help="also list changes that did not help"
    )
    p_adv.set_defaults(func=cmd_advise)


    p_route = sub.add_parser(
        "route",
        parents=[common],
        help="resolve -> gate -> simulate -> advise, from a fixture or the record",
    )
    # Exclusive because they are two different claims about where the numbers
    # came from, and a run that quietly used one while reporting the other is
    # the invented-provenance failure this project exists to criticise.
    p_source = p_route.add_mutually_exclusive_group(required=True)
    p_source.add_argument("--fixture", help="path to a ResolutionSet JSON file")
    p_source.add_argument(
        "--recorded",
        action="store_true",
        help="replay the recorded literature findings instead; needs --assay",
    )
    p_route.add_argument(
        "--assay",
        help=(
            f"assay key. Required with --recorded; defaults to "
            f"{ROUTE_DEFAULT_ASSAY} with --fixture"
        ),
    )
    p_route.set_defaults(func=cmd_route)

    p_intake = sub.add_parser(
        "intake",
        parents=[common],
        help="residual prose -> which assay could settle it, ranked",
    )
    p_intake.add_argument(
        "residual", help="what layer 1 could not settle without new data"
    )
    p_intake.set_defaults(func=cmd_intake)

    sub.add_parser(
        "vocabulary",
        parents=[common],
        help="the terms this side declares, and the ones it cannot",
    ).set_defaults(func=cmd_vocabulary)

    p_search = sub.add_parser(
        "search",
        parents=[common],
        help="query the live corpus (needs a Paperclip credential)",
    )
    p_search.add_argument("query", nargs="?", default="", help="free-text query")
    p_search.add_argument("--key", help="use a protocol's own recorded query")
    p_search.add_argument("--limit", type=int, default=8)
    p_search.set_defaults(func=cmd_search)

    p_cal = sub.add_parser(
        "calibrate", parents=[common], help="what literature calibration recovered"
    )
    p_cal.add_argument("--key", help="show one protocol's attempt in detail")
    p_cal.add_argument(
        "--source", default="auto", choices=("auto", "paperclip", "recorded")
    )
    p_cal.set_defaults(func=cmd_calibrate)

    sub.add_parser(
        "providers", parents=[common], help="which models are callable right now"
    ).set_defaults(func=cmd_providers)

    p_run = sub.add_parser(
        "run", parents=[common], help="propose -> simulate -> revise (needs API key)"
    )
    p_run.add_argument("--no-revise", action="store_true")
    p_run.add_argument(
        "--harness",
        default="single-shot",
        help="scaffolding around the model: single-shot | self-critique | checklist",
    )
    p_run.add_argument(
        "--record",
        metavar="PATH",
        help="save the run to JSON so it can be replayed and re-scored later",
    )
    p_run.add_argument(
        "--agent",
        default="openai:gpt-5.5",
        help="model under test, e.g. openai:gpt-5.5 or claude-opus-5",
    )
    p_run.add_argument(
        "--agent-effort", default="high", choices=("low", "medium", "high")
    )
    p_run.add_argument(
        "--extractor",
        help="prose->spec model. Leave unset: it should be constant across runs.",
    )
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
