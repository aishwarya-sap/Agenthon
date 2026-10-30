"""Tests for the on-prem S4 transport seam — BTP Destination Service + Cloud Connector.

ACTIVE path: BasicAuthentication (technical user) over ProxyType OnPremise. The
Destination Service returns a ready Authorization header; the request is routed via
the Connectivity Proxy. PrincipalPropagation (X-user-token) is kept as a forward-looking
placeholder. All network calls are monkeypatched so these run fully offline.
"""
import json
import os
import sys

import httpx
import pytest

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


FAKE_CREDS = {
    "clientid": "dest-client-id",
    "clientsecret": "dest-client-secret",
    "url": "https://btp-xsuaa.example",
    "uri": "https://dest-service.example",
}

FAKE_VCAP = json.dumps({"destination": [{"credentials": FAKE_CREDS}]})

# BasicAuthentication destination (the client's S4HANA_HTTP): OnPremise proxy,
# sap-client=150, ready Authorization: Basic header in authTokens[0].http_header.
FAKE_DEST_RESPONSE = {
    "destinationConfiguration": {
        "URL": "https://s4.client.example",
        "Authentication": "BasicAuthentication",
        "ProxyType": "OnPremise",
        "sap-client": "150",
    },
    "authTokens": [
        {"type": "BasicAuthentication", "value": "dXNlcjpwdw==",
         "http_header": {"key": "Authorization", "value": "Basic dXNlcjpwdw=="}}
    ],
}

FAKE_TOKEN_RESPONSE = {"access_token": "dst-bearer-token"}


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_destination_cache()
    yield
    clear_destination_cache()


# --- _vcap_destination_creds ------------------------------------------------

def test_vcap_destination_creds_found(monkeypatch):
    monkeypatch.setenv("VCAP_SERVICES", FAKE_VCAP)
    assert _vcap_destination_creds()["clientid"] == "dest-client-id"


def test_vcap_destination_creds_missing(monkeypatch):
    monkeypatch.setenv("VCAP_SERVICES", json.dumps({"redis": []}))
    with pytest.raises(RuntimeError, match="No Destination service binding"):
        _vcap_destination_creds()


def test_vcap_destination_creds_invalid_json(monkeypatch):
    monkeypatch.setenv("VCAP_SERVICES", "not-json")
    with pytest.raises(RuntimeError, match="VCAP_SERVICES is not valid JSON"):
        _vcap_destination_creds()


# --- _dst_service_token -----------------------------------------------------

