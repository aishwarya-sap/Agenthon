# Sample Data — In-Process Tools over a Bundled SQLite DB

The **why** behind running a dropped-in agent against representative sample data for a demo,
without standing up MCP servers or live back-end connectivity. Read this before wiring a
demo agent's tools to data.

## The pattern

For a demo/pilot the agent talks to a **bundled SQLite database, seeded at startup**, through
**in-process LangChain `StructuredTool`s** — no separate MCP server, no Agent Gateway, no
live back end.

```
agent (LangGraph)  ──►  in-process StructuredTools  ──►  app/db/store.py  ──►  bundled SQLite
```

This is the cookbook default: in-process tools are for tools that live with the agent
(`08-subagents-tools.md`); MCP is only for cross-agent or independently-deployable tool
servers. A demo needs neither, so dropping MCP removes the one managed piece (Agent Gateway)
that plain CF lacks — and removes a whole deployable app.

## Why drop MCP / Agent Gateway for a demo

- **Agent Gateway is the only managed runtime piece absent on plain CF.** Everything else in
  the `sap_cloud_sdk` stack (`bootstrap`, `set_aicore_config`, `create_checkpointer`) degrades
  or runs on plain CF; Agent Gateway does not. Removing MCP removes that dependency.
- **One fewer deployable.** No separate MCP-server app, route, or health check.
- **Same tool surface later fronts live data.** The `store.py` seam swaps from SQLite to live
  OData/MCP in the production tier with the tool signatures unchanged.

## How to wire it

1. **`app/db/schema.sql`** — DDL for the entity tables the agent's tools read, plus seed rows.
   Seed rows should exercise **every dimension/branch the agent scores or reasons over**, so
   the demo output is meaningful (e.g. one row per failure mode + at least one clean row).
2. **`app/db/store.py`** — a thin sync data-access layer (SQLite is fast; blocking calls are
   fine for a demo). Reads `SQLITE_PATH` (default under the system temp dir); runs
   `schema.sql` at import **if the DB is absent** (`_ensure_seeded()`). This is the frozen
   contract between the data layer and the tools — agree signatures and return-dict shapes
   before parallel work starts.
3. **`app/mcp_providers/<agent>_local_tools.py`** — in-process `StructuredTool`s whose
   coroutines call `store.py`. Reuse the existing `_build_mock_tools()` StructuredTool shape
   in `agw.py`, swapping static JSON for query results.
4. **Flip the one wiring seam: `get_mcp_tools()`.** This function (in `agw.py`) is the
   *single* place the tool set is chosen — `agent_executor.py` calls it once and merges the
   result with any skill tools, so the demo swap is one branch there and **no edit to
   `main.py` / `agent.py` / `agent_executor.py`**. Add a demo branch at the top, lazy-importing
   the local tools to avoid an import cycle; leave the Agent Gateway path intact below it:

   ```python
   def get_mcp_tools():
       if _ibd_testing_on():                      # demo: in-process SQLite tools
           from mcp_providers.<agent>_local_tools import get_local_tools
           return get_local_tools()
       ...                                        # production: Agent Gateway (unchanged)
   ```

   **Gate on a *truthy* flag, via one shared helper — never `== "1"`.** The same off-platform
   switch degrades the JWT subject (`get_user_sub()`) *and* selects the tool set, so both must
   read the flag the same way. The runtime sets `IBD_TESTING:"1"` (mta.yaml) but a test
   harness may set `"true"` — two spellings of "on". Gate both call sites on one helper so they
   can never disagree:

   ```python
   def _ibd_testing_on() -> bool:
       return os.environ.get("IBD_TESTING", "").strip().lower() in ("1", "true", "yes", "on")
   ```

5. **Keep deterministic logic in Python.** Tools only *fetch/mutate* data; any scoring,
   arithmetic, or tolerance check stays in plain unit-tested Python — the **LLM never
   computes**. Tools feed it the numbers; it orchestrates and explains.

**Running the tool/data tests — `app/` is the import root.** These agents put `app/` on
`sys.path` (the autouse conftest does bare `import mcp_tools`, `import store`, etc.), so the
suite only resolves with `app/` on `PYTHONPATH`. Run from the agent dir:

```bash
PYTHONPATH="$(pwd)/app" python -m pytest tests/ -q     # from assets/<agent>/
```

`db/` and `mcp_providers/` therefore import as top-level (`import store`, `from db import
calculations`), not `app.db.*`. `store.py` is a module-level singleton seeded at first import,
so tests that need an isolated temp DB must **defer their imports into the test body** rather
than importing `store` / the local tools at module top (a module-top import races whichever
test file is collected first alphabetically and wins the seeding).

