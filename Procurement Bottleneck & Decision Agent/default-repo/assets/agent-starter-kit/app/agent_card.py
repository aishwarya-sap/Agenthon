"""A2A Agent Card — served at /.well-known/agent.json for Joule and A2A client discovery.

The skill id MUST match a2aSkillId in the Joule capability function YAML.
Customize name, description, and skills per engagement before deploying.
"""
from __future__ import annotations

from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from app.config import AGENT_NAME, AGENT_VERSION


def get_agent_card(base_url: str) -> AgentCard:
    """Build the AgentCard for this agent.

    base_url is derived from VCAP_APPLICATION (CF) or AGENT_PUBLIC_URL at startup.
    """
    skill = AgentSkill(
        id="analyze",  # TODO: rename — MUST match a2aSkillId in joule/.../functions/*.yaml
        name="Analyze",  # TODO: rename
        description="[TODO: describe what this skill does and when Joule should route to it]",
        tags=["todo"],  # TODO: replace with domain tags, e.g. ["procurement", "s4hana"]
        examples=["[TODO: example user utterance that should route here]"],
    )

    return AgentCard(
        name=AGENT_NAME,
        description="[TODO: one-sentence description — Joule uses this for routing decisions]",
        url=f"{base_url}/",
        version=AGENT_VERSION,
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
        skills=[skill],
    )
