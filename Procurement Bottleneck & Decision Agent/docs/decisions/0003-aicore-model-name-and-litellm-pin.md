# ADR-0003: SAP AI Core model-name format + litellm version pin

- **Status:** Accepted
- **Date:** 2026-10-27

## Context
Every LLM call silently fell back to a canned reply. Two stacked causes were found only after adding
an error log around `ChatLiteLLM.ainvoke` and reading `cf logs`.

## Decision
1. **Model name uses a dot before the minor version.** SAP AI Core rejects
   `sap/anthropic--claude-4-5-sonnet` with HTTP 400; the accepted form is
   `sap/anthropic--claude-4.5-sonnet` (likewise `-4.5-haiku`). The 400 body lists the supported set.
2. **Pin the litellm stack.** Loose ranges pulled litellm 1.10x which broke `sap/` provider
   resolution. Pinned: `litellm==1.94.1`, `langchain==1.3.10`, `langchain-core==1.6.1`,
   `langchain-litellm==0.7.1`, `langgraph==1.2.6`.

## Consequences
- Never swallow the LLM exception — always log it so the real cause is visible in `cf logs`.
- When wiring a new BAI CF agent to AI Core, reuse these pins and the dot model name.
