"""IBD_TESTING flag and minimal run-mode helpers for the generic scaffold."""
from __future__ import annotations
import os


def is_mock_mode() -> bool:
    return os.environ.get("IBD_TESTING", "").strip().lower() in ("1", "true", "yes", "on")
