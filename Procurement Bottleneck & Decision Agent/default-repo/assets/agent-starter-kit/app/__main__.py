"""Entry point: python -m app

Reads the public URL from VCAP_APPLICATION (CF) or AGENT_PUBLIC_URL / localhost.
Credentials for AI Core come from VCAP_SERVICES (CF) or AICORE_SERVICE_KEY (local dev).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env for local dev. No-op in CF — env comes from VCAP_SERVICES / cf set-env.
load_dotenv(Path(__file__).parent.parent / ".env", override=False)

import uvicorn
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore

from app.agent_card import get_agent_card
from app.agent_executor import AgentStarterKitExecutor


def _app_url() -> str:
    """Derive the public agent URL.

    Priority: VCAP_APPLICATION.application_uris[0] (CF) → AGENT_PUBLIC_URL → localhost.
    """
    vcap_app = os.getenv("VCAP_APPLICATION", "{}")
    try:
        uris = json.loads(vcap_app).get("application_uris", [])
        if uris:
            return f"https://{uris[0]}"
    except (json.JSONDecodeError, AttributeError):
        pass
    explicit = os.getenv("AGENT_PUBLIC_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    port = os.getenv("PORT", "8080")
    return f"http://localhost:{port}"


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))

    app_url = _app_url()
    agent_card = get_agent_card(app_url)
    executor = AgentStarterKitExecutor()

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    application = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=handler,
    )
    uvicorn.run(application.build(), host=host, port=port)


if __name__ == "__main__":
    main()
