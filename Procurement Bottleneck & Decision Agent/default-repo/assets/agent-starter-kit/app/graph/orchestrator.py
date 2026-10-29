"""LangGraph build_graph() orchestration seam.

The compiled graph wraps the agent's existing handle() turn in a StateGraph so the
standard A2A scaffolding (typed state, MemorySaver checkpointer keyed by contextId,
recursion_limit) is in place from the start.

The langgraph import is guarded: when langgraph is absent (offline CI, no requirements
installed) langgraph_available() returns False and callers fall back to agent.handle()
directly — the mock-first test suite never requires langgraph to be installed.

Architecture note (answer B3 in agent-build-brief.md before choosing):
  - PROCESS-SCOPED tool set → call build_graph() once at startup and cache the result.
  - USER-SCOPED tool set (Agent Gateway / MCP returns different tools per user) →
    call build_graph() per request; never cache the compiled graph across users.

TODO: Replace the single-node "agent" pattern here with a multi-node graph if the
agent requires supervisor→worker topology (see B2 in agent-build-brief.md).
"""
from __future__ import annotations

from typing import Any

from .state import TurnState

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    _LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover — exercised implicitly in offline CI
    _LANGGRAPH_AVAILABLE = False

DEFAULT_RECURSION_LIMIT = 10


def langgraph_available() -> bool:
    """True when langgraph is importable (deployed runtime), False in offline CI."""
    return _LANGGRAPH_AVAILABLE


def build_graph(agent: Any, *, checkpointer: Any | None = None) -> Any:
    """Compile a minimal StateGraph that runs one agent turn.

    Raises RuntimeError if langgraph is not installed — callers must gate on
    langgraph_available() and fall back to agent.handle() directly.
    """
    if not _LANGGRAPH_AVAILABLE:
        raise RuntimeError("langgraph is not installed; call agent.handle() directly")

    async def agent_node(state: TurnState) -> dict[str, Any]:
        result = await agent.handle(
            state["user_input"],
            context_id=state.get("context_id", ""),
            correlation_id=state.get("correlation_id", ""),
        )
        return {"result": result}

    graph = StateGraph(TurnState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile(
        checkpointer=checkpointer or MemorySaver(),
        recursion_limit=DEFAULT_RECURSION_LIMIT,
    )
