"""Reference designs, so an agent's score means something.

"The agent reached 97% testable" is not a result on its own. Ninety-seven per
cent of what a competent person would have managed? Of what is possible at all?
Without a reference point the number only says the agent beat a design that
scored zero, which is a low bar and the wrong comparison.

Four references, each answering a different question:

    AS_RUN   what actually happened, and the twin's calibration target
    NAIVE    what someone does who has not thought about the apparatus
    EXPERT   the best design available on one plate, written knowing everything
             Experiment 4 taught - the CEILING
    CEILING  EXPERT with the plate limit lifted, to show what the constraint
             costs rather than only that it binds

The important one is EXPERT. It is written with hindsight the agent is denied:
its author knows about the fibrinolysis, knows contraction is over by 24 h, and
knows the measurement precision. If EXPERT also fails to reach 80% power, then
the infeasibility verdict is a fact about the apparatus rather than a verdict on
any particular agent - and that is the finding this project actually reports.

None of these are model output. They are hand-written, and their reasoning is
stated so a reader can disagree with the choices rather than trust them.
"""

from __future__ import annotations

from dataclasses import dataclass

from .calibration import PLATE_WELLS
from .design import EXPERIMENT_4_AS_RUN, DesignSpec

# ---------------------------------------------------------------------------
# NAIVE - no thought given to the apparatus
#
# Not a straw man. This is the standard shape of a first pass: every condition
# gets an arm because every condition is interesting, imaging happens when
# somebody is in the lab, and the endpoint is the round number furthest away.
# It is wrong in ways that are invisible until the plate is cast.
# ---------------------------------------------------------------------------

NAIVE = DesignSpec(
    conditions=["N-SS", "N-T", "N-CM", "N-CM+T"],
    replicates_per_condition=3,
    imaging_times_h=[168, 240],           # nothing before treatment at all
    treatment_time_h=120.0,
    endpoint_time_h=240.0,
    antifibrinolytic=False,
    normalise_to_own_baseline=False,       # group means, so heterogeneity stays in
    locked_imaging_protocol=False,         # handheld whole-plate frames
    anticipates_scaffold_failure=False,
    rationale=(
        "Four arms because all four comparisons are interesting; Day 10 because "
        "longer is more contraction; photograph the plate at the end. Every "
        "choice here is defensible in the abstract and wrong on this apparatus."
    ),
)

# ---------------------------------------------------------------------------
# EXPERT - the ceiling on one plate, written with full hindsight
#
# Every choice below is a lesson Experiment 4 taught, and the agent is given
# none of them in its brief:
#
#   two arms      the headline contrast is N-T vs N-CM+T; the other two arms
#                 cost 6 wells and answer a question nobody asked
#   n=6           the whole plate, spent on the comparison that matters
#   aprotinin     fibrinolysis is what destroyed the treatment window
#   Day 7 end     inside the observed survival window, not past it
#   6 h imaging   contraction is ~94% done by 24 h, so the kinetics are only
#                 identifiable before then
#   own baseline  per-well ratios; between-well spread is 0.60-0.96
#   locked rig    handheld frames segmented ~1 in 10
# ---------------------------------------------------------------------------

EXPERT = DesignSpec(
    conditions=["N-T", "N-CM+T"],
    replicates_per_condition=6,
    imaging_times_h=[2, 6, 12, 24, 48, 96, 120, 168],
    treatment_time_h=120.0,
    endpoint_time_h=168.0,
    antifibrinolytic=True,
    antifibrinolytic_agent="aprotinin 200 KIU/mL in the fibrin mix",
    normalise_to_own_baseline=True,
    locked_imaging_protocol=True,
    anticipates_scaffold_failure=True,
    rationale=(
        "The best plate available, written knowing what Experiment 4 found: "
        "narrow to the headline contrast, spend all 12 wells on it, protect the "
        "scaffold, end inside the survival window, and sample early enough to "
        "identify the contraction curve. If this still cannot answer the "
        "question, no design on one plate can."
    ),
)

# ---------------------------------------------------------------------------
# CEILING - EXPERT with the apparatus constraint lifted
#
# Deliberately over-capacity, and it will say so. Included to separate two
# claims that are easy to conflate: "this design is bad" and "one plate is not
# enough". Scoring it shows what the constraint costs, not merely that it binds.
#
# The twin is NOT calibrated beyond one plate - there is no data on between-cast
# or between-plate batch effects - so this number is an optimistic bound, and
# `over_plate_capacity` fires to say so.
# ---------------------------------------------------------------------------

CEILING = EXPERT.model_copy(
    update={
        "replicates_per_condition": 60,
        "rationale": (
            "EXPERT with replication the apparatus cannot hold, to show what the "
            "one-plate limit costs. Over-capacity by design; the twin has no "
            "between-plate calibration, so treat this as an optimistic bound."
        ),
    }
)

AS_RUN = EXPERIMENT_4_AS_RUN


@dataclass(frozen=True)
class Baseline:
    key: str
    design: DesignSpec
    question: str


BASELINES: tuple[Baseline, ...] = (
    Baseline("as_run", AS_RUN, "what actually happened"),
    Baseline("naive", NAIVE, "no thought given to the apparatus"),
    Baseline("expert", EXPERT, "the best plate available, with full hindsight"),
    Baseline("ceiling", CEILING, "the same design, plate limit lifted"),
)


def get(key: str) -> Baseline:
    for b in BASELINES:
        if b.key == key:
            return b
    raise KeyError(f"unknown baseline '{key}'. Known: {', '.join(b.key for b in BASELINES)}")


def sanity_check() -> None:
    """Guard the properties these references exist to have.

    A baseline set that silently drifted - EXPERT overflowing the plate, NAIVE
    accidentally being reasonable - would make every comparison against it
    meaningless, and the drift would not be visible in any score.
    """
    assert EXPERT.total_wells == PLATE_WELLS, "EXPERT must spend exactly one plate"
    assert NAIVE.total_wells <= PLATE_WELLS, "NAIVE must be a plate someone could cast"
    assert not CEILING.fits_plate(PLATE_WELLS), "CEILING must exceed the apparatus"
    # NAIVE must be worse than EXPERT in every respect the twin can see, or it
    # is not a lower reference point.
    assert not NAIVE.antifibrinolytic and EXPERT.antifibrinolytic
    assert not NAIVE.locked_imaging_protocol and EXPERT.locked_imaging_protocol
    assert not NAIVE.normalise_to_own_baseline and EXPERT.normalise_to_own_baseline
