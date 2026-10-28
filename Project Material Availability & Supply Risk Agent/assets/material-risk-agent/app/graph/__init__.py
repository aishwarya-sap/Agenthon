"""LangGraph orchestration package (build standard seam) for the Material Risk agent.

Isolates the ReAct graph construction (``create_agent``) behind ``build_graph()`` so
the repo matches the template's ``graph/`` structure. See ``orchestrator.py`` for why
this agent builds the graph per turn (per-request MCP tools) rather than caching it
across requests like the Procurement agent's deterministic ``handle()``-wrapping graph.
"""
from .orchestrator import DEFAULT_RECURSION_LIMIT, build_graph, langgraph_available
from .state import make_run_config

__all__ = [
    "build_graph",
    "langgraph_available",
    "DEFAULT_RECURSION_LIMIT",
    "make_run_config",
]
