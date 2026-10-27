"""HITL governance tests: keywords, LIFNR extraction, checkpoint triggers, store."""
import pytest

from app import hitl

pytestmark = pytest.mark.unit


def test_approval_and_rejection_keywords():
    assert hitl.is_approval("approve")
    assert hitl.is_approval("yes proceed")
    assert hitl.is_approval("Confirm the switch")
    assert hitl.is_rejection("cancel")
    assert not hitl.is_approval("maybe later")


def test_extract_lifnr():
    assert hitl.extract_lifnr("approve LIFNR-0010099") == "LIFNR-0010099"
    assert hitl.extract_lifnr("approve vendor 10099123") == "10099123"
    assert hitl.extract_lifnr("approve") is None


def test_action_classification_table():
    assert hitl.ACTION_CLASSIFICATION["get_open_pr_po_chain"] == "autonomous"
    assert hitl.ACTION_CLASSIFICATION["recommend_next_action"] == "advisory"
    assert hitl.ACTION_CLASSIFICATION["write_decision_record"] == "blocked"
    assert set(hitl.BLOCKED_TOOLS) == {"write_decision_record", "trigger_escalation_notification"}


def test_checkpoints_source_switch_triggers_cp2_cp4_cp5():
    cps = hitl.evaluate_checkpoints({
        "action": "source_switch", "exposure_eur": 192400.0, "penalty_exposure_eur": 24000.0,
        "is_critical_path": True, "alt_vendor_confirmed": False, "has_pinfo_record": True,
        "has_agreement": True, "contract_source": "ariba",
    })
    ids = {c.id for c in cps}
    assert {"CP1", "CP2", "CP4", "CP5"} <= ids
    assert "CP3" not in ids  # not obsolete


def test_checkpoints_obsolete_and_uncontracted():
    cps = hitl.evaluate_checkpoints({
        "action": "escalate", "days_since_due": 120, "no_grn": True,
        "contract_source": "none", "has_pinfo_record": True,
    })
    ids = {c.id for c in cps}
    assert "CP3" in ids and "CP9" in ids


def test_checkpoints_erp_fallback_and_no_pinfo():
    cps = hitl.evaluate_checkpoints({
        "action": "escalate", "contract_source": "erp", "has_pinfo_record": False,
        "has_agreement": False,
    })
    ids = {c.id for c in cps}
    assert {"CP6", "CP7", "CP8"} <= ids


def test_approval_store_put_get_clear():
    store = hitl.get_approval_store()
    p = hitl.PendingApproval("ctx-1", "escalate", {}, [])
    store.put(p)
    assert store.get("ctx-1") is p
    store.clear("ctx-1")
    assert store.get("ctx-1") is None
