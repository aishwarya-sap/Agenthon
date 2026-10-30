"""LangGraph `build_graph()` seam.

The compiled graph has one node that invokes the agent's existing `handle()` — the
deterministic intent-routing + LLM-reasoning turn is unchanged. The graph adds the
standard scaffolding the standard template expects:

- typed `TurnState`,
- an in-memory checkpointer keyed by the Joule Context ID (thread_id),
- a bounded `recursion_limit`.

Human-in-the-loop stays on the agent's existing `pending` mechanism (→ A2A
`input-required`), which already resumes the same context on the approval turn; the
graph seam does not re-implement it.

The langgraph import is guarded: offline (tests, no langgraph) `langgraph_available()`
returns False and callers fall back to calling `agent.handle()` directly.
"""
from __future__ import annotations

from typing import Any

from .state import TurnState

try:  # langgraph ships on the CF runtime (requirements.txt); absent in the offline test venv.
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    _LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover - exercised implicitly offline
    _LANGGRAPH_AVAILABLE = False

# Single-agent advisory turn → a small recursion budget is plenty (pattern: Single-Agent).
DEFAULT_RECURSION_LIMIT = 10


def langgraph_available() -> bool:
    """True when langgraph is importable (deployed runtime), False offline."""
    return _LANGGRAPH_AVAILABLE


def build_graph(agent: Any, *, checkpointer: Any | None = None) -> Any:
    """Compile a minimal StateGraph that runs one agent turn.

    Raises RuntimeError if langgraph is not installed — callers must gate on
    ``langgraph_available()`` and fall back to ``agent.handle()``.
    """
    if not _LANGGRAPH_AVAILABLE:
        raise RuntimeError("langgraph is not installed; use agent.handle() directly")

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
    return graph.compile(checkpointer=checkpointer or MemorySaver())
