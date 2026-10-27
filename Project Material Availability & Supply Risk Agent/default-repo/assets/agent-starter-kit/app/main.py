import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except Exception:
    pass

try:
    from sap_cloud_sdk.aicore import set_aicore_config
except Exception:
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

try:
    from sap_cloud_sdk import bootstrap
except Exception:
    def bootstrap(_app):
        return None

from agent_executor import AgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

AGENT_NAME = os.environ.get("AGENT_NAME", "agent-starter-kit")
AGENT_DESCRIPTION = os.environ.get(
    "AGENT_DESCRIPTION",
    "SAP A2A agent — replace this description with your domain-specific text.",
)


@click.command()
@click.option("--host", default=HOST)
@click.option("--port", default=PORT)
def main(host: str, port: int):
    skill = AgentSkill(
        id="default-skill",
        name="Default Skill",
        description="Replace with your domain-specific skill description.",
        tags=["sap", "btp"],
        examples=["What can you help me with?"],
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
    bootstrap(app)

    logger.info("Starting agent at http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
