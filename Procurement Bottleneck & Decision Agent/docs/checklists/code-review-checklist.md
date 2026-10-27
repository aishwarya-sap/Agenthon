# Python Agent Code Review Checklist

> Deep code review for Python agent projects. 4 reviewer domains, 115 checks, parallel sub-agent model.
> Used by `/gdhaifactory-agentic-pipeline:agent-code-review` (standalone) and scaffold STATE 10.

## Overview

Code Review runs **after** Quality Gate passes. It applies deep architectural and pattern analysis beyond what deterministic checks can catch.

**Architecture:** 4 independent reviewer sub-agents run IN PARALLEL. Each reads assigned project files and applies its checklist. Results merge into severity-ranked findings table.

**Severity levels:**
- **Critical** — Architectural violation or security flaw. Must fix.
- **Major** — Pattern deviation or significant quality issue. Should fix.
- **Minor** — Improvement opportunity. Optional.

**Pass criteria:**
- **PASS**: 0 Critical, <=8 Major
- **CONDITIONAL**: 0 Critical, 9-15 Major (warn, flag TODOs)
- **FAIL**: any Critical OR >15 Major

**Finding format:**
```
| ID | Severity | File:Line | Finding | Fix |
```

**Execution model:**
1. **Deterministic pre-pass** (`code_review_checklist.py`) — ~46 checks via AST/regex (fast, seconds)
2. **LLM sub-agents** (4 parallel) — ~54 remaining checks requiring code comprehension (slower, minutes)
3. **Merge** — deduplicate, severity-rank, compile report

---

## Reviewer 1: Architecture Reviewer (CR-AR)

**Scope:** D1 pattern adherence, graph topology, node wiring, sub-agent responsibilities, dependency injection, state management.

**Files to read:** `orchestration/orchestrator.py`, `orchestration/state.py`, `orchestration/hitl/*.py`, `agents/*.py`, `runtime/agent_executor.py`, `platform/data_client/base.py`, `platform/data_client/*.py`

