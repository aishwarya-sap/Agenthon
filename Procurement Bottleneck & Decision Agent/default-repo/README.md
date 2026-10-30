# Default Repo — Agent Starter Template

Generic, reusable scaffold for any SAP A2A agent engagement. Share this repo with the
client as the starting point for their build.

---

## What's in this repo

```
default-repo/
├── assets/agent-starter-kit/         ← Python A2A agent (rename to your agent name)
├── assets/agent-starter-kit-ui/      ← chat UI
├── governance/
│   └── agent_checklist_L0_to_L10.md   ← governance checklist
├── docs/
│   ├── data_readiness_questionnaire.md
│   └── client_kickoff_email.md
├── manifest.yml                 ← CF deployment (parameterized)
└── deploy.sh                    ← CF push helper (prompts for domain)
```

---

## Run locally (mock mode)

```bash
# Install dependencies (Python 3.11+)
cd assets/agent-starter-kit
pip install -r requirements.txt

# Run fully offline on mock data — no credentials needed
IBD_TESTING=1 python app/_boot.py

# Run smoke tests
IBD_TESTING=1 pytest tests/test_smoke.py -v
```

Configuration is read from the process environment; credentials come from bound CF
service instances (`VCAP_SERVICES`) / BTP Destinations, never a committed file.

---

## Deploy to Cloud Foundry

```bash
# From the default-repo/ root (prompts for your CF domain):
./deploy.sh

# Or manually:
CF_APP_DOMAIN=cfapps.<region>.hana.ondemand.com cf push -f manifest.yml
```

---

## Customise for your domain

- Rename `assets/agent-starter-kit/` to your agent name (update `manifest.yml` to match)
- Edit `assets/agent-starter-kit/app/agent.py` → replace the agent name and workflow in `get_system_prompt()`
- Replace `mcp-mock.json` with your domain's mock tool responses
- Add real tools in `assets/agent-starter-kit/app/mcp_providers/agw.py`
- Update `manifest.yml` agent/UI app names

---

## Persistence — recommendations & approvals

The agent persists its recommendations and approvals to an **append-only** table on
**HANA Cloud** (the audit trail), with the HANA Cloud **Vector Engine** for optional
semantic recall. Selected via the `MEMORY_BACKEND` environment variable (default `in_memory`):

- `MEMORY_BACKEND=in_memory` — in-process store (mock, tests)
- `MEMORY_BACKEND=hana` — durable HANA Cloud audit table (`ZAGENT_DECISION_LOG`)

**Seam pattern:** one `MemoryStore` interface (`append()` / `recall()`); a `HanaMemoryStore`
behind the same interface, selected when `MEMORY_BACKEND=hana`. Business logic and tests do
not change. Use a technical user with an **INSERT/SELECT-only** role (append-only audit). On CF,
bind a HANA (HDI-container / schema) service — credentials arrive via `VCAP_SERVICES`, never in a
committed file. See `docs/data_readiness_questionnaire.md` for what to request from the client.

---

## Governance

Review the [Agent Checklist](governance/agent_checklist_L0_to_L10.md) periodically through the build.

Mandatory rules enforced:
- Exactly 3 `@agent_*` decorators in `agent.py`
- 6 MANDATORY RULES in every system prompt (incl. `top=100` and financial disclaimer)
- `IBD_TESTING=1` mock mode working before any live connectivity
- `pytest` coverage ≥ 70%
