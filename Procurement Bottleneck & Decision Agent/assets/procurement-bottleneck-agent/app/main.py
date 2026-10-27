"""Server entry point — A2A JSON-RPC surface on Starlette.

Routes (README §8):
* ``GET  /``                       — chat UI (what a browser opening the base URL sees).
* ``POST /``                       — A2A ``message/send`` (JSON-RPC) — same path A2A clients call.
* ``GET  /.well-known/agent.json`` — A2A agent card (CF health-check target).
* ``GET  /ui``                     — alias of the chat UI (kept for older links).
* ``GET  /health``                 — liveness probe; returns ``{"status":"ok","version":"..."}``.
  (Some SAP CF monitors / load balancers probe ``/health`` separately from the A2A card.)

GET and POST on ``/`` are distinct routes: a browser gets the UI, A2A clients
POST JSON-RPC — so the public URL needs no ``/ui`` suffix.

The JSON-RPC wire shape matches the A2A protocol Joule and clients call, so the
agent is A2A-native without a hard dependency on the a2a-sdk being installed
locally (the SAP runtime can swap in the native server; the surface is identical).
VCAP_SERVICES is mapped before any AI-framework import; OTel auto-instrumentation
is wired first.
"""
from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path

# dotenv is optional locally; VCAP provides vars in CF.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except Exception:
    pass

# Map bound CF service credentials into the environment before importing the agent.
_vcap = os.environ.get("VCAP_SERVICES")
if _vcap:
    try:
        _services = json.loads(_vcap)
        for _svc in _services.get("aicore", []):
            _c = _svc.get("credentials", {})
            os.environ.setdefault("AICORE_CLIENT_ID", _c.get("clientid", ""))
            os.environ.setdefault("AICORE_CLIENT_SECRET", _c.get("clientsecret", ""))
            os.environ.setdefault("AICORE_AUTH_URL", _c.get("url", ""))
            os.environ.setdefault("AICORE_BASE_URL", _c.get("serviceurls", {}).get("AI_API_URL", ""))
            break
    except Exception:
        pass

from .observability import auto_instrument  # noqa: E402

auto_instrument()  # must precede AI framework imports

from .agent import ProcurementConsequenceAgent  # noqa: E402
from .agent_card import get_agent_card, public_base_url  # noqa: E402
from .agent_executor import IdentityError, run_turn, to_a2a_response, validate_identity  # noqa: E402
from . import config  # noqa: E402
from .observability import get_logger, log_event  # noqa: E402

logger = get_logger()
_AGENT = ProcurementConsequenceAgent()
_UI_PATH = Path(__file__).parent.parent / "demo" / "index.html"


async def s4_canary_read(user_jwt: str | None) -> dict:
    """Diagnostic canary: prove the agent can reach S/4 as the propagated user.

    Wired to the live S/4 read path once the connectivity target (SAP Business
    Accelerator Hub sandbox for BAI, or the principal-propagation Destination for
    Joule) is configured. Until then it reports the intended mode so /whoami still
    shows the first four hops of the chain.
    """
    try:
        from .mcp_tools import get_mcp_tools
        tools = await get_mcp_tools()
        names = [getattr(t, "name", "") for t in tools]
        mode = ("mock" if config.is_mock_mode() else os.environ.get("SAP_MODE", "gateway"))
        note = ("live S/4 reads via SAP Business Accelerator Hub (APIKey)"
                if mode == "accelerator_hub"
                else "mock/offline" if mode == "mock" else f"connectivity mode '{mode}'")
        return {"reachable": True, "mode": mode, "tools_loaded": len(names), "note": note}
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def _pdf_to_text(raw: bytes) -> str:
    """Extract text from a digital (text-based) PDF. Returns '' for scanned/image
    PDFs or when pypdf is unavailable — image OCR is delegated to Joule document
    grounding, so this stays a pure-Python, CF-safe best-effort extractor."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((pg.extract_text() or "") for pg in reader.pages)
    except Exception:
        return ""


def _extract_attachment_text(parts: list) -> str:
    """Turn A2A file parts (invoice PDFs / images) into text the agent can reason
    over. Digital PDFs are read in-agent; scanned images are acknowledged and left
    for Joule's document-grounding OCR."""
    chunks: list[str] = []
    for p in parts:
        if p.get("kind") != "file" and "file" not in p:
            continue
        f = p.get("file", {}) or {}
        name = f.get("name", "attachment")
        mime = (f.get("mimeType") or "").lower()
        b64 = f.get("bytes") or f.get("data")
        if not b64:
            chunks.append(f"[Attached '{name}' — no inline content; Joule document grounding will process it.]")
            continue
        try:
            raw = base64.b64decode(b64)
        except Exception:
            continue
        extracted = ""
        if "pdf" in mime or name.lower().endswith(".pdf"):
            extracted = _pdf_to_text(raw)
        if extracted.strip():
            chunks.append(f"[Attached document '{name}' — extracted text follows]\n{extracted[:6000]}")
        else:
            chunks.append(
                f"[Attached '{name}' ({mime or 'unknown type'}) — appears to be a scanned/image document; "
                f"in-agent text extraction found none. Joule document grounding (OCR) will read it when available.]"
            )
    return "\n\n".join(chunks)


