"""Central configuration for the Procurement Bottleneck & Decision Agent.

All business thresholds live here as plain Python constants. In production these
are externalized to **SAP Build Process Automation — Business Rules** so the
Procurement Centre of Excellence can edit them without a code deployment; this
module is the single source of truth consumed by the deterministic skills and the
orchestration layer, and mirrors the Business Rules decision tables 1:1.

Nothing here is a secret. Secrets are supplied at runtime via environment
variables / Cloud Foundry VCAP_SERVICES (see .env.example), never committed.
"""
from __future__ import annotations

import os

# --- Model / runtime (overridable via environment) -------------------------
AGENT_NAME = "procurement-bottleneck-decision-agent"
AGENT_VERSION = "1.0.0"
AGENT_MODEL = os.environ.get("AGENT_MODEL", "sap/anthropic--claude-4.5-sonnet")
AGENT_MODEL_FALLBACK = os.environ.get("AGENT_MODEL_FALLBACK", "sap/anthropic--claude-4.5-haiku")
LLM_TEMPERATURE = 0.0
TOKEN_BUDGET_PER_RUN = 52_000  # design agent-detail budget; enforced as a soft ceiling

# --- Delay / silence detection ---------------------------------------------
SCAN_HORIZON_DAYS = 14          # EKPO.EINDT within this horizon with no VGABE=1 ack is in scope
SILENCE_TOLERANCE_DAYS = 3      # < 3 days of silence -> log and exit (no action worth taking yet)
SILENCE_HITL_TRIGGER_DAYS = 7   # >= 7 days of silence on a critical-path PO -> raise the HoD gate
# Note: the two thresholds coexist by design. 3 days is the floor to *consider* a PO;
# 7 days is the default that *triggers* a Human-in-the-Loop review for the HoD.

# --- Critical path ----------------------------------------------------------
CRITICAL_PATH_FLOAT_BUFFER_DAYS = 5   # float > buffer -> downgrade to watch list; float == 0 -> critical

# --- Materiality / escalation ----------------------------------------------
MATERIALITY_EXPOSURE_EUR = 25_000.0   # total consequence exposure above this -> high-urgency path
PENALTY_EXPOSURE_HITL_EUR = 10_000.0  # penalty exposure above this -> mandatory HoD confirmation
OBSOLETE_PO_AGE_DAYS = 90             # no GRN, no confirmation, due date older than this -> obsolete candidate

# --- Vendor performance -----------------------------------------------------
SUPPLIER_CONFIRMATION_SLA_HOURS = 48  # KPI: >= 85% of critical-path POs confirmed within 48h of issuance
SUPPLIER_CONFIRMATION_SLA_TARGET_PCT = 85
VENDOR_RISK_HIGH = 70                 # supplier_delivery_risk_score >= -> high risk band
VENDOR_RISK_MEDIUM = 40               # >= medium, below VENDOR_RISK_HIGH

# --- RAG --------------------------------------------------------------------
RAG_SIMILARITY_GATE = 0.82            # include retrieved chunks only at/above this similarity
RAG_TOP_K = 4
EMBEDDING_MODEL = "text-embedding-3-small"

# --- Emergency sourcing -----------------------------------------------------
# Configurable spot-market uplift (% of PO net price) by material category.
EMERGENCY_SOURCING_PREMIUM_PCT = {
    "STEEL": 0.18,
    "CONCRETE": 0.12,
    "ELECTRICAL": 0.22,
    "MECHANICAL": 0.20,
    "DEFAULT": 0.15,
}

# --- Memory -----------------------------------------------------------------
MEMORY_RECALL_TOP_N = 5               # top-N similar prior decision records to recall

# --- HITL -------------------------------------------------------------------
APPROVAL_KEYWORDS = ("approve", "confirm", "yes proceed", "proceed", "yes")
REJECTION_KEYWORDS = ("reject", "cancel", "no", "stop", "decline")

