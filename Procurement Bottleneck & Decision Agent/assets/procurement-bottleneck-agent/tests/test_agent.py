"""End-to-end integration tests — orchestration, report, and the HITL approval loop.

Runs fully offline (IBD_TESTING=1): mock tools, deterministic verdict (no live LLM).
"""
import pytest

from app.memory import get_memory_store

pytestmark = pytest.mark.integration


async def test_analyze_seed_scenario_produces_full_report(agent):
    res = await agent.handle("Run the critical-path procurement analysis for project P-INFRA-07",
                             context_id="ctx-seed")
    content = res["content"]
    assert res["pending"] is True
    for section in ["Procurement Blockers", "Situation", "Business Impact",
                    "Recommended Next Steps", "Awaiting Your Approval"]:
        assert section in content, f"missing report section: {section}"
    assert res["action"] == "source_switch"
    assert res["exposure_eur"] >= 25000.0           # material
    assert "CP5" in res["checkpoints"]              # penalty > €10k confirmation
    assert "Urgent" in content and "critical path" in content  # float 0 → critical path (regression guard)
    assert "estimates based on available SAP data" in content  # disclaimer


async def test_approval_executes_and_logs_decision(agent):
    await agent.handle("analyse P-INFRA-07", context_id="ctx-ok")
    res = await agent.handle("approve LIFNR-0010099", context_id="ctx-ok")
    assert res["pending"] is False
    assert res["record_id"] and res["record_id"] != "n/a"
    assert res["spa_task_id"].startswith("SPA-")
    assert "No SAP business object" in res["content"]
    store = get_memory_store()
    assert len(store.all()) == 1
    assert store.all()[0].action_taken == "source_switch"


async def test_source_switch_requires_named_vendor(agent):
    await agent.handle("analyse P-INFRA-07", context_id="ctx-lifnr")
    res = await agent.handle("approve", context_id="ctx-lifnr")  # no LIFNR named
    assert res["pending"] is True
    assert "named" in res["content"].lower()
    assert len(get_memory_store().all()) == 0  # nothing written yet


async def test_rejection_cancels_without_writing(agent):
    await agent.handle("analyse P-INFRA-07", context_id="ctx-no")
    res = await agent.handle("cancel", context_id="ctx-no")
    assert res["pending"] is False
    assert "cancelled" in res["content"].lower()
    assert len(get_memory_store().all()) == 0


async def test_ambiguous_reply_keeps_gate_open(agent):
    await agent.handle("analyse P-INFRA-07", context_id="ctx-amb")
    res = await agent.handle("hmm not sure", context_id="ctx-amb")
    assert res["pending"] is True


def test_parse_query_extracts_identifiers():
    from app.agent import ProcurementConsequenceAgent
    f = ProcurementConsequenceAgent._parse_query("check PO 4500000123 for LIFNR-0010045 on P-INFRA-07")
    assert f["po_number"] == "4500000123"
    assert f["supplier_lifnr"] == "LIFNR-0010045"
    assert f["project_code"] == "P-INFRA-07"


def test_nonissue_report_text():
    from app.agent import ProcurementConsequenceAgent
    txt = ProcurementConsequenceAgent._nonissue_report("PO1", "LIFNR-1", 1)
    assert "on track" in txt.lower()
    assert "PO1" in txt


async def test_backend_failure_is_honest_not_hallucinated(agent, monkeypatch):
    """When the primary SAP read fails, the agent must surface the failure honestly
    and must NOT proceed into the LLM path (which would invent plausible PO data)."""
    from app.agent import ProcurementConsequenceAgent
    from app.resilience import ToolError

    real_call = ProcurementConsequenceAgent._call

    async def fake_call(self, tools, name, breaker, correlation_id, **args):
        if name == "get_open_pr_po_chain":
            return ToolError("quota_exceeded", "quota used up", name)
        return await real_call(self, tools, name, breaker, correlation_id, **args)

    monkeypatch.setattr(ProcurementConsequenceAgent, "_call", fake_call)
    res = await agent.handle("What happens to PO 4500210380 if delivery is delayed?",
                             context_id="ctx-fail")
    content = res["content"]
    assert res["pending"] is False
    assert "unavailable" in content.lower()
    # Must not fabricate: no euro figures, no invented supplier/material names.
    assert "€" not in content
    assert "estimates based on available SAP data" in content


def test_quota_violation_classified_terminal():
    """A sandbox quota violation must be terminal (no retries that burn more quota)."""
    from app.resilience import QuotaExceeded
    assert QuotaExceeded().retryable is False
    assert QuotaExceeded().code == "quota_exceeded"


async def test_delivery_performance_question_not_open_po_list(agent):
    """'Show delivery performance history' must return the supplier's track record,
    not the Open Purchase Orders list (intent-routing regression guard)."""
    res = await agent.handle("Show delivery performance history for this supplier",
                             context_id="ctx-perf")
    content = res["content"]
    assert "Open Purchase Orders" not in content
    assert "on-time" in content.lower() or "track record" in content.lower()
    assert "risk level" in content.lower() or "delivery-risk" in content.lower()
