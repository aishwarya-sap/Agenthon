# Developer Hand-off — Procurement Bottleneck & Decision Agent

## 1. What this is

An advisory, **read-only** SAP agent for Adarsh Developers' Purchasing team. It detects supplier
silence on critical-path purchase orders, quantifies the delivery/schedule risk, recommends an
action for human approval, and answers free-form questions — every quantitative output carries a
"validate before acting" disclaimer. It never writes to SAP business objects.

- Runtime: Starlette + uvicorn, A2A 0.3.0 (JSON-RPC over `POST /`), Cloud Foundry (`python_buildpack`).
- LLM: SAP AI Core via `langchain_litellm.ChatLiteLLM`, model `sap/anthropic--claude-4.5-sonnet`.
- Data: SAP Business Accelerator Hub sandbox OData (`SAP_MODE=accelerator_hub`) or offline fixtures (`IBD_TESTING=1`).

## 2. Read these first (in order)

1. `docs/specs/design-brief.md` — the problem and who it's for.
2. `docs/specs/functional-specification.md` — what it does.
3. `docs/specs/technical-specification.md` — how it's built (modules, flow, integration).
4. `docs/decisions/` — the ADRs behind the non-obvious choices.
5. `docs/checklists/agent-checklist-L0-L10.md` (v5 checklist) + `docs/agent-checklist-assessment.md` — production-readiness status.

## 3. Run it locally (5 minutes, no SAP needed)

```bash
cd assets/procurement-bottleneck-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
IBD_TESTING=1 pytest            # 134 tests, coverage >= 70%
IBD_TESTING=1 python -m app     # serves on :8080
# http://localhost:8080/ui  (demo UI)   /health   /.well-known/agent.json
```

## 4. What's done vs. pending

- **Done:** full mock-first agent; live BAH OData reads; AI Core LLM reasoning; dashboard + chat;
  HITL approval gate; honest backend-failure handling; intent routing; 134 tests.
- **Pending (tenant-dependent):** live S/4 on Adarsh's Tokyo landscape; IAS principal propagation
  (`AGENT_AUTH_MODE=ias`); turning off `ENABLE_WHOAMI`/`AGENT_AUTH_MODE=none` for production.

## 5. Deploy (Cloud Foundry, us10-001 internal BAI dev)

```bash
cd assets/procurement-bottleneck-agent
cf login --sso
cf push                         # manifest.yml: command `python -m app`, health /health
# secrets via cf set-env (never committed): S4_API_KEY, AICORE_*, IAS_*
```

Current state: running in **mock mode** (`IBD_TESTING=1` set via `cf set-env`) for the demo because
the BAH sandbox API key is quota-locked (resets ~00:00 UTC). AI Core creds remain set, so the LLM
still reasons over the mock data. To return to live data once quota resets: `cf set-env
procurement-bottleneck-agent IBD_TESTING 0 && cf restart procurement-bottleneck-agent`.

## 6. Provenance

Hand-built to the SAP build standard (not copier-generated). Production readiness is tracked
against the authoritative **agent build checklist** :
`docs/checklists/agent-checklist-L0-L10.md` — per-pillar status in `docs/agent-checklist-assessment.md`.
