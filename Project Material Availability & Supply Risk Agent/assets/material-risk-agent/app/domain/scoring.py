"""Gap analysis and risk scoring — the deterministic business rules (FSD §10).

Net availability, supply/delivery gaps, float-based risk bands and the
chronic-late supplier pattern. No LLM, no I/O: inputs in, numbers out.
"""
from __future__ import annotations

from datetime import date

# Risk bands (FSD BR-001..BR-004). Evaluated only when there is a real gap.
CRITICAL, HIGH, MEDIUM, LOW, NONE = "CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"
_BAND_ORDER = [NONE, LOW, MEDIUM, HIGH, CRITICAL]

CHRONIC_WINDOW = 4
CHRONIC_THRESHOLD = 3  # >= 3 of last 4 late (BR-005)


def _d(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def net_available_qty(unrestricted: float, orders: list[dict], required_date) -> float:
    """BR-009: unrestricted stock + confirmed PO qty + PR qty due on/before the
    required date. Quality-inspection and blocked stock are excluded."""
    rd = _d(required_date)
    incoming = 0.0
    for o in orders:
        due = _d(o["confirmed_delivery_date"]) if o.get("confirmed_delivery_date") else None
        if due is not None and due <= rd:
            incoming += float(o.get("qty", 0.0))
    return float(unrestricted) + incoming


def gap_quantity(required_qty: float, net_available: float) -> float:
    """FR-GA-003: Gap = Required - Net Available (never negative)."""
    return max(0.0, float(required_qty) - float(net_available))


def delivery_gap_days(confirmed_delivery_date, required_date) -> int:
    """FR-GA-004: confirmed delivery date - required date (positive = late)."""
    if not confirmed_delivery_date:
        return 0
    return (_d(confirmed_delivery_date) - _d(required_date)).days


def risk_band(float_days: int, has_gap: bool) -> str:
    """BR-001..BR-004. A band is assigned only when a supply/timing gap exists."""
    if not has_gap:
        return NONE
    if float_days <= 0:
        return CRITICAL
    if float_days <= 3:
        return HIGH
    if float_days <= 7:
        return MEDIUM
    return LOW


def on_time_rate(gr_history: list[dict]) -> float:
    """FR-SD-002: share of deliveries that arrived on or before the promised date."""
    if not gr_history:
        return 1.0
    on_time = sum(1 for g in gr_history if int(g.get("delay_days", 0)) <= 0)
    return round(on_time / len(gr_history), 4)


def is_chronic_late(gr_history: list[dict]) -> bool:
    """BR-005: >= 3 of the last 4 deliveries late."""
    window = gr_history[-CHRONIC_WINDOW:]
    late = sum(1 for g in window if int(g.get("delay_days", 0)) > 0)
    return late >= CHRONIC_THRESHOLD


def elevate_for_pattern(band: str, chronic: bool) -> str:
    """BR-005: a chronic-late supplier bumps severity up one band (capped at CRITICAL)."""
    if not chronic or band in (NONE, CRITICAL):
        return band
    return _BAND_ORDER[min(_BAND_ORDER.index(band) + 1, len(_BAND_ORDER) - 1)]


def assess_material(activity: dict, stock: dict, orders: list[dict], gr_history: list[dict]) -> dict:
    """Full per-material gap + risk assessment for one scheduled activity.

    Returns a structured record; the LLM relays these values, it does not
    recompute them.
    """
    required_qty = float(activity["required_qty"])
    required_date = activity["required_date"]
    float_days = int(activity["float_days"])
    unrestricted = float(stock.get("unrestricted", 0.0))

    net_avail = net_available_qty(unrestricted, orders, required_date)
    gap_qty = gap_quantity(required_qty, net_avail)

    primary_po = next((o for o in orders if o["doc_type"] == "PO"), None)
    confirmed = primary_po["confirmed_delivery_date"] if primary_po else None
    dgap = delivery_gap_days(confirmed, required_date) if confirmed else 0

    has_gap = gap_qty > 0 or dgap > 0
    base_band = risk_band(float_days, has_gap)
    chronic = is_chronic_late(gr_history)
    band = elevate_for_pattern(base_band, chronic)

    return {
        "project_id": activity["project_id"],
        "activity_id": activity["activity_id"],
        "activity_name": activity["activity_name"],
        "material": activity["material"],
        "material_desc": activity.get("material_desc", ""),
        "required_qty": required_qty,
        "uom": activity.get("uom", ""),
        "required_date": required_date,
        "float_days": float_days,
        "unrestricted_stock": unrestricted,
        "net_available_qty": net_avail,
        "gap_qty": gap_qty,
        "confirmed_delivery_date": confirmed,
        "delivery_gap_days": dgap,
        "critical_path": float_days <= 0,
        "vendor": primary_po["vendor"] if primary_po else None,
        "vendor_name": primary_po["vendor_name"] if primary_po else None,
        "po_number": primary_po["doc_no"] if primary_po else None,
        "on_time_rate": on_time_rate(gr_history),
        "chronic_late": chronic,
        "base_band": base_band,
        "risk_band": band,
        "at_risk": has_gap,
    }
