# Agent Checklist Assessment — Procurement Bottleneck & Decision Agent

Scored against the authoritative **GDH APAC Agent Checklist (v5)** — the 10-pillar / 60-item model in
[`docs/checklists/agent-checklist-L0-L10.md`](checklists/agent-checklist-L0-L10.md). Honest status;
evidence points to the real artifacts in `assets/procurement-bottleneck-agent/governance/`, the test
suite, and the code.

**Headline:** advisory, **read-only** agent · mock-first (`IBD_TESTING=1`) · 134 tests, coverage ≥ 70%
· SAP AI Core (`ChatLiteLLM`, `sap/anthropic--claude-4.5-sonnet`) · A2A 0.3.0 on Cloud Foundry.

> Note on stack: this agent runs on raw Starlette + a custom JSON-RPC surface and a LangGraph seam,
> rather than the `a2a-sdk` `A2AStarletteApplication` shape. That is a deliberate architecture choice
> documented in `../CODEBASE_ALIGNMENT.md` and ADR-0004 — it is orthogonal to the pillars below.

## Per-pillar status

| Pillar | Status | Evidence |
|---|---|---|
| **L0-1 · AI Feature & Agent Onboarding Governance** | Documented | `docs/specs/design-brief.md` (persona, pain, advisory scope); feature classified *agentic*. Formal Idea2Value/ESCE sign-off is client-side. |
| **L0-2 · LLM Selection & Benchmarking** | Covered | `governance/2.6-frontier-model-justification.md`, `2.7-model-update-retraining-governance.md`; model pinned via AI Core (ADR-0003). |
| **L0-3 · Document Grounding & RAG Quality** | Covered | `governance/3.3-rag-evaluation-scorecard.md`; `eval/rag_eval.py` + `eval/rag_scorecard.json` + gold set. |
| **L0-4 · AI Commercialization & Metering** | Covered (docs) | `governance/4.5-customer-token-consumption-forecast.md`, `4.6-cost-per-transaction-baseline.md`; `TOKEN_BUDGET_PER_RUN` in `config.py`. |
| **L0-5 · Responsible AI & Safety Validation** | Covered | `governance/5.2-bias-fairness-assessment.md`, `5.3-redteam-report.md`, `5.5-gdpr-euaiact-compliance.md`, `5.7-ip-data-ownership-governance.md`; `app/sanitize.py` injection boundary; `tests/test_redteam.py`, `tests/test_sanitize.py`; advisory read-only (never writes SAP). |
| **L0-6 · Agent Development & Deployment Standards** | Covered (CI partial) | Mock-first `IBD_TESTING`; 6 mandatory prompt rules; 134 tests ≥ 70%; CF entry (`Procfile`/`gunicorn.conf.py`/`manifest.yml`); `governance/6.1-6.2-agent-builder-exception.md`. Gap: ruff/mypy/bandit not yet wired in CI. |
| **L0-7 · End-to-End Release Validation & Go-Live** | Partial | `tests/integration/`, `/health`, agent card, A2A `message/send` validated; live BAH connectivity (ADR-0005). Client-tenant go-live pending. |
| **L0-8 · Agent Design Classification & Performance Engineering** | Covered | `governance/8.4-performance-slas.md`; deterministic skills + gated LLM reasoning; LangGraph seam with `recursion_limit`. |
| **L0-9 · Knowledge & Data Grounding Strategy** | Partial | Live S/4HANA OData grounding (`app/s4_client.py`, `app/project_data.py`) + decision recall (`app/memory.py`). HANA Cloud Vector Engine recall is a **placeholder** (see HANA persistence seam). |
| **L0-10 · Dependency & Change Resilience** | Covered | `governance/10.2-dependency-map.md`, `10.3-10.4-10.5-drift-detection-design.md`; `app/resilience.py` (retry / circuit-breaker / quota-terminal); pinned `requirements.txt`. |

## Open items (honest)
- **Static-analysis CI (L0-6):** wire ruff + mypy + bandit into a workflow + pre-commit.
- **HANA Cloud persistence (L0-9):** the durable audit table + Vector Engine recall is a placeholder
  (`MEMORY_BACKEND=hana` seam) — implement once the client provisions HANA Cloud (see
  `docs/ADARSH_CLIENT_PREREQUISITES.md` + `docs/internal/DATA_READINESS_QUESTIONNAIRE.md`).
- **Client go-live (L0-7):** final E2E on the Adarsh tenant with IAS principal propagation.