| ID | Check | Severity | Auto | Detail |
|----|-------|----------|------|--------|
| CR-AR-01 | D1 pattern adherence: node count and topology match chosen pattern spec (Single-Agent=1 node, Coordinator=supervisor+N specialists, Sequential=N linear, Parallel=fan-out+synthesizer) | Critical | LLM | Compare graph structure to D1 spec |
| CR-AR-02 | Sub-agent responsibilities clearly separated — no two agents handle same capability/domain | Major | LLM | Read agent factory functions |
| CR-AR-03 | State graph has no unreachable nodes (every node has at least one incoming edge or is START) | Critical | Script | AST: parse add_node/add_edge calls |
| CR-AR-04 | State graph has no infinite loops without exit condition (every cycle has conditional edge that can break out) | Critical | LLM | Trace graph cycles |
| CR-AR-05 | All conditional edges have defined routing functions and cover all possible return values | Major | LLM | Read routing functions |
| CR-AR-06 | Router node exists if D4=hybrid or D4=intent-LLM | Major | Script | Grep for router node |
| CR-AR-07 | No router node if D4=code-controlled or D4=none or D1=Single-Agent | Major | Script | Grep absence check |
| CR-AR-08 | FAST_ROUTES regex dictionary defined if D4=hybrid (pre-LLM classification) | Major | Script | Grep for FAST_ROUTES |
| CR-AR-09 | Every node function is imported and registered in graph via `graph.add_node()` | Critical | Script | AST: match add_node args to imports |
| CR-AR-10 | State schema (`AgentState` TypedDict) includes all fields that nodes read and write | Critical | LLM | Compare state fields to node access patterns |
| CR-AR-11 | DataClient ABC: concrete class implements all 5 methods (`get`, `list`, `create`, `update`, `delete`) with matching parameter names from `base.py` | Major | Script | AST: compare method signatures |
| CR-AR-12 | Constructor alignment: `_build_data_client()` in `agent_executor.py` constructs client with kwargs that match the concrete client's `__init__` signature | Major | Script | AST: compare kwargs |
| CR-AR-13 | Dependency injection: no global mutable state; closures, `Runtime[T]`, or `context_schema` used for per-request dependencies | Major | LLM | Scan for module-level mutable variables |
| CR-AR-14 | HITL layer present if D2=Yes: action guard or hitl_gate node exists with 3-layer defense (whitelist → policy → human). If D10≠none, hitl_gate replaces action_guard. | Critical | LLM | Read action guard / hitl_gate node |
| CR-AR-15 | Memory/session: `SessionStore` or equivalent used if D5 != stateless; history injected into agent context | Major | Script | Grep for SessionStore import |
| CR-AR-16 | Error handler node present for multi-agent patterns (Coordinator, Hierarchical, Parallel) — converts internal errors to user-facing messages | Major | LLM | Check for error handling node |
| CR-AR-17 | Checkpointer (`InMemorySaver`) configured in `graph.compile()` for patterns that maintain state across turns | Major | Script | Grep for InMemorySaver |
| CR-AR-18 | Agent creation uses `from langchain.agents import create_agent` with `system_prompt=` parameter (LangGraph) | Critical | Script | Import scan |
| CR-AR-19 | Tool functions use `@tool` decorator from `langchain_core.tools` (not raw functions passed to agent) | Major | Script | AST: check decorator |
| CR-AR-20 | Design rationale documented: architecture.md or ADR explains WHY this pattern was chosen over alternatives | Minor | LLM | Read docs/architecture.md |
| CR-AR-21 | If D8=mcp-multi: MCPMultiClient uses lazy connection pattern — connects on first tool use, not at startup | Major | `[LLM]` Read mcp/client.py |
| CR-AR-22 | If D8=mcp-multi: Tool namespacing uses double-underscore `{server}__{tool}` convention (valid Python identifiers) | Major | `[Script]` Grep for `__` in tool name construction |
| CR-AR-23 | If D9=registry: DelegationClient passes `context_id` to all remote agent calls (contextId propagation for multi-turn) | Critical | `[LLM]` Read a2a_client/delegation_client.py |
| CR-AR-24 | If D9≠none: A2A delegation tools follow `delegate_to_{name}` naming convention | Major | `[Script]` Grep for `delegate_to_` pattern in tool_factory.py |
| CR-AR-25 | If D10≠none: `hitl_gate` node positioned correctly — after specialist nodes, before synthesizer; has incoming edges from HITL-raising nodes | Critical | `[LLM]` Read orchestrator.py, trace graph edges |
| CR-AR-26 | If D10≠none: Specialist nodes raise HITL by returning `hitl_request` in state dict (not by calling `interrupt()` or A2A methods directly — that's hitl_gate's job) | Major | `[LLM]` Read all node implementations |
| CR-AR-27 | If D10 includes `info_request`: Info request payloads include `fields` array with `name`, `label`, `type`, `required` per field; sensitive fields marked `sensitive: True` | Major | `[LLM]` Read nodes raising info_request |
| CR-AR-28 | If D6=odata-s4-oauth2 or odata-s4-basic: S4HanaClient instantiated once (not per-request) in `agent_executor.py`; shared across tool calls via closure injection | Major | `[LLM]` Read agent_executor.py for S4HanaClient instantiation pattern |
| CR-AR-29 | If D6=odata-s4-oauth2 or odata-s4-basic: Error handling on S/4HANA calls differentiates `404` (not found — return None) from `401/403` (config error — alert ops) from `500` (S/4HANA fault — log + raise) | Major | `[LLM]` Read tools/s4_tools.py or data_client/s4hana_client.py |
| CR-AR-30 | If framework=LangGraph AND agent uses `create_agent`: cross-cutting concerns (guardrails, retry, HITL) implemented as `middleware=[...]`, not duplicated inline in every node | Major | `[LLM]` Read agent factory / build_graph for middleware usage |
| CR-AR-31 | If framework=LangGraph: middleware ordering is deliberate — cheapest-blocking guards (call limits) first, HITL last; no redundant double-layering of graph-level `interrupt()` AND `HumanInTheLoopMiddleware` for the same tool | Major | `[LLM]` Read middleware list order + graph HITL nodes |
| CR-AR-32 | If framework=LangGraph AND agent is resumable: `durability` mode is deliberate (`"async"`/`"sync"` for HITL/long-running, `"exit"` only for throughput-first non-resumable runs) and documented | Minor | `[LLM]` Read invoke/stream calls + architecture.md |

