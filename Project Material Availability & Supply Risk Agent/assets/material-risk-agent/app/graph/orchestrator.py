"""LangGraph ``build_graph()`` seam for the Material Risk agent.

Isolates the agent-graph construction in one place so orchestration matches the
template's ``graph/`` structure (the same seam the Procurement agent exposes).

How this differs from the Procurement agent's graph — and why:
  * Procurement wraps a *deterministic* ``handle()`` in a hand-built ``StateGraph``
    with no tools baked in, so its compiled graph is built once and cached.
  * This agent is a real LLM-orchestrated **ReAct** agent: ``create_agent()`` bakes
    the MCP tool set and system prompt into the compiled graph. The tool set is
    (re)loaded from the Agent Gateway before each turn (the user token is resolved
    live from a context var), so the graph is built per turn via this seam rather
    than cached across requests.

The import is guarded for parity with the template; langchain/langgraph are a hard
dependency of this agent at runtime, so ``langgraph_available()`` is normally True.
"""
from __future__ import annotations

from typing import Any, Sequence

from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM

try:  # langchain/langgraph ship on the runtime; guarded for template parity.
    from langchain.agents import create_agent
    from langgraph.graph.state import CompiledStateGraph

    _LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover - agent requires langchain at runtime
    _LANGGRAPH_AVAILABLE = False
    CompiledStateGraph = Any  # type: ignore[assignment,misc]

# Single-agent advisory ReAct turn → a small recursion budget bounds tool-call loops
# so a vague query can't run away.
DEFAULT_RECURSION_LIMIT = 15


def langgraph_available() -> bool:
    """True when langchain/langgraph are importable (deployed runtime)."""
    return _LANGGRAPH_AVAILABLE


def build_graph(
    llm: ChatLiteLLM,
    tools: Sequence[BaseTool],
    system_prompt: str,
    *,
    checkpointer: Any,
    middleware: Sequence[Any] | None = None,
) -> "CompiledStateGraph":
    """Compile a ReAct agent graph for one model in the fallback chain.

    Bakes the given tool set + system prompt into a ``create_agent`` graph wired to
    the shared checkpointer and summarization middleware. Raises RuntimeError if
    langchain/langgraph are unavailable — callers gate on ``langgraph_available()``.
    """
    if not _LANGGRAPH_AVAILABLE:
        raise RuntimeError("langchain/langgraph unavailable; cannot build the agent graph")
    return create_agent(
        llm,
        tools=list(tools),
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        middleware=list(middleware or []),
    )
