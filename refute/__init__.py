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

import importlib

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


# The layers above the twin: the seam that turns findings into requirements, the
# gate that routes on them, and the pipeline that walks a design through both.
#
# Enumerated rather than star-imported. A star import re-exports whatever a
# module happens to define today, so the package's surface would change every
# time somebody added a helper, and nothing would say which names were meant to
# be public.
#
# `pipeline.run` is exported as `run_pipeline`. `refute run` on the command line
# is the agent loop - propose, simulate, revise - and `refute.run` would be the
# resolve-gate-simulate-advise walk, which is a different thing under the same
# word. A caller who imports the wrong one gets a confusing error at best.
_LAYERED: tuple[tuple[str, tuple[str | tuple[str, str], ...]], ...] = (
    ("resolve", ("FixtureResolver", "Requirement", "Resolution", "ResolutionSet",
                 "Resolver")),
    ("adapt", ("RecordedResolver",)),
    ("gate", ("Route", "RouteDecision", "route_design")),
    ("pipeline", ("PipelineResult", ("run_pipeline", "run"))),
    ("handoff", ("Finding", "GapReason", "Handoff", "OpenItem")),
    ("intake", ("AssaySelection", "Intake", "intake", "select_assay")),
)


def _export_layers() -> None:
    """Bind every name in `_LAYERED` that exists, and record it in `__all__`.

    A function rather than a module-level loop so the bookkeeping variables do
    not end up as attributes of the package.
    """
    for module_name, exports in _LAYERED:
        try:
            module = importlib.import_module(f".{module_name}", __name__)
        except ModuleNotFoundError as exc:
            # Only the absence of this module is survivable, and only because
            # these land one at a time: importing `refute` must not fail because
            # the next layer has not been written yet. A ModuleNotFoundError
            # raised from INSIDE the module - a missing third-party dependency,
            # a typo in one of its own imports - is a real failure wearing the
            # same exception type, and swallowing it would turn a broken install
            # into a package that imports cleanly and is quietly missing half
            # its names.
            if exc.name != f"{__name__}.{module_name}":
                raise
            continue
        for entry in exports:
            name, attribute = entry if isinstance(entry, tuple) else (entry, entry)
            # No default. A name missing from a module that exists means this
            # list has drifted from the code, which is worth an import error.
            globals()[name] = getattr(module, attribute)
            __all__.append(name)


_export_layers()