---

## Reviewer 2: Security Reviewer (CR-SR)

**Scope:** OWASP AI Top 10, credential management, authentication, authorization, injection prevention, data privacy.

**Files to read:** `config.py`, `main.py`, `middleware/*.py`, `tools/*.py`, `agents/*.py`, `prompts/system/*.txt`, `.env.example`, `.gitignore`, `xs-security.json` (if exists)

| ID | Check | Severity | Auto | Detail |
|----|-------|----------|------|--------|
| CR-SR-01 | No hardcoded credentials in source: API keys, passwords, tokens, service keys (regex: patterns like `password\s*=\s*["'][^"']+["']`, `api_key\s*=\s*["']`) | Critical | Script | Regex scan all .py files |
| CR-SR-02 | All secrets loaded from environment variables via `config.py` (Settings class), not from files or inline | Critical | Script | Verify Settings fields for known secrets |
| CR-SR-03 | Authentication middleware present: `XSUAAJWTMiddleware` (CF) or IAS/OAuth middleware (AppFND) in `main.py` | Critical | Script | Import scan |
| CR-SR-04 | Authorization scopes checked on mutation operations: tools that write/approve/delete verify user has required scope | Critical | LLM | Read tools with write operations |
| CR-SR-05 | Input length validation before LLM calls: user message checked for max length to prevent token-budget attacks | Major | Script | Regex for length check patterns |
| CR-SR-06 | System prompt boundary: user input never directly concatenated into system prompt string; uses separate `HumanMessage` | Critical | LLM | Read prompt construction |
| CR-SR-07 | Tool output sanitized before returning to user: no raw stack traces, internal paths, or service credentials in error messages | Major | LLM | Read tool error handling |
| CR-SR-08 | No `eval()`, `exec()`, `__import__()` in any source file (code injection vectors) | Critical | Script | Regex scan |
| CR-SR-09 | No `pickle.loads()` or `pickle.load()` on untrusted data (deserialization attack) | Critical | Script | Regex scan |
| CR-SR-10 | PII not logged at INFO/WARNING level: no user names, emails, phone numbers in structured log `msg` field | Major | LLM | Read logging calls |
| CR-SR-11 | CORS restricted to known origins (not `allow_origins=["*"]` in production middleware config) | Major | Script | Regex for CORS config |
| CR-SR-12 | TLS enforced: all external API calls use `https://` URLs; no `verify=False` in httpx/requests calls | Major | Script | Regex scan |
| CR-SR-13 | Rate limiting configured or documented as TODO with timeline | Minor | LLM | Check middleware + docs |
| CR-SR-14 | Session isolation: no cross-user state leakage; `InMemorySaver` keyed by `context_id` or `task_id` (not shared global state) | Critical | LLM | Read checkpointer usage |
| CR-SR-15 | Cloud Connector proxy used for on-premise backend calls (if S/4HANA destination configured) | Major | LLM | Check data client construction |
| CR-SR-16 | CSRF token handling for OData v2 backends: fetch token via HEAD + `X-CSRF-Token: Fetch`, send on mutations | Major | Script | Grep for csrf/CSRF in data_client |
| CR-SR-17 | No `debug=True` or `AGENT_DEBUG=true` as default in config.py; debug must default to False | Major | Script | Regex in config.py |
| CR-SR-18 | `.gitignore` excludes `.env`, `.env.local`, `*.key`, `*.pem`, `service-key*.json`, `VCAP_SERVICES.json` | Critical | Script | File content check |
| CR-SR-19 | Audit logging for mutation operations if SOX/GDPR flagged: mutations emit structured log event with actor, action, resource, result | Major | LLM | Read mutation tools + logging |
| CR-SR-20 | Dependencies: no known malicious or typosquatted packages in pyproject.toml (check against common attack patterns) | Critical | Script | Package name validation |
| CR-SR-21 | If D10 includes `info_request`: Fields marked `sensitive: True` (passwords, API keys) NOT logged to `hitl_history` or structured logs; sensitive data cleared from state after HITL resolution | Critical | `[LLM]` Read info_request payloads + hitl_gate state cleanup |
| CR-SR-22 | If D6=odata-s4-oauth2 or odata-s4-basic: No S/4HANA credentials (client_id, client_secret, username, password) hardcoded in any Python source file | Critical | Script | Regex scan src/ for credential patterns near `s4hana\|S4HANA\|communication_user` |
| CR-SR-23 | If D6=odata-s4-oauth2 or odata-s4-basic: No S/4HANA tenant URL (`.s4hana.ondemand.com`) hardcoded anywhere in src/ — must be resolved via Destination Service at runtime | Critical | Script | Regex scan src/ for `.s4hana.ondemand.com` |
| CR-SR-24 | If D6=odata-s4-oauth2 or odata-s4-basic: Communication User is a dedicated service account — no evidence of personal user credentials (e.g. P/S-user IDs that look like personal accounts) | Major | LLM | Scan config comments, docs, .env.example for comm user naming |
| CR-SR-25 | If D6=odata-s4-oauth2 or odata-s4-basic: S4HanaClient wrapped in a tool function before being called by graph nodes — not called directly inside node functions | Major | LLM | Read orchestrator.py / nodes/*.py for direct S4HanaClient calls |
| CR-SR-26 | If framework=LangGraph AND agent handles PII / SAP business data: `PIIMiddleware` (or equivalent redaction) applied with `apply_to_tool_results=True` so PII returned from S/4HANA tools is scrubbed | Critical | `[LLM]` Read middleware config + tool return paths |
| CR-SR-27 | If framework=LangGraph: content moderation does NOT send SAP customer data to a non-SAP endpoint (no raw `OpenAIModerationMiddleware` in production — routed via SAP AI Core / SAP-approved service) | Critical | `[LLM]` Read middleware imports + config |
| CR-SR-28 | If framework=LangGraph: prompt-injection defense present — `wrap_model_call` re-asserts system policy OR system prompt has explicit boundary instruction; tool-result content treated as untrusted data | Major | `[LLM]` Read middleware + prompt files |
| CR-SR-29 | If framework=LangGraph AND side-effect tools present: write/approve tools capped by `ToolCallLimitMiddleware` (or equivalent) to prevent runaway side effects | Major | `[Script]` Grep for ToolCallLimitMiddleware or manual cap |

---

## Reviewer 3: A2A Compliance Reviewer (CR-A2)

**Scope:** A2A protocol adherence, AgentCard correctness, streaming, task lifecycle, Joule integration.

**Files to read:** `main.py`, `agent_executor.py`, `agent_card.py`, `config.py`, `joule/a2a/capability.sapdas.yaml`, `joule/a2a/functions/*.yaml`, `joule/a2a/scenarios/*.yaml`

| ID | Check | Severity | Auto | Detail |
|----|-------|----------|------|--------|
| CR-A2-01 | AgentCard schema valid: all required fields present (name, description, url, version, skills) | Critical | Script | AST parse build_agent_card |
| CR-A2-02 | AgentCard `url` uses HTTPS scheme (not HTTP) or is resolved from env var that should be HTTPS | Critical | Script | Regex |
| CR-A2-03 | AgentCard `skills` array non-empty; each `AgentSkill` has `id` and `name` fields | Major | Script | AST |
| CR-A2-04 | `/.well-known/agent-card.json` endpoint returns full AgentCard (route registered or auto-handled by A2AStarletteApplication) | Critical | Script | Grep for well-known route |
| CR-A2-05 | JSON-RPC 2.0 format: request handler accepts `jsonrpc`, `method`, `id`; responses include these fields | Critical | LLM | Read request handling |
| CR-A2-06 | `message/send` method supported (core A2A method) | Critical | Script | Grep for method routing |
| CR-A2-07 | `message/stream` or `sendSubscribe` supported if AgentCard declares streaming capability | Major | LLM | Check streaming handler |
| CR-A2-08 | SSE events use correct types: `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent` (not custom event names) | Major | Script | Grep for event type strings |
| CR-A2-09 | Task state transitions follow spec: submitted -> working -> completed/failed/canceled; no direct submitted -> completed | Critical | LLM | Trace state transitions |
| CR-A2-10 | Error propagation uses `await updater.failed(message=...)` — not `raise ServerError(...)` or raw exceptions | Critical | Script | Regex: check for raise ServerError |
| CR-A2-11 | `cancel()` method implemented in AgentExecutor subclass | Major | Script | AST: method exists |
| CR-A2-12 | `context.get_user_input()` used for user message extraction (not manual JSON parsing of request body) | Major | Script | Grep for get_user_input |
| CR-A2-13 | `context.task_id` and `context.context_id` used directly (not extracted from raw request dict) | Major | Script | Grep for context.task_id |
| CR-A2-14 | Artifacts include `parts` array with correct structure: `[{"kind": "text", "text": ...}]` or `[{"kind": "data", "data": ...}]` | Major | LLM | Read artifact construction |
| CR-A2-15 | TextPart uses `kind: "text"` and DataPart uses `kind: "data"` (not `type` field) | Major | Script | Grep for part construction |
| CR-A2-16 | Health endpoint returns JSON `{"status": "ok"}` (not HTML, not plain text) | Major | Script | Regex in health route |
| CR-A2-17 | Joule YAML `capability.sapdas.yaml` `schema_version` matches required version (3.27.0) | Major | Script | YAML parse |
| CR-A2-18 | Joule function YAML has 5 `action_groups` with null-safety guards (`.status != null`, `.artifacts != null`, `.artifacts.size() > 0`) | Major | Script | YAML parse + regex |
| CR-A2-19 | Agent supports resubscription: task ID based reconnection via `tasks/get` or equivalent method | Minor | LLM | Check task store usage |
| CR-A2-20 | AgentCard `authentication` section matches deployed auth configuration (XSUAA scopes match xs-security.json if exists) | Major | LLM | Cross-reference files |
| CR-A2-21 | If D9≠none AND D2=Yes: HITL propagation — `A2ARemoteInputRequired` caught in executor and surfaced as `TaskState.input_required` (not swallowed) | Critical | `[LLM]` Read agent_executor.py |
| CR-A2-22 | If D9=registry: `DelegationClient.delegate()` uses SDK `ClientFactory.connect()` for agent discovery (not raw httpx JSON-RPC calls) | Major | `[LLM]` Read a2a_client/delegation_client.py |
| CR-A2-23 | If D10≠none: `TaskState.input_required` message includes typed metadata — `DataPart` with `hitl_type` field matching D10 type and `ui_hint` for Joule UI routing | Major | `[LLM]` Read executor HITL emission |
| CR-A2-24 | If D9≠none AND D10≠none: `A2ARemoteInputRequired` carries `hitl_type` field; `A2ARemoteEscalation` used for escalation propagation from remote agents | Major | `[LLM]` Read a2a_client exceptions + delegation_client |
| CR-A2-25 | If D8≠none: `agent_executor.py` calls `await mcp_client.get_tools()` and passes the result as `extra_tools=` to `build_graph()` — MCP tools reach sub-agents via the extra_tools propagation chain | Critical | `[LLM]` Read agent_executor.py + orchestrator.py |
| CR-A2-26 | If D8≠none or D9≠none: `build_graph()` accepts `extra_tools` and every agent factory call inside it passes `extra_tools`; each factory merges `create_X_tools(data_client) + (extra_tools or [])` | Critical | `[Script: regex]` grep orchestrator.py for `extra_tools` in agent factory calls |
| CR-A2-27 | If D6=odata-v2, btp-destination, or multiple: concrete data clients call `resolve_destination()` from `data_client/destination.py` to obtain the runtime URL — they NEVER read a hardcoded URL or raw config string as the base URL; destination is always resolved lazily via BTP Destination Service at runtime | Critical | `[LLM]` Read data_client/s4hana_client.py (or btp_destination_client.py) + agent_executor.py; verify `_ensure_client()` calls `resolve_destination()` |
| CR-A2-28 | `destination/` package integrity — `service.py` defines `DestinationService`, `models.py` defines `DestinationConfig`, `__init__.py` exports both + `resolve_destination()`; `llm/provider.py` imports from `..destination` (not `.destination`). Always required — AI Core is consumed via BTP Destination | Critical | `[Script: file+regex]` Check destination/ package files exist; verify provider.py import path |

---

## Reviewer 4: Performance Reviewer (CR-PR)

**Scope:** Token efficiency, caching, parallelization, query optimization, async patterns, resource management.

**Files to read:** `orchestration/orchestrator.py`, `orchestration/hitl/*.py`, `data_client/*.py`, `llm/*.py`, `tools/*.py`, `config.py`, `gunicorn.conf.py` (CF) or `app.yaml` (AppFND)

| ID | Check | Severity | Auto | Detail |
|----|-------|----------|------|--------|
| CR-PR-01 | No LLM calls for deterministic operations: routing by keyword/regex, data formatting, field extraction done in code, not via LLM | Major | LLM | Read node implementations |
| CR-PR-02 | Router uses FAST_ROUTES regex dictionary before LLM-based classification (if D4=hybrid) | Major | Script | Grep for FAST_ROUTES usage order |
| CR-PR-03 | System prompts < 2000 tokens (heuristic: < 8000 characters) to leave room for context | Minor | Script | File size check |
| CR-PR-04 | Conversation history trimmed: windowing, summary compaction, or max-messages limit configured | Major | LLM | Read memory/session handling |
| CR-PR-05 | Parallel execution used for independent sub-agent tasks (not sequential when independence is possible) | Major | LLM | Check graph topology for parallelizable branches |
| CR-PR-06 | Caching: `CachePolicy` per node or manual cache for repeated deterministic LLM calls (e.g., same classification input) | Minor | Script | Grep for CachePolicy or functools.lru_cache |
| CR-PR-07 | Data client queries use server-side filtering: `$filter` parameter passed to OData (not fetching all records and filtering in Python) | Major | Script | Grep for $filter in data_client |
| CR-PR-08 | OData queries use `$select` to limit response fields (reduce payload size) | Minor | Script | Grep for $select |
| CR-PR-09 | OData list queries use `$top` parameter with reasonable default limit (not unbounded) | Major | Script | Grep for $top |
| CR-PR-10 | No N+1 query patterns: batch reads (`$filter=ID in (...)`) instead of per-item `get()` calls in loops | Major | LLM | Read tool implementations |
| CR-PR-11 | All external calls use `async`/`await`: no synchronous `requests.get()` or `httpx.Client` in async context | Major | Script | Import scan for sync HTTP clients |
| CR-PR-12 | No `time.sleep()` in async code paths (blocks event loop); use `asyncio.sleep()` if delay needed | Major | Script | Grep for time.sleep |
| CR-PR-13 | Lightweight model used for routing (smaller/faster), full model for reasoning (if LLMRegistry has multiple roles) | Minor | LLM | Check LLMRegistry model assignments |
| CR-PR-14 | `recursion_limit` in `graph.compile()` set appropriately: Single-Agent=10, Coordinator/Sequential=25, Hierarchical=50 (not unlimited or default) | Major | Script | Grep + value check |
| CR-PR-15 | Streaming: response chunks sent incrementally via EventQueue, not buffered until full response complete | Minor | LLM | Read event emission in execute() |
| CR-PR-16 | HTTP connection pooling: `httpx.AsyncClient` created once and reused (not instantiated per request) | Major | Script | AST: check for client in __init__ vs per-call |
| CR-PR-17 | Gunicorn workers configured (`workers` in gunicorn.conf.py) for CF; resource limits set in `app.yaml` for AppFND | Major | Script | File content check |
| CR-PR-18 | No heavy initialization on module import level: large model loads, DB connections, API calls should be in lifespan/startup, not at import time | Minor | LLM | Scan module-level code |
| CR-PR-19 | No unbounded list growth in state: `messages` field uses `add_messages` reducer with trim, not unlimited append | Major | LLM | Check state reducers |
| CR-PR-20 | Structured logging at appropriate levels: DEBUG for verbose trace, INFO for request lifecycle, WARNING for recoverable errors, ERROR for failures | Minor | LLM | Read logging calls |
| CR-PR-21 | If D8=mcp-multi: MCP server connections use async context manager — connection lifecycle is bounded (no leaked sessions) | Major | `[LLM]` Read mcp/client.py |
| CR-PR-22 | If D8=mcp-multi: Tool list cached per server in `_tools_cache` — not re-discovered on every agent invocation | Major | `[Script]` Grep for `_tools_cache` in mcp/client.py |
| CR-PR-23 | If D9≠none: DelegationClient has explicit `timeout` parameter (not unbounded httpx calls) | Major | `[Script]` Grep for `timeout` in a2a_client/delegation_client.py |
| CR-PR-24 | If D9≠none: DelegationClient error handling distinguishes timeout from remote failure (separate error paths) | Minor | `[LLM]` Read a2a_client/delegation_client.py |
| CR-PR-25 | If framework=LangGraph AND stateful: production checkpointer is `PostgresSaver`/`AsyncPostgresSaver` with a bounded connection pool (`max_size`), not `InMemorySaver`; `ShallowPostgresSaver` not used (deprecated) | Major | `[LLM]` Read checkpointer setup in agent_executor.py / main.py |
| CR-PR-26 | If framework=LangGraph AND long-running SAP backend calls: bounded by `TimeoutPolicy(run_timeout=...)` or node-level timeout so a stuck backend cannot pin an A2A task indefinitely | Minor | `[LLM]` Read Send/node timeout config |

---

## Running the Code Review

### During scaffold (STATE 10)

Automatic. Runs after STATE 9 (Quality Gate). Uses scaffold context for D0-D9 awareness.

### Standalone

```bash
/gdhaifactory-agentic-pipeline:agent-code-review                  # all 4 reviewers
/gdhaifactory-agentic-pipeline:agent-code-review --reviewer SR    # Security only
/gdhaifactory-agentic-pipeline:agent-code-review --reviewer AR,SR # Architecture + Security
/gdhaifactory-agentic-pipeline:agent-code-review --fix            # auto-fix Critical findings
```

### CI/CD (deterministic pre-pass only)

```bash
python scripts/code_review_checklist.py < config.json
# Exit 0 = no Critical findings, Exit 1 = Critical findings
```

---

## Report Format

### JSON (`.claude/code_review_report.json`)

```json
{
  "timestamp": "2026-04-21T14:35:00Z",
  "project": "invoice-agent",
  "reviewers": {
    "AR": {
      "findings": [
        {"id": "CR-AR-03", "severity": "Critical", "file": "src/invoice_agent/orchestration/orchestrator.py", "line": 45, "finding": "Node 'fallback_handler' has no incoming edge — unreachable", "fix": "Add edge from error_handler to fallback_handler or remove the node"}
      ],
      "summary": {"critical": 1, "major": 0, "minor": 1}
    },
    "SR": { "findings": [...], "summary": {...} },
    "A2": { "findings": [...], "summary": {...} },
    "PR": { "findings": [...], "summary": {...} }
  },
  "summary": {
    "total_findings": 12,
    "critical": 1, "major": 5, "minor": 6,
    "deterministic_checks": 46,
    "llm_checks": 54
  },
  "overall": "FAIL",
  "pass_criteria": "0 Critical, <=8 Major"
}
```

### Result Box (stdout)

```
╔════════════════════════════════════════════════════════════╗
║  Code Review — invoice-agent                               ║
╠════════════════════════════════════════════════════════════╣
║  Architecture : ✗  1 Critical, 0 Major, 1 Minor            ║
║  Security     : ✓  0 Critical, 2 Major, 1 Minor            ║
║  A2A Protocol : ✓  0 Critical, 1 Major, 0 Minor            ║
║  Performance  : ✓  0 Critical, 2 Major, 4 Minor            ║
╠════════════════════════════════════════════════════════════╣
║  ✗  Review FAILED — 1 Critical, 5 Major, 6 Minor           ║
╚════════════════════════════════════════════════════════════╝
```
