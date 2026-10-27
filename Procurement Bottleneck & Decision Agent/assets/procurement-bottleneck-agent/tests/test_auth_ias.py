"""IAS inbound token validation tests (Joule A2A path, L0-5).

Generates a throwaway RSA key, builds a JWKS, signs tokens, and exercises
validate_ias_token + validate_identity(AGENT_AUTH_MODE=ias) offline.
"""
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import auth_ias
from app.auth_ias import IASValidationError, validate_ias_token

pytestmark = pytest.mark.security

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
    claims = validate_ias_token(_sign(keypair, _claims(aud="")), issuer=ISSUER,
                                audience=AUD, jwks_uri="x", required_api=API)
    assert claims["sub"] == "P1"


def test_aud_match_accepted_without_api(keypair):
    claims = validate_ias_token(_sign(keypair, _claims(ias_apis=[])), issuer=ISSUER,
                                audience=AUD, jwks_uri="x", required_api=None)
    assert claims["sub"] == "P1"


def test_wrong_issuer_rejected(keypair):
    with pytest.raises(IASValidationError):
        validate_ias_token(_sign(keypair, _claims(iss="https://evil")), issuer=ISSUER,
                           audience=AUD, jwks_uri="x", required_api=API)


def test_expired_rejected(keypair):
    with pytest.raises(IASValidationError):
        validate_ias_token(_sign(keypair, _claims(exp=int(time.time()) - 10)), issuer=ISSUER,
                           audience=AUD, jwks_uri="x", required_api=API)


def test_wrong_audience_and_api_rejected(keypair):
    tok = _sign(keypair, _claims(aud="other", ias_apis=["something_else"]))
    with pytest.raises(IASValidationError):
        validate_ias_token(tok, issuer=ISSUER, audience=AUD, jwks_uri="x", required_api=API)


def test_bad_signature_rejected():
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tok = jwt.encode(_claims(), other, algorithm="RS256", headers={"kid": KID})
    with pytest.raises(IASValidationError):
        validate_ias_token(tok, issuer=ISSUER, audience=AUD, jwks_uri="x", required_api=API)


def test_validate_identity_ias_mode_accepts(monkeypatch, keypair):
    monkeypatch.delenv("IBD_TESTING", raising=False)
    monkeypatch.setenv("AGENT_AUTH_MODE", "ias")
    monkeypatch.setenv("IAS_ISSUER", ISSUER)
    monkeypatch.setenv("IAS_AUDIENCE", AUD)
    monkeypatch.setenv("IAS_REQUIRED_API", API)
    from app.agent_executor import validate_identity
    subject = validate_identity({"authorization": f"Bearer {_sign(keypair, _claims())}"})
    assert subject == "user@example.com"


def test_validate_identity_ias_mode_rejects_bad(monkeypatch, keypair):
    monkeypatch.delenv("IBD_TESTING", raising=False)
    monkeypatch.setenv("AGENT_AUTH_MODE", "ias")
    monkeypatch.setenv("IAS_ISSUER", ISSUER)
    monkeypatch.setenv("IAS_REQUIRED_API", API)
    from app.agent_executor import IdentityError, validate_identity
    with pytest.raises(IdentityError):
        validate_identity({"authorization": f"Bearer {_sign(keypair, _claims(iss='https://evil'))}"})


def test_validate_identity_ias_mode_requires_bearer(monkeypatch):
    monkeypatch.delenv("IBD_TESTING", raising=False)
    monkeypatch.setenv("AGENT_AUTH_MODE", "ias")
    monkeypatch.setenv("IAS_ISSUER", ISSUER)
    from app.agent_executor import IdentityError, validate_identity
    with pytest.raises(IdentityError):
        validate_identity({})
