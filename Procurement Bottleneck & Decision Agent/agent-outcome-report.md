# Agent Outcome Report — Procurement Bottleneck & Decision Agent
Generated: 2026-10-13 · Scored against GDH APAC Agent Checklist v5 (10-pillar / 60-item): 2026-10-27
Build scope: full custom agent (advisory, read-only)

> **Governance note (2026-10-27):** production readiness is tracked against the authoritative
> **GDH APAC Agent Checklist v5** — the 10-pillar (L0-1 … L0-10), 60-item model. Checklist:
> `docs/checklists/agent-checklist-L0-L10.md`; per-pillar assessment for this agent:
> `docs/agent-checklist-assessment.md`. The pillar numbering is also reflected in the agent's
> `assets/procurement-bottleneck-agent/governance/` artifacts (e.g. `2.6`, `5.3`, `10.2`).

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
| Checklists + assessment | ✅ | `docs/checklists/agent-checklist-L0-L10.md` (v5) + `docs/agent-checklist-assessment.md` |

## 3. Governance status (v5 Agent Checklist — 10 pillars)
Full per-pillar detail in `docs/agent-checklist-assessment.md`. Honest summary:

| Pillar | Status | Note |
|---|---|---|
| L0-2 LLM Selection · L0-3 RAG · L0-4 Metering · L0-5 Responsible AI · L0-8 Perf · L0-10 Resilience | ✅ Covered | Backed by `governance/` artifacts (`2.6`, `2.7`, `3.3`, `4.5`, `4.6`, `5.2`, `5.3`, `5.5`, `5.7`, `8.4`, `10.2`, `10.3-10.5`). |
| L0-6 Dev & Deployment Standards | ✅ Covered (CI partial) | Mock-first, 134 tests ≥ 70%, CF deploy artifacts. Gap: ruff/mypy/bandit not yet wired in CI. |
| L0-1 Onboarding · L0-7 Release & Go-Live · L0-9 Data Grounding | ⚠ Partial | Specs + internal validation done; client-tenant go-live and HANA Cloud Vector persistence pending. |

**The open items are enablement/go-live steps, not behavioural defects** — see
`docs/agent-checklist-assessment.md` for the per-pillar breakdown and evidence.

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
3. Complete the remaining partial pillars (L0-7 go-live, L0-9 HANA Cloud persistence) per `docs/agent-checklist-assessment.md`.
