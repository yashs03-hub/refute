"""Build the tier-0 form, and prove the browser maths matches the Python.

    python scripts/build_tier0_form.py

Writes `site/tier0.html` with the JavaScript and critical-value table inlined -
one file, no requests, no key, nothing leaves the machine. That is the whole
point: a lab member can plan an experiment without their unpublished design being
sent to a third party.

`web/tier0.js` is a second implementation of `refute/tier0.py`, which is a
liability. This script manages it: a dense grid goes through BOTH and the build
FAILS on any disagreement beyond TOLERANCE. Editing either file without the other
breaks the build rather than shipping a page that quietly disagrees with the CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scipy import stats  # noqa: E402

from refute.tier0 import Tier0Design, score_tier0, _power  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
JS_SRC = ROOT / "web" / "tier0.js"
OUT = ROOT / "site" / "tier0.html"

# n per arm the table covers; df = 2n-2 is always even, so only even df is stored.
N_MAX = 400

ALPHAS = (0.05, 0.01)
TARGET_POWERS = (0.8, 0.9)

TOLERANCE = 1e-6


def _by_df(quantile: float) -> dict[str, float]:
    return {
        str(2 * n - 2): round(float(stats.t.ppf(quantile, 2 * n - 2)), 7)
        for n in range(2, N_MAX + 1)
    }


def critical_values() -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Two separate tables, keyed by the exact strings JavaScript will produce.

    Deliberately NOT one table reached by arithmetic. The first version derived
    the one-sided quantile as tCrit(df, 2*(1-targetPower)), and 2*(1-0.8) is
    0.3999999999999999 in floating point - it missed the "0.4" key and threw on
    every page load. Float arithmetic must never produce a lookup key.
    """
    t_crit = {str(a): _by_df(1 - a / 2.0) for a in ALPHAS}
    t_power = {str(p): _by_df(p) for p in TARGET_POWERS}
    return t_crit, t_power


def js_with_table() -> str:
    src = JS_SRC.read_text()
    marker = "/* __T_CRIT__ */"
    if marker not in src:
        raise SystemExit(f"{JS_SRC} is missing the {marker} marker")
    t_crit, t_power = critical_values()
    injected = (
        f"const T_CRIT = {json.dumps(t_crit, separators=(',', ':'))};\n"
        f"const T_POWER = {json.dumps(t_power, separators=(',', ':'))};"
    )
    return src.replace(marker, injected)


