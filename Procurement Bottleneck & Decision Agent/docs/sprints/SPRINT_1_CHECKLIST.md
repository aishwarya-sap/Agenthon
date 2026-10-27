# Sprint 1 Checklist — CF App on Mock Data

**Goal:** Running CF app with mock SAP data; client has git access and can demo offline.  
**Gate:** Agent card 200, mock A2A turn works, functional SPOC signs off.

---

## Pre-sprint
- [ ] Client BTP subaccount confirmed (region matches CF org — us10)
- [ ] CF space created (`STAGING` or `PROD`)
- [ ] BAI team has SpaceDeveloper + OrgManager
- [ ] AI Core service instance confirmed (or created)
- [ ] Git repo shared with client dev team

## Development
- [ ] `IBD_TESTING=1` smoke tests pass offline (3 tests minimum)
- [ ] `mcp-mock.json` covers all tool calls
- [ ] Agent card endpoint returns correct JSON
- [ ] Health endpoint returns `{"status":"ok"}`
- [ ] System prompt has exactly 6 MANDATORY RULES
- [ ] Financial disclaimer present in every quantitative output
- [ ] TOKEN_BUDGET_PER_RUN configured

## Deployment
- [ ] `.cfignore` excludes `.venv/`, `__pycache__/`, `tests/`
- [ ] `cf push` succeeds from `assets/<agent-name>/`
- [ ] App starts and passes health check on CF
- [ ] Mock A2A turn works via `curl`

## Sign-off
- [ ] Functional SPOC demonstrated mock query end-to-end
- [ ] CF URL shared with client
- [ ] Client dev team has git access and can run `IBD_TESTING=1 pytest`

---
**Sprint 1 complete date:** ___________  
**Signed off by:** ___________
