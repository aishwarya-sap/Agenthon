# Agent Outcome Report — Procurement Bottleneck & Decision Agent
Generated: 2026-10-13 · Reframed to GDH AI Factory Quality-Gate / Code-Review standard: 2026-10-27
Build scope: full custom agent (advisory, read-only)

> **Governance note (2026-10-27):** this report was previously framed against a non-standard
> "L0–L10 pillar" model. That model does not exist in the official SAP GDH AI Factory standards.
> Production readiness is now tracked against the two authoritative checklists:
> **Quality Gate** → `docs/checklists/quality-gate-checklist.md` (report: `docs/quality-gate-report.md`)
> and **Code Review** → `docs/checklists/code-review-checklist.md` (report: `docs/code-review-report.md`).

---

## 1. What was built
- **Agent:** `procurement-bottleneck-agent` — detects supplier silence on critical-path POs across
  active projects, quantifies the downstream consequence, recalls similar past decisions, and
  recommends an action for Purchasing-HoD approval; every outcome captured as institutional memory.
- **Type:** deterministic tool/skill orchestration core + bounded LLM reasoning (not a LangGraph graph).
- **Build path:** pro-code (hand-built to the GDH AI Factory standard).
- **Runtime:** Starlette + A2A 0.3.0 on Cloud Foundry (us10); LLM via SAP AI Core (ChatLiteLLM).
- **Grounding:** S/4 OData (BAH sandbox) + RAG (HANA Vector, design) + institutional memory;
  project data via SAP PS or Excel/CSV.
- **Constraint:** advisory, **read-only** — no SAP business-object writes (ADR-0001).

## 2. Deliverables produced
| Deliverable | Status | Notes |
|---|---|---|
| Agent code | ✅ | `assets/procurement-bottleneck-agent/app/` — 17 modules, 13 tools, 3 skills |
| Specs | ✅ | `docs/specs/` (design-brief, functional, technical, rtm) |
| ADRs | ✅ | `docs/decisions/0001–0005` |
| Mock data (`IBD_TESTING=1`) | ✅ | `mcp-mock.json` + deterministic in-process tools |
| Demo UI (offline) | ✅ | `demo/index.html` — Daily Blockers dashboard + chat |
| Tests | ✅ | **134 tests passing, coverage ≥ 70%** |
| Deploy artifacts | ✅ | `manifest.yml`, `xs-security.json`, `.env.example` |
| Checklists + reports | ✅ | `docs/checklists/` + `docs/quality-gate-report.md` + `docs/code-review-report.md` |

## 3. Governance status (Quality Gate + Code Review)
Full detail in the two reports under `docs/`. Honest summary:

| Area | Status | Note |
|---|---|---|
| Test Execution (QG-TE) | ✅ PASS | 134 tests, conftest, unit + integration, coverage ≥ 70% |
| Security (CR-SR) | ✅ Strong | No hardcoded secrets; `.env` gitignored; advisory read-only; injection scan. 1 Major: CORS wildcard to restrict for prod |
| Performance (CR-PR) | ✅ Good | Server-side OData `$filter/$select/$top`; async I/O; bounded retries |
| Static Analysis (QG-SA) | ⚠ Not enforced | ruff/mypy/bandit not yet wired in CI |
| API Contract (QG-AC) / A2A (CR-A2) | ⚠ Divergent stack | Functional A2A (card, `message/send`, `/health`); not the a2a-sdk object model (ADR-0004) |
| Dependency (QG-DA) | ⚠ Conditional | Pins + `requirements.txt` lock present; no `pyproject.toml` |
| LLM Quality (QG-LQ) | ⚠ Partial | Low temp, grounding, input/output validation, no PII in prompts; uses ChatLiteLLM not `gen_ai_hub` |

**The material gaps are stack-alignment, not behavioural defects** — see the reports for the
per-check breakdown and the resolution path (a deferred, separately-authorized code migration).

## 4. Flagged items — tenant / follow-up
| Item | Issue | Remediation |
|---|---|---|
| CORS | `allow_origins=["*"]` in `main.py` | Restrict to Joule/BTP origin(s) before production |
| CI static analysis | ruff/mypy/bandit not in CI | Add `quality.yml` + `.pre-commit-config.yaml` |
| Live integration | validated on mock + BAH sandbox | Validate against Adarsh Tokyo S/4; flip `AGENT_AUTH_MODE`→ias, `ENABLE_WHOAMI`→off |
| Stack alignment | non-SDK A2A / no pyproject | Deferred code migration (out of current docs-only scope) |

## 5. Mock mode & demo status
| Item | Status |
|---|---|
| `IBD_TESTING=1 pytest` passes offline | ✅ 134 passed |
| Coverage ≥ 70% | ✅ |
| Demo UI runs offline | ✅ Daily Blockers + chat |
| Deployed demo on mock data (quota-locked) | ✅ AI Core reasoning still live |

## 6. Go / No-Go verdict
> **CONDITIONAL GO ⚠️**
>
> Functionally complete and working as an advisory, read-only build: 13 tools, 3 skills, 4-dimension
> consequence simulation, HITL approval gate, institutional memory, resilience (terminal quota
> handling), structured observability, indirect-injection gate, honest backend-failure handling —
> 134 passing tests, A2A + demo UI end-to-end, deployed and verified. Advisory-only enforced.
>
> **Production go-live remains conditional** on: restricting CORS, wiring static-analysis CI,
> live-tenant integration + sign-off, and (if a true checklist PASS is required) the deferred
> stack-alignment migration (a2a-sdk surface, `pyproject.toml`). None are behavioural defects.

## 7. Next steps
1. Restrict CORS and add ruff/mypy/bandit CI (quick, in-repo).
2. Validate against the Adarsh Tokyo S/4 landscape with IAS principal propagation.
3. If a literal Quality-Gate PASS is required, schedule the authorized code migration (ADR-0004 scope).
