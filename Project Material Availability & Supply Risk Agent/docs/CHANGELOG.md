# Changelog

All notable changes to this agent are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] — 2026-10-27

### Added
- Full spec set under `docs/specs/` (design-brief, functional-specification, technical-specification, rtm) and ADRs under `docs/decisions/`.
- Quality Gate (QG-) and Code Review (CR-) reports under `docs/`, aligned to the SAP BTP checklists.
- Live-first fallback: a failed live S/4 read serves seeded data tagged `signal_status=simulated` when both `IBD_LIVE_S4` and `IBD_TESTING` are set.
- `.cfignore` in the agent folder to exclude `.venv` from the CF droplet.
- Standalone Node/Express chat UI with dynamic `[SUGGESTIONS]` follow-up chips and a single attachment control.

### Changed
- Response is brief-by-default (headline + table) and expands only on request; tabular multi-material output; no technical/data-source names in user-facing text.
- Risk/date accuracy: `days_to_required`/`overdue` computed against the real current date; removed the hardcoded demo date.
- Monetary figures standardized to EUR in user-facing output.
- Documentation restructured to the SAP BTP layout; L0-1..L0-10 checklist replaced with QG/CR checklists.

### Fixed
- A2A agent-card endpoint migrated to `/.well-known/agent-card.json`.
- Context overflow on unfiltered queries: `$top=100` caps + `recursion_limit=15`.
- Event-loop stall: synchronous OData offloaded via `run_in_executor`.
- CF deploy crash loop: `.venv` was being bundled into the droplet (now excluded).

### Notes
- Agent code, `requirements.txt`, and the `python app/_boot.py` start command are unchanged (no `src/`/gunicorn migration).
- Pending: Joule registration, principal-propagation end-to-end test, HANA-backed memory.
