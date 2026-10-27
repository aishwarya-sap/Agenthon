"""A2A executor — the boundary adapter.

Responsibilities (README §3a, §3b):
* validate the incoming identity (JWT) at the A2A boundary — never trust
  client-supplied identity; skipped only in mock mode (IBD_TESTING=1) so offline
  tests/demos work;
* honour per-request ``metadata`` (``mock``, ``sap_mode``) for *behaviour* only;
* run one agent turn (fresh analysis or pending-approval resolution) and shape the
  A2A artifact + task status.

Framework-free ``run_turn`` is the core; a thin ``a2a`` executor subclass is
provided for the SAP runtime when the a2a-sdk is installed.
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Any

from .agent import ProcurementConsequenceAgent
from . import config
from .config import is_mock_mode
from .observability import get_logger, log_event

logger = get_logger()


class IdentityError(Exception):
    """Raised when the incoming request fails identity validation."""


def validate_identity(headers: dict[str, str]) -> str:
    """Validate the bearer token at the A2A boundary and return the subject.

    Mode is selected by ``AGENT_AUTH_MODE`` (see config.agent_auth_mode):
    * ``mock``  — offline; validation skipped (IBD_TESTING=1).
    * ``ias``   — Joule A2A: validate the IAS user token (JWKS/RS256/iss/exp +
                  audience/API grant) and return the user's mail/sub for principal
                  propagation to S/4HANA. This is the Joule-integration path.
    * ``xsuaa`` — legacy/direct: validate the XSUAA JWT.

    Identity is NEVER taken from message metadata.
    """
    mode = config.agent_auth_mode()
    if mode == "mock":
        return "mock-user"
    if mode == "none":
        # DEV-ONLY inbound-auth bypass for BAI standalone testing BEFORE Joule/IAS is
        # wired. Opt-in via AGENT_AUTH_MODE=none. NEVER enable in production.
        log_event(logger, "auth_bypass_DEV_ONLY", status="warning",
                  detail="AGENT_AUTH_MODE=none — inbound identity NOT validated")
        return "dev-bypass-user"

    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise IdentityError("Missing bearer token at the A2A boundary.")
    token = auth.split(" ", 1)[1].strip()

    if mode == "ias":
        from .auth_ias import IASValidationError, validate_ias_token
        try:
            claims = validate_ias_token(
                token,
                issuer=config.ias_issuer(),
                audience=config.ias_audience(),
                jwks_uri=config.ias_jwks_uri(),
                required_api=config.ias_required_api(),
            )
        except IASValidationError as exc:
            raise IdentityError(str(exc)) from exc
        return claims.get("mail") or claims.get("email") or claims.get("sub") or "authenticated-user"

    # xsuaa (legacy/direct)
    try:  # pragma: no cover - requires XSUAA + verification lib at runtime
        from sap_cloud_sdk.security import validate_xsuaa_jwt  # type: ignore
        claims = validate_xsuaa_jwt(token)
        return claims.get("user_name") or claims.get("sub") or "authenticated-user"
    except ImportError as exc:
        raise IdentityError(
            "JWT validation library unavailable; refusing the request rather than trusting it."
        ) from exc


@contextmanager
def _request_behavior(metadata: dict[str, Any]):
    """Apply per-request behaviour flags (mock / sap_mode) for the request duration,
    then restore. These control behaviour only — never authorization."""
    prev_ibd = os.environ.get("IBD_TESTING")
    prev_mode = os.environ.get("SAP_MODE")
    use_mock = str(metadata.get("mock", "")).lower() in ("1", "true")
    if use_mock:
        os.environ["IBD_TESTING"] = "1"
    if metadata.get("sap_mode") in ("cloud", "onprem", "gateway"):
        os.environ["SAP_MODE"] = metadata["sap_mode"]
    try:
        yield
    finally:
        for key, prev in (("IBD_TESTING", prev_ibd), ("SAP_MODE", prev_mode)):
            if prev is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev


async def run_turn(
    agent: ProcurementConsequenceAgent,
    user_input: str,
    *,
    context_id: str | None = None,
    correlation_id: str | None = None,
    headers: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one agent turn and return a result dict ready for A2A shaping."""
    metadata = metadata or {}
    context_id = context_id or str(uuid.uuid4())
    correlation_id = correlation_id or metadata.get("messageId") or str(uuid.uuid4())

    with _request_behavior(metadata):
        subject = validate_identity(headers or {})  # raises IdentityError on failure
        log_event(logger, "turn_start", context_id=context_id, correlation_id=correlation_id,
                  sap_mode=os.environ.get("SAP_MODE", "mock" if is_mock_mode() else "gateway"),
                  subject=subject)
        result = await _run_turn_core(agent, user_input, context_id, correlation_id)
        result.setdefault("context_id", context_id)
        result.setdefault("correlation_id", correlation_id)
        log_event(logger, "turn_complete", context_id=context_id, correlation_id=correlation_id,
                  status="ok", pending=result.get("pending"))
        return result


