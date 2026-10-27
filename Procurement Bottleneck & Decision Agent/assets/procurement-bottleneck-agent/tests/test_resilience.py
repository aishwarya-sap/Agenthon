"""Resilience contract tests: taxonomy, retry/backoff, no-retry, circuit breaker."""
import pytest

from app import resilience as R

pytestmark = pytest.mark.unit


def test_classify_http_status():
    assert isinstance(R.classify_http_status(401), R.AuthExpired)
    assert isinstance(R.classify_http_status(403), R.Forbidden)
    assert isinstance(R.classify_http_status(404), R.NotFound)
    assert isinstance(R.classify_http_status(429), R.Throttled)
    assert isinstance(R.classify_http_status(500), R.BackendUnavailable)


async def test_success_passthrough():
    async def ok(**kw):
        return {"value": [1, 2]}
    out = await R.call_tool_safely("t", ok, {})
    assert out == {"value": [1, 2]}


async def test_forbidden_not_retried():
    calls = {"n": 0}

    async def forbidden(**kw):
        calls["n"] += 1
        raise R.Forbidden()
    out = await R.call_tool_safely("t", forbidden, {})
    assert isinstance(out, R.ToolError) and out.code == "not_authorized"
    assert calls["n"] == 1  # no retry


async def test_notfound_not_retried():
    async def nf(**kw):
        raise R.NotFound()
    out = await R.call_tool_safely("t", nf, {})
    assert out.code == "not_found"


async def test_retry_then_success():
    state = {"n": 0}

    async def flaky(**kw):
        state["n"] += 1
        if state["n"] < 2:
            raise R.BackendUnavailable()
        return {"ok": True}
    out = await R.call_tool_safely("t", flaky, {})
    assert out == {"ok": True}
    assert state["n"] == 2


async def test_auth_refresh_once_then_success():
    state = {"n": 0, "refreshed": 0}

    async def refresh():
        state["refreshed"] += 1

    async def needs_auth(**kw):
        state["n"] += 1
        if state["refreshed"] == 0:
            raise R.AuthExpired()
        return {"ok": True}
    out = await R.call_tool_safely("t", needs_auth, {}, refresh_tokens=refresh)
    assert out == {"ok": True}
    assert state["refreshed"] == 1


async def test_circuit_breaker_opens():
    breaker = R.CircuitBreaker(threshold=2)

    async def always_down(**kw):
        raise R.BackendUnavailable()
    first = await R.call_tool_safely("t", always_down, {}, breaker=breaker)
    assert isinstance(first, R.ToolError)
    # breaker should now be open for this tool
    assert breaker.is_open("t")
    second = await R.call_tool_safely("t", always_down, {}, breaker=breaker)
    assert second.code == "circuit_open"