def _extract_message(body: dict) -> tuple[str, str | None, str | None, dict]:
    params = body.get("params", {}) or {}
    message = params.get("message", {}) or {}
    parts = message.get("parts", []) or []
    text = ""
    for p in parts:
        if p.get("kind") == "text" or "text" in p:
            text += p.get("text", "")
    attachment_text = _extract_attachment_text(parts)
    if attachment_text:
        text = (text + "\n\n" + attachment_text).strip() if text else attachment_text
    metadata = dict(message.get("metadata", {}) or {})
    if message.get("messageId"):
        metadata.setdefault("messageId", message["messageId"])
    context_id = message.get("contextId") or params.get("contextId")
    task_id = message.get("taskId") or params.get("taskId")
    return text, context_id, task_id, metadata


def build_app():
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.requests import Request
    from starlette.responses import HTMLResponse, JSONResponse
    from starlette.routing import Route

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    async def agent_card(_request: Request):
        return JSONResponse(get_agent_card(public_base_url(host, port)))

    async def message_endpoint(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"jsonrpc": "2.0", "id": None,
                                 "error": {"code": -32700, "message": "Parse error"}}, status_code=400)
        text, context_id, task_id, metadata = _extract_message(body)
        if not text:
            return JSONResponse({"jsonrpc": "2.0", "id": body.get("id"),
                                 "error": {"code": -32602, "message": "message.parts[].text is required"}},
                                status_code=400)
        headers = {k.lower(): v for k, v in request.headers.items()}
        try:
            result = await run_turn(_AGENT, text, context_id=context_id, headers=headers, metadata=metadata)
        except IdentityError as exc:
            return JSONResponse({"jsonrpc": "2.0", "id": body.get("id"),
                                 "error": {"code": -32001, "message": str(exc)}}, status_code=401)
        except Exception:
            log_event(logger, "turn_error", status="error")
            return JSONResponse({"jsonrpc": "2.0", "id": body.get("id"),
                                 "error": {"code": -32603, "message": "Internal agent error"}}, status_code=500)
        return JSONResponse(to_a2a_response(result, str(body.get("id", "1")), task_id=task_id))

    async def ui(_request: Request):
        if _UI_PATH.exists():
            return HTMLResponse(_UI_PATH.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Chat UI not found</h1>", status_code=404)

    async def health(_request: Request):
        """Liveness probe expected by SAP CF monitors and some load balancers."""
        version = "unknown"
        try:
            import configparser, pathlib
            cp = configparser.ConfigParser()
            cp.read(pathlib.Path(__file__).parent.parent / "version.ini")
            version = cp.get("version", "version", fallback="unknown")
        except Exception:
            pass
        return JSONResponse({"status": "ok", "version": version, "agent": config.AGENT_NAME})

    async def whoami(request: Request):
        """Diagnostic: show which identity arrived and whether each hop would pass.

        Gated by ENABLE_WHOAMI; returns 404 when disabled. Catches principal-
        propagation bugs between Joule -> agent -> S/4 without any agent logic in
        the way. Never returns the raw token. Disable before production.
        """
        if not config.whoami_enabled():
            return JSONResponse({"error": "not found"}, status_code=404)
        headers = {k.lower(): v for k, v in request.headers.items()}
        auth = headers.get("authorization", "")
        has_token = auth.lower().startswith("bearer ")
        token = auth.split(" ", 1)[1].strip() if has_token else ""

        claims: dict = {}
        if has_token:
            from .auth_ias import decode_unverified
            claims = decode_unverified(token)

        validation = {"result": "n/a"}
        try:
            subject = validate_identity(headers)
            validation = {"result": "pass", "subject": subject}
        except IdentityError as exc:
            validation = {"result": "fail", "reason": str(exc)}

        return JSONResponse({
            "auth_mode": config.agent_auth_mode(),
            "sap_mode": ("mock" if config.is_mock_mode() else os.environ.get("SAP_MODE", "gateway")),
            "inbound_token_present": has_token,
            "inbound_token_claims": claims,          # unverified, diagnostic subset only
            "boundary_validation": validation,
            "ias_config": {
                "issuer": config.ias_issuer() or None,
                "audience": config.ias_audience(),
                "required_api": config.ias_required_api(),
                "jwks_uri": config.ias_jwks_uri() or None,
            },
            "s4_canary": await s4_canary_read(token or None),
        })

    app = Starlette(routes=[
        Route("/.well-known/agent.json", agent_card, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/", ui, methods=["GET"]),
        Route("/", message_endpoint, methods=["POST"]),
        Route("/ui", ui, methods=["GET"]),
        Route("/whoami", whoami, methods=["GET"]),
    ])
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])
    return app


def main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    log_event(logger, "server_start", status="ok",
              sap_mode=("mock" if os.environ.get("IBD_TESTING") else os.environ.get("SAP_MODE", "gateway")))
    uvicorn.run(build_app(), host=host, port=port)


# Module-level ASGI app for gunicorn (`gunicorn app.main:app`), the production entry
# point on CF. The local/dev path (`python -m app`) uses main() above and is unaffected.
app = build_app()


if __name__ == "__main__":
    main()
