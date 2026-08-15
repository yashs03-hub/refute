"""Recovering constants papers report without meaning to.

The failure constants are not as absent as a keyword search suggests. They are
mostly *unstated but present*, encoded as arithmetic between things the paper
does report - and recoverable by differencing them.

The canonical case, and the one that makes this worth building:

    Methods:  "n = 12 per group"
    Table 2:  "n = 9"

Nobody writes "we lost 25% of our units". That number is sitting in the gap
between two sentences, and no keyword finds it because it was never written
down. §6's 0/10 measured how often a constant is STATED. It did not measure how
often it is RECOVERABLE, and those are very different quantities.

The one that matters most for tier 1 is `N_BY_TIMEPOINT`. A hazard model needs
failure as a function of time, not a single endpoint rate - Experiment 4's own
lysis model is weakly identified precisely because it rests on one endpoint plus
a qualitative note. Any paper with a time course and per-timepoint group sizes
contains that curve, whether or not its authors noticed.

RULES OF THE HOUSE, because inference is exactly where a calibration harness
starts inventing things:

1. Every rule produces `Evidence(derived=True, ...)`, which the evidence layer
   refuses to construct without a stated assumption. An inferred constant can
   never be mistaken for a measured one.
2. Every rule declares what would INVALIDATE it. A rule that cannot be wrong is
   not doing any work.
3. Inference is offered, never applied silently. A human confirms the reading of
   a specific paper; the rule only says where to look and what the arithmetic is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .evidence import Evidence


@dataclass(frozen=True)
class InferenceRule:
    """A way to recover a constant nobody wrote down."""

    key: str
    recovers: str                  # the constant it produces
    needs: tuple[str, ...]         # what the paper must report
    derivation: str                # the arithmetic, in words
    invalidated_by: tuple[str, ...]  # when the reading is wrong
    why: str                       # why the paper never states it directly

    def describe(self) -> str:
        lines = [
            f"{self.key}  ->  {self.recovers}",
            f"  needs       : {'; '.join(self.needs)}",
            f"  derivation  : {self.derivation}",
            f"  why unstated: {self.why}",
            "  wrong when  :",
        ]
        lines += [f"    - {v}" for v in self.invalidated_by]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------

N_DRIFT = InferenceRule(
    key="n_drift",
    recovers="attrition rate",
    needs=("group size declared in methods", "group size used in results"),
    derivation="attrition = (n_declared - n_analysed) / n_declared",
    invalidated_by=(
        "the results report a deliberate subgroup, not the surviving units",
        "the two numbers refer to different assays on the same cohort",
        "units were pooled (e.g. 3 wells combined per lysate) rather than lost",
    ),
    why=(
        "attrition is not a result, so it has no home in the paper. The methods "
        "state the plan and the results state what was analysed; the difference "
        "is nobody's section."
    ),
)

VARIABLE_N = InferenceRule(
    key="variable_n",
    recovers="attrition rate (lower bound)",
    needs=('a range rather than a number, e.g. "n = 5-8 per group"',),
    derivation="attrition >= (n_max - n_min) / n_max",
    invalidated_by=(
        "the range spans different conditions with different intended sizes",
        "the range is across independent experiments, not within one",
    ),
    why=(
        "a range is how authors report loss without naming it. It is usually the "
        "only trace left."
    ),
)

N_BY_TIMEPOINT = InferenceRule(
    key="n_by_timepoint",
    recovers="failure as a function of time (a hazard curve)",
    needs=("group sizes reported per timepoint, in a table or figure legend",),
    derivation=(
        "S(t) = n(t) / n(0), then fit a survival function. Two timepoints give a "
        "rate; three or more constrain its SHAPE, which one endpoint cannot."
    ),
    invalidated_by=(
        "animals or wells were sacrificed at each timepoint by design, so the "
        "decline is planned rather than failure - the single most likely "
        "misreading, and it inverts the conclusion",
        "different timepoints were run as separate cohorts",
    ),
    why=(
        "the curve is a by-product of a time course. Authors report n so the "
        "statistics are checkable, not to describe attrition."
    ),
)

EXCLUSION_WITHOUT_RATE = InferenceRule(
    key="exclusion_without_rate",
    recovers="confirmation the failure mode EXISTS (not its rate)",
    needs=('exclusion criteria naming a failure mode, e.g. "constructs that '
           'detached were excluded"',),
    derivation=(
        "none - this recovers a mechanism, not a number. It moves the constant "
        "from 'nobody mentions this happening' to 'it happens often enough to "
        "need a rule, and the rate is unstated'."
    ),
    invalidated_by=(
        "the criterion is boilerplate copied between protocols and no exclusion "
        "actually occurred",
    ),
    why=(
        "a pre-specified exclusion criterion is evidence the authors expected the "
        "failure. That is weaker than a rate and much stronger than silence, and "
        "the existing taxonomy had nowhere to put it."
    ),
)

SEM_TO_SD = InferenceRule(
    key="sem_to_sd",
    recovers="within-group SD (the precision floor)",
    needs=("SEM reported", "the n it was computed from"),
    derivation="SD = SEM * sqrt(n)",
    invalidated_by=(
        "the n quoted is experiments, not units - a very common mismatch",
        "the error bar is a confidence interval or SD already, mislabelled",
    ),
    why=(
        "SEM is preferred because it looks smaller. The SD is what a power "
        "calculation needs, and it is one multiplication away."
    ),
)

COUNT_PHRASING = InferenceRule(
    key="count_phrasing",
    recovers="a failure rate, stated but never converted",
    needs=('a count in prose, e.g. "3 of 24 constructs ruptured"',),
    derivation="rate = numerator / denominator",
    invalidated_by=(
        "the denominator is a different population from the analysed one",
    ),
    why=(
        "it IS reported - just not as a number a search for 'rate' or a "
        "percentage would ever match. This is a search-strategy failure rather "
        "than a reporting one."
    ),
)

RULES: tuple[InferenceRule, ...] = (
    N_DRIFT,
    N_BY_TIMEPOINT,
    VARIABLE_N,
    EXCLUSION_WITHOUT_RATE,
    SEM_TO_SD,
    COUNT_PHRASING,
)

BY_KEY = {r.key: r for r in RULES}


# ---------------------------------------------------------------------------
# Derivations. Each returns Evidence(derived=True), so the evidence layer
# enforces that the assumption is stated.
# ---------------------------------------------------------------------------


def attrition_from_n_drift(
    n_declared: int, n_analysed: int, source: str, quote: str, constant: str = "attrition_rate"
) -> Evidence:
    if n_declared <= 0:
        raise ValueError("n_declared must be positive")
    if n_analysed > n_declared:
        raise ValueError(
            f"n_analysed ({n_analysed}) exceeds n_declared ({n_declared}) - this "
            "is not attrition, and the two numbers describe different things"
        )
    return Evidence(
        constant=constant,
        value=(n_declared - n_analysed) / n_declared,
        units="fraction",
        source=source,
        quote=quote,
        derived=True,
        assumption=(
            f"n dropped {n_declared}->{n_analysed} between methods and results, "
            "and that drop is loss rather than a deliberate subgroup or pooling"
        ),
    )


def sd_from_sem(sem: float, n: int, source: str, quote: str, constant: str) -> Evidence:
    if n < 1:
        raise ValueError("n must be at least 1")
    return Evidence(
        constant=constant,
        value=sem * math.sqrt(n),
        units="same as SEM",
        source=source,
        quote=quote,
        derived=True,
        assumption=(
            f"SD = SEM*sqrt(n) with n={n}, and that n counts UNITS rather than "
            "independent experiments"
        ),
    )


def survival_from_n_by_timepoint(
    n_by_time: dict[float, int], source: str, quote: str, constant: str = "survival_curve"
) -> list[Evidence]:
    """One Evidence per timepoint: S(t) = n(t)/n(0).

    Returns a curve rather than a scalar because that is the point - a hazard's
    SHAPE needs three or more timepoints, and a single endpoint is what left
    Experiment 4's own lysis model weakly identified.
    """
    if not n_by_time:
        raise ValueError("no timepoints given")
    times = sorted(n_by_time)
    n0 = n_by_time[times[0]]
    if n0 <= 0:
        raise ValueError("the first timepoint must have a positive n")

    out: list[Evidence] = []
    for t in times[1:]:
        n_t = n_by_time[t]
        if n_t > n0:
            raise ValueError(
                f"n rose from {n0} to {n_t} at t={t} - units were added, so this "
                "is not a survival curve"
            )
        out.append(
            Evidence(
                constant=f"{constant}@{t:g}h",
                value=n_t / n0,
                units="fraction surviving",
                source=source,
                quote=quote,
                derived=True,
                assumption=(
                    f"n fell {n0}->{n_t} by t={t:g} h through FAILURE, not through "
                    "planned sacrifice at that timepoint - if animals or wells "
                    "were harvested by design, this reading inverts"
                ),
            )
        )
    return out


def rate_from_counts(
    numerator: int, denominator: int, source: str, quote: str, constant: str
) -> Evidence:
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator > denominator:
        raise ValueError(f"{numerator} of {denominator} is not a rate")
    return Evidence(
        constant=constant,
        value=numerator / denominator,
        units="fraction",
        source=source,
        quote=quote,
        derived=True,
        assumption=(
            f"{numerator}/{denominator} refers to the analysed population, not a "
            "different denominator elsewhere in the paper"
        ),
    )


# ---------------------------------------------------------------------------
# What to grep for. These find the SHAPE of an unstated constant, which is the
# whole trick: you cannot search for a number nobody wrote.
# ---------------------------------------------------------------------------

GREP_PATTERNS: dict[str, tuple[str, ...]] = {
    "n_drift": (
        r"n *= *[0-9]+",
        r"[0-9]+ (animals|mice|rats|wells|constructs|chips|gels) per (group|arm|condition)",
    ),
    "n_by_timepoint": (
        r"n *= *[0-9]+ *(at|on) *(day|d|week|h) *[0-9]+",
        r"(day|week) *[0-9]+ *\(n *= *[0-9]+\)",
    ),
    "variable_n": (
        r"n *= *[0-9]+ *[-–] *[0-9]+",
    ),
    "exclusion_without_rate": (
        r"(excluded|removed|discarded) (from|if|when|due)",
        r"(detached|delaminated|ruptured|contaminated|failed to (form|polymeri))",
        r"humane endpoint|euthanas|welfare",
    ),
    "sem_to_sd": (
        r"(mean|shown) *[±\+/-]* *SEM",
        r"standard error of the mean",
    ),
    "count_phrasing": (
        r"[0-9]+ (of|/) *[0-9]+ (animals|mice|wells|constructs|chips|samples)",
        r"[0-9]+ (animals|mice|wells|constructs) (died|were lost|detached|ruptured)",
    ),
}


def patterns_for(rule_key: str) -> tuple[str, ...]:
    if rule_key not in GREP_PATTERNS:
        raise KeyError(f"no grep patterns for '{rule_key}'. Known: {sorted(GREP_PATTERNS)}")
    return GREP_PATTERNS[rule_key]


def summary() -> str:
    lines = [
        "Constants papers report without meaning to.",
        "",
        "A keyword search finds constants that were STATED. These recover ones",
        "that were not - by differencing what the same paper says in different",
        "places. §6's 0/10 measured how often a constant is stated; it did not",
        "measure how often it is recoverable, and those are different numbers.",
        "",
    ]
    for r in RULES:
        lines.append(r.describe())
        lines.append("")
    lines.append(
        "Every rule yields Evidence(derived=True), which cannot be constructed\n"
        "without a stated assumption - so an inferred constant can never be\n"
        "mistaken for a measured one. Rules are offered, never applied silently:\n"
        "a human confirms the reading of a specific paper."
    )
    return "\n".join(lines)
