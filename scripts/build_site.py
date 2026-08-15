"""Generate the static site from the real computed output.

    python scripts/build_site.py            # writes site/index.html
    python scripts/build_site.py --raw      # also include the per-well data

Static on purpose. No Python runtime on Vercel, no serverless cold starts, and -
the reason that matters - no public `/score` endpoint. The HTTP API stays on your
own machine; this is a page.

Every number here is computed at build time by calling the same functions the CLI
calls, so the site cannot drift from what the tool says. Regenerate after any
calibration change; do not hand-edit the HTML.

WHAT THIS PUBLISHES. Experiment 4 is unpublished research data. The aggregate
result - 6/6 vs 0/4 lysed, the fitted half-time, the fill percentages inside the
diagnosis strings - IS the finding, and putting it on a public URL discloses it.
That is the owner's call and it has been made. The per-well table is a further
step and is OFF unless `--raw` is passed, because a summary statistic and a
subject-level dataset are different things to publish.
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from refute.assays import REGISTRY  # noqa: E402
from refute.baselines import BASELINES  # noqa: E402
from refute.record import RecordedRun  # noqa: E402
from refute.score import score_design  # noqa: E402
from refute.tier0 import Tier0Design, score_tier0  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "site" / "index.html"
RECORDED = Path(__file__).resolve().parent.parent / "cases/exp4/runs/gpt-5.5-high.json"
DATA_CSV = Path(__file__).resolve().parent.parent / "cases/exp4/data/observed_timecourse.csv"

SIMS = 800  # more than the CLI default: this runs once, so buy the precision

VERCEL_JSON = """{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "cleanUrls": true,
  "trailingSlash": false,
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "no-referrer" },
        { "key": "X-Robots-Tag", "value": "noindex, nofollow, noarchive" },
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
        }
      ]
    }
  ]
}
"""

CSS = """
:root{--bg:#0b0c0e;--fg:#e8e6e3;--dim:#8b8781;--line:#23262b;--hi:#f0eeeb;--acc:#c9a227}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
 -webkit-font-smoothing:antialiased}
main{max-width:44rem;margin:0 auto;padding:5rem 1.5rem 8rem}
h1{font-size:2.4rem;line-height:1.1;letter-spacing:-.02em;margin:0 0 .4rem;color:var(--hi)}
h2{font-size:1.05rem;letter-spacing:.09em;text-transform:uppercase;color:var(--dim);
 margin:4.5rem 0 1.1rem;font-weight:600}
h3{font-size:1.1rem;margin:2.4rem 0 .6rem;color:var(--hi)}
p{margin:0 0 1.1rem}
.lede{font-size:1.2rem;color:var(--dim);margin-bottom:2.5rem}
.rule{height:1px;background:var(--line);border:0;margin:0}
table{width:100%;border-collapse:collapse;margin:1.2rem 0;font-size:.9rem;
 font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:600;font-size:.78rem;letter-spacing:.05em;
 text-transform:uppercase}
