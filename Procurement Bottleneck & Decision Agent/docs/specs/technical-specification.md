# Technical Specification: Procurement Bottleneck & Decision Agent

## Executive Summary

### Document Metadata
Advisory, read-only SAP A2A agent on BTP Cloud Foundry. Hand-built to the build standard.

### Version History
See `docs/CHANGELOG.md`.

### Approval
Production readiness tracked in `docs/agent-checklist-assessment.md` against the v5 Agent Checklist (`docs/checklists/agent-checklist-L0-L10.md`).

## Architecture

### Business Context
Surfaces supplier silence on critical-path POs with a quantified consequence and a HoD-approved
recommendation. See `docs/specs/design-brief.md`.

### Solution Approach
Deterministic orchestration with an LLM reasoning layer: tools gather signals → deterministic
simulation + recommendation → the LLM composes the business-language reply (AI Core), with a
deterministic fallback when the LLM is unavailable. **No framework rewrite** — this is a Starlette +
A2A app, not LangGraph/gen_ai_hub (see ADR-0004).

### Architecture Diagram
```
Joule ──A2A JSON-RPC (POST /)──▶ agent_executor ─▶ agent.handle()
                                                     │ intent routing
                                                     ▼
          get_mcp_tools() ──▶ [13 tools] ──▶ simulation ─▶ recommend ─▶ HITL gate
                                   │                                     │
                        mock | BAH OData (s4_client)        LLM (ChatLiteLLM / AI Core)
```

### Design Decision Summary
Advisory-only (ADR-0001); mock-first via `IBD_TESTING` (ADR-0002); AI Core model-name dot-format +
litellm pin (ADR-0003); intent routing + LLM reasoning decoupled from data-mock (ADR-0004); BAH
sandbox connectivity (ADR-0005).

## Components

### Component Inventory (`app/`, unchanged)
| Module | Role |
|---|---|
| `main.py` | Starlette app, routes `/`, `/.well-known/agent.json`, `/health`, `/ui`, `/whoami`; uvicorn entry |
| `__main__.py` | `python -m app` entrypoint |
| `agent_card.py` | A2A AgentCard (skills, tags, examples) |
| `agent_executor.py` | A2A executor; JWT validation at boundary; HITL state |
| `agent.py` | Orchestration: intent routing, signal gathering, report/answer composition |
| `config.py` | Thresholds + runtime flags (`is_mock_mode`, `aicore_configured`, `agent_auth_mode`) |
| `tools.py` | 13 tool specs wired through the resilience layer |
| `mcp_tools.py` | `get_mcp_tools()` indirection: mock \| live |
| `skills.py` | `critical_path_flag`, `run_consequence_simulation`, `recommend_next_action` |
| `simulation.py` | 4-dimension consequence model (pure Python) |
| `s4_client.py` | Live S/4 OData reads via BAH (PO, GRN, Info Record, BP, Contract) |
| `project_data.py` | SAP PS reader + Excel/CSV Phase-1 adapter |
| `memory.py` | Institutional memory (in-memory; HANA-Vector drop-in interface) |
| `hitl.py` | Approval gate + checkpoints + action classification |
| `resilience.py` | Error taxonomy, retry/backoff, circuit breaker, `QuotaExceeded` terminal |
| `observability.py` | Structured logs, correlation id, OTel spans, PII redaction |
| `sanitize.py` | Indirect-prompt-injection scan on retrieved rows |
| `auth_ias.py` | IAS token validation (Joule A2A identity) |

### Sub-Agent Breakdown
Single-agent (no multi-agent graph). Routing is regex intent-classification + LLM reasoning.

### Primary Workflow — Silent critical-path PO
`handle` → `_analyze` → gather signals → simulate → recommend → HITL gate → scorecard; `approve`
logs a decision record (no SAP write).

## Data Model

### Core Entities
PR/PO chain, supplier-silence record, WBS/critical-path, vendor performance, source/contract terms,
consequence scorecard, decision record.

### Join Keys and Relationships
PO ↔ Supplier (LIFNR) ↔ Material ↔ WBS/activity ↔ Contract.

### Agent State and Memory
Per-context pending-approval store; institutional memory of prior outcomes.

## Integration

### Integration Inventory
| Service (Cloud) | On-Prem | Entity sets | Used by |
|---|---|---|---|
| API_PURCHASEORDER_PROCESS_SRV | OP_PURCHASEORDER_0001 | A_PurchaseOrder/Item/ScheduleLine | chain, silence |
| API_MATERIAL_DOCUMENT_SRV | OP_API_MATERIAL_DOCUMENT_SRV | A_MaterialDocumentItem/Header (mvt 101) | silence/GRN |
| API_INFORECORD_PROCESS_SRV | OP_API_INFORECORD_PROCESS_SRV_0001 | A_PurchasingInfoRecord | alternate sources |
| API_BUSINESS_PARTNER | OP_API_BUSINESS_PARTNER_SRV | A_Supplier | name, block status |
| API_PURCHASECONTRACT_PROCESS_SRV | OP_PPS_PURCHASECONTRACT_0001 | A_PurchaseContract | contract on file |

(Plus Purchase Requisition + Material Stock services to light up approval-workflow and stock signals.)

### S/4HANA Public Cloud Supplement
OData V2 (`d.results`, `/Date(ms)/`). APIKey auth on the BAH sandbox; Destination + Cloud Connector + principal propagation on the client landscape.

### Primary Integration Flow
`s4_client._get()` → classify HTTP status → `QuotaExceeded` (terminal) on sandbox quota 500, else resilience taxonomy.

## Security

### Role Catalogue / Authorization Matrix
Read-only; no mutation scopes. Joule user identity via IAS; XSUAA `Invoke` scope on the app.

### Segregation of Duties / HITL Authorization Gates
Recommendations require explicit HoD `approve`; high-penalty (> €10k) and source-switch carry extra checkpoints.

### Identity and External API Authentication
`AGENT_AUTH_MODE` = ias (Joule) | xsuaa | none (DEV only). Secrets via env/VCAP only.

## 7. Error Handling

### 7.1 Error Catalogue
401 → refresh once; 403/404 → terminal; 429/quota-500 → `QuotaExceeded` terminal (no retry); 5xx →
backoff retry; circuit-break after 3 consecutive failures. Backend failure never fabricates data —
returns an honest "live SAP data unavailable" message.
