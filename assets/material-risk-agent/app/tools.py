"""The 15 material-risk tools exposed to the LLM (Design PDF · tool surface).

Each tool is a LangChain ``StructuredTool`` whose body runs deterministic
``domain`` logic and returns a compact JSON string tagged with
``signal_status`` ("live" from SAP-equivalent reads, "simulated" for the
external enrichment feed). The LLM selects and sequences tools and relays
their values; it never computes the numbers itself.

The three write tools (side_effect) are gated: they refuse unless called with
``confirmed=True`` (HITL). In production the mock reads are replaced by Agent
Gateway MCP calls with the same tool names/shapes.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Awaitable, Callable

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from domain import data, memory, prediction, recommend, sanitize, scoring
from domain.hitl import gate_write
from domain.simulation import SimulationInput, simulate

RAG_SIMILARITY_GATE = 0.82
RAG_TOP_K = 4

# Price proxy (EUR per base UoM) so simulation can cost expedite/alt premiums.
_UNIT_PRICE = {"1000234": 900.0, "1000567": 45.0, "1000890": 28.0, "1001234": 120.0}


def _dump(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False, default=str)


def _live(payload: dict) -> dict:
    payload.setdefault("signal_status", "live")
    return payload


async def _assess(material: str) -> dict | None:
    acts = data.get_activities(material=material)
    if not acts:
        return None
    activity = acts[0]
    stock = await data.get_stock_async(material)
    orders = await data.get_orders_async(material=material)
    primary = next((o for o in orders if o["doc_type"] == "PO"), None)
    gr = await data.get_gr_history_async(primary["vendor"], material) if primary else []
    return scoring.assess_material(activity, stock, orders, gr)


def _po_value(material: str, qty: float) -> float:
    return round(qty * _UNIT_PRICE.get(material, 500.0), 2)


# --- args schemas -----------------------------------------------------------
class ProjectArgs(BaseModel):
    project_id: str = Field("P-ALPHA-01", description="Project identifier, e.g. P-ALPHA-01")


class MaterialArgs(BaseModel):
    material: str = Field(..., description="SAP material number, e.g. 1000234")


class OrdersArgs(BaseModel):
    material: str | None = Field(None, description="Optional material number to filter open POs/PRs")


class SupplierArgs(BaseModel):
    vendor: str = Field(..., description="SAP vendor number, e.g. 1001")
    material: str = Field(..., description="SAP material number, e.g. 1000234")


class RagArgs(BaseModel):
    query: str = Field(..., description="Natural-language retrieval query")
    project_id: str | None = Field(None, description="Optional project filter")
    vendor_id: str | None = Field(None, description="Optional vendor filter")


class RecommendArgs(BaseModel):
    material: str = Field(..., description="SAP material number")
    caller_role: str = Field("purchase_executive",
                             description="Caller role: purchase_executive | purchase_manager | purchase_hod | project_manager")


class EscalationArgs(BaseModel):
    material: str = Field(..., description="SAP material number at risk")
    escalation_level: str = Field("purchase_manager",
                                  description="Target: purchase_manager | project_management")
    confirmed: bool = Field(False, description="Must be true (set only after explicit human approval) to execute")


class MemoryWriteArgs(BaseModel):
    vendor: str = Field(..., description="SAP vendor number")
    material: str = Field(..., description="SAP material number")
    action_type: str = Field(..., description="expedite | split_delivery | alternative_source | escalation")
    days_recovered: int = Field(0, description="Schedule days recovered by the intervention")
    confirmed: bool = Field(False, description="Must be true (only after explicit human approval) to execute")


class PoWriteArgs(BaseModel):
    po_number: str = Field(..., description="PO number to update, e.g. 4500001234")
    action_type: str = Field("update_delivery_date", description="update_delivery_date | create_expedite_po")
    new_date: str | None = Field(None, description="New confirmed delivery date (ISO) when updating")
    confirmed: bool = Field(False, description="Must be true (only after explicit human approval) to execute")


# --- tool bodies ------------------------------------------------------------
async def _get_project_material_requirements(project_id: str = "P-ALPHA-01", **_: Any) -> str:
    rows = data.get_activities(project_id=project_id)
    return _dump(_live({"project_id": project_id, "requirements": rows, "count": len(rows)}))


async def _parse_excel_project_schedule(project_id: str = "P-ALPHA-01", **_: Any) -> str:
    rows = data.get_activities(project_id=project_id)
    return _dump(_live({
        "project_id": project_id, "template_columns": data.EXCEL_TEMPLATE_COLUMNS,
        "source": "EXCEL", "activities": rows, "count": len(rows),
    }))


async def _get_material_stock_position(material: str, **_: Any) -> str:
    stock = await data.get_stock_async(material)
    stock["available_for_project"] = stock.get("unrestricted", 0.0)  # QI/blocked excluded
    return _dump(_live({"material": material, **stock}))


async def _get_open_purchase_orders_and_prs(material: str | None = None, **_: Any) -> str:
    return _dump(_live({"material": material, "orders": await data.get_orders_async(material=material)}))


async def _get_consolidation_material_master(material: str, **_: Any) -> str:
    return _dump(_live({"material": material, "material_master": data.get_material_master(material)}))


async def _compute_material_availability_gaps(project_id: str = "P-ALPHA-01", **_: Any) -> str:
    acts = data.get_activities(project_id=project_id)
    assessments = []
    for a in acts:
        stock = await data.get_stock_async(a["material"])
        orders = await data.get_orders_async(material=a["material"])
        primary = next((o for o in orders if o["doc_type"] == "PO"), None)
        gr = await data.get_gr_history_async(primary["vendor"], a["material"]) if primary else []
        assessments.append(scoring.assess_material(a, stock, orders, gr))
    order = {scoring.CRITICAL: 0, scoring.HIGH: 1, scoring.MEDIUM: 2, scoring.LOW: 3, scoring.NONE: 4}
    assessments.sort(key=lambda x: order.get(x["risk_band"], 9))
    at_risk = [x for x in assessments if x["at_risk"]]
    return _dump(_live({
        "project_id": project_id, "at_risk_count": len(at_risk),
        "assessments": assessments,
    }))


async def _get_supplier_delivery_history(vendor: str, material: str, **_: Any) -> str:
    gr = await data.get_gr_history_async(vendor, material)
    return _dump(_live({
        "vendor": vendor, "material": material, "deliveries": gr,
        "on_time_rate": scoring.on_time_rate(gr), "chronic_late": scoring.is_chronic_late(gr),
    }))


async def _predict_delivery_outcome(vendor: str, material: str, **_: Any) -> str:
    gr = await data.get_gr_history_async(vendor, material)
    primary = await data.primary_order_for_async(material)
    confirmed = primary["confirmed_delivery_date"] if primary else None
    pred = prediction.predict_delivery(gr, confirmed)
    return _dump(_live({"vendor": vendor, "material": material,
                        "confirmed_delivery_date": confirmed, **pred}))


async def _simulate_schedule_consequence(material: str, **_: Any) -> str:
    a = await _assess(material)
    if not a:
        return _dump(_live({"material": material, "error": "no scheduled activity for material"}))
    store = memory.get_memory_store()
    alts = data.get_alt_suppliers(material)
    inp = SimulationInput(
        material=material,
        supply_gap_days=a["delivery_gap_days"],
        float_remaining_days=a["float_days"],
        successor_count=len(data.get_activities(material=material)[0].get("successors", [])),
        supplier_responsiveness=store.supplier_responsiveness(a.get("vendor") or "", material),
        alt_lead_time_days=alts[0]["planned_delivery_days"] if alts else None,
        po_value=_po_value(material, a["required_qty"]),
    )
    return _dump(_live(simulate(inp).as_dict()))


async def _retrieve_schedule_and_supplier_context(query: str, project_id: str | None = None,
                                                   vendor_id: str | None = None, **_: Any) -> str:
    chunks = data.get_rag_chunks(query, project_id=project_id, vendor_id=vendor_id)
    chunks.sort(key=lambda c: c.get("similarity", 0.0), reverse=True)
    clean, flagged = sanitize.sanitize_chunks(chunks, RAG_SIMILARITY_GATE)
    return _dump(_live({
        "query": query, "similarity_gate": RAG_SIMILARITY_GATE, "top_k": RAG_TOP_K,
        "chunks": clean[:RAG_TOP_K], "retrieved": len(clean[:RAG_TOP_K]),
        "injection_blocked": len(flagged),
    }))


async def _recommend_procurement_action(material: str, caller_role: str = "purchase_executive", **_: Any) -> str:
    a = await _assess(material)
    if not a:
        return _dump(_live({"material": material, "error": "no scheduled activity for material"}))
    sim = json.loads(await _simulate_schedule_consequence(material))
    rec = recommend.recommend(a, sim, caller_role=caller_role)
    if rec["risk_band"] in (scoring.CRITICAL, scoring.HIGH):
        gr = await data.get_gr_history_async(a.get("vendor") or "", material)
        primary = await data.primary_order_for_async(material)
        pred = prediction.predict_delivery(gr, primary["confirmed_delivery_date"] if primary else None)
        rec["draft_email"] = recommend.draft_expedite_email({**a, "po_number": a.get("po_number")}, pred)
    if rec["alternative_supplier_visible"]:
        rec["alternative_suppliers"] = data.get_alt_suppliers(material)
    return _dump(_live({"assessment": a, "recommendation": rec}))


async def _draft_supplier_expedite_communication(material: str, **_: Any) -> str:
    a = await _assess(material)
    if not a:
        return _dump(_live({"material": material, "error": "no scheduled activity for material"}))
    gr = await data.get_gr_history_async(a.get("vendor") or "", material)
    primary = await data.primary_order_for_async(material)
    pred = prediction.predict_delivery(gr, primary["confirmed_delivery_date"] if primary else None)
    return _dump(_live({"material": material,
                        "draft_email": recommend.draft_expedite_email({**a, "po_number": a.get("po_number")}, pred)}))


# --- write tools (HITL-gated) ----------------------------------------------
async def _trigger_escalation_workflow(material: str, escalation_level: str = "purchase_manager",
                                       confirmed: bool = False, **_: Any) -> str:
    payload = {"material": material, "escalation_level": escalation_level}
    gated = gate_write(confirmed, "trigger_escalation_workflow", payload)
    if gated:
        return _dump(gated)
    a = (await _assess(material)) or {}
    record = {
        "status": "executed", "action": "trigger_escalation_workflow",
        "escalation_id": f"ESC-{uuid.uuid4().hex[:8].upper()}",
        "spa_task_id": f"SPA-{uuid.uuid4().hex[:10].upper()}",
        "recipient_role": escalation_level, "material": material,
        "project_id": a.get("project_id"), "activity_id": a.get("activity_id"),
        "float_days": a.get("float_days"), "risk_band": a.get("risk_band"),
        "note": "Advisory escalation notification — no SAP business object modified.",
        "signal_status": "live",
    }
    return _dump(record)


async def _write_intervention_outcome_to_memory(vendor: str, material: str, action_type: str,
                                                days_recovered: int = 0, confirmed: bool = False, **_: Any) -> str:
    payload = {"vendor": vendor, "material": material, "action_type": action_type,
               "days_recovered": days_recovered}
    gated = gate_write(confirmed, "write_intervention_outcome_to_memory", payload)
    if gated:
        return _dump(gated)
    rec = memory.get_memory_store().record(memory.INTERVENTION_OUTCOME, {
        **payload, "float_restored": days_recovered > 0,
    })
    return _dump({"status": "executed", "action": "write_intervention_outcome_to_memory",
                  "record": rec, "signal_status": "live"})


async def _update_po_delivery_date_or_create_expedite_po(po_number: str, action_type: str = "update_delivery_date",
                                                         new_date: str | None = None, confirmed: bool = False, **_: Any) -> str:
    payload = {"po_number": po_number, "action_type": action_type, "new_date": new_date}
    gated = gate_write(confirmed, "update_po_delivery_date_or_create_expedite_po", payload)
    if gated:
        return _dump(gated)
    # Advisory demo: returns the change that WOULD be posted — never writes to SAP.
    return _dump({
        "status": "executed", "action": "update_po_delivery_date_or_create_expedite_po",
        "po_number": po_number, "action_type": action_type, "new_date": new_date,
        "sap_change_document": f"CDHDR-{uuid.uuid4().hex[:8].upper()}",
        "note": "ADVISORY demo — simulated SAP change document; no live PO was modified.",
        "signal_status": "live",
    })


_SPECS: list[tuple[str, str, type[BaseModel], Callable[..., Awaitable[str]]]] = [
    ("get_project_material_requirements", "Retrieve project material line items (material, required qty/date, activity, float) for a project.", ProjectArgs, _get_project_material_requirements),
    ("parse_excel_project_schedule", "Parse the Phase-1 Excel project schedule into structured activities with required dates and float.", ProjectArgs, _parse_excel_project_schedule),
    ("get_material_stock_position", "Get unrestricted stock for a material (QI and blocked stock excluded from availability).", MaterialArgs, _get_material_stock_position),
    ("get_open_purchase_orders_and_prs", "Get open POs and PRs with confirmed delivery dates, quantities and vendors.", OrdersArgs, _get_open_purchase_orders_and_prs),
    ("get_consolidation_material_master", "Get material master planning data (safety stock, reorder point, lead time).", MaterialArgs, _get_consolidation_material_master),
    ("compute_material_availability_gaps", "Compute net-availability gaps and risk bands for every material in a project (the core analysis).", ProjectArgs, _compute_material_availability_gaps),
    ("get_supplier_delivery_history", "Get the last deliveries for a vendor x material with on-time rate and chronic-late flag.", SupplierArgs, _get_supplier_delivery_history),
    ("predict_delivery_outcome", "Predict delay range and on-time probability for the current PO from the supplier's delivery history.", SupplierArgs, _predict_delivery_outcome),
    ("simulate_schedule_consequence", "Simulate the schedule and cost consequence of a supply gap and score recovery options.", MaterialArgs, _simulate_schedule_consequence),
    ("retrieve_schedule_and_supplier_context", "RAG retrieval over schedule rows, supplier emails and vendor scorecards (similarity gate + injection/PII sanitised).", RagArgs, _retrieve_schedule_and_supplier_context),
    ("recommend_procurement_action", "Produce a ranked, role-aware recommendation (expedite / escalate / source alternatively). Alternative sourcing is HoD-only.", RecommendArgs, _recommend_procurement_action),
    ("draft_supplier_expedite_communication", "Draft a pre-populated expedite email to the supplier for an at-risk material.", MaterialArgs, _draft_supplier_expedite_communication),
    ("trigger_escalation_workflow", "WRITE (gated): route a risk to Purchase Manager / Project Management. Requires confirmed=true after human approval.", EscalationArgs, _trigger_escalation_workflow),
    ("write_intervention_outcome_to_memory", "WRITE (gated): persist an intervention outcome to institutional memory. Requires confirmed=true after human approval.", MemoryWriteArgs, _write_intervention_outcome_to_memory),
    ("update_po_delivery_date_or_create_expedite_po", "WRITE (gated): update a PO delivery date or create an expedite PO (advisory demo). Requires confirmed=true after human approval.", PoWriteArgs, _update_po_delivery_date_or_create_expedite_po),
]


def build_mock_tools() -> list[BaseTool]:
    """Build the 15 material-risk StructuredTools (used in IBD_TESTING/demo mode)."""
    tools: list[BaseTool] = []
    for name, description, args_model, coro in _SPECS:
        tools.append(StructuredTool(
            name=name, description=description, args_schema=args_model,
            coroutine=coro, handle_tool_error=True,
        ))
    return tools


def build_live_tools() -> list[BaseTool]:
    """Build the 15 tools backed by live S/4 OData via s4_client (IBD_LIVE_S4 mode).

    The domain logic (scoring, simulation, prediction) is identical to mock mode —
    only the data source changes from seeded fixtures to real S/4 API calls.
    Write tools remain HITL-gated and advisory-only.
    """
    from s4_client import (  # lazy import — only needed in live mode
        get_stock_live, get_purchase_orders_live, get_purchase_requisitions_live,
        get_gr_history_live, get_vendor_master_live, get_alt_sources_live,
        DEFAULT_PLANT,
    )

    async def _stock_live(material: str, **_: Any) -> str:
        stock = await get_stock_live(material)
        return _dump(_live({"material": material, **stock}))

    async def _orders_live(material: str | None = None, **_: Any) -> str:
        pos = await get_purchase_orders_live(material)
        prs = await get_purchase_requisitions_live(material)
        return _dump(_live({"material": material, "orders": pos + prs}))

    async def _gr_history_live(vendor: str, material: str, **_: Any) -> str:
        gr = await get_gr_history_live(vendor, material)
        return _dump(_live({
            "vendor": vendor, "material": material, "deliveries": gr,
            "on_time_rate": scoring.on_time_rate(gr),
            "chronic_late": scoring.is_chronic_late(gr),
        }))

    async def _vendor_master_live(material: str, **_: Any) -> str:
        pos = await get_purchase_orders_live(material)
        vendor = pos[0]["vendor"] if pos else "unknown"
        master = await get_vendor_master_live(vendor)
        return _dump(_live({"material": material, **master}))

    async def _alt_sources_live(material: str, caller_role: str = "purchase_executive", **_: Any) -> str:
        a = await _assess(material)
        if not a:
            return _dump(_live({"material": material, "error": "no scheduled activity for material"}))
        alts = await get_alt_sources_live(material, DEFAULT_PLANT)
        rec = recommend.recommend(a, {}, caller_role=caller_role)
        if rec["alternative_supplier_visible"]:
            rec["alternative_suppliers"] = alts
        if rec["risk_band"] in (scoring.CRITICAL, scoring.HIGH):
            gr = await get_gr_history_live(a.get("vendor") or "", material)
            primary = await data.primary_order_for_async(material)
            pred = prediction.predict_delivery(gr, primary["confirmed_delivery_date"] if primary else None)
            rec["draft_email"] = recommend.draft_expedite_email({**a, "po_number": a.get("po_number")}, pred)
        return _dump(_live({"assessment": a, "recommendation": rec}))

    # Override the data-layer tools with live equivalents; keep domain/write tools identical.
    live_overrides: dict[str, Any] = {
        "get_material_stock_position": (MaterialArgs, _stock_live),
        "get_open_purchase_orders_and_prs": (OrdersArgs, _orders_live),
        "get_supplier_delivery_history": (SupplierArgs, _gr_history_live),
        "get_consolidation_material_master": (MaterialArgs, _vendor_master_live),
        "recommend_procurement_action": (RecommendArgs, _alt_sources_live),
    }

    tools: list[BaseTool] = []
    for name, description, args_model, mock_coro in _SPECS:
        if name in live_overrides:
            args_model, coro = live_overrides[name]
        else:
            coro = mock_coro
        tools.append(StructuredTool(
            name=name, description=description, args_schema=args_model,
            coroutine=coro, handle_tool_error=True,
        ))
    return tools


TOOL_NAMES = [name for name, *_ in _SPECS]
