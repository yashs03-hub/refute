# Experiment 4 — provenance

## ⚠ Unpublished data

`data/observed_timecourse.csv` contains **unpublished MPhil research data**
(primary human synovial fibroblasts, consented waste tissue). It is included
because the twin's calibration is meaningless without the measurements it was
fitted to — a benchmark whose ground truth you cannot inspect is not a
benchmark.

**This repository must stay private** until the underlying work is published or
the author decides otherwise. Do not redistribute the CSV.

## What was run

Anchored fibrin gel contracture assay on the Roberts 2022 "contracture-in-a-well"
model. Constructs anchored at both ends by Mersilk sutures over pins set in
PDMS, holding each gel a few mm above the plate floor. One 12-well plate, cast
2026-06-12.

| Column | Condition | Meaning |
|---|---|---|
| 1 | `N-SS` | serum-starved control |
| 2 | `N-T` | + TGF-β1 |
| 3 | `N-CM` | + MSC-conditioned media |
| 4 | `N-CM+T` | + both |

Rows A/B/C are replicates. Treatments applied Day 5 (t0 = 120 h post-cast).

**Exclusions:** A1 (construct never formed — casting failure), B3 (microbial
contamination, excluded at all timepoints). n = 10 evaluable.

## What was measured

Imaging was phone-only on a fixed rig. Quantification is the fraction of the
well covered by gel (`fill%`), segmented per-well from the value channel within
a Hough-detected well ROI. Scale comes from the well's own inner diameter
(22.1 mm) — **not** the pins, whose spacing varied between wells.

Stated precision: ±2–3 fill-points, limited by diffuse gel edges.

Auto-segmentation only worked under a locked protocol: individual well,
centred, light on, dark matte background, richly saturated phenol-red medium.
Handheld whole-plate frames with glare defeated every method attempted
(brightness, texture, greenness, HSV-saturation, central neck-profile).

## The two findings the twin is calibrated on

**1. Contraction is fast and nearly over before the first image.**
Exponential fit: plateau 13.8% fill (86% area reduction), half-time ~5.8 h.
First imageable timepoint was Day 1, by which contraction was ~94% complete —
so t₀ and slope were unidentifiable and no Boltzmann sigmoid could be fitted.

**2. Scaffold failure is contractility-dependent.**
At Day 10, TGF-β⁺ arms lysed 6/6; TGF-β⁻ arms lysed 0/4 (they collapsed onto
the pins instead of dissolving). Fisher exact **p = 0.0048**. Day 7 was
transitional, not a clean cutoff.

Mechanism: the fibrin recipe contained no antifibrinolytic, so plasmin-mediated
scaffold loss ran fastest in the most contractile constructs — destroying the
treatment-phase window in exactly the arms the comparison depended on.

## What was NOT measured

**The treatment effect.** Fibrinolysis removed the endpoint before any
MSC-CM vs TGF-β contrast could be read. The twin therefore *injects* an effect
size as ground truth rather than calibrating one, and asks whether a design
would have recovered it. Nothing here supports a claim about whether MSC-CM
actually suppresses contraction.

**Any antifibrinolytic arm.** No aprotinin was used, so the twin's
`APROTININ_HAZARD_SCALE` is an assumption, not a result. Sweep it; never report
a conclusion that rests on one value of it.

## Source records

Original data and analysis live outside this repository, under
`Cambridge MPhil/Modules/5 - Research Project/Research/05_Contracture_Assay/`
(`contracture_run1/`, plus `experiment4_analysis_summary.md` dated 2026-06-29).
