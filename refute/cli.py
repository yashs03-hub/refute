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

from .design import EXPERIMENT_4_AS_RUN, DesignSpec
from .score import feedback_for_agent, score_design


def _print(title: str, body: str) -> None:
    print("=" * 68)
    print(title)
    print("=" * 68)
    print(body)
    print()


def cmd_baseline(args: argparse.Namespace) -> int:
    design = EXPERIMENT_4_AS_RUN
    if args.design:
        design = DesignSpec.model_validate(json.loads(open(args.design).read()))
    score = score_design(design, n_sims=args.sims)
    _print(f"{design.total_wells}-well design, endpoint {design.endpoint_time_h:.0f} h",
           score.summary())
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
    from .agent import EXPERIMENT_4_BRIEF, extract_design, propose_design, revise_design
    from .providers import DEFAULT_EXTRACTOR, ledger_summary, spec_from_string

    agent = spec_from_string(args.agent, args.agent_effort)
    extractor = (
        spec_from_string(args.extractor, "low") if args.extractor else DEFAULT_EXTRACTOR
    )
    print(f"agent     {agent}\nextractor {extractor}  (held constant)\n")

    design_text = propose_design(agent=agent)
    _print("PROPOSED DESIGN", design_text)

    spec = extract_design(design_text, extractor=extractor)
    _print("EXTRACTED SPEC", spec.model_dump_json(indent=2))

    score = score_design(spec, n_sims=args.sims)
    _print("SIMULATED", score.summary())

    if args.no_revise:
        _print("TOKENS", ledger_summary())
        return 0

    feedback = feedback_for_agent(score)
    revised_text = revise_design(EXPERIMENT_4_BRIEF, design_text, feedback, agent=agent)
    _print("REVISED DESIGN", revised_text)

    revised_spec = extract_design(revised_text, extractor=extractor)
    _print("EXTRACTED SPEC (revised)", revised_spec.model_dump_json(indent=2))

    revised_score = score_design(revised_spec, n_sims=args.sims)
    _print("SIMULATED (revised)", revised_score.summary())

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
    p_base.set_defaults(func=cmd_baseline)

    sub.add_parser(
        "sweep", parents=[common], help="antifibrinolytic x replicates grid"
    ).set_defaults(func=cmd_sweep)

    sub.add_parser(
        "providers", parents=[common], help="which models are callable right now"
    ).set_defaults(func=cmd_providers)

    p_run = sub.add_parser(
        "run", parents=[common], help="propose -> simulate -> revise (needs API key)"
    )
    p_run.add_argument("--no-revise", action="store_true")
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
