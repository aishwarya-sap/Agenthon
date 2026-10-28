# Project Material Availability & Supply Risk Agent

**SAP Joule 2.0 A2A Agent** — Agenthon (Savic + Adarsh, October 2026)

An advisory, read-only supply-risk agent for construction/engineering project procurement. Cross-references project material requirements (Phase 1: Excel schedule; Phase 2: SAP PS) against S/4HANA stock, open POs/PRs and GR history, scores supply gaps, predicts supplier delivery, simulates schedule/cost consequences, and recommends expedite/escalate/alternative-source actions.

All write actions (escalation, memory, PO update) require explicit **human approval** in the chat before executing.

---

## Quick start (local demo — no credentials needed)

```bash
# 1. Python deps (3.14 venv for local test; CF uses 3.11)
python3.14 -m venv /tmp/mr_venv && /tmp/mr_venv/bin/pip install -r requirements.txt

# 2. Start agent on port 5055 (macOS AirPlay holds port 5000)
IBD_TESTING=1 PORT=5055 /tmp/mr_venv/bin/python -m app

# 3. Start Joule-style UI (in another terminal)
cd ../material-risk-ui && npm install && AGENT_URL=http://localhost:5055 npm start

# 4. Open http://localhost:3000
# Try: "Will the materials for the Level 3 Slab Pour be available on time?"
```

## Run tests

```bash
IBD_TESTING=1 /tmp/mr_venv/bin/python -m pytest -q
# Expected: 154 passed, ~80% coverage
```

## Deploy to Cloud Foundry

```bash
# From the repo root (where mta.yaml lives)
mbt build
cf deploy mta_archives/*.mtar --strategy rolling
```

See `../../docs/INTEGRATION_GUIDE.md` for full BTP service setup, Joule integration, and principal propagation steps.

---

## Architecture

- **LLM-orchestrated**: LangChain ReAct + `ChatLiteLLM` (SAP AI Core / Generative AI Hub)
- **Deterministic domain core**: all arithmetic in `app/domain/` (scoring, simulation, prediction) — "LLM never computes"
- **15 tools**: 12 read/compute, 3 HITL-gated write tools
- **Signal tagging**: every tool response carries `signal_status: live | simulated`
- **Mock-first**: `IBD_TESTING=1` runs with seeded data, no SAP or AI Core needed
- **Live sandbox**: `IBD_LIVE_S4=1` wires to Business Accelerator Hub OData APIs
- **Production**: Agent Gateway MCP path (neither flag set)
- **A2A protocol**: v0.3.0, card at `/.well-known/agent.json`

## Key business rules

| Rule | What it does |
|------|-------------|
| Net availability | Unrestricted stock + due PO qty + due PR qty (QI/blocked excluded) |
| Risk bands | CRITICAL (float≤0), HIGH (float 1–3), MEDIUM (float 4–7), LOW (>7) |
| Chronic-late | ≥3 of last 4 GRs late → elevate one risk band |
| HoD-only alt-source | Alternative supplier data visible only to `purchase_hod` role |
| HITL gate | Write tools refuse unless `confirmed=True` after a human approval keyword |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `IBD_TESTING=1` | Demo mode: mock data + mock auth |
| `IBD_LIVE_S4=1` | Functional test: real S/4 OData via sandbox |
| `S4_API_KEY` | Business Accelerator Hub API key |
| `AGENT_AUTH_MODE=ias` | Production: validate IAS JWTs from Joule |
| `AICORE_*` | AI Core creds (from `aicore-creds` user-provided-service on CF) |

See `.env.example` for the full list.

## Production readiness

Governance outcome: **CONDITIONAL GO** — demo/Agenthon ready; 12 items deferred to live BTP tenant.  
Full checklist status: see `agent-outcome-report.md` and `governance/`.

---

*Built on SAP LastMileSupport Joule 2.0 A2A template. SAP BTP — October 2026.*
