# Implementation Plan — Project Material Availability & Supply Risk Agent

## Scope
- Build scope: **full custom agent** (SAP Agent Golden Path, advisory / read-only).

## Selected approach
- Agent type: **LLM-orchestrated** (LangChain `create_agent` + `ChatLiteLLM`) over a deterministic domain core; tool loop bounded by `recursion_limit=15`, history summarized past 30k tokens. The LLM never computes numbers.
- Path: **pro-code** (hand-built scaffold on the Joule 2.0 A2A template; Joule-Studio bootstrap/MCP/eval skills unavailable in this environment — logged as the 6.1/6.2 exception).
- Platform / runtime: SAP AI Core (LiteLLM) + **Cloud Foundry** (region us10), 1 GB.

## Selected assets
- Cookbook: GDH AI Factory / KG Cookbook (primary); SAP Agent Golden Path scaffold.
- Accelerator / starter: `solution.yaml` + `assets/<asset>/` structure; separate Node.js chat UI as an upgrade over an inline demo page.
- Grounding strategy: **mix** — OData live reads + RAG (HANA Vector) + structured context injection; project data from SAP PS **or** Excel/CSV behind one boundary.

## Prerequisites
- BTP subaccount (CF, AI Core, XSUAA; optional Agent Gateway / Destination+Connectivity / HANA Cloud) in region us10.
- Joule IAS + JouleAdmin for registration; Space Developer CF role; memory quota ≥ 1 GB.
- AI Core service key kept **outside** the repo (never committed).
- Identity model: **principal propagation** (interactive purchasing persona via IAS).

## Ordered implementation steps
1. Prepare — restate value case; confirm advisory-only + API read policy (gate: L0-1, L0-5). ✅
2. Configure — mode flags + thresholds in `config.py` / `scoring.py`; model via `get_model_name()`; secrets via `.env`/VCAP (gate: L0-2, L0-6). ✅
3. Build (mock-first, `IBD_TESTING=1`) — 15 tools, deterministic domain core (scoring, simulation, prediction, recommend), HITL gate, RAG sanitize, resilience, observability (gate: L0-6, L0-8). ✅
4. Connect live data — `IBD_LIVE_S4=1` direct OData (Accelerator Hub sandbox) with `$top` caps + request cache + async executor; Agent Gateway path for production; advisory side-effects only (gate: L0-3/9, L0-6.6/6.7). ✅ (sandbox)
5. Test (offline) — `IBD_TESTING=1 pytest`: 175 tests, 73% coverage, `test_report.json` emitted (gate: L0-5, L0-7.1). ✅
6. Deploy & register — `manifest.yml` / `mta.yaml`, `asset.yaml` ORD IDs, `.env.example` ready; `cf push` done to us10; Joule registration pending IAS (gate: L0-7, L0-10). ⏳
7. Cleanup — no dead stubs, `.env` gitignored, no secrets committed (gate: L0-6). ✅

## Demo assets
- Mock fixtures (`IBD_TESTING=1`): seeded Tower Alpha scenario (structural steel on a critical-path slab pour + HIGH/MEDIUM/LOW/clean materials) exercising every risk band and the chronic-late pattern.
- Live sandbox (`IBD_LIVE_S4=1`): real S/4 OData via the Accelerator Hub sandbox.
- Chat UI: `assets/material-risk-ui` — Node/Express, A2A proxy, dynamic follow-up suggestion chips.

## Cleanup checklist
- [x] Dead scaffold / empty stub dirs removed
- [x] No secrets in code/markdown; `.env` gitignored
- [x] Mock data + demo UI retained (gated by mode flags)
- [x] Governance artifact set complete (13 docs + README)

## Applicable checklist subset
Full custom agent → all pillars L0-1…L0-10 apply; see `agent-outcome-report.md` (repo root) for every control's flag. Items that require the live BTP tenant (metering L0-4, benchmarking/safety L0-2/L0-5, go-live L0-7, live drift L0-10.3/10.4) are flagged ⚠️/❌ with remediation owned by the deploying team.

## Dependencies and owners
- SAP API read policy sign-off → procurement / API policy team.
- BTP entitlements (CF, AI Core, XSUAA, AGW) → BTP admin.
- Live SAP connectivity (gateway / destination / Cloud Connector) → client Basis.
- IAS principal propagation → IAS admin.

## Next action
Run the offline verification (CODE_WALKTHROUGH §Running tests), then complete Joule registration once IAS principal propagation is configured.
