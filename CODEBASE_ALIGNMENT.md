# Codebase Alignment — Savic × Adarsh Agenthon

Both agents in this repo are built to **one standard**. This document is the answer to "are the two
codebases aligned?" — what is shared by design, and where they legitimately differ.

| | Project Material Availability & Supply Risk Agent | Procurement Bottleneck & Decision Agent |
|---|---|---|
| Folder | `Project Material Availability & Supply Risk Agent/` | `Procurement Bottleneck & Decision Agent/` |
| Agent asset | `assets/material-risk-agent/` | `assets/procurement-bottleneck-agent/` |
| Status | ✅ Live (us10) | ✅ Live (us10) |
| Tests | 175 tests, coverage 73% | 134 tests, coverage ≥ 70% |

## 1. Shared build standard (aligned — "the one way of building")

Both agents are the same kind of artifact, assembled the same way:

- **Protocol/runtime:** A2A 0.3.0 over Starlette, deployed on SAP BTP Cloud Foundry (us10).
- **LLM:** SAP AI Core via `ChatLiteLLM` (`sap/anthropic--claude-4.5-*`), low temperature, token budget.
- **Mock-first:** `IBD_TESTING=1` runs fully offline against fixtures; tests gate every change (≥ 70%).
- **Advisory, read-only:** neither writes SAP business objects; HITL approval gate on recommendations.
- **Grounding:** `s4_client.py` S/4HANA OData (BAH sandbox → client tenant); `eval/` RAG scorecard.
- **Identity:** IAS (Joule A2A) / XSUAA seam at the A2A boundary; `/whoami` dev-only diagnostic.
- **Governance:** the **GDH APAC Agent Checklist v5** (10-pillar / 60-item) is the single checklist —
  `docs/checklists/agent-checklist-L0-L10.md` in each, with a per-pillar `docs/agent-checklist-assessment.md`,
  and `governance/*.md` artifacts named by pillar item (`2.6`, `5.3`, `10.2`, …).
- **Persistence:** the same **HANA Cloud** decision/approval seam — `MEMORY_BACKEND=in_memory|hana`,
  `HanaMemoryStore` placeholder behind the `MemoryStore` interface, `ZAGENT_DECISION_LOG` audit table
  + Vector Engine recall (append-only, INSERT/SELECT-only role). Default in-process; not yet wired.
- **Starter template:** both carry an **identical** `default-repo/` — the generic Sprint-1 template
  shared with client developers (`default-repo/` + the use-case intent → a same-standard agent).

## 2. Intentional per-agent differences (not a defect — different domains)

The two agents solve different problems, so their domain code differs. This is deliberate:

| Aspect | Material Risk | Procurement |
|---|---|---|
| Module layout | `app/domain/` + `app/mcp_providers/` subpackages | flat `app/` + `app/graph/` (LangGraph seam) |
| A2A surface | `a2a-sdk` (`A2AStarletteApplication` + `AgentExecutor` + `TaskUpdater`) | raw Starlette + custom JSON-RPC handler |
| Resilience module | `app/circuit_breaker.py` | `app/resilience.py` (retry + circuit-breaker + quota-terminal) |
| Injection boundary | `app/prompt_injection_detector.py` | `app/sanitize.py` |
| Skills loader | `app/load_skill_resources.py` | `app/skills.py` |
| Memory module | `app/domain/memory.py` (3 memory types) | `app/memory.py` (`DecisionRecord` log) |
| Orchestration | deterministic scoring/prediction + gated LLM | deterministic skills + LangGraph seam + gated LLM |
| Deploy files | `mta.yaml` + `manifest.yml` + `deploy.sh` at repo root | `manifest.yml` inside the agent asset |

These are domain and stack choices, not divergent build styles. A reviewer should read them as two
instances of the same standard, specialised to material-availability vs procurement-bottleneck use cases.

## 3. If you are a client developer starting a new agent

Take `default-repo/` (identical in both folders), rename `assets/agent-starter-kit/` to your agent,
implement your use-case intent in the seams (`tools.py`, `agent.py`, `s4_client` service names, the
persistence store), and work the L0–L10 checklist in `default-repo/governance/`. The result will be
recognisably "built the same way" as the two agents here.
