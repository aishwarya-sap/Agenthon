"""Tests for the LangGraph orchestration seam (`app/graph`).

Offline (no langgraph in the test venv) the seam must degrade gracefully: the agent
turn still runs via the direct fallback in `run_turn`. When langgraph IS installed, the
compiled graph is exercised. Both paths must return the same result shape.
"""
import pytest

from app.agent import ProcurementConsequenceAgent
from app.agent_executor import run_turn
from app.graph import build_graph, langgraph_available

pytestmark = pytest.mark.integration


async def test_run_turn_works_regardless_of_langgraph(agent):
    """run_turn produces a valid result whether the graph seam or the fallback is used."""
    res = await run_turn(agent, "Which suppliers have gone silent on active purchase orders?",
                         context_id="ctx-graph")
    assert res.get("content")
    assert res.get("context_id") == "ctx-graph"


def test_build_graph_guarded_when_langgraph_absent():
    """Offline, the seam reports unavailable and build_graph refuses rather than crashing imports."""
    if langgraph_available():
        pytest.skip("langgraph installed — graph path is exercised by run_turn")
    with pytest.raises(RuntimeError):
        build_graph(ProcurementConsequenceAgent())


@pytest.mark.skipif(not langgraph_available(), reason="langgraph not installed in offline test venv")
async def test_compiled_graph_runs_turn():
    """When langgraph is present, the compiled graph runs one turn and returns the result."""
    agent = ProcurementConsequenceAgent()
    graph = build_graph(agent)
    out = await graph.ainvoke(
        {"user_input": "What are the current procurement blockers?", "context_id": "ctx-g2",
         "correlation_id": "c2"},
        config={"recursion_limit": 10, "configurable": {"thread_id": "ctx-g2"}},
    )
    assert out["result"].get("content")
