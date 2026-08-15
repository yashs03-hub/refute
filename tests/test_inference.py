"""Recovering constants papers report without meaning to.

The point of this module is that §6's 0/10 measured how often a failure constant
is STATED, not how often it is RECOVERABLE. These tests pin the arithmetic and,
more importantly, the guards - inference is exactly where a calibration harness
starts inventing things.
"""

from __future__ import annotations

import math

import pytest

from refute.assays.inference import (
    BY_KEY,
    GREP_PATTERNS,
    RULES,
    attrition_from_n_drift,
    patterns_for,
    rate_from_counts,
    sd_from_sem,
    summary,
    survival_from_n_by_timepoint,
)


# --- the rules describe themselves honestly --------------------------------

def test_every_rule_says_what_would_make_it_wrong():
    """A rule that cannot be wrong is not doing any work."""
    for r in RULES:
        assert r.invalidated_by, f"{r.key} claims it can never be misread"
        assert r.derivation
        assert r.why, f"{r.key} must say why the paper never states it directly"


def test_every_rule_has_grep_patterns():
    """A rule you cannot search for is a rule nobody will apply."""
    for r in RULES:
        assert patterns_for(r.key), r.key


def test_patterns_for_rejects_an_unknown_rule():
    with pytest.raises(KeyError, match="no grep patterns"):
        patterns_for("wishful_thinking")


# --- n-drift: the canonical case -------------------------------------------

def test_n_drift_recovers_an_attrition_rate_nobody_wrote_down():
    ev = attrition_from_n_drift(
        n_declared=12, n_analysed=9,
        source="10.1/x", quote="n = 12 per group ... Table 2: n = 9",
    )
    assert ev.value == pytest.approx(0.25)
    assert ev.derived is True


def test_a_derived_value_must_carry_its_assumption():
    """Enforced by the evidence layer, and the reason inference is safe here:
    an inferred constant can never be mistaken for a measured one."""
    ev = attrition_from_n_drift(12, 9, "10.1/x", "q")
    assert ev.assumption
    assert "deliberate subgroup" in ev.assumption or "pooling" in ev.assumption
    assert ev.provenance.startswith("DERIVED")


def test_n_rising_is_refused_because_it_is_not_attrition():
    with pytest.raises(ValueError, match="not attrition"):
        attrition_from_n_drift(n_declared=9, n_analysed=12, source="s", quote="q")


def test_zero_declared_is_refused():
    with pytest.raises(ValueError):
        attrition_from_n_drift(n_declared=0, n_analysed=0, source="s", quote="q")


def test_no_drift_is_zero_attrition_not_an_error():
    assert attrition_from_n_drift(12, 12, "s", "q").value == 0.0


# --- n by timepoint: the one that could unblock tier 1 ---------------------

def test_n_by_timepoint_recovers_a_curve_not_a_scalar():
    """A hazard's SHAPE needs three or more timepoints. One endpoint is what
    left Experiment 4's own lysis model weakly identified."""
    evs = survival_from_n_by_timepoint(
        {0: 12, 72: 11, 168: 8, 240: 5}, source="10.1/y", quote="Table 1",
    )
    assert len(evs) == 3
    assert evs[0].value == pytest.approx(11 / 12)
    assert evs[-1].value == pytest.approx(5 / 12)
    # Monotone decreasing, as a survival function must be.
    assert [e.value for e in evs] == sorted((e.value for e in evs), reverse=True)


def test_the_survival_assumption_names_the_inverting_misreading():
    """Planned sacrifice at each timepoint looks identical to attrition and
    means the opposite. If the assumption does not say so, the rule is unsafe."""
    ev = survival_from_n_by_timepoint({0: 10, 24: 7}, "s", "q")[0]
    assert "sacrifice" in ev.assumption
    assert "inverts" in ev.assumption


def test_n_rising_across_timepoints_is_refused():
    with pytest.raises(ValueError, match="not a survival curve"):
        survival_from_n_by_timepoint({0: 5, 24: 9}, "s", "q")


def test_empty_timepoints_are_refused():
    with pytest.raises(ValueError):
        survival_from_n_by_timepoint({}, "s", "q")


# --- SEM -> SD --------------------------------------------------------------

def test_sd_from_sem_is_the_precision_floor_one_multiplication_away():
    ev = sd_from_sem(sem=0.5, n=9, source="s", quote="mean ± SEM, n = 9",
                     constant="within_arm_sd")
    assert ev.value == pytest.approx(0.5 * math.sqrt(9))


def test_the_sem_assumption_names_the_common_mismatch():
    """n counting experiments rather than units is the usual way this goes
    wrong, and it inflates the recovered SD."""
    ev = sd_from_sem(0.5, 9, "s", "q", "sd")
    assert "independent experiments" in ev.assumption


# --- counts stated but never converted -------------------------------------

def test_rate_from_counts_catches_what_a_percentage_search_misses():
    ev = rate_from_counts(3, 24, "s", "3 of 24 constructs ruptured", "p_rupture")
    assert ev.value == pytest.approx(0.125)


def test_a_numerator_above_the_denominator_is_refused():
    with pytest.raises(ValueError, match="not a rate"):
        rate_from_counts(30, 24, "s", "q", "p")


# --- the exclusion rule recovers a mechanism, not a number -----------------

def test_exclusion_rule_is_explicit_that_it_yields_no_number():
    r = BY_KEY["exclusion_without_rate"]
    assert "not its rate" in r.recovers or "not a number" in r.derivation
    # It must say why that is still worth more than silence.
    assert "stronger than silence" in r.why


# --- the framing ------------------------------------------------------------

def test_summary_states_the_distinction_the_module_exists_for():
    text = summary()
    assert "stated" in text.lower() and "recoverable" in text.lower()
    assert "derived=True" in text
    for r in RULES:
        assert r.key in text


def test_grep_patterns_are_valid_regexes():
    import re

    for key, pats in GREP_PATTERNS.items():
        for p in pats:
            re.compile(p)  # must not raise
