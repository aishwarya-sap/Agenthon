# ADR-0002: Mock-first via `IBD_TESTING`

- **Status:** Accepted
- **Date:** 2026-10-17

## Context
The agent must be developable and testable offline (no SAP tenant, no secrets, deterministic tests)
and demoable even when the live backend is unavailable.

## Decision
A single flag, `IBD_TESTING=1`, mocks the **SAP data boundary** only — `get_mcp_tools()` returns
deterministic fixtures from `mcp-mock.json`. Business logic is identical in mock and live; the switch
happens only at the tool/data layer.

## Consequences
- The full test suite runs offline with no SAP/AI-Core calls.
- For a demo while the live backend is quota-locked, flip `IBD_TESTING=1` on the deployed app to run
  end-to-end on realistic sample data.
- **Important corollary (see ADR-0004):** `IBD_TESTING` must mock *data*, not *LLM reasoning* — the
  LLM is gated separately on AI Core credentials.
