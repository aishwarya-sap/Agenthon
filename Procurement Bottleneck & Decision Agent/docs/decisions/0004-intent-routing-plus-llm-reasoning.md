# ADR-0004: Intent routing + LLM reasoning (decoupled from data-mock)

- **Status:** Accepted
- **Date:** 2026-10-27

## Context
Specific questions got the wrong handler (e.g. "show delivery performance history" returned the
open-PO list), and answers dumped every fact in a table instead of answering concisely. Root causes
were in two distinct layers.

## Decision
Two layers, clearly separated:

1. **Deterministic intent routing (regex) decides *which handler* runs.** A broad `(show|list)…(supplier|po)`
   pattern was swallowing specific questions; the fix is a dedicated, higher-priority intent (e.g.
   `_PERF_QUERY_RE` for delivery-performance) and explicit exclusion from the broad list pattern.
2. **The LLM decides *what to say and how much*.** `IBD_TESTING` mocks only the data boundary; the LLM
   is gated on `aicore_configured()` (AI Core creds present), so it reasons over mock data too. The
   prompt instructs: answer only what was asked, briefly; use only relevant facts; table only when
   several figures are needed. A deterministic focused-answer fallback runs if AI Core is unreachable.

We explicitly did **not** rewrite the internals into LangGraph/gen_ai_hub — that would change working
functionality for no user benefit.

## Consequences
- Wrong-handler bugs are fixed at the routing layer; verbosity is fixed at the prompt layer.
- Tests stay offline (no creds) and get the deterministic fallback; the deployed app (creds present)
  gets concise LLM reasoning.
