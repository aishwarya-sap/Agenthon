# Data Readiness Questionnaire — SAP A2A Agent Engagement

**INTERNAL — send to client SPOC at Sprint 1 kickoff**  
**Engagement:** [Client Name] — [Agent Name]  
**Sent by:** BAI Team  
**Due before Sprint 2 start**

---

## Mail template

**Subject:** Data Readiness Confirmation — [Agent Name] (Action Required Before Sprint 2)

Hi [Client SPOC name],

We are kicking off Sprint 2 of the [Agent Name] engagement next week and need your team to confirm readiness on a few items before we can connect the agent to live SAP data.

Could you please go through the checklist below and share your answers by [date — 2 business days before Sprint 2 start]?

---

## Section A — S/4HANA system access

| # | Question | Your answer |
|---|---|---|
| A1 | What is the S/4HANA release version (e.g., 2023 FPS01, Tokyo SP01)? | |
| A2 | Is this an on-premise system or SAP S/4HANA Cloud? | |
| A3 | Is the system reachable via SAP Cloud Connector from BTP? (yes/no/TBD) | |
| A4 | Who is the Basis contact responsible for Cloud Connector / OData activation? | |
| A5 | Is `/IWFND/MAINT_SERVICE` accessible on this system? (yes/no) | |

---

## Section B — OData service availability

For each OData service the agent uses, please confirm it is active in your system and note any naming differences.

> **How to verify:** Log on to the S/4 system, run transaction `/IWFND/MAINT_SERVICE`, search for the service name below.

| OData service | Standard name | Active in your system? | Custom name (if different) |
|---|---|---|---|
| Purchase Orders | `MM_PUR_PO_MAINT_V2_SRV` | | |
| Purchase Requisitions | `ME_PURCHASEREQ_MANAGE_SRV` | | |
| Goods Movements | `API_GOODSMVT_SRV` | | |
| Project Structure | `PS_PROJECTDEF_SRV` | | |
| Network Activities | `API_PROJECT_NETWORK_ACTV_SRV` | | |

> ⚠️ If a service is inactive, the Basis team needs to activate it via `/IWFND/MAINT_SERVICE` → "Activate and Maintain Services" before Sprint 2.

---

## Section C — User and role setup

| # | Question | Your answer |
|---|---|---|
| C1 | Do you have S/4 users the agent can read data for in DEV/QA? | |
| C2 | Do these users exist in IAS (Identity Authentication Service)? (required for principal propagation) | |
| C3 | Do the S/4 users and IAS users share the same email address? | |
| C4 | Which authorization roles do the demo users have? (e.g., MM_PURCH_* or custom) | |
| C5 | Is a dedicated technical user available for the Cloud Connector/SCC service account? | |

---

## Section D — Data quality

| # | Question | Your answer |
|---|---|---|
| D1 | Are there active Purchase Orders in the system with WBS/project assignments? | |
| D2 | Are there POs with open items (not fully goods-received) that the agent can use as test data? | |
| D3 | Are project network activities (AFVV) populated with float values? | |
| D4 | Are there any POs where the supplier has not confirmed (Confirmation Status = "Not Confirmed")? | |
| D5 | Are vendor delivery history records available (EKBE, LFM1)? | |

---

## Section E — IAS / BTP prerequisites (Sprint 3 dependency)

*This section is needed for Joule integration in Sprint 3. If Sprint 1–2 are on sandbox data, this can be answered later — but please review so we can flag blockers early.*

| # | Question | Your answer |
|---|---|---|
| E1 | IAS tenant URL (e.g., `<tenant>.accounts.ondemand.com`) | |
| E2 | Who is the IAS administrator for this tenant? | |
| E3 | Is the "04 - Build Code with Joule" (or equivalent Joule-enabled) subaccount available? | |
| E4 | Are you willing to grant BAI team the `Joule_Content_Manager` role in the Joule-enabled subaccount? | |
| E5 | Is the `Cli2Joule` IAS App2App dependency already configured? (BAI will confirm this; just note if you know) | |

---

## Section HANA — Decision/approval persistence (HANA Cloud)

The agent stores its recommendations and approvals in an append-only HANA Cloud table (audit trail),
with optional Vector Engine semantic recall. Confirm so this can be provisioned.

| # | Item | Answer |
|---|---|---|
| H1 | Is a HANA Cloud instance available in the BTP subaccount (or should one be provisioned)? | |
| H2 | Can a schema (e.g. `ADARSH_AGENT`) + the `ZAGENT_DECISION_LOG` table (+ vector table) be created? | |
| H3 | Can a technical user be created with an **INSERT/SELECT-only** role (no update/delete)? | |
| H4 | Share credentials via a HANA service key, or bind the HANA instance to the CF app (HDI/schema)? | |
| H5 | Is the HANA Cloud Vector Engine enabled (needed for semantic recall)? | |
| H6 | Any data-residency / retention requirements for the stored decisions? | |

---

## Section F — Timeline confirmation

| # | Item | Target date |
|---|---|---|
| F1 | Section A–B answers returned to BAI | |
| F2 | Basis team activates missing OData services | |
| F3 | Cloud Connector reachable from BTP DEV space | |
| F4 | Sprint 2 kickoff call | |

---

## What BAI will provide

- Agent source code in `default-repo/` (shared via git) — ready to clone and `cf push`
- CF app URL for functional SPOC testing (mock data, no SAP connection needed)
- Step-by-step guide for Basis team: Cloud Connector setup + OData service activation
- IAS admin mail template for Sprint 3 prerequisites

Please reply to this mail with the completed table, or share it as a comment in the project tracker.

Thanks,  
[BAI engagement lead]
