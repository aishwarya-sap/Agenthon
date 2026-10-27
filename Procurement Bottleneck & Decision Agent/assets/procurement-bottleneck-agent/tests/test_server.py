"""A2A server-surface tests (Starlette TestClient, offline)."""
import uuid

import pytest

from app import config

pytestmark = pytest.mark.server


@pytest.fixture
def client():
    from starlette.testclient import TestClient
    from app.main import build_app
    return TestClient(build_app())


def _msg(text, context_id=None):
    msg = {"messageId": str(uuid.uuid4()), "role": "user", "parts": [{"kind": "text", "text": text}]}
    if context_id:
        msg["contextId"] = context_id
    return {"jsonrpc": "2.0", "method": "message/send", "params": {"message": msg}, "id": "1"}


def test_agent_card_resolves(client):
    r = client.get("/.well-known/agent.json")
    assert r.status_code == 200
    card = r.json()
    assert card["name"] == config.AGENT_NAME
    assert card["skills"][0]["id"] == "procurement-bottleneck-decision"
    assert card["capabilities"]["streaming"] is False


def test_message_send_returns_report(client):
    r = client.post("/", json=_msg("Run the analysis for project P-INFRA-07", "ctx-srv"))
    assert r.status_code == 200
    body = r.json()
    res = body["result"]
    # A2A 0.3.0 non-streaming Task: Joule reads status.message.parts[].text
    assert res["kind"] == "task"
    text = res["status"]["message"]["parts"][0]["text"]
    assert "Awaiting Your Approval" in text
    assert res["status"]["state"] == "input-required"
    # Same report is also carried as an artifact for A2A clients.
    assert res["artifacts"][0]["parts"][0]["text"] == text
    # Task carries id (taskId) + contextId so Joule can persist multi-turn state.
    assert res["id"]
    assert res["contextId"] == "ctx-srv"


def test_message_send_echoes_task_id_for_multi_turn(client):
    # Follow-up turn (e.g. HITL "approve") sends the taskId back; the agent must
    # echo the same id so Joule keeps the turns on one task.
    first = client.post("/", json=_msg("Run the analysis for project P-INFRA-07", "ctx-mt")).json()
    task_id = first["result"]["id"]
    follow = {"jsonrpc": "2.0", "method": "message/send", "id": "2",
              "params": {"message": {"messageId": "m2", "role": "user",
                                     "parts": [{"kind": "text", "text": "approve"}],
                                     "contextId": "ctx-mt", "taskId": task_id}}}
    r = client.post("/", json=follow)
    assert r.status_code == 200
    assert r.json()["result"]["id"] == task_id


def test_message_without_text_is_400(client):
    bad = {"jsonrpc": "2.0", "method": "message/send",
           "params": {"message": {"messageId": "x", "parts": []}}, "id": "9"}
    r = client.post("/", json=bad)
    assert r.status_code == 400


def test_parse_error_is_400(client):
    r = client.post("/", content=b"not json")
    assert r.status_code == 400


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["agent"] == "procurement-bottleneck-decision-agent"


def test_ui_served_with_agent_name(client):
    # UI is served at the clean root and at /ui; it carries the proper agent name
    # and none of the old demo/mock labelling.
    for path in ("/", "/ui"):
        r = client.get(path)
        assert r.status_code == 200
        assert "Procurement Bottleneck &amp; Decision Agent" in r.text
        assert "DEMO" not in r.text
