# Code Walkthrough — Procurement Bottleneck & Decision Agent

**For:** Adarsh Developers dev team / handover reviewers
**Agent path:** `assets/procurement-bottleneck-agent/`

---

## Module map

```
app/
├── __main__.py           entry point — `python -m app`
├── main.py               Starlette server, routes, VCAP_SERVICES mapping
├── agent_card.py         /.well-known/agent.json (A2A discovery)
├── agent.py              core agent class, 3 decorators, system prompt, orchestration
├── agent_executor.py     A2A boundary — JWT validation, response shaping
├── auth_ias.py           IAS JWT validation (Sprint 3+)
├── config.py             all constants, IBD_TESTING flag, AGENT_AUTH_MODE
├── tools.py              13 StructuredTool definitions with ORD IDs
├── mcp_tools.py          get_mcp_tools() — mock | gateway | direct indirection
├── skills.py             3 deterministic skills (critical_path_flag, simulation, recommend)
├── simulation.py         4-dimension consequence model (pure Python, zero LLM tokens)
├── hitl.py               HITL gate — 9 checkpoints, approval keyword matching
├── memory.py             institutional memory (in-memory; HANA Vector interface)
├── project_data.py       SAP PS reader + Excel/CSV Phase-1 adapter
├── resilience.py         error taxonomy, retry/backoff, circuit breaker
├── observability.py      structured logs, OTel spans, correlation ID, PII redaction
└── sanitize.py           prompt-injection detection on RAG chunks (L0-5.6)
```

---

## Request lifecycle

```
User message (POST /)
    │
    ▼
main.py::a2a()               ← parse JSON-RPC
    │
    ▼
agent_executor.py::validate_identity()   ← JWT boundary (never trust client metadata)
    │  IBD_TESTING=1 → "mock-user"
    │  AGENT_AUTH_MODE=none → "dev-bypass" (dev only)
    │  AGENT_AUTH_MODE=ias → auth_ias.validate_ias_token()
    │  AGENT_AUTH_MODE=xsuaa → sap_cloud_sdk.validate_xsuaa_jwt()
    │
    ▼
agent_executor.py::run_turn()
    │
    ▼
agent.py::ProcurementConsequenceAgent.handle()
    │
    ├── _parse_query()             ← extract project_id, PO refs from natural language
    │
    ├── M1–M3 Tool calls (via mcp_tools.py::get_mcp_tools())
    │   ├── get_open_pr_po_chain()
    │   ├── detect_supplier_silence()
    │   ├── get_approval_workflow_status()
    │   └── … (13 tools total)
    │
    ├── skills.py::critical_path_flag()    ← deterministic (AFVV float = 0)
    ├── skills.py::run_consequence_simulation()  ← 4-dimension model
    ├── skills.py::recommend_next_action()       ← decision matrix
    │
    ├── sanitize.py on every RAG chunk          ← prompt-injection gate (L0-5.6)
    │
    ├── hitl.py::check_approval_needed()        ← 9 HITL checkpoints
    │   └── if approval needed → return state="input-required", "Awaiting Approval"
    │
    ├── _summarize_with_llm()               ← LLM call 1 of 2 (verdict synthesis)
    │
    └── _build_report()                     ← fixed 7-section report
            1. Verdict + confidence
            2. Signal Coverage table
            3. SAP Findings
            4. External Evidence (live/simulated labelled)
            5. Simulation Results
            6. Ranked Recommendations (🔴🟡🟢)
            7. Awaiting Approval (if HITL triggered)
    │
    ▼
agent_executor.py::to_a2a_response()    ← shape into A2A artifact
    │
    ▼
POST / response (JSON-RPC)
```

---

## Key design decisions

### 1. Exactly 2 LLM calls per run
The agent is **not** a ReAct loop. The LLM is called exactly twice:
1. `_parse_query()` — intent framing from natural language to structured params
2. `_summarize_with_llm()` — final verdict synthesis from deterministic tool outputs

All 13 tools, the simulation, and the decision matrix are **deterministic Python** — zero LLM tokens, fully unit-testable offline.

### 2. IBD_TESTING flag
`IBD_TESTING=1` activates the mock branch in `mcp_tools.py::get_mcp_tools()`. All 13 tools return fixtures from `mcp-mock.json`. This is how offline tests pass without any network calls. Never set in production.

### 3. Token budget
`config.TOKEN_BUDGET_PER_RUN = 52_000` is a ceiling, not a target. Typical runs use 1,650–4,250 tokens. The ceiling guards against accidental prompt inflation from injected RAG content. Tracked per-run via `observability.py`.

### 4. Advisory-only enforcement
Three layers:
- System prompt MANDATORY RULE 4: "Never execute write, update, or delete operations"
- `hitl.py` blocks both write-capable tools (`write_decision_record`, `trigger_escalation_notification`) until `approve` is received
- `config.APPROVAL_KEYWORDS` is the exhaustive list; anything not in it is treated as not-yet-approved

### 5. Circuit breaker
`resilience.py::CircuitBreaker` opens after `config.CIRCUIT_BREAKER_THRESHOLD = 3` consecutive failures on a tool. An open circuit returns a `DataGap` not an exception — the report marks that dimension as "unavailable" and continues.

---

## Where to customise for your engagement

| What to change | File | What to update |
|---|---|---|
| Agent name | `config.py` | `AGENT_NAME` |
| System prompt rules | `agent.py` | `SYSTEM_PROMPT` — 6 MANDATORY RULES |
| Guardrail thresholds | `config.py` | `SILENCE_TOLERANCE_DAYS`, `MATERIALITY_EXPOSURE_EUR`, etc. |
| Tools | `tools.py` + `mcp-mock.json` | Add/remove StructuredTool entries + matching mock fixture |
| HITL checkpoints | `hitl.py` | `CHECKPOINT_REGISTRY` list |
| Report sections | `agent.py::_build_report()` | Adjust the 7-section Markdown template |
| S/4 OData base URL | `s4_client.py` + `.env` | `S4_BASE_URL`, `S4_API_KEY` |
| CF app name | `manifest.yml` | `name:` field |

---

## Running tests

```bash
cd assets/procurement-bottleneck-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
IBD_TESTING=1 pytest -v                # 111 tests, 92% coverage
IBD_TESTING=1 pytest tests/test_server.py -v    # server surface only
INTEGRATION=1 AGENT_URL=https://... pytest tests/integration/ -v  # live smoke
```

## Environment variables (minimum to run locally)

```bash
export IBD_TESTING=1
export AGENT_AUTH_MODE=none
python -m app  # starts on http://localhost:8080
```

For live AI Core calls, set `AICORE_AUTH_URL`, `AICORE_BASE_URL`, `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET` — see `.env.example`.
