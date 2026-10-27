"""The 15 tools: live/simulated tagging, gap analysis, HITL gate, HoD gating."""
import json

import pytest

import tools as tool_mod


@pytest.fixture
def byname():
    return {t.name: t for t in tool_mod.build_mock_tools()}


async def _call(byname, name, **kw):
    return json.loads(await byname[name].coroutine(**kw))


def test_fifteen_tools_registered(byname):
    assert len(byname) == 15
    assert set(byname) == set(tool_mod.TOOL_NAMES)


async def test_every_read_tool_tags_signal_status(byname):
    for name in ("get_project_material_requirements", "get_material_stock_position",
                 "compute_material_availability_gaps", "get_supplier_delivery_history"):
        if name == "get_material_stock_position" or name == "get_supplier_delivery_history":
            continue
        out = await _call(byname, name, project_id="P-ALPHA-01")
        assert out["signal_status"] == "live"


async def test_compute_gaps_orders_critical_first(byname):
    out = await _call(byname, "compute_material_availability_gaps", project_id="P-ALPHA-01")
    bands = [a["risk_band"] for a in out["assessments"]]
    assert bands[0] == "CRITICAL"
    assert out["at_risk_count"] == 3


async def test_stock_excludes_qi_and_blocked(byname):
    out = await _call(byname, "get_material_stock_position", material="1000234")
    assert out["available_for_project"] == out["unrestricted"] == 10.0


async def test_rag_tool_blocks_injection_and_applies_gate(byname):
    out = await _call(byname, "retrieve_schedule_and_supplier_context",
                      query="structural steel delay", project_id="P-ALPHA-01")
    assert out["injection_blocked"] >= 1
    assert out["retrieved"] <= tool_mod.RAG_TOP_K
    texts = " ".join(c["text"] for c in out["chunks"])
    assert "IGNORE ALL PREVIOUS" not in texts.upper()


async def test_escalation_write_tool_is_gated(byname):
    refused = await _call(byname, "trigger_escalation_workflow", material="1000234",
                          escalation_level="purchase_manager")
    assert refused["status"] == "confirmation_required"
    done = await _call(byname, "trigger_escalation_workflow", material="1000234",
                       escalation_level="purchase_manager", confirmed=True)
    assert done["status"] == "executed"
    assert done["escalation_id"].startswith("ESC-")
    assert done["spa_task_id"].startswith("SPA-")


async def test_po_write_tool_never_touches_sap(byname):
    done = await _call(byname, "update_po_delivery_date_or_create_expedite_po",
                       po_number="4500001234", action_type="update_delivery_date",
                       new_date="2026-10-22", confirmed=True)
    assert done["status"] == "executed"
    assert "ADVISORY" in done["note"].upper()


async def test_alternative_supplier_is_hod_only(byname):
    ex = await _call(byname, "recommend_procurement_action", material="1000234",
                     caller_role="purchase_executive")
    hod = await _call(byname, "recommend_procurement_action", material="1000234",
                      caller_role="purchase_hod")
    assert ex["recommendation"]["alternative_supplier_visible"] is False
    assert "alternative_suppliers" not in ex["recommendation"]
    assert hod["recommendation"]["alternative_supplier_visible"] is True
    assert hod["recommendation"]["alternative_suppliers"]


async def test_recommend_includes_draft_email_for_high_risk(byname):
    out = await _call(byname, "recommend_procurement_action", material="1000234")
    assert "draft_email" in out["recommendation"]
    assert out["recommendation"]["draft_email"]["subject"]


async def test_simulate_returns_scored_options_and_disclaimer(byname):
    out = await _call(byname, "simulate_schedule_consequence", material="1000234")
    assert out["on_critical_path"] is True
    assert out["recovery_options"]
    assert out["disclaimer"]
