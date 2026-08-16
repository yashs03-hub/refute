# Grounding agent × refute — how they compose

> ## ⚠️ SUPERSEDED 2026-08-16 — read the SPEC first
>
> **The current agreement is `15 - SPEC - the whole system.md`.** For the seam in
> code, read `HANDOFF.md`. This file is kept because most of its argument still
> holds and because the part that did not is worth being able to point at.
>
> **What changed.** This document was written against the teammates' *earlier*
> scope, in which the grounding agent was a retrieval step feeding refute's own
> calibration — §5 here offers `CalibrationSource` as the seam, which makes the
> other half a *backend* of this repository. The agreement since is a **two-layer
> split**: layer 1 answers everything about a hypothesis that can be answered
> without a bench — data and literature, to exhaustion — and hands over what it
> could not settle. Layer 2, this repository, designs the experiment for that
> residual. Layer 1 is the stage *before* refute, not a source plugged into it,
> and it may terminate without a handoff at all. That case did not exist in this
> document.
>
> **Still transfers, unchanged:**
> - §2, the two failure classes. Knowledge defect versus design defect is the
>   reason there are two layers, and the SPEC restates it in its §2.
> - §3's rule: *the model extracts, the simulator judges.* Nothing in the SPEC
>   says this in these words and it is the load-bearing constraint on both
>   layers.
> - §4, the Experiment 4 demo arc, and its numbers — 9% power, 0% → 97%
>   testable. Unaffected by the re-scope.
> - §5's `Blocked` taxonomy, which is still the most transferable thing here. It
>   has since gained a sixth reason, `NOT_SUPPLIED` — see `assays/evidence.py`.
> - §5's 35-constant work queue, still 35 across six scaffolds.
> - §9, the Track B framing.
>
> **Superseded, and where to look instead:**
> - §3's composition diagram and §5's "agree these two shapes" → SPEC §5 and
>   `refute/handoff.py`. The agreed crossing is `Handoff` / `Finding` /
>   `OpenItem` into `Resolution` / `ResolutionSet`, not `CalibrationSource` and
>   `Evidence`.
> - §7's Workstream B. Item 1, requirements extraction, is built —
>   `refute/requirements.py`. Item 2, the `PRIMARY` provenance tag, is built. Item
>   3, the MCP surface, is not.
> - §8's two asks. The Paperclip credential exists and works. The exp4 authorship
>   gate was cleared by the owner on 2026-08-15 (`cases/exp4/PROVENANCE.md`);
>   repository visibility remains a separate decision nobody has taken.
> - The test count below. It read 321 when written; the suite is several hundred
>   larger and moving hour to hour. Run it rather than quoting this file.

For the shared repo. Written from the refute side by someone who knows that half
cold, so treat the claims about *your* half as proposals and the claims about
refute as checkable — everything here is backed by code in this repository.

---

## 1. The short version

Your brainstorm's §12 open question 5 is *"how do we simulate an experimental
setup well enough to say the design was wrong?"*, and §7 says the missing piece
is *"a way to feed back on your setup and tell you the setup was wrong. Simulate
it, retest it."*

That is built. It is `score_design`. It takes an experimental design and returns
whether the design can detect the effect it is looking for, judged by a
mechanistic simulator calibrated against real measurements from a real
experiment that really failed — not by a model's opinion.

And the traffic runs both ways, which is the part worth getting excited about:

| Your layer gives refute | refute gives your layer |
|---|---|
| The constants a twin needs, pulled from literature — which is what lets refute cover more than one assay | An **objective score for retrieval quality**: did your extracted constants build a twin that reproduces a known measured outcome? |

That second one is unusual. Every literature-grounding system has the same
unanswerable question — *is my grounding any good?* — and normally you cannot
tell, because the only judge available is another model. Here you can:
extract the constants, build the twin, and check whether it predicts what
actually happened on a plate we have the data for.

---

## 2. What each half is for, honestly

They are **not** the same tool, and pretending otherwise will produce a mushy
demo. Two failure classes, and only one of them is yours:

**Knowledge defect** — your §3 example. The cell type is not permissive to
infection. The literature says so. You retrieve it, the agent reassesses.
**refute contributes nothing here** and should not pretend to. This part of your
product stands alone.

**Design defect** — the experiment cannot answer its question regardless of
whether the hypothesis is right. Not a knowledge gap; an apparatus and
statistics problem. **Literature is structurally silent on this**, and refute
has the measurement to prove it (§4 below).

Symmetrically: refute's `tier0` — power and sample size from your own effect
size and SD — needs nothing from your layer.

So: two things that stand alone, and one place they compose. The composition is
the pitch.

---

## 3. The composition

