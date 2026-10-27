# SAP A2A Agent Starter Kit

> Generic scaffold for building SAP Joule-ready A2A agents on SAP BTP Cloud Foundry.  
> Built and maintained by the BAI AI Factory team.

---

## What is this?

A production-grade starting point for any SAP agent engagement. Clone once, rename, fill in your domain logic. The scaffold includes:

- A2A 0.3.0 conformant server (`kind: "task"` response, multi-turn context)
- Joule BYOA capability bundle (schema 3.28.0 / 1.4.0, `namespace: joule.ext`)
- JWT validation at the A2A boundary (`AGENT_AUTH_MODE`: `ias` / `xsuaa` / `none`)
- IBD_TESTING flag — full offline mock mode, no SAP credentials needed
- Smoke tests with ≥ 70% coverage gate enforced by `pytest.ini`
- SonarQube config, CF manifest, Procfile, xs-security.json, asset.yaml
- CI/CD template (`.github/workflows/ci.yml.example`)

> **Every decision in this kit is grounded.** See [`DESIGN_RATIONALE.md`](DESIGN_RATIONALE.md)
> for why each file and convention exists, traced to the SAP Agent cookbook, the A2A spec,
> or a lesson learned on a real deployment. Read it before removing or replacing anything.

---

## Quick start — rename and run offline (5 minutes)

```bash
# 1. Rename everything in one command
chmod +x rename.sh
./rename.sh <your-agent-name>
# e.g. ./rename.sh material-risk-agent

# 2. Install and test offline
cd assets/<your-agent-name>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
IBD_TESTING=1 pytest tests/ -v

# 3. Run locally
IBD_TESTING=1 python -m app
# → http://localhost:8080/.well-known/agent.json  (agent card)
# → POST http://localhost:8080/                    (A2A message/send)
# → http://localhost:8080/health                   (liveness)
```

---

## Repository structure

```
default-repo/
├── README.md                          ← this file
├── CLAUDE.md                          ← self-contained SAP standards + governance (no external repo needed)
├── DESIGN_RATIONALE.md                ← why every file/convention exists (read before deleting anything)
├── AGENT_CHECKLIST.md                 ← L0–L10 governance checklist (fill per engagement)
├── solution.yaml                      ← deploy descriptor — makes assets/ a deployable solution
├── CB_README.md                       ← client brief template
├── REQUIREMENTS.md                    ← scope/API/acceptance template (§6.2)
├── implementation-plan.md             ← phased build plan template (§6.3)
├── CODE_WALKTHROUGH.md                ← dev-team handover template (§6.4)
├── agent-outcome-report.md            ← L0–L10 evidence template (§6.5)
├── doc-insights-accelerator.md        ← reusable discoveries template (§6.6)
├── rename.sh                          ← one-command rename script
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml.example             ← copy to ci.yml and configure
└── assets/
    └── agent-starter-kit/             ← rename via ./rename.sh <your-agent-name>
        ├── app/
        │   ├── __main__.py            ← entry point: A2AStarletteApplication + VCAP_APPLICATION URL
        │   ├── agent.py               ← LangGraph create_react_agent + get_llm() + ResponseFormat
        │   ├── agent_card.py          ← AgentCard from a2a.types (/.well-known/agent.json)
        │   ├── agent_executor.py      ← AgentExecutor bridge: a2a-sdk ↔ StarterKitAgent
        │   ├── config.py              ← all thresholds as named constants
        │   └── tools.py               ← @tool functions (echo_tool + get_sap_data placeholder)
        ├── joule/
        │   ├── da.sapdas.yaml                    ← schema 1.4.0, capability bundle root
        │   └── agent-starter-kit-capability/
        │       ├── capability.sapdas.yaml        ← schema 3.28.0, namespace: joule.ext
        │       ├── capability_context.yaml       ← contextId/taskId (mandatory — missing = deploy error)
        │       ├── functions/call_agent.yaml     ← multi-turn A2A function
        │       └── scenarios/invoke_agent.yaml   ← intent-matching + context persistence
        ├── tests/
        │   └── test_smoke.py          ← 6 offline smoke tests (health, agent card, A2A Task shape, tools)
        ├── .cfignore                  ← keeps CF push lean (no .venv, tests/, __pycache__)
        ├── .env.example               ← all required variables documented, zero secrets
        ├── .gitignore                 ← blocks .env, .coverage, .pytest_cache, __pycache__
        ├── asset.yaml                 ← ORD asset descriptor (asset.sap/v1)
        ├── conftest.py                ← auto-sets IBD_TESTING=1 for all tests
        ├── manifest.yml               ← CF: 512M→1G, python_buildpack, health=/.well-known/agent.json
        ├── mcp-mock.json              ← offline tool fixtures (echo_tool + get_metadata)
        ├── Procfile                   ← CF start command fallback
        ├── pytest.ini                 ← --cov=app --cov-fail-under=70
        ├── requirements.txt           ← core deps + commented Sprint 2+ deps
        ├── requirements-test.txt      ← pytest, pytest-asyncio, pytest-cov, httpx
        ├── runtime.txt                ← python-3.10.x (3.11/3.12 also supported)
        ├── sonar-project.properties   ← SonarQube template with quality gate
        └── xs-security.json           ← XSUAA scopes, roles, redirect-uri placeholder
```

