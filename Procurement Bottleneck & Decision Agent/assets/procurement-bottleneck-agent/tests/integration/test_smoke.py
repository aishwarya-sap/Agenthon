"""Post-deploy smoke tests — run against the live CF app, not offline.

Usage:
    cp tests/integration/example.env tests/integration/.env
    # fill in AGENT_URL (and optionally AGENT_BEARER_TOKEN)
    INTEGRATION=1 pytest tests/integration/ -v

These tests are intentionally excluded from the main offline suite (pytest.ini
addopts does not include this folder). They exist to verify the deployed app
on any landscape — our environment or client — without re-running the full unit suite.
"""
import os
import uuid

import pytest

BASE_URL = os.environ.get("AGENT_URL", "").rstrip("/")
TOKEN = os.environ.get("AGENT_BEARER_TOKEN", "")


@pytest.fixture(scope="session")
def session():
    if not os.environ.get("INTEGRATION"):
        pytest.skip("set INTEGRATION=1 to run live smoke tests")
    if not BASE_URL:
        pytest.skip("AGENT_URL not set in tests/integration/.env")
    import httpx
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return httpx.Client(base_url=BASE_URL, headers=headers, timeout=30)


def test_agent_card(session):
    r = session.get("/.well-known/agent.json")
    assert r.status_code == 200
    card = r.json()
    assert card["name"] == "procurement-bottleneck-decision-agent"
    assert card["skills"][0]["id"] == "procurement-bottleneck-decision"


def test_health(session):
    r = session.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"


def test_ui_loads(session):
    r = session.get("/")
    assert r.status_code == 200
    assert "Procurement Bottleneck" in r.text


def test_message_send(session):
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": "Run analysis for project P-INFRA-07"}],
            }
        },
        "id": "smoke-1",
    }
    r = session.post("/", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "result" in body or "error" in body  # either is a valid A2A response
