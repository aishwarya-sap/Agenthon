"""Typed turn state for the LangGraph orchestration seam.

Minimal by design — the agent's deterministic turn produces the full result dict;
the graph state carries only the inputs and the produced result.

Imports only stdlib typing so the offline test suite (no langgraph installed) can
import this module freely.

TODO: Extend TurnState with domain-specific fields as the agent's state grows.
"""
from __future__ import annotations

from typing import Any, TypedDict


class TurnState(TypedDict, total=False):
    user_input: str
    context_id: str
    correlation_id: str
    result: dict[str, Any]
