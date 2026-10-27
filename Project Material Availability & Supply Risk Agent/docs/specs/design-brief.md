## Design Brief: material-risk-agent

Use case: An advisory AI agent embedded in SAP Joule and a standalone chat UI that surfaces material supply gaps which will block scheduled construction activities, predicts supplier delivery outcomes, simulates schedule/cost consequences, and recommends the least-cost recovery action — for the Purchase Executive / Purchase Manager / Purchase Head-of-Department / Project Manager personas on a construction project.

Pattern: Single LLM-orchestrated agent (ReAct tool loop) over a deterministic domain core. One agent with a bounded tool-calling loop fits the use case: the work is a read-analyse-recommend pipeline across one domain (project material supply), not multiple independent specialist domains. All data-mutating actions (escalation, memory write, expedite-PO proposal) pass a structured HITL gate.

Sub-agents: none — single-agent design. The "specialists" are tools + a deterministic domain core, not separate LLM agents:
  - deterministic domain core (`app/domain/`): scoring, simulation, prediction, recommend, sanitize, hitl, memory — zero LLM tokens, fully unit-tested
  - 15 StructuredTools (`app/tools.py`): 12 read/compute + 3 HITL-gated write

D0: LangChain `create_agent` + LangGraph — bounded ReAct loop (`recursion_limit=15`), SummarizationMiddleware at 30k tokens
D1: Single agent (not Coordinator) — one domain, read-analyse-recommend; deterministic core keeps numbers exact
D2: Yes — escalation, intervention-outcome memory write, and expedite-PO proposal are side effects; HITL `confirmed=true` gate required before any write. No SAP business object is ever mutated.
D3: joule+advisor — Joule-facing conversational agent; advisory recommendations the buyer accepts/actions
D4: LLM routing — the LLM decides which tools to call per query; no regex fast-path needed at this scale
D5: LLM-summary — multi-turn buyer sessions; summarize prior turns past 30k tokens to stay within the ~52k-token envelope
D6: multiple read sources — SAP S/4HANA OData (stock, PO/PR, GR history, supplier, info-record, contract) + HANA Cloud Vector (RAG over supplier emails/scorecards) + structured context injection (project schedule from SAP PS or Excel)
   AGENT_BACKEND_TYPE=multiple
   S4_SERVICE_PROFILE=cloud (BAI Accelerator Hub sandbox, APIKey) | onprem (Adarsh tenant, Destination + Cloud Connector, principal propagation)
D10: clarification, HITL review_gate — clarify ambiguous project/material scope; mandatory review_gate before escalation / memory-write / expedite-PO writes
D11 — rich rendering: brief-by-default markdown table + `[SUGGESTIONS]` follow-up chips (standalone UI) / Joule-side rendering
D12 — live-first fallback: when both IBD_LIVE_S4 and IBD_TESTING are set, a failed live S/4 read falls back to seeded data tagged `signal_status=simulated` so the agent never errors a turn

Retrieval: Hybrid — structured OData reads (authoritative transactional data) + standalone vector RAG (HANA Cloud Vector, similarity gate 0.82, top-k 4, injection-scanned fail-closed, PII-redacted) over supplier emails / delivery schedules / vendor scorecards. No knowledge graph in scope.

Risk model (deterministic, `app/domain/scoring.py`): schedule-buffer bands — Critical (buffer ≤0 & gap>0) / High (1–3) / Medium (4–7) / Low (>7); a chronically-late supplier (≥3 of last 4 late) elevates the band one level.

ADRs to create: framework-selection, design-pattern-selection, advisory-only-hitl
