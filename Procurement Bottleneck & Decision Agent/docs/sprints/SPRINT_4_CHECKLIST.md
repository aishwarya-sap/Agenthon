# Sprint 4 Checklist — Production Handover

**Goal:** Agent running in production; client team can maintain it independently.  
**Gate:** Production URL live, client signs off on CODE_WALKTHROUGH.

---

## Pre-sprint
- [ ] Client has confirmed production BTP subaccount and CF space
- [ ] On-prem S/4 connectivity (if applicable):
  - SCC installed and connected to BTP
  - S/4 OData resources exposed in SCC
  - Principal propagation configured (STRUST/SNC)
  - Production destination configured in BTP cockpit

## Production deployment
- [ ] IBD_TESTING=0, AGENT_AUTH_MODE=ias in production
- [ ] `cf push` to production space succeeds
- [ ] Health endpoint returns 200 on production URL
- [ ] All environment variables set (no `.env.example` leftovers)
- [ ] BAI team temporary SpaceDeveloper role **revoked** after handover

## Governance final check (Agent Checklist L0-1 through L0-10)
- [ ] L0-1: SonarQube clean (0 blockers/critical)
- [ ] L0-2: Test coverage ≥ 80%, all edge cases covered
- [ ] L0-3: 3 decorators, 6 mandatory rules, disclaimer on every quantitative output
- [ ] L0-4: JWT validation, advisory-only confirmed, xs-security.json correct
- [ ] L0-5: `.cfignore` clean, health endpoint working, `cf push` stable
- [ ] L0-6: All 4 Joule YAML files deployed
- [ ] L0-7: TOKEN_BUDGET_PER_RUN set, monthly cost estimate agreed
- [ ] L0-8: `mcp-mock.json` accurate, IBD_TESTING offline verified
- [ ] L0-9: CB_README.md, REQUIREMENTS.md, CODE_WALKTHROUGH.md complete
- [ ] L0-10: .env.example clean, client prerequisites met, sprint checklists signed

## Handover documents
- [ ] CODE_WALKTHROUGH.md provided to client dev team and reviewed
- [ ] REQUIREMENTS.md final version signed off
- [ ] CB_README.md Go/No-Go verdict updated to ✅ Go for production
- [ ] Client prerequisites document confirmed complete

## Client training
- [ ] Client dev team can run `IBD_TESTING=1 pytest` locally
- [ ] Client dev team can `cf push` from the repo
- [ ] Client knows how to rotate AI Core service key
- [ ] Client knows how to update `mcp-mock.json` for new scenarios

## Sign-off
- [ ] Production URL shared and confirmed working
- [ ] Client IT and functional SPOC signatures received
- [ ] Post-engagement review scheduled (2 weeks after go-live)

---
**Sprint 4 complete date:** ___________  
**Signed off by (BAI):** ___________  
**Signed off by (Client):** ___________
