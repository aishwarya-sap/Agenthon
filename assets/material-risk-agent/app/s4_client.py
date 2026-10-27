"""S/4HANA OData client for the Material Risk agent — VERIFIED entity/field names.

Service + entity + field names below were verified against the SAP Business
Accelerator Hub sandbox ($metadata probe, 2026-10-21). All seven services are
OData **V2**: collections arrive under ``d.results`` and dates as ``/Date(ms)/``.

Two operating modes, selected by environment:

  Sandbox (IBD_LIVE_S4=1, S4_SERVICE_PROFILE=cloud — the default):
      Calls the Accelerator Hub sandbox with an APIKey header. The sandbox
      resolves the S/4HANA Cloud ``API_*`` service names.

  On-prem / production (S4_SERVICE_PROFILE=onprem):
      Routes every OData call through the BTP Destination Service. The user's
      IAS JWT (set by JWTContextMiddleware) is forwarded as X-user-token so the
      Destination Service performs the IAS→S/4 token exchange (OAuth2SAMLBearer
      or PrincipalPropagation, depending on the destination config). The ``OP_*``
      service paths are used (Adarsh on-prem naming).

Service names are resolved through ``config.s4_service()`` so the profile switch
is a single env var, never a code change.
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlencode

import httpx

import config

logger = logging.getLogger(__name__)

SANDBOX_BASE = os.environ.get(
    "S4_BASE_URL",
    "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap",
)
S4_API_KEY = os.environ.get("S4_API_KEY", "")           # Accelerator Hub APIKey (from .env)
S4_DESTINATION = os.environ.get("S4_DESTINATION", "S4_MATERIAL_RISK")  # BTP dest name (on-prem)
DEFAULT_PLANT = os.environ.get("S4_PLANT", "1710")

_TIMEOUT = httpx.Timeout(30.0)

# ---------------------------------------------------------------------------
# Request-scoped S4 data cache — TTL 30 s, keyed by (service, entity, params).
# Eliminates duplicate BAH API calls when the LLM calls multiple tools that
# fetch the same entity (e.g. POs for the same material across several tools).
# ---------------------------------------------------------------------------
_S4_CACHE: dict[str, tuple[list[dict], float]] = {}
_CACHE_TTL = 30.0  # seconds; short enough that a user won't see stale data


def _cache_key(service: str, entity: str, params: dict | None) -> str:
    return f"{service}/{entity}?{json.dumps(params or {}, sort_keys=True)}"


def _cache_get(key: str) -> list[dict] | None:
    entry = _S4_CACHE.get(key)
    if entry and time.time() - entry[1] < _CACHE_TTL:
        return entry[0]
    return None


def _cache_set(key: str, value: list[dict]) -> None:
    _S4_CACHE[key] = (value, time.time())
    # Evict entries older than 2× TTL to keep dict small
    cutoff = time.time() - _CACHE_TTL * 2
    expired = [k for k, (_, ts) in _S4_CACHE.items() if ts < cutoff]
    for k in expired:
        _S4_CACHE.pop(k, None)


def clear_s4_cache() -> None:
    """Flush the request-scoped S4 data cache (used in tests)."""
    _S4_CACHE.clear()


# OData V2 stock-type codes (InventoryStockType).
_STOCK_UNRESTRICTED = "01"
_STOCK_QUALITY_INSPECTION = "02"
_STOCK_BLOCKED = "03"

_DATE_RE = re.compile(r"/Date\((-?\d+)")

# ---------------------------------------------------------------------------
# BTP Destination Service — on-prem transport with Principal Propagation
# ---------------------------------------------------------------------------
# Cache: (resolved_url, s4_access_token, token_expiry_epoch)
# Keyed by (destination_name, user_token_hash) so different users get their
# own exchanged tokens while static dest URL is reused.
_DEST_CACHE: dict[str, tuple[str, str, float]] = {}


def _vcap_destination_creds() -> dict:
    """Parse VCAP_SERVICES to find the Destination service binding credentials."""
    raw = os.environ.get("VCAP_SERVICES", "{}")
    try:
        services = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("VCAP_SERVICES is not valid JSON") from exc
    # CF binds under 'destination' or occasionally 'xsuaa-destination-service'
    bindings = services.get("destination") or services.get("xsuaa-destination-service") or []
    if not bindings:
        raise RuntimeError(
            "No Destination service binding found in VCAP_SERVICES. "
            "Bind the 'destination' service instance to this CF app."
        )
    return bindings[0]["credentials"]


def _dst_service_token(creds: dict) -> str:
    """Obtain an OAuth2 client-credentials token for the Destination service API."""
    resp = httpx.post(
        creds["url"].rstrip("/") + "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": creds["clientid"],
            "client_secret": creds["clientsecret"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _resolve_destination(dest_name: str, user_token: str | None) -> tuple[str, str]:
    """Call the BTP Destination REST API and return (s4_base_url, s4_auth_token).

    Passing ``user_token`` (the IAS JWT from Joule) as ``X-user-token`` triggers
    Principal Propagation: the Destination Service exchanges the IAS token for an
    S/4-scoped credential (SAMLBearer or OAuth2SAMLBearerAssertion), which is
    returned in ``authTokens[0].value``.

    When ``user_token`` is None (technical call, no user context), the destination's
    own OAuth2 client credentials are used — the ``authTokens`` entry still provides
    the ready-to-use Bearer value.
    """
    cache_key = f"{dest_name}:{hash(user_token)}"
    cached = _DEST_CACHE.get(cache_key)
    if cached:
        base_url, s4_token, expiry = cached
        if time.time() < expiry - 60:  # 60 s safety margin
            return base_url, s4_token

    creds = _vcap_destination_creds()
    dst_token = _dst_service_token(creds)

    headers: dict = {"Authorization": f"Bearer {dst_token}"}
    if user_token:
        headers["X-user-token"] = user_token

    resp = httpx.get(
        f"{creds['uri'].rstrip('/')}/destination-configuration/v1/destinations/{dest_name}",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()

    dest_cfg = body.get("destinationConfiguration", {})
    base_url = dest_cfg.get("URL", "").rstrip("/")
    if not base_url:
        raise RuntimeError(f"Destination '{dest_name}' has no URL configured.")

    auth_tokens = body.get("authTokens") or []
    if not auth_tokens:
        raise RuntimeError(
            f"Destination '{dest_name}' returned no authTokens — check the destination "
            "authentication type and that x_user_token.jwks_uri is set."
        )
    token_entry = auth_tokens[0]
    if token_entry.get("error"):
        raise RuntimeError(
            f"Destination '{dest_name}' auth token error: {token_entry['error']}"
        )
    s4_token = token_entry["value"]
    # Cache for the token's remaining lifetime (expires_in field, or 1 hour)
    ttl = int(token_entry.get("expires_in") or 3600)
    _DEST_CACHE[cache_key] = (base_url, s4_token, time.time() + ttl)

    logger.info("Resolved BTP Destination '%s' → %s (PP=%s)", dest_name, base_url, bool(user_token))
    return base_url, s4_token


def clear_destination_cache() -> None:
    """Flush the destination cache (used in tests)."""
    _DEST_CACHE.clear()


# ---------------------------------------------------------------------------
# Core OData GET — branches on S4_SERVICE_PROFILE
# ---------------------------------------------------------------------------

def _parse_odata_date(value: Any) -> str | None:
    """Convert an OData V2 ``/Date(epochMillis)/`` string to an ISO date (UTC)."""
    if not value or not isinstance(value, str):
        return value
    m = _DATE_RE.search(value)
    if not m:
        return value
    from datetime import datetime, timezone
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).date().isoformat()


def _headers() -> dict:
    return {"Accept": "application/json", "APIKey": S4_API_KEY}


def _odata_get(service: str, entity: str, params: dict | None = None) -> list[dict]:
    """GET an OData V2 entity set; return the ``d.results`` (or ``value``) array.

    Cloud/sandbox profile (S4_SERVICE_PROFILE=cloud):
        Calls Accelerator Hub sandbox directly with APIKey header.

    On-prem profile (S4_SERVICE_PROFILE=onprem):
        Routes through BTP Destination Service with the user's IAS JWT as
        X-user-token for Principal Propagation. The Destination Service exchanges
        the token and returns a ready-to-use S/4 Bearer in authTokens[0].

    Results are cached for _CACHE_TTL seconds to eliminate duplicate BAH calls
    within a single LLM turn (the LLM calls several tools that each fetch the same
    material's POs/stock, causing redundant round-trips without the cache).
    """
    key = _cache_key(service, entity, params)
    cached = _cache_get(key)
    if cached is not None:
        logger.debug("S4 cache HIT %s/%s", service, entity)
        return cached

    qs = "?" + urlencode({**(params or {}), "$format": "json"})

    if config.s4_service_profile() == "onprem":
        from mcp_providers.agw import get_user_token
        user_token = get_user_token()
        base_url, s4_token = _resolve_destination(S4_DESTINATION, user_token)
        # On-prem: path is /sap/opu/odata/sap/<service>/<entity>
        url = f"{base_url}/sap/opu/odata/sap/{service}/{entity}{qs}"
        headers = {"Accept": "application/json", "Authorization": f"Bearer {s4_token}"}
    else:
        base_url = SANDBOX_BASE.rstrip("/")
        url = f"{base_url}/{service}/{entity}{qs}"
        headers = _headers()

    logger.info("S/4 OData GET %s", url)
    resp = httpx.get(url, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    d = body.get("d") or body
    result = d.get("results") or d.get("value") or []
    _cache_set(key, result)
    return result


async def _odata_get_async(service: str, entity: str, params: dict | None = None) -> list[dict]:
    """Async wrapper: runs the blocking OData GET in a thread-pool executor so the
    asyncio event loop stays responsive (handles health checks, other requests)
    while the httpx network call is in flight.
    """
    key = _cache_key(service, entity, params)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, functools.partial(_odata_get, service, entity, params)
    )
    return result


# ---------------------------------------------------------------------------
# Stock — API_MATERIAL_STOCK_SRV / A_MatlStkInAcctMod
# Qty is a single field split by InventoryStockType code (01/02/03).
# ---------------------------------------------------------------------------
async def get_stock_live(material: str, plant: str = DEFAULT_PLANT) -> dict:
    rows = await _odata_get_async(
        config.s4_service("material_stock"),
        "A_MatlStkInAcctMod",
        {"$filter": f"Material eq '{material}' and Plant eq '{plant}'",
         "$select": "Material,Plant,StorageLocation,InventoryStockType,"
                    "InventorySpecialStockType,MatlWrhsStkQtyInMatlBaseUnit,MaterialBaseUnit"},
    )
    by_type: dict[str, float] = {}
    for r in rows:
        stype = r.get("InventoryStockType", "")
        qty = float(r.get("MatlWrhsStkQtyInMatlBaseUnit") or 0)
        by_type[stype] = by_type.get(stype, 0.0) + qty
    unrestricted = by_type.get(_STOCK_UNRESTRICTED, 0.0)
    return {
        "plant": plant,
        "unrestricted": unrestricted,
        "quality_inspection": by_type.get(_STOCK_QUALITY_INSPECTION, 0.0),
        "blocked": by_type.get(_STOCK_BLOCKED, 0.0),
        "available_for_project": unrestricted,  # QI/blocked excluded per BR-001
        "base_unit": rows[0].get("MaterialBaseUnit") if rows else None,
    }


# ---------------------------------------------------------------------------
# Purchase orders — API_PURCHASEORDER_PROCESS_SRV
# Three-entity join: item (A_PurchaseOrderItem) + header (Supplier) + schedule
# line (delivery date). Supplier is on the HEADER; delivery date on the SCHEDULE.
# ---------------------------------------------------------------------------
async def get_purchase_orders_live(material: str | None = None,
                             plant: str = DEFAULT_PLANT) -> list[dict]:
    item_filter = f"Material eq '{material}'" if material else f"Plant eq '{plant}'"
    items = await _odata_get_async(
        config.s4_service("purchase_order"),
        "A_PurchaseOrderItem",
        {"$filter": item_filter,
         "$top": "100",  # hard cap — unfiltered plant queries can return thousands of rows
         "$select": ("PurchaseOrder,PurchaseOrderItem,Material,Plant,OrderQuantity,"
                     "NetPriceAmount,IsCompletelyDelivered,"
                     "to_PurchaseOrder/Supplier,to_PurchaseOrder/PurchaseOrderDate,"
                     "to_ScheduleLine/ScheduleLineDeliveryDate,"
                     "to_ScheduleLine/ScheduleLineOrderQuantity"),
         "$expand": "to_PurchaseOrder,to_ScheduleLine"},
    )
    orders: list[dict] = []
    for it in items:
        hdr = it.get("to_PurchaseOrder") or {}
        sched = it.get("to_ScheduleLine") or {}
        sched_rows = sched.get("results", sched) if isinstance(sched, dict) else sched
        first_sched = (sched_rows[0] if isinstance(sched_rows, list) and sched_rows else {}) or {}
        orders.append({
            "po_number": it.get("PurchaseOrder"),
            "po_item": it.get("PurchaseOrderItem"),
            "doc_type": "PO",
            "material": it.get("Material"),
            "vendor": hdr.get("Supplier"),
            "plant": it.get("Plant"),
            "order_qty": float(it.get("OrderQuantity") or 0),
            "confirmed_delivery_date": _parse_odata_date(first_sched.get("ScheduleLineDeliveryDate")),
            "delivery_complete": it.get("IsCompletelyDelivered") is True
                                 or it.get("IsCompletelyDelivered") == "X",  # ELIKZ
            "net_price": float(it.get("NetPriceAmount") or 0),
        })
    return orders


# ---------------------------------------------------------------------------
# Purchase requisitions — API_PURCHASEREQ_PROCESS_SRV / A_PurchaseRequisitionItem
# ---------------------------------------------------------------------------
async def get_purchase_requisitions_live(material: str | None = None) -> list[dict]:
    item_filter = f"Material eq '{material}'" if material else "PurchaseRequisition ne ''"
    items = await _odata_get_async(
        config.s4_service("purchase_requisition"),
        "A_PurchaseRequisitionItem",
        {"$filter": item_filter,
         "$top": "100",  # hard cap — the unfiltered "ne ''" query can return thousands of rows
         "$select": ("PurchaseRequisition,PurchaseRequisitionItem,Material,Plant,"
                     "RequestedQuantity,DeliveryDate,ReleaseCode,ProcessingStatus")},
    )
    reqs: list[dict] = []
    for it in items:
        reqs.append({
            "pr_number": it.get("PurchaseRequisition"),
            "pr_item": it.get("PurchaseRequisitionItem"),
            "doc_type": "PR",
            "material": it.get("Material"),
            "plant": it.get("Plant"),
            "request_qty": float(it.get("RequestedQuantity") or 0),
            "required_date": _parse_odata_date(it.get("DeliveryDate")),
            "release_status": it.get("ReleaseCode") or it.get("ProcessingStatus"),
        })
    return reqs


# ---------------------------------------------------------------------------
# GR history — API_MATERIAL_DOCUMENT_SRV / A_MaterialDocumentItem (mvt 101)
# Posting date + PO ref live on the header (to_MaterialDocumentHeader).
# ---------------------------------------------------------------------------
async def get_gr_history_live(vendor: str, material: str,
                        plant: str = DEFAULT_PLANT, limit: int = 4) -> list[dict]:
    if not vendor or vendor in ("", "unknown"):
        # No vendor to filter on — skip the BAH call, return empty history.
        return []
    items = await _odata_get_async(
        config.s4_service("material_document"),
        "A_MaterialDocumentItem",
        {"$filter": (f"Material eq '{material}' and Plant eq '{plant}'"
                     f" and GoodsMovementType eq '101'"),
         "$select": ("MaterialDocument,MaterialDocumentItem,MaterialDocumentYear,"
                     "Material,Plant,GoodsMovementType,Supplier,QuantityInBaseUnit,"
                     "to_MaterialDocumentHeader/PostingDate,"
                     "to_MaterialDocumentHeader/ReferenceDocument"),
         "$expand": "to_MaterialDocumentHeader",
         "$top": str(limit)},
    )
    history: list[dict] = []
    for it in items:
        hdr = it.get("to_MaterialDocumentHeader") or {}
        history.append({
            "gr_document": it.get("MaterialDocument"),
            "vendor": it.get("Supplier") or vendor,
            "material": it.get("Material"),
            "gr_date": _parse_odata_date(hdr.get("PostingDate")),
            "gr_qty": float(it.get("QuantityInBaseUnit") or 0),
            "po_number": hdr.get("ReferenceDocument") or "",
            "delay_days": None,   # computed downstream vs PO schedule line
        })
    return history


# ---------------------------------------------------------------------------
# Vendor master — API_BUSINESS_PARTNER / A_Supplier
# ---------------------------------------------------------------------------
async def get_vendor_master_live(vendor: str) -> dict:
    if not vendor or vendor in ("", "unknown"):
        return {"vendor": vendor, "name": "unknown", "found": False}
    rows = await _odata_get_async(
        config.s4_service("business_partner"),
        "A_Supplier",
        {"$filter": f"Supplier eq '{vendor}'",
         "$select": "Supplier,SupplierName,SupplierFullName,PurchasingIsBlocked,"
                    "SupplierAccountGroup"},
    )
    if not rows:
        return {"vendor": vendor, "name": "unknown", "found": False}
    bp = rows[0]
    return {
        "vendor": vendor,
        "name": bp.get("SupplierFullName") or bp.get("SupplierName"),
        "purchasing_blocked": bp.get("PurchasingIsBlocked") in (True, "X"),
        "account_group": bp.get("SupplierAccountGroup"),
        "found": True,
    }


# ---------------------------------------------------------------------------
# Alternative sources — info record + contract (BR-006).
# No EORD/source-list OData; resolve via info record + contract (validity dates
# live on the CONTRACT, not the info record — probe-confirmed 2026-10-21).
# ---------------------------------------------------------------------------
async def get_alt_sources_live(material: str, plant: str = DEFAULT_PLANT) -> list[dict]:
    sources: list[dict] = []

    try:
        info_rows = await _odata_get_async(
            config.s4_service("info_record"),
            "A_PurgInfoRecdOrgPlantData",
            {"$filter": f"Material eq '{material}' and Plant eq '{plant}'",
             "$select": "PurchasingInfoRecord,Supplier,Material,Plant,"
                        "MaterialPlannedDeliveryDurn,IsMarkedForDeletion"},
        )
        for r in info_rows:
            if r.get("IsMarkedForDeletion") in (True, "X"):
                continue
            sources.append({
                "source_type": "info_record",
                "vendor": r.get("Supplier"),
                "material": material,
                "planned_delivery_days": int(r.get("MaterialPlannedDeliveryDurn") or 0),
                "record_id": r.get("PurchasingInfoRecord"),
            })
    except httpx.HTTPStatusError as e:
        logger.warning("Info record fetch failed for %s: %s", material, e)

    try:
        contract_rows = await _odata_get_async(
            config.s4_service("purchase_contract"),
            "A_PurchaseContractItem",
            {"$filter": f"Material eq '{material}'",
             "$select": ("PurchaseContract,PurchaseContractItem,Material,Plant,"
                         "TargetQuantity,to_PurchaseContract/Supplier,"
                         "to_PurchaseContract/ValidityStartDate,"
                         "to_PurchaseContract/ValidityEndDate"),
             "$expand": "to_PurchaseContract"},
        )
        for r in contract_rows:
            hdr = r.get("to_PurchaseContract") or {}
            sources.append({
                "source_type": "contract",
                "vendor": hdr.get("Supplier"),
                "material": material,
                "contract_no": r.get("PurchaseContract"),
                "valid_from": _parse_odata_date(hdr.get("ValidityStartDate")),
                "valid_to": _parse_odata_date(hdr.get("ValidityEndDate")),
                "target_qty": float(r.get("TargetQuantity") or 0),
                "planned_delivery_days": None,
            })
    except httpx.HTTPStatusError as e:
        logger.warning("Contract fetch failed for %s: %s", material, e)

    return sources


# ---------------------------------------------------------------------------
# Canary — reachability probe for /whoami (ENABLE_WHOAMI=1).
# ---------------------------------------------------------------------------
def s4_canary_read(plant: str = DEFAULT_PLANT) -> dict:
    try:
        rows = _odata_get(
            config.s4_service("material_stock"), "A_MatlStkInAcctMod",
            {"$filter": f"Plant eq '{plant}'", "$top": "1", "$select": "Material,Plant"},
        )
        return {"reachable": True, "profile": config.s4_service_profile(),
                "plant": plant, "rows_returned": len(rows)}
    except Exception as exc:
        return {"reachable": False, "profile": config.s4_service_profile(), "error": str(exc)}