async def _run_turn_core(
    agent: ProcurementConsequenceAgent, user_input: str, context_id: str, correlation_id: str,
) -> dict[str, Any]:
    """Run the turn through the LangGraph seam when available, else call handle() directly.

    The graph node calls ``agent.handle()`` so behaviour is identical; the graph only adds
    the standard checkpointer (thread_id = context_id) + recursion limit. Offline (no
    langgraph) this falls back to a direct call so the framework-free test suite still runs.
    """
    from .graph import build_graph, langgraph_available, DEFAULT_RECURSION_LIMIT

    if langgraph_available():
        graph = getattr(agent, "_compiled_graph", None)
        if graph is None:
            graph = build_graph(agent)
            agent._compiled_graph = graph  # cache the compiled graph on the agent
        out = await graph.ainvoke(
            {"user_input": user_input, "context_id": context_id, "correlation_id": correlation_id},
            config={"recursion_limit": DEFAULT_RECURSION_LIMIT,
                    "configurable": {"thread_id": context_id}},
        )
        return out["result"]
    return await agent.handle(user_input, context_id=context_id, correlation_id=correlation_id)


def to_a2a_response(
    result: dict[str, Any],
    request_id: str = "1",
    *,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Shape a run_turn result into an A2A ``message/send`` response.

    Returns a conformant A2A 0.3.0 **Task** object (``kind: "task"``), not a
    streaming ``artifact-update`` event — ``message/send`` is non-streaming
    (agent card advertises ``streaming: false``). Joule's capability function
    reads the text from ``status.message.parts[].text`` and persists
    ``id`` (taskId) + ``contextId`` for multi-turn; ``artifacts[]`` carries the
    same report for A2A clients that consume artifacts. ``input-required`` keeps
    the task open so the HITL approval turn resumes the same context.
    """
    text = result.get("content", "")
    context_id = result.get("context_id")
    tid = task_id or result.get("task_id") or str(uuid.uuid4())
    state = "input-required" if result.get("pending") else "completed"
    agent_message = {
        "role": "agent",
        "messageId": str(uuid.uuid4()),
        "parts": [{"kind": "text", "text": text}],
        "contextId": context_id,
        "taskId": tid,
    }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "kind": "task",
            "id": tid,
            "contextId": context_id,
            "status": {"state": state, "message": agent_message},
            "artifacts": [
                {
                    "artifactId": str(uuid.uuid4()),
                    "name": "procurement_consequence_report",
                    "parts": [{"kind": "text", "text": text}],
                }
            ],
        },
    }


# --- Optional native a2a-sdk executor (SAP runtime) -------------------------
try:  # pragma: no cover - only when a2a-sdk is installed
    from a2a.server.agent_execution import AgentExecutor
    from a2a.server.agent_execution.context import RequestContext
    from a2a.server.events.event_queue import EventQueue

    class ProcurementAgentExecutor(AgentExecutor):
        def __init__(self) -> None:
            self.agent = ProcurementConsequenceAgent()

        async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
            user_input = context.get_user_input()
            md = getattr(getattr(context, "message", None), "metadata", {}) or {}
            ctx_id = getattr(context, "context_id", None) or str(uuid.uuid4())
            result = await run_turn(self.agent, user_input, context_id=ctx_id, metadata=md)
            # Event emission is handled by the server's request handler wrapper.
            context.result = result  # type: ignore[attr-defined]

        async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
            task_id = getattr(context, "task_id", None) or getattr(context, "context_id", "unknown")
            await event_queue.enqueue_event({
                "jsonrpc": "2.0",
                "id": task_id,
                "result": {
                    "id": task_id,
                    "status": {"state": "cancelled"},
                    "artifacts": [],
                },
            })
except Exception:  # a2a-sdk absent offline — Starlette surface in main.py is used instead
    ProcurementAgentExecutor = None  # type: ignore
