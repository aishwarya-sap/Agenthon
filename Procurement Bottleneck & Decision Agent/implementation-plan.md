# Implementation Plan — Critical-Path Procurement Consequence Agent

## Scope
- Build scope: **full custom agent** (SAP Agent Golden Path, advisory/read-only).

## Selected approach
- Agent type: **orchestrated graph** — deterministic tool/skill core with two LLM touch-points (intent framing, verdict synthesis); step- and cost-bounded (not a free ReAct loop).
- Path: **pro-code** (hand-built scaffold faithful to the documented `sap-agent-bootstrap` output; the Joule-Studio bootstrap/MCP/eval skills are unavailable in this environment).
- Platform / runtime: SAP AI Core (LiteLLM) + **Cloud Foundry** (region us10).

## Selected assets
- Cookbook: CoE pattern (secondary) after evaluating the primary GDH AI Factory dev-tools cookbook.
- Accelerator / starter: Agent-GoldenPath-Kit structure (`solution.yaml` + `assets/<asset>/`).
- Grounding strategy: **mix** — OData/CDS + BDC data products + RAG (HANA Vector Engine) + institutional memory; project data from SAP PS **or** Excel/CSV behind one boundary.

## Prerequisites
- BTP subaccount (CF, AI Core, XSUAA; optional Agent Gateway / Destination+Connectivity / HANA Cloud) in region us10.
- Joule IAS (`das-ias`) + JouleAdmin for registration; Space Developer CF role; memory quota ≥ 512M.
- AI Core service key (kept outside the repo at `/Users/I778959/Documents/Common Repo/BAI-AICore-Credentials.md`).
- Identity model: **principal propagation** (interactive HoD persona).

## Ordered implementation steps
1. Prepare — restate value case; confirm advisory-only + API read policy (gate: L0-1, L0-5). ✅
2. Configure — thresholds in `config.py`; model via `AGENT_MODEL`; secrets via `.env`/VCAP (gate: L0-2, L0-6). ✅
3. Build (mock-first, IBD_TESTING=1) — 13 tools, 3 skills, orchestration, 4-dimension simulation, memory, 9 HITL checkpoints, resilience, observability (gate: L0-6, L0-8). ✅
4. Connect knowledge & actions — mock MCP layer + in-process tools; SAP PS/Excel boundary; RAG with similarity gate; advisory side-effects only (gate: L0-3/9, L0-6.6/6.7). ✅ (mock)
5. Test (offline) — `IBD_TESTING=1 pytest`: 72 tests, coverage 91.6%, `test_report.json` emitted (gate: L0-5, L0-7.1/7.6). ✅ (offline subset)
6. Deploy & register — `manifest.yml`, `asset.yaml` ORD IDs, `xs-security.json`, `.env.example` ready; **user runs `cf push`** then Joule registration (gate: L0-7, L0-6.8, L0-10). ⏳ user action
7. Cleanup — no dead stubs, no `[illustrative]` leftovers, `.env` gitignored, no secrets committed (gate: L0-6). ✅

## Demo assets (mock-mode, IBD_TESTING=1)
- Mock data fixtures: `mcp-mock.json` (8 SAP/RAG tools, seed scenario: supplier LIFNR-0010045 silent 11d on critical-path structural-steel PO 4500000123) + deterministic in-process tools.
- Demo UI (HTML): `demo/index.html` — standalone, offline, labelled **"DEMO — MOCK DATA"**, drives the full analysis → approval loop against the local agent.

## Cleanup checklist
- [x] Unused scaffold code / dead decorators removed (exactly 3 decorators)
- [x] Unused accelerator/cookbook templates removed
- [x] `[illustrative]` snippets removed or wired in
- [x] No secrets in code/markdown; `.env` gitignored
- [x] Mock data + demo UI retained (gated by `IBD_TESTING`)

## Applicable checklist subset
Full custom agent → all pillars L0-1…L0-10 apply; see `agent-outcome-report.md` for every control's flag. Items that require the live BTP tenant (metering L0-4, red-team/bias L0-5, go-live L0-7, drift L0-10) are flagged ⚠️/❌ with remediation owned by the deploying team.

## Dependencies and owners
- SAP API read policy sign-off → Procurement / API policy team.
- BTP entitlements (CF, AI Core, XSUAA, AGW) → BTP admin.
- Live SAP connectivity (gateway/destination) → Basis.
- Thresholds → Procurement CoE (SPA Business Rules).

## Next action
Run the offline verification (README §Verify), then `cf push` from `assets/procurement-bottleneck-agent/` with the AI Core + XSUAA services bound.
