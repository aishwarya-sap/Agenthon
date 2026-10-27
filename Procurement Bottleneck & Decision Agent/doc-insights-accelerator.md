# Insights & Accelerators — Adarsh Developers Procurement Bottleneck Agent

> **Purpose.** Captures novel patterns, reusable components, and gotchas from this engagement.
> After delivery, relevant items are promoted to `07-accelerators/` in Agent-PathToProd-main-3.

---

## Accelerators discovered

- **`sonar-project.properties` pattern for Python A2A agents** — see `assets/procurement-bottleneck-agent/sonar-project.properties`; covers app/ sources + tests/ + exclusion of demo/, eval/, .venv/
- **`.cfignore` pattern** — critical for Python buildpack: excludes `.venv/`, `__pycache__/`, `tests/`, `eval/`, `governance/` from CF staging; without it, upload can be 100s MB and buildpack can find local venv before its own
- **VCAP_SERVICES → env var mapping at module top** — parse `VCAP_SERVICES` in `main.py` BEFORE any AI framework import; `os.environ.setdefault` so CF-bound creds don't overwrite local `.env` values
- **IBD_TESTING flag pattern** — `config.is_mock_mode()` dispatched in `mcp_tools.py::get_mcp_tools()`; conftest.py sets it automatically so unit tests never need network
- **Decorator import shim** — `try/except ImportError` around `sap_cloud_sdk.agent_decorators` with no-op fallbacks lets the same `agent.py` run offline (tests) and in production (real decorators) without branching
- **TOKEN_BUDGET_PER_RUN as a named constant** — putting the ceiling in `config.py` (not the LLM call) makes it easy to find for governance audits and LLM Calculator (L0-4.1)
- **DAS service key discovery** — `INS-AI-GLOBAL-JOU-01` instance was found in the DEV space (not the same space as the CF agent); `cf create-service-key` works on any instance you have SpaceDeveloper on

## SAP gotchas hit

- **A2A `message/send` must return a Task, not an `artifact-update`** — Joule BYOA calls the non-streaming `message/send` method (agent card `streaming: false`). The response `result` must be a conformant A2A 0.3.0 **Task**: top-level `kind: "task"`, `id` (taskId), `contextId`, `status.state` + `status.message.parts[].text`, and `artifacts[].parts[].text`. Joule's capability function reads the reply from `result.body.status.message.parts[0].text` and persists `result.body.id`/`result.body.contextId` for multi-turn. Returning a streaming-event shape (`kind: "artifact-update"`, singular `artifact`, no `status.message`) compiles and deploys but renders **blank** in Joule and breaks multi-turn/HITL. Fix lives in `agent_executor.py::to_a2a_response`.
- **Joule capability bundle minimum schema versions** — `capability.sapdas.yaml` needs `schema_version: 3.28.0` (3.27.0 and below reject the `agent-request` BYOA action); `da.sapdas.yaml` needs `schema_version: 1.4.0` with `capabilities[].name` + `.folder` set. `capability_context.yaml` (declaring `contextId`/`taskId`) is **mandatory** whenever scenarios reference `$capability_context` — its absence is a hard compile error, not a warning. `functions/` and `scenarios/` must live **inside** the capability folder, not at the bundle root.
- **`joule login` AUTH_FETCH_TOKEN_FAILED** — not a credentials problem; requires IAS App2App `Cli2Joule` dependency configured in the IAS tenant. No `--app-tid` flag combination fixes this. Only resolution: IAS admin configures the dependency in `an46vc4ar.accounts.ondemand.com/admin`
- **BTP Destination Cockpit UI down across all subaccounts** — workaround: use the Destination Service REST API directly (`POST /destination-configuration/v1/subaccountDestinations`); requires binding from `tcc-destination-service` (destination, lite plan) to get auth URL + credentials
- **`cf push` without `manifest.yml` in current directory fails** — always cd to the asset folder containing `manifest.yml` before pushing; or use `-f <manifest-path> -p <app-path>`
- **zsh `!` history expansion breaks `cf login --clientid` flags** — clientid strings containing `!b` (e.g. `sb-das-designer!b302615|das-application!b170816`) expand under zsh; use interactive prompts or wrap in single quotes
- **`@sap/joule-cli` 404s on npm** — correct package is `@sap/joule-studio-cli` (v2.0.4); the old `@sap/joule-cli` name is deprecated
- **`asset.yaml` API version inconsistency** — procurement agent uses `com.sap.ai/v1`; material risk agent uses `asset.sap/v1`; `asset.sap/v1` is the newer standard; both deploy but use `asset.sap/v1` for new agents
- **CF app `health-check-http-endpoint` on `/.well-known/agent.json`** — using the agent card as the health target means CF correctly validates the app is serving valid JSON before marking it healthy, not just TCP-open

## Architecture decisions made

| Decision | Options considered | Chosen | Reason |
|---|---|---|---|
| LLM call count | ReAct loop / 2 fixed calls | 2 fixed calls | Deterministic simulation = zero tokens; bounded cost; fully testable offline |
| Write actions | Full write / Advisory-only | Advisory-only | Engagement constraint C-01; reduces risk surface; HITL is the only path to side effects |
| HITL implementation | External SPA workflow / In-agent gate | In-agent keyword gate | SPA not in scope for Sprint 1–2; keyword gate unblocks demo; SPA is a Sprint 4 upgrade path |
| Grounding | KG / Document Grounding / OData | OData (+ institutional memory) | Flat transactional data (PO/PR/GRN) routes to OData per cookbook Part 0.0; KG not required |
| Chat UI | Separate Node.js app / Python served | Python served (same process) | Single CF app simpler for Sprint 1; material risk agent uses separate Node.js as upgrade path |
| CF memory | 256M / 512M / 1G | 512M | LiteLLM + LangChain + all 13 tools fit in 512M; material risk agent uses 1G for larger dependency tree |

## What to feed back to Golden Path repo

| What | File to update | Section |
|---|---|---|
| `.cfignore` template | `06-templates/` or `07-accelerators/` | Add as `cfignore-python-agent.md` |
| `joule login` IAS blocker + resolution steps | `02-build-guide/joule-skill-recipe.md` | Add prerequisite checklist |
| DAS service discovery (DEV space, not same space as CF app) | `05-deployment/cf-deployment-guide.md` | Add DAS service key section |
| Destination API workaround (Cockpit down) | `05-deployment/cf-deployment-guide.md` | Add REST API fallback section |

## What to feed back to Common Repo CLAUDE.md

- §8 Gap Flags: add "Joule CLI `AUTH_FETCH_TOKEN_FAILED` = IAS App2App Cli2Joule not configured — escalate to IAS admin BEFORE any Joule CLI work"
- §10 Quick-Reference: add `DAS_API_URL`, `DAS_AUTH_URL` pattern from service key; note they live in DEV space, not the same CF space as the agent
