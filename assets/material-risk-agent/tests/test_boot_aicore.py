"""Unit tests for app/_boot.py — the AI Core credential launcher shim.

Copied into <AGENT_DIR>/tests/ by /cf-deploy for any LLM agent. Verifies the three
behaviours the bound-service credential mechanism depends on:
  1. maps a bound service's creds from VCAP_SERVICES into AICORE_* env vars,
  2. no-op when AICORE_CLIENT_ID is already set (explicit export / cf set-env wins),
  3. no-op off-CF (no VCAP_SERVICES) and on unparseable VCAP_SERVICES.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from _boot import apply_vcap_aicore

_CREDS = {
    "AICORE_CLIENT_ID": "id-123",
    "AICORE_CLIENT_SECRET": "secret-xyz",
    "AICORE_AUTH_URL": "https://auth.example",
    "AICORE_BASE_URL": "https://api.example",
}


def _vcap(creds):
    # Mirrors how a bound user-provided service appears in VCAP_SERVICES.
    return json.dumps({"user-provided": [{"name": "aicore-creds", "credentials": creds}]})


def test_maps_bound_creds_into_env():
    env = {"VCAP_SERVICES": _vcap(_CREDS)}
    apply_vcap_aicore(env)
    for key, value in _CREDS.items():
        assert env[key] == value


def test_noop_when_already_set():
    env = {
        "AICORE_CLIENT_ID": "preset-id",
        "AICORE_CLIENT_SECRET": "preset-secret",
        "VCAP_SERVICES": _vcap(_CREDS),
    }
    apply_vcap_aicore(env)
    # An explicit export / cf set-env wins — the bound service must not clobber it.
    assert env["AICORE_CLIENT_ID"] == "preset-id"
    assert env["AICORE_CLIENT_SECRET"] == "preset-secret"


def test_noop_off_cf():
    env = {}
    apply_vcap_aicore(env)
    assert "AICORE_CLIENT_ID" not in env


def test_noop_on_unparseable_vcap():
    env = {"VCAP_SERVICES": "{not json"}
    apply_vcap_aicore(env)
    assert "AICORE_CLIENT_ID" not in env