td.n{text-align:right;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
tr.hl td{background:#15171a;color:var(--hi)}
pre{background:#111316;border:1px solid var(--line);border-left:2px solid var(--acc);
 padding:1rem 1.1rem;overflow-x:auto;font-size:.82rem;line-height:1.5;
 font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--fg)}
blockquote{margin:1.4rem 0;padding:.2rem 0 .2rem 1.2rem;border-left:2px solid var(--acc);
 color:var(--hi);font-size:1.05rem}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;
 background:#15171a;padding:.1rem .3rem;border-radius:3px}
.note{font-size:.86rem;color:var(--dim);border:1px solid var(--line);
 padding:.9rem 1.1rem;margin:1.4rem 0;background:#0e1013}
.k{color:var(--hi);font-weight:600}
footer{margin-top:6rem;padding-top:1.5rem;border-top:1px solid var(--line);
 font-size:.82rem;color:var(--dim)}
a{color:var(--acc)}
"""


def esc(s: object) -> str:
    return html.escape(str(s))


def table(headers: list[str], rows: list[list[object]], highlight: int | None = None) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for i, r in enumerate(rows):
        cls = ' class="hl"' if highlight == i else ""
        cells = "".join(
            f'<td class="n">{esc(c)}</td>' if j else f"<td>{esc(c)}</td>"
            for j, c in enumerate(r)
        )
        body.append(f"<tr{cls}>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def pct(x: float) -> str:
    return f"{x:.0%}"


# ---------------------------------------------------------------------------


def section_baselines() -> tuple[str, dict[str, float]]:
    """(table html, the figures the prose quotes).

    The prose MUST interpolate these rather than hard-coding them. First draft of
    this page said "it reaches 9%" beside a table reading 10% - the numbers moved
    with the simulation count and the sentence did not. Generated pages drift
    exactly where a human types a number.
    """
    rows = []
    hl = None
    figures: dict[str, float] = {}
    for i, b in enumerate(BASELINES):
        s = score_design(b.design, n_sims=SIMS)
        figures[b.key] = s.power
        if b.key == "expert":
            hl = i
        rows.append([
            b.key,
            b.design.total_wells,
            pct(s.power),
            pct(s.testable_rate),
            pct(s.mean_lysed_fraction),
            s.replicates_needed if s.replicates_needed > 0 else "not estimable",
            s.feasibility,
        ])
    return (
        table(
            ["design", "wells", "power", "testable", "lysed", "wells/arm needed",
             "verdict"],
            rows,
            highlight=hl,
        ),
        figures,
    )


def section_assays() -> str:
    rows = [
        [p.key, p.status.value, "yes" if p.runnable else "no", len(p.missing_constants())]
        for p in REGISTRY.values()
    ]
    return table(["assay", "status", "scoreable", "constants missing"], rows)


def section_agent() -> tuple[str, str, dict[str, float]]:
    """(table of rounds, the refusal quote, figures the prose quotes)."""
    if not RECORDED.exists():
        return "<p class=\"note\">No recorded run present.</p>", "", {}
    run = RecordedRun.load(RECORDED)
    rows = []
    figures: dict[str, float] = {}
    for i, rnd in enumerate(run.rounds, 1):
        s = score_design(rnd.extracted, n_sims=SIMS)
        if i == 1:
            figures["round1_lysed"] = s.mean_lysed_fraction
            figures["round1_power"] = s.power
        rows.append([
            f"round {i}",
            "declined" if s.declined else pct(s.power),
            "-" if s.declined else pct(s.testable_rate),
            "-" if s.declined else pct(s.mean_lysed_fraction),
            s.feasibility,
        ])
    quote = (
        "No-go for the biological question. There is no one-12-well-plate design "
        "that will actually answer whether MSC-conditioned medium suppresses "
        "TGF-&beta;1-driven contraction&hellip; Total required scale: approximately "
        "130&ndash;140 cast wells, not 12."
    )
    meta = f"{run.agent} &middot; harness <code>{esc(run.harness)}</code>"
    return (
        table(["", "power", "testable", "lysed", "verdict"], rows) +
        f'<p class="note">Recorded run: {meta}. Scores recomputed at build time, '
        "not read back from the file.</p>",
        quote,
        figures,
    )


def section_tier0() -> str:
    examples = [
        ("scratch migration", 2, 6, 12, 8.0, 6.0, "well"),
        ("bleomycin lung, Ashcroft", 2, 8, 20, 1.2, 1.0, "animal"),
        ("qPCR fold-change", 3, 3, 12, 0.8, 0.5, "sample"),
    ]
    rows = []
    for assay, arms, n, cap, eff, sd, unit in examples:
        s = score_tier0(Tier0Design(
            assay=assay, n_arms=arms, replicates_per_arm=n, capacity=cap,
            expected_effect=eff, variability_sd=sd, unit=unit,
        ))
        rows.append([
            # A literal multiplication sign, not "&times;" - every cell goes
            # through html.escape, so an entity would be double-escaped and
            # shown as source text. (It was.)
            assay, f"{arms}×{n}", f"{eff:g} / {sd:g}", pct(s.power),
            s.replicates_needed if s.replicates_needed > 0 else "beyond scale",
            s.feasibility,
        ])
    return table(
        ["assay", "design", "effect / SD", "power", "needed per arm", "verdict"], rows
    )


def section_raw() -> str:
    rows = []
    for line in DATA_CSV.read_text().splitlines():
        if line.startswith("#") or line.startswith("well,"):
            continue
        rows.append(line.split(","))
    return table(
        ["well", "condition", "d1", "d3", "d4", "d5", "d10", "state"], rows
    )


def build(include_raw: bool) -> str:
    baselines, base_fig = section_baselines()
    assays = section_assays()
    agent_table, refusal, agent_fig = section_agent()
    tier0 = section_tier0()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Every figure the prose quotes comes from here, never from a keystroke.
    expert_p = pct(base_fig["expert"])
    ceiling_p = pct(base_fig["ceiling"])
    r1_lysed = pct(agent_fig.get("round1_lysed", 0.0))

    raw = ""
    if include_raw:
        raw = f"""
    <h2>The plate</h2>
    <p>Per-well fill percentage by day, and the Day&nbsp;10 state. Two wells
    excluded: cast failure and contamination.</p>
    {section_raw()}"""

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>refute &mdash; can this experiment answer its own question?</title>
<meta name="description" content="A benchmark that scores AI-designed experiments
against a mechanistic digital twin calibrated on an experiment that failed.">
<!-- Empty data URI: suppresses the favicon request rather than 404ing on it. -->
<link rel="icon" href="data:,">
<!-- Experiment 4 is unpublished. A public URL is the owner's decision and has
     been made, but being indexed and cached by search engines is a further step
     and is not required for showing the page to people. Remove to allow it. -->
<meta name="robots" content="noindex, nofollow, noarchive">
<style>{CSS}</style>
</head><body><main>

<h1>refute</h1>
<p class="lede">Can this experiment answer its own question?</p>
<hr class="rule">

<h2>The gap</h2>
<p>Evaluations for experiment-designing agents are built almost entirely on
published work. But published work is filtered: the experiments that did not work
are largely absent from it. So the single most informative signal for judging a
design &mdash; <span class="k">what actually goes wrong when you run it</span> &mdash;
is the signal missing from what these agents learned on.</p>
<p>This benchmark supplies one. A real fibrin-gel contracture assay whose
treatment window was destroyed by cell-mediated fibrinolysis, never published. Its
measurements calibrate a simulator, and a proposed plate is scored by
<em>simulating it</em> &mdash; not by asking a language model whether the design
looks sensible.</p>
{raw}

<h2>Is it the design, or the apparatus?</h2>
<p>Four hand-written references, so a score has a scale. <span class="k">expert</span>
is written with full hindsight: narrow to the headline contrast, spend all twelve
wells on it, protect the scaffold, sample the kinetics densely.</p>
{baselines}
<p><span class="k">It reaches {expert_p}.</span> Lift the plate limit and the
identical design reaches {ceiling_p} &mdash; so the binding constraint is the
apparatus, not the design. No design on one 12-well plate answers this question.
There is no model in the loop for that conclusion.</p>
<div class="note"><span class="k">unestimable</span> is a third verdict, not a
missing value. Those designs lose half their wells, and fibrinolysis takes the most
contractile wells first &mdash; so the survivors are biased against the very effect
being measured. Fix the scaffold loss before asking how many wells you need.</div>

<h2>Why this is not in the literature</h2>
<p>Six further fibrosis assays, structurally declared and numerically empty. They
refuse to be scored until real values exist.</p>
{assays}
<p>Searching published full text for the missing constants gives an asymmetry:
what the assay <em>measures</em> is partly recoverable, <span class="k">how it
breaks is not recoverable at all</span>. That is why verification lags generation
&mdash; the corpus training everyone's intuitions about what goes wrong is thin by
construction.</p>

<h2>What a frontier model did</h2>
{agent_table}
<p>Round one drove scaffold loss to {r1_lysed} with <span class="k">no
antifibrinolytic at all</span>, by treating at 1&nbsp;h and ending at 72&nbsp;h
&mdash; finishing
before the fibrinolysis window opens rather than spending a reagent to survive it.
Neither the original researcher nor the <code>expert</code> baseline did that.</p>
<p>Then it declined to run the experiment:</p>
<blockquote>{refusal}</blockquote>
<p>Which is this benchmark's own conclusion, reached independently &mdash; and
<span class="k">the scorer gave it 0% power</span>, the worst score available,
until that was fixed. A declined design is now its own verdict; nothing is
simulated and no power figure is printed. What a correct refusal is <em>worth</em>
against a {expert_p} plate is left deliberately unresolved: inventing that number
would be the kind of invented ground truth this project exists to object to.</p>

<h2>Scaling without pretending</h2>
<p>A mechanistic twin needs somebody's unpublished data, and that does not get
cheaper. Most experiments do not need one.</p>
<p><span class="k">Tier&nbsp;0</span> &mdash; underpowering and scale &mdash; is
arithmetic, works for any assay, and needs only your own effect size and
variability:</p>
{tier0}
<p>It will not invent a variance. Without one it refuses, because a power figure
computed from a guessed SD looks like a calculation and is not one. And it says
nothing about whether the preparation survives to be measured &mdash; that needs a
tier&nbsp;1 twin, which needs somebody's raw data on how the assay breaks.</p>
<p><a href="/tier0"><span class="k">Try it on your own experiment &rarr;</span></a>
Runs entirely in the page: no account, no key, and nothing you type is sent
anywhere.</p>

<h2>Honest limits</h2>
<p>Calibrated on <span class="k">one plate</span>, n=10 evaluable wells, one cell
source. The contraction curve rests on a single pre-plateau timepoint. The lysis
model rests on one endpoint plus a qualitative Day&nbsp;7. Aprotinin's benefit is
assumed, not measured &mdash; so any verdict depending on it is flagged rather than
reported plainly. The treatment effect is <em>injected</em>, not calibrated:
nothing here supports a claim about whether MSC-conditioned media actually
suppresses contraction.</p>
<p>And the twin cannot reward a design exploiting a mechanism it does not model,
so it refuses to score one rather than returning a confident number about a
different experiment.</p>

<footer>
Generated {stamp} from the repository at build time &mdash; every figure on this
page is computed by the same code paths the tool uses, at {SIMS} simulated plates
per design. Not hand-written, and regenerated rather than edited.
</footer>
</main></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--raw",
        action="store_true",
        help="include the per-well table (subject-level unpublished data)",
    )
    args = ap.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(include_raw=args.raw))
    # Belt and braces with the meta tag: some crawlers honour one and not the other.
    (OUT.parent / "robots.txt").write_text("User-agent: *\nDisallow: /\n")

    # vercel.json lives INSIDE site/ so the deploy can be `vercel --cwd site`.
    # Deploying from the repository root would upload cases/exp4/data/ to a third
    # party even though only site/ is served, and there is no reason to send the
    # per-well data anywhere. This way exactly two files leave the machine.
    (OUT.parent / "vercel.json").write_text(VERCEL_JSON)
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({kb:.1f} kB){'  [includes per-well data]' if args.raw else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