---

## What to fill in per engagement

| File | What to change |
|---|---|
| `rename.sh` | Run `./rename.sh <your-agent-name>` first — handles everything below automatically |
| `manifest.yml` | `AGENT_PUBLIC_URL`, scale memory to 1G for production |
| `app/agent.py` | System prompt 6 rules, `SYSTEM_INSTRUCTION` |
| `app/agent_card.py` | Agent name, description, skill id, example utterances |
| `app/tools.py` | Live `@tool` functions calling Agent Gateway / S/4HANA OData |
| `mcp-mock.json` | Mock responses (keyed by ORD ID) matching your live tools |
| `xs-security.json` | `xsappname`, role names, redirect URI with real CF URL |
| `asset.yaml` | All `[TODO]` placeholders |
| `sonar-project.properties` | `projectKey`, `projectName` |
| `joule/` | `system_alias` (must match BTP destination name), scenario description, progress text |
| `AGENT_CHECKLIST.md` | Fill ✅/⚠️/❌/⏭️ for each L0–L10 item |
| `.github/workflows/ci.yml.example` | Copy to `ci.yml`, set `SONAR_TOKEN` secret |

---

## Deploy to Cloud Foundry

```bash
cd assets/<your-agent-name>

# 1. Copy and fill in your credentials
cp .env.example .env   # fill in AICORE_*, IAS_*, AGENT_PUBLIC_URL

# 2. Push (secrets via cf set-env, never in manifest.yml)
cf login --sso
cf push

# 3. Verify
curl https://<your-agent-name>.cfapps.<region>.hana.ondemand.com/.well-known/agent.json
```

---

## Deploy Joule capability bundle (Sprint 3)

```bash
cd assets/<your-agent-name>/joule

# Prerequisites:
# - npm install -g @sap/joule-studio-cli
# - IAS App2App Cli2Joule dependency configured in your IAS tenant
# - BTP Destination created matching system_alias in capability.sapdas.yaml

joule login --subdomain <your-subaccount-subdomain>
joule deploy ./da.sapdas.yaml --compile -n "<capability-name>"
joule list capabilities | grep <your-agent-name>
```

> **Note:** `joule login` will fail with `AUTH_FETCH_TOKEN_FAILED` until the IAS admin configures the `Cli2Joule` App2App dependency. This is an IAS admin action — not a code issue.

---

## Sprint delivery gates

| Sprint | Goal | Gate |
|---|---|---|
| Sprint 1 | CF app live (mock data), client git access confirmed | Agent card 200, mock A2A turn works, all tests pass |
| Sprint 2 | Live S/4HANA data | End-to-end report from real data, functional SPOC sign-off |
| Sprint 3 | Joule + IAS security + SonarQube | Joule round-trip works, no SonarQube blockers, token budget confirmed |
| Sprint 4 | Production handover | Production URL live, client sign-off, governance docs delivered |

---

## Key environment variables

| Variable | Dev default | Production |
|---|---|---|
| `IBD_TESTING` | `1` (mock) | `0` |
| `AGENT_AUTH_MODE` | `none` | `ias` |
| `AGENT_PUBLIC_URL` | `http://localhost:8080` | CF app URL |
| `AICORE_SERVICE_KEY` | — | From AI Core service binding (VCAP_SERVICES in CF) |
| `AGENT_MODEL` | `sap/anthropic--claude-4-5-sonnet` | Same or override |
| `AICORE_RESOURCE_GROUP` | `default` | Your AI Core resource group |
| `IAS_ISSUER` | — | Your IAS tenant URL |

> See `.env.example` for the complete list with descriptions.