```
hypothesis (prose)
      │
      ├─► [GROUND]     your layer. Retrieval + interpretation.
      │                returns Evidence + Blocked. NOT a verdict.
      │
   design (prose)
      │
      ├─► [EXTRACT]    prose → DesignSpec. One model call. refute has this.
      │
      ├─► [SIMULATE]   score_design → power, testable_rate, diagnoses
      │
      ├─► [ADVISE]     one-lever perturbations, each with a simulated
      │                before/after. refute has this too.
      │
      └─► revise, loop
```

**The rule that must not erode**, because it will, under time pressure, in a
chat interface, at 2am:

> The model **extracts**. The simulator **judges**.
>
> Prose → structured data is a job models are reliable at. "Would this work" is
> not. Your grounding agent returns evidence and gaps; it must never return a
> verdict on the design. The moment it does, the whole thing is an LLM grading
> an LLM, which is your §6 objection to model consensus — arriving by the back
> door.

This is your §12.2 (same agent or separate?) answered structurally rather than
by preference: it does not matter much which agent *retrieves*, because
retrieval is extraction. It matters enormously that whatever *judges* is not a
model.

---

## 4. The warning, and it is the best demo beat you have

Your §11 says: ground the prototype in an existing lab hypothesis, work
backwards from something you know the answer to, see if the system recapitulates
it.

refute is exactly that, already done — and the result is a problem for a
literature-only design:

**Experiment 4.** Anchored fibrin gel contracture assay, primary human synovial
fibroblasts. Hypothesis: TGF-β1 drives contracture, MSC-conditioned media
modulates it. That hypothesis is entirely consistent with the literature. The
mechanism checks out. Novelty is reasonable. **Your grounding agent would pass
it, and would be right to.**

It failed anyway, for two independent reasons neither of which is a knowledge
gap:

1. **Scaffold failure.** No antifibrinolytic. Fibrinolysis is fastest in the
   most contractile arm, so the TGF-β arms — the ones the contrast depends on —
   destroy themselves first. Succeeding at the biology is what destroyed the
   readout.
2. **Underpowering, independently.** ±2–3 fill-points of quantification noise
   against the effect size means the experiment needed roughly an order of
   magnitude more wells per arm than the three it ran.

And the reason literature could not have warned you is measured, not asserted.
A calibration attempt over published protocols found effect sizes and precisions
reported routinely — and **the failure constants absent from every protocol
examined**: delamination rates, detachment rates, chip rupture per cycle,
bleomycin mortality, contamination over long culture. Papers report what the
assay does when it works. What it does when it goes wrong is not written down,
because the plate that delaminated on day 3 never became a figure.

So the demo arc:

1. Here is a hypothesis.
2. Grounding agent: consistent with the literature, here is the supporting work,
   here are the effect sizes others report. **Green light.**
3. Here is the experiment designed to test it. Still green.
4. refute simulates it: **0% of runs yield a testable result.** Every treated
   gel is gone before the endpoint.
5. **Literature could not have told you that** — and here is the dataset showing
   why not.
6. Fix it: testable **0% → 97%**. Power still only **9%**. The honest verdict is
   that the question cannot be answered at this scale, and *that verdict is the
   finding*.

Beat 2→4 is the whole pitch. It also fixes your §10 worry that the problem is
murky and judges will not see it: this gives the murk a crisp, quantified edge.

---

## 5. The seam — where the two halves actually meet

One protocol, four methods. It already exists in `refute/assays/sources.py`:

```python
class CalibrationSource(Protocol):
    name: str
    @property
    def available(self) -> bool: ...
    def why_unavailable(self) -> str: ...
    def search(self, query: str, limit: int = 10) -> list[Hit]: ...
```

Implement that and your agent is plugged in. There is already a `RecordedSource`
(offline, replays known findings) and a `PaperclipSource` (shells out to the
Paperclip CLI) behind it, so the swap is a swap and not a rewrite.

### The return types are the answer to your §12.1

You did not settle whether interpretation should be an LLM summary or a
quantified system. refute's position is **quantified**, and the types exist:

```python
@dataclass(frozen=True)
class Evidence:
    constant: str
    value: float
    units: str
    source: str        # DOI or stable identifier
    quote: str         # the sentence the number came from
    derived: bool      # computed from reported quantities, not read off
    assumption: str    # REQUIRED when derived — construction fails without it
```

A summary cannot be checked. A number with its units, its source, and the
sentence it came from can. And a *derived* number that does not state its
assumption is indistinguishable from a measured one, which is why the dataclass
refuses to construct.

**But the complement matters more, and this is the piece I would most want you
to steal:**

