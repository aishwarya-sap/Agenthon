"""Gunicorn configuration for the Procurement Bottleneck & Decision Agent on Cloud Foundry.

Production entry point (matches the GDH AI Factory reference): gunicorn with a Uvicorn
ASGI worker, fronting the Starlette A2A app built in ``app/main.py`` (module-level ``app``).

WEB_CONCURRENCY defaults to 1: the agent keeps per-context HITL approval state and the
institutional-memory store in-process, so a two-turn approve/cancel flow must hit the same
worker. Keep a single worker unless that state moves to a shared backend.

The local/dev path (`python -m app`) is unaffected — it runs uvicorn directly via ``app.main:main``.
"""
import os

# Single worker — required for in-memory HITL approval continuity (see module docstring).
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))

# Uvicorn ASGI worker — supports async/await and the A2A JSON-RPC surface.
worker_class = "uvicorn.workers.UvicornWorker"

# LLM calls (AI Core) need a generous timeout; also covers the Joule dialog window.
timeout = 120
graceful_timeout = 30
keepalive = 5

# Bind to the CF-assigned PORT (falls back to the configured default).
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Logs to stdout/stderr for the CF log drain -> BTP Cloud Logging.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("AGENT_LOG_LEVEL", "info").lower()
