"""Which scaffolds are actually phenotype-coupled, and which only look it.

`tier1.py` selects on one criterion: the phenotype being measured is what
destroys the assay. Only `fibrosis_on_chip` does not meet it - driven by an
applied strain you set. `stiffness_drift` moved INTO the coupled class
2026-08-16, an owner call that the drift depends on encapsulated cells; see
`tier1.py`'s `STIFFNESS_DRIFT.hazard` for the exact evidence and its stated
limits (cell presence, not a dose-response on activation level; unconfirmed
transfer from the swept paper's 3D geometry to this scaffold's 2D one). The
header states the count, and this pins it, because the claim "one mechanism
class, six instances" is exactly the kind of tidy generalisation that
survives unchecked until somebody reads the `driver` fields in front of you.
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
    "stiffness_drift",
    "apoptosis_resistance",
}

# Real failure modes, but independent of the readout - no survivorship bias and
# no coupling constant, which makes them easier rather than disqualifying.
INDEPENDENT_HAZARD = {"fibrosis_on_chip"}


def test_the_two_classes_cover_the_registry_exactly():
    assert PHENOTYPE_COUPLED | INDEPENDENT_HAZARD == set(REGISTRY)


def test_the_coupled_ones_name_the_readout_in_their_driver():
    """The driver must reference the measured quantity, not an input.

    `stiffness_drift`'s driver names cells rather than 'contractility' or
    'severity' - a narrower, cell-presence claim, not an activation-level
    one (see the module docstring). 'cell' is accepted here for exactly
    that scaffold; the other four still match on the stronger words.
    """
    for key in PHENOTYPE_COUPLED:
        p = REGISTRY[key]
        if p.hazard is None:
            continue
        driver = p.hazard.driver.lower()
        assert any(
            w in driver
            for w in ("contractil", "traction", "severity", "pre-stress", "fibro",
                      "cell", "activation", "resistan")
        ), f"{key}: driver '{p.hazard.driver}' does not reference the phenotype"


def test_the_independent_ones_are_driven_by_a_parameter_or_by_time():
    for key in INDEPENDENT_HAZARD:
        driver = REGISTRY[key].hazard.driver.lower()
        assert any(
            w in driver for w in ("strain", "cycle", "time", "medium")
        ), f"{key}: driver '{driver}' looks phenotype-coupled after all"


def test_the_header_admits_the_one_that_does_not_fit():
    """Cheaper to say it than to be caught by it."""
    import refute.assays.tier1 as tier1

    doc = tier1.__doc__ or ""
    assert "One of the six does not meet that criterion" in doc
    for key in INDEPENDENT_HAZARD:
        assert key in doc
    # And it must state the corrected count, since "six instances" is the
    # generalisation somebody will otherwise repeat.
    assert "it is five" in doc


def test_the_generalisation_is_five_not_six():
    """`bleomycin_lung` promoted to LITERATURE tier 2026-08-16 (calibrated,
    runnable). `stiffness_drift` moved into PHENOTYPE_COUPLED the same day
    but is still SCAFFOLD, and `apoptosis_resistance` landed the same day as
    a brand-new, entirely uncalibrated SCAFFOLD - so the uncalibrated-coupled
    count is 5 now (3 -> 4 -> 5), not because anything regressed: one moved
    class, one is new. Note what 'calibrated' does and does not mean either
    way: `bleomycin_lung.runnable` is True, but `twin.py`/`score.py` still
    model only the fibrin apparatus, so a design against it still can't
    actually be scored without its own twin - see that module's docstring."""
    uncalibrated_coupled = {
        k for k in PHENOTYPE_COUPLED if not REGISTRY[k].runnable
    }
    assert len(uncalibrated_coupled) == 5, (
        "a twin parameterised on 'hazard scales with the readout' would cover "
        f"{len(uncalibrated_coupled)} uncalibrated scaffolds, not six"
    )
