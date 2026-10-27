"""Configuration — read from environment, never hardcoded."""
import os

AGENT_NAME: str = os.environ.get("AGENT_NAME", "agent-starter-kit")  # TODO: rename
AGENT_VERSION: str = os.environ.get("AGENT_VERSION", "1.0.0")

TOKEN_BUDGET_PER_RUN: int = int(os.environ.get("TOKEN_BUDGET_PER_RUN", "50000"))
RAG_SIMILARITY_GATE: float = float(os.environ.get("RAG_SIMILARITY_GATE", "0.80"))
CIRCUIT_BREAKER_THRESHOLD: int = int(os.environ.get("CIRCUIT_BREAKER_THRESHOLD", "3"))

AICORE_BASE_URL: str = os.environ.get("AICORE_BASE_URL", "")
AICORE_CLIENT_ID: str = os.environ.get("AICORE_CLIENT_ID", "")
AICORE_CLIENT_SECRET: str = os.environ.get("AICORE_CLIENT_SECRET", "")
AICORE_AUTH_URL: str = os.environ.get("AICORE_AUTH_URL", "")
AICORE_RESOURCE_GROUP: str = os.environ.get("AICORE_RESOURCE_GROUP", "default")


def is_mock_mode() -> bool:
    return os.environ.get("IBD_TESTING", "").lower() in ("1", "true")


def agent_auth_mode() -> str:
    if is_mock_mode():
        return "mock"
    # Default to the production-safe mode (matches .env.example / manifest.yml).
    # If unset, fail closed to ias rather than a weaker mode.
    return os.environ.get("AGENT_AUTH_MODE", "ias").strip().lower()
