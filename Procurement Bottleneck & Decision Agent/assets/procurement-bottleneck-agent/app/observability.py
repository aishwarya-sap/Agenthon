"""Observability: structured logging, correlation IDs, milestone instrumentation,
PII redaction, and OpenTelemetry spans.

Pure-stdlib with a graceful OpenTelemetry fallback so the module imports and runs
offline even when the OTel packages are absent (tests / air-gapped dev). In
production the real OTel SDK is installed and `auto_instrument()` wires it up.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from contextlib import contextmanager
from typing import Any

from . import config

# --- OpenTelemetry (optional) ----------------------------------------------
try:  # pragma: no cover - exercised only when OTel is installed
    from opentelemetry import trace as _otel_trace

    _OTEL = True
    tracer = _otel_trace.get_tracer(config.AGENT_NAME)
except Exception:  # pragma: no cover - offline / not installed
    _OTEL = False

    class _NoopSpan:
        def set_attribute(self, *_a, **_k):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    class _NoopTracer:
        @contextmanager
        def start_as_current_span(self, _name, *_a, **_k):
            yield _NoopSpan()

    tracer = _NoopTracer()


def auto_instrument() -> None:
    """Hook for OTel auto-instrumentation. Called at the top of main.py before any
    AI framework import. No-op when OTel is unavailable (offline/tests)."""
    if not _OTEL:  # pragma: no cover
        return
    # Real auto-instrumentation (logging/httpx) is wired by the platform at deploy
    # time; nothing to do here beyond ensuring the tracer provider exists.


# --- Structured logging -----------------------------------------------------
_SECRET_KEYS = re.compile(
    r"(client[_-]?secret|password|api[_-]?key|authorization|bearer|token|assertion)",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
# High-entropy secret backstop: long base64/hex-like runs (JWTs, keys). Excludes
# snake_case identifiers (tool names, field names) which contain underscores.
_LONG_TOKEN = re.compile(r"[A-Za-z0-9+/=]{40,}")


def redact(value: Any) -> Any:
    """Redact secrets/PII before anything is logged.

    - secret-named keys -> '<redacted>'
    - email addresses -> keep only the domain (design: MS-Graph email reduced to
      supplier domain + PO reference, no personal identifiers persisted)
    - long opaque tokens -> '<redacted>'
    """
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if _SECRET_KEYS.search(str(k)):
                out[k] = "<redacted>"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        s = _EMAIL.sub(lambda m: f"<email@{m.group(1)}>", value)
        s = _LONG_TOKEN.sub("<redacted>", s)
        return s
    return value


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("correlation_id", "context_id", "tool_name", "sap_mode",
                    "status", "latency_ms", "prompt_tokens", "completion_tokens",
                    "prompt_version", "milestone"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(redact(extra))
        return json.dumps(payload, default=str)


_configured = False


def get_logger(name: str = config.AGENT_NAME) -> logging.Logger:
    global _configured
    logger = logging.getLogger(name)
    if not _configured:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(logging.INFO)
        _configured = True
    return logger


def log_event(logger: logging.Logger, msg: str, **fields: Any) -> None:
    """Emit one structured record. Fields are redacted before serialization."""
    logger.info(msg, extra={"extra_fields": redact(fields)})


def log_milestone(logger: logging.Logger, milestone_id: str, achieved: bool, description: str,
                  **fields: Any) -> None:
    """Milestone instrumentation. Pattern: `[MILESTONE_ID].[achieved|missed]: desc`."""
    state = "achieved" if achieved else "missed"
    logger.info(
        f"{milestone_id}.{state}: {description}",
        extra={"milestone": f"{milestone_id}.{state}", "extra_fields": redact(fields)},
    )


# Milestone catalogue — the agent's business steps (design process flow S1..S18).
MILESTONES = {
    "M1": "Delay/silence detection scan completed",
    "M2": "PR→PO chain traced",
    "M3": "Critical-path linkage resolved",
    "M4": "Consequence simulation computed",
    "M5": "Institutional memory recalled",
    "M6": "Ranked recommendation synthesized",
    "M7": "HoD approval gate reached",
    "M8": "Decision record written (approved)",
    "M9": "Escalation notification raised (approved)",
}
