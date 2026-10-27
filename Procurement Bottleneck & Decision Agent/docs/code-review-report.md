# Code Review Report — Procurement Bottleneck & Decision Agent

Assessed against `docs/checklists/code-review-checklist.md` (authoritative GDH AI Factory Code
Review: 4 reviewer domains). `N/A (stack)` = check assumes the LangGraph/a2a-sdk copier stack this
agent deliberately does not use (ADR-0004); it is an architecture divergence, not a defect.

## Pre-pass (deterministic)
No hardcoded credentials found in `app/`; no `eval`/`exec`/`__import__`; no `pickle` on untrusted
data; `.gitignore` excludes `.env`/`*.env` (keeps `.env.example`). Secrets read from env only.

## Reviewer verdicts

| Reviewer | Verdict | Note |
|---|---|---|
| Architecture (CR-AR) | ✅ Sound (non-LangGraph) | Clean single-agent deterministic orchestration; LangGraph-specific checks N/A. |
| Security (CR-SR) | ⚠ 1 Major | Strong overall; CORS wildcard to tighten for prod. |
| A2A Compliance (CR-A2) | ⚠ Partial | Functional A2A (agent card, message/send, task states); not the a2a-sdk object model. |
| Performance (CR-PR) | ✅ Good | Server-side OData filtering, async I/O, bounded retries. |

**Overall:** 0 Critical, 1 Major (CORS), remaining items are stack-alignment (N/A) or Minor. Strong
code-health posture; A2A/architecture items reflect the deliberate non-SDK stack.

## Findings resolved / passing

### Architecture (CR-AR)
- ✅ CR-AR-02: clear separation — orchestration (`agent.py`), skills (`skills.py`/`simulation.py`),
  data (`s4_client.py`/`project_data.py`), resilience, observability, HITL are distinct modules.
- N/A (stack): CR-AR-01/03..10/17..19/30..32 — StateGraph nodes/edges/`create_agent`/checkpointer/
  middleware (no LangGraph graph; routing is regex intent + LLM composition).
- ✅ CR-AR-14: HITL layer present (`hitl.py`) with approval keywords + action classification.

### Security (CR-SR)
- ✅ CR-SR-01/02/08/09: no hardcoded secrets; env-only config; no eval/exec; no untrusted pickle.
- ✅ CR-SR-03: auth at the A2A boundary (`auth_ias.py`; `AGENT_AUTH_MODE` ias/xsuaa/none-dev).
- ✅ CR-SR-06: user input not concatenated into the system prompt; passed as the question.
- ✅ CR-SR-07/28: tool output sanitised; retrieved rows injection-scanned (`sanitize.py`).
- ✅ CR-SR-18: `.gitignore` excludes `.env`/`*.env`.
- ⚠ **CR-SR-11 (Major): CORS `allow_origins=["*"]`** in `app/main.py`. Acceptable for the demo;
  restrict to the Joule/BTP origin(s) before production.
- ✅ CR-SR-17: no `debug=True` default; dev-only flags (`ENABLE_WHOAMI`, `AGENT_AUTH_MODE=none`)
  documented as off-for-prod.

### A2A Compliance (CR-A2)
- ✅ CR-A2-01/03/04: AgentCard has name/description/url/version + skills; `/.well-known/agent.json` served.
- ✅ CR-A2-02: deployed URL is HTTPS (`*.hana.ondemand.com`).
- ✅ CR-A2-05/06: JSON-RPC 2.0 `message/send` supported; status/message parts returned.
- ✅ CR-A2-16: `/health` returns `{"status":"ok"}`.
- N/A (stack): CR-A2-08..15 TaskUpdater/`context.get_user_input()`/DataPart `kind` — custom JSON-RPC
  implementation rather than the a2a-sdk object model.

### Performance (CR-PR)
- ✅ CR-PR-07/08/09: OData reads use `$filter`/`$select`/`$top`.
- ✅ CR-PR-11/12/16: async `httpx.AsyncClient`; no `time.sleep` in async; client reused per call scope.
- ✅ CR-PR-01/02: deterministic ops (silence, simulation) are not LLM calls; intent routing is regex-first.

## Remaining (advisory, non-blocking)
1. **CR-SR-11** — restrict CORS for production (Major).
2. **Stack alignment** — adopt the a2a-sdk object model + LangGraph middleware patterns if/when the
   deferred code migration is authorized (out of current docs-only scope).
3. Wire ruff/mypy/bandit in CI (mirrors the Quality-Gate Static-Analysis gap).

## Validation
Behaviour verified by running the deployed endpoint this engagement (dashboard blocker, delivery-
performance answer, honest backend-failure, concise LLM reasoning). 134 tests pass, coverage ≥ 70%.
