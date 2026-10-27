# Agent Production-Readiness Checklist

> **Authoritative model (SAP GDH AI Factory).** There is **no "L0–L10 pillar" model** — that framing
> was wrong. Readiness is gated by two ID-coded checklists from the `gdhaifactory-agentic-pipeline`:
> the **Quality Gate** and the **Code Review**. The full, verbatim checklists live in
> `docs/checklists/quality-gate-checklist.md` and `docs/checklists/code-review-checklist.md`.
> This file is the condensed sprint-gate reference for a new agent built from this starter.

## Quality Gate — 5 gates (run `agent-quality-gate`)

- **QG-SA · Static Analysis** — `py_compile` clean; ruff (E,F,W,I,B,S,A,ASYNC,TRY,C90) = 0;
  mypy (if present); bandit 0 High/Critical; no function > 50 lines; nesting ≤ 4.
- **QG-TE · Test Execution** — `tests/` + `conftest.py`; ≥ 1 unit + ≥ 1 integration file;
  `pytest --collect-only` clean; `pytest -m unit` green; coverage ≥ 70%.
- **QG-DA · Dependency Audit** — `pyproject.toml` valid; all deps version-constrained;
  pip-audit 0 Critical/High; lock file present; `requires-python` set; `a2a-sdk` + framework dep listed.
- **QG-AC · API Contract** — `build_agent_card` → `AgentCard` (name/description/url/version/skills);
  `A2AStarletteApplication`; `/health` → `{"status":"ok"}`; `AgentExecutor.execute(context, event_queue)`;
  `TaskUpdater` from `a2a.server.tasks`; config via pydantic `BaseSettings`; `/.well-known/agent-card.json`.
- **QG-LQ · LLM Quality** — LLM via `gen_ai_hub…init_llm`; temp ≤ 0.3 on routers; token budget env var;
  grounding instruction; input/output validation; no PII in prompts; prompt-injection boundary; retry policy.

**Pass criteria:** PASS = 0 Critical & ≤ 5 Major · CONDITIONAL = 0 Critical & 6–10 Major · FAIL = any Critical or > 10 Major.

## Code Review — 4 reviewer domains (run `agent-code-review`)

- **CR-AR · Architecture** — pattern adherence; no unreachable nodes / infinite loops; clear sub-agent
  separation; DataClient implements all CRUD; dependency injection (no global mutable state); HITL layer if writes.
- **CR-SR · Security** — no hardcoded secrets; secrets from env via Settings; auth middleware + scope checks;
  input-length validation; user input never concatenated into the system prompt; no eval/exec/pickle;
  CORS restricted in prod; TLS enforced; `.gitignore` excludes `.env`/`*.key`/`*.pem`/service-key JSON.
- **CR-A2 · A2A Compliance** — AgentCard schema valid + HTTPS url; `/.well-known/agent-card.json`;
  JSON-RPC 2.0; `message/send` (+ stream if declared); spec-correct task transitions; `updater.failed(...)`;
  `cancel()` implemented; `context.get_user_input()`; DataPart `kind:"data"`.
- **CR-PR · Performance** — no LLM calls for deterministic ops; server-side OData `$filter/$select/$top`;
  no N+1; all external calls async; no `time.sleep` in async; connection pooling; `recursion_limit` per pattern.

**Pass criteria:** PASS = 0 Critical & ≤ 8 Major · CONDITIONAL = 9–15 Major · FAIL = any Critical or > 15 Major.

---

**How to use:** build the agent, then run the Quality Gate and Code Review against the full checklists
in `docs/checklists/`. Record results in `docs/quality-gate-report.md` and `docs/code-review-report.md`.
Mark framework-gated checks `N/A` honestly when the agent uses a different (but valid) stack — do not
fake passes.
