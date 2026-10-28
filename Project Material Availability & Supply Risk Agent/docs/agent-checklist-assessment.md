# Agent Checklist Assessment — Project Material Availability & Supply Risk Agent

Scored against the authoritative **agent build checklist (v5)** — the  model in
[`docs/checklists/agent-checklist-L0-L10.md`](checklists/agent-checklist-L0-L10.md). Honest status;
evidence points to the real artifacts in `assets/material-risk-agent/governance/`, the test suite,
and the code.

**Headline:** advisory, **read-only** agent · mock-first (`IBD_TESTING=1`) · 175 tests, coverage 73%
· SAP AI Core (`ChatLiteLLM` via Gen AI Hub) · A2A 0.3.0 (`a2a-sdk` / `A2AStarletteApplication`) on
Cloud Foundry · Joule-style chat UI.

> Note on stack: this agent uses the `a2a-sdk` `A2AStarletteApplication` + `AgentExecutor` surface and
> an `app/domain/` + `app/mcp_providers/` module layout (no LangGraph graph dir). The divergence from
> the Procurement agent's flat + `app/graph/` layout is deliberate and documented in
> `../CODEBASE_ALIGNMENT.md` — it is orthogonal to the pillars below.

## Per-pillar status

| Pillar | Status | Evidence |
|---|---|---|
| **L0-1 · AI Feature & Agent Onboarding Governance** | Documented | `docs/specs/design-brief.md`; feature classified *agentic*. Formal Idea2Value/ESCE sign-off is client-side. |
| **L0-2 · LLM Selection & Benchmarking** | Covered | `governance/2.6-frontier-model-justification.md`, `2.7-model-update-retraining-governance.md`; model via AI Core, temp 0.0, token budget + summarization @30k. |
| **L0-3 · Document Grounding & RAG Quality** | Covered | `governance/3.3-rag-evaluation-scorecard.md`; `eval/rag_eval.py` + `eval/rag_scorecard.json` + gold set. |
| **L0-4 · AI Commercialization & Metering** | Covered (docs) | `governance/4.5-customer-token-consumption-forecast.md`, `4.6-cost-per-transaction-baseline.md`; `docs/token_calculation.md`. |
| **L0-5 · Responsible AI & Safety Validation** | Covered | `governance/5.2-bias-fairness-assessment.md`, `5.3-redteam-report.md`, `5.5-gdpr-euaiact-compliance.md`, `5.7-ip-data-ownership-governance.md`; `app/prompt_injection_detector.py`; `tests/test_redteam.py`, `tests/test_sanitize.py`; advisory read-only. |
| **L0-6 · Agent Development & Deployment Standards** | Covered (CI partial) | Mock-first `IBD_TESTING`; 175 tests, coverage 73%; `a2a-sdk[all]` + `pydantic-settings`; CF deploy (`mta.yaml`/`manifest.yml`/`deploy.sh`); `governance/6.1-6.2-agent-builder-exception.md`. Gap: ruff/mypy advisory-only; some functions > 50 lines. |
| **L0-7 · End-to-End Release Validation & Go-Live** | Partial | `/.well-known/agent-card.json` 200, `AgentExecutor` lifecycle, `TaskUpdater`; `docs/INTEGRATION_GUIDE.md` (destination + principal propagation). Client-tenant live smoke pending; 5 npm UI advisories to clear. |
| **L0-8 · Agent Design Classification & Performance Engineering** | Covered | `governance/8.4-performance-slas.md`; deterministic scoring (`app/domain/scoring.py`, `prediction.py`) + gated LLM; `recursion_limit=15`; `app/circuit_breaker.py`. |
| **L0-9 · Knowledge & Data Grounding Strategy** | Partial | Live S/4HANA OData grounding (`app/s4_client.py`, `app/domain/data.py`) + decision recall (`app/domain/memory.py`). HANA Cloud Vector Engine recall is a **placeholder** (see HANA persistence seam). |
| **L0-10 · Dependency & Change Resilience** | Covered | `governance/10.2-dependency-map.md`, `10.3-10.4-10.5-drift-detection-design.md`; `app/circuit_breaker.py`; pinned `requirements.txt`. |

## Open items (honest)
- **Static-analysis CI (L0-6):** promote ruff/mypy from advisory to enforced; extract the >50-line
  functions in `agent.py` / `agent_executor.py`.
- **HANA Cloud persistence (L0-9):** durable audit table + Vector Engine recall is a placeholder
  (`MEMORY_BACKEND=hana` seam) — implement once HANA Cloud is provisioned.
- **Client go-live (L0-7):** live E2E on the client tenant; `npm audit fix` in `assets/material-risk-ui`.
