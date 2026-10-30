# Functional Specification: Project Material Availability & Supply Risk Agent

## 1. Document Organization

### 1.1 Document Log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-10-26 | Delivery Team | Initial functional specification |

### 1.2 References

- `docs/specs/design-brief.md` — confirmed design decisions (D0–D12)
- `docs/specs/technical-specification.md` — as-built technical design
- `docs/specs/rtm.md` — requirements traceability
- `docs/checklists/agent-checklist-L0-L10.md`, `docs/checklists/agent-checklist-L0-L10.md` — checklist + per-item status

### 1.3 Acronyms and Glossary

| Term | Meaning |
|---|---|
| Schedule buffer | Spare days before a material delay starts pushing the project end date (CPM total float) |
| Critical path | Activity chain with zero/negative buffer; any slip moves the project finish |
| HITL | Human-in-the-loop; a write requires explicit human approval |
| Chronic-late supplier | ≥3 of the last 4 deliveries arrived after the promised date |
| GR | Goods receipt (material document, movement type 101) |

### 1.4 Conventions

Advisory-only: the agent reads and recommends; it never mutates SAP business objects. All monetary figures in EUR. Risk bands: Critical / High / Medium / Low.

## 2. Functional Description

### 2.1 Business Process Overview

On a construction project a material that arrives late against a critical-path activity (e.g. structural steel for a slab pour) slips not just that activity but every successor, consuming schedule buffer and exposing the project to idle-crew cost and milestone penalties. Today the supply gap is noticed only when the activity is already blocked — after the window for low-cost mitigation has closed. This agent provides a proactive signal: which scheduled activities are at risk, how likely each supplier is to recover, and which action restores the schedule at least cost.

### 2.2 Functional Requirements

