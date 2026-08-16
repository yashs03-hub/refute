"""HTTP interface to the twin.

Three surfaces, deliberately separated by what they cost and what they can be
trusted with:

    POST /score        a DesignSpec        -> a score.   No model, no key, free.
    POST /score/text   prose               -> a score.   One extractor call.
    POST /run          a brief             -> the loop.   Agent + extractor calls.
    GET  /assays       registry status - which protocols may legitimately score.

`/score` is the one this project can fully vouch for: it is pure simulation, so
it can be exposed publicly without a credential anywhere near the process. That
matters beyond convenience - the scoring path stays available when a provider is
down, rate-limited, or unaffordable.

`/run` drives a paid model on the server's own credentials, so it is **disabled
unless `REFUTE_ENABLE_RUN=1`**. An open endpoint that spends someone's API
budget on request is not a default anyone should inherit by installing this.

Run it with:

    pip install -e ".[api]"
    uvicorn refute.api:app --reload
"""

from __future__ import annotations

import math
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from .bleomycin_design import BleomycinDesignSpec
from .design import DesignSpec, OutOfTwinScopeError
from .score import DesignScore, score_design
from .twins import get_twin

# A request may not ask for unbounded simulation. 400 plates is the CLI default
# and is enough for a stable power estimate; the ceiling exists so one caller
# cannot occupy the process indefinitely.
DEFAULT_N_SIMS = 400
MAX_N_SIMS = 5000

# `/run` spends real money per request on the server's credentials. Opt-in only.
RUN_ENABLED_ENV = "REFUTE_ENABLE_RUN"

app = FastAPI(
    title="refute",
    version="0.1.0",
    summary="Score a proposed experiment by simulating it, not by judging it.",
    description=__doc__,
)


# ---------------------------------------------------------------------------
# Wire formats
#
# `DesignScore` reports "no value" as `float('nan')` and `-1`, which are fine in
# Python and are not representable in JSON - `NaN` is not valid JSON and a
# sentinel `-1` would be read as a real count by any client that did not know
# the convention. Both become `null` at this boundary.
# ---------------------------------------------------------------------------


def _finite_or_none(x: float) -> float | None:
    return None if x is None or math.isnan(x) or math.isinf(x) else float(x)


class ScoreResponse(BaseModel):
    """What the twin says about a design."""

    power: float = Field(description="P(recover the injected treatment effect).")
    testable_rate: float = Field(
        description="P(enough surviving wells that any test can be run)."
    )
    mean_usable_wells: float
    mean_lysed_fraction: float = Field(
        description="Mean fraction of wells whose scaffold failed before the endpoint."
    )
    over_plate_capacity: bool
    identifies_contraction_kinetics: bool
    min_detectable_ratio_diff: float | None = Field(
        description="Smallest endpoint-ratio difference detectable at 80% power. "
        "null when the design left too little to estimate it."
    )
    replicates_needed: int | None = Field(
        description="Wells per arm the injected effect would actually need. "
        "null when it is not estimable."
    )
    n_conditions: int
    failed: bool = Field(description="power < 0.5.")
    infeasible_as_scoped: bool = Field(
        description="The replication required exceeds one plate. No change to "
        "timing or formulation recovers this - a finding, not a failure."
    )
    feasibility: str = Field(
        description="'feasible' | 'infeasible' | 'unestimable' | 'declined'. The "
        "last two are distinct from a low score: 'unestimable' means the design "
        "left too little to say what it would need, 'declined' means it assigned "
        "no wells at all."
    )
    declined: bool = Field(
        description="True if the design declines to run the experiment. Power and "
        "testability are then placeholders, not measurements - nothing was "
        "simulated. Declining can be the correct answer; compare `refute baselines`."
    )
    verdict_sensitive_to_assumption: bool = Field(
        description="True if this verdict does not survive the plausible range "
        "of an ASSUMED constant. Treat the numbers as one point in a span."
    )
    assumptions_in_play: list[str] = Field(
        description="Uncalibrated constants this design actually reaches."
    )
    power_range_under_assumptions: tuple[float, float] | None = Field(
        default=None,
        description="Power at the edges of those constants' plausible range.",
    )
    diagnoses: list[str] = Field(
        description="Consequences, never corrections: what went wrong, not what to add."
    )
    summary: str = Field(description="The CLI's human-readable rendering.")

    @classmethod
    def of(cls, score: Any) -> "ScoreResponse":
        mean_wells = getattr(score, "mean_usable_wells", getattr(score, "mean_animals_scored", 0.0))
        mean_lysed = getattr(score, "mean_lysed_fraction", 0.0)
        over_cap = getattr(score, "over_plate_capacity", getattr(score, "over_cohort_capacity", False))
        kinetics = getattr(score, "identifies_contraction_kinetics", False)
        min_diff = _finite_or_none(getattr(score, "min_detectable_ratio_diff", getattr(score, "min_detectable_effect_size", float("nan"))))

        return cls(
            power=score.power,
            testable_rate=score.testable_rate,
            mean_usable_wells=mean_wells,
            mean_lysed_fraction=mean_lysed,
            over_plate_capacity=over_cap,
            identifies_contraction_kinetics=kinetics,
            min_detectable_ratio_diff=min_diff,
            replicates_needed=(
                score.replicates_needed if score.replicates_needed > 0 else None
            ),
            n_conditions=getattr(score, "n_conditions", len(getattr(score, "conditions", []))),
            failed=score.failed,
            infeasible_as_scoped=getattr(score, "infeasible_as_scoped", False),
            feasibility=getattr(score, "feasibility", "unestimable"),
            declined=score.declined,
            verdict_sensitive_to_assumption=score.verdict_sensitive_to_assumption,
            assumptions_in_play=list(score.assumptions_in_play),
            power_range_under_assumptions=score.power_range_under_assumptions,
            diagnoses=list(score.diagnoses),
            summary=score.summary(),
        )


