# Design Rationale — SAP A2A Agent Starter Kit

> **Purpose.** Every file and convention in this starter kit exists for a reason that
> traces back to an authority — the SAP Agent cookbook, the A2A specification, a
> governance control, or a lesson learned on a real engagement. This document is that
> trace. Before you delete, replace, or "simplify" anything here, read why it's here.
>
> **Audience.** Developers using this starter kit to build a new SAP A2A agent.
>
> **If a row says "re-verify per engagement," do not trust it blindly** — it was true
> when captured and must be confirmed against your target tenant.

---

## Grounding sources (the authorities this kit is built on)

| Tag | Source | What it governs |
|---|---|---|
| **CB** | SAP Agent engineering standards (see [`CLAUDE.md`](CLAUDE.md)) | Architecture principles, L0–L10 governance, repo structure |
| **GP** | SAP Agent Golden Path | Engineering blueprint, developer toolkit, cost model |
| **A2A** | A2A protocol 0.3.0 specification | `message/send` request/response shape, Task object, agent card |
| **INS** | [`doc-insights-accelerator.md`](doc-insights-accelerator.md) (shipped in this repo) | Joule schema minimums + A2A Task shape, empirically discovered and deployed |
| **REF** | A deployed, production-tested SAP A2A agent | The reference implementation (131 tests) that every pattern here is extracted from |

> **Why ground in INS and REF, not just SAP docs?** The Joule schema versions and the
> exact A2A Task shape are **not** stated as a single number in the public cookbook — they
> were discovered by deploying a real agent and reading the compiler errors. INS records
> what actually worked; REF is the agent it worked on. That is stronger grounding than a
> remembered version number, which is why those two sources exist and why the schema
> numbers below carry a **re-verify** flag.

---

## Structural decisions

### Why `assets/<agent-name>/` instead of the cookbook's flat `agent/` layout

**CB §5** shows a flat `agent/` folder for a single-agent client project. This starter kit
nests the agent under `assets/` instead.

**Grounded in:** REF — the reference agent ships a top-level `solution.yaml` that points at
`assets/<agent>/`, the layout SAP Joule 2.0 / Build expects for a deployable **solution** that
can hold more than one asset. A client engagement often grows a second asset (a chat UI, a
second agent). Starting in `assets/` means that growth is adding a folder, not restructuring
the repo. **Divergence from CB §5 is deliberate and is the Joule-2.0-ready layout from CB §2.1
("switchable-code").**

### Why the top-level files are split the way they are

| File | Why it's here | Grounded in |
|---|---|---|
| `README.md` | Technical readme: run, test, deploy, rename | CB §5 (README mandated for every project) |
| `AGENT_CHECKLIST.md` | The L0–L10 governance gate, condensed to a per-engagement tick-list | CB §4 (70 controls across 10 pillars; every item marked ✅/⚠️/❌/⏭️) |
| `DESIGN_RATIONALE.md` | This file — so the kit is not cargo-culted | GP (toolkit principle: a handover must explain *why*, not just *what*) |
| `rename.sh` | One-command rename; a manual rename misses `xsappname`, `namespace`, `system_alias` | INS (rename is error-prone — six files reference the name) |
| `.github/workflows/ci.yml.example` | CI gate from day one; `.example` so teams opt in consciously | CB §4 L0-6 (CI/CD + structured logs) |

---

## Per-file rationale — agent code (`app/`)

