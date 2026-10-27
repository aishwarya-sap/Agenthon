"""MCP tool provider — Sprint 1: mock mode only.

In Sprint 2, this file gains a `IBD_LIVE_S4` branch that calls real OData services,
and a gateway branch that routes through SAP Agent Gateway. For Sprint 1 all calls
go to the seeded mock in mcp-mock.json so the agent runs fully offline.
"""
from __future__ import annotations

import contextvars
import json
import os
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool

_user_token_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_token", default=None
)


def set_user_token(token: str | None) -> Any:
    return _user_token_var.set(token)


def reset_user_token(ctx: Any) -> None:
    _user_token_var.reset(ctx)


def get_user_sub() -> str:
    return "anonymous"


def _load_mock_tools() -> list[StructuredTool]:
    mock_path = Path(__file__).parent.parent.parent / "mcp-mock.json"
    if not mock_path.exists():
        return []
    data = json.loads(mock_path.read_text())
    tools = []
    for tool_def in data.get("tools", []):
        name = tool_def["name"]
        response = tool_def.get("response", {})

        def _make_fn(r):
            def _fn(**_kwargs):
                return r
            return _fn

        tools.append(
            StructuredTool.from_function(
                func=_make_fn(response),
                name=name,
                description=tool_def.get("description", name),
                args_schema=None,
                return_direct=False,
            )
        )
    return tools


async def get_mcp_tools() -> list:
    """Return tools for the current run mode.

    Sprint 1: always returns mock tools (IBD_TESTING=1).
    Sprint 2: add IBD_LIVE_S4 branch here.
    """
    return _load_mock_tools()
