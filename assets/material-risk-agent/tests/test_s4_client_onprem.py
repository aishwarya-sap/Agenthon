"""Tests for the on-prem S4 transport seam (BTP Destination Service + Principal Propagation).

All network calls are monkeypatched so these run fully offline under IBD_TESTING=1.
"""
import json
import os
import sys

import httpx
import pytest

# ---------------------------------------------------------------------------
# Path setup (mirrors conftest.py convention)
# ---------------------------------------------------------------------------
APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import s4_client
from s4_client import (
    _vcap_destination_creds,
    _dst_service_token,
    _resolve_destination,
    clear_destination_cache,
    _odata_get,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int, body: dict) -> httpx.Response:
    """Build an httpx.Response with a real request so raise_for_status() works."""
    req = httpx.Request("GET", "https://example.com/fake")
    return httpx.Response(status_code, json=body, request=req)


FAKE_CREDS = {
    "clientid": "dest-client-id",
    "clientsecret": "dest-client-secret",
    "url": "https://btp-xsuaa.example",
    "uri": "https://dest-service.example",
}

FAKE_VCAP = json.dumps({
    "destination": [{"credentials": FAKE_CREDS}]
})

FAKE_DEST_RESPONSE = {
    "destinationConfiguration": {
        "URL": "https://s4.client.example",
        "Authentication": "OAuth2SAMLBearerAssertion",
    },
    "authTokens": [
        {"type": "Bearer", "value": "s4-exchanged-token", "expires_in": "3600"}
    ],
}

FAKE_TOKEN_RESPONSE = {"access_token": "dst-bearer-token"}


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_destination_cache()
    yield
    clear_destination_cache()


# ---------------------------------------------------------------------------
# _vcap_destination_creds
# ---------------------------------------------------------------------------

def test_vcap_destination_creds_found(monkeypatch):
    monkeypatch.setenv("VCAP_SERVICES", FAKE_VCAP)
    creds = _vcap_destination_creds()
    assert creds["clientid"] == "dest-client-id"


def test_vcap_destination_creds_missing(monkeypatch):
    monkeypatch.setenv("VCAP_SERVICES", json.dumps({"redis": []}))
    with pytest.raises(RuntimeError, match="No Destination service binding"):
        _vcap_destination_creds()


def test_vcap_destination_creds_invalid_json(monkeypatch):
    monkeypatch.setenv("VCAP_SERVICES", "not-json")
    with pytest.raises(RuntimeError, match="VCAP_SERVICES is not valid JSON"):
        _vcap_destination_creds()


# ---------------------------------------------------------------------------
# _dst_service_token
# ---------------------------------------------------------------------------

def test_dst_service_token(monkeypatch):
    """OAuth2 client-credentials call returns access token."""
    def fake_post(url, data=None, timeout=None):
        assert "oauth/token" in url
        assert data["grant_type"] == "client_credentials"
        req = httpx.Request("POST", url)
        return httpx.Response(200, json=FAKE_TOKEN_RESPONSE, request=req)

    monkeypatch.setattr(httpx, "post", fake_post)
    token = _dst_service_token(FAKE_CREDS)
    assert token == "dst-bearer-token"


# ---------------------------------------------------------------------------
# _resolve_destination
# ---------------------------------------------------------------------------

def _patch_destination_service(monkeypatch, vcap=FAKE_VCAP, dest_body=None):
    """Monkeypatch VCAP + httpx.post + httpx.get for Destination service calls."""
    monkeypatch.setenv("VCAP_SERVICES", vcap)
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(("post", url, data))
        req = httpx.Request("POST", url)
        return httpx.Response(200, json=FAKE_TOKEN_RESPONSE, request=req)

    def fake_get(url, headers=None, timeout=None):
        calls.append(("get", url, headers or {}))
        req = httpx.Request("GET", url)
        return httpx.Response(200, json=dest_body or FAKE_DEST_RESPONSE, request=req)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_resolve_destination_returns_url_and_token(monkeypatch):
    calls = _patch_destination_service(monkeypatch)
    base_url, s4_token = _resolve_destination("S4_MATERIAL_RISK", user_token="user-jwt")
    assert base_url == "https://s4.client.example"
    assert s4_token == "s4-exchanged-token"
    # X-user-token must be forwarded for PP
    get_calls = [c for c in calls if c[0] == "get"]
    assert get_calls, "No GET call made to Destination service"
    assert get_calls[0][2].get("X-user-token") == "user-jwt"


