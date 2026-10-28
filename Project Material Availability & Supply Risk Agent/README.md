# Project Material Availability & Supply Risk Agent

> **Agenthon 2026 — Savic × Adarsh Developers**
> Advisory-only A2A agent on SAP BTP. Surfaces material supply gaps that will block scheduled construction activities, predicts supplier delivery outcomes, and recommends the least-cost recovery — with your approval on every action.

---

## Folder structure

```
.
├── assets/
│   ├── material-risk-agent/        ← Python A2A agent (main build)
│   │   ├── app/                    ← agent, tools, domain logic, auth
│   │   ├── tests/                  ← 175 tests, 73% coverage
│   │   ├── governance/             ← 14 governance artifacts
│   │   ├── .env.example            ← all env var names (no secrets)
│   │   └── requirements.txt
│   └── material-risk-ui/           ← Joule-style chat UI (Node/Express)
├── joule/                          ← Joule Studio DAS capability bundle
├── docs/                           ← Integration guide, BTP checklist, flow diagrams
├── governance/                     ← Sprint tracker, L0 checklist
├── default-repo/                   ← Generic SAP agent starter kit (reusable template)
├── manifest.yml                    ← CF deployment (parameterised domain)
├── mta.yaml                        ← MTA deployment descriptor
├── deploy.sh                       ← CF push helper
└── sonar-project.properties
```

---

## What it does

| Capability | Detail |
|---|---|
| Supply gap detection | Cross-references project material requirements vs live stock + open POs/PRs |
| Risk banding | Critical / High / Medium / Low based on schedule buffer days |
| Supplier prediction | Delivery outcome + chronic-late flag (≥3 of last 4 late → band elevated) |
| Schedule simulation | Buffer consumed, cascade slip, cost exposure |
| Recovery recommendation | Least-cost action; alternate sourcing visible to Purchase HoD only |
| Advisory-only | No SAP write operations without explicit human approval (HITL gate) |

---

## Quickstart — mock mode (no SAP credentials needed)

```bash
cd assets/material-risk-agent
cp .env.example .env
pip install -r requirements.txt
IBD_TESTING=1 python app/_boot.py
```

Agent card: `http://localhost:8000/.well-known/agent-card.json`

**Run the UI:**
```bash
cd assets/material-risk-ui
npm install
AGENT_URL=http://localhost:8000 npm start
```
Open `http://localhost:3000`

---

## Run tests

```bash
cd assets/material-risk-agent
IBD_TESTING=1 pytest prebuilt_tests tests -q
# 175 passed, 73% coverage
```

---

## Deploy to Cloud Foundry

```bash
# Stop running agent first (frees CF org memory quota)
cf stop material-risk-agent

# Push agent + UI
cf push

# Restart agent
cf start material-risk-agent
```

Set `CF_APP_DOMAIN` in your shell or replace in `manifest.yml` before pushing.

---

## Environment variables

Copy `assets/material-risk-agent/.env.example` → `.env` and fill in:

| Variable | Purpose |
|---|---|
| `AICORE_AUTH_URL` / `AICORE_BASE_URL` / `AICORE_CLIENT_ID` / `AICORE_CLIENT_SECRET` | SAP AI Core |
| `IBD_TESTING=1` | Mock mode (no live SAP calls) |
| `IBD_LIVE_S4=1` | Direct OData via Accelerator Hub sandbox |
| `S4_API_KEY` / `S4_BASE_URL` | S/4HANA sandbox credentials |
| `AGENT_AUTH_MODE=ias` | Enable IAS JWT validation (Joule principal propagation) |

---

## Key docs

- [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md) — module map + request lifecycle
- [REQUIREMENTS.md](REQUIREMENTS.md) — scope, APIs, acceptance criteria
- [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) — CF deploy + Joule registration + principal propagation steps
- [governance/sprint_tracker.md] — sprint-by-sprint progress

---

## Architecture

```
User (Joule / Chat UI)
        │  A2A JSON-RPC
        ▼
main.py  (Starlette + A2A SDK)
        │
agent_executor.py  ←  IAS JWT validation (auth_ias.py)
        │
agent.py  (LangChain create_agent + ChatLiteLLM, recursion_limit=15)
        │
   15 tools via mcp_providers/agw.py
   ├── IBD_TESTING=1   → in-process mock (Tower Alpha fixtures)
   ├── IBD_LIVE_S4=1   → direct OData (Accelerator Hub sandbox)
   └── production      → Agent Gateway MCP discovery
        │
domain/  (deterministic Python — LLM never computes numbers)
   scoring · simulation · prediction · recommend · hitl · sanitize
        │
S/4HANA OData  (s4_client.py — $top=100 cap, 30s cache, async executor)
```

---

## Security

- Secrets via `.env` (gitignored) or `VCAP_SERVICES` — never committed
- Advisory-only: no POST/PATCH/DELETE to SAP business objects
- HITL gate: 3 write tools blocked until `confirmed=true`
- RAG injection scan + PII redaction on every vector chunk
- Circuit breaker: 3 failures / 30s cooldown
