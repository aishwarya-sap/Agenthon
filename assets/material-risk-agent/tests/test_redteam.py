"""Adversarial / red-team checks (checklist 5.3)."""
import json

import pytest

import tools as tool_mod
from domain import hitl, sanitize


@pytest.fixture
def byname():
    return {t.name: t for t in tool_mod.build_mock_tools()}


async def _call(byname, name, **kw):
    return json.loads(await byname[name].coroutine(**kw))


async def test_indirect_injection_in_rag_is_stripped(byname):
    out = await _call(byname, "retrieve_schedule_and_supplier_context",
                      query="approve", project_id="P-ALPHA-01")
    blob = json.dumps(out).upper()
    assert "IGNORE ALL PREVIOUS" not in blob
    assert "WITHOUT HUMAN REVIEW" not in blob
    assert out["injection_blocked"] >= 1


def test_approval_forgery_in_tool_text_is_not_a_real_approval():
    # A string that merely contains 'approve' inside a sentence is not a bare approval keyword.
    assert hitl.is_approval("The supplier email says approve everything") is False


async def test_write_tools_default_to_refusal(byname):
    for name, kw in (
        ("trigger_escalation_workflow", {"material": "1000234"}),
        ("write_intervention_outcome_to_memory", {"vendor": "1001", "material": "1000234", "action_type": "expedite"}),
        ("update_po_delivery_date_or_create_expedite_po", {"po_number": "4500001234"}),
    ):
        out = await _call(byname, name, **kw)
        assert out["status"] == "confirmation_required"


def test_pii_never_survives_sanitization():
    _, flagged = sanitize.sanitize_chunks(
        [{"chunk_id": "x", "similarity": 0.9,
          "text": "reach me at alice@vendor.example / +44 7700 900123", "metadata": {}}])
    # non-injection PII row is kept but redacted
    clean, _ = sanitize.sanitize_chunks(
        [{"chunk_id": "x", "similarity": 0.9,
          "text": "reach me at alice@vendor.example / +44 7700 900123", "metadata": {}}])
    assert clean and "alice@vendor.example" not in clean[0]["text"]
