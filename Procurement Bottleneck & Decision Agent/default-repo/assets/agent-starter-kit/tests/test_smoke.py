"""Sprint 1 smoke tests — verifies the scaffold starts and responds in mock mode.

Run with: IBD_TESTING=1 pytest tests/test_smoke.py -v
"""
import os
import pytest

os.environ.setdefault("IBD_TESTING", "1")


def test_agent_card_is_importable():
    """agent.py imports without errors and the 3 decorators return sensible values."""
    import app.agent as ag  # noqa: F401
    name = ag.get_model_name()
    assert isinstance(name, str) and len(name) > 0

    temp = ag.get_temperature()
    assert isinstance(temp, float) and 0.0 <= temp <= 1.0

    prompt = ag.get_system_prompt()
    assert "MANDATORY RULES" in prompt
    assert "top=100" in prompt


def test_mock_tools_load():
    """mcp_providers/agw.py returns at least one mock tool when IBD_TESTING=1."""
    import asyncio
    from app.mcp_providers.agw import get_mcp_tools
    tools = asyncio.run(get_mcp_tools())
    assert len(tools) >= 1
    assert all(hasattr(t, "name") for t in tools)


def test_config_mock_mode():
    """config.is_mock_mode() returns True when IBD_TESTING=1."""
    from app.config import is_mock_mode
    assert is_mock_mode() is True