class ScoreRequest(BaseModel):
    assay: str = Field(default="fibrin_contracture", description="Assay key from TWINS registry.")
    design: dict[str, Any] | DesignSpec | BleomycinDesignSpec
    n_sims: int = Field(default=DEFAULT_N_SIMS, ge=1, le=MAX_N_SIMS)
    seed: int | None = Field(
        default=0, description="Fixed by default, so a score is reproducible."
    )


class TextScoreRequest(BaseModel):
    assay: str = Field(default="fibrin_contracture", description="Assay key from TWINS registry.")
    design_text: str = Field(min_length=1, description="A design, as prose.")
    n_sims: int = Field(default=DEFAULT_N_SIMS, ge=1, le=MAX_N_SIMS)
    seed: int | None = 0
    extractor: str | None = Field(
        default=None,
        description="Extractor model, e.g. 'openai:gpt-5.4-mini:low'. Hold this "
        "CONSTANT across designs being compared: varying it confounds design "
        "quality with parsing fidelity.",
    )


class TextScoreResponse(BaseModel):
    extracted: Any = Field(
        description="What the extractor read. Check this before trusting the score."
    )
    score: ScoreResponse


class RunRequest(BaseModel):
    agent: str = Field(
        default="openai:gpt-5.5:high", description="Model under test, provider:model:effort."
    )
    extractor: str | None = None
    n_sims: int = Field(default=DEFAULT_N_SIMS, ge=1, le=MAX_N_SIMS)
    revise: bool = Field(
        default=True, description="Run the consequence-feedback revision turn."
    )


class RunRound(BaseModel):
    design_text: str
    extracted: DesignSpec
    score: ScoreResponse


class RunResponse(BaseModel):
    agent: str
    extractor: str
    rounds: list[RunRound]
    tokens: str = Field(description="Token ledger for the request.")


class AssayStatus(BaseModel):
    key: str
    name: str
    status: str
    runnable: bool = Field(
        description="False for a scaffold: it will refuse to be scored."
    )
    missing_constants: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.exception_handler(OutOfTwinScopeError)
