"""MCP tool provider.

Behaviour is controlled by the IBD_TESTING environment variable:

  Demo / test mode (IBD_TESTING=1):
      Returns the 15 in-process material-risk StructuredTools from ``tools.py``.
      These compute over the deterministic ``domain`` layer and the seeded mock
      data — no network, no SAP SDK, no AI Core.

  Live S/4 sandbox (IBD_LIVE_S4=1):
      Returns the 15 tools wired to the SAP Business Accelerator Hub sandbox via
      ``s4_client.py``. Useful for functional testing before BTP/Agent Gateway
      setup is complete. Set S4_API_KEY + S4_BASE_URL in .env.

  Production (IBD_TESTING not set, IBD_LIVE_S4 not set):
      Uses the Agent Gateway SDK to discover MCP tools (same tool names/shapes),
      with the per-request user token set by JWTContextMiddleware in main.py.
"""

import base64
import json
import logging
import os
from contextvars import ContextVar, Token

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

# Per-request user token, set by JWTContextMiddleware via set_user_token()
_user_token_context: ContextVar[str | None] = ContextVar("user_token", default=None)


def set_user_token(token: str | None) -> Token:
    """Set the user token for the current async context (called by JWTContextMiddleware)."""
    return _user_token_context.set(token)


def get_user_token() -> str | None:
    """Get the user token for the current async context."""
    return _user_token_context.get()


def _get_user_token() -> str | None:
    return _user_token_context.get()


def _ibd_testing_on() -> bool:
    return os.environ.get("IBD_TESTING", "").strip().lower() in ("1", "true", "yes", "on")


def _ibd_live_s4_on() -> bool:
    return os.environ.get("IBD_LIVE_S4", "").strip().lower() in ("1", "true", "yes", "on")


async def get_mcp_tools() -> list[BaseTool]:
    """Return LangChain-compatible MCP tools.

    Demo/test mode (IBD_TESTING truthy): the 15 in-process material-risk tools.
    Live S/4 sandbox (IBD_LIVE_S4 truthy): the 15 tools backed by real OData calls.
    Production: Agent Gateway discovery (lazy SAP-SDK import so offline boot works).
    """
    if _ibd_testing_on():
        from tools import build_mock_tools
        return build_mock_tools()

    if _ibd_live_s4_on():
        from tools import build_live_tools
        logger.info("IBD_LIVE_S4 mode — using live S/4 OData tools (sandbox)")
        return build_live_tools()

    # Production path — SAP runtime only.
    from sap_cloud_sdk.agentgateway import create_client
    from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain
    from util import call_mcp_tool_with_retry

    agw_client = create_client()
    mcp_tools = await agw_client.list_mcp_tools(user_token=_get_user_token)
    if not mcp_tools:
        logger.warning("Agent Gateway returned 0 tools — MCP servers may not be available")
        return []

    def _make_caller(t):
        async def call(_tool=None, *, user_token=None, **kwargs):
            return await call_mcp_tool_with_retry(agw_client, t, user_token=_get_user_token(), **kwargs)
        return call

    tools = [mcp_tool_to_langchain(t, _make_caller(t), _get_user_token) for t in mcp_tools]
    logger.info("Loaded %d MCP tool(s) from Agent Gateway", len(tools))
    return sorted(tools, key=lambda t: t.name)


def get_user_sub() -> str:
    """Extract the JWT subject claim from the current request's token.

    Decodes the JWT payload without verifying the signature (the platform has
    already verified it). Returns 'unknown' in demo/test mode when no token is
    present so the agent still runs offline.
    """
    token = _user_token_context.get()
    if not token:
        if _ibd_testing_on() or _ibd_live_s4_on():
            return "unknown"
        raise ValueError("No user token in context — cannot extract sub claim")

    try:
        payload_segment = token.split(".")[1]
        padding = 4 - len(payload_segment) % 4
        if padding != 4:
            payload_segment += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_segment))
        sub = payload.get("sub")
        if not sub:
            raise ValueError("JWT payload contains no 'sub' claim")
        return sub
    except (IndexError, ValueError):
        raise
    except Exception as e:
        raise ValueError(f"Failed to decode JWT payload: {e}") from e


def reset_user_token(token: Token) -> None:
    """Restore the user token context to its previous value."""
    _user_token_context.reset(token)
    logger.debug("User token context reset to previous value")
