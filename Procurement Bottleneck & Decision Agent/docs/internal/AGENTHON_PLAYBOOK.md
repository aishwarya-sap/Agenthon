# Agenthon Delivery Program — 4-Sprint Playbook

**INTERNAL REFERENCE — not shared with client**
**Program:** Agenthon — SAP A2A Agent Delivery
**Engagement model:** 4 sprints × 2 weeks = ~8 weeks per agent
**Owner:** BAI Team

---

## Overview

The Agenthon program delivers a production-ready SAP Joule A2A agent in 4 structured sprints. Each sprint has a defined goal, deliverables, and a completion gate. The gate must be passed before the next sprint begins.

```
Sprint 1          Sprint 2          Sprint 3          Sprint 4
Foundation        Live Data         AI + Security     Production
& Mock            Integration       + Joule           Handover
───────────       ──────────        ─────────         ──────────
Weeks 1-2         Weeks 3-4         Weeks 5-6         Weeks 7-8
```

---

## Sprint 1 — Foundation & Mock Validation (Weeks 1–2)

**Goal:** Client has a running CF app they can interact with on mock data. Git access established. Data readiness confirmed.

### What we deliver
- Push `default-repo/` to client's git repository
- CF app deployed in BAI test space (`IBD_TESTING=1`, mock data)
- Agent card live at `/.well-known/agent.json`
- A2A endpoint working — mock 7-section report returned
- Smoke tests passing (3 tests: card, health, A2A turn)
- Data readiness questionnaire sent → client confirms S/4 data availability

### What client does
- Grant git repository access (create repo, add BAI team)
- Review and confirm data readiness questionnaire
- Functional SPOC tests the mock app via the direct URL

### Sprint 1 completion gate
- [ ] Agent card returns HTTP 200
- [ ] Mock A2A turn produces structured report
- [ ] 3 smoke tests pass
- [ ] Client confirms data readiness (or raises blockers)
- [ ] L0 checklist items reviewed: L0-1.3, L0-6.3–6.5, L0-8.1–8.2

### Sprint 1 artefacts
- `default-repo/` pushed to client git
- CF app URL confirmed working
- Sprint 1 checklist completed: `docs/sprints/SPRINT_1_CHECKLIST.md`

---

## Sprint 2 — Live Data Integration (Weeks 3–4)

**Goal:** Agent runs against real S/4HANA data. Functional and technical validation complete.

### What we deliver
- `IBD_TESTING=0` — live OData calls via SAP Accelerator Hub sandbox
- All tools tested with real data shapes (13 tools)
- Functional validation with Purchasing HoD (report is meaningful)
- Technical validation (correct data, correct OData entity sets)
- Flow diagrams updated and presented on Sprint 2 program call
- Environment upgrade: `AGENT_AUTH_MODE` reviewed; XSUAA service binding if needed

### What client does
- Confirm S/4 entity set names via `/IWFND/MAINT_SERVICE` (Basis team)
- Validate flow diagrams against their business process
- Functional SPOC signs off on report quality

### Sprint 2 completion gate
- [ ] End-to-end report from live OData data (not mock)
- [ ] All 13 tools return expected data shapes
- [ ] Functional SPOC sign-off: "report makes sense for our procurement process"
- [ ] Flow diagrams reviewed and approved
- [ ] L0 checklist items reviewed: L0-2.1, L0-3.1–3.3, L0-6.3–6.5, L0-9

### Sprint 2 artefacts
- Live data demo (recorded or live)
- Flow diagrams in `docs/flow-diagrams/`
- Sprint 2 checklist completed: `docs/sprints/SPRINT_2_CHECKLIST.md`

---

## Sprint 3 — AI Enhancement + Security + Joule (Weeks 5–6)

**Goal:** Agent is production-quality: token-measured, secured, Joule-integrated, SonarQube clean.

