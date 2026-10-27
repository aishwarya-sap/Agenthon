# ADR-0001: Framework Selection — LangChain `create_agent` + LangGraph + ChatLiteLLM

**Status:** Accepted · **Date:** 2026-10-27

## Context

The agent must orchestrate a multi-step read → analyse → recommend pipeline over SAP data, call SAP AI Core models, bound per-turn cost, and keep all numeric computation exact and auditable for a procurement audience.

## Decision

Use **LangChain `create_agent`** on **LangGraph** for the ReAct tool loop, with **`ChatLiteLLM`** routing to **SAP AI Core / Generative AI Hub** (`sap/anthropic--claude-4.5-sonnet`). Bound the loop with `recursion_limit=15` and a `SummarizationMiddleware` at 30k tokens. All arithmetic lives in a deterministic Python domain core (`app/domain/`) — the LLM never computes.

## Alternatives

- **Raw Anthropic/OpenAI SDK loop** — more control, but we'd rebuild tool-calling, summarization, and checkpointing that LangGraph provides.
- **Fixed N-call pipeline** — simpler, but inflexible for ambiguous multi-hop queries.

## Consequences

- Flexible multi-hop reasoning with bounded cost (≤52k tokens/run).
- Prompt-cache on the static prefix; summarization keeps context bounded.
- Dependency on the LangChain/LangGraph stack and a2a-sdk versions (pinned in `requirements.txt`).
