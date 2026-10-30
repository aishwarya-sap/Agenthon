"""Owned MCP tool-loader indirection.

Business code and the agent graph import ``get_mcp_tools`` from here and resolve
tools *by capability*, never by hard-coded name. ``conftest.py`` monkey-patches
this function for offline tests, so agent code is byte-identical in mock and
production. Mock mode (``IBD_TESTING=1``) always overrides the connectivity mode.
"""
from __future__ import annotations

import os

from . import config, tools
from .observability import get_logger, log_event

logger = get_logger()


async def get_mcp_tools() -> list[tools.AgentTool]:
    """Return the agent's tool set for the active mode.

    * mock (IBD_TESTING=1)         → deterministic fixtures (offline).
    * gateway                      → Agent Gateway (ORD/MCP), preferred production.
    * cloud / onprem               → Direct via Destination + Connectivity.
    """
    if config.is_mock_mode():
        log_event(logger, "load_tools", sap_mode="mock", status="ok")
        return tools.build_mock_tools()

    mode = os.environ.get("SAP_MODE", "gateway").lower()
    log_event(logger, "load_tools", sap_mode=mode, status="ok")
    # accelerator_hub (sandbox APIKey) and onprem (BTP Destination + Cloud Connector)
    # are both backed by s4_client, which picks its transport from SAP_MODE.
    if mode in ("accelerator_hub", "onprem"):
        return tools.build_accelerator_hub_tools()
    return tools.build_live_tools(mode)
