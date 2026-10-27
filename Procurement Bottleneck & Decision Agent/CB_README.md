# Adarsh Developers — Procurement Bottleneck & Decision Agent

**Engagement date:** October 2026
**Prepared by:** BAI Team — aishwarya.sharma01@sap.com
**Status:** Sprint 1 Complete / Sprint 2 In Progress

---

## What was built

An advisory, read-only SAP agent that detects supplier silence on critical-path purchase orders across active construction projects, quantifies the downstream consequence (schedule slip, idle-resource cost, milestone-penalty exposure, emergency-sourcing premium), and recommends an action (escalate / source-switch / absorb) for the Purchasing Head of Department. All outcomes are captured as institutional memory. The agent makes **no writes to SAP systems**; every proposed action requires explicit human approval via the HITL gate.

## Architecture

- **Agent type:** User-triggered + scheduled scan
- **Pattern:** P1 Standard (LLM-orchestrated, deterministic domain core)
- **Build path:** KG Cookbook (primary) / Agent-PathToProd-main-3 Golden Path
- **Runtime:** SAP AI Core `sap/anthropic--claude-4-5-sonnet` + Cloud Foundry us10-001
- **SAP connectivity:** Mode B Agent Gateway (SAP Accelerator Hub sandbox in Sprint 1–2; on-prem S/4 via Cloud Connector in Sprint 3–4)
- **Joule integration:** Capability bundle ready (`joule/` folder), CLI deploy pending IAS App2App configuration

## APIs consumed

| API / Service | SAP Business Accelerator Hub | Clean Core Level | Status |
|---|---|---|---|
| MM Purchasing PO Maintain V2 | `MM_PUR_PO_MAINT_V2_SRV` | A | Mock (Sprint 1), Live (Sprint 2+) |
| Purchase Requisition Manage | `ME_PURCHASEREQ_MANAGE_SRV` | A | Mock (Sprint 1), Live (Sprint 2+) |
| Goods Movement / GR | `API_GOODSMVT_SRV` | A | Mock (Sprint 1), Live (Sprint 2+) |
| Project System (PS) WBS | `PS_PROJECTDEF_SRV` | B | Mock (Sprint 1), Live (Sprint 2+) |
| Project Network Activities | `API_PROJECT_NETWORK_ACTV_SRV` | B | Mock (Sprint 1), Live (Sprint 2+) |
| HANA Vector Engine (memory) | Internal | N/A | Planned Sprint 3+ |

## Governance verdict

| Check | Status | Notes |
|---|---|---|
| API Policy v.4.2026a | ⚠️ | ATQ sign-off pending — Sprint 4 gate |
| Clean Core | ✅ | Level A/B APIs only; no BAPI writes; advisory-only confirmed |
| Safety Dashboard | ⚠️ | Automated red team passing (6/6); human red team pending go-live |
| Cross-functional sign-off | ⚠️ | Pending Sprint 4 |
| Advisory-only | ✅ | No POST/PATCH/DELETE confirmed — enforced in system prompt + HITL |
| Token budget | ✅ | 52,000/run ceiling, instrumentation wired (governance/4.5) |
| GDPR/EU AI Act | ⚠️ | Legal/DPO classification pending (governance/5.5) |

## Go / No-Go

**Current verdict:** ✅ Go for Sprint 1–2 testing (mock + sandbox data)

❌ Not for production until:
- [ ] IAS App2App configuration for Joule integration (B2/B3)
- [ ] Cloud Connector + principal propagation on Adarsh S/4 (Phase C)
- [ ] ATQ API policy sign-off
- [ ] Cross-functional sign-off (L0-7.4)
- [ ] Human red team on tenant (L0-5.3)

## Handover checklist

- [x] Repo shared with Adarsh dev team via Git
- [ ] JIRA epic created with all tickets
- [x] `.env.example` reviewed — no actual values committed
- [x] Mock mode verified offline (IBD_TESTING=1): 111 tests / 92% coverage
- [x] Token cost estimate: 52,000/run ceiling (governance/4.5)
- [ ] CF space + services set up in Adarsh's subaccount (Sprint 4)
- [ ] Joule registration completed by Adarsh's Joule admin (Sprint 3)
- [x] CODE_WALKTHROUGH.md provided to client dev team
- [ ] BAI team's temporary Space Developer role revoked (Sprint 4)
