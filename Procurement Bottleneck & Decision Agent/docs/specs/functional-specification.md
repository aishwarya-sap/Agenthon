# Functional Specification: Procurement Bottleneck & Decision Agent

## 1. Document Organization

### 1.1 Document Log
Hand-authored to the SAP build standard. Maintained alongside the code in `docs/specs/`.

### 1.2 References
- `docs/specs/design-brief.md`, `docs/specs/technical-specification.md`, `docs/specs/rtm.md`
- `docs/decisions/` (ADRs), `docs/checklists/` (Quality Gate + Code Review)

### 1.3 Acronyms and Glossary
PR = Purchase Requisition · PO = Purchase Order · GRN = Goods Receipt · WBS = Work Breakdown
Structure · HITL = Human-in-the-Loop · HoD = Head of Department · BAH = SAP Business Accelerator Hub ·
A2A = Agent-to-Agent protocol · silence = days since PO issue with no confirmation/GRN.

### 1.4 Conventions
🔴 critical / 🟡 watch / 🟢 on-track. All monetary figures are estimates and carry the financial disclaimer.

## 2. Functional Description

### 2.1 Business Process Overview
Daily scan of open POs → flag supplier silence on critical-path deliveries → quantify consequence →
recommend action → HoD approves → decision logged. Plus ad-hoc Q&A over the same data.

### 2.2 Functional Requirements
- **FR-1 Daily Blockers dashboard** — table of open POs ranked by urgency; critical blockers
  (silence ≥ 7 days) surfaced separately from watch-list items.
- **FR-2 Supplier-silence detection** — days since PO issue or last GRN vs tolerance (3d) / HITL trigger (7d).
- **FR-3 Consequence simulation** — schedule slip, idle-crew cost, milestone-penalty exposure.
- **FR-4 Ranked recommendation** — contact supplier / line up backup source / hold and monitor.
- **FR-5 Alternate-supplier lookup** — approved alternate sources for a material.
- **FR-6 Delivery-performance history** — supplier on-time rate, late count, average delay, risk band.
- **FR-7 Free-form Q&A** — answer the exact question asked, concisely, grounded in the gathered signals.
- **FR-8 HITL approval gate** — recommendations require explicit `approve`/`cancel`; decision logged.
- **FR-9 Honest failure** — if a SAP read fails, say so; never fabricate data.

### 2.3 Authorization, Security and Guardrails
JWT validated at the A2A boundary (`AGENT_AUTH_MODE` = ias | xsuaa | none-dev). Advisory-only: system
prompt forbids writes; no BAPI/OData write ever issued. Secrets only via env/VCAP. Financial
disclaimer appended to every quantitative answer. Indirect-prompt-injection scan on retrieved rows.

### 2.4 Interaction Design
Joule chat + a standalone demo UI (`/ui`): Daily Blockers dashboard (landing) and a conversational
panel with context-aware prompt chips. Intents routed: list / alternate-supplier / delivery-performance
/ free-form consequence / full analysis.

### 2.5 Interfaces and Knowledge Sources
S/4 OData via BAH sandbox (PO, Material Document/GRN, Info Record, Business Partner, Purchase
Contract); project data via SAP PS or Excel; institutional memory + RAG (HANA Cloud Vector, design).

## 3. Alternative Approaches Considered
Full scorecard for every turn (rejected — too verbose; see ADR-0004). LangGraph multi-agent rewrite
(rejected — would change working functionality). Direct ChatOpenAI (rejected — must go through AI Core).

## 4. Detailed Description

### 4.1 Orchestration, Input and Output
`agent_executor` receives the A2A message → `agent.handle()` → intent routing → signal gathering →
either a focused answer, the HITL scorecard, or an honest backend-error message.

### 4.2 Processing Logic
Deterministic signal gathering + simulation + recommendation; the LLM composes the final
business-language reply (when AI Core is configured) with a deterministic fallback otherwise.

### 4.3 Data Objects and Entities
PR/PO chain, supplier-silence record, WBS/critical-path, vendor performance, source/contract,
consequence scorecard, decision record.

### 4.4 System Interfaces and Tool Specifications
13 tools (see technical spec §Components) resolved via `get_mcp_tools()`; all `side_effect:false`
except the two log/notify tools which never touch SAP.

## 5. Non-Functional Requirements
Turn latency bounded (tool timeouts 30s, ≤3 retries, circuit breaker). Coverage ≥ 70%. Mock mode
fully offline. Token budget design ceiling 52k/run.

## 6. Operational Considerations
### 6.1 Cutover / Rollout
DEV mock → BAH sandbox (our environment test) → Adarsh Tokyo S/4 (prod). Flip `AGENT_AUTH_MODE`→ias and
`ENABLE_WHOAMI`→off before production.
### 6.2 Operational Model
CF app, single instance; logs to stdout → BTP Cloud Logging.

## 7. Assumptions
Standard S/4 OData services are activated and reachable; project schedule available via PS or Excel.

## 8. Open Issues
### 8.1 Open Issues Register
Vendor on-time metrics and contract penalty clauses are not in standard OData → simulated until a KPI
source is connected. Approval-workflow and stock signals require the PR and Material-Stock services.
### 8.2 Low-Confidence Requirements Carried Forward
Exact on-prem OData service names on the Adarsh landscape (confirm against `$metadata`).

## 9. Test Plan (Business Test Conditions)
### 9.1 Test Scenarios
Silent critical-path PO → scorecard + approval gate; low-silence PO → "on track"; delivery-performance
question → track-record table; backend failure → honest "data unavailable"; approve → decision logged.
### 9.2 Test Data Requirements
Offline fixtures in `mcp-mock.json`; BAH sandbox POs for live mode.

## 10. Decision Sources and Sign-Off
Design PDF + SAP Agent Golden Path; decisions recorded as ADRs in `docs/decisions/`.
