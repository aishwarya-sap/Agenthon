# ADR-0002: Design Pattern — Single LLM-orchestrated agent over a deterministic domain core

**Status:** Accepted · **Date:** 2026-10-27

## Context

The use case is one domain (project material supply) with a read → analyse → recommend flow. The output (risk bands, cost exposure, recovery options) must be numerically exact and repeatable for purchasing decisions.

## Decision

Use a **single agent** (not a Coordinator/multi-specialist pattern). The LLM orchestrates tool calls and writes the narrative; all computation — net availability, risk banding, schedule/cost simulation, delivery prediction — is **deterministic Python** in `app/domain/` (`scoring`, `simulation`, `prediction`, `recommend`). The 15 tools are the "specialists"; there are no sub-agents.

## Alternatives

- **Coordinator + specialist sub-agents** (as in the CATL reference) — warranted for 2–6 distinct domains; overkill here and would add routing cost and non-determinism.
- **LLM computes the numbers** — rejected: LLMs drift on arithmetic; procurement figures must be exact.

## Consequences

- Numbers are exact, unit-tested (175 tests), and token-free to compute.
- The LLM's role is bounded to orchestration + language; guardrails in the system prompt prevent it from narrating beyond the computed data.
- Simpler to reason about and cheaper per turn than a multi-agent graph.