def test_dst_service_token(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        assert "oauth/token" in url
        assert data["grant_type"] == "client_credentials"
        return httpx.Response(200, json=FAKE_TOKEN_RESPONSE, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", fake_post)
    assert _dst_service_token(FAKE_CREDS) == "dst-bearer-token"


# --- _resolve_destination (returns a context dict) --------------------------

def _patch_destination_service(monkeypatch, vcap=FAKE_VCAP, dest_body=None):
    monkeypatch.setenv("VCAP_SERVICES", vcap)
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(("post", url, data))
        return httpx.Response(200, json=FAKE_TOKEN_RESPONSE, request=httpx.Request("POST", url))

    def fake_get(url, headers=None, timeout=None):
        calls.append(("get", url, headers or {}))
        return httpx.Response(200, json=dest_body or FAKE_DEST_RESPONSE, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_resolve_destination_returns_ctx_basic(monkeypatch):
    _patch_destination_service(monkeypatch)
    ctx = _resolve_destination("S4HANA_HTTP", user_token=None)
    assert ctx["base_url"] == "https://s4.client.example"
    assert ctx["auth_header"] == "Basic dXNlcjpwdw=="     # from authTokens http_header
    assert ctx["proxy_type"] == "OnPremise"
    assert ctx["sap_client"] == "150"


def test_resolve_destination_forwards_user_token(monkeypatch):
    """PrincipalPropagation placeholder: X-user-token forwarded when present."""
    calls = _patch_destination_service(monkeypatch)
    _resolve_destination("S4HANA_HTTP", user_token="user-jwt")
    get_calls = [c for c in calls if c[0] == "get"]
    assert get_calls and get_calls[0][2].get("X-user-token") == "user-jwt"


def test_resolve_destination_no_user_token(monkeypatch):
    calls = _patch_destination_service(monkeypatch)
    _resolve_destination("S4HANA_HTTP", user_token=None)
    assert "X-user-token" not in [c for c in calls if c[0] == "get"][0][2]


def test_resolve_destination_cached(monkeypatch):
    calls = _patch_destination_service(monkeypatch)
    _resolve_destination("S4HANA_HTTP", user_token="u1")
    _resolve_destination("S4HANA_HTTP", user_token="u1")
    assert len([c for c in calls if c[0] == "get"]) == 1


def test_resolve_destination_basic_from_user_password(monkeypatch):
    """No authTokens but User/Password present → build Basic header from them."""
    body = {"destinationConfiguration": {"URL": "https://s4.example",
                                          "User": "ABAP-SUPPORT", "Password": "pw"},
            "authTokens": []}
    _patch_destination_service(monkeypatch, dest_body=body)
    ctx = _resolve_destination("S4HANA_HTTP", user_token=None)
    assert ctx["auth_header"].startswith("Basic ")


def test_resolve_destination_no_auth_is_allowed(monkeypatch):
    """No authTokens and no User/Password → auth_header None (does not raise)."""
    body = {"destinationConfiguration": {"URL": "https://s4.example"}, "authTokens": []}
    _patch_destination_service(monkeypatch, dest_body=body)
    assert _resolve_destination("S4HANA_HTTP", user_token=None)["auth_header"] is None


def test_resolve_destination_no_url_raises(monkeypatch):
    _patch_destination_service(monkeypatch, dest_body={"destinationConfiguration": {"URL": ""},
                                                       "authTokens": [{"value": "tok"}]})
    with pytest.raises(RuntimeError, match="has no URL configured"):
        _resolve_destination("S4HANA_HTTP", user_token=None)


def test_resolve_destination_auth_token_error_raises(monkeypatch):
    _patch_destination_service(monkeypatch, dest_body={
        "destinationConfiguration": {"URL": "https://s4.example"},
        "authTokens": [{"error": "Token exchange failed: user not found"}]})
    with pytest.raises(RuntimeError, match="Token exchange failed"):
        _resolve_destination("S4HANA_HTTP", user_token="bad-jwt")


# --- _odata_get — profile branching ----------------------------------------

class _FakeClient:
    """Stands in for httpx.Client(proxy=...) as a context manager."""
    captured = {}

    def __init__(self, *a, **kw):
        _FakeClient.captured["kw"] = kw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, headers=None):
        _FakeClient.captured["url"] = url
        _FakeClient.captured["headers"] = headers or {}
        return httpx.Response(200, json={"d": {"results": [{"Material": "RM-001"}]}},
                              request=httpx.Request("GET", url))


def test_odata_get_onprem_basic_via_connectivity_proxy(monkeypatch):
    """On-prem: Basic auth header + sap-client + routed through the connectivity proxy."""
    monkeypatch.setattr("config.s4_service_profile", lambda: "onprem")
    monkeypatch.setattr(s4_client, "_resolve_destination",
                        lambda name, user_token: {"base_url": "https://s4-onprem.example",
                                                  "auth_header": "Basic abc", "proxy_type": "OnPremise",
                                                  "sap_client": "150"})
    monkeypatch.setattr(s4_client, "_vcap_connectivity_creds",
                        lambda: {"onpremise_proxy_host": "proxy.int", "onpremise_proxy_port": "20003",
                                 "url": "https://conn-xsuaa.example", "clientid": "c", "clientsecret": "s"})
    monkeypatch.setattr(s4_client, "_connectivity_proxy_token", lambda creds: "proxy-tok")
    monkeypatch.setattr(httpx, "Client", _FakeClient)
    import unittest.mock as mock
    with mock.patch.dict("sys.modules",
                         {"tool_provider.agw": mock.MagicMock(get_user_token=lambda: "joule-jwt")}):
        rows = s4_client._odata_get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    cap = _FakeClient.captured
    assert rows == [{"Material": "RM-001"}]
    assert "s4-onprem.example" in cap["url"] and "sap-client=150" in cap["url"]
    assert cap["headers"]["Authorization"] == "Basic abc"
    assert cap["headers"]["Proxy-Authorization"] == "Bearer proxy-tok"
    assert cap["kw"].get("proxy") == "http://proxy.int:20003"
    assert "APIKey" not in cap["headers"]


def test_odata_get_cloud_uses_apikey(monkeypatch):
    """Cloud profile: _odata_get calls the sandbox directly with an APIKey header."""
    monkeypatch.setattr("config.s4_service_profile", lambda: "cloud")
    monkeypatch.setattr(s4_client, "S4_API_KEY", "my-sandbox-key")

    def fake_get(url, headers=None, timeout=None):
        assert "sandbox.api.sap.com" in url
        assert headers.get("APIKey") == "my-sandbox-key"
        return httpx.Response(200, json={"d": {"results": []}}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    assert isinstance(_odata_get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod"), list)
