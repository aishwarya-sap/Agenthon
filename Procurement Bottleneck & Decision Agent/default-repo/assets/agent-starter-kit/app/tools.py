"""LangGraph tools — one @tool function per SAP API the agent can call.

STARTER-KIT DEFAULTS:
  echo_tool     — connectivity test, always works, keep this
  get_sap_data  — placeholder; replace body with your real Agent Gateway / OData call

Each tool's docstring is read by the LLM to decide when and how to call it,
so keep them precise and action-oriented.
"""
from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

from app.config import is_mock_mode

_MOCK_FILE = Path(__file__).parent.parent / "mcp-mock.json"


def _mock_responses() -> dict:
    try:
        data = json.loads(_MOCK_FILE.read_text())
        servers = data.get("servers", {})
        first = next(iter(servers.values()), {})
        return first.get("responses", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


@tool
def echo_tool(message: str) -> dict:
    """Echo the input message back. Use this to verify agent connectivity.

    Args:
        message: Any string to echo back.
    """
    return {"echo": message, "status": "ok"}


@tool
def get_sap_data(query: str) -> dict:
    """Retrieve data from SAP. TODO: replace with your real Agent Gateway or OData call.

    Args:
        query: The search query or OData filter expression.
    """
    if is_mock_mode():
        responses = _mock_responses()
        first = next(iter(responses.values()), {"results": [], "source": "MOCK"})
        return first

    # TODO: implement live call — example pattern:
    # import httpx, os
    # dest_url = os.getenv("SAP_DESTINATION_URL", "")
    # resp = httpx.get(f"{dest_url}/sap/opu/odata/sap/MY_API/EntitySet",
    #                  params={"$filter": query, "$format": "json"}, timeout=30)
    # resp.raise_for_status()
    # return resp.json().get("d", {}).get("results", [])
    return {"error": "Live SAP data fetch not yet implemented — fill in this tool."}


def get_tools() -> list:
    """Return all tools available to the agent."""
    return [echo_tool, get_sap_data]
