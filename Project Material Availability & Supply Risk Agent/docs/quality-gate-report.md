# Quality Gate Report

Generated: 2026-10-27
Project: material-risk-agent
Overall: **PASS**

Checklist source: GDH AI Factory Quality Gate (`plugins/python-agent/skills/python-agent-dev/references/30-quality-gate-checklist.md`) — 5 gates. Pass criteria: 0 Critical, ≤5 Major.

## Summary

| Gate | Area | Status | Notes |
|------|------|--------|-------|
| QG-SA | Static Analysis | WARN | py_compile clean; ruff/mypy advisories only; some functions >50 lines (`agent.py`, `agent_executor.py`) |
| QG-TE | Test Execution | PASS | 175 tests pass; coverage 73% (≥70% threshold); `conftest.py` present; unit + integration tiers |
| QG-DA | Dependency Audit | PASS | `requirements.txt` pinned; `a2a-sdk[all]==0.3.22`, `pydantic-settings` present; no GPL/AGPL; 5 npm (UI) advisories tracked |
| QG-AC | A2A API Contract | PASS | `A2AStarletteApplication`, `/.well-known/agent-card.json` 200, `AgentExecutor.execute(context, event_queue)`, `TaskUpdater` lifecycle |
| QG-LQ | LLM Quality | PASS | LLM via AI Core / Gen AI Hub (ChatLiteLLM), temp 0.0, token budget + summarization @30k, `recursion_limit=15`, grounding + injection boundary in prompt |

**Total:** 5 gates | **Overall:** PASS | **Critical:** 0 | **Major:** 0 | **Minor/advisory:** see below.

## Findings

### Critical
No findings.

### Major
No findings.

### Minor (advisory — not blocking)

| ID | File | Finding | Fix |
|----|------|---------|-----|
| QG-SA-15 | agent.py, agent_executor.py | Some functions exceed 50 lines | Extract helpers during hardening |
| QG-LQ-04 | agent.py | System prompt is inline (not under `prompts/system/`) | Externalize prompts if migrating to the copier layout |
| QG-DA (UI) | assets/material-risk-ui | 5 npm advisories (1 high, 4 moderate) | `npm audit fix` in the UI before go-live |
| QG-TE | — | LLM/e2e paths skip unless `AICORE_CLIENT_ID` set | Run live smoke on tenant |

## Gate reference (what each gate checks)

- **QG-SA (Static Analysis):** py_compile, ruff (E/F/I/W/C90/UP/B/S/A/T20/N/TRY/ASYNC), mypy, bandit, function length ≤50, nesting ≤4, no magic numbers.
- **QG-TE (Test Execution):** `tests/` dir, `conftest.py`, unit + integration tests, pytest passes, coverage ≥70%.
- **QG-DA (Dependency Audit):** valid dep manifest, pinned deps, pip-audit (0 Critical/High), no GPL/AGPL, `a2a-sdk` present.
- **QG-AC (API Contract):** `build_agent_card`, AgentCard fields + skills, `A2AStarletteApplication`, well-known endpoint, executor contract, `TaskUpdater`.
- **QG-LQ (LLM Quality):** LLM via Gen AI Hub, low temp for routing, token budget, externalized prompts, grounding + prompt-injection boundary, `recursion_limit`.
