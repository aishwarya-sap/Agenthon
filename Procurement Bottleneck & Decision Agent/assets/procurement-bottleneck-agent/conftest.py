"""Shared test fixtures and the offline mock harness.

Sets ``IBD_TESTING=1`` for the whole suite so the tool layer
(``app.mcp_tools.get_mcp_tools``) returns deterministic fixtures and no live SAP /
AI Core call is ever made. Agent code is byte-identical in mock and production —
the switch happens only at the tool/data boundary, never in business logic.
"""
from __future__ import annotations

import os

import pytest

os.environ["IBD_TESTING"] = "1"  # mock everywhere, before any app import


@pytest.fixture(autouse=True)
def _reset_stores():
    """Clear process-wide in-memory stores between tests for isolation."""
    from app import memory
    from app import hitl
    memory.reset_memory_store()
    hitl._APPROVALS = None  # force a fresh ApprovalStore
    yield
    memory.reset_memory_store()
    hitl._APPROVALS = None


@pytest.fixture
def agent():
    from app.agent import ProcurementConsequenceAgent
    return ProcurementConsequenceAgent()


@pytest.fixture
async def mock_tools():
    from app.mcp_tools import get_mcp_tools
    return await get_mcp_tools()
