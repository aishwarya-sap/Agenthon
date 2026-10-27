# Agent Outcome Report — Production Readiness

**Agent:** material-risk-agent — *Project Material Risk — Construction Activity Impact Agent*
**Checklist:** GDH APAC AI Agent Checklist (10 pillars, 60 L1 items)
**Date:** 2026-10-20
**Verdict:** **CONDITIONAL GO** — go for demo / Agenthon; tenant-only items gate production.

---

## 1. Delivery summary

material-risk-agent is a **mock-first** (`IBD_TESTING=1`), **advisory-only** supply-risk agent built on the **LastMileSupport Joule 2.0 A2A template**. It is **LLM-orchestrated** (`langchain create_agent` + `ChatLiteLLM` via SAP AI Core / Generative AI Hub) over a **deterministic domain core** that performs all arithmetic in pure stdlib Python ("LLM never computes").

- **Models:** primary `sap/anthropic--claude-4.5-sonnet`, summarization `sap/anthropic--claude-4.5-haiku`, temperature 0.0, fallback empty, circuit breaker 3 / 30s, summarization at 30k tokens.
- **Tools:** 15 (12 read/compute + 3 write). The 3 write tools are HITL-gated side effects requiring `confirmed=true` after a human approval keyword — the agent **never autonomously writes SAP business objects**.
- **Deterministic business rules:** net-availability (unrestricted + due PO/PR qty, QI/blocked excluded); risk bands Critical/High/Medium/Low; chronic-late (>=3 of last 4 late elevates one band); alt-supplier HoD-only; escalation SLAs L1→L2 24h, L2→L3 48h.
- **RAG:** HANA Cloud Vector Engine (in-tenant), text-embedding-3-small via AI Core, similarity gate 0.82, top-k 4, injection-scanned fail-closed + PII-redacted.
- **Token envelope:** ~2 LLM calls per interaction, deterministic core = 0 tokens, worst case <= 52,000 tokens.
- **Tests:** offline pytest suite with mock tools, coverage target >=70%, writes `test_report.json`; LLM/e2e paths skip unless `AICORE_CLIENT_ID` is set.

Status legend: ✅ Satisfied · ⚠️ Partial (documented/interim; tenant finalisation) · ❌ Not satisfied (tenant-only) · ⏭️ N/A.

---

## 2. Checklist status — all 60 items

### L0-1 · AI Feature & Agent Onboarding Governance
| Item | Name | Status | Note |
|---|---|---|---|
| 1.0 | Idea2Value | ✅ | Use case framed (persona, pain, SAP fit, advisory ROI) |
| 1.1 | Feature Type Classification | ✅ | Classified agentic (ReAct, tool-calling) |
| 1.2 | Commercial Tier Determination | ✅ | Tier proposed; confirm against LLM Calculator (4.1) |
| 1.3 | AI Golden Path | ✅ | On path; 6.1/6.2 deviation logged as exception |
| 1.4 | Document - AI Commercialization Tracker | ⏭️ | No per-page Document AI processing in scope |
| 1.5 | GDH APAC Architect Group Support | ✅ | Architecture review engaged |

### L0-2 · LLM Selection & Benchmarking
| Item | Name | Status | Note |
|---|---|---|---|
| 2.1 | Test Data Preparation & Submission | ⚠️ | Offline mock test data interim; tenant submission pending |
| 2.2 | Automated Multi-Model Evaluation | ❌ | Tenant — AI Core unavailable offline |
| 2.3 | Generative AI Evaluation Roadmap | ⚠️ | Monitored; no action due |
| 2.4 | Internal Evaluation Dashboard | ❌ | Tenant evidence surface |
| 2.5 | Ongoing Model Version Re-evaluation | ⚠️ | Policy documented (2.7); live re-eval tenant |
| 2.6 | Frontier Model Justification Gate | ⚠️ | **Documented; dual sign-off pending** (assets/material-risk-agent/governance/2.6) |
| 2.7 | Model Update & Retraining Governance | ✅ | Documented — no training/fine-tuning (assets/material-risk-agent/governance/2.7) |