## Deriving the seed set (for whatever domain the agent is)

Step 1 above says "one row per failure mode + a clean row" — the recipe is the same for every
agent, but *the rows themselves come from that agent's own logic*, not from this file. To
enumerate them:

- **Read the agent's validation/scoring code and list each branch that changes the outcome** —
  every failure mode, each threshold boundary, and the guardrail paths (e.g. the HITL
  confirmation branch). Author one seed row that trips each branch, plus one clean row that
  trips none.
- **Where the agent encodes its branches as data, that structure *is* the checklist.** A
  weights map, an enum of issue types, a rules table — enumerate rows straight from it. Where
  validation is scattered in free-form code, the classify step (deploy-plan Step 2) has to read
  it out by hand; there's no generic shortcut, and that's fine.
- **The seed set and the e2e golden are the same set.** Every seeded row must appear in the
  A2A golden (see `guidelines-e2e-testing.md`) — a golden that covers only some rows lets a
  mis-relabelled row pass silently. Enumerate once; use it for both.
- **Gate a derived status flag on the state it applies to, not on elapsed time alone.** A flag
  computed from duration — `is_stalled`, `is_overdue`, `aging`, `expiring` — only means something
  in a particular state, so it must **AND-in that precondition**: a PO is `stalled` only while
  `pending_approval`; a goods receipt is `overdue` only while *not yet delivered*. Compute it from
  the duration *alone* and it misfires on every legitimately old record that has already moved past
  that state — e.g. a PO approved months ago reported as "stalled." This is **invariant-#1-critical**:
  the model relays the deterministic flag verbatim with no sanity check *by design*, so a wrong flag
  becomes a confidently-wrong answer to the user (a whole list rendering as "all stalled" is the
  tell). Keep the pure duration check in `calculations.py`; apply the state gate where the row is
  assembled (`store.py`). Seed at least one **old-but-past-the-state** row (an approved, long-ago
  PO) and assert in the golden that it reads *not* flagged — a duration-only bug sails through a
  golden that only checks the genuinely-flagged row.

This is why a different agent yields a different `schema.sql`: same mechanism, domain-specific
rows derived from that agent's branches. The order-readiness fixture (8 orders, one per SD
dimension + a clean one) is just this applied to that domain.

## The LLM relays deterministic results — it must never alter them

"The LLM never computes" is necessary but **not sufficient**. Even when scoring is fully
deterministic in Python, the model can still corrupt a correct result at the **presentation
layer** while composing a narrative — silently relabelling a flagged order as "fully ready",
dropping one from a flagged count, or rounding a score. This is *mis-transcription*, not
recomputation, and it slips past invariant #1 because the arithmetic was never in doubt.

Two mitigations, applied together:

- **Prompt (config).** Instruct the model to **reproduce each value — score, urgency, flags,
  failing dimensions, and the flagged/total counts — EXACTLY as the tool returned them**, never
  recompute, re-derive, or relabel, and to defer to the tool's numbers if its own summary
  disagrees. Word the role line as *"retrieves the tool-computed score"*, never *"computes a
  score"* — the verb leaks into behaviour.
- **Test (enforcement).** The A2A e2e golden must cover **all** seeded orders (a two-order
  golden let a mis-relabelled middle order pass silently) plus a guard asserting a flagged
  order is never rendered as ready. See `guidelines-e2e-testing.md`.

## Guardrails on write tools (HITL)

Any tool that mutates state must carry its human-in-the-loop guardrail in the tool itself,
not only the prompt: e.g. a `release_credit_block(sales_order, confirmed: bool)` tool
**refuses unless `confirmed is True`**, returning `{"status": "confirmation_required", ...}`.
Prompt-only guardrails are not enforcement; the tool boundary is.

## Caveats (state them at demo time)

- **Ephemeral disk.** CF container filesystems are wiped on restart/evacuation. Startup
  seeding means the DB is always rebuilt — fine for a demo, but **writes do not persist**
  across restarts. Durable state (learned overrides, task store) is a production concern
  (bind a volume service / Object Store / HANA).
- **Static seed dates drift.** Seed dates are fixed ISO strings chosen near the demo date.
  Anything that computes against "today" (urgency windows, age) will drift if the demo runs
  much later. Acceptable for a demo; regenerate the seed or compute dates relative to now if
  it matters.
- **Keep the tool count ≤ 8–10.** Consolidate to task-shaped tools, not raw CRUD
  (`08-subagents-tools.md`). Defer tools the deterministic path does not consume.