| File | Why it's here | Grounded in |
|---|---|---|
| `agent.py` | Exactly **3 decorators** (`@agent_model`, `@agent_config`, `@prompt_section`) + a **6-rule** system prompt. The `try/except ImportError` shim lets the same file run offline (tests) and on BTP (real SDK). | CB §4 L0-3 (3 decorators, 6 mandatory rules); REF (shim pattern) |
| `agent_card.py` | Serves `/.well-known/agent.json`. `streaming: false` is declared here, which is **why** the response must be a Task and not a stream event (see below). | A2A (agent card discovery); CB §4 L0-6 (`a2aSkillId` must match the card) |
| `agent_executor.py` | `to_a2a_response()` returns a conformant A2A 0.3.0 **Task**: `kind:"task"`, `id`, `contextId`, `status.message.parts[]`, `artifacts[]`. | A2A; **INS** — returning the streaming shape (`kind:"artifact-update"`) compiles and deploys but renders **blank** in Joule. This is the single most expensive mistake to make and the reason this kit exists. |
| `main.py` | Starlette routes: `GET /.well-known/agent.json`, `POST /` (JSON-RPC `message/send`), `GET /health`. JWT is read when `AGENT_AUTH_MODE` is not `none`/`mock`, with a Sprint-3 hardening TODO. | A2A (`message/send` is the non-streaming method Joule calls); CB §2.2 (JWT at the A2A boundary before any tool runs) |
| `config.py` | Every threshold is a **named constant** read from env — `TOKEN_BUDGET_PER_RUN`, `RAG_SIMILARITY_GATE`, `CIRCUIT_BREAKER_THRESHOLD`, `is_mock_mode()`, `agent_auth_mode()`. | CB §4 L0-4 (budget ceiling findable for metering audits); CB §2.2 (auth mode not hardcoded) |
| `mcp_providers/agw.py` | One boundary with two branches: mock (`IBD_TESTING=1`) and live (Agent Gateway). Business code never knows which is active. | CB §2.1 (mock-first always); CB §2.1 (endorsed: A2A via Agent Gateway, no community MCP wrappers) |

---

## Per-file rationale — Joule BYOA bundle (`joule/`)

> **All four of the facts below are flagged `re-verify`** against the target Joule tenant
> with `joule status` before Sprint 3 deploy. They are what worked on this engagement (INS),
> not a permanent SAP guarantee.

| File / fact | Why it's here | Grounded in |
|---|---|---|
| `da.sapdas.yaml` → `schema_version: 1.4.0` | Descriptor needs 1.4.0 with `capabilities[].name` + `.folder`. 1.2.0 omits `name` and fails. | INS (re-verify) |
| `capability.sapdas.yaml` → `schema_version: 3.28.0` | 3.28.0 is the minimum that accepts the `agent-request` (BYOA) action; 3.27.0 and below silently reject it. | INS (re-verify) |
| `capability.sapdas.yaml` → `namespace: joule.ext` | Any other namespace fails deploy (error 5013/5014). | INS (re-verify) |
| `capability_context.yaml` (present) | Mandatory whenever a scenario references `$capability_context`. Its **absence is a hard compile error**, not a warning. Declares `contextId` + `taskId`. | INS (re-verify) |
| `functions/call_agent.yaml` | Multi-turn: `body` is null on turn 1, carries `contextId`/`taskId` on follow-ups; reads the reply from `result.body.status.message.parts[0].text`. | A2A (multi-turn task resumption); INS (exact body path) |
| `scenarios/invoke_agent.yaml` | Intent-matching shell. `capability_context` persists ids across turns; `target.parameters` feeds them back in. | INS (context wiring) |
| `functions/` + `scenarios/` **inside** the capability folder | Not at bundle root — root placement fails to compile. | INS (re-verify) |

---

## Per-file rationale — deploy & config