### What we deliver
- **Gen AI Hub model testing:** run eval dataset against candidate models, confirm `sap/anthropic--claude-4-5-sonnet` selection, update `governance/2.6-frontier-model-justification.md`
- **Token calculation:** measure actual tokens per run via Gen AI Hub, compare vs 52k budget, update `governance/4.5-customer-token-consumption-forecast.md`
- **Principal propagation:** configure IAS App2App (B2/B3), update `PROCUREMENT_AGENT` destination to `OAuth2JWTBearer`, set `AGENT_AUTH_MODE=ias`
- **RBAC:** bind `xs-security.json` XSUAA service, test with real user roles
- **Joule integration:** `joule deploy ./da.sapdas.yaml --compile -n "procurement_bottleneck_test"`, test via Joule panel
- **SonarQube:** run local scan, fix any critical/blocker findings, report

### Prerequisites (must be done before Sprint 3 starts)
- IAS admin configures `Cli2Joule` dependency + `A2A_Proxy_App` + `A2A_Custom_Agent_App` in `an46vc4ar.accounts.ondemand.com/admin` (see mail template: `docs/internal/DATA_READINESS_QUESTIONNAIRE.md`)
- Adarsh Basis team confirms S/4 Cloud Connector + principal propagation is ready

### Sprint 3 completion gate
- [ ] Joule round-trip: question in Joule panel → 7-section report returned
- [ ] IAS token validated (`/whoami` shows correct user)
- [ ] SonarQube: zero critical/blocker findings
- [ ] Token actuals within 52k budget
- [ ] L0 checklist items reviewed: L0-2.2–2.6, L0-4.1–4.2, L0-5.1–5.4, L0-6.1–6.2

### Sprint 3 artefacts
- Token cost report (actual vs forecast)
- Joule integration demo (recorded or live)
- SonarQube scan report
- Sprint 3 checklist completed: `docs/sprints/SPRINT_3_CHECKLIST.md`

---

## Sprint 4 — Production Handover (Weeks 7–8)

**Goal:** Agent live on client production environment. Full handover package delivered. Client signed off.

### What we deliver
- Push complete codebase to client's production BTP environment
- Agent live on production CF (client's org/space)
- Data validation: run against production data, client validates output accuracy
- Final L0-L10 checklist review — close all completable items, document remaining gaps
- Full handover package:
  - `CB_README.md` (what was built, governance verdict)
  - `CODE_WALKTHROUGH.md` (for client dev team)
  - `REQUIREMENTS.md` (acceptance criteria signed off)
  - All sprint checklists completed
  - `agent-outcome-report.md` updated with final status
- Revoke BAI team's temporary Space Developer role

### Follow-up plan (if data validation fails)
- 2-week follow-up window after go-live
- Daily check-in with Adarsh Purchasing HoD
- If report is factually incorrect → diagnose OData entity set mapping → hotfix within 48h
- If KPI output is misleading → adjust thresholds in `config.py` → re-deploy

### Sprint 4 completion gate
- [ ] Production agent URL live and responding
- [ ] Client data validation: "report is accurate against our live S/4 data"
- [ ] All handover docs delivered and reviewed
- [ ] Cross-functional sign-off obtained (L0-7.4)
- [ ] BAI team access revoked
- [ ] Client formal sign-off recorded

### Sprint 4 artefacts
- Production URL
- Signed handover record
- Final outcome report
- Sprint 4 checklist completed: `docs/sprints/SPRINT_4_CHECKLIST.md`

---

## Program governance

| Meeting | Cadence | Participants | Agenda |
|---|---|---|---|
| Sprint kickoff | Start of each sprint | BAI team + client SPOC | Goals, blockers, access needed |
| Mid-sprint check | Week 2 of each sprint | BAI lead + client SPOC | Status, blockers, data issues |
| Sprint review | End of each sprint | BAI team + client stakeholders | Demo, checklist review, gate decision |
| Program close | After Sprint 4 | BAI team + Adarsh management | Handover, feedback, next steps |

## Escalation path

| Blocker type | Owner | Escalation to |
|---|---|---|
| IAS/BTP access issues | Adarsh IT admin | BAI engagement manager |
| S/4 data / Basis issues | Adarsh Basis team | Adarsh IT Director |
| AI Core / platform issues | BAI team | SAP BTP support |
| Scope change request | BAI lead | Both engagement managers |
