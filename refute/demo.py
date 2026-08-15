"""The pitch, as one command.

Six beats in a fixed order, each with the line to say and the computation that
backs it. `refute demo` runs them all with a pause between; nothing here needs a
network, an API key, or sponsor compute.

Why this exists rather than a list of commands in a README: five commands typed
live, with flags, while talking, is five chances to mistype or scroll past the
number that matters. The order is also load-bearing - the finding only lands if
the ceiling (beat 3) comes before the agent (beat 6), or the agent's refusal
reads as a failure rather than as agreement.

Each beat delegates to the same `cmd_*` function the CLI exposes, so the demo
cannot drift from what the tool actually does. If a beat's output changes, the
demo changes with it.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RULE = "=" * 70

# The recorded agent run. Beat 6 degrades to an explanation if it is absent
# rather than crashing mid-demo.
RECORDED_RUN = Path("cases/exp4/runs/gpt-5.5-high.json")
DATA_CSV = Path("cases/exp4/data/observed_timecourse.csv")


@dataclass
class Beat:
    n: int
    title: str
    say: str            # what to deliver out loud while this is on screen
    run: Callable[[int], None]
    seconds: int        # rough budget, for keeping the whole thing under time


# ---------------------------------------------------------------------------
# Beat 1 - the data. Not a slide: the actual CSV the twin is calibrated on.
# ---------------------------------------------------------------------------


def _beat_data(_sims: int) -> None:
    if not DATA_CSV.exists():
        print(f"  (missing {DATA_CSV} - run from the repository root)")
        return

    rows = [
        r
        for r in csv.DictReader(
            line for line in DATA_CSV.read_text().splitlines() if not line.startswith("#")
        )
    ]

    print(f"  {'well':>5} {'condition':>9} {'d1':>6} {'d5':>6} {'d10':>6}  state")
    for r in rows:
        d10 = r["d10_fill"] or "-"
        print(
            f"  {r['well']:>5} {r['condition']:>9} {r['d1_fill'] or '-':>6} "
            f"{r['d5_fill'] or '-':>6} {d10:>6}  {r['d10_state']}"
        )

    tgfb = [r for r in rows if r["condition"] in ("N-T", "N-CM+T") and r["d10_state"] != "excluded"]
    other = [r for r in rows if r["condition"] in ("N-SS", "N-CM") and r["d10_state"] != "excluded"]
    lysed_tgfb = sum(1 for r in tgfb if "lysed" in r["d10_state"])
    lysed_other = sum(1 for r in other if "lysed" in r["d10_state"])

    print()
    print(
        f"  Lysed by Day 10:  TGF-b arms {lysed_tgfb}/{len(tgfb)}   "
        f"non-TGF-b arms {lysed_other}/{len(other)}   (Fisher p = 0.0048)"
    )
    print(
        "  The scaffold dissolved fastest in the most contractile arms - exactly\n"
        "  the arms the comparison needed. Two wells were lost to cast failure and\n"
        "  contamination. This was never published."
    )


# ---------------------------------------------------------------------------
# Beats 2-6 delegate to the real commands.
# ---------------------------------------------------------------------------


def _cli(name: str, **kwargs):
    """Call a cmd_* function with a namespace, so the demo cannot drift from it."""
    from . import cli

    def run(sims: int) -> None:
        args = argparse.Namespace(sims=sims, **kwargs)
        getattr(cli, name)(args)

    return run


def _beat_agent(sims: int) -> None:
    if not RECORDED_RUN.exists():
        print(
            f"  No recorded run at {RECORDED_RUN}.\n\n"
            "  Record one with:\n"
            "    refute run --agent openai:gpt-5.5 --agent-effort high \\\n"
            f"      --record {RECORDED_RUN}\n\n"
            "  Do NOT run the agent live in front of an audience: frontier models\n"
            "  are rate-limited to 10k TPM and a proposal is a multi-minute silence."
        )
        return
    _cli("cmd_replay", path=str(RECORDED_RUN), verbose=False)(sims)


BEATS: tuple[Beat, ...] = (
    Beat(
        n=1,
        title="A real experiment that failed",
        say=(
            "This is one 12-well plate of anchored fibrin gels, asking whether "
            "MSC-conditioned\nmedia blunts TGF-beta-driven contraction in human "
            "synovial fibroblasts. Look at\nthe last column."
        ),
        run=_beat_data,
        seconds=45,
    ),
    Beat(
        n=2,
        title="Score the design that was actually run",
        say=(
            "The twin is calibrated on that plate. Scoring the design that "
            "produced it:\nzero power, half the wells gone. Note it refuses to say "
            "how many wells were\nneeded - the survivors are biased against the "
            "effect."
        ),
        run=_cli("cmd_baseline", design=None),
        seconds=45,
    ),
    Beat(
        n=3,
        title="Is that the design's fault, or the apparatus's?",
        say=(
            "The load-bearing screen. EXPERT is hand-written with full hindsight - "
            "narrow the\ncontrast, spend all twelve wells, protect the scaffold, "
            "sample early. It reaches\nnine percent. Lift the plate limit and the "
            "SAME design reaches eighty-three.\nSo no design on one plate answers "
            "this question. That is the finding, and there\nis no model in the loop."
        ),
        run=_cli("cmd_baselines"),
        seconds=60,
    ),
    Beat(
        n=4,
        title="Two defects, separable, and neither fix alone is enough",
        say=(
            "Without an antifibrinolytic, a quarter of wells are lost at every n, "
            "which caps\npower. Add one and the losses vanish - but n=3 still gives "
            "two percent. Both\nhad to be fixed, and at twelve wells both together "
            "are still short."
        ),
        run=_cli("cmd_sweep"),
        seconds=45,
    ),
    Beat(
        n=5,
        title="Why none of this is in the literature",
        say=(
            "Six more fibrosis assays, thirty-five constants, searched against "
            "published\nfull text. What the assay MEASURES is partly recoverable. "
            "How it BREAKS is not\nrecoverable at all. That asymmetry is why "
            "agents trained on published work\ncannot judge experimental design - "
            "and it is a measurement, not an assertion."
        ),
        run=_cli("cmd_calibrate", key=None, source="auto"),
        seconds=60,
    ),
    Beat(
        n=6,
        title="What a frontier model did with it",
        say=(
            "Recorded, not live. Round one: it drove scaffold loss to one percent "
            "with NO\nantifibrinolytic, by ending at 72 hours instead of fighting "
            "fibrinolysis - a\nstrategy neither I nor the original researcher used. "
            "Then round two declined to\nrun the experiment at all, for the same "
            "reason the simulator gives.\n\nMy scorer gave that refusal zero "
            "percent until I fixed it. That is the most\nhonest thing in the "
            "project."
        ),
        run=_beat_agent,
        seconds=75,
    ),
)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _pause(interactive: bool) -> None:
    if not interactive:
        return
    try:
        input("\n    [enter] ")
    except EOFError:  # piped stdin - carry on rather than crash mid-demo
        pass


def run_demo(
    sims: int = 400, pause: bool = True, only: int | None = None
) -> int:
    """Run the pitch. Returns an exit code."""
    interactive = pause and sys.stdin.isatty()
    beats = [b for b in BEATS if only is None or b.n == only]
    if not beats:
        print(f"no such beat: {only}. Beats are 1-{len(BEATS)}.", file=sys.stderr)
        return 2

    if only is None:
        budget = sum(b.seconds for b in BEATS)
        print(RULE)
        print("refute - can this experiment answer its own question?")
        print(RULE)
        print(
            f"\n  {len(BEATS)} beats, ~{budget // 60}m{budget % 60:02d}s of material.\n"
            "  No network, no API key, no sponsor compute. Nothing here can fail "
            "on venue wifi.\n"
        )
        _pause(interactive)

    started = time.monotonic()
    for beat in beats:
        print()
        print(RULE)
        print(f"  {beat.n}/{len(BEATS)}   {beat.title}")
        print(RULE)
        print()
        for line in beat.say.splitlines():
            print(f"  > {line}")
        print()
        beat.run(sims)
        _pause(interactive)

    if only is None:
        elapsed = time.monotonic() - started
        print()
        print(RULE)
        print(
            f"  Ends on the refusal, deliberately. Compute took {elapsed:.1f}s;\n"
            "  the talking is the rest.\n\n"
            "  If asked 'can others run it?': refute exposes an Agent protocol, a\n"
            "  gym-style environment, and an HTTP API - see README. If asked about\n"
            "  extraction: 6/6 on hand-written designs with known specs."
        )
        print(RULE)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    return run_demo(sims=args.sims, pause=not args.no_pause, only=args.beat)
