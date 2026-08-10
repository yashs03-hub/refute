"""refute - benchmarking experiment-designing agents against experiments that failed.

Agentic-science evaluations are built almost entirely on published work. But
published work is filtered: the experiments that did not work are largely
absent from it. That makes the single most informative signal for judging an
experimental design - what actually goes wrong when you run it - the signal
that is missing from what these agents learned on.

This benchmark supplies one. Experiment 4 is a real fibrin gel contracture
assay whose treatment window was destroyed by cell-mediated fibrinolysis. It
was never published. Its measurements calibrate a digital twin, and an agent's
proposed plate is scored by simulating it - not by asking a language model
whether the design looks sensible.
"""

from .calibration import DEFAULT_PARAMS, TwinParams
from .design import EXPERIMENT_4_AS_RUN, DesignSpec, OutOfTwinScopeError
from .environment import RefuteEnv, StepResult
from .score import DesignScore, feedback_for_agent, score_design
from .twin import ExperimentTwin, PlateResult, WellResult

__all__ = [
    "DEFAULT_PARAMS",
    "EXPERIMENT_4_AS_RUN",
    "DesignScore",
    "DesignSpec",
    "ExperimentTwin",
    "OutOfTwinScopeError",
    "PlateResult",
    "RefuteEnv",
    "StepResult",
    "TwinParams",
    "WellResult",
    "feedback_for_agent",
    "score_design",
]
