# Code Walkthrough — [ClientName] [Use Case] Agent

> Explains the code to the dev team that will own it. Written for developers. (SAP Agent solution-doc standard)
> This describes the starter-kit code **as actually implemented** (Starlette + the 3 SAP
> decorators). Rename placeholders with `./rename.sh` before handover.

## Repo structure
See the tree in `README.md`. Agent code lives under `assets/<agent-name>/app/`.

## Entry point
`python -m app` → `app/__main__.py` starts the Starlette server (default port 8080).
The CF `Procfile` and `manifest.yml` both use `python -m app`.

## Key files
| File | Role |
|---|---|
| `app/agent.py` | 3 SAP decorators (`@agent_model`, `@agent_config`, `@prompt_section`) + the 6-rule system prompt. `try/except ImportError` shim lets it run offline and on BTP. |
| `app/agent_card.py` | A2A AgentCard served at `/.well-known/agent.json`. `AgentSkill(id=...)` must match the skill id in `joule/.../functions/`. Declares `streaming: false`. |
| `app/agent_executor.py` | `run_turn()` executes one turn; `to_a2a_response()` shapes it into an A2A 0.3.0 **Task** (`kind:"task"`, `id`, `contextId`, `status.message.parts[]`, `artifacts[]`). |
| `app/main.py` | Starlette routes: `GET /.well-known/agent.json`, `POST /` (JSON-RPC `message/send`), `GET /health`. JWT read when `AGENT_AUTH_MODE` ≠ none/mock. |
| `app/config.py` | All thresholds as named constants from env; `is_mock_mode()`, `agent_auth_mode()`. |
| `app/mcp_providers/agw.py` | Tool boundary: mock branch (`IBD_TESTING=1`) vs live Agent Gateway branch. |
| `mcp-mock.json` | Offline mock data; covers in-scope tools + edge cases. Never calls SAP. |

> Not yet in the kit (add per engagement): `scripts/` EDMX pipeline (fetch → translate →
> register MCP servers) for live OData — a Phase 2 addition.

## Running locally
```bash
cp .env.example .env            # fill in values
IBD_TESTING=1 python -m app     # offline / mock mode — always start here
```

## Running against live SAP
```bash
# Set SAP connectivity vars in .env (Agent Gateway / Destination), IBD_TESTING=0
python -m app
```

## Deploying to BTP Cloud Foundry
```bash
cf login --sso
cf push                         # reads manifest.yml; VCAP_SERVICES injected automatically
```

## Environment variables
| Variable | Purpose | Local (`.env`) | CF |
|---|---|---|---|
| `AGENT_MODEL` | LLM model id | `sap/anthropic--claude-4-5-sonnet` | manifest.yml |
| `IBD_TESTING` | `1` = mock mode | `1` for local dev | `0` in production |
| `AGENT_AUTH_MODE` | `ias` / `xsuaa` / `none` | `none` for local | `ias` in production |
| `AGENT_PUBLIC_URL` | agent card URL | localhost | CF app URL |

## Tests
```bash
IBD_TESTING=1 pytest tests/ -v --cov=app --cov-report=term-missing
```
Coverage gate: ≥ 70% (enforced in `pytest.ini`) before any push to production.

## Logs
Structured JSON. Every entry: `correlation_id`, `tool_name`, `latency_ms`, `tokens_used`.
**No secrets or PII ever in logs.**

## Known limitations / open items
[INFER from gap flags in agent-outcome-report.md]
