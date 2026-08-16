"""Which scaffolds are actually phenotype-coupled, and which only look it.

`tier1.py` selects on one criterion: the phenotype being measured is what
destroys the assay. Two of the six do not meet it - `fibrosis_on_chip` is driven
by an applied strain you set, `stiffness_drift` by elapsed time. The header now
says so, and this pins it, because the claim "one mechanism class, six
instances" is exactly the kind of tidy generalisation that survives unchecked
until somebody reads the `driver` fields in front of you.
"""

from __future__ import annotations

from refute.assays import REGISTRY

# The property that matters: units fail BECAUSE of how strongly they responded,
# so the survivors are biased against the effect being measured.
PHENOTYPE_COUPLED = {
    "fibrin_contracture",
    "traction_force",
    "scar_in_a_jar",
    "cell_derived_matrix",
    "bleomycin_lung",
}

# Real failure modes, but independent of the readout - no survivorship bias and
# no coupling constant, which makes them easier rather than disqualifying.
INDEPENDENT_HAZARD = {"fibrosis_on_chip", "stiffness_drift"}


def test_the_two_classes_cover_the_registry_exactly():
    assert PHENOTYPE_COUPLED | INDEPENDENT_HAZARD == set(REGISTRY)


def test_the_coupled_ones_name_the_readout_in_their_driver():
    """The driver must reference the measured quantity, not an input."""
    for key in PHENOTYPE_COUPLED:
        p = REGISTRY[key]
        if p.hazard is None:
            continue
        driver = p.hazard.driver.lower()
        assert any(
            w in driver
            for w in ("contractil", "traction", "severity", "pre-stress", "fibro")
        ), f"{key}: driver '{p.hazard.driver}' does not reference the phenotype"


def test_the_independent_ones_are_driven_by_a_parameter_or_by_time():
    for key in INDEPENDENT_HAZARD:
        driver = REGISTRY[key].hazard.driver.lower()
        assert any(
            w in driver for w in ("strain", "cycle", "time", "medium")
        ), f"{key}: driver '{driver}' looks phenotype-coupled after all"


def test_the_header_admits_the_two_that_do_not_fit():
    """Cheaper to say it than to be caught by it."""
    import refute.assays.tier1 as tier1

    doc = tier1.__doc__ or ""
    assert "Two of the six do not meet that criterion" in doc
    for key in INDEPENDENT_HAZARD:
        assert key in doc
    # And it must state the corrected count, since "six instances" is the
    # generalisation somebody will otherwise repeat.
    assert "it is four" in doc


def test_the_generalisation_is_four_not_six():
    """Was 4 of 5 uncalibrated; `bleomycin_lung` promoted to LITERATURE tier
    2026-08-16 (see `bleomycin_lung.py`), so it's 3 now. Note what promotion
    did NOT do: `bleomycin_lung.runnable` is True, but `twin.py`/`score.py`
    still model only the fibrin apparatus, so being 'calibrated' here means
    the registry's numbers are real, not that a design against it can
    actually be scored - see that module's docstring before reading this
    count as closer to a working four-instance twin than it is."""
    uncalibrated_coupled = {
        k for k in PHENOTYPE_COUPLED if not REGISTRY[k].runnable
    }
    assert len(uncalibrated_coupled) == 3, (
        "a twin parameterised on 'hazard scales with the readout' would cover "
        f"{len(uncalibrated_coupled)} uncalibrated scaffolds, not six"
    )
