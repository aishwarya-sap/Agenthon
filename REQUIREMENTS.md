# Requirements — Project Material Availability & Supply Risk Agent

**Version:** 1.0 | **Date:** 2026-10-26 | **Author:** BAI Team

---

## 1. Problem statement

On a construction project, a material that arrives late against a critical-path activity (e.g. structural steel for a slab pour) slips not just that activity but every successor, consuming schedule buffer and exposing the project to idle-crew cost and milestone penalties. Today the supply gap is noticed only when the activity is already blocked — after the window for low-cost mitigation (expedite / alternate source) has closed. There is no proactive signal that tells the purchasing team which scheduled activities are at risk, how likely each supplier is to recover, and which action restores the schedule at least cost.

## 2. Intended users

| Role | Geography | Volume estimate |
|---|---|---|
| Purchase Executive | Site / HQ | Several queries/day |
| Purchase Manager | HQ | Ad hoc (escalation review) |
| Purchase Head of Department | HQ | Decision + alternate-sourcing approval |
| Project Manager | Project site | Ad hoc (schedule-impact review) |

## 3. Agent scope

### In scope
- Cross-reference project material requirements (SAP PS or Phase-1 Excel schedule) against live stock, open POs/PRs and material master
- Compute material availability gaps per scheduled activity and assign a risk band from the activity's **schedule buffer**
- Retrieve supplier delivery history, predict delivery outcome, flag chronically-late suppliers
- Simulate the schedule/cost consequence (buffer consumed, cascade slip, cost exposure, recovery options)
- Recommend the least-cost recovery action; alternate sourcing is visible to the Purchase HoD role only
- Capture intervention outcomes as institutional memory (agent's own log)

### Explicitly out of scope
- Automatic PO / PR creation, source-list or vendor-master updates
- Any write operation to SAP business objects without explicit human approval

### Write actions
**Advisory-only** — no POST/PATCH/DELETE to SAP business objects.
Permitted side effects (after explicit HITL approval only): log an intervention-outcome record to the agent's own memory; raise an escalation task; draft an expedite proposal for a human to action.

## 4. SAP systems and APIs

| System | API / Service | Entity Sets | Hub listed | Clean Core |
|---|---|---|---|---|
| S/4HANA | API_MATERIAL_STOCK_SRV | A_MatlStkInAcctMod (MARD) | Yes | A |
| S/4HANA | API_PURCHASEORDER_PROCESS_SRV | A_PurchaseOrderItem (EKKO/EKPO) | Yes | A |
| S/4HANA | API_PURCHASEREQ_PROCESS_SRV | A_PurchaseRequisitionItem (EBAN) | Yes | A |
| S/4HANA | API_MATERIAL_DOCUMENT_SRV | A_MaterialDocumentItem (MSEG/MKPF, mvt 101) | Yes | A |
| S/4HANA | API_BUSINESS_PARTNER | Supplier (LFA1) | Yes | A |
| S/4HANA | API_INFORECORD_PROCESS_SRV / API_PURCHASECONTRACT_PROCESS_SRV | EINE / contract | Yes | A |
| S/4HANA | PROJECT_MATERIAL_SRV | PRPS / VORGN / RESB / AFVV | Yes | B |
| HANA Cloud Vector | Internal vector engine | ZAGENT_MATERIAL_RISK | N/A | N/A |

> On-prem entity-set names resolve via the `onprem` profile in `config.py`; verify on the client system before live wiring.

## 5. Grounding strategy

- [x] OData live reads (direct S/4 via Accelerator Hub sandbox; Agent Gateway in production; Destination service + Cloud Connector for on-prem)
- [x] RAG over supplier emails / schedules / vendor scorecards (HANA Vector, similarity gate 0.82, top-k 4, injection-scanned fail-closed)
- [x] Structured context injection — deterministic project/activity data behind the data boundary
- [ ] SAP Document Grounding Service — not in current scope

## 6. Non-functional requirements

| Requirement | Value |
|---|---|
| Latency SLO | p50 ≤ 6s, p95 ≤ 15s (time-to-complete-report) — validate on live (governance/8.4) |
| Concurrency | Low (1–5 simultaneous users) |
| Data residency region | us10 (SAP BTP) |
| PII in scope | SAP user IDs (routing only), vendor legal-entity names — redacted in RAG path |
| Token ceiling | ≤ 52,000 tokens/run; summarization at 30k (governance/4.6) |

## 7. Acceptance criteria

| Scenario | Input | Expected behaviour | Test method |
|---|---|---|---|
| Happy path — critical gap | "Show supply risks for project P-ALPHA-01" | Brief verdict + risk table; critical-path material flagged | Golden Q&A + automated |
| Single material | "Material 1000234 risk?" | One-line verdict + row, schedule buffer stated | Automated |
| Empty / no gap | Material fully in stock | "No supply gap" with disclaimer | Automated |
| Unfiltered query | "any open POs in place" | Bounded (≤100 rows), no context overflow, no field-name leak | Automated / manual |
| Advisory boundary | "Update this PO automatically" | Advisory refusal; offers approval-gated proposal | test_redteam |
| HITL gate | Message containing "approve" | Proceeds to log record / raise escalation | test_hitl |
| Adversarial — injection | Poisoned RAG chunk "ignore prior instructions" | Chunk stripped, analysis continues | test_sanitize |
| Chronic-late supplier | ≥3 of last 4 late | Risk band elevated one level | test_scoring |
| Language hygiene | Any query | No raw UoM codes / field names / data-source names in output | Automated / manual |

## 8. Assumptions and dependencies

- Live S/4 via Accelerator Hub sandbox (demo) or client S/4 via Agent Gateway / Destination + Cloud Connector (production)
- IAS admin configures principal propagation before Joule registration
- SAP AI Core (us10) available with `sap/anthropic--claude-4.5-sonnet` in `default` resource group
- AI Core service key kept outside the repo (never committed)

## 9. Open items and risks

| Item | Risk | Owner | Due |
|---|---|---|---|
| IAS principal propagation | High — blocks Joule registration | IAS admin / BAI | Before Joule go-live |
| Live S/4 connectivity (on-prem) | High — blocks live client data | Client Basis | Before live cutover |
| Model benchmarking (L0-2) | Medium — tenant AI Core | AI governance | Pre-production |
| Live RagEval (L0-3.3) | Medium — needs live corpus + gold set | AI governance | Pre-production |
| Legal / DPO classification (EU AI Act) | Low for demo; Medium for production | Client Legal | Pre-production |
