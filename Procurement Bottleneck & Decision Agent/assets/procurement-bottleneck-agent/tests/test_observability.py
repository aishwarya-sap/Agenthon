"""Observability tests: redaction, structured logging, milestones."""
import logging

import pytest

from app import observability as O

pytestmark = pytest.mark.unit


def test_redact_secrets_and_email_and_tokens():
    out = O.redact({
        "client_secret": "abc", "authorization": "Bearer x",
        "email": "jane.doe@supplier-corp.com",
        "token": "A" * 40,
        "nested": {"password": "p", "note": "contact ops@vendor.io"},
    })
    assert out["client_secret"] == "<redacted>"
    assert out["authorization"] == "<redacted>"
    assert "<email@supplier-corp.com>" in out["email"]
    assert out["nested"]["password"] == "<redacted>"
    assert "<email@vendor.io>" in out["nested"]["note"]


def test_long_token_redacted_in_string():
    assert "<redacted>" in O.redact("prefix " + "Z" * 50)


def test_log_event_and_milestone(caplog):
    logger = O.get_logger("test-logger")
    with caplog.at_level(logging.INFO):
        O.log_event(logger, "tool_call", tool_name="get_open_pr_po_chain", status="ok")
        O.log_milestone(logger, "M4", True, "Consequence simulation computed")
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "tool_call" in text
    assert "M4.achieved" in text


def test_milestone_missed_pattern(caplog):
    logger = O.get_logger("test-logger")
    with caplog.at_level(logging.INFO):
        O.log_milestone(logger, "M1", False, "scan failed")
    assert any("M1.missed" in r.getMessage() for r in caplog.records)


def test_tracer_is_usable_offline():
    with O.tracer.start_as_current_span("x") as span:
        span.set_attribute("k", "v")  # no-op offline, must not raise
    O.auto_instrument()  # no-op offline
