"""HITL approval gate + action classification."""
from domain import hitl


def test_approval_and_rejection_keywords():
    for k in ("approve", "confirm", "yes proceed", "proceed", "yes"):
        assert hitl.is_approval(k)
    assert hitl.is_approval("approve LIFNR-1009")
    assert hitl.is_approval("Yes proceed please")
    for k in ("reject", "cancel", "no", "stop", "decline"):
        assert hitl.is_rejection(k)
    assert not hitl.is_approval("what are the risks?")
    assert not hitl.is_rejection("approve")


def test_write_tools_are_blocked():
    assert set(hitl.BLOCKED_TOOLS) == {
        "trigger_escalation_workflow",
        "write_intervention_outcome_to_memory",
        "update_po_delivery_date_or_create_expedite_po",
    }
    for name, cls in hitl.ACTION_CLASSIFICATION.items():
        assert cls in (hitl.AUTONOMOUS, hitl.ADVISORY, hitl.BLOCKED)


def test_gate_write_refuses_without_confirmation():
    gated = hitl.gate_write(False, "trigger_escalation_workflow", {"material": "1000234"})
    assert gated is not None
    assert gated["status"] == hitl.CONFIRMATION_REQUIRED
    assert "approve" in gated["message"].lower()


def test_gate_write_passes_when_confirmed():
    assert hitl.gate_write(True, "trigger_escalation_workflow", {"material": "1000234"}) is None
