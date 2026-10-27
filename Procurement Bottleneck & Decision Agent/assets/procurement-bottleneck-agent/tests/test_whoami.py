"""/whoami diagnostic endpoint tests."""
import jwt
import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.server


def _client():
    from app.main import build_app
    return TestClient(build_app())


def test_whoami_404_when_disabled(monkeypatch):
    monkeypatch.delenv("ENABLE_WHOAMI", raising=False)
    r = _client().get("/whoami")
    assert r.status_code == 404


def test_whoami_reports_mode_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_WHOAMI", "1")
    r = _client().get("/whoami")
    assert r.status_code == 200
    data = r.json()
    assert "auth_mode" in data
    assert "s4_canary" in data
    assert data["inbound_token_present"] is False
    assert data["boundary_validation"]["result"] in ("pass", "fail", "n/a")


def test_whoami_echoes_unverified_claims(monkeypatch):
    monkeypatch.setenv("ENABLE_WHOAMI", "1")
    tok = jwt.encode({"sub": "P1", "mail": "u@x.com", "ias_apis": ["a2a_custom_agent_app_api"]},
                     "secret", algorithm="HS256")
    r = _client().get("/whoami", headers={"Authorization": f"Bearer {tok}"})
    data = r.json()
    assert data["inbound_token_present"] is True
    assert data["inbound_token_claims"].get("mail") == "u@x.com"
    assert "a2a_custom_agent_app_api" in data["inbound_token_claims"].get("ias_apis", [])
