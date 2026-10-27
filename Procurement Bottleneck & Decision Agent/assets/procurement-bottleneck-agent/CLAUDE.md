# CLAUDE.md — Procurement Bottleneck & Decision Agent

Advisory, **read-only** SAP A2A agent (Adarsh Developers). Built to the GDH AI Factory standard.
Full docs: repo-root `docs/` (specs, decisions/ADRs, checklists, HANDOFF).

## Architecture
- Starlette + A2A 0.3.0 (`POST /`), deployed on CF. LLM via SAP AI Core (`ChatLiteLLM`).
- Orchestration: `app/graph/build_graph()` LangGraph seam (typed state + checkpointer +
  recursion limit) wrapping the deterministic turn in `app/agent.py::handle()`. The graph import
  is guarded — offline (no langgraph) `run_turn` falls back to `handle()` directly.
- Data: `app/s4_client.py` (live BAH OData) or offline fixtures (`IBD_TESTING=1`, `mcp-mock.json`).

## Hard rules
1. **Mock-first:** `IBD_TESTING=1 pytest` must pass before any live connection.
2. **Advisory/read-only:** never POST/PATCH/DELETE to SAP. "Write" tools only log decisions.
3. **No secrets in the repo** — `.env` (gitignored) / VCAP bindings only.
4. **Never fabricate** SAP data: on a failed read, surface it (`_backend_error_report`) — don't guess.
5. **LLM gating:** `IBD_TESTING` mocks *data*; the LLM is gated on `config.aicore_configured()`.
6. **Keep tests green** before any `cf push`; coverage ≥ 70%.

## Run
```bash
IBD_TESTING=1 pytest                 # 136 tests
IBD_TESTING=1 python -m app          # local (:8080)
gunicorn app.main:app -c gunicorn.conf.py   # production entry (CF Procfile)
```

## Governance
Tracked against the GDH APAC Agent Checklist v5 (10-pillar / 60-item):
`docs/checklists/agent-checklist-L0-L10.md`; per-pillar status in `docs/agent-checklist-assessment.md`.
Pillar numbering mirrors the `governance/*.md` artifacts. Decisions in `docs/decisions/`.
