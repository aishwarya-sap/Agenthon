"""IBD_TESTING flag and minimal run-mode helpers for the generic scaffold."""
from __future__ import annotations
import os


def is_mock_mode() -> bool:
    return os.environ.get("IBD_TESTING", "").strip().lower() in ("1", "true", "yes", "on")


def memory_backend() -> str:
    """Decision/approval persistence backend: 'in_memory' (default) or 'hana'.

    'hana' selects a durable HANA Cloud audit store (append-only ZAGENT_DECISION_LOG
    + optional Vector Engine recall). Implement the store before enabling it.
    """
    return os.environ.get("MEMORY_BACKEND", "in_memory").strip().lower()


def hana_configured() -> bool:
    """True when HANA Cloud connection placeholders are present (host + user)."""
    return bool(os.environ.get("HANA_HOST") and os.environ.get("HANA_USER"))
