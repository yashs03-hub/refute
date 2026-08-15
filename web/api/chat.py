"""Serverless endpoint for the web chat. Computes; never opines.

POST {"design": {...DesignSpec...}, "message": "what should I change?"}
  -> {"answer": "...", "evidence": [...], "intent": "advise"}

NO MODEL IS CALLED HERE, and that is the design rather than a limitation. The
only step in `refute.chat` that needs a model is prose -> DesignSpec; the web
form supplies the spec directly, so every turn of the conversation is a
simulation. Consequences: no API key on the server, no per-message cost, no
abuse surface on a public URL, and the endpoint cannot be made to say anything
that was not computed.

Prose entry can be added later behind a rate limit and a budget cap. It is
deliberately not here, because an open endpoint that spends the owner's API
budget per request is not something to ship first and gate afterwards.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from refute.chat import Session, _cite
from refute.design import DesignSpec, OutOfTwinScopeError
from refute.score import score_design

# Public endpoint, so the simulation count is fixed rather than caller-supplied:
# it is the only lever that costs CPU, and 300 plates is enough for a stable
# power estimate at these design sizes.
N_SIMS = 300

MAX_BODY = 64 * 1024


class handler(BaseHTTPRequestHandler):  # noqa: N801 - Vercel's expected name
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._send(400, {"error": "bad Content-Length"})
        if length <= 0 or length > MAX_BODY:
            return self._send(413, {"error": "body too large or empty"})

        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return self._send(400, {"error": "body is not JSON"})

        message = str(payload.get("message", "")).strip()
        if not message:
            return self._send(400, {"error": "message is required"})

        try:
            design = DesignSpec.model_validate(payload.get("design") or {})
        except Exception as exc:
            return self._send(422, {"error": f"design did not validate: {exc}"})

        session = Session(extractor=None, n_sims=N_SIMS)
        try:
            session.design = design
            session.score = score_design(design, n_sims=N_SIMS)
        except OutOfTwinScopeError as exc:
            # A limit of the twin, not a verdict on the design. Said in those
            # words because the difference is the whole point.
            return self._send(
                422,
                {
                    "error": "out_of_twin_scope",
                    "answer": (
                        "I can't score this, and that is a limit of the simulator "
                        "rather than a problem with your design."
                    ),
                    "reasons": exc.reasons,
                },
            )

        if session.score.declined:
            return self._send(
                200,
                {
                    "intent": "design",
                    "answer": (
                        "That assigns no wells, so nothing was simulated. "
                        "Declining can be the right answer."
                    ),
                    "evidence": [],
                },
            )

        turn = session.ask(message)
        self._send(
            200,
            {
                "intent": turn.intent,
                "answer": turn.answer,
                "evidence": turn.evidence or _cite(session.score, N_SIMS),
            },
        )

    def do_GET(self) -> None:  # noqa: N802
        self._send(
            200,
            {
                "ok": True,
                "computes": True,
                "calls_a_model": False,
                "n_sims": N_SIMS,
                "note": (
                    "POST {design, message}. Every answer is a simulation; no "
                    "model is called."
                ),
            },
        )