```python
class BlockedReason(Enum):
    NOT_REPORTED       # nobody publishes it. The survivorship class.
    UNITS_MISMATCH     # published, but as a different quantity.
    ASSAY_SPECIFIC     # published, but instrument-relative, not transferable.
    CONTEXT_DEPENDENT  # the constant is ill-posed as a scalar.
    NOT_YET_SEARCHED   # no claim either way. The honest default.
```

Your §5 says the corpus is solved and traversal is the problem. Agreed — but the
sharper statement is that **the hard part is knowing what you failed to find.**
"We could not find X" and "we did not look for X" support completely different
conclusions, and a system that conflates them is worthless for the argument it
is meant to support. So `Blocked` *refuses* to claim `NOT_REPORTED` without a
recorded query that came back empty.

That taxonomy is domain-agnostic and is probably the most transferable thing in
this repository.

### There is already a work queue

Every scaffold declares its structure, leaves its numbers `None`, and ships the
query that would find them. Right now:

| Scaffold | Missing constants |
|---|---|
| `traction_force` | 6 |
| `scar_in_a_jar` | 7 |
| `cell_derived_matrix` | 6 |
| `fibrosis_on_chip` | 6 |
| `bleomycin_lung` | 6 |
| `stiffness_drift` | 4 |
| **total** | **35** |

All six carry a `paperclip_query`. `refute assays` prints them. That is a
35-item, pre-specified retrieval task with a built-in grader — your agent's
first benchmark, available before it can do anything else.

And the gate is enforced in code, not in a docstring: a protocol whose constants
are missing **cannot produce a score**. `score_design` refuses. So the catalogue
can grow without the claims growing, which is what makes any of this portable.

---

## 6. Your open questions, answered where refute has an answer

| | Your question | Position |
|---|---|---|
| §12.1 | Summary or quantified? | **Quantified.** `Evidence` + `Blocked` above. A summary cannot be graded; a number can. |
| §12.2 | Same agent or separate? | Already a *variable*, not a decision — `harness.py` ships SingleShot / SelfCritique / Checklist and no harness ever sees the twin. **Warning:** hold the extractor constant while you vary the harness, or you cannot tell design quality from parsing fidelity. That confound is the reason this is a knob and not a preference. |
| §12.3 | Skill vs tool vs MCP? | Not a hard call. There is already a CLI, a gym-style env (`RefuteEnv`), and an HTTP endpoint (`api.py`, `/score`, keyless, no model call). MCP is a thin wrapper over the HTTP surface — pick MCP for the agent-facing skin and keep HTTP underneath. |
| §12.4 | How much idea generation? | **Recommend: none.** It is the murkiest part and the least verifiable, and the generator must never verify itself. Prune at design time, where there is a ground truth to prune against. Your call, but the leverage is not at ideation. |
| §12.5 | How do we simulate? | **Done.** `score_design`. |

---

## 7. Two parallel workstreams, nobody blocked

Your §13 wants a split where neither person waits. The seam in §5 gives you one
cleanly, because both sides talk to a typed interface rather than to each other.

**Workstream A — grounding (your half)**
1. Hypothesis → the quantities its verdict depends on.
2. Retrieve against Paperclip.
3. Return `Evidence` for what was found, `Blocked` for what was not, with the
   query recorded.
4. Grade yourself on the 35-constant queue.

**Workstream B — the join (refute half)**
1. **Requirements extraction** — given a design, emit the list of quantities the
   verdict depends on. Currently hand-written per scaffold in `tier1.py`;
   generalising it is the real join point and neither project has it yet.
2. `PRIMARY` provenance tag — the evidence model can express LITERATURE and
   DERIVED but not "counted off primary records", which is a gap.
3. MCP surface over the existing HTTP endpoint.

They meet at `CalibrationSource` and `Evidence`. Agree those two shapes in the
first hour and then do not talk until integration.

---

## 8. What refute needs from you, and one thing you should know

**Needs:** a Paperclip credential (owner action, nobody else can create it), and
agreement on the two type shapes above.

**Should know:** `cases/exp4/` holds unpublished MPhil research data. The owner
is content to publish the results, but this is supervised work and the PI has
not been asked — so **the exp4 data does not move into a shared repo until that
conversation happens.** Everything else here is unblocked, and Workstream A does
not depend on it at all: the 35-constant queue is entirely literature-side.

---

## 9. The framing for Track B

The dataset is not "papers about fibrosis". It is **what the literature does and
does not record about experimental failure** — 35 constants, each labelled found
or blocked, each blocked one carrying a typed reason and the query that came back
empty. That is a claim about publishing practice, backed by a measurement.

Your retrieval agent is the instrument that builds it at scale. refute is the
thing that proves the constants are right, by checking whether a twin built from
them predicts an experiment we already know the answer to.

One of you brought a verification agent; the other brought a simulator. The
reason they fit is that verification without simulation passes Experiment 4.
