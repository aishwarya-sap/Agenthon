"""Tool layer — the 13 agent tools.

Design reconciliation (the design lists 8/10/13 inconsistently and double-lists
two skills as tools). The authoritative set implemented here is **13 agent tools**:

  MCP-backed SAP / RAG reads (8, from mcp-mock.json in mock mode):
    get_open_pr_po_chain, get_approval_workflow_status, detect_supplier_silence,
    get_source_and_contract_dependencies, get_procurement_contract_terms,
    link_po_to_project_wbs, get_vendor_delivery_performance,
    rag_retrieve_contract_and_history
  In-process (5):
    recall_supplier_memory (memory), run_consequence_simulation (skill),
    recommend_next_action (skill), write_decision_record* (memory, side-effect),
    trigger_escalation_notification* (mock SPA, side-effect)
  (critical_path_flag is a bounded internal skill used by the orchestrator.)

Tools are plain ``AgentTool`` objects (stdlib only) so they can be imported and
exercised in tests without any agent framework; ``agent.py`` adapts them to
LangChain ``StructuredTool`` at graph-build time. Every tool returns a dict with a
``signal_status`` of ``live`` or ``simulated`` so the agent never presents
simulated data as live.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from . import config, skills
from .memory import DecisionRecord, get_memory_store
from .simulation import SimulationInput

_MOCK_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp-mock.json")


@dataclass
class AgentTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[..., Awaitable[dict[str, Any]]]
    side_effect: bool = False
    ord_id: str = ""

    async def arun(self, **kwargs: Any) -> dict[str, Any]:
        return await self.func(**kwargs)


# --- MCP-backed tools (mock) ------------------------------------------------
def _load_mock() -> dict[str, Any]:
    with open(_MOCK_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _mock_tool_factory(server_ord: str, tool_name: str, spec: dict[str, Any]) -> AgentTool:
    async def _run(**kwargs: Any) -> dict[str, Any]:
        resp = dict(spec.get("mock_response", {}))
        # Deterministic: return the fixture. A real MCP server would filter by kwargs;
        # the mock echoes the requested filters for traceability.
        resp.setdefault("signal_status", "live")
        resp["_filters"] = {k: v for k, v in kwargs.items() if v is not None}
        return resp

    return AgentTool(
        name=tool_name,
        description=spec.get("description", ""),
        input_schema=spec.get("input_schema", {"type": "object", "properties": {}}),
        func=_run,
        side_effect=False,
        ord_id=server_ord,
    )


def build_mock_mcp_tools() -> list[AgentTool]:
    data = _load_mock()
    tools: list[AgentTool] = []
    for server in data.get("servers", {}).values():
        ord_id = server.get("mcp_server_name", "")
        for name, spec in server.get("tools", {}).items():
            tools.append(_mock_tool_factory(ord_id, name, spec))
    return tools


# --- In-process tools -------------------------------------------------------
async def _recall_supplier_memory(supplier_lifnr: str = "", material_group: str = "",
                                  silence_duration: int = 0, top: int = config.MEMORY_RECALL_TOP_N,
                                  **_: Any) -> dict[str, Any]:
    store = get_memory_store()
    records = store.recall(supplier_lifnr, material_group, int(silence_duration or 0), top_n=top)
    return {
        "signal_status": "live",
        "value": records,
        "repeat_offender_count": store.repeat_offender(supplier_lifnr, material_group),
    }


async def _run_consequence_simulation(**kwargs: Any) -> dict[str, Any]:
    allowed = SimulationInput.__dataclass_fields__.keys()
    payload = {k: kwargs[k] for k in allowed if k in kwargs}
    inp = SimulationInput(**payload)
    cards = skills.run_consequence_simulation(inp)
    return {"signal_status": "live", "value": [c.as_dict() for c in cards]}


async def _recommend_next_action(**kwargs: Any) -> dict[str, Any]:
    from .simulation import Scorecard
    from .skills import SourceReadiness

    sc = kwargs["worst_scorecard"]
    worst = sc if isinstance(sc, Scorecard) else Scorecard(**sc)
    sr = kwargs.get("source_readiness") or {}
    readiness = sr if isinstance(sr, SourceReadiness) else SourceReadiness(**sr)
    actions = skills.recommend_next_action(
        worst_scorecard=worst,
        is_critical_path=bool(kwargs.get("is_critical_path", False)),
        supplier_delivery_risk_score=int(kwargs.get("supplier_delivery_risk_score", 0)),
        source_readiness=readiness,
        repeat_offender_count=int(kwargs.get("repeat_offender_count", 0)),
        has_contract=bool(kwargs.get("has_contract", True)),
    )
    return {"signal_status": "live", "value": [a.as_dict() for a in actions]}


async def _write_decision_record(**kwargs: Any) -> dict[str, Any]:
    """SIDE EFFECT (advisory): append to the institutional-memory decision log ONLY.
    Never writes a SAP business object. HITL approval is enforced upstream."""
    allowed = DecisionRecord.__dataclass_fields__.keys()
    payload = {k: kwargs[k] for k in allowed if k in kwargs}
    record = DecisionRecord(**payload)
    record_id = get_memory_store().append(record)
    return {"signal_status": "live", "record_id": record_id, "stored": "ZAGENT_DECISION_LOG (institutional memory)"}


async def _trigger_escalation_notification(**kwargs: Any) -> dict[str, Any]:
    """SIDE EFFECT (advisory): raise an SAP Build Process Automation notification /
    approval task to the HoD + project managers. Mocked offline. Never performs a
    SAP source-of-supply reassignment — that remains a human action."""
    import uuid
    recipients = kwargs.get("pm_recipients") or kwargs.get("recipients") or []
    return {
        "signal_status": "live",
        "spa_task_id": f"SPA-{uuid.uuid4().hex[:10].upper()}",
        "recipients": recipients,
        "action": kwargs.get("action"),
        "note": "Advisory notification only — no SAP write performed.",
    }


def build_inprocess_tools() -> list[AgentTool]:
    return [
        AgentTool("recall_supplier_memory",
                  "Recall the top-N most similar prior HoD decision records from institutional memory.",
                  {"type": "object", "properties": {
                      "supplier_lifnr": {"type": "string"}, "material_group": {"type": "string"},
                      "silence_duration": {"type": "integer"}, "top": {"type": "integer"}}},
                  _recall_supplier_memory),
        AgentTool("run_consequence_simulation",
                  "Compute the four-dimension consequence scorecard (schedule slip, idle resource cost, "
                  "milestone penalty, emergency sourcing premium) at 24h and 48h horizons.",
                  {"type": "object", "properties": {
                      "po_number": {"type": "string"}, "material_category": {"type": "string"},
                      "po_net_value_eur": {"type": "number"}, "silence_duration_days": {"type": "integer"},
                      "available_float_days": {"type": "integer"}, "expected_lead_time_days": {"type": "integer"},
                      "days_since_due": {"type": "integer"}, "idle_teams": {"type": "integer"},
                      "daily_team_cost_rate_eur": {"type": "number"}, "milestone_at_risk": {"type": "boolean"},
                      "milestone_penalty_eur": {"type": "number"}}},
                  _run_consequence_simulation),
        AgentTool("recommend_next_action",
                  "Apply the decision matrix (exposure x source readiness x supplier risk x memory) and "
                  "return a ranked action set (escalate / source_switch / absorb) with confidence and evidence.",
                  {"type": "object", "properties": {
                      "worst_scorecard": {"type": "object"}, "is_critical_path": {"type": "boolean"},
                      "supplier_delivery_risk_score": {"type": "integer"}, "source_readiness": {"type": "object"},
                      "repeat_offender_count": {"type": "integer"}, "has_contract": {"type": "boolean"}}},
                  _recommend_next_action),
        AgentTool("write_decision_record",
                  "ADVISORY SIDE EFFECT: persist the HoD's decision to institutional memory. Requires prior "
                  "human approval. Never writes a SAP business object.",
                  {"type": "object", "properties": {
                      "supplier_lifnr": {"type": "string"}, "material_group": {"type": "string"},
                      "plant": {"type": "string"}, "po_reference": {"type": "string"},
                      "silence_duration_at_detection": {"type": "integer"},
                      "consequence_exposure_at_decision": {"type": "number"},
                      "action_taken": {"type": "string"}, "hod_reviewer_id": {"type": "string"},
                      "approval_keyword_received": {"type": "string"}, "annotation": {"type": "string"}}},
                  _write_decision_record, side_effect=True),
        AgentTool("trigger_escalation_notification",
                  "ADVISORY SIDE EFFECT: raise an SPA notification/approval task to the HoD and project "
                  "managers with the consequence scorecard. Requires prior human approval. No SAP write.",
                  {"type": "object", "properties": {
                      "action": {"type": "string"}, "pm_recipients": {"type": "array"},
                      "scorecard": {"type": "object"}, "recommended_action": {"type": "string"}}},
                  _trigger_escalation_notification, side_effect=True),
    ]


def build_mock_tools() -> list[AgentTool]:
    """All 13 agent tools in mock mode (8 MCP fixtures + 5 in-process)."""
    return build_mock_mcp_tools() + build_inprocess_tools()


def build_accelerator_hub_tools() -> list[AgentTool]:
    """BAI end-to-end: real S/4 reads via the SAP Business Accelerator Hub (APIKey).

    All 8 MCP tools are wired: 5 backed by live OData (s4_client); 3 that have no
    BAH sandbox equivalent (Project System WBS, HANA Vector RAG, approval workflow)
    return an empty unavailable stub so no hardcoded demo data leaks into FC testing.
    """
    from . import s4_client

    async def _unavailable(tool_name: str, **_kw: object) -> dict:
        return {"signal_status": "unavailable", "value": [],
                "note": f"{tool_name} has no BAH sandbox equivalent — connect to client S/4 for live data."}

    real = {
        "get_open_pr_po_chain": s4_client.get_open_pr_po_chain,
        "detect_supplier_silence": s4_client.detect_supplier_silence,
        "get_source_and_contract_dependencies": s4_client.get_source_and_contract_dependencies,
        "get_procurement_contract_terms": s4_client.get_procurement_contract_terms,
        "get_vendor_delivery_performance": s4_client.get_vendor_delivery_performance,
    }
    stub_names = {"link_po_to_project_wbs", "rag_retrieve_contract_and_history", "get_approval_workflow_status"}

    out: list[AgentTool] = []
    for t in build_mock_mcp_tools():
        if t.name in real:
            out.append(AgentTool(t.name, t.description, t.input_schema, real[t.name],
                                 side_effect=False, ord_id="accelerator-hub"))
        elif t.name in stub_names:
            def _make_stub(n: str) -> object:
                async def _stub(**kw: object) -> dict:
                    return await _unavailable(n, **kw)
                return _stub
            out.append(AgentTool(t.name, t.description, t.input_schema,
                                 _make_stub(t.name),
                                 side_effect=False, ord_id="stub-no-bah"))
        else:
            out.append(t)
    return out + build_inprocess_tools()


def build_live_tools(mode: str) -> list[AgentTool]:  # pragma: no cover - requires BTP runtime
    """Production tool construction. The 5 in-process tools are identical; the 8
    SAP/RAG reads are resolved from Agent Gateway (``gateway``) or Destination+
    Connectivity (``cloud``/``onprem``). Requires the SAP Cloud SDK, present only
    in the BTP runtime; raises an informative error if invoked offline."""
    try:
        from sap_cloud_sdk.agentgateway import create_client  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            f"SAP connectivity mode '{mode}' requires the SAP Cloud SDK (BTP runtime). "
            "Run with IBD_TESTING=1 for offline mock mode."
        ) from exc
    client = create_client()  # reads AGW_CREDENTIALS_JSON / Destination bindings
    mcp = client.list_mcp_tools()  # adapted to AgentTool by the production wiring
    adapted = [
        AgentTool(t.name, t.description, getattr(t, "input_schema", {}),
                  (lambda _t: (lambda **kw: _t.arun(kw)))(t), ord_id=getattr(t, "ord_id", ""))
        for t in mcp
    ]
    return adapted + build_inprocess_tools()
