"""Test setup for the agent-owned suite.

Puts app/ on sys.path (the runtime runs main.py from inside app/, so modules are
top-level), forces mock mode, and resets the in-process memory store per test.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("IBD_TESTING", "1")

_APP = Path(__file__).resolve().parent.parent / "app"
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_memory():
    from domain import memory
    memory.reset_memory_store()
    yield
    memory.reset_memory_store()