def cross_validate(js: str) -> None:
    """Run a grid through both implementations. Any divergence fails the build."""
    grid = [
        (d, n)
        for d in (0.1, 0.2, 0.35, 0.5, 0.8, 1.0, 1.33, 2.0, 3.5)
        for n in (2, 3, 4, 6, 8, 12, 20, 30, 64, 120)
    ]
    expected = [_power(d, n, 0.05) for d, n in grid]

    harness = (
        js
        + "\nconst grid = "
        + json.dumps(grid)
        + ";\nconsole.log(JSON.stringify(grid.map(([d,n]) => power(d, n, 0.05))));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(harness)
        path = fh.name
    try:
        proc = subprocess.run(
            ["node", path], capture_output=True, text=True, timeout=300
        )
    finally:
        Path(path).unlink(missing_ok=True)

    if proc.returncode != 0:
        raise SystemExit(f"node failed:\n{proc.stderr.strip()}")

    got = json.loads(proc.stdout.strip().splitlines()[-1])
    worst = 0.0
    worst_case = None
    for (d, n), want, have in zip(grid, expected, got):
        diff = abs(want - have)
        if diff > worst:
            worst, worst_case = diff, (d, n, want, have)
    if worst > TOLERANCE:
        d, n, want, have = worst_case
        raise SystemExit(
            "browser and Python power functions disagree.\n"
            f"  worst case d={d} n={n}: python={want!r} js={have!r} "
            f"diff={worst:.3e} (tolerance {TOLERANCE:.0e})\n"
            "  Fix web/tier0.js or refute/tier0.py - do NOT relax the tolerance. "
            "A page that\n  disagrees with the CLI is worse than no page."
        )
    print(f"cross-check ok: {len(grid)} points, worst diff {worst:.2e}")

    # And the required-n solver, which is what a user actually reads.
    reps_expected = [
        score_tier0(
            Tier0Design(
                assay="x", n_arms=2, replicates_per_arm=3, capacity=10_000,
                expected_effect=d, variability_sd=1.0,
            )
        ).replicates_needed
        for d in (0.2, 0.5, 0.8, 1.0, 1.33)
    ]
    harness2 = (
        js
        + "\nconsole.log(JSON.stringify([0.2,0.5,0.8,1.0,1.33]"
        ".map(d => replicatesNeeded(d, 0.05, 0.8))));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(harness2)
        path2 = fh.name
    try:
        proc2 = subprocess.run(["node", path2], capture_output=True, text=True, timeout=300)
    finally:
        Path(path2).unlink(missing_ok=True)
    if proc2.returncode != 0:
        raise SystemExit(f"node failed:\n{proc2.stderr.strip()}")
    reps_got = json.loads(proc2.stdout.strip().splitlines()[-1])
    if reps_got != reps_expected:
        raise SystemExit(
            f"required-n solvers disagree: python={reps_expected} js={reps_got}"
        )
    print(f"cross-check ok: required-n matches {reps_expected}")

    # The minimum detectable effect, over EVERY alpha x target-power combination
    # the form offers. This was the gap that let a float-keyed lookup ship: the
    # first version of this check covered power() and replicatesNeeded() only,
    # and the page threw on load for the default settings. Validate every
    # function the UI can reach, at every setting the UI can select.
    combos = [
        (alpha, tp, n)
        for alpha in ALPHAS
        for tp in TARGET_POWERS
        for n in (2, 3, 6, 12, 30)
    ]
    mde_expected = []
    for alpha, tp, n in combos:
        s = score_tier0(
            Tier0Design(
                assay="x", n_arms=2, replicates_per_arm=n, capacity=10_000,
                expected_effect=1.0, variability_sd=2.5, alpha=alpha,
                target_power=tp,
            )
        )
        mde_expected.append(s.min_detectable_effect)

    harness3 = (
        js
        + "\nconst combos = " + json.dumps(combos) + ";"
        + "\nconsole.log(JSON.stringify(combos.map("
        "([a,tp,n]) => minDetectableEffect(2.5, n, a, tp))));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(harness3)
        path3 = fh.name
    try:
        proc3 = subprocess.run(
            ["node", path3], capture_output=True, text=True, timeout=300
        )
    finally:
        Path(path3).unlink(missing_ok=True)
    if proc3.returncode != 0:
        raise SystemExit(f"node failed on minDetectableEffect:\n{proc3.stderr.strip()}")
    mde_got = json.loads(proc3.stdout.strip().splitlines()[-1])

    worst_mde = 0.0
    worst_combo = None
    for combo, want, have in zip(combos, mde_expected, mde_got):
        diff = abs(want - have)
        if diff > worst_mde:
            worst_mde, worst_combo = diff, (combo, want, have)
    if worst_mde > TOLERANCE:
        combo, want, have = worst_combo
        raise SystemExit(
            "minimum-detectable-effect implementations disagree.\n"
            f"  worst case alpha/power/n={combo}: python={want!r} js={have!r} "
            f"diff={worst_mde:.3e}"
        )
    print(
        f"cross-check ok: MDE matches over {len(combos)} alpha x power x n "
        f"combinations, worst diff {worst_mde:.2e}"
    )


PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Is my experiment big enough? &mdash; refute tier 0</title>
<link rel="icon" href="data:,">
<meta name="robots" content="noindex, nofollow">
<style>
:root{{--bg:#0b0c0e;--fg:#e8e6e3;--dim:#8b8781;--line:#23262b;--hi:#f0eeeb;
 --acc:#c9a227;--bad:#d4726a;--ok:#7fa87f}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
 font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}}
main{{max-width:40rem;margin:0 auto;padding:3.5rem 1.5rem 7rem}}
h1{{font-size:1.9rem;margin:0 0 .3rem;letter-spacing:-.02em;color:var(--hi)}}
.lede{{color:var(--dim);margin:0 0 2rem}}
fieldset{{border:1px solid var(--line);padding:1.2rem;margin:0 0 1.2rem}}
legend{{color:var(--dim);font-size:.75rem;letter-spacing:.09em;
 text-transform:uppercase;padding:0 .4rem}}
label{{display:block;margin:0 0 1rem}}
label span{{display:block;font-size:.85rem;color:var(--dim);margin-bottom:.3rem}}
input,select{{width:100%;background:#111316;color:var(--fg);
 border:1px solid var(--line);padding:.55rem .7rem;font:inherit;border-radius:3px}}
input:focus,select:focus{{outline:0;border-color:var(--acc)}}
.row{{display:flex;gap:1rem}} .row>label{{flex:1}}
.hint{{font-size:.78rem;color:var(--dim);margin-top:-.7rem}}
#out{{margin-top:1.5rem}}
.card{{border:1px solid var(--line);border-left:2px solid var(--acc);
 background:#0e1013;padding:1.2rem}}
.big{{font-size:2rem;color:var(--hi);font-variant-numeric:tabular-nums;
 letter-spacing:-.02em}}
.verdict{{font-size:.78rem;letter-spacing:.09em;text-transform:uppercase;
 color:var(--dim);margin-bottom:.2rem}}
table{{width:100%;border-collapse:collapse;margin:1rem 0 0;font-size:.9rem;
 font-variant-numeric:tabular-nums}}
td{{padding:.4rem 0;border-bottom:1px solid var(--line)}}
td:last-child{{text-align:right;font-family:ui-monospace,Menlo,monospace}}
.bad{{color:var(--bad)}} .ok{{color:var(--ok)}}
.why{{margin-top:1rem;font-size:.9rem}} .why li{{margin-bottom:.5rem}}
.caveat{{margin-top:1.6rem;border:1px solid var(--line);padding:1rem;
 font-size:.85rem;color:var(--dim);background:#0e1013}}
.caveat b{{color:var(--hi)}}
footer{{margin-top:3.5rem;padding-top:1.2rem;border-top:1px solid var(--line);
 font-size:.8rem;color:var(--dim)}}
a{{color:var(--acc)}}
</style>
</head><body><main>

<h1>Is my experiment big enough?</h1>
<p class="lede">Tier&nbsp;0 of <a href="/">refute</a>. Runs entirely in this
page &mdash; nothing you type is sent anywhere.</p>

<form id="f" autocomplete="off">
<fieldset><legend>what you are comparing</legend>
  <label><span>Assay or experiment</span>
    <input id="assay" value="my experiment"></label>
  <div class="row">
    <label><span>Arms (groups)</span><input id="arms" type="number" value="2"
      min="2" step="1"></label>
    <label><span>Replicates per arm</span><input id="n" type="number" value="3"
      min="1" step="1"></label>
    <label><span>Units available</span><input id="capacity" type="number"
      value="12" min="2" step="1"></label>
  </div>
</fieldset>

<fieldset><legend>your own estimates &mdash; both required</legend>
  <div class="row">
    <label><span>Difference you expect</span>
      <input id="effect" type="number" value="8" step="any"></label>
    <label><span>Within-arm SD of that measurement</span>
      <input id="sd" type="number" value="6" step="any" min="0"></label>
  </div>
  <p class="hint">Same units for both. The SD must come from a pilot, prior runs,
  or a published estimate for this assay &mdash; this page will not invent one.</p>
  <div class="row">
    <label><span>Significance</span><select id="alpha">
      <option value="0.05" selected>0.05</option><option value="0.01">0.01</option>
    </select></label>
    <label><span>Target power</span><select id="tp">
      <option value="0.8" selected>80%</option><option value="0.9">90%</option>
    </select></label>
  </div>
</fieldset>
</form>

<div id="out"></div>

<div class="caveat">
<b>This cannot tell you the experiment will work.</b> It answers whether the
comparison could resolve the difference you stated, and says nothing about
whether the preparation survives to be measured. The experiment this project is
built on was destroyed by its own gels dissolving before the endpoint &mdash; no
power calculation anywhere would have predicted that. Modelling how an assay
<em>breaks</em> needs somebody's raw failure data.
</div>

<footer>
Same arithmetic as <code>refute tier0</code>, cross-checked against it at build
time &mdash; the build fails if the two disagree. Noncentral&nbsp;t, not the
normal approximation, because at bench sizes the approximation overstates power.
</footer>
</main>

<script>
{js}

const $ = id => document.getElementById(id);
const IDS = ['assay','arms','n','capacity','effect','sd','alpha','tp'];

function fmtPct(x) {{ return (x*100).toFixed(0) + '%'; }}
function sig(x) {{ return Math.abs(x) >= 100 ? x.toFixed(0) : x.toPrecision(3); }}

function render() {{
  const arms = parseInt($('arms').value, 10);
  const n = parseInt($('n').value, 10);
  const capacity = parseInt($('capacity').value, 10);
  const effect = parseFloat($('effect').value);
  const sd = parseFloat($('sd').value);
  const alpha = parseFloat($('alpha').value);
  const targetPower = parseFloat($('tp').value);
  const out = $('out');

  const missing = [];
  if (!isFinite(effect) || effect === 0) missing.push(
    'the difference you expect between the two arms');
  if (!isFinite(sd) || sd <= 0) missing.push(
    'the within-arm SD of that measurement');
  if (missing.length) {{
    out.innerHTML = '<div class="card"><div class="verdict">cannot assess</div>' +
      '<p>Needs ' + missing.join(' and ') + '.</p>' +
      '<p style="color:var(--dim);font-size:.88rem;margin:0">A power figure ' +
      'computed from a guessed variance looks like a calculation and is not one. ' +
      'Run a pilot, use prior data, or record the design as unassessable.</p></div>';
    return;
  }}
  if (!(arms >= 2) || !(n >= 1) || !(capacity >= 2)) {{
    out.innerHTML = '<div class="card"><div class="verdict">cannot assess</div>' +
      '<p>A comparison needs at least 2 arms, 1 replicate and 2 available units.' +
      '</p></div>';
    return;
  }}

  let r;
  try {{ r = assess({{effect, sd, arms, n, capacity, alpha, targetPower}}); }}
  catch (e) {{
    out.innerHTML = '<div class="card"><div class="verdict">cannot assess</div><p>' +
      e.message + '</p></div>';
    return;
  }}

  const needed = r.replicatesNeeded > 0 ? r.replicatesNeeded
    : 'more than ' + {n_max};
  const cls = r.underpowered ? 'bad' : 'ok';
  const why = [];
  if (r.underpowered) why.push('<li class="bad">Underpowered: ' + n +
    ' per arm gives ' + fmtPct(r.power) + ' power, not ' + fmtPct(targetPower) +
    '.</li>');
  if (!r.fitsCapacity) why.push('<li class="bad">Over capacity as designed: ' +
    r.totalUnits + ' units requested, ' + capacity + ' available.</li>');
  if (r.feasibility === 'infeasible') why.push('<li class="bad">Infeasible at ' +
    'this scale: ' + needed + ' per arm across ' + arms + ' arms exceeds the ' +
    capacity + ' available. Narrow the comparison, measure more precisely, or ' +
    'report that the question cannot be answered at this scale &mdash; the last ' +
    'is a legitimate answer, not a failure.</li>');
  if (r.feasibility === 'beyond-scale') why.push('<li class="bad">The difference ' +
    'you expect is very small relative to your measurement noise, so no ' +
    'practical replication resolves it.</li>');
  if (!why.length) why.push('<li class="ok">This comparison can resolve the ' +
    'difference you stated, within the units you have.</li>');

  out.innerHTML =
    '<div class="card">' +
      '<div class="verdict">power at ' + arms + '&times;' + n + '</div>' +
      '<div class="big ' + cls + '">' + fmtPct(r.power) + '</div>' +
      '<table>' +
        '<tr><td>Cohen&rsquo;s d</td><td>' + r.d.toFixed(2) + '</td></tr>' +
        '<tr><td>Replicates per arm needed</td><td>' + needed + '</td></tr>' +
        '<tr><td>Smallest difference detectable</td><td>' +
          sig(r.minDetectableEffect) + '</td></tr>' +
        '<tr><td>Units used / available</td><td>' + r.totalUnits + ' / ' +
          capacity + '</td></tr>' +
        '<tr><td>Verdict</td><td>' + r.feasibility + '</td></tr>' +
      '</table>' +
      '<ul class="why">' + why.join('') + '</ul>' +
    '</div>';
}}

IDS.forEach(id => {{
  const el = $(id);
  el.addEventListener('input', render);
  el.addEventListener('change', render);
}});
render();
</script>
</body></html>
"""


def main() -> int:
    js = js_with_table()
    cross_validate(js)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(PAGE.format(js=js, n_max=N_MAX))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
