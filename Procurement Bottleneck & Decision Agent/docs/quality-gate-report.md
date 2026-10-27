# Quality Gate Report — Procurement Bottleneck & Decision Agent

Assessed against `docs/checklists/quality-gate-checklist.md` (authoritative GDH AI Factory Quality
Gate: 5 gates). Honest assessment — `N/A (stack)` means the check assumes the copier-template stack
(a2a-sdk / `A2AStarletteApplication` / `gen_ai_hub` / pydantic-`BaseSettings`) that this agent
deliberately does **not** use (see ADR-0004); it is an architecture divergence, not a defect.

## Summary

| Gate | Verdict | Note |
|---|---|---|
| 1 — Static Analysis (QG-SA) | ⚠ Not enforced | Code is clean and typed-by-convention, but ruff/mypy/bandit are not yet wired in CI. Gap, not a failure of code. |
| 2 — Test Execution (QG-TE) | ✅ PASS | 114 test fns / 134 tests, `conftest.py`, unit + integration dirs, coverage ≥ 70%. |
| 3 — Dependency Audit (QG-DA) | ⚠ CONDITIONAL | Pins present; `requirements.txt` lock satisfies QG-DA-06. No `pyproject.toml` (QG-DA-01) and no `a2a-sdk` (QG-DA-08, stack). |
| 4 — API Contract (QG-AC) | ✗ FAIL (literal) | Raw Starlette + custom JSON-RPC, not `A2AStarletteApplication`/`AgentExecutor` SDK. Contract works; it just isn't the SDK shape the gate asserts. |
| 5 — LLM Quality (QG-LQ) | ⚠ Partial | Stack-agnostic items pass; `gen_ai_hub` item (QG-LQ-01) is N/A (uses ChatLiteLLM via AI Core). |

**Overall:** Against the *literal* checklist → **FAIL** (Gate-4 criticals are triggered purely by the
non-SDK A2A stack). On *stack-agnostic quality* (tests, security, grounding, resilience) → strong.
The gaps are architectural-alignment items, not behavioural defects.

## Findings

### Critical
- **QG-AC-05 / QG-AC-07..09 — not the a2a-sdk surface.** Uses `Starlette(routes=…)` + a custom
  JSON-RPC handler instead of `A2AStarletteApplication` + `AgentExecutor`/`TaskUpdater`. *Resolution
  path:* adopt a2a-sdk in a future, deliberate refactor (explicitly out of current scope per the
  approved plan). Functionally compliant today (`message/send`, agent card, task states).
- **QG-DA-01 — no `pyproject.toml`.** Deps live in `requirements.txt` (+`requirements-test.txt`).
  *Resolution:* add `pyproject.toml` when the code migration is authorized.

### Major
- **QG-SA — static-analysis tools not in CI.** Add ruff (E,F,W,I,B,S,A,ASYNC,TRY,C90) + mypy + bandit
  to a `quality.yml` workflow and a `.pre-commit-config.yaml`.
- **QG-AC-10/11 — config is `os.environ` constants, not pydantic `BaseSettings`.** Works and is
  centralised in `config.py`; not the asserted shape.
- **QG-LQ-01 — LLM via `langchain_litellm.ChatLiteLLM` (AI Core), not `gen_ai_hub.init_llm`.**
  Deliberate (ADR-0003). N/A to the literal check.

### Minor / Passing highlights
- ✅ QG-TE-01..09: tests, conftest, unit+integration, `pytest --collect-only` clean, coverage ≥ 70%.
- ✅ QG-DA-02/06/07: version constraints, lock file, `requires-python` (via runtime).
- ✅ QG-AC-06/15: `/health` returns `{"status":"ok"}`; `/.well-known/agent.json` served.
- ✅ QG-LQ-02/05/06/07/11/12: low temperature on reasoning, grounding instruction, input/output
  validation, no PII in prompts, prompt-injection boundary (`sanitize.py`).

## How to reach PASS
The behaviour is production-quality; the gate failures are all *stack-alignment*. To pass the literal
gate, the authorized follow-up is the code migration deferred in the approved plan (a2a-sdk surface,
`pyproject.toml`, pydantic-settings, ruff/mypy CI). Tracked, not done here (docs-only scope).
