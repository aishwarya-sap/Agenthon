# Technical Specification: Project Material Availability & Supply Risk Agent

## Executive Summary

An advisory-only SAP A2A agent on SAP BTP Cloud Foundry that surfaces construction-material supply gaps, predicts supplier delivery, simulates schedule/cost impact, and recommends least-cost recovery — surfaced through SAP Joule and a standalone chat UI. LLM-orchestrated (LangChain `create_agent` + LangGraph) over a deterministic domain core; the LLM never computes numbers.

### Document Metadata

| Field | Value |
|---|---|
| Agent | material-risk-agent |
| Protocol | A2A v0.3.0 (a2a-sdk 0.3.22) |
| Runtime | SAP BTP Cloud Foundry, Python 3.11, 1 GB |
| LLM | `sap/anthropic--claude-4.5-sonnet` via SAP AI Core / Gen AI Hub (ChatLiteLLM) |
| Start command | `python app/_boot.py` |

### Version History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-26 | As-built technical specification |

### Approval

Pending tenant release gate.

## Architecture

### Business Context

See `docs/specs/functional-specification.md` §2.1.

### Solution Approach

LLM-orchestrated ReAct loop (`recursion_limit=15`, summarization at 30k tokens) that calls 15 tools; all arithmetic is deterministic Python in `app/domain/`. Three operating modes (mock / live-sandbox / production) dispatch behind one tool surface.

### Architecture Diagram

```
User (Joule / Chat UI)
        │  A2A JSON-RPC
        ▼
app/main.py  (Starlette + A2A SDK; /whoami; /.well-known/agent-card.json)
        │
app/agent_executor.py  ←  IAS JWT validation (app/auth_ias.py)
        │
app/agent.py  (LangChain create_agent + ChatLiteLLM, recursion_limit=15)
        │
   15 tools via app/mcp_providers/agw.py
   ├── IBD_TESTING=1   → in-process mock (seeded Tower Alpha fixtures)
   ├── IBD_LIVE_S4=1   → direct OData (Accelerator Hub sandbox); live-first fallback to seeded data
   └── production      → Agent Gateway MCP discovery
        │
app/domain/  (deterministic Python — zero LLM tokens)
   scoring · simulation · prediction · recommend · hitl · sanitize · memory
        │
S/4HANA OData  (app/s4_client.py — $top=100 cap, 30s cache, async executor)
```

### Design Decision Summary

See `docs/specs/design-brief.md` (D0–D12) and `docs/decisions/` ADRs.

## Components

### Component Inventory

| Module | Responsibility |
|---|---|
| `app/_boot.py` | Entry point — maps AI Core creds from VCAP_SERVICES, re-execs main |
| `app/main.py` | A2A Starlette server, routes, `/whoami`, uvicorn |
| `app/agent.py` | Core agent: system prompt, LLM orchestration, fallback chain, circuit breaker |
| `app/agent_executor.py` | A2A boundary: identity validation, streaming, response shaping |
| `app/auth_ias.py` | IAS JWT validation (Joule principal propagation) |
| `app/config.py` | Mode flags, S/4 service profile, auth mode |
| `app/tools.py` | 15 StructuredTool definitions (mock + live builders) |
| `app/s4_client.py` | OData transport: `$top` caps, 30s request cache, async executor, onprem PP |
| `app/circuit_breaker.py` | Per-model circuit breaker (3 failures / 30s) |
| `app/prompt_injection_detector.py` | Layered RAG injection defence |
| `app/domain/` | Deterministic core: data, scoring, simulation, prediction, recommend, memory, sanitize, hitl |

### Sub-Agent Breakdown

None — single-agent design (see design-brief D1).

### Primary Workflow — Supply Risk Report

requirements → stock + open POs/PRs + material master → compute gaps → per at-risk material: supplier history + delivery prediction + RAG context → simulate consequence → recommend → brief verdict + table + `[SUGGESTIONS]`.

## Data Model

### Core Entities

Activity, Stock (MARD), Order (PO/PR), GR history (material document mvt 101), Supplier (BP), Alt-source (info record / contract).

### Agent State and Memory

InMemorySaver checkpointer; 30s request-scoped OData cache keyed by `(service, entity, params)`; institutional memory in `app/domain/memory.py` (in-process append-only — HANA Cloud backend pending).

## Integration

### Integration Inventory — S/4HANA OData services (read-only)

| Purpose | Cloud (sandbox) | On-prem (Adarsh) | Entity |
|---|---|---|---|
| Material stock | `API_MATERIAL_STOCK_SRV` | `OP_API_MATERIAL_STOCK_SRV` | `A_MatlStkInAcctMod` |
| Purchase orders | `API_PURCHASEORDER_PROCESS_SRV` | `OP_PURCHASEORDER_0001` | `A_PurchaseOrderItem` |
| Purchase requisitions | `API_PURCHASEREQ_PROCESS_SRV` | `OP_PURCHASEREQUISITION_0001` | `A_PurchaseRequisitionItem` |
| Material documents (GR) | `API_MATERIAL_DOCUMENT_SRV` | `OP_API_MATERIAL_DOCUMENT_SRV` | `A_MaterialDocumentItem` |
| Business partner / supplier | `API_BUSINESS_PARTNER` | `OP_API_BUSINESS_PARTNER_SRV` | `A_Supplier` |
| Purchasing info record | `API_INFORECORD_PROCESS_SRV` | `OP_API_INFORECORD_PROCESS_SRV_0001` | `A_PurgInfoRecdOrgPlantData` |
| Purchase contract | `API_PURCHASECONTRACT_PROCESS_SRV` | `OP_PPS_PURCHASECONTRACT_0001` | `A_PurchaseContractItem` |

Also: HANA Cloud Vector (RAG corpus `ZAGENT_MATERIAL_RISK`); project schedule from SAP PS or Excel/CSV. Service names resolve via `app/config.py::s4_service()` keyed on `S4_SERVICE_PROFILE`.

### Identity and External API Authentication

Cloud profile: APIKey (sandbox). On-prem profile: IAS JWT inbound (`auth_ias.py`) → `X-user-token` → Destination Service OAuth2SAMLBearer / PrincipalPropagation → S/4 scoped to the user's authorizations.

## Security

### Authorization & HITL Gates

Advisory-only; 3 write tools gated by `app/domain/hitl.py` until `confirmed=true`. Alternate sourcing restricted to Purchase HoD. RAG injection scan + PII redaction in `app/domain/sanitize.py`.

## 7. Error Handling

### 7.1 Error Catalogue & Degradation

Per-tool 30s timeout; circuit breaker opens after 3 consecutive model failures (30s cooldown) and the fallback chain advances. Live-first fallback: a failed live S/4 read (both flags set) serves seeded data tagged `signal_status=simulated`.

## 8. Deployment

### 8.1 BTP Service Instances

AI Core (LLM), optional Destination + Connectivity (on-prem), optional HANA Cloud (RAG/memory), XSUAA/IAS (auth).

### 8.2 Deployment Topology

CF app `material-risk-agent` (1 GB, `python app/_boot.py`) + CF app `material-risk-ui` (Node, proxies via `AGENT_URL`). Deploy via `manifest.yml` / `mta.yaml`.

## 9. Testing

### 9.1 Test Strategy

Offline pytest suite with mock tools (`IBD_TESTING=1` forced in conftest). 175 tests, 73% coverage. LLM/e2e paths skip unless `AICORE_CLIENT_ID` is set.

### 9.2 Requirements Traceability

See `docs/specs/rtm.md`.

## 10. Open Items

See `docs/specs/functional-specification.md` §8 and `docs/HANDOFF.md` §4.
