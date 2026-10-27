# Project Material Availability & Supply Risk Agent

**Engagement:** BAI / GDH APAC — Agenthon construction supply-risk build
**Prepared by:** BAI Team — aishwarya.sharma01@sap.com
**Status:** Demo-ready (mock + live S/4 sandbox) / production gated on tenant items

---

## What was built

An advisory, read-only SAP agent that cross-references a construction project's material requirements against live S/4HANA stock and procurement data, surfaces the supply gaps that will block scheduled activities before the construction window closes, predicts each supplier's delivery, simulates the schedule/cost consequence, and recommends the least-cost recovery for the purchasing team. Every proposed action requires explicit human approval via the HITL gate. The agent makes **no writes to SAP systems**.

## Architecture

- **Agent type:** User-triggered (scheduled material-availability sweep is a documented future trigger)
- **Pattern:** LLM-orchestrated (LangChain `create_agent` + `ChatLiteLLM`) over a deterministic domain core — the LLM never computes numbers; `recursion_limit = 15` bounds the tool loop
- **Build path:** KG Cookbook (primary) / SAP Agent Golden Path (advisory, read-only)
- **Runtime:** SAP AI Core `sap/anthropic--claude-4.5-sonnet` (summarization `claude-4.5-haiku`) + Cloud Foundry us10-001, 1 GB
- **SAP connectivity:** three-way — mock (`IBD_TESTING`) / direct S/4 via SAP Business Accelerator Hub sandbox (`IBD_LIVE_S4`) / Agent Gateway (production); on-prem S/4 via Destination service + Cloud Connector
- **UI:** standalone Node.js / Express chat UI (`assets/material-risk-ui`) proxying the A2A endpoint
- **Joule integration:** agent card live; registration pending IAS principal propagation

## APIs consumed

| API / Service | SAP Business Accelerator Hub | Clean Core Level | Status |
|---|---|---|---|
| Material Stock | `API_MATERIAL_STOCK_SRV` | A | Live (sandbox) |
| Purchase Order Process | `API_PURCHASEORDER_PROCESS_SRV` | A | Live (sandbox) |
| Purchase Requisition Process | `API_PURCHASEREQ_PROCESS_SRV` | A | Live (sandbox) |
| Material Document (GR) | `API_MATERIAL_DOCUMENT_SRV` | A | Live (sandbox) |
| Business Partner (vendor) | `API_BUSINESS_PARTNER` | A | Live (sandbox) |
| Project System activities (PRPS/VORGN/RESB/AFVV) | `PROJECT_MATERIAL_SRV` | B | Phase 1 Excel adapter; live Phase 2 |
| HANA Vector Engine (RAG + memory) | Internal | N/A | In-tenant |

## Governance verdict

| Check | Status | Notes |
|---|---|---|
| Clean Core | ✅ | Level A/B APIs only; no BAPI writes; advisory-only confirmed |
| Advisory-only | ✅ | No POST/PATCH/DELETE — enforced in system prompt + 3 HITL-gated write tools |
| Safety / red team | ⚠️ | Automated battery passing; human red team pending go-live |
| Token budget | ✅ | ≤ 52,000/run ceiling; summarization at 30k (governance/4.6) |
| GDPR / EU AI Act | ✅ | Limited-risk, PII-redacted record documented (governance/5.5) |
| Cross-functional sign-off | ❌ | Tenant release gate |

## Go / No-Go

**Current verdict:** ✅ Go for demo / Agenthon (mock + live S/4 sandbox). **CONDITIONAL GO** for production.

❌ Not for production until:
- [ ] IAS principal-propagation config for Joule registration
- [ ] Cloud Connector + principal propagation on the client S/4 (on-prem)
- [ ] L0-2 model benchmarking + L0-3.3 live RagEval
- [ ] L0-5.1 Responsible-AI safety evaluation + human red team
- [ ] Cross-functional sign-off (L0-7.4)

## Handover checklist

- [x] `.env.example` reviewed — no actual values committed; `.env` gitignored
- [x] Mock mode verified offline (`IBD_TESTING=1`): 175 tests / 73% coverage
- [x] Live S/4 sandbox mode verified (`IBD_LIVE_S4=1`)
- [x] Token cost ceiling: ≤ 52,000/run (governance/4.6)
- [x] CODE_WALKTHROUGH.md provided
- [x] Governance artifact set complete (13 docs + README, `assets/material-risk-agent/governance/`)
- [ ] CF space + services set up in the client subaccount
- [ ] Joule registration completed by the client's Joule admin
