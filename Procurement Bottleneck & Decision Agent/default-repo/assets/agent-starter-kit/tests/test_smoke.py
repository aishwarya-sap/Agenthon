"""Smoke tests — run fully offline with IBD_TESTING=1 (set by conftest.py).

Tests cover:
  - agent card construction (a2a.types.AgentCard)
  - tools list and direct tool invocation
  - StarterKitAgent mock invocation (no LLM, no SAP)
  - ResponseFormat Pydantic schema
  - __main__._app_url fallback logic
"""
import os

import pytest

from app.agent import ResponseFormat, StarterKitAgent
from app.agent_card import get_agent_card
from app.tools import echo_tool, get_sap_data, get_tools


# ── Agent card ──────────────────────────────────────────────────────────────


def test_agent_card_has_required_fields():
    card = get_agent_card("http://localhost:8080")
    assert card.name
    assert card.url == "http://localhost:8080/"
    assert card.skills
    assert card.capabilities.streaming is True


def test_agent_card_skill_has_id():
    card = get_agent_card("http://localhost:8080")
    assert card.skills[0].id


# ── Tools ───────────────────────────────────────────────────────────────────


def test_get_tools_returns_nonempty_list():
    tools = get_tools()
    assert isinstance(tools, list)
    assert len(tools) >= 1


def test_echo_tool_returns_echo_and_status():
    result = echo_tool.invoke({"message": "hello"})
    assert result["echo"] == "hello"
    assert result["status"] == "ok"


def test_get_sap_data_mock_returns_dict():
    result = get_sap_data.invoke({"query": "test"})
    assert isinstance(result, dict)


# ── StarterKitAgent (mock mode) ─────────────────────────────────────────────


def test_agent_mock_invoke_returns_correct_keys():
    agent = StarterKitAgent()
    result = agent.invoke("What are my open POs?", "session-1")
    assert "is_task_complete" in result
    assert "require_user_input" in result
    assert "content" in result


def test_agent_mock_invoke_is_complete():
    agent = StarterKitAgent()
    result = agent.invoke("Hello", "session-2")
    assert result["is_task_complete"] is True
    assert result["require_user_input"] is False


def test_agent_mock_content_has_mock_prefix():
    agent = StarterKitAgent()
    result = agent.invoke("Any query", "session-3")
    assert result["content"].startswith("[MOCK]")


# ── ResponseFormat schema ───────────────────────────────────────────────────


def test_response_format_completed():
    rf = ResponseFormat(status="completed", message="Done.")
    assert rf.status == "completed"
    assert rf.message == "Done."


def test_response_format_input_required():
    rf = ResponseFormat(status="input_required", message="Which company code?")
    assert rf.status == "input_required"


def test_response_format_error():
    rf = ResponseFormat(status="error", message="Something went wrong.")
    assert rf.status == "error"


# ── __main__ URL resolution ─────────────────────────────────────────────────


def test_app_url_falls_back_to_localhost():
    os.environ.pop("VCAP_APPLICATION", None)
    os.environ.pop("AGENT_PUBLIC_URL", None)
    from app.__main__ import _app_url
    url = _app_url()
    assert url.startswith("http://localhost:")


def test_app_url_reads_agent_public_url():
    os.environ["AGENT_PUBLIC_URL"] = "https://my-agent.cfapps.us10.hana.ondemand.com"
    from app.__main__ import _app_url
    url = _app_url()
    assert url == "https://my-agent.cfapps.us10.hana.ondemand.com"
    del os.environ["AGENT_PUBLIC_URL"]
