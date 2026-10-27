# Insights & Accelerators — Project Material Availability & Supply Risk Agent

> **Purpose.** Captures novel patterns, reusable components, and gotchas from this build.
> After delivery, relevant items are promoted to the Golden Path accelerators.

---

## Accelerators discovered

- **Three-way MCP tool provider** — `app/mcp_providers/agw.py::get_mcp_tools()` dispatches mock (`IBD_TESTING`) / direct-S4 sandbox (`IBD_LIVE_S4`) / Agent Gateway (production) behind one capability-resolved seam; tool names/shapes are identical across all three, so tests and demo exercise the same surface as production.
- **`$top` hard cap at the OData client** — a vague query ("any open POs") against a shared sandbox returns thousands of rows and overflows the LLM context; capping PO/PR reads at `$top=100` in `s4_client` (not relying on the LLM to pass `top`) makes the agent robust to under-specified prompts.
- **Request-scoped OData cache** — a 30s dict cache keyed by `(service, entity, params)` dedupes the repeated reads a single multi-tool turn would otherwise fire for the same material.
- **Async executor for blocking httpx** — wrapping synchronous OData calls in `loop.run_in_executor(...)` keeps the asyncio event loop responsive (CF health checks on `/.well-known/agent-card.json` were intermittently timing out when a turn fired 10–15 serial blocking calls).
- **`recursion_limit` on the LangGraph invocation** — bounds the tool-call loop so an ambiguous query cannot run away; pairs with the summarization-at-30k-tokens middleware to keep per-run cost bounded.
- **Decorator import shim** — `try/except` around `sap_cloud_sdk.agent_decorators` with no-op fallbacks lets the same `agent.py` run offline (tests) and in production (real decorators) without branching.
- **conftest forces mock mode** — `conftest.py` sets `IBD_TESTING=1` **and** `IBD_LIVE_S4=0`; because `main.py` calls `load_dotenv()` on import, a developer's live-demo `.env` would otherwise leak real OData calls into the offline suite.

## SAP gotchas hit

- **A2A agent-card endpoint renamed** — a2a-sdk ≥ 0.3.22 deprecates `/.well-known/agent.json` in favour of `/.well-known/agent-card.json`; the CF `health-check-http-endpoint` and the UI's card fetch must both use the new path or the app intermittently 404s via the GoRouter while a blocking turn stalls the health check.
- **`asset.yaml` API version** — this agent uses `asset.sap/v1` (the newer standard); the sibling procurement agent uses `com.sap.ai/v1`. Both deploy; prefer `asset.sap/v1` for new agents.
- **Org CF memory quota during paired push** — pushing the 1 GB agent + UI together can exceed the org quota at staging (staging needs a transient ~1 GB container on top of the running app); stop the old agent first to free its 1 GB, then push.
- **Field-name / UoM leakage into chat** — the LLM will echo raw `delivery_complete=true` / UoM codes (`TO`, `EA`) unless the system prompt explicitly forbids `key=value` expressions and maps codes to words; a concrete negative example in the prompt was needed to stop it.
- **Shared sandbox has no demo materials** — the Accelerator Hub sandbox doesn't contain the Tower Alpha material numbers, so unscoped queries surface sandbox noise; steer demo users to project/material-scoped prompts (the UI's starter chips do this).

## Architecture decisions made

| Decision | Options considered | Chosen | Reason |
|---|---|---|---|
| Orchestration | Fixed N-call / ReAct tool loop | Bounded tool loop (`recursion_limit=15`) | Flexible multi-hop reasoning while bounding cost; deterministic core keeps numbers exact |
| Write actions | Full write / Advisory-only | Advisory-only | Engagement constraint; HITL gate is the only path to side effects |
| Chat UI | Inline Python-served page / separate Node.js app | **Separate Node.js / Express** | Reusable multi-turn UI with A2A proxy + dynamic suggestion chips; decouples UI iteration from the agent |
| Deploy descriptor | `manifest.yml` only / `mta.yaml` | **both present** | `manifest.yml` for fast `cf push`; `mta.yaml` for MTA-based deployment to managed spaces |
| CF memory | 512M / 1G | **1G** | LiteLLM + LangChain + LangGraph + all tools + the larger dependency tree fit comfortably in 1G |
| Grounding | KG / Document Grounding / OData | OData + RAG + context injection | Structured transactional data → OData; emails/schedules → RAG; small deterministic config → injection |

## Deliberate differences vs the reference procurement agent (same team, same cookbook)

| Dimension | This agent | Procurement reference | Rationale |
|---|---|---|---|
| Chat UI | separate Node.js/Express (`assets/material-risk-ui`) | inline Python-served `demo/index.html` | reusable multi-turn UI; see deploy/standardisation note in handover |
| Deploy | `manifest.yml` + `mta.yaml` | `manifest.yml` | MTA path available for managed-space deploy |
| `asset.yaml` schema | `asset.sap/v1` | `com.sap.ai/v1` | newer standard |
| CF memory | 1 GB | 512 MB | larger dependency tree |

These are intentional and documented; they are **not** drift. A standardisation recommendation is in the handover report.
