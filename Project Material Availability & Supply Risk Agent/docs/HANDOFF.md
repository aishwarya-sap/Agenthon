# Developer Hand-off — Project Material Availability & Supply Risk Agent

**Repo:** `https://github.tools.sap/GDH-Data-AI-Architecture-APAC/Savic-Adarsh-Developers-Agenthon` · branch `main`
**Status:** Build complete — specs written, agent deployed to CF (us10) and healthy, 175 tests green (73% coverage), quality gate PASS, code review PASS. Joule registration + principal-propagation end-to-end test pending (tenant-side config). HANA-backed memory pending.
**Checklist tracker:** https://agentchecklist.cfapps.us10-001.hana.ondemand.com/

---

## 1. What this is

An advisory AI agent for the **Purchase Executive / Purchase Manager / Purchase HoD / Project Manager** personas on a construction project. It surfaces material supply gaps that will block scheduled activities, predicts supplier delivery, simulates schedule/cost consequence, and recommends the least-cost recovery — with every data-changing action (escalation, memory write, expedite-PO proposal) behind a human-in-the-loop (HITL) confirmation gate. Built on SAP BTP with LangChain + LangGraph + the a2a-sdk, surfaced through SAP Joule and a standalone chat UI.

**Architecture:** Single LLM-orchestrated agent (ReAct tool loop, `recursion_limit=15`) over a deterministic domain core — the LLM orchestrates and narrates; it never computes numbers.

| Component | Responsibility | Backend |
|-----------|----------------|---------|
| `agent.py` | System prompt, LLM orchestration, fallback chain, circuit breaker | AI Core (ChatLiteLLM) |
| `tools.py` (15 tools) | 12 read/compute + 3 HITL-gated write | S/4 OData / mock / RAG |
| `domain/` | scoring · simulation · prediction · recommend · sanitize · hitl · memory (deterministic) | — |
| `s4_client.py` | OData transport ($top cap, 30s cache, async executor, onprem PP) | S/4HANA |
| `auth_ias.py` | IAS JWT validation (Joule principal propagation) | IAS |

**Retrieval = Hybrid:** structured OData reads (authoritative transactional data) + standalone vector RAG (HANA Cloud Vector) over supplier emails / scorecards / schedules. No knowledge graph in scope.

Design decisions: LangChain/LangGraph · Single agent · Advisory-only + HITL · Hybrid OData+RAG · S/4HANA OData (cloud sandbox APIKey / on-prem Destination+PP) · deploy to Cloud Foundry (us10 demo, Tokyo prod) · LLM via SAP AI Core (`sap/anthropic--claude-4.5-sonnet`). Full rationale in `docs/specs/design-brief.md` and `docs/decisions/`.

---

## 2. Read these first (in order)

| Document | What it gives you |
|----------|-------------------|
| `docs/specs/functional-specification.md` | Requirements, scope, guardrails, acceptance criteria, open issues |
| `docs/specs/design-brief.md` | Confirmed design decisions (D0–D12) |
| `docs/specs/technical-specification.md` | As-built design: components, data model, real S/4 OData services + entities, security, deployment |
| `docs/specs/rtm.md` | Requirements → implementation → test traceability (100%) |
| `docs/checklists/agent-checklist-L0-L10.md` | GDH APAC Agent Checklist v5 (10-pillar / 60-item) |
| `docs/agent-checklist-assessment.md` | Per-pillar readiness status for this agent |
| `CODE_WALKTHROUGH.md` | Module map + request lifecycle |

---

## 3. Run it locally (mock mode, no SAP needed)

Requires Python ≥ 3.11.

```bash
cd assets/material-risk-agent
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
IBD_TESTING=1 python app/_boot.py       # starts the A2A server
```

Fetch the AgentCard:

```bash
curl http://localhost:5000/.well-known/agent-card.json
```

Run the tests:

```bash
IBD_TESTING=1 pytest prebuilt_tests tests -q   # 175 passed, 73% coverage
```

Standalone chat UI:

```bash
cd assets/material-risk-ui && npm install && AGENT_URL=http://localhost:5000 npm start
# open http://localhost:3000
```

---

## 4. What's done vs. pending

**Done:**
- Full spec set (FS, TS, RTM 100%) under `docs/specs/`.
- Agent code: 15 tools, deterministic domain core, HITL gate, RAG injection/PII sanitize, circuit breaker, live-first fallback.
- Deployed to CF us10 (`material-risk-agent` + `material-risk-ui`), both `1/1 running`, agent-card 200.
- Quality gate PASS; code review PASS; 175 tests green, 73% coverage.

**Pending (needs live BTP / tenant / human):**
1. **Joule registration** — bundle authored under `joule/`; blocked on IAS App2App trust (`Cli2Joule`) in the Adarsh IAS tenant.
2. **Principal propagation end-to-end test** — coded (`auth_ias.py` + `s4_client` onprem profile), unexercised against real on-prem S/4; needs Destination (PrincipalPropagation) + Cloud Connector (`vhdvladvci:44300`, client 100) + IAS user→S/4 mapping.
3. **HANA-backed memory** — `domain/memory.py` is in-process append-only; needs a HANA Cloud table + vector recall.
4. **Tenant-only governance** — model benchmarking, live RagEval, Responsible AI evaluation, release gates, live drift monitors.

---

## 5. Deploy (Cloud Foundry, us10)

```bash
# From the agent directory (NOT the repo root — root manifest diff currently 500s on CF):
cd assets/material-risk-agent
cf stop material-risk-agent        # free the 1 GB quota before push
cf push material-risk-agent
cf push material-risk-ui

# Verify
curl https://material-risk-agent.cfapps.us10-001.hana.ondemand.com/.well-known/agent-card.json
```

Keep both `IBD_LIVE_S4=1` and `IBD_TESTING=1` set so the live-first fallback serves seeded data if the shared sandbox is down.

---

## 6. Provenance

Hand-built on the SAP Agent Golden Path A2A template (mock-first), aligned to the GDH AI Factory documentation standard (QG/CR checklists, `docs/specs/` layout). Kept the `app/` package layout and `python app/_boot.py` start (no `src/`/gunicorn migration) per engagement decision.