def _out_of_scope_handler(_request: Request, exc: OutOfTwinScopeError) -> JSONResponse:
    """422 with a machine-readable reason, on every endpoint that scores.

    Registered once rather than caught per-endpoint so no future endpoint can
    forget it and silently return a number instead. The `error` key makes this
    distinguishable from a schema-validation 422, which shares the status code
    but means something entirely different.
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": "out_of_twin_scope",
            "out_of_scope": exc.reasons,
            "detail": str(exc),
        },
    )


@app.get("/healthz", summary="Liveness. Calls nothing.")
def healthz() -> dict[str, Any]:
    return {"ok": True, "run_enabled": _run_enabled()}


@app.post("/score", response_model=ScoreResponse, summary="Score a design")
def post_score(req: ScoreRequest) -> ScoreResponse:
    """Simulate a design. No model is called and no credential is required."""
    twin = get_twin(req.assay)
    try:
        if isinstance(req.design, BaseModel):
            design = req.design
        else:
            design = twin.design_spec_type.model_validate(req.design)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ScoreResponse.of(
        twin.score_fn(design, n_sims=req.n_sims, seed=req.seed)
    )


@app.post(
    "/score/text", response_model=TextScoreResponse, summary="Extract prose, then score"
)
def post_score_text(req: TextScoreRequest) -> TextScoreResponse:
    """Read a design written in prose, then simulate it.

    Costs one extractor call. The extracted spec is returned alongside the
    score so a caller can see what was read - a low score that comes from a
    misread design is a parsing failure, and must be distinguishable from a
    design that genuinely does not work.
    """
    twin = get_twin(req.assay)
    spec = _extract(req.design_text, req.extractor, spec_type=twin.design_spec_type)
    score = twin.score_fn(spec, n_sims=req.n_sims, seed=req.seed)
    return TextScoreResponse(extracted=spec, score=ScoreResponse.of(score))


@app.post("/run", response_model=RunResponse, summary="The full loop (opt-in)")
def post_run(req: RunRequest) -> RunResponse:
    """Propose, score, then revise against consequence feedback.

    Disabled unless REFUTE_ENABLE_RUN=1, because it spends the server's own API
    budget per request.
    """
    if not _run_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                f"/run is disabled. It calls a paid model on this server's "
                f"credentials, so it must be enabled deliberately: set "
                f"{RUN_ENABLED_ENV}=1. /score needs no key and no model."
            ),
        )

    from .agent import EXPERIMENT_4_BRIEF, propose_design, revise_design
    from .providers import DEFAULT_EXTRACTOR, ledger_summary

    agent = _model_spec(req.agent, "high")
    extractor = _model_spec(req.extractor, "low") if req.extractor else DEFAULT_EXTRACTOR

    rounds: list[RunRound] = []

    def record(text: str) -> DesignScore:
        spec = _extract(text, req.extractor)
        score = score_design(spec, n_sims=req.n_sims, seed=0)
        rounds.append(
            RunRound(
                design_text=text, extracted=spec, score=ScoreResponse.of(score)
            )
        )
        return score

    try:
        design_text = propose_design(agent=agent)
    except Exception as exc:
        raise _provider_error(exc) from exc

    score = record(design_text)

    if req.revise:
        from .score import feedback_for_agent

        try:
            revised = revise_design(
                EXPERIMENT_4_BRIEF, design_text, feedback_for_agent(score), agent=agent
            )
        except Exception as exc:
            raise _provider_error(exc) from exc
        record(revised)

    return RunResponse(
        agent=str(agent),
        extractor=str(extractor),
        rounds=rounds,
        tokens=ledger_summary(),
    )


@app.get("/assays", response_model=list[AssayStatus], summary="Registry status")
def get_assays() -> list[AssayStatus]:
    """Which protocols may legitimately produce a score, and what the rest lack.

    A scaffold is structurally declared and numerically empty. It refuses to be
    scored rather than scoring against invented constants, which is the failure
    mode this project exists to criticise.
    """
    from .assays import REGISTRY

    return [
        AssayStatus(
            key=p.key,
            name=p.name,
            status=p.status.value,
            runnable=p.runnable,
            missing_constants=[c.name for c in p.missing_constants()],
        )
        for p in REGISTRY.values()
    ]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _run_enabled() -> bool:
    return os.environ.get(RUN_ENABLED_ENV, "").strip() == "1"


def _model_spec(text: str, default_effort: str) -> Any:
    from .providers import spec_from_string

    try:
        return spec_from_string(text, default_effort)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"bad model spec: {exc}") from exc


def _extract(design_text: str, extractor: str | None, spec_type: type = DesignSpec) -> Any:
    """Prose -> spec_type, translating provider failures into HTTP errors."""
    if not design_text.strip():
        raise HTTPException(status_code=422, detail="design_text is empty")

    from .agent import extract_design as agent_extract_design
    from .providers import DEFAULT_EXTRACTOR

    spec = _model_spec(extractor, "low") if extractor else DEFAULT_EXTRACTOR
    try:
        if spec_type is DesignSpec:
            return agent_extract_design(design_text, extractor=spec)
        else:
            from .intake import extract_design as intake_extract_design
            from .providers import get_provider

            def model_extractor(text: str) -> Any:
                return get_provider(spec.provider).parse(
                    [{"role": "user", "content": text}],
                    spec,
                    32000,
                    spec_type,
                )

            return intake_extract_design(
                design_text, extractor=model_extractor, design_spec_type=spec_type
            )
    except Exception as exc:
        raise _provider_error(exc) from exc




def _provider_error(exc: Exception) -> HTTPException:
    """502, not 500: the failure is upstream, and saying so is actionable.

    A missing key is the caller's configuration problem and reads as 503 -
    the service is not set up for this, rather than the request being wrong.
    """
    message = str(exc)
    if "is not set" in message:
        return HTTPException(status_code=503, detail=message)
    return HTTPException(status_code=502, detail=f"{type(exc).__name__}: {message}")
