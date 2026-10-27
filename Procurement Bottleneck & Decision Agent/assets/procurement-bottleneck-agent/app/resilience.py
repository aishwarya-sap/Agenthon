"""Error handling & resilience contract (README §3b).

An advisory agent that silently hallucinates around a failed SAP call is worse
than one that says "I couldn't reach the data." This module defines what a tool
call *returns* when it fails, and wraps tool invocation with a retry / backoff /
circuit-breaker policy. All SAP calls in this agent are idempotent GETs
(advisory-only), so retry is safe — but the guard is explicit so any future
non-GET tool must opt in.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from . import config
from .observability import get_logger, log_event

logger = get_logger()


# --- Typed tool failures ----------------------------------------------------
class ToolFailure(Exception):
    """Base class carrying a user-safe message (never a raw trace/SAP payload)."""

    code = "unavailable"
    user_msg = "SAP data is temporarily unavailable. Please retry shortly."
    retryable = False


class AuthExpired(ToolFailure):
    code, user_msg, retryable = "auth_expired", "Re-authenticating…", True


class Throttled(ToolFailure):
    code, user_msg, retryable = "throttled", "The backend is busy; retrying.", True


class QuotaExceeded(ToolFailure):
    # Daily/periodic request quota used up (e.g. BAH sandbox). Retrying inside one
    # request cannot help — the quota only resets on the provider's clock, so terminal.
    code = "quota_exceeded"
    user_msg = "The SAP sandbox request quota has been used up; it resets on the provider's schedule."
    retryable = False


class BackendUnavailable(ToolFailure):
    code, user_msg, retryable = "backend_unavailable", "SAP backend is temporarily unavailable.", True


class Forbidden(ToolFailure):
    code = "not_authorized"
    user_msg = "You don't have authorization to read this SAP data; contact Basis."
    retryable = False


class NotFound(ToolFailure):
    code = "not_found"
    user_msg = "That record or service was not found in SAP."
    retryable = False


@dataclass
class ToolError:
    """Advisory-safe error the agent folds into its answer (never the raw exception)."""
    code: str
    user_msg: str
    tool_name: str = ""

    @property
    def is_error(self) -> bool:
        return True


def classify_http_status(status: int) -> ToolFailure:
    """Map an HTTP status to the resilience taxonomy (README §3b table)."""
    if status == 401:
        return AuthExpired()
    if status == 403:
        return Forbidden()
    if status == 404:
        return NotFound()
    if status == 429:
        return Throttled()
    return BackendUnavailable()


@dataclass
class CircuitBreaker:
    """Stop calling a tool after K consecutive failures within one request."""
    threshold: int = config.CIRCUIT_BREAKER_THRESHOLD
    _failures: dict[str, int] = field(default_factory=dict)

    def is_open(self, tool_name: str) -> bool:
        return self._failures.get(tool_name, 0) >= self.threshold

    def record_failure(self, tool_name: str) -> None:
        self._failures[tool_name] = self._failures.get(tool_name, 0) + 1

    def record_success(self, tool_name: str) -> None:
        self._failures.pop(tool_name, None)


async def _backoff(attempt: int) -> None:
    # Exponential backoff; kept tiny in mock/test (no real network).
    await asyncio.sleep(min(0.01 * (2 ** attempt), 0.2))


async def call_tool_safely(
    tool_name: str,
    func: Callable[..., Awaitable[Any]],
    args: dict[str, Any],
    *,
    breaker: CircuitBreaker | None = None,
    refresh_tokens: Callable[[], Awaitable[None]] | None = None,
    correlation_id: str = "",
) -> Any | ToolError:
    """Invoke a tool coroutine under the resilience policy.

    Returns the tool result, or a ``ToolError`` the agent folds into its answer.
    Retries only idempotent GETs (all tools here) with backoff; 403/404 never retry.
    """
    breaker = breaker or CircuitBreaker()
    if breaker.is_open(tool_name):
        return ToolError("circuit_open", "SAP data source repeatedly failed; skipped for this request.", tool_name)

    last: ToolFailure = BackendUnavailable()
    for attempt in range(config.MAX_RETRIES):
        started = asyncio.get_event_loop().time()
        try:
            result = await func(**args)
            breaker.record_success(tool_name)
            log_event(logger, "tool_call", tool_name=tool_name, status="ok",
                      correlation_id=correlation_id,
                      latency_ms=int((asyncio.get_event_loop().time() - started) * 1000))
            return result
        except AuthExpired as exc:
            last = exc
            if refresh_tokens is not None:
                await refresh_tokens()
            continue
        except (Throttled, BackendUnavailable) as exc:
            last = exc
            breaker.record_failure(tool_name)
            await _backoff(attempt)
            continue
        except (Forbidden, NotFound, QuotaExceeded) as exc:  # terminal — do not retry
            log_event(logger, "tool_call", tool_name=tool_name, status=exc.code,
                      correlation_id=correlation_id)
            return ToolError(exc.code, exc.user_msg, tool_name)
        except Exception as exc:  # unknown — treat as backend failure, never leak
            last = BackendUnavailable()
            breaker.record_failure(tool_name)
            log_event(logger, "tool_call", tool_name=tool_name, status="error",
                      correlation_id=correlation_id, error=type(exc).__name__)
            await _backoff(attempt)
            continue

    log_event(logger, "tool_call", tool_name=tool_name, status=last.code, correlation_id=correlation_id)
    return ToolError(last.code, last.user_msg, tool_name)