# --- Resilience -------------------------------------------------------------
MAX_RETRIES = 3
CIRCUIT_BREAKER_THRESHOLD = 3         # K consecutive failures to one tool -> stop calling it this run
TOOL_TIMEOUT_SECONDS = 30

# --- Governance -------------------------------------------------------------
FINANCIAL_DISCLAIMER = (
    "These are estimates based on available SAP data. "
    "Validate with your finance and procurement teams before acting."
)
SESSION_TTL_HOURS = 24                # IdeaState working-memory TTL


# --- Inbound identity (A2A boundary) ----------------------------------------
# mock (IBD_TESTING) | ias (Joule A2A — IAS user token) | xsuaa (legacy/direct XSUAA)
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
    # The API exposed on the Custom-Agent IAS app (appears in the token's ias_apis claim).
    return os.environ.get("IAS_REQUIRED_API") or None


def ias_jwks_uri() -> str:
    explicit = os.environ.get("IAS_JWKS_URI")
    if explicit:
        return explicit
    issuer = ias_issuer()
    return f"{issuer}/oauth2/certs" if issuer else ""


def whoami_enabled() -> bool:
    """Diagnostic /whoami endpoint — OFF unless explicitly enabled. Never leave on in prod."""
    return os.environ.get("ENABLE_WHOAMI", "").strip().lower() in ("1", "true")


def is_mock_mode() -> bool:
    """True when the agent must run fully offline against deterministic fixtures."""
    return os.environ.get("IBD_TESTING", "").lower() in ("1", "true")


def aicore_configured() -> bool:
    """True when SAP AI Core credentials are present, so the LLM can be called.

    This is deliberately independent of IBD_TESTING: mocking the SAP *data* boundary
    (offline fixtures) must not disable the LLM's *reasoning*. On the deployed demo
    the data is mocked but AI Core creds are set, so the model still composes answers;
    in the test suite no creds are set, so the deterministic fallback is used.
    """
    return bool(os.environ.get("AICORE_CLIENT_ID") and os.environ.get("AICORE_AUTH_URL"))


def emergency_premium_pct(material_category: str | None) -> float:
    """Return the configured spot-market premium for a material category."""
    key = (material_category or "DEFAULT").upper()
    return EMERGENCY_SOURCING_PREMIUM_PCT.get(key, EMERGENCY_SOURCING_PREMIUM_PCT["DEFAULT"])


# --- Grouped typed settings (GDH AI Factory standard surface) ---------------
# A typed, grouped accessor over the same env vars as the module constants above,
# with an AGENT_ env prefix and a get_settings() singleton (the shape the template
# expects). Callers migrate from the constants to get_settings() incrementally — the
# constants remain the operational source meanwhile. The pydantic-settings import is
# guarded so the offline test venv (which does not install it) still imports this module.
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class AgentSettings(BaseSettings):
        """Typed governance/runtime settings. Env: AGENT_MODEL, AGENT_TEMPERATURE, ..."""
        model_config = SettingsConfigDict(env_prefix="AGENT_", extra="ignore",
                                          protected_namespaces=())

        model: str = AGENT_MODEL
        model_fallback: str = AGENT_MODEL_FALLBACK
        temperature: float = LLM_TEMPERATURE
        token_budget_per_run: int = TOKEN_BUDGET_PER_RUN
        rag_similarity_gate: float = RAG_SIMILARITY_GATE
        circuit_breaker_threshold: int = CIRCUIT_BREAKER_THRESHOLD

    _settings: "AgentSettings | None" = None

    def get_settings() -> "AgentSettings":
        """Process-wide singleton (module-level, not lru_cache — resettable in tests)."""
        global _settings
        if _settings is None:
            _settings = AgentSettings()
        return _settings

    def reset_settings() -> None:
        global _settings
        _settings = None

except Exception:  # pragma: no cover - pydantic-settings absent offline; constants remain the source
    def get_settings():  # type: ignore[misc]
        raise RuntimeError("pydantic-settings not installed; use the module constants in config.py")

    def reset_settings() -> None:  # type: ignore[misc]
        return None
