# Agent Checklist — 10-Pillar Governance (L0-1 to L0-10)

> **How to use:** At the end of each sprint, review the items marked for that sprint.
> Mark ✅ complete, ⚠️ partial, ❌ not applicable, or ⏭️ deferred.
> The canonical source for this checklist is the SAP Agent-PathToProd cookbook.

---

## L0-1 — AI Feature & Agent Onboarding Governance

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-1.1 | AI use-case documented and approved | 1 | ⏳ |
| L0-1.2 | Business sponsor identified | 1 | ⏳ |
| L0-1.3 | Data owner sign-off for each data source | 2 | ⏳ |
| L0-1.4 | AI governance committee review | 3 | ⏳ |
| L0-1.5 | Change management plan in place | 4 | ⏳ |
| L0-1.6 | Rollback plan documented | 4 | ⏳ |

---

## L0-2 — LLM Selection & Benchmarking

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-2.1 | Primary model selected and justified | 1 | ⏳ |
| L0-2.2 | Fallback model configured | 2 | ⏳ |
| L0-2.3 | Model benchmark run on domain tasks | 3 | ⏳ |
| L0-2.4 | Temperature set to 0.0 (deterministic) for advisory tasks | 1 | ⏳ |
| L0-2.5 | System prompt reviewed and approved | 1 | ⏳ |
| L0-2.6 | Model version pinned in config | 1 | ⏳ |
| L0-2.7 | Model upgrade path documented | 4 | ⏳ |
| L0-2.8 | GenAI Hub model testing completed | 3 | ⏳ |

---

## L0-3 — Document Grounding & RAG Quality Evaluation

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-3.1 | Data sources identified and documented | 1 | ⏳ |
| L0-3.2 | Data freshness SLA defined | 2 | ⏳ |
| L0-3.3 | Retrieval accuracy benchmarked | 3 | ⏳ |
| L0-3.4 | Grounding confidence threshold set | 3 | ⏳ |
| L0-3.5 | Citation / source reference in agent output | 2 | ⏳ |
| L0-3.6 | RAG evaluation test set created | 2 | ⏳ |
| L0-3.7 | Knowledge base update cadence defined | 4 | ⏳ |
| L0-3.8 | Hallucination guardrail architecture in place | 3 | ⏳ |

---

## L0-4 — AI Commercialization & Metering

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-4.1 | LLM token cost estimated per interaction type | 3 | ⏳ |
| L0-4.2 | AI Core SKU and pricing confirmed | 1 | ⏳ |
| L0-4.3 | AI Scenario metering integration | 3 | ⏳ |
| L0-4.4 | Cost monitoring dashboard defined | 3 | ⏳ |
| L0-4.5 | Budget ceiling alert configured | 3 | ⏳ |
| L0-4.6 | Cost per transaction baseline measured | 3 | ⏳ |
| L0-4.7 | Customer token consumption forecast | 3 | ⏳ |
| L0-4.8 | Cost per transaction ceiling threshold | 3 | ⏳ |

---

## L0-5 — Responsible AI & Safety Validation

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-5.1 | Advisory-only confirmed (no write ops without HITL) | 1 | ⏳ |
| L0-5.2 | PII handling policy defined | 2 | ⏳ |
| L0-5.3 | Direct prompt injection tested (adversarial set) | 3 | ⏳ |
| L0-5.4 | Role boundary erosion tested | 3 | ⏳ |
| L0-5.5 | Financial disclaimer present on all cost outputs | 1 | ⏳ |
| L0-5.6 | Indirect prompt injection via business data tested | 3 | ⏳ |
| L0-5.7 | Bias / fairness review completed | 3 | ⏳ |

---

## L0-6 — Agent Development & Deployment Standards

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-6.1 | A2A protocol v0.3.0 compliant (card + JSON-RPC POST /) | 1 | ⏳ |
| L0-6.2 | IBD_TESTING=1 mock mode working | 1 | ⏳ |
| L0-6.3 | Tests passing, coverage ≥ 70% | 1 | ⏳ |
| L0-6.4 | Sonar scan completed with no critical issues | 3 | ⏳ |
| L0-6.5 | CF deployment automated (manifest.yml + deploy.sh) | 1 | ⏳ |
| L0-6.6 | Health check endpoint returning 200 | 1 | ⏳ |
| L0-6.7 | Structured logging per turn (context_id, latency_ms) | 2 | ⏳ |

---

## L0-7 — End-to-End Release Validation & Go-Live

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-7.1 | End-to-end test in client dev environment | 2 | ⏳ |
| L0-7.2 | Functional consultant sign-off on data accuracy | 2 | ⏳ |
| L0-7.3 | UAT completed with representative users | 4 | ⏳ |
| L0-7.4 | Production deployment plan reviewed | 4 | ⏳ |
| L0-7.5 | Go-live gate checklist signed off | 4 | ⏳ |

---

## L0-8 — Agent Design Classification & Performance Engineering

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-8.1 | Agent classification documented (LLM-orchestrated / deterministic / hybrid) | 1 | ⏳ |
| L0-8.2 | Tool call latency benchmarked | 2 | ⏳ |
| L0-8.3 | Context window budget managed (top=100 enforced) | 1 | ⏳ |
| L0-8.4 | Summarization strategy defined for long sessions | 2 | ⏳ |
| L0-8.5 | Circuit breaker / fallback chain configured | 2 | ⏳ |
| L0-8.6 | Load test results reviewed | 4 | ⏳ |

---

## L0-9 — Knowledge & Data Grounding Strategy

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-9.1 | Data readiness confirmed by client | 1 | ⏳ |
| L0-9.2 | Live SAP data access configured (dev) | 2 | ⏳ |
| L0-9.3 | Data transformation / normalization logic documented | 2 | ⏳ |
| L0-9.4 | Data quality issues catalogued | 2 | ⏳ |
| L0-9.5 | Knowledge base refresh schedule agreed | 4 | ⏳ |

---

## L0-10 — Dependency & Change Resilience

| # | Item | Sprint | Status |
|---|------|--------|--------|
| L0-10.1 | All dependencies pinned (requirements.txt) | 1 | ⏳ |
| L0-10.2 | Dependency update process defined | 3 | ⏳ |
| L0-10.3 | SAP API change monitoring in place | 4 | ⏳ |
| L0-10.4 | Runbook for common failures documented | 4 | ⏳ |
| L0-10.5 | Escalation contacts defined | 4 | ⏳ |

---

## Summary by Sprint

| Sprint | Checklist Items | Goal |
|--------|----------------|------|
| **Sprint 1** | L0-1.1, L0-1.2, L0-2.1, L0-2.4, L0-2.5, L0-2.6, L0-4.2, L0-5.1, L0-5.5, L0-6.1–L0-6.6, L0-8.1, L0-8.3, L0-9.1, L0-10.1 | Scaffold working on mock data in client CF |
| **Sprint 2** | L0-1.3, L0-2.2, L0-3.1–L0-3.6, L0-5.2, L0-6.7, L0-7.1, L0-7.2, L0-8.2–L0-8.5, L0-9.2–L0-9.4 | Live S/4HANA data, FC sign-off |
| **Sprint 3** | L0-1.4, L0-2.3, L0-2.8, L0-3.7, L0-3.8, L0-4.1, L0-4.3–L0-4.8, L0-5.3–L0-5.7, L0-6.4, L0-10.2 | Security, PP, token economics |
| **Sprint 4** | L0-1.5, L0-1.6, L0-3.7, L0-7.3–L0-7.5, L0-8.6, L0-9.5, L0-10.3–L0-10.5 | QA → production handover |