### L0-3 · Document Grounding & RAG Quality Evaluation
| Item | Name | Status | Note |
|---|---|---|---|
| 3.1 | Document Grounding Setup | ⚠️ | Mock corpus seeded; live Document Grounding API tenant |
| 3.2 | Vector Embedding & Retrieval Pipeline | ⚠️ | HANA Vector + text-embedding-3-small designed; live pipeline tenant |
| 3.3 | RAG Evaluation Scorecard | ⚠️ | Offline lexical-proxy harness built & passing (eval/); live RagEval run pending |
| 3.4 | Prompt Engineering Governance | ✅ | Prompts/config version-controlled; injection-reviewed |
| 3.5 | Automated Grounding Roadmap | ⏭️ | Roadmap awareness only |
| 3.6 | Runtime Hallucination Guardrail Architecture | ✅ | 0.82 grounding gate, citations, fail-closed, deterministic core |

### L0-4 · AI Commercialization & Metering
| Item | Name | Status | Note |
|---|---|---|---|
| 4.1 | LLM Calculator | ❌ | Tenant internal pricing tool |
| 4.2 | AI Scenario Metering Integration | ❌ | Tenant metering infrastructure |
| 4.3 | Floor Price Impact Review | ❌ | Tenant — depends on 4.1 |
| 4.4 | SAP Business AI Pricing Model | ⏭️ | SAP commercial model; aligns via 4.2 on tenant |
| 4.5 | Customer Token Consumption Forecast | ✅ | Documented; volumes TBD with customer (assets/material-risk-agent/governance/4.5) |
| 4.6 | Cost Per Transaction Baseline | ✅ | Documented + instrumentation defined (assets/material-risk-agent/governance/4.6) |

### L0-5 · Responsible AI & Safety Validation
| Item | Name | Status | Note |
|---|---|---|---|
| 5.1 | Responsible AI Pre-Release Evaluation | ❌ | Tenant hard gate + safety dashboard |
| 5.2 | AI Bias & Fairness Assessment | ✅ | Documented; deterministic transparent scoring (assets/material-risk-agent/governance/5.2) |
| 5.3 | Adversarial & Red Team Testing | ⚠️ | Offline attacks pass (assets/material-risk-agent/governance/5.3); formal tenant red-team deferred |
| 5.4 | AI Ethics & Governance Alignment | ⚠️ | HITL + disclosure present; RAI-function sign-off tenant |
| 5.5 | GDPR / EU AI Act Compliance | ✅ | Documented; limited-risk, PII-redacted (assets/material-risk-agent/governance/5.5) |
| 5.6 | Indirect Prompt Injection via Business Data | ✅ | `scan_injection` fail-closed + PII redaction, tested |
| 5.7 | IP Rights & Data Ownership Governance | ✅ | Documented standalone artefact (assets/material-risk-agent/governance/5.7) |

### L0-6 · Agent Development & Deployment Standards
| Item | Name | Status | Note |
|---|---|---|---|
| 6.1 | Agent Builder in Joule Studio | ⚠️ | Exception requested — Builder unavailable (assets/material-risk-agent/governance/6.1-6.2) |
| 6.2 | Skill Builder in Joule Studio | ⚠️ | Exception requested; skills hand-built with schemas |
| 6.3 | Generative AI Hub (J17) | ✅ | All LLM calls route via AI Core / Gen AI Hub |
| 6.4 | SAP AI Core & AI Launchpad | ✅ | AI Core serving runtime; prod deploy on tenant |
| 6.5 | Agent Tool Access Governance | ✅ | 15 tools enumerated, least-privilege, HoD gating, audit |
| 6.6 | Human-in-the-Loop Approval Governance | ✅ | 3 write tools gated, confirmed=true, logged |
| 6.7 | Agent Execution Observability & Tracing | ✅ | OpenTelemetry step spans + structured JSON logs |

### L0-7 · End-to-End Release Validation & Go-Live
| Item | Name | Status | Note |
|---|---|---|---|
| 7.1 | AI-Driven Exploratory Testing (AET) | ❌ | Tenant; GA Dec 2027, offline suite interim |
| 7.2 | Integration Validation | ⚠️ | Offline pytest; prod-like tenant validation pending |
| 7.3 | CBC Toggle Activation | ❌ | Tenant deploy step |
| 7.4 | Cross-Functional Sign-Off | ❌ | Tenant release gate |
| 7.5 | Agent Regression Testing Environment | ⚠️ | Offline pytest is interim regression; prod-parity env tenant |

