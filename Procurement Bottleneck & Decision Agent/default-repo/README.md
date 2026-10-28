# SAP A2A Agent — Default Repo (Sprint 1 Template)

Generic, reusable scaffold for any SAP A2A agent engagement.
Share this repo with the client at the start of Sprint 1.

---

## What's in this repo

```
default-repo/
├── assets/agent-starter-kit/         ← Python A2A agent (rename to your agent name)
├── assets/agent-starter-kit-ui/      ← Joule-style chat UI
├── governance/
│   ├── agent_checklist_L0_to_L10.md   ← governance checklist
│   └── sprint_checklist_stage0_to_8.md ← Engineering build checklist
├── docs/
│   ├── data_readiness_questionnaire.md
│   └── client_sprint1_email.md
├── manifest.yml                 ← CF deployment (parameterized)
├── deploy.sh                    ← CF push helper (prompts for domain)
└── sonar-project.properties
```

---

## Quickstart (Sprint 1 — mock mode)

```bash
# 1. Copy and fill in your credentials
cp assets/agent-starter-kit/.env.example assets/agent-starter-kit/.env
# Edit .env: set AICORE_* values

# 2. Install dependencies (Python 3.11+)
cd assets/agent-starter-kit
pip install -r requirements.txt

# 3. Run locally (fully offline, mock data)
IBD_TESTING=1 python app/_boot.py

# 4. Run smoke tests
IBD_TESTING=1 pytest tests/test_smoke.py -v
```

---

## Deploy to Cloud Foundry

```bash
# From the default-repo/ root:
./deploy.sh
# You will be prompted for your CF domain.
```

Or manually:
```bash
CF_APP_DOMAIN=cfapps.ap20.hana.ondemand.com cf push -f manifest.yml
```

---

## Customise for your domain (Sprint 2)

1. Rename `assets/agent-starter-kit/` to your agent name (update `manifest.yml` to match)
2. Edit `assets/agent-starter-kit/app/agent.py` → replace the `[Agent Name]` and workflow section in `get_system_prompt()`
3. Replace `mcp-mock.json` with your domain's mock tool responses
4. Add real tools in `assets/agent-starter-kit/app/mcp_providers/agw.py` (IBD_LIVE_S4 branch)
5. Update `manifest.yml` agent/UI app names

---

## Persistence — recommendations & approvals (Sprint 4)

The agent persists its recommendations and approvals to an **append-only** backend table on
**HANA Cloud** (the audit trail), with the HANA Cloud **Vector Engine** for optional semantic recall
of prior decisions. Selected via `MEMORY_BACKEND` in `.env` (default `in_memory` for Sprint 1 mock):

```bash
MEMORY_BACKEND=in_memory    # Sprint 1/2 — in-process store (mock, tests)
# MEMORY_BACKEND=hana       # Sprint 4 — durable HANA Cloud audit table (ZAGENT_DECISION_LOG)
```

**Seam pattern:** keep one `MemoryStore` interface (`append()` / `recall()`); implement a
`HanaMemoryStore` behind the same interface and select it when `MEMORY_BACKEND=hana`. Business logic
and tests do not change. Use a technical user with an **INSERT/SELECT-only** role (append-only audit).
On CF, bind a HANA (HDI-container / schema) service — credentials arrive via `VCAP_SERVICES`, never in
env. See `docs/data_readiness_questionnaire.md` §HANA Cloud for what to request from the client.

---

## Governance

Review the [Agent Checklist](governance/agent_checklist_L0_to_L10.md) at the end of each sprint.
Review the [Engineering Checklist](governance/sprint_checklist_stage0_to_8.md) before each deployment.

---

## Cookbook reference

This scaffold follows the **SAP  / Custom-Agentic-Solutions-CoE** cookbook.
Mandatory rules enforced:
- Exactly 3 `@agent_*` decorators in `agent.py`
- 6 MANDATORY RULES in every system prompt (incl. `top=100` and financial disclaimer)
- `IBD_TESTING=1` mock mode working before any live connectivity
- `pytest` coverage ≥ 70% before Sprint 2
