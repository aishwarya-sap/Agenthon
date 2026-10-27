"""Structure & governance checks (analogous to the bootstrap's prebuilt tests)."""
import json
import os

import pytest

ASSET_ROOT = os.path.dirname(os.path.dirname(__file__))

pytestmark = pytest.mark.unit


def test_required_files_present():
    for rel in ["app/agent.py", "app/agent_executor.py", "app/main.py", "app/mcp_tools.py",
                "app/tools.py", "app/skills.py", "app/simulation.py", "app/memory.py",
                "app/hitl.py", "app/project_data.py", "app/config.py", "app/observability.py",
                "app/resilience.py", "app/agent_card.py", "mcp-mock.json", "asset.yaml",
                "manifest.yml", "xs-security.json", ".env.example", "demo/index.html"]:
        assert os.path.exists(os.path.join(ASSET_ROOT, rel)), f"missing {rel}"


def test_mcp_mock_is_valid_json_and_deterministic():
    with open(os.path.join(ASSET_ROOT, "mcp-mock.json")) as fh:
        data = json.load(fh)
    assert data["metadata"]["mock_mode"] is True
    tools = data["servers"]["s4-sourcing-procurement"]["tools"]
    assert len(tools) == 8
    for spec in tools.values():
        assert "mock_response" in spec and "input_schema" in spec


def test_exactly_three_decorators_present():
    src = open(os.path.join(ASSET_ROOT, "app/agent.py")).read()
    assert "sap_cloud_sdk.agent_decorators" in src
    assert src.count("\n@agent_model") == 1
    assert src.count("\n@agent_config") == 1
    assert src.count("\n@prompt_section") == 1


def test_system_prompt_has_mandatory_rules_and_disclaimer():
    from app.agent import SYSTEM_PROMPT
    for needle in ["Never fabricate", "top=100", "advisory", "estimates based on available SAP data"]:
        assert needle in SYSTEM_PROMPT


def test_no_sap_write_verbs_in_tools():
    """Advisory-only: no POST/PATCH/DELETE/BAPI_PO_CREATE in the tool layer."""
    src = open(os.path.join(ASSET_ROOT, "app/tools.py")).read()
    for forbidden in ["BAPI_PO_CREATE", ".post(", ".patch(", ".delete("]:
        assert forbidden not in src