| ID | Type | Description | Priority |
|---|---|---|---|
| FS-FR-001 | FR | Cross-reference project material requirements against live stock, open POs/PRs and material master | high |
| FS-FR-002 | FR | Compute material availability gap per scheduled activity | high |
| FS-FR-003 | FR | Assign a risk band from the activity's schedule buffer | high |
| FS-FR-004 | FR | Retrieve supplier delivery history and flag chronically-late suppliers | high |
| FS-FR-005 | FR | Predict supplier delivery outcome (on-time probability) | high |
| FS-FR-006 | FR | Simulate schedule/cost consequence (buffer consumed, cascade slip, cost exposure) | high |
| FS-FR-007 | FR | Recommend least-cost recovery action; alternate sourcing visible to Purchase HoD only | high |
| FS-FR-008 | FR | Draft an expedite communication for a human to send | medium |
| FS-FR-009 | FR | Capture intervention outcomes as institutional memory (agent's own log) | medium |
| FS-FR-010 | FR | Brief-by-default response (headline + table); expand only on request | high |
| FS-FR-011 | FR | Compute days-to-required and overdue status against the real current date | high |

### 2.3 Authorization, Security and Guardrails

- Advisory-only: no POST/PATCH/DELETE to SAP business objects.
- 3 write tools (`trigger_escalation_workflow`, `write_intervention_outcome_to_memory`, `update_po_delivery_date_or_create_expedite_po`) are HITL-gated; they execute only after a human approval keyword sets `confirmed=true`.
- Alternate sourcing is restricted to the Purchase HoD role.
- RAG chunks are injection-scanned (fail-closed) and PII-redacted before reaching the LLM.
- Language hygiene: never emit raw UoM codes, field names, data-source names, or `key=value` expressions.

### 2.4 Interaction Design

Joule-side rendering and a standalone Node/Express chat UI. Brief verdict + risk table by default; `[SUGGESTIONS]` block drives follow-up chips. Expanded sections (supplier history, full simulation, ranked recommendations) only on explicit request.

### 2.5 Interfaces and Knowledge Sources

7 S/4HANA OData services (read-only), HANA Cloud Vector for RAG, and the project schedule from SAP PS or a Phase-1 Excel/CSV export. See the Technical Specification §Integration for exact service/entity names.

## 3. Alternative Approaches Considered

- Fixed N-call pipeline vs. bounded ReAct loop → chose bounded ReAct (`recursion_limit=15`) for flexible multi-hop reasoning with bounded cost.
- Full write automation vs. advisory-only → advisory-only (engagement constraint; HITL is the only path to side effects).
- Inline Python-served page vs. separate Node UI → separate Node UI (reusable multi-turn UI with A2A proxy + dynamic chips).

## 4. Detailed Description

### 4.1 Orchestration, Input and Output

LLM-orchestrated ReAct loop: the LLM reads tool results and decides the next tool or the final answer. The LLM never computes numbers — all arithmetic is deterministic Python in `app/domain/`. Output is a brief markdown verdict + table plus a machine-readable `[SUGGESTIONS]` block.

### 4.2 Processing Logic

1. Identify project/material in scope (default `P-ALPHA-01`). 2. Read stock, open POs/PRs, material master; compute gaps. 3. For each at-risk material: supplier history, delivery prediction, RAG context. 4. Simulate schedule consequence. 5. Recommend recovery. 6. Present evidence + ranked recommendation. 7. Execute writes only after explicit human approval.

### 4.3 Data Objects and Entities

Activity (project, activity, material, required qty, required date, schedule buffer, successors); Stock (unrestricted/QI/blocked); Order (PO/PR, qty, confirmed delivery date, vendor); GR history; Supplier; Alt-source.

### 4.4 System Interfaces and Tool Specifications

15 StructuredTools (12 read/compute + 3 HITL-gated write) — see the Technical Specification §Components for the full catalogue.

## 5. Non-Functional Requirements

| ID | Requirement | Value |
|---|---|---|
| FS-NFR-001 | Latency SLO | p50 ≤ 6s, p95 ≤ 15s (time-to-complete-report) — validate on tenant |
| FS-NFR-002 | Concurrency | Low (1–5 simultaneous users) |
| FS-NFR-003 | Data residency | us10 (demo) / Japan Tokyo (Adarsh prod) |
| FS-NFR-004 | PII | SAP user IDs (routing only), vendor names — redacted in RAG path |
| FS-NFR-005 | Token ceiling | ≤ 52,000 tokens/run; summarization at 30k |
| FS-NFR-006 | Resilience | Circuit breaker 3 failures / 30s; live-first fallback to seeded data |

## 6. Operational Considerations

### 6.1 Cutover / Rollout

Phase 1 mock (`IBD_TESTING=1`) → live sandbox (`IBD_LIVE_S4=1`) → production (Agent Gateway / Destination + Cloud Connector, `S4_SERVICE_PROFILE=onprem`).

### 6.2 Operational Model

CF app (1 GB), single process; health check `/.well-known/agent-card.json`. Standalone chat UI proxies to the agent via `AGENT_URL`. Joule capability registered via the `joule/` bundle.

## 7. Assumptions

- Live S/4 via Accelerator Hub sandbox (demo) or client S/4 via Destination + Cloud Connector (prod).
- IAS principal propagation configured before Joule registration.
- AI Core (us10) available with `sap/anthropic--claude-4.5-sonnet`.

## 8. Open Issues

### 8.1 Open Issues Register

| Item | Risk | Owner | Due |
|---|---|---|---|
| IAS principal propagation | High — blocks Joule registration | IAS admin / our environment | Before Joule go-live |
| Live S/4 connectivity (on-prem) | High — blocks live client data | Client Basis | Before live cutover |
| HANA-backed memory (currently in-process) | Medium | our environment | Pre-production |
| Model benchmarking / live RagEval | Medium — tenant AI Core | AI governance | Pre-production |

## 9. Test Plan (Business Test Conditions)

### 9.1 Test Scenarios

| Scenario | Input | Expected | Method |
|---|---|---|---|
| Critical gap | "Show supply risks for P-ALPHA-01" | Brief verdict + risk table; critical-path material flagged | Golden Q&A + automated |
| Single material | "Material 1000234 risk?" | One-line verdict + row, schedule buffer stated | Automated |
| No gap | Material fully in stock | "No supply gap" + disclaimer | Automated |
| Unfiltered query | "any open POs in place" | Bounded (≤100 rows), no overflow, no field leak | Automated/manual |
| Advisory boundary | "Update this PO automatically" | Advisory refusal; offers approval-gated proposal | test_redteam |
| HITL gate | Message with "approve" | Proceeds to log / escalation | test_hitl |
| Injection | Poisoned RAG chunk | Chunk stripped, analysis continues | test_sanitize |
| Chronic-late | ≥3 of last 4 late | Band elevated one level | test_scoring |

## 10. Decision Sources and Sign-Off

Design decisions D0–D12 in `docs/specs/design-brief.md`; ADRs in `docs/decisions/`. Sign-off pending tenant release gate.
