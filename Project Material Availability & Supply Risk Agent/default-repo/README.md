# Default Repo — Agent Starter Template

Generic, reusable scaffold for any SAP A2A agent engagement. Share this repo with the
client as the starting point for their build.

---

## What's in this repo

```
default-repo/
├── assets/agent-starter-kit/         ← Python A2A agent (rename to your agent name)
│   ├── app/                          ← agent code (main, agent, graph, config, s4_client)
│   ├── xs-security.json              ← XSUAA scopes/roles
│   ├── Procfile                      ← CF start command (web: python app/_boot.py)
│   ├── runtime.txt                   ← pinned Python (full patch version)
│   └── requirements.txt
├── assets/agent-starter-kit-ui/      ← Joule-style chat UI
├── agent_checklist_L0_to_L10.md      ← governance checklist
├── mta.yaml                          ← CF deployment descriptor (MTA / mtar)
├── deploy.sh                         ← build + deploy helper (mbt build → cf deploy)
└── .gitignore
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

## Deploy to Cloud Foundry (MTA / mtar)

Deployment uses the Multi-Target Application (MTA) approach — `mbt build` produces an
`.mtar` archive, then `cf deploy` pushes every module in one transaction. Routes are
assigned automatically from your CF domain via `mta.yaml`'s `${default-url}`.

Prerequisites: `cf` CLI, [`mbt`](https://github.com/SAP/cloud-mta-build-tool), the
MultiApps plugin (`cf install-plugin multiapps`), and a live session (`cf login --sso`).

```bash
# From the default-repo/ root (runs preflight checks, then builds + deploys):
./deploy.sh

# Or manually:
mbt build
cf deploy mta_archives/*.mtar --strategy rolling
```

`mta.yaml` binds two managed services automatically: the **Destination Service**
(`agent-destination`) and **XSUAA** (`agent-xsuaa`, scopes from `xs-security.json`).
It deliberately does **not** bind AI Core as a service.

After deploy, create the backend BTP Destinations in the BTP Cockpit (Connectivity →
Destinations) — they can't live in `mta.yaml` because they reference credentials outside CF:

- **`aicore`** — AI Core (Type HTTP, OAuth2ClientCredentials). The agent resolves the LLM
  through this destination at runtime. Until it exists, the agent runs in mock mode (`IBD_TESTING=1`).
- **S/4HANA** (e.g. `S4_AGENT_DEV`) — one destination per environment, resolved by `S4_DESTINATION`.

Use **Check Connection** on each destination — it must return HTTP 200 before the agent can use it.

---

## Customise for your domain

- Rename `assets/agent-starter-kit/` to your agent name (update `mta.yaml` module name + `path` to match)
- Edit `assets/agent-starter-kit/app/agent.py` → replace the agent name and workflow in `get_system_prompt()`
- Update the agent / UI module names and `ID` in `mta.yaml`

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
committed file.

---

## Governance

Review the [Agent Checklist](agent_checklist_L0_to_L10.md) periodically through the build.

Mandatory rules enforced:
- Exactly 3 `@agent_*` decorators in `agent.py`
- 6 MANDATORY RULES in every system prompt (incl. `top=100` and financial disclaimer)
- `IBD_TESTING=1` mock mode working before any live connectivity
- `pytest` coverage ≥ 70%
