"""One unit test per tool (13 tools: 8 MCP-backed + 5 in-process)."""
import pytest

from app.memory import DecisionRecord, get_memory_store
from app.mcp_tools import get_mcp_tools

pytestmark = pytest.mark.unit


async def _tool(name):
    tools = await get_mcp_tools()
    t = next(t for t in tools if t.name == name)
    return t


async def test_tool_count_is_thirteen():
    tools = await get_mcp_tools()
    assert len(tools) == 13
    names = {t.name for t in tools}
    assert {"write_decision_record", "trigger_escalation_notification"} <= names


async def test_get_open_pr_po_chain():
    t = await _tool("get_open_pr_po_chain")
    r = await t.arun(po_number="4500000123", top=100)
    assert r["value"][0]["supplier_lifnr"] == "LIFNR-0010045"
    assert r["signal_status"] == "live"


async def test_get_approval_workflow_status():
    r = await (await _tool("get_approval_workflow_status")).arun(document_number="4500000123")
    assert r["value"][0]["release_status"] == "FULLY_RELEASED"


async def test_detect_supplier_silence():
    r = await (await _tool("detect_supplier_silence")).arun(po_number="4500000123")
    assert r["value"][0]["silence_duration_days"] == 11


async def test_get_source_and_contract_dependencies():
    r = await (await _tool("get_source_and_contract_dependencies")).arun(material_number="MAT-STRUCT-STEEL-01")
    assert r["value"][0]["alternatives"][0]["supplier_lifnr"] == "LIFNR-0010099"


async def test_get_procurement_contract_terms():
    r = await (await _tool("get_procurement_contract_terms")).arun(supplier_lifnr="LIFNR-0010045")
    assert r["value"][0]["penalty_clause_eur"] == 40000.0


async def test_link_po_to_project_wbs():
    r = await (await _tool("link_po_to_project_wbs")).arun(po_number="4500000123")
    assert r["value"][0]["available_float_days"] == 0
    assert r["value"][0]["critical_path"] is True


async def test_get_vendor_delivery_performance():
    r = await (await _tool("get_vendor_delivery_performance")).arun(supplier_lifnr="LIFNR-0010045")
    assert r["value"][0]["supplier_delivery_risk_score"] == 78


async def test_rag_retrieve_contract_and_history():
    r = await (await _tool("rag_retrieve_contract_and_history")).arun(query="penalty", supplier_lifnr="LIFNR-0010045")
    assert any(c["similarity"] >= 0.82 for c in r["value"])


async def test_recall_supplier_memory_empty():
    r = await (await _tool("recall_supplier_memory")).arun(supplier_lifnr="LIFNR-0010045",
                                                           material_group="STEEL", silence_duration=11)
    assert r["value"] == []
    assert r["repeat_offender_count"] == 0


async def test_run_consequence_simulation_tool():
    r = await (await _tool("run_consequence_simulation")).arun(
        po_number="PO1", material_category="STEEL", po_net_value_eur=180000.0,
        silence_duration_days=11, available_float_days=0, expected_lead_time_days=21,
        days_since_due=0, idle_teams=2, daily_team_cost_rate_eur=8500.0,
        milestone_at_risk=True, milestone_penalty_eur=40000.0)
    assert len(r["value"]) == 2  # 24h + 48h
    assert r["value"][0]["total_consequence_exposure_eur"] > 0


async def test_recommend_next_action_tool():
    from app.simulation import Scorecard
    sc = Scorecard("PO1", 48, 8, 136000.0, 24000.0, 32400.0, 192400.0, ["x"]).as_dict()
    r = await (await _tool("recommend_next_action")).arun(
        worst_scorecard=sc, is_critical_path=True, supplier_delivery_risk_score=78,
        source_readiness={"alternative_available": True, "alternative_contracted": True,
                          "alternative_lifnr": "LIFNR-0010099", "has_pinfo_record": True,
                          "purchasing_blocked": False, "alternative_on_time_rate": 0.94},
        repeat_offender_count=0, has_contract=True)
    assert r["value"][0]["action"] == "source_switch"


async def test_write_decision_record_tool_is_side_effect():
    t = await _tool("write_decision_record")
    assert t.side_effect is True
    r = await t.arun(supplier_lifnr="LIFNR-0010045", material_group="STEEL", plant="1710",
                     po_reference="4500000123", silence_duration_at_detection=11,
                     consequence_exposure_at_decision=192400.0, action_taken="escalate",
                     hod_reviewer_id="HOD-ADARSH", approval_keyword_received="approve")
    assert r["record_id"]
    assert len(get_memory_store().all()) == 1


async def test_trigger_escalation_notification_tool_is_side_effect():
    t = await _tool("trigger_escalation_notification")
    assert t.side_effect is True
    r = await t.arun(action="escalate", pm_recipients=["PM-ANDERSON"])
    assert r["spa_task_id"].startswith("SPA-")
    assert "no sap write" in r["note"].lower()
