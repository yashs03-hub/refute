"""Builds talks/reagent_judging_5min.pptx.

A 5-minute judging deck for re:AGENT (End to End Agentic Science), Track B.
Narrative backbone is PLAN.md §7.4a/§7.4b/§8.3 (the sixty-second version,
who the buyer is, the line worth having ready) — this expands that already-
tested script into slides rather than inventing new pitch language.

Regenerate: python talks/build_deck.py
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# --- palette -----------------------------------------------------------------

BG = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1A, 0x1D, 0x21)
MUTED = RGBColor(0x5B, 0x63, 0x6C)
NAVY = RGBColor(0x0F, 0x2A, 0x4A)
ACCENT = RGBColor(0xC0, 0x3B, 0x2E)      # the number-that-matters red
ACCENT_GREEN = RGBColor(0x1E, 0x7B, 0x4D)
RULE = RGBColor(0xDD, 0xE1, 0xE5)
CODE_BG = RGBColor(0x14, 0x17, 0x1A)
CODE_TEXT = RGBColor(0xE8, 0xEA, 0xED)
CODE_MUTED = RGBColor(0x8A, 0x92, 0x9C)

SANS = "Arial"
MONO = "Courier New"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _bg(slide, color=BG):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def _no_autosize(tf):
    el = tf._txBody
    bodyPr = el.find(qn("a:bodyPr"))
    for tag in ("a:normAutofit", "a:spAutoFit"):
        existing = bodyPr.find(qn(tag))
        if existing is not None:
            bodyPr.remove(existing)
    bodyPr.append(el.makeelement(qn("a:noAutofit"), {}))


def _box(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    _no_autosize(tf)
    return tb, tf


def _set(p, text, size, color=INK, bold=False, font=SANS, italic=False):
    r = p.add_run()
    r.text = text if text else " "
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    return r


def _add(p, text, size, color=INK, bold=False, font=SANS, italic=False):
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    return r


def _kicker(slide, text, y=Inches(0.55)):
    _, tf = _box(slide, Inches(0.7), y, Inches(11.9), Inches(0.4))
    p = tf.paragraphs[0]
    _set(p, text.upper(), 13, MUTED, bold=True)
    for r in p.runs:
        r.font._rPr.set("spc", "150")


def _title(slide, text, y=Inches(0.95), size=32):
    _, tf = _box(slide, Inches(0.7), y, Inches(11.9), Inches(1.1))
    p = tf.paragraphs[0]
    _set(p, text, size, NAVY, bold=True)


def _rule(slide, y):
    ln = slide.shapes.add_connector(1, Inches(0.7), y, Inches(12.63), y)
    ln.line.color.rgb = RULE
    ln.line.width = Pt(1)


def _footer(slide, n):
    _, tf = _box(slide, Inches(0.7), Inches(7.08), Inches(6), Inches(0.35))
    p = tf.paragraphs[0]
    _set(p, "refute — re:AGENT, Track B", 10, MUTED)
    _, tf2 = _box(slide, Inches(11.9), Inches(7.08), Inches(0.7), Inches(0.35))
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.RIGHT
    _set(p2, str(n), 10, MUTED)


def _code_block(slide, x, y, w, h, lines, size=15):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    box.adjustments[0] = 0.04
    box.fill.solid()
    box.fill.fore_color.rgb = CODE_BG
    box.line.fill.background()
    box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.3)
    tf.margin_right = Inches(0.3)
    tf.margin_top = Inches(0.22)
    tf.margin_bottom = Inches(0.22)
    _no_autosize(tf)
    for i, (text, color, bold) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(4)
        _set(p, text, size, color, bold=bold, font=MONO)
    return box


def _bullets(slide, x, y, w, h, items, size=17, gap=10, color=INK, lead_color=NAVY):
    _, tf = _box(slide, x, y, w, h)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        if isinstance(item, tuple):
            lead, rest = item
            _set(p, f"{lead}  ", size, lead_color, bold=True)
            _add(p, rest, size, color)
        else:
            _set(p, item, size, color)
    return tf


def _big_stat(slide, x, y, w, number, label, number_color=ACCENT, number_size=44):
    _, tf = _box(slide, x, y, w, Inches(1.0))
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _set(p, number, number_size, number_color, bold=True)
    _, tf2 = _box(slide, x, y + Inches(0.85), w, Inches(0.7))
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    p2.word_wrap = True
    _set(p2, label, 13, MUTED)


# -------------------------------------------------------------------------

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
blank = prs.slide_layouts[6]

n = 0


def new_slide():
    global n
    n += 1
    s = prs.slides.add_slide(blank)
    _bg(s)
    return s


# --- 1. Title ------------------------------------------------------------

s = new_slide()
_, tf = _box(s, Inches(0.9), Inches(2.5), Inches(11.5), Inches(1.4))
p = tf.paragraphs[0]
_set(p, "refute", 60, NAVY, bold=True)
_, tf = _box(s, Inches(0.95), Inches(3.75), Inches(11.5), Inches(1.0))
p = tf.paragraphs[0]
_set(p, "Benchmarking experiment-designing agents against experiments that failed.",
     22, INK)
_, tf = _box(s, Inches(0.95), Inches(4.5), Inches(11.5), Inches(0.6))
p = tf.paragraphs[0]
_set(p, "re:AGENT — End to End Agentic Science  ·  Track B: Build the Dataset",
     15, MUTED)
_rule(s, Inches(6.3))
_footer(s, n)

# --- 2. The gap ------------------------------------------------------------

s = new_slide()
_kicker(s, "The gap")
_title(s, "Published work is filtered.")
_bullets(s, Inches(0.7), Inches(2.05), Inches(7.6), Inches(4.0), [
    ("What's missing —", "the experiments that didn't work are largely "
     "absent from the corpus these agents learned on."),
    ("What that costs —", "an agent that generates a thousand plausible "
     "hypotheses and can't tell you which one is right hasn't automated "
     "science. It's automated speculation."),
    ("The actual bottleneck —", "was never idea generation. It's the cost "
     "of finding out you were wrong."),
], size=19, gap=22)
_code_block(s, Inches(8.55), Inches(2.05), Inches(4.05), Inches(3.7), [
    ("effect sizes,", CODE_MUTED, False),
    ("precision estimates:", CODE_MUTED, False),
    ("reported.", CODE_TEXT, True),
    ("", CODE_TEXT, False),
    ("failure rates,", CODE_MUTED, False),
    ("attrition, dropout:", CODE_MUTED, False),
    ("not reported.", ACCENT, True),
    ("", CODE_TEXT, False),
    ("measured across", CODE_MUTED, False),
    ("6 real assay", CODE_MUTED, False),
    ("scaffolds — not", CODE_MUTED, False),
    ("assumed. §6", CODE_MUTED, False),
], size=15)
_footer(s, n)

# --- 3. The real failure ---------------------------------------------------

s = new_slide()
_kicker(s, "The evidence")
_title(s, "A real experiment failed. It was never published.")
_bullets(s, Inches(0.7), Inches(2.05), Inches(11.9), Inches(3.3), [
    "Anchored fibrin gels, human synovial fibroblasts — testing whether "
    "MSC-conditioned media blunts TGF-β-driven contraction.",
    "The gels dissolved before the treatment window closed — cell-mediated "
    "fibrinolysis, fastest in exactly the arms the comparison needed.",
    "Nothing like it is in the literature. This benchmark is built on the "
    "one thing that never gets to be: the failure itself, as primary data.",
], size=20, gap=20)
_rule(s, Inches(5.55))
_, tf = _box(s, Inches(0.7), Inches(5.85), Inches(11.9), Inches(0.9))
p = tf.paragraphs[0]
_set(p, "A digital twin, calibrated on that plate — contraction kinetics, "
        "scaffold survival, measurement noise, attrition — all fitted to what "
        "actually happened, not assumed.", 16, MUTED, italic=True)
_footer(s, n)

# --- 4. The mechanism --------------------------------------------------

s = new_slide()
_kicker(s, "How it works")
_title(s, "The model extracts. The simulator judges.")
_code_block(s, Inches(0.7), Inches(2.15), Inches(11.9), Inches(1.15), [
    ("agent proposes  ──▶  LLM extracts  ──▶  twin simulates  ──▶  score",
     CODE_TEXT, True),
    ("  (free text)          (DesignSpec)        (calibrated)     (power)",
     CODE_MUTED, False),
], size=17)
_bullets(s, Inches(0.7), Inches(3.65), Inches(11.9), Inches(2.9), [
    ("Extraction —", "turning prose into parameters. Models do this "
     "reliably."),
    ("Judgement —", "deciding whether a design works. Models don't — so "
     "that half is a mechanistic simulator, not an LLM-as-judge rubric."),
    ("Feedback reports consequences, never corrections —", "“the scaffold "
     "was gone before your endpoint,” never “add aprotinin.” Working out "
     "the fix is the part being benchmarked."),
], size=18, gap=16)
_footer(s, n)

# --- 5. The live result ------------------------------------------------

s = new_slide()
_kicker(s, "The result")
_title(s, "A frontier model made the same three mistakes.")
_bullets(s, Inches(0.7), Inches(2.05), Inches(6.7), Inches(3.2), [
    "n=3 per arm. No antifibrinolytic. No reasoning about the scaffold "
    "at all — the same defects Experiment 4 actually had.",
    "Given consequences instead of corrections, it narrowed to the arms "
    "that mattered, filled the plate, flagged scaffold failure.",
], size=18, gap=18)
_big_stat(s, Inches(7.7), Inches(1.9), Inches(2.55), "0% → 97%",
          "runs yielding a testable result — one revision turn",
          number_color=ACCENT_GREEN, number_size=36)
_big_stat(s, Inches(10.3), Inches(1.9), Inches(2.3), "9%",
          "power — the honest ceiling on one plate",
          number_color=ACCENT, number_size=44)
_rule(s, Inches(5.35))
_, tf = _box(s, Inches(0.7), Inches(5.6), Inches(11.9), Inches(1.4))
p = tf.paragraphs[0]
_set(p, "Even the best design available cannot answer the question.", 22,
     NAVY, bold=True)
p2 = tf.add_paragraph()
p2.space_before = Pt(6)
_set(p2, "Hand-written with full hindsight, the same design reaches 9% power "
         "on one plate — and 83% the moment the plate limit is lifted. "
         "The constraint is the apparatus, not the agent.", 15, MUTED)
_footer(s, n)

# --- 6. Scale ------------------------------------------------------------

s = new_slide()
_kicker(s, "Scale")
_title(s, "Not one twin. A pattern.")
_bullets(s, Inches(0.7), Inches(2.05), Inches(6.9), Inches(4.4), [
    ("Six-scaffold literature calibration —", "the asymmetry stated above "
     "isn't assumed, it's measured: dual-instrument sweep, every quote "
     "checked against fetched full text."),
    ("A second mechanistic twin, live —", "bleomycin-induced pulmonary "
     "fibrosis + an MSC treatment arm. Triggered by a real question the "
     "fibrin twin structurally couldn't answer."),
    ("The optimizer —", "cheapest design meeting a power target. "
     "Human-facing only, tripwire-tested to never reach the agent under "
     "test — a search over designs is a search against the twin (§9.1)."),
], size=17, gap=18)
_code_block(s, Inches(8.0), Inches(2.05), Inches(4.6), Inches(4.4), [
    ("$ pytest -q", CODE_MUTED, False),
    ("821 passed, 6 skipped", ACCENT_GREEN, True),
    ("", CODE_TEXT, False),
    ("$ refute optimize \\", CODE_MUTED, False),
    ("    --assay bleomycin_lung \\", CODE_MUTED, False),
    ("    --msc-route IT", CODE_MUTED, False),
    ("WINNER: 2 arms x 20", CODE_TEXT, False),
    ("power 100%  testable 100%", ACCENT_GREEN, False),
    ("", CODE_TEXT, False),
    ("survivorship bias:", CODE_MUTED, False),
    ("+0.21 Ashcroft pts", ACCENT, True),
    ("(the project's own", CODE_MUTED, False),
    ("finding, as a number a", CODE_MUTED, False),
    ("second twin produces)", CODE_MUTED, False),
], size=13)
_footer(s, n)

# --- 7. Who needs this ---------------------------------------------------

s = new_slide()
_kicker(s, "Who this is for")
_title(s, "Anyone about to spend a budget on an underpowered plate.")
_, tf = _box(s, Inches(0.7), Inches(2.15), Inches(11.9), Inches(2.0))
p = tf.paragraphs[0]
p.word_wrap = True
_set(p, "Experiment 4 cost a term of MPhil work to discover something a "
        "simulator says in 40 milliseconds:", 19, INK)
_, tf2 = _box(s, Inches(0.7), Inches(3.2), Inches(11.9), Inches(1.3))
p2 = tf2.paragraphs[0]
_set(p2, "You needed thirty wells per arm. You have three.", 24, ACCENT,
     bold=True)
p3 = tf2.add_paragraph()
p3.space_before = Pt(6)
_set(p3, "And until the gel stops dissolving, you can't even find that out.",
     18, MUTED, italic=True)
_rule(s, Inches(4.9))
_, tf = _box(s, Inches(0.7), Inches(5.2), Inches(11.9), Inches(1.4))
p = tf.paragraphs[0]
_set(p, "The agentic-science framing is why it's a benchmark today. The "
        "durable version is a pre-registration check — the optimizer, "
        "returning the cheapest sufficient design, before a single well "
        "gets cast.", 17, INK)
_footer(s, n)

# --- 8. Close --------------------------------------------------------------

s = new_slide()
_kicker(s, "The line worth having ready")
_title(s, "The common failure isn't malicious AI biology.")
_, tf = _box(s, Inches(0.7), Inches(2.1), Inches(11.9), Inches(1.9))
p = tf.paragraphs[0]
p.word_wrap = True
_set(p, "It's incompetent AI-designed biology — an agent proposing an "
        "experiment that cannot answer its own question, and nobody "
        "catching it because there's no simulator in the loop.", 20, INK)
p2 = tf.add_paragraph()
p2.space_before = Pt(10)
_set(p2, "That failure is measurable. This measures it against primary "
         "data.", 20, NAVY, bold=True)
_rule(s, Inches(4.3))
_bullets(s, Inches(0.7), Inches(4.6), Inches(11.9), Inches(2.0), [
    "Live on GitHub — yashs03-hub/refute. 821 tests, two independently "
    "calibrated twins, an optimizer, a CLI.",
    "Track B: build the dataset. This is that dataset's first two entries, "
    "built the way the rest of it should be.",
], size=17, gap=14)
_footer(s, n)

out_path = "talks/reagent_judging_5min.pptx"
prs.save(out_path)
print(f"wrote {out_path}, {n} slides")
