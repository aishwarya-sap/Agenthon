# Specification (PRD) — Critical-Path Procurement Consequence Agent

**Agent ID:** `procurement-bottleneck-agent` · **Version:** 1.0.0 · **Status:** Build complete (mock-first), deploy pending
**Source of truth:** `Design — Procurement Bottleneck & Decision Agent` (SAP IDEA "Idea to Value · Design" export).
**Classification:** Advisory, read-only on SAP. Full custom agent (SAP Agent Golden Path).

## 1. Purpose
Give the Purchasing Head of Department a real-time, consequence-aware view of which supplier silences across all active projects will cause schedule slip and idle resources — with alternatives and escalation routing ready to act on, and every outcome captured as institutional memory so the same blind spot never repeats.

## 2. Personas & access
| Persona | Role | Access |
|---|---|---|
| Purchasing HoD (Purchaser – Central Procurement) | Primary decision-maker; reviews scorecards, approves actions | Full (via "My Projects – Critical" Fiori app) |
| Project Manager(s) (from `PRPS.VERNR`) | Receive escalation notifications | Notification-only (SPA tasks) |
| Procurement CoE | Owns configurable thresholds (SPA Business Rules) | Config |
| Procurement Operations | Receives platform alerts | Alerts only |

Identity: XSUAA OAuth2 + principal propagation to S/4HANA (backend auth objects enforced). Advisory agents still require per-user authorization so a user only sees data they may read.

## 3. Reasoning classification (L0-8)
- **Trigger types:** user-initiated (Fiori/Joule query), event-driven (`po.confirmation.overdue`), scheduled (14-day due-date sweep).
- **Reasoning:** orchestrated graph — deterministic tool/skill core with two LLM touch-points (intent framing, verdict synthesis). Not a free-running ReAct loop; step-bounded and cost-bounded.
- **Model:** `sap/anthropic--claude-4-5-sonnet` (fallback `claude-3-5-haiku`), temperature 0.0, token budget 52,000/run.

## 4. Tools (13)
**MCP-backed SAP/RAG reads (8):** `get_open_pr_po_chain`, `get_approval_workflow_status`, `detect_supplier_silence`, `get_source_and_contract_dependencies`, `get_procurement_contract_terms`, `link_po_to_project_wbs`, `get_vendor_delivery_performance`, `rag_retrieve_contract_and_history`.
**In-process (5):** `recall_supplier_memory`, `run_consequence_simulation`*, `recommend_next_action`*, `write_decision_record`†, `trigger_escalation_notification`†.
**Internal skill:** `critical_path_flag`.
(* design double-lists these as both skills and tools; implemented once as skills, exposed as tools. † side-effecting, HITL-gated, advisory-only.)

## 5. Grounding (L0-3 / L0-9)
Hybrid: OData/CDS live reads (EKKO/EKPO/EKBE/EBAN/PRPS/AFKO/AFVV/MLST/KONP/EORD/LFM1) + BDC data products + RAG over HANA Cloud Vector Engine (contract clauses/history; `text-embedding-3-small`; similarity gate ≥ 0.82) + institutional memory (`ZAGENT_DECISION_LOG`). Project/schedule data via one boundary: **SAP Project System** (Phase 2) or **structured Excel/CSV** (Phase 1 PMO upload). A finding is labelled "live" only when the tool returned live data; all else "simulated".

## 6. Consequence simulation (4 dimensions)
`schedule_slip_days` (predicted delay beyond AFVV float), `idle_resource_cost_eur` (slip × teams × CATS daily rate), `penalty_exposure_eur` (KONP penalty prorated to milestone breach probability), `emergency_sourcing_premium_eur` (category spot-market uplift on PO value) → `total_consequence_exposure_eur`. Run at 24h and 48h horizons.

## 7. Business rules (defaults; externalized to SPA Business Rules in prod)
Scan horizon 14d · silence tolerance 3d (proceed) / 7d (HITL trigger) · critical-path float buffer 5d · materiality €25k · penalty-exposure HITL €10k · obsolete PO > 90d · RAG similarity ≥ 0.82 · confirmation SLA 85 %/48h · emergency premium % by category · memory recall top-5.

## 8. Human-in-the-loop (L0-6.6/6.7)
Two side-effecting tools run only after an approval keyword (`approve` / `confirm` / `yes proceed`); source-switch confirmation must name the LIFNR. Nine checkpoints: CP1 scorecard+action · CP2 alt-vendor LIFNR · CP3 obsolete-PO closure · CP4 escalation payload · CP5 penalty > €10k · CP6 supplier-without-InfoRecord · CP7 PO-without-agreement · CP8 ERP-fallback contract · CP9 uncontracted supplier. Action-classification table: autonomous (reads) / advisory (skills) / blocked-pending-approval (writes). All approvals logged (approver, timestamp, keyword).

## 9. Advisory-only boundary
No `POST`/`PATCH`/`DELETE`, no `BAPI_PO_CREATE1`, no source-list write. The only side effects are (a) append to the agent's institutional-memory decision log and (b) raise an SPA notification/approval task. A source switch is a recommendation a human executes in SAP.

## 10. KPIs (success metrics)
Silence detection lead time 10–14d → ≤ 3d · touchless escalation ≥ 70% · source-switch lead time ≤ 2 business days · supplier confirmation ≥ 85% within 48h · schedule-slip days avoided ≥ 5/project/yr · decision-record coverage ≥ 95% · HoD recommendation acceptance ≥ 65%. Catalogue KPI: revenue loss due to stock-outs (%).

## 11. Out of scope
SAP writes / source-of-supply reassignment execution; SAP GUI automation; live connector hardening (MS Graph, D&B/Resilinc) beyond read-only pattern; metering/CBC/commercial sign-off (tenant-side).
