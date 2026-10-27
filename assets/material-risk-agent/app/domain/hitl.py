"""Human-in-the-loop (HITL) approval gate (Design PDF · approval gate).

The three write tools are blocked until the user replies with an approval
keyword. The gate is enforced in the tool itself (a write tool refuses unless
confirmed=True) AND surfaced in the system prompt — defence in depth, so the
LLM cannot talk its way past it.
"""
from __future__ import annotations

APPROVAL_KEYWORDS = ("approve", "confirm", "yes proceed", "proceed", "yes")
REJECTION_KEYWORDS = ("reject", "cancel", "no", "stop", "decline")

# Tool action classification (checklist 6.5 Tool Access Governance).
AUTONOMOUS = "autonomous"   # read/compute — safe to run unprompted
ADVISORY = "advisory"       # reasoning/draft — safe, produces a recommendation
BLOCKED = "blocked"         # side-effecting — requires explicit approval

ACTION_CLASSIFICATION: dict[str, str] = {
    "get_project_material_requirements": AUTONOMOUS,
    "parse_excel_project_schedule": AUTONOMOUS,
    "get_material_stock_position": AUTONOMOUS,
    "get_open_purchase_orders_and_prs": AUTONOMOUS,
    "get_consolidation_material_master": AUTONOMOUS,
    "compute_material_availability_gaps": AUTONOMOUS,
    "get_supplier_delivery_history": AUTONOMOUS,
    "predict_delivery_outcome": AUTONOMOUS,
    "simulate_schedule_consequence": AUTONOMOUS,
    "retrieve_schedule_and_supplier_context": AUTONOMOUS,
    "recommend_procurement_action": ADVISORY,
    "draft_supplier_expedite_communication": ADVISORY,
    "trigger_escalation_workflow": BLOCKED,
    "write_intervention_outcome_to_memory": BLOCKED,
    "update_po_delivery_date_or_create_expedite_po": BLOCKED,
}

BLOCKED_TOOLS = tuple(name for name, cls in ACTION_CLASSIFICATION.items() if cls == BLOCKED)

CONFIRMATION_REQUIRED = "confirmation_required"


def is_approval(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(t == k or t.startswith(k + " ") or t.startswith(k) for k in APPROVAL_KEYWORDS)


def is_rejection(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(t == k or t.startswith(k + " ") for k in REJECTION_KEYWORDS)


def gate_write(confirmed: bool, action: str, payload: dict) -> dict | None:
    """Return a confirmation-required envelope if not confirmed, else None.

    Every write tool calls this first; it returns the structured refusal the LLM
    must relay as 'Awaiting Approval' instead of executing.
    """
    if confirmed:
        return None
    return {
        "status": CONFIRMATION_REQUIRED,
        "action": action,
        "payload": payload,
        "message": (
            f"Write action '{action}' requires human approval. Review the details and reply "
            f"'approve', 'confirm', or 'yes proceed' to execute, or 'cancel' to abort."
        ),
        "signal_status": "live",
    }