### L0-8 · Agent Design Classification & Performance Engineering
| Item | Name | Status | Note |
|---|---|---|---|
| 8.1 | Trigger Type Classification | ✅ | User-initiated synchronous A2A, documented |
| 8.2 | Agentic Reasoning Classification | ✅ | ReAct (reasoning + tool calls), 2 LLM touch-points |
| 8.3 | Cross-Agent Intent Conflict Resolution | ⏭️ | Single advisory agent; no multi-agent write contention |
| 8.4 | UI Layer Performance | ⚠️ | SLA to be measured on tenant UI under load |
| 8.5 | Orchestration / Reasoning Layer Performance | ✅ | Bounded ~2 hops, step limits, <=52k envelope, breaker |
| 8.6 | Backend / Tool Call Performance | ✅ | Per-tool 30s timeout + fallback; logged via 6.7 |

### L0-9 · Knowledge & Data Grounding Strategy
| Item | Name | Status | Note |
|---|---|---|---|
| 9.1 | SAP KG as Runtime Grounding Source | ⏭️ | No runtime SAP KG dependency; OData + RAG reads |
| 9.2 | Custom KG Design & Governance | ⏭️ | No custom KG |
| 9.3 | KG vs RAG Decision Framework | ✅ | Documented: deterministic SAP reads / RAG emails / structured injection |
| 9.4 | KG Freshness & Staleness Management | ⏭️ | No KG; RAG rolling 90-day + session TTL cover staleness |
| 9.5 | Context Engineering - Structured Context Injection | ✅ | Deterministic tool outputs + role/session context injected |

### L0-10 · Dependency & Change Resilience
| Item | Name | Status | Note |
|---|---|---|---|
| 10.1 | Runtime KG Dependency Resolution | ⏭️ | No runtime KG; tools config-pinned |
| 10.2 | Agent Tool Dependency Map | ✅ | 15-tool map with timeouts/versions (mcp-mock.json) |
| 10.3 | Model Drift Detection | ❌ | Tenant continuous monitoring |
| 10.4 | Data Drift Detection | ❌ | Tenant continuous monitoring |
| 10.5 | Architecture Drift Detection | ⚠️ | ORD IDs pinned in `asset.yaml` `requires[]`; manifest-vs-ORD reconciliation designed (assets/material-risk-agent/governance/10.3-10.4-10.5); live monitor tenant |

---

## 3. Scorecard tally

| Status | Count |
|---|---|
| ✅ Satisfied | **26** |
| ⚠️ Partial (documented/interim) | **15** |
| ❌ Not satisfied (tenant-only) | **11** |
| ⏭️ N/A | **8** |
| **Total** | **60** |

**Satisfied + N/A-cleared = 34 / 60.** Of the remaining 26, all 15 Partial items are documented or have an interim offline control, and all 11 Not-satisfied items are **tenant-only** (benchmarking dashboards, LLM Calculator / metering, Responsible AI safety dashboard, release-gate / CBC / sign-off, and the two live drift monitors) that cannot be executed in the offline build environment.

## 4. Verdict — CONDITIONAL GO

**GO for demo / Agenthon.** The agent is functionally complete, advisory-only, and safe-by-construction: deterministic business logic, HITL-gated writes, fail-closed injection + PII handling, grounded synthesis, observability, and thirteen written governance artefacts (`assets/material-risk-agent/governance/`, indexed in its `README.md`).

**Production is gated** on the tenant-only items: L0-2.2/2.4/2.5 benchmarking, L0-3.3 live RagEval run, L0-4.1/4.2/4.3 LLM Calculator + metering + floor price, L0-5.1 Responsible AI evaluation + formal L0-5.3 red-team, L0-7.1/7.2/7.3/7.4/7.5 release validation + sign-off, and L0-10.3/10.4 live drift detection (L0-10.5 architecture-drift design is documented) — plus dual sign-off on L0-2.6 and the L0-6.1/6.2 Agent-Builder exception + security review.
