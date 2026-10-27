# Material Risk Agent — Build Repo (Agent-Build-Repo)

Full implementation of the Project Material Availability & Supply Risk Agent on SAP BTP.
Built on the SAP Agent-PathToProd / Custom-Agentic-Solutions-CoE cookbook.

**For the generic Sprint 1 template:** see `default-repo/`.

---

## Structure

```
.
├── assets/material-risk-agent/      ← Python A2A agent (LangChain + LiteLLM + A2A SDK)
├── assets/material-risk-ui/         ← Joule-style chat UI (Node.js Express)
├── joule/                           ← Joule Studio capability YAML (Sprint 3)
├── governance/
│   ├── agent_checklist_L0_to_L10.md ← 10-pillar governance checklist
│   ├── sprint_checklist_stage0_to_8.md ← Engineering build checklist
│   └── sprint_tracker.md            ← Sprint-by-sprint progress
├── docs/
│   ├── INTEGRATION_GUIDE.md
│   ├── MASTER_REFERENCE.md
│   ├── BTP_ENABLEMENT_CHECKLIST.md
│   ├── flow_diagrams/material_risk_flow.md  ← Sprint 2 flow diagrams
│   └── token_calculation.md                 ← Sprint 3 token economics
├── manifest.yml                     ← CF deployment (uses ${CF_APP_DOMAIN})
├── deploy.sh                        ← CF push helper (prompts for domain)
├── sonar-project.properties
└── default-repo/                    ← Generic Sprint 1 template (separate)
```

---

## Quickstart (mock mode)

```bash
cd assets/material-risk-agent
cp .env.example .env    # Fill in AICORE_* values
pip install -r requirements.txt
IBD_TESTING=1 python app/_boot.py
```

## Tests

```bash
cd assets/material-risk-agent
IBD_TESTING=1 pytest prebuilt_tests tests -v --tb=short
```

## Deploy to CF

```bash
# From project root:
./deploy.sh    # prompts for CF domain
```

## Sprint progress

See [governance/sprint_tracker.md](governance/sprint_tracker.md).

---

## Cookbook compliance

| Rule | Status |
|------|--------|
| 6 MANDATORY RULES in system prompt (incl. `top=100`) | ✅ |
| A2A protocol v0.3.0 (`protocolVersion` in card) | ✅ |
| Advisory-only; HITL gate on write tools | ✅ |
| IAS auth layer (`AGENT_AUTH_MODE=ias`) | ✅ (Sprint 3) |
| Tests passing, coverage ≥ 69% | ✅ |
| Sonar config | ✅ |
| Token logging per turn | ✅ (token values Sprint 3) |
