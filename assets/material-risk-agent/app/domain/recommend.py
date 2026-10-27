"""Recommendation engine (FSD §8.5 + BR-001/002/006) and escalation routing.

Maps a material assessment + simulation scorecard to a ranked, role-aware set
of actions. Alternative-supplier options are gated to the Purchase HoD role.
"""
from __future__ import annotations

from . import scoring

# Roles (FSD §5) and their escalation level.
ROLE_PURCHASE_EXECUTIVE = "purchase_executive"
ROLE_PURCHASE_MANAGER = "purchase_manager"
ROLE_PURCHASE_HOD = "purchase_hod"
ROLE_PROJECT_MANAGER = "project_manager"

# Dashboard priority markers (match the required report format).
PRIORITY_URGENT = "🔴 URGENT"
PRIORITY_HIGH = "🟡 HIGH"
PRIORITY_RECOMMENDED = "🟢 RECOMMENDED"

# Escalation SLAs (BR-007/008), in hours.
SLA_L1_TO_L2_HOURS = 24
SLA_L2_TO_L3_HOURS = 48


def _priority_for(band: str) -> str:
    if band == scoring.CRITICAL:
        return PRIORITY_URGENT
    if band == scoring.HIGH:
        return PRIORITY_HIGH
    return PRIORITY_RECOMMENDED


def recommend(assessment: dict, scorecard: dict, caller_role: str = ROLE_PURCHASE_EXECUTIVE) -> dict:
    """Produce a ranked recommendation for one at-risk material.

    BR-001 Critical -> flag Purchase Manager immediately (no SLA wait).
    BR-002 High     -> recommend Expedite with a pre-drafted email.
    BR-003 Medium   -> Monitor. BR-004 Low -> informational.
    BR-006 Alternative-supplier action is included only for the Purchase HoD.
    """
    band = assessment["risk_band"]
    actions: list[dict] = []

    if band == scoring.CRITICAL:
        actions.append({"action": "flag_purchase_manager", "priority": PRIORITY_URGENT,
                        "rationale": "Critical path (float <= 0) with a confirmed delivery gap — immediate managerial review, no SLA wait (BR-001)."})
        actions.append({"action": "expedite", "priority": PRIORITY_URGENT,
                        "rationale": "Request earlier commitment from the supplier; draft expedite email prepared."})
    elif band == scoring.HIGH:
        actions.append({"action": "expedite", "priority": PRIORITY_HIGH,
                        "rationale": "Low float with a delivery gap — expedite recommended; draft email prepared (BR-002)."})
    elif band == scoring.MEDIUM:
        actions.append({"action": "monitor", "priority": PRIORITY_RECOMMENDED,
                        "rationale": "Moderate float — monitor on the dashboard; no automatic action (BR-003)."})
    elif band == scoring.LOW:
        actions.append({"action": "informational", "priority": PRIORITY_RECOMMENDED,
                        "rationale": "Ample float — informational alert only (BR-004)."})

    if assessment.get("chronic_late"):
        actions.append({"action": "flag_chronic_supplier", "priority": PRIORITY_HIGH,
                        "rationale": "Supplier is chronically late (>=3 of last 4 deliveries) — severity elevated (BR-005)."})

    # BR-006: alternative sourcing is HoD-only.
    alt_visible = caller_role == ROLE_PURCHASE_HOD
    alt_options = None
    if alt_visible and band in (scoring.CRITICAL, scoring.HIGH):
        actions.append({"action": "source_alternatively", "priority": PRIORITY_HIGH,
                        "rationale": "Approved alternative vendor available — HoD may authorise a switch (BR-006)."})

    best = scorecard.get("recommended_option") if scorecard else None

    return {
        "material": assessment["material"],
        "risk_band": band,
        "priority": _priority_for(band),
        "actions": actions,
        "simulation_recommended_option": best,
        "alternative_supplier_visible": alt_visible,
        "escalation_target": _escalation_target(band),
    }


def _escalation_target(band: str) -> str:
    if band == scoring.CRITICAL:
        return ROLE_PURCHASE_MANAGER  # immediate (BR-001)
    if band in (scoring.HIGH, scoring.MEDIUM):
        return ROLE_PURCHASE_EXECUTIVE
    return ROLE_PURCHASE_EXECUTIVE


def draft_expedite_email(assessment: dict, prediction: dict | None = None) -> dict:
    """FR-RE-002: pre-populated supplier expedite email."""
    pred = ""
    if prediction and prediction.get("predicted_delivery_low"):
        pred = (f"\n\nOur records indicate recent deliveries on this material have run "
                f"{prediction['mean_overrun_days']} days late on average. A revised commitment "
                f"between {prediction['predicted_delivery_low']} and {prediction['predicted_delivery_high']} "
                f"would materially impact our schedule.")
    subject = f"Expedite request — PO {assessment.get('po_number')} / {assessment['material_desc']}"
    body = (
        f"Dear {assessment.get('vendor_name', 'Supplier')},\n\n"
        f"We require material {assessment['material']} ({assessment['material_desc']}), "
        f"quantity {assessment['required_qty']} {assessment['uom']}, on site by "
        f"{assessment['required_date']} for a scheduled construction activity "
        f"({assessment['activity_name']}).\n\n"
        f"The current confirmed delivery date on PO {assessment.get('po_number')} is "
        f"{assessment.get('confirmed_delivery_date')}, which is {assessment['delivery_gap_days']} days "
        f"after our required date. Please confirm the earliest possible revised delivery date.{pred}\n\n"
        f"Kind regards,\nProcurement"
    )
    return {"to_vendor": assessment.get("vendor"), "subject": subject, "body": body, "editable": True}
