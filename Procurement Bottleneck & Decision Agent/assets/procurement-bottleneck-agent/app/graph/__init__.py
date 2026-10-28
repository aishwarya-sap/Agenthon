"""LangGraph orchestration package (build standard seam).

The graph wraps the agent's existing deterministic turn so the repo matches the
template's `build_graph()` structure (typed state, checkpointer, recursion limit)
without changing turn behaviour. The langgraph import is guarded so the framework-free
offline test suite still imports and runs.
"""
from .orchestrator import DEFAULT_RECURSION_LIMIT, build_graph, langgraph_available
from .state import TurnState

__all__ = ["TurnState", "build_graph", "langgraph_available", "DEFAULT_RECURSION_LIMIT"]
