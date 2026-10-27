"""Typed turn state for the LangGraph orchestration seam.

Kept intentionally minimal: the agent's deterministic turn already produces the full
result dict, so the graph state just carries the turn inputs and the produced result.
This module imports only the stdlib typing surface so the offline test suite (which runs
without langgraph installed) can import it freely.
"""
from __future__ import annotations

from typing import Any, TypedDict


class TurnState(TypedDict, total=False):
    user_input: str
    context_id: str
    correlation_id: str
    result: dict[str, Any]
