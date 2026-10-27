"""A2A Agent Card — capabilities, skills, tags, and examples for Joule discovery
and intent routing. Served at ``/.well-known/agent.json``.

Built as a plain A2A-compliant dict so the card resolves offline with no agent
framework installed; ``main.py`` serves it directly and the CF health check polls
it. In the SAP runtime the same fields map onto ``a2a.types.AgentCard``.
"""
from __future__ import annotations

import os
from typing import Any

from . import config

SKILL = {
    "id": "procurement-bottleneck-decision",
    "name": "Procurement Bottleneck & Decision",
    "description": (
        "Advisory procurement agent for the Purchasing Head of Department. Detects supplier silence on "
        "critical-path purchase orders across active projects, traces the PR→PO→confirmation chain, "
        "quantifies the downstream consequence (schedule slip, idle-resource cost, milestone-penalty "
        "exposure, emergency-sourcing premium), recalls similar past decisions, and presents a ranked, "
        "evidence-backed recommendation (escalate / source-switch / absorb) for human approval. "
        "Read-only on SAP S/4HANA Sourcing & Procurement and SAP Project System; never writes SAP business objects."
    ),
    "tags": ["procurement", "sourcing", "supplier-risk", "project-system", "critical-path",
             "s4hana", "consequence-simulation", "advisory"],
    "examples": [
        "Run the procurement bottleneck analysis for project P-INFRA-07.",
        "Which open POs have suppliers silent on critical-path materials?",
        "What is the cost of inaction if PO 4500000123 is not confirmed in 48 hours?",
        "Show the consequence scorecard and recommended action for supplier LIFNR-0010045.",
    ],
}


def get_agent_card(base_url: str) -> dict[str, Any]:
    return {
        "name": config.AGENT_NAME,
        "description": (
            "Procurement Bottleneck & Decision Agent — advisory, read-only SAP agent that surfaces "
            "which supplier silences will cause schedule slip and idle resources, with alternatives and "
            "escalation routing, every outcome captured as institutional memory."
        ),
        "url": base_url,
        "documentation_url": base_url,
        "version": config.AGENT_VERSION,
        "default_input_modes": ["text/plain"],
        "default_output_modes": ["text/plain"],
        "capabilities": {"streaming": False, "push_notifications": False},
        "skills": [SKILL],
        "supported_interfaces": [],
        "provider": {"organization": "Adarsh Developers (SAP GDH APAC)", "url": base_url},
    }


def public_base_url(host: str, port: int) -> str:
    env_url = os.environ.get("AGENT_PUBLIC_URL")
    if env_url:
        return env_url.rstrip("/")
    display = "localhost" if host in ("0.0.0.0", "") else host
    return f"http://{display}:{port}"
