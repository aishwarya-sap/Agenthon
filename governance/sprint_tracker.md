# Sprint Tracker — Material Risk Agent

Track which checklist items are done per sprint. Update at end of each sprint review.

---

## Sprint 1 Status — COMPLETE ✅

**Goal achieved:** Agent deployed on BAI CF (us10), mock mode working, UI functional.

| Item | Status | Notes |
|------|--------|-------|
| Agent A2A card live (`/.well-known/agent.json`) | ✅ | Both BAI CF routes running |
| `IBD_TESTING=1` mock mode working | ✅ | 163 tests passing |
| Test coverage ≥ 70% | ✅ | 69% (163 tests) |
| Chat UI working (Prompt Library + send/receive) | ✅ | Joule-style UI deployed |
| System prompt: 6 MANDATORY RULES | ✅ | Updated 2026-10-22 |
| Advisory-only (no write without HITL) | ✅ | Approval gate on write tools |
| Financial disclaimer in system prompt | ✅ | |
| CF deployment automated (manifest.yml) | ✅ | cf push -f manifest.yml |
| Sonar config in place | ✅ | sonar-project.properties added 2026-10-22 |
| Agent Checklist L0-1 to L0-2 reviewed | ⚠️ | Partial — pending formal sign-off |
| Data readiness questionnaire sent to Adarsh | ⏳ | Pending |

---

## Sprint 2 Status — PENDING ⏳

**Goal:** Live S/4HANA data from Adarsh dev system; FC sign-off.

| Item | Status | Notes |
|------|--------|-------|
| S/4HANA OData connectivity (Cloud Connector) | ⏳ | Adarsh on-prem, SEA region |
| `IBD_LIVE_S4=1` mode + `S4_SERVICE_PROFILE=onprem` | ⏳ | On-prem transport seam to code |
| All 7 OData services returning real data | ⏳ | |
| Technical validation with Adarsh team | ⏳ | |
| Functional consultant sign-off on data accuracy | ⏳ | |
| Flow diagrams updated for client program call | ⏳ | See `docs/flow_diagrams/` |
| Agent Checklist L0-3 to L0-5 reviewed | ⏳ | |

---

## Sprint 3 Status — PENDING ⏳

**Goal:** Production-grade security (PP + RBAC), token economics validated.

| Item | Status | Notes |
|------|--------|-------|
| GenAI Hub model benchmark | ⏳ | |
| Token calculation per interaction type | ⏳ | See `docs/token_calculation.md` |
| IAS app registration (BAI IAS tenant) | ⏳ | `AGENT_AUTH_MODE=ias` code ready |
| `/whoami` confirms IAS identity chain | ⏳ | Code ready, env vars TBC |
| RBAC: HoD role sees alternative sourcing | ⏳ | |
| Joule capability imported + tested | ⏳ | `joule/da.sapdas.yaml` ready |
| Principal propagation end-to-end | ⏳ | |
| Sonar scan completed | ⏳ | |
| Agent Checklist L0-6 to L0-8 reviewed | ⏳ | |

---

## Sprint 4 Status — PENDING ⏳

**Goal:** QA → Production handover; agent live in Adarsh production.

| Item | Status | Notes |
|------|--------|-------|
| Production deployment plan approved | ⏳ | |
| UAT with representative users | ⏳ | |
| Runbook written | ⏳ | |
| Production CF push completed | ⏳ | Region: SEA |
| Joule capability registered in production | ⏳ | |
| Final acceptance sign-off | ⏳ | |
| Agent Checklist L0-9 to L0-10 reviewed | ⏳ | |

---

## Key dates

| Milestone | Date | Status |
|-----------|------|--------|
| Agenthon Demo (BAI internal) | 2026-10-26 | ⏳ |
| Sprint 1 delivery to Adarsh | TBC | ⏳ |
| Sprint 2 completion | TBC | ⏳ |
| Sprint 3 completion | TBC | ⏳ |
| Sprint 4 / Production go-live | TBC | ⏳ |
