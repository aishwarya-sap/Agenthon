import os

try:  # SAP runtime provides sap_cloud_sdk; offline/CI it is absent — degrade gracefully.
    from sap_cloud_sdk.aicore import set_aicore_config
except Exception:  # pragma: no cover - exercised only off-platform
    def set_aicore_config(*_a, **_k):
        return None

set_aicore_config()

import logging

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

try:
    from sap_cloud_sdk import bootstrap
except Exception:  # pragma: no cover
    def bootstrap(_app):
        return None

from agent_executor import AgentExecutor
from mcp_providers.agw import set_user_token, reset_user_token
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

AGENT_NAME = "material-risk-agent"
AGENT_DESCRIPTION = (
    "Project Material Risk — Construction Activity Impact Agent. Cross-references project "
    "material requirements against SAP S/4HANA stock and procurement data to surface supply "
    "gaps that will block scheduled construction activities, predicts supplier delivery, "
    "simulates the schedule/cost consequence, and recommends the least-cost recovery — with a "
    "human approval gate on all write actions."
)

_PUBLIC_PREFIXES = ("/.well-known", "/whoami")


class JWTContextMiddleware(BaseHTTPMiddleware):
    """Extract the inbound JWT, set it in context, and — when AGENT_AUTH_MODE=ias —
    validate it at the A2A boundary (Joule delivers an IAS token, not XSUAA).

    ``/.well-known/*`` and ``/whoami`` stay unauthenticated (card discovery +
    diagnostics). In mock/xsuaa mode the token is only threaded to context.
    """

    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("authorization", "")
        token = auth_header[7:] if auth_header.lower().startswith("bearer ") else None

        path = request.url.path
        is_public = any(path.startswith(p) for p in _PUBLIC_PREFIXES)
        if config.agent_auth_mode() == "ias" and not is_public:
            from auth_ias import validate_ias_token, IASValidationError
            if not token:
                return JSONResponse({"error": "missing bearer token"}, status_code=401)
            try:
                validate_ias_token(
                    token,
                    issuer=config.ias_issuer(),
                    audience=config.ias_audience(),
                    jwks_uri=config.ias_jwks_uri(),
                    required_api=config.ias_required_api(),
                )
            except IASValidationError as exc:
                return JSONResponse({"error": f"unauthorized: {exc}"}, status_code=401)

        token_ctx = set_user_token(token)
        try:
            return await call_next(request)
        finally:
            reset_user_token(token_ctx)


async def whoami(request: Request):
    """Diagnostic: show which identity arrived and whether each hop would pass.

    Gated by ENABLE_WHOAMI; 404 when disabled. Pinpoints principal-propagation
    bugs between Joule -> agent -> S/4. Never returns the raw token. Off in prod.
    """
    if not config.whoami_enabled():
        return JSONResponse({"error": "not found"}, status_code=404)
    auth = request.headers.get("authorization", "")
    has_token = auth.lower().startswith("bearer ")
    token = auth[7:].strip() if has_token else ""

    claims: dict = {}
    validation = {"result": "n/a"}
    if has_token:
        from auth_ias import decode_unverified, validate_ias_token, IASValidationError
        claims = decode_unverified(token)
        if config.agent_auth_mode() == "ias":
            try:
                validate_ias_token(
                    token, issuer=config.ias_issuer(), audience=config.ias_audience(),
                    jwks_uri=config.ias_jwks_uri(), required_api=config.ias_required_api(),
                )
                validation = {"result": "pass"}
            except IASValidationError as exc:
                validation = {"result": "fail", "reason": str(exc)}

    canary: dict = {"mode": "mock"}
    if config.is_live_s4():
        from s4_client import s4_canary_read
        canary = s4_canary_read()

    return JSONResponse({
        "auth_mode": config.agent_auth_mode(),
        "run_mode": ("mock" if config.is_mock_mode()
                     else ("live_s4" if config.is_live_s4() else "gateway")),
        "inbound_token_present": has_token,
        "inbound_token_claims": claims,          # unverified, diagnostic subset only
        "boundary_validation": validation,
        "ias_config": {
            "issuer": config.ias_issuer() or None,
            "audience": config.ias_audience(),
            "required_api": config.ias_required_api(),
            "jwks_uri": config.ias_jwks_uri() or None,
        },
        "s4_canary": canary,
    })


def build_app(host: str = HOST, port: int = PORT):
    """Construct the A2A ASGI app. The module-level ``app`` below is the gunicorn
    entry (`gunicorn app.main:app`); main() builds it for the CLI / `python app/_boot.py`
    path. Behaviour is identical across both.
    """
    skill = AgentSkill(
        id="project-material-supply-risk",
        name="Project Material Supply-Risk Analysis",
        description=(
            "Identify at-risk project materials, map them to construction activities and float, "
            "score supplier delivery risk, simulate schedule consequence, and recommend "
            "expedite / escalate / alternative-source actions."
        ),
        tags=["procurement", "supply-risk", "construction", "sap", "s4hana", "project-system"],
        examples=[
            "Will the materials for the next activity on Project Alpha be available on time?",
            "Show me the supply risks for project P-ALPHA-01.",
            "Show me the supplier delivery history for structural steel.",
            "What is the schedule consequence of the structural steel delay?",
        ],
    )
    agent_card = AgentCard(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        url=os.environ.get("AGENT_PUBLIC_URL", f"http://{host}:{port}/"),
        version="1.0.0",
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        skills=[skill],
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=DefaultRequestHandler(
            agent_executor=AgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    app = server.build()
    app.add_middleware(JWTContextMiddleware)
    app.router.add_route("/whoami", whoami, methods=["GET"])
    bootstrap(app)
    return app


# Module-level ASGI app for gunicorn (`gunicorn app.main:app`). The `python app/_boot.py`
# path uses main() below and is unaffected.
app = build_app()


@click.command()
@click.option("--host", default=HOST)
@click.option("--port", default=PORT)
def main(host: str, port: int):
    target = app if (host, port) == (HOST, PORT) else build_app(host, port)
    try:
        logger.info("M1.achieved: agent initialized and ready")
        logger.info(f"Starting A2A server at http://{host}:{port}")
        uvicorn.run(target, host=host, port=port)
    except Exception:
        logger.exception("M1.missed: agent initialization failed")
        raise


if __name__ == "__main__":
    main()
