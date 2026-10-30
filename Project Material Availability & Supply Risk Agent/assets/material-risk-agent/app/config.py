"""Central runtime configuration for the Project Material Risk agent.

Nothing here is a secret. Secrets (AICORE_*, S4_API_KEY, IAS client creds) come
from the environment / .env (git-ignored) / CF VCAP_SERVICES — never committed.

This module centralises the two cross-cutting concerns the handoff brief calls
out: the inbound-identity mode (mock | ias | xsuaa) at the A2A boundary, and the
S/4 connectivity mode + env-specific OData service names (cloud API_* for our
sandbox; on-prem OP_* for the Adarsh tenant).
"""
from __future__ import annotations

import os


AGENT_NAME = "material-risk-agent"

# --- Run mode ---------------------------------------------------------------
def is_mock_mode() -> bool:
    """True under IBD_TESTING — fully offline against the seeded fixtures."""
    return os.environ.get("IBD_TESTING", "").strip().lower() in ("1", "true", "yes", "on")


def is_live_s4() -> bool:
    """True under IBD_LIVE_S4 — call real S/4 OData (Accelerator Hub sandbox)."""
    return os.environ.get("IBD_LIVE_S4", "").strip().lower() in ("1", "true", "yes", "on")


def is_live_fallback() -> bool:
    """True when BOTH IBD_LIVE_S4 and IBD_TESTING are set — live-first, fall back
    to seeded data if a live read fails. Keeps the agent answering when the shared
    sandbox is unavailable; the fallback data is tagged 'simulated', never 'live'."""
    return is_live_s4() and is_mock_mode()


# --- Inbound identity (A2A boundary) ----------------------------------------
# mock (IBD_TESTING) | ias (Joule A2A — IAS user token) | xsuaa (legacy/direct).
# Joule delivers an IAS token, so AGENT_AUTH_MODE=ias is the Joule-integration path.
def agent_auth_mode() -> str:
    if is_mock_mode():
        return "mock"
    return os.environ.get("AGENT_AUTH_MODE", "xsuaa").strip().lower()


def ias_issuer() -> str:
    return os.environ.get("IAS_ISSUER", "").rstrip("/")


def ias_audience() -> str | None:
    return os.environ.get("IAS_AUDIENCE") or None


def ias_required_api() -> str | None:
    """The API exposed on the Custom-Agent IAS app (token's ias_apis claim)."""
    return os.environ.get("IAS_REQUIRED_API") or None


def ias_jwks_uri() -> str:
    explicit = os.environ.get("IAS_JWKS_URI")
    if explicit:
        return explicit
    issuer = ias_issuer()
    return f"{issuer}/oauth2/certs" if issuer else ""


def whoami_enabled() -> bool:
    """Diagnostic /whoami endpoint — OFF unless explicitly enabled. Never on in prod."""
    return os.environ.get("ENABLE_WHOAMI", "").strip().lower() in ("1", "true", "yes", "on")


# --- S/4 connectivity + env-specific OData service names --------------------
# The sandbox APIKey resolves S/4HANA Cloud `API_*` services (200); the on-prem
# `OP_*` names 403 there. So our environment test = cloud, Adarsh prod = on-prem. Make the
# names config-driven: S4_SERVICE_PROFILE = cloud | onprem (default cloud).
#
# Field names are IDENTICAL between the two profiles for the entities we read;
# only the service path prefix differs. Verified cloud names (Accelerator Hub,
# 2026-10-21); on-prem names from the Adarsh client API list.
_SERVICE_NAMES = {
    "cloud": {
        "material_stock": "API_MATERIAL_STOCK_SRV",
        "material_document": "API_MATERIAL_DOCUMENT_SRV",
        "purchase_order": "API_PURCHASEORDER_PROCESS_SRV",
        "purchase_requisition": "API_PURCHASEREQ_PROCESS_SRV",
        "business_partner": "API_BUSINESS_PARTNER",
        "info_record": "API_INFORECORD_PROCESS_SRV",
        "purchase_contract": "API_PURCHASECONTRACT_PROCESS_SRV",
    },
    # Adarsh on-prem S/4 exposes the standard API_* OData services (client-confirmed
    # service list, 2026-10), activated in /IWFND/MAINT_SERVICE and reached via the
    # S4HANA_DEV_HTTP destination + Cloud Connector. Same names as cloud; only the
    # transport differs (destination + connectivity proxy vs. Accelerator Hub APIKey).
    "onprem": {
        "material_stock": "API_MATERIAL_STOCK_SRV",
        "material_document": "API_MATERIAL_DOCUMENT_SRV",
        "purchase_order": "API_PURCHASEORDER_PROCESS_SRV",
        "purchase_requisition": "API_PURCHASEREQ_PROCESS_SRV",
        "business_partner": "API_BUSINESS_PARTNER",
        "info_record": "API_INFORECORD_PROCESS_SRV",
        "purchase_contract": "API_PURCHASECONTRACT_PROCESS_SRV",
    },
}


def s4_sap_client() -> str:
    """S/4 client number sent with on-prem OData calls (destination sap-client=150)."""
    return os.environ.get("S4_SAP_CLIENT", "150")


def s4_service_profile() -> str:
    return os.environ.get("S4_SERVICE_PROFILE", "cloud").strip().lower()


def s4_service(name: str) -> str:
    """Resolve a logical service key to the env-specific OData service path."""
    profile = s4_service_profile()
    names = _SERVICE_NAMES.get(profile, _SERVICE_NAMES["cloud"])
    return names[name]


# --- Decision/approval persistence (HANA Cloud) -----------------------------
# The agent persists its decision/intervention records to an append-only audit
# store. Default is the in-process MemoryStore (mock-first MVP + offline tests).
# Set MEMORY_BACKEND=hana to select the durable HANA Cloud backend
# (ZAGENT_DECISION_LOG table, INSERT/SELECT-only role, + Vector Engine recall).
HANA_DECISION_TABLE = os.environ.get("HANA_DECISION_TABLE", "ZAGENT_DECISION_LOG")
HANA_VECTOR_TABLE = os.environ.get("HANA_VECTOR_TABLE", "ZAGENT_DECISION_VEC")
HANA_SCHEMA = os.environ.get("HANA_SCHEMA", "")


def memory_backend() -> str:
    """Persistence backend for the decision log: 'in_memory' (default) or 'hana'."""
    return os.environ.get("MEMORY_BACKEND", "in_memory").strip().lower()


def hana_configured() -> bool:
    """True when HANA Cloud connection placeholders are present (host + user).

    Independent of MEMORY_BACKEND so deployment can verify the binding before
    flipping the backend. On CF the credentials arrive via VCAP_SERVICES (bound
    HANA/HDI service); locally they come from HANA_* env vars.
    """
    return bool(os.environ.get("HANA_HOST") and os.environ.get("HANA_USER"))