| File | Why it's here | Grounded in |
|---|---|---|
| `manifest.yml` | CF descriptor. `health-check-http-endpoint: /.well-known/agent.json` makes CF verify the app serves valid JSON before marking it healthy — not just TCP-open. `memory: 512M` with a scale-to-1G note. | REF (health target); GP (CF sizing) |
| `Procfile` | `web: python -m app` — explicit start command so the Python buildpack never has to guess. | GP (CF Python buildpack) |
| `runtime.txt` | `python-3.10.14` with a note that 3.11/3.12 are buildpack-supported and 3.10 is EOL Oct 2026. | GP; honest EOL flag |
| `xs-security.json` | XSUAA scopes + roles + an `oauth2-configuration.redirect-uris` placeholder for UI/OAuth flows. | CB §4 L0-4 (correct scopes); REF |
| `asset.yaml` | ORD descriptor (`asset.sap/v1`) so the agent is discoverable and the Joule 2.0 migration is an infra swap. | CB §2.1 + L0-10 (`asset.yaml` ORD IDs = Joule 2.0 readiness) |
| `.env.example` | All variable **names**, zero values. `AGENT_AUTH_MODE=ias` by default. | CB §2.2 (secrets never committed); auth is production-first, not bolted on |
| `.cfignore` / `.gitignore` | Keep `.venv`, `tests/`, `__pycache__`, `.env`, `.coverage` out of CF staging and git. | REF (a missing `.cfignore` makes the upload 100s of MB and the buildpack can find the local venv) |

---

## Per-file rationale — testing & governance

| File | Why it's here | Grounded in |
|---|---|---|
| `tests/test_smoke.py` | 6 offline tests: health, agent card at `/.well-known/`, A2A **Task** shape, mock tool list, known/unknown tool call. | CB §4 L0-2 (offline smoke tests, edge cases) |
| `conftest.py` | Forces `IBD_TESTING=1` + `AGENT_AUTH_MODE=mock` for every test run, so tests never touch the network. | CB §2.1 (mock-first) |
| `pytest.ini` | `--cov=app --cov-fail-under=70` — the coverage gate is enforced by the runner, not the honor system. | CB §4 L0-2 (≥ coverage gate) |
| `sonar-project.properties` | SonarQube wired with a quality gate; business logic only (demo/eval/governance excluded). | CB §4 L0-1 (SonarQube configured) |
| `mcp-mock.json` | Deterministic offline fixtures (`echo_tool`, `get_metadata`) so tests are reproducible and Sprint 1 demos need zero SAP creds. | CB §2.1 (mock-first); REF |
| `AGENT_CHECKLIST.md` | The L0–L10 gate as a tick-list; no control is silently skipped. | CB §1 (every L0–L10 item marked with a reason) + §4 |

---

## Decisions we deliberately did NOT make (scope boundaries)

| Not included | Why not | Grounded in |
|---|---|---|
| A live LLM call in `_live_turn()` | The kit is domain-agnostic; the LLM loop is engagement-specific. Left as a TODO with the 4 steps spelled out. | CB §6 (never fabricate [CLIENT INPUT]) |
| Real tools in `mcp-mock.json` | Tools are per-domain. Two generic tools prove the wiring; teams replace them. | — |
| Hardcoded CF region/URL | Region differs per client (us10, ap20…). URL comes from `AGENT_PUBLIC_URL`. | REF (region is a per-engagement value) |
| JWKS/aud/iss/exp JWT hardening | The hooks are in place; full validation is a Sprint 3 security task, flagged in `main.py`. | CB §2.2 + L0-5; honest Sprint-3 boundary |
| Business-object writes (POST/PATCH/DELETE) | Default posture is advisory/read-only; writes are an explicit per-engagement decision. | CB §2.2 (no ungoverned write access) |

---

## What you MUST re-verify per engagement

1. **Joule schema versions** (`1.4.0`, `3.28.0`, `joule.ext`) — run `joule status` against the
   target tenant. These are INS-captured, not permanent SAP constants.
2. **AI Core model names** (`sap/anthropic--claude-*`) — confirm against the client's AI Core
   entitlement; availability varies by region and contract.
3. **CF region + org/space** — set in `manifest.yml`, `asset.yaml`, `xs-security.json`.
4. **IAS App2App `Cli2Joule`** — must be configured by the IAS admin before `joule login`
   works; no CLI flag fixes `AUTH_FETCH_TOKEN_FAILED`.
5. **On-prem vs cloud OData service names** — `API_*` (cloud) vs `OP_*` (on-prem) differ.

> Rule of thumb from CB §6: fields marked **[VERIFY]** are placeholders that need
> confirmation from the client or SAP — never ship them as fact.
