# Sprint 3 Checklist — Joule Integration + Security + Token Analysis

**Goal:** Agent connected to Joule via A2A; SonarQube clean; token usage measured.  
**Gate:** Joule round-trip working, SonarQube quality gate passes.

---

## Pre-sprint
- [ ] IAS admin has configured App2App trust chain:
  - `Cli2Joule` dependency configured in IAS tenant
  - `A2A_Proxy_App` created
  - `A2A_Custom_Agent_App` created
  - `joule-to-proxy` and `proxy-to-target` dependencies wired
- [ ] `joule login --app-tid <tenant>` succeeds (AUTH_FETCH_TOKEN_FAILED resolved)
- [ ] Joule Studio accessible (correct subscription — enterprise capability manager, NOT SAP Build)

## Joule YAML deployment
- [ ] `joule/da.sapdas.yaml` reviewed and correct CF app URL in endpoint
- [ ] `joule/<capability>/capability.sapdas.yaml` correct
- [ ] `joule/functions/<function>.yaml` matches agent's actual parameters
- [ ] `joule/scenarios/<scenario>.yaml` has at least 3 realistic trigger phrases
- [ ] `joule deploy` (or Studio upload) succeeds
- [ ] Joule skill appears in capability list

## Security (L0-4)
- [ ] AGENT_AUTH_MODE=ias in production manifest
- [ ] IAS JWT validation implemented in `auth_ias.py`
- [ ] JWT validated on every A2A request
- [ ] xs-security.json scopes correct
- [ ] SonarQube configured (`sonar-project.properties`)
- [ ] SonarQube quality gate passes (0 blockers, 0 critical)
- [ ] No secrets in code, no hardcoded credentials

## Token analysis (L0-4.1)
- [ ] Token budget per run measured (update TOKEN_BUDGET_PER_RUN)
- [ ] Monthly cost estimate calculated (formula: turns/day × tokens/turn × $/1k × 30)
- [ ] Cost ceiling agreed with client
- [ ] Token count logged per turn

## Sign-off
- [ ] End-to-end Joule query → agent → SAP → response demonstrated
- [ ] SonarQube report shared with client

---
**Sprint 3 complete date:** ___________  
**Signed off by:** ___________
