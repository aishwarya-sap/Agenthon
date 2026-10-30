"""IAS inbound token validation tests (Joule A2A path, L0-5 / principal propagation).

Generates a throwaway RSA key, builds a JWKS, signs tokens, and exercises
validate_ias_token offline (JWKS fetch is monkeypatched). Flat imports: conftest
puts app/ on sys.path.
"""
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import auth_ias
import config
from auth_ias import IASValidationError, validate_ias_token

ISSUER = "https://tenant.accounts.ondemand.com"
AUD = "custom-agent-client-id"
API = "a2a_custom_agent_app_api"
KID = "test-key-1"


@pytest.fixture
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def _patch_jwks(monkeypatch, keypair):
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(keypair.public_key()))
    jwk.update({"kid": KID, "use": "sig", "alg": "RS256"})
    auth_ias.reset_jwks_cache()
    monkeypatch.setattr(auth_ias, "_fetch_jwks", lambda uri: {"keys": [jwk]})
    yield
    auth_ias.reset_jwks_cache()


def _claims(**over):
    c = {"iss": ISSUER, "aud": AUD, "mail": "user@example.com", "sub": "P1",
         "ias_apis": [API], "exp": int(time.time()) + 300}
    c.update(over)
    return c


def _sign(keypair, claims, kid=KID):
    return jwt.encode(claims, keypair, algorithm="RS256", headers={"kid": kid})


def test_valid_token_returns_claims(keypair):
    claims = validate_ias_token(_sign(keypair, _claims()), issuer=ISSUER,
                                audience=AUD, jwks_uri="x", required_api=API)
    assert claims["mail"] == "user@example.com"


def test_api_grant_accepted_when_aud_empty(keypair):
    # Joule's IAS token often leaves aud empty; the ias_apis grant must carry it.
    claims = validate_ias_token(_sign(keypair, _claims(aud="")), issuer=ISSUER,
                                audience=AUD, jwks_uri="x", required_api=API)
    assert claims["sub"] == "P1"


def test_expired_token_rejected(keypair):
    with pytest.raises(IASValidationError):
        validate_ias_token(_sign(keypair, _claims(exp=int(time.time()) - 10)),
                           issuer=ISSUER, audience=AUD, jwks_uri="x", required_api=API)


def test_wrong_issuer_rejected(keypair):
    with pytest.raises(IASValidationError):
        validate_ias_token(_sign(keypair, _claims(iss="https://evil.example")),
                           issuer=ISSUER, audience=AUD, jwks_uri="x", required_api=API)


def test_bad_audience_and_missing_api_rejected(keypair):
    with pytest.raises(IASValidationError):
        validate_ias_token(_sign(keypair, _claims(aud="someone-else", ias_apis=[])),
                           issuer=ISSUER, audience=AUD, jwks_uri="x", required_api=API)


def test_tampered_signature_rejected(keypair):
    token = _sign(keypair, _claims())
    tampered = token[:-4] + ("abcd" if not token.endswith("abcd") else "efgh")
    with pytest.raises(IASValidationError):
        validate_ias_token(tampered, issuer=ISSUER, audience=AUD,
                           jwks_uri="x", required_api=API)


def test_decode_unverified_returns_safe_subset(keypair):
    claims = auth_ias.decode_unverified(_sign(keypair, _claims()))
    assert claims["sub"] == "P1" and claims["mail"] == "user@example.com"


# --- config: env-driven service-name profile (cloud API_* vs on-prem OP_*) ---
def test_service_profile_cloud_vs_onprem(monkeypatch):
    # Client on-prem S/4 exposes the standard API_* services (same names as cloud);
    # only the transport differs (destination + Cloud Connector vs. sandbox APIKey).
    monkeypatch.setenv("S4_SERVICE_PROFILE", "cloud")
    assert config.s4_service("material_stock") == "API_MATERIAL_STOCK_SRV"
    assert config.s4_service("purchase_order") == "API_PURCHASEORDER_PROCESS_SRV"
    monkeypatch.setenv("S4_SERVICE_PROFILE", "onprem")
    assert config.s4_service("material_stock") == "API_MATERIAL_STOCK_SRV"
    assert config.s4_service("purchase_order") == "API_PURCHASEORDER_PROCESS_SRV"


def test_auth_mode_mock_under_ibd_testing(monkeypatch):
    monkeypatch.setenv("IBD_TESTING", "1")
    assert config.agent_auth_mode() == "mock"
    monkeypatch.setenv("IBD_TESTING", "")
    monkeypatch.setenv("AGENT_AUTH_MODE", "ias")
    assert config.agent_auth_mode() == "ias"
