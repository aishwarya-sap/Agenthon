# Code Walkthrough — Project Material Availability & Supply Risk Agent

**For:** handover reviewers / client dev team
**Agent path:** `assets/material-risk-agent/`

---

## Module map

```
app/
├── _boot.py                entry point — maps bound AI Core creds from VCAP_SERVICES, then hands off to main
├── main.py                 A2A Starlette server (a2a-sdk), routes, /whoami, uvicorn
├── agent.py                core agent class, decorators, system prompt, LLM orchestration + fallback chain
├── agent_executor.py       A2A boundary — identity validation, streaming, response shaping
├── auth_ias.py             IAS JWT validation (Joule principal propagation)
├── config.py               mode flags (IBD_TESTING / IBD_LIVE_S4), S4 service profile, auth mode
├── tools.py                15 StructuredTool definitions (mock + live builders)
├── s4_client.py            S/4 OData transport — $top caps, 30s request cache, async executor
├── circuit_breaker.py      per-model circuit breaker for the fallback chain
├── prompt_injection_detector.py   layered tool-result injection defence
├── load_skill_resources.py skill/prompt resource loader
├── util.py                 response trimming + MCP helpers
└── domain/                 deterministic domain core (zero LLM tokens)
    ├── data.py             single data boundary — mock fixtures | live S/4 (async)
    ├── scoring.py          risk bands + chronic-late pattern
    ├── simulation.py       schedule/cost consequence model
    ├── prediction.py       supplier delivery prediction
    ├── recommend.py        role-aware recommendation (alt-sourcing HoD-only)
    ├── memory.py           intervention-outcome memory (HANA Vector interface)
    ├── sanitize.py         RAG injection scan + PII redaction (L0-5.6)
    └── hitl.py             HITL gate — write tools require confirmed=true
```

---

## Request lifecycle

```
User message (POST /)
    │
    ▼
main.py (A2AStarletteApplication)        ← parse JSON-RPC message/send
    │
    ▼
agent_executor.py                         ← identity boundary; stream "working" then final
    │  IBD_TESTING / IBD_LIVE_S4 → "unknown" sub; AGENT_AUTH_MODE=ias → auth_ias
    │
    ▼
agent.py::SampleAgent.stream()
    │
    ├── _invoke_with_fallback()           ← walk model chain, skip circuit-open models
    │   └── LangGraph create_agent (recursion_limit=15, SummarizationMiddleware @30k)
    │
    ├── Tool calls via tool_provider/agw.py::get_mcp_tools()
    │   ├── get_project_material_requirements / parse_excel_project_schedule
    │   ├── get_material_stock_position / get_open_purchase_orders_and_prs
    │   ├── get_consolidation_material_master
    │   ├── compute_material_availability_gaps      ← deterministic core
    │   ├── get_supplier_delivery_history / predict_delivery_outcome
    │   ├── simulate_schedule_consequence           ← deterministic core
    │   ├── retrieve_schedule_and_supplier_context  ← RAG + sanitize (L0-5.6)
    │   ├── recommend_procurement_action            ← role-aware; alt-sourcing HoD-only
    │   └── draft_supplier_expedite_communication
    │
    ├── domain/scoring.py   ← risk band (schedule buffer) + chronic-late elevation
    ├── domain/sanitize.py  ← every RAG chunk: injection strip + PII redact (L0-5.6)
    ├── domain/hitl.py      ← 3 write tools blocked until confirmed=true
    │
    └── brief verdict + table; [SUGGESTIONS] block for the UI's follow-up chips
    │
    ▼
agent_executor.py  ← shape into A2A Task (status.message + artifacts)
    ▼
POST / response (JSON-RPC)
```

---

## Key design decisions

### 1. LLM never computes
All arithmetic — net availability, risk banding, schedule/cost simulation, delivery prediction — is **deterministic Python** in `domain/`, fully unit-testable offline. The LLM orchestrates tool calls and synthesises the final verdict; it relays tool numbers verbatim.

### 2. Three operating modes
`tool_provider/agw.py::get_mcp_tools()` dispatches on env: `IBD_TESTING=1` → in-process mock tools over seeded fixtures; `IBD_LIVE_S4=1` → real OData via `s4_client` (Accelerator Hub sandbox); neither → Agent Gateway MCP discovery (production). Tool names/shapes are identical across all three.

### 3. Context-overflow guards
`s4_client` caps PO and PR reads at `$top=100` (an unfiltered query against a shared sandbox can otherwise return thousands of rows and overflow the context window), caches reads for 30s per `(service, entity, params)`, and runs blocking `httpx` in a thread-pool executor so a slow OData call never stalls the async loop. `recursion_limit=15` bounds the tool loop.

### 4. Advisory-only enforcement
Three layers: system-prompt MANDATORY RULE ("never execute write or delete operations"); `domain/hitl.py` blocks the 3 write tools (`trigger_escalation_workflow`, `write_intervention_outcome_to_memory`, `update_po_delivery_date_or_create_expedite_po`) until `confirmed=true`; no SAP business object is ever written — side effects are limited to the agent's own memory + a notification.

### 5. Resilience
`circuit_breaker.py` opens after 3 consecutive transient model failures (30s cooldown); the ordered fallback chain advances to the next model on retryable errors and propagates non-transient errors immediately.

---

## Where to customise for your engagement

| What to change | File | What to update |
|---|---|---|
| System prompt / rules | `app/agent.py` | `get_system_prompt()` |
| Model + fallback | `app/agent.py` | `get_model_name()` / `get_fallback_model_names()` |
| Risk-band thresholds | `app/domain/scoring.py` | buffer cutoffs + chronic-late rule |
| Tools | `app/tools.py` + `mcp-mock.json` | StructuredTool entries + mock fixture |
| HITL write gate | `app/domain/hitl.py` | gated tool list |
| S/4 service names | `app/config.py` | `cloud` / `onprem` profile maps |
| S/4 base URL + key | `.env` | `S4_BASE_URL`, `S4_API_KEY` |
| CF app name / routes | `manifest.yml` / `mta.yaml` | `name:` + routes |

---

## Running tests

```bash
cd assets/material-risk-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
IBD_TESTING=1 pytest -q            # 175 tests, 73% coverage
```

`conftest.py` forces `IBD_TESTING=1` and `IBD_LIVE_S4=0` so the offline suite always uses mock tools (never a stray `.env`'s live mode). LLM/e2e paths skip unless `AICORE_CLIENT_ID` is set.

## Environment variables (minimum to run locally)

```bash
export IBD_TESTING=1
python app/_boot.py   # starts the A2A server
```

For live S/4 sandbox: `IBD_LIVE_S4=1`, `S4_API_KEY`, `S4_BASE_URL`. For live AI Core: `AICORE_AUTH_URL`, `AICORE_BASE_URL`, `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET` — see `.env.example`.
