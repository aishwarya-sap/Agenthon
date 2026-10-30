# Critical-Path Procurement Consequence Agent

Advisory, **read-only** SAP agent for the Purchasing Head of Department. It detects
supplier silence on critical-path purchase orders across active projects, quantifies
the downstream consequence (schedule slip · idle-resource cost · milestone-penalty
exposure · emergency-sourcing premium), recalls similar past decisions, and presents
a ranked, evidence-backed recommendation (**escalate / source-switch / absorb**) for
human approval — every outcome captured as institutional memory.

Built to the SAP Agent Golden Path (A2A, SAP AI Core, Cloud Foundry). **The agent
never writes SAP business objects.** Its only side effects — after explicit human
approval — are appending a decision record to its own institutional memory and
raising an SAP Build Process Automation notification.

- Idea / design: `../Design-Procurement Bottleneck & Decision Agent.pdf`
- PRD: `assets/procurement-bottleneck-agent/specification/procurement-bottleneck-agent/specification.md`

## Layout
```
solution.yaml
assets/procurement-bottleneck-agent/
  app/            15 modules — orchestration, 13 tools, 3 skills, simulation, memory, HITL, resilience, observability
  demo/index.html standalone mock-mode demo UI ("DEMO — MOCK DATA")
  tests/          72 tests (unit + integration + server), coverage 91.6%
  mcp-mock.json   deterministic offline fixtures (seed: supplier silent on critical-path steel)
  asset.yaml · manifest.yml · xs-security.json · .env.example
```

## Run & verify (offline, no SAP / no credentials)
```bash
cd "assets/procurement-bottleneck-agent"
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt      # or just requirements-test.txt for the suite

# 1) Tests — must pass, coverage ≥ 70%, writes test_report.json
IBD_TESTING=1 pytest

# 2) Run the agent locally (mock mode) and check the A2A agent card
IBD_TESTING=1 PORT=8080 python -m app &
curl -s http://localhost:8080/.well-known/agent.json | python3 -m json.tool

# 3) Drive one analysis + approval turn
curl -s -X POST http://localhost:8080/ -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","method":"message/send","id":"1","params":{"message":{
    "messageId":"m1","contextId":"c1","role":"user",
    "parts":[{"kind":"text","text":"Run the critical-path procurement analysis for project P-INFRA-07"}],
    "metadata":{"mock":true}}}}'
# → full 7-section report, status "input-required" (halts at Awaiting Approval)
# reply "approve LIFNR-0010099" on the same contextId to execute (advisory) write + escalation
```
Open `demo/index.html` in a browser (agent running as above) for a click-through demo.

## Deploy to Cloud Foundry (you run this)
Secrets are never in the repo. Bind the AI Core service key from your secure credentials store at push time.
```bash
cd "assets/procurement-bottleneck-agent"
cf login -a https://api.cf.<your-region>.hana.ondemand.com --sso   # always --sso

# Services (names match manifest.yml)
cf create-service aicore <plan> procurement-agent-aicore
cf create-service xsuaa application procurement-agent-xsuaa -c xs-security.json

# Provide model creds (either bind the AI Core instance above, or set-env from the creds file)
cf set-env procurement-bottleneck-agent AICORE_CLIENT_ID     "<clientid>"
cf set-env procurement-bottleneck-agent AICORE_CLIENT_SECRET "<clientsecret>"
cf set-env procurement-bottleneck-agent AICORE_AUTH_URL      "<url>"
cf set-env procurement-bottleneck-agent AICORE_BASE_URL      "<serviceurls.AI_API_URL>"

# Production uses live SAP data — unset mock:
cf unset-env procurement-bottleneck-agent IBD_TESTING

cf push
curl https://procurement-bottleneck-agent.cfapps.<your-region>.hana.ondemand.com/.well-known/agent.json
```
Then register the agent-card URL in Joule (admin UI or `joule deploy`). See
`docs/checklists/agent-checklist-L0-L10.md` §4 for the go-live gates still required (Agent-Builder
exception review, model benchmarking, RAG-triad, safety/red-team, cross-functional
sign-off, drift/ops monitoring).

## Connectivity & modes
`SAP_MODE=gateway` (Agent Gateway, preferred) · `cloud` / `onprem` (Destination +
Connectivity). `IBD_TESTING=1` forces offline mock everywhere and always wins.
Project data: `PROJECT_DATA_SOURCE=SAP_PS` (Phase 2) or `EXCEL` (Phase 1 upload;
set `PROJECT_DATA_EXCEL_PATH`). All environment variables: see `.env.example`.

## Guardrails (enforced)
Advisory-only (no POST/PATCH/DELETE, no `BAPI_PO_CREATE1`) · `top=100` on reads ·
never fabricate · live/simulated labelling + RAG similarity gate ≥ 0.82 ·
financial disclaimer on every quantitative output · JWT validated at the A2A
boundary (skipped only under `IBD_TESTING=1`) · PII redaction in logs · HITL
approval + 9 checkpoints before any side effect.
