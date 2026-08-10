# TEMPLATE — what a tier-1 case needs

Copy this directory, rename it after your assay, fill in `data/` and this file.

The whole ask is **one CSV and the answers below**. The fibrin twin's entire
failure model rests on **ten wells** — 6/6 lysed in the TGF-β arms, 0/4 in the
others, at one timepoint. Tier 1 is not blocked by data volume. It is blocked by
four or five numbers per assay that nobody records in a recoverable form.

---

## 1. The timecourse — `data/observed_timecourse.csv`

One row per unit per timepoint. See the comments in the template.

**The one thing that is easy to get wrong:** record a row even when the
measurement failed, with `state` set. A blank `value` with `state=failed` is the
single most valuable cell in the file, because it is the thing that is absent from
every published paper. A CSV containing only successful measurements is a CSV that
cannot calibrate a tier-1 twin.

**`failed` and `unmeasurable` must not be merged.** One is the assay breaking
(the hazard being modelled); the other is you missing a reading (measurability).
They enter the twin as different constants and pull in different directions.

## 2. Failure counts by condition

Copy this table out and fill it in. This is the hazard anchor, and it is what
makes the twin more than a power calculator.

| Condition | Units started | Failed by endpoint | Endpoint (hours) | Failed earlier? |
|---|---|---|---|---|
| control | | | | |
| treated | | | | |

**Why by condition, and why this is tractable.** The constant that matters is the
*coupling* — whether units fail because of how strongly they responded. Measured
per unit that is circular: a unit that failed has no readout. Experiment 4 got
around it by scoring failure categorically per arm, so arm membership stands in
for the phenotype. You do not need per-unit response. You need **counts split by
condition**, and a second timepoint if you have one — with only an endpoint, the
shape of the hazard is unidentifiable (see limit 3 below).

## 3. Attrition, with reasons separated

| Reason | Count | Of how many |
|---|---|---|
| never entered (casting/dosing failure) | | |
| lost to contamination | | |
| measurement failed but prep intact | | |

## 4. The design as actually run

- Units per condition, and total capacity of one run (one plate, one cage rack…)
- When treatment was applied, in hours since start
- Which timepoint you treated as the primary endpoint
- The readout, and its units

## 5. What you already know about precision

Either of these is enough:

- repeated measurements of the same unit at the same timepoint (best — it splits
  systematic bias from per-reading noise), or
- your own statement of the measurement error, e.g. "±2–3 units on a diffuse
  edge", which is what Experiment 4 supplied

---

## What Experiment 4 wishes had been recorded

Its own documented limits are exactly the collection spec. Three things cost it
precision, and all three were free to avoid at the bench:

1. **Denser early sampling.** Contraction was ~94% complete by the first
   imageable timepoint (24 h), so the time constant is extrapolated from a single
   pre-plateau point and no sigmoid could be fitted. *Sample early and often
   during the fast phase, even roughly.*

2. **Failure scored at more than one timepoint.** The hazard rests on one
   endpoint (Day 10) plus a qualitative Day 7 note. That is enough to fit a rate
   and not enough to pin its shape. *Score failure whenever you look, not only at
   the end.*

3. **An arm with the obvious mitigation in it.** There was no antifibrinolytic
   arm, so aprotinin's effect is ASSUMED, not measured — and any verdict that
   depends on it now gets flagged rather than reported. *If you already suspect
   the failure mode, include one arm that tries to prevent it. That arm is worth
   more than a third biological condition.*

## What not to bother collecting

- Raw images or instrument files — the twin needs numbers, not pixels.
- Anything about the biological conclusion. The twin scores *designs*, not
  hypotheses; the treatment effect is injected as ground truth, so whether your
  intervention worked is irrelevant to calibration.
- Perfect data. A failed, messy, half-abandoned run is **more** useful than a
  clean one, because the failure modes are the point.

## Provenance to state

- What was run, on what, when
- Ethics/approval reference if the material is human or animal
- Whether the data is published, and whether it may be redistributed

⚠️ Unpublished data stays in a private repository. Note that derived constants
leak too: a calibrated twin's diagnosis strings quote the measured values back,
so publishing code built on unpublished data publishes the result.
