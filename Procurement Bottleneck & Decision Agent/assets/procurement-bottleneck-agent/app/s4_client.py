"""Live S/4HANA OData reads via the SAP Business Accelerator Hub (APIKey).

Used by `SAP_MODE=accelerator_hub` for the BAI end-to-end run against the sandbox's
S/4HANA Cloud `API_*` services. Field mappings were verified against each service's
`$metadata` (see ADARSH_AGENTHON_REFERENCE.md §5.2). Service names are env-overridable
so the same code targets Adarsh's on-prem `OP_*` services in the client landscape.

Advisory/read-only: GET only. Returns the same dict shapes the agent's tools produce,
with `signal_status` 'live' for real reads and 'simulated' where the standard API
lacks the field (vendor risk, penalty clauses). Project/WBS data is NOT available from
these APIs and stays on the mock/Excel project adapter.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from typing import Any

import httpx

from .resilience import QuotaExceeded, classify_http_status

_DATE_RE = re.compile(r"/Date\((\d+)")


def _base() -> str:
    return os.environ.get("S4_BASE_URL", "").rstrip("/")


def _headers() -> dict[str, str]:
    return {"APIKey": os.environ.get("S4_API_KEY", ""), "Accept": "application/json"}


def _svc(env_name: str, default: str) -> str:
    return os.environ.get(env_name, default)


def _parse_date(v: Any) -> str:
    """OData V2 '/Date(ms)/' -> ISO date (YYYY-MM-DD); pass through otherwise."""
    if not v:
        return ""
    m = _DATE_RE.search(str(v))
    if not m:
        return str(v)
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).date().isoformat()


def _days_since(iso: str) -> int:
    try:
        return (datetime.now(timezone.utc).date() - date.fromisoformat(iso)).days
    except Exception:
        return 0


async def _get(client: httpx.AsyncClient, service: str, entityset: str,
               params: dict[str, Any]) -> list[dict[str, Any]]:
    params.setdefault("$format", "json")
    url = f"{_base()}/{service}/{entityset}"
    resp = await client.get(url, params=params, headers=_headers())
    if resp.status_code >= 400:
        # The BAH sandbox returns rate-limit/quota violations as HTTP 500 with a
        # fault body, not 429 — detect it so the resilience layer treats it as a
        # terminal quota error (no pointless retries that burn more quota).
        body = (resp.text or "")[:500].lower()
        if resp.status_code == 429 or "quotaviolation" in body or "rate limit" in body:
            raise QuotaExceeded()
        raise classify_http_status(resp.status_code)
    d = resp.json().get("d", {})
    if isinstance(d, dict) and "results" in d:
        return d["results"]
    return [d] if d else []


# --- tool implementations (names match the agent's tool set) ----------------
async def _enrich_po_row(c: httpx.AsyncClient, po_svc: str, h: dict[str, Any]) -> dict[str, Any]:
    """Build one PR->PO chain row from a PO header by fetching its first item + schedule line."""
    po = h.get("PurchaseOrder")
    items = await _get(c, po_svc, "A_PurchaseOrderItem",
                       {"$top": 1, "$filter": f"PurchaseOrder eq '{po}'"})
    it = items[0] if items else {}
    sched = await _get(c, po_svc, "A_PurchaseOrderScheduleLine",
                       {"$top": 1, "$filter": f"PurchasingDocument eq '{po}'"})
    sl = sched[0] if sched else {}
    return {
        "po_number": po, "po_item": it.get("PurchaseOrderItem"),
        "supplier_lifnr": h.get("Supplier"),
        "material_number": it.get("Material"),
        "material_category": it.get("MaterialGroup") or "DEFAULT",
        "po_net_value_eur": float(it.get("NetPriceAmount") or 0),
        "expected_lead_time_days_plifz": 0,
        "delivery_due_date": _parse_date(sl.get("ScheduleLineDeliveryDate")),
        "po_issued_date": _parse_date(h.get("PurchaseOrderDate")),
        "last_confirmation_event": None,
        "delivery_complete_flag_elikz": it.get("IsCompletelyDelivered"),
        "deletion_flag_loekz": it.get("PurchasingDocumentDeletionCode", ""),
    }


async def get_open_pr_po_chain(po_number: str = "", project_code: str = "",
                               supplier_lifnr: str = "", top: int = 100, **_: Any) -> dict[str, Any]:
    po_svc = _svc("S4_SVC_PO", "API_PURCHASEORDER_PROCESS_SRV")
    async with httpx.AsyncClient(timeout=30) as c:
        # Specific PO: return the single enriched chain.
        if po_number:
            hdr = await _get(c, po_svc, f"A_PurchaseOrder('{po_number}')", {})
            if not hdr:
                return {"signal_status": "live", "value": []}
            return {"signal_status": "live", "value": [await _enrich_po_row(c, po_svc, hdr[0])]}
        # List/discovery: pull several open POs so the dashboard shows a real worklist,
        # not a single row. Capped to keep the live scan latency bounded. Newest-first
        # so the worklist surfaces current POs (which carry materials/dates) rather than
        # the oldest archived documents; falls back to default order if $orderby is unsupported.
        list_n = max(1, min(int(top or 6), 6))
        base_params: dict[str, Any] = {"$top": list_n,
                                       "$select": "PurchaseOrder,Supplier,PurchaseOrderDate"}
        if supplier_lifnr:
            base_params["$filter"] = f"Supplier eq '{supplier_lifnr}'"
        try:
            hdrs = await _get(c, po_svc, "A_PurchaseOrder",
                              {**base_params, "$orderby": "PurchaseOrderDate desc"})
        except Exception:
            hdrs = await _get(c, po_svc, "A_PurchaseOrder", base_params)
        rows: list[dict[str, Any]] = []
        for h in hdrs:
            try:
                rows.append(await _enrich_po_row(c, po_svc, h))
            except Exception:
                continue
        return {"signal_status": "live", "value": rows}


async def detect_supplier_silence(po_number: str = "", supplier_lifnr: str = "",
                                   top: int = 100, **_: Any) -> dict[str, Any]:
    po_svc = _svc("S4_SVC_PO", "API_PURCHASEORDER_PROCESS_SRV")
    md_svc = _svc("S4_SVC_MATDOC", "API_MATERIAL_DOCUMENT_SRV")
    async with httpx.AsyncClient(timeout=30) as c:
        po_issue = ""
        if po_number:
            hdr = await _get(c, po_svc, f"A_PurchaseOrder('{po_number}')", {"$select": "PurchaseOrderDate"})
            if hdr:
                po_issue = _parse_date(hdr[0].get("PurchaseOrderDate"))
        grns: list[dict[str, Any]] = []
        if po_number:
            grns = await _get(c, md_svc, "A_MaterialDocumentItem",
                              {"$top": 50, "$select": "MaterialDocument,MaterialDocumentYear",
                               "$filter": f"PurchaseOrder eq '{po_number}' and GoodsMovementType eq '101'"})
        last_grn = ""
        if grns:
            g = grns[0]
            try:
                hd = await _get(c, md_svc,
                                f"A_MaterialDocumentHeader(MaterialDocument='{g.get('MaterialDocument')}',"
                                f"MaterialDocumentYear='{g.get('MaterialDocumentYear')}')",
                                {"$select": "PostingDate"})
                if hd:
                    last_grn = _parse_date(hd[0].get("PostingDate"))
            except Exception:
                pass
        silence = _days_since(last_grn) if last_grn else (_days_since(po_issue) if po_issue else 0)
        return {"signal_status": "live", "value": [{
            "po_number": po_number, "supplier_lifnr": supplier_lifnr,
            "silence_duration_days": silence,
            "days_since_po_issue": _days_since(po_issue) if po_issue else 0,
            "last_order_ack_vgabe1": None, "last_grn_date": last_grn or None,
            "expected_ack_window_days": 3,
            "composite_silence_score": round(min(1.0, silence / 14.0), 2) if silence else 0.0,
        }]}


async def get_source_and_contract_dependencies(material_number: str = "", plant: str = "",
                                                top: int = 100, **_: Any) -> dict[str, Any]:
    ir_svc = _svc("S4_SVC_INFORECORD", "API_INFORECORD_PROCESS_SRV")
    bp_svc = _svc("S4_SVC_BP", "API_BUSINESS_PARTNER")
    ct_svc = _svc("S4_SVC_CONTRACT", "API_PURCHASECONTRACT_PROCESS_SRV")
    alts: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as c:
        if material_number:
            irs = await _get(c, ir_svc, "A_PurchasingInfoRecord",
                             {"$top": 3, "$filter": f"Material eq '{material_number}' and IsDeleted eq false",
                              "$select": "PurchasingInfoRecord,Supplier,AvailabilityStartDate,"
                                         "AvailabilityEndDate,IsRegularSupplier"})
            for ir in irs:
                sup = ir.get("Supplier")
                blocked = False
                contracted = False
                try:
                    s = await _get(c, bp_svc, f"A_Supplier('{sup}')", {"$select": "PurchasingIsBlocked"})
                    blocked = bool(s[0].get("PurchasingIsBlocked")) if s else False
                except Exception:
                    pass
                try:
                    ct = await _get(c, ct_svc, "A_PurchaseContract",
                                    {"$top": 1, "$filter": f"Supplier eq '{sup}'", "$select": "PurchaseContract"})
                    contracted = bool(ct)
                except Exception:
                    pass
                alts.append({
                    "supplier_lifnr": sup, "contracted": contracted, "has_pinfo_record": True,
                    "on_time_rate": 0.0, "lead_time_days": None, "purchasing_blocked": blocked,
                    "valid_from": _parse_date(ir.get("AvailabilityStartDate")),
                    "valid_to": _parse_date(ir.get("AvailabilityEndDate")),
                })
    return {"signal_status": "live", "value": [{
        "material_number": material_number, "plant": plant,
        "current_supplier_lifnr": None, "fixed_source": False, "alternatives": alts,
    }]}


async def get_procurement_contract_terms(supplier_lifnr: str = "", material_number: str = "",
                                         top: int = 100, **_: Any) -> dict[str, Any]:
    ct_svc = _svc("S4_SVC_CONTRACT", "API_PURCHASECONTRACT_PROCESS_SRV")
    async with httpx.AsyncClient(timeout=30) as c:
        cts: list[dict[str, Any]] = []
        if supplier_lifnr:
            cts = await _get(c, ct_svc, "A_PurchaseContract",
                             {"$top": 1, "$filter": f"Supplier eq '{supplier_lifnr}'",
                              "$select": "PurchaseContract,ValidityStartDate,ValidityEndDate,"
                                         "PurchaseContractTargetAmount"})
    if not cts:
        return {"signal_status": "live", "value": []}
    ct = cts[0]
    return {"signal_status": "live", "value": [{
        "supplier_lifnr": supplier_lifnr, "contract_source": "erp",
        "contract_ref": ct.get("PurchaseContract"),
        "penalty_clause_eur": 0.0, "liquidated_damages_per_day_eur": 0.0, "force_majeure": None,
        "valid_from": _parse_date(ct.get("ValidityStartDate")),
        "valid_to": _parse_date(ct.get("ValidityEndDate")),
        "_note": "penalty / liquidated damages are not in the standard contract OData (absent/simulated)",
    }]}


async def get_vendor_delivery_performance(supplier_lifnr: str = "", material_category: str = "",
                                          top: int = 100, **_: Any) -> dict[str, Any]:
    bp_svc = _svc("S4_SVC_BP", "API_BUSINESS_PARTNER")
    blocked = False
    name = ""
    async with httpx.AsyncClient(timeout=30) as c:
        if supplier_lifnr:
            try:
                s = await _get(c, bp_svc, f"A_Supplier('{supplier_lifnr}')",
                               {"$select": "PurchasingIsBlocked,SupplierName"})
                if s:
                    blocked = bool(s[0].get("PurchasingIsBlocked"))
                    name = s[0].get("SupplierName", "")
            except Exception:
                pass
    # standard OData has no delivery-timeliness metrics -> heuristic, labelled simulated
    return {"signal_status": "simulated", "value": [{
        "supplier_lifnr": supplier_lifnr, "supplier_name": name,
        "material_category": material_category,
        "supplier_delivery_risk_score": 90 if blocked else 50,
        "on_time_rate": 0.5, "deliveries_last_12m": None, "late_deliveries": None, "avg_days_late": None,
        "purchasing_block_sperm": "X" if blocked else "",
        "external_risk_feed": {"signal_status": "simulated", "distress_flag": False},
        "_note": "delivery-risk heuristic; standard OData lacks on-time metrics (simulated)",
    }]}