def test_resolve_destination_no_user_token(monkeypatch):
    calls = _patch_destination_service(monkeypatch)
    _resolve_destination("S4_MATERIAL_RISK", user_token=None)
    get_calls = [c for c in calls if c[0] == "get"]
    assert "X-user-token" not in get_calls[0][2]


def test_resolve_destination_cached(monkeypatch):
    calls = _patch_destination_service(monkeypatch)
    _resolve_destination("S4_MATERIAL_RISK", user_token="u1")
    _resolve_destination("S4_MATERIAL_RISK", user_token="u1")  # should hit cache
    assert len([c for c in calls if c[0] == "get"]) == 1  # only 1 Destination API call


def test_resolve_destination_no_url_raises(monkeypatch):
    bad_body = {
        "destinationConfiguration": {"URL": ""},
        "authTokens": [{"value": "tok"}],
    }
    _patch_destination_service(monkeypatch, dest_body=bad_body)
    with pytest.raises(RuntimeError, match="has no URL configured"):
        _resolve_destination("S4_MATERIAL_RISK", user_token=None)


def test_resolve_destination_no_auth_tokens_raises(monkeypatch):
    bad_body = {
        "destinationConfiguration": {"URL": "https://s4.example"},
        "authTokens": [],
    }
    _patch_destination_service(monkeypatch, dest_body=bad_body)
    with pytest.raises(RuntimeError, match="no authTokens"):
        _resolve_destination("S4_MATERIAL_RISK", user_token=None)


def test_resolve_destination_auth_token_error_raises(monkeypatch):
    bad_body = {
        "destinationConfiguration": {"URL": "https://s4.example"},
        "authTokens": [{"error": "Token exchange failed: user not found"}],
    }
    _patch_destination_service(monkeypatch, dest_body=bad_body)
    with pytest.raises(RuntimeError, match="Token exchange failed"):
        _resolve_destination("S4_MATERIAL_RISK", user_token="bad-jwt")


# ---------------------------------------------------------------------------
# _odata_get — profile branching
# ---------------------------------------------------------------------------

def test_odata_get_onprem_routes_through_destination(monkeypatch):
    """On-prem profile: _odata_get resolves via BTP Destination and uses Bearer token."""
    monkeypatch.setattr("config.s4_service_profile", lambda: "onprem")

    # Stub _resolve_destination to avoid VCAP/httpx setup
    monkeypatch.setattr(
        s4_client, "_resolve_destination",
        lambda name, user_token: ("https://s4-onprem.example", "s4-bearer-xyz"),
    )
    # Stub get_user_token at the module level (avoid importing langchain_core)
    import unittest.mock as mock
    with mock.patch.dict("sys.modules", {"mcp_providers.agw": mock.MagicMock(get_user_token=lambda: "joule-jwt")}):
        # Patch httpx.get for the actual S4 OData call
        def fake_s4_get(url, headers=None, timeout=None):
            assert "s4-onprem.example" in url
            assert headers.get("Authorization") == "Bearer s4-bearer-xyz"
            assert "APIKey" not in headers
            req = httpx.Request("GET", url)
            return httpx.Response(200, json={"d": {"results": [{"Material": "RM-001"}]}}, request=req)

        monkeypatch.setattr(httpx, "get", fake_s4_get)

        # Reload _odata_get after mocking
        rows = s4_client._odata_get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    assert rows == [{"Material": "RM-001"}]


def test_odata_get_cloud_uses_apikey(monkeypatch):
    """Cloud profile: _odata_get calls sandbox directly with APIKey header."""
    monkeypatch.setattr("config.s4_service_profile", lambda: "cloud")
    monkeypatch.setattr(s4_client, "S4_API_KEY", "my-sandbox-key")

    def fake_get(url, headers=None, timeout=None):
        assert "sandbox.api.sap.com" in url
        assert headers.get("APIKey") == "my-sandbox-key"
        req = httpx.Request("GET", url)
        return httpx.Response(200, json={"d": {"results": []}}, request=req)

    monkeypatch.setattr(httpx, "get", fake_get)
    rows = _odata_get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    assert isinstance(rows, list)
