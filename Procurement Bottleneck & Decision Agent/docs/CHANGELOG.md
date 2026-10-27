# Changelog

All notable changes to the Procurement Bottleneck & Decision Agent. Format follows
[Keep a Changelog](https://keepachangelog.com/); this agent is pre-1.0 (advisory pilot).

## [Unreleased]

### Added
- Dedicated **delivery-performance** intent and answer (supplier on-time rate, late count, average
  delay, risk band) so "show delivery performance history" no longer returns the open-PO list.
- Honest **backend-failure** reporting (`_backend_error_report`) — a failed SAP read returns "live
  SAP data unavailable" instead of letting the LLM fabricate PO details.
- `resilience.QuotaExceeded` — terminal (non-retryable) classification for BAH sandbox quota
  violations (returned as HTTP 500 with a `QuotaViolation` body), so retries stop burning quota.
- `config.aicore_configured()` — enables LLM reasoning whenever AI Core creds exist, independent of
  data-mock mode.
- CATL-style `docs/` tree (HANDOFF, specs, decisions, checklists) and authoritative QG/CR checklists.

### Changed
- Free-form answers now **concise and question-specific** — the LLM runs over mock data too (not just
  live), and the prompt instructs it to answer only what was asked (no full-table dumps).
- Agent responses use **business language** (removed "verdict"/"absorb"/"exposure" jargon) rendered
  as compact tables.
- Dashboard shows an amber "data unavailable" banner on a failed scan instead of a false "all clear".
- UI chat welcome restyled to match the Material Risk reference (centered welcome, subtle pill chips)
  while keeping the Daily Blockers dashboard as the landing.

### Fixed
- Single-line-item dashboard bug — `get_open_pr_po_chain` pulled only 1 PO (`$top:1`); now pulls a
  newest-first worklist.
- AI Core LLM silently falling back — model name needed a **dot** (`claude-4.5-sonnet`, not `-4-5-`)
  and the litellm stack had to be pinned (`litellm==1.94.1`); both fixed, real LLM output restored.
- Intent short-circuit swallowing valid questions (`wants_freeform` regex too narrow).

### Governance
- Replaced the non-standard "L0–L10 pillar" checklist with the authoritative Quality Gate (`QG-*`)
  and Code Review (`CR-*`) checklists.
