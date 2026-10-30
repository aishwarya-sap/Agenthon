# ADR-0005: BAH sandbox connectivity + quota handling

- **Status:** Accepted
- **Date:** 2026-10-27

## Context
The our environment end-to-end test reads live S/4 data through the SAP Business Accelerator Hub sandbox
(`SAP_MODE=accelerator_hub`, APIKey auth, OData V2). Heavy testing exhausted the sandbox quota and
reads began failing.

## Decision
- Use the BAH sandbox S/4HANA Cloud `API_*` services for our test phase; the client landscape
  overrides these with its on-prem `OP_*` service names (config-driven per environment).
- The sandbox returns quota violations as **HTTP 500 with a `QuotaViolation` fault body**, not 429.
  Detect that body in `s4_client._get` and raise `QuotaExceeded` (terminal, non-retryable) so the
  resilience layer stops retrying and does not burn more quota.
- The quota is tied to the **account**, not the key — regenerating the API key does not reset it.
  While quota-locked, demo on mock data (`IBD_TESTING=1`) with AI Core still reasoning.

## Consequences
- A failed live read surfaces honestly ("live SAP data unavailable"); the LLM never fabricates over it.
- Live data returns automatically when the sandbox quota refreshes, or via a different-account key.
