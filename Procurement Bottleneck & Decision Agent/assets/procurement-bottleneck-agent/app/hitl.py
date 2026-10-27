"""Human-in-the-Loop governance (L0-6.6 / L0-6.7).

Encodes:
* the **action-classification table** (autonomous / advisory / blocked-pending-approval);
* the **approval gate** — the two side-effecting tools run only after an explicit
  approval keyword, and alternative-vendor confirmation must name the LIFNR;
* the **nine design checkpoints**, each with its trigger condition, surfaced to the
  Purchasing HoD before any write-ish action proceeds;
* pending-approval **state**, keyed by A2A ``context_id``, so a multi-turn
  conversation can halt at "Awaiting Approval" and resume on approval.

Advisory-only: approval authorizes the agent to log a decision record and raise an
SPA notification/approval task — never to write SAP business objects.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from . import config

# --- Action classification --------------------------------------------------
# tool_name -> one of: "autonomous" (read, runs freely),
#                      "advisory" (produces a recommendation, no side effect),
#                      "blocked" (side_effect:true — requires approval keyword).
ACTION_CLASSIFICATION: dict[str, str] = {
    # read / grounding tools — autonomous
    "get_open_pr_po_chain": "autonomous",
    "get_approval_workflow_status": "autonomous",
    "detect_supplier_silence": "autonomous",
    "get_source_and_contract_dependencies": "autonomous",
    "get_procurement_contract_terms": "autonomous",
    "link_po_to_project_wbs": "autonomous",
    "recall_supplier_memory": "autonomous",
    "get_vendor_delivery_performance": "autonomous",
    "rag_retrieve_contract_and_history": "autonomous",
    # reasoning skills — advisory (no side effect)
    "run_consequence_simulation": "advisory",
    "recommend_next_action": "advisory",
    # side-effecting tools — blocked pending human approval
    "write_decision_record": "blocked",
    "trigger_escalation_notification": "blocked",
}

BLOCKED_TOOLS = tuple(name for name, cls in ACTION_CLASSIFICATION.items() if cls == "blocked")


def is_approval(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(t == k or t.startswith(k) for k in config.APPROVAL_KEYWORDS)


def is_rejection(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(t == k or t.startswith(k) for k in config.REJECTION_KEYWORDS)


def extract_lifnr(text: str) -> str | None:
    """Alternative-vendor confirmation must name the LIFNR explicitly. Returns the
    full supplier token (e.g. 'LIFNR-0010099'), or a bare vendor number if given."""
    import re
    m = re.search(r"\b(LIFNR-\d{4,10}|VENDOR-[A-Z0-9]+)\b", text or "", re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{4,10})\b", text or "")
    return m.group(1) if m else None


# --- The nine checkpoints ---------------------------------------------------
@dataclass
class Checkpoint:
    id: str
    description: str
    required: bool
    display: dict[str, Any] = field(default_factory=dict)


def evaluate_checkpoints(context: dict[str, Any]) -> list[Checkpoint]:
    """Return the HITL checkpoints triggered by the current analysis context.

    ``context`` keys (all optional): action, penalty_exposure_eur, days_since_due,
    has_pinfo_record, has_agreement, contract_source ('ariba'|'erp'|None),
    alt_vendor_confirmed, exposure_eur, is_critical_path.
    """
    cps: list[Checkpoint] = []
    action = context.get("action")

    # 1. Scorecard review & action selection (always, once a recommendation exists)
    cps.append(Checkpoint(
        "CP1", "Review the recommended action and confirm how you would like to proceed.",
        required=True,
        display={"exposure_eur": context.get("exposure_eur"),
                 "critical_path": context.get("is_critical_path")},
    ))

    # 2. Alternative-vendor confirmation (source switch, vendor not yet confirmed)
    if action == "source_switch" and not context.get("alt_vendor_confirmed"):
        cps.append(Checkpoint(
            "CP2", "Confirm the specific alternative vendor (name the LIFNR) before any "
                   "source-of-supply reassignment is recommended for execution.",
            required=True,
            display={"alt_vendor": context.get("alt_vendor_lifnr"),
                     "lead_time": context.get("alt_lead_time"),
                     "contract_coverage": context.get("alt_contract_coverage"),
                     "purchasing_block": context.get("alt_purchasing_block")},
        ))

    # 3. Obsolete-PO closure (no GRN/confirmation, due > 90 days ago)
    if (context.get("days_since_due") or 0) > config.OBSOLETE_PO_AGE_DAYS and context.get("no_grn"):
        cps.append(Checkpoint(
            "CP3", "Confirm closure/cancellation of this obsolete PO item before it is logged resolved.",
            required=True,
            display={"original_value": context.get("po_net_value_eur"),
                     "wbs": context.get("wbs_element"),
                     "obsolescence_reason": "no GRN / no confirmation past due date"},
        ))

    # 4. Escalation payload approval (notifying PMs)
    if action in ("escalate", "source_switch"):
        cps.append(Checkpoint(
            "CP4", "Approve the escalation payload (recipients, scorecard summary, recommended action) "
                   "before dispatch to project managers.",
            required=True,
            display={"recipients": context.get("pm_recipients")},
        ))

    # 5. High penalty-exposure confirmation (> €10k)
    if (context.get("penalty_exposure_eur") or 0) >= config.PENALTY_EXPOSURE_HITL_EUR:
        cps.append(Checkpoint(
            "CP5", "Confirm the simulation given penalty exposure exceeds the configured threshold.",
            required=True,
            display={"penalty_exposure_eur": context.get("penalty_exposure_eur"),
                     "contract_ref": context.get("contract_ref")},
        ))

    # 6. Supplier-without-PInfoRecord guard
    if context.get("has_pinfo_record") is False:
        cps.append(Checkpoint(
            "CP6", "Confirm a recommendation involving a supplier with no Purchasing Info Record "
                   "(data-quality gap: missing PLIFZ/MINBM).",
            required=True, display={"supplier": context.get("supplier_lifnr")},
        ))

    # 7. PO-without-agreement/PInfoRecord
    if context.get("has_agreement") is False and context.get("has_pinfo_record") is False:
        cps.append(Checkpoint(
            "CP7", "Confirm simulation/escalation for a PO item lacking both agreement and Info Record; "
                   "some dimensions are estimated.", required=True,
        ))

    # 8. ERP fallback contract (EKKO.BSTYP=K instead of Ariba)
    if context.get("contract_source") == "erp":
        cps.append(Checkpoint(
            "CP8", "Confirm penalty exposure computed from an ERP-native outline agreement (not Ariba).",
            required=True, display={"contract_number": context.get("contract_ref")},
        ))

    # 9. Uncontracted supplier
    if context.get("contract_source") in (None, "none") and action in ("escalate", "source_switch"):
        cps.append(Checkpoint(
            "CP9", "Confirm escalation/source-switch for a supplier with no contract (uncontracted spend, "
                   "no penalty protection).", required=True,
        ))

    return cps


# --- Pending-approval state -------------------------------------------------
@dataclass
class PendingApproval:
    context_id: str
    action: str
    payload: dict[str, Any]
    checkpoints: list[Checkpoint]
    created_ts: float = field(default_factory=time.time)

    def expired(self, ttl_seconds: int = config.SESSION_TTL_HOURS * 3600) -> bool:
        return (time.time() - self.created_ts) > ttl_seconds


class ApprovalStore:
    """Thread-safe pending-approval registry keyed by context_id (in-memory MVP)."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingApproval] = {}
        self._lock = threading.Lock()

    def put(self, pending: PendingApproval) -> None:
        with self._lock:
            self._pending[pending.context_id] = pending

    def get(self, context_id: str) -> PendingApproval | None:
        with self._lock:
            p = self._pending.get(context_id)
            if p and p.expired():
                self._pending.pop(context_id, None)
                return None
            return p

    def clear(self, context_id: str) -> None:
        with self._lock:
            self._pending.pop(context_id, None)


_APPROVALS: ApprovalStore | None = None


def get_approval_store() -> ApprovalStore:
    global _APPROVALS
    if _APPROVALS is None:
        _APPROVALS = ApprovalStore()
    return _APPROVALS
