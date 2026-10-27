# E2E Testing — Scripted A2A + UI-through-proxy (demo tier)

The **why** and **shape** of end-to-end tests for a dropped-in agent + chat UI. Read this
before deciding how deep to test a demo deployment.

## Tiering (demo vs production)

| Tier | Layers | Rationale |
| --- | --- | --- |
| **Demo / MVP** | Two scripted `httpx`/`pytest` files: **direct A2A** + **UI-through-proxy**. No browser. | Covers the deployment-fragile wiring with zero heavyweight deps. |
| **Production** | Adds **browser (Playwright) UI e2e** + quality-gate + code-review + agent-card validation + coverage. | Full-fidelity UI + gate machinery, once the demo is proven. |

**Why the browser leg is deferred to production:** `npx playwright install chromium` is a
~120 MB CDN download — the single biggest window/environment risk behind a corporate proxy.
The `/agent/*` proxy test already covers the fragile wiring (AGENT_URL binding, path rewrite,
same-origin) without a headless browser. The UI markup has stable IDs (`#messageInput`,
`#sendBtn`, `#messages`) so the browser leg is straightforward to add later.

## The two demo files

Both live in `tests/e2e/`, both use `httpx` + `pytest` (already available), no browser.

### `test_a2a_e2e.py` — drives the agent over real A2A `message/send`

Parameterized on `AGENT_URL` (default `http://localhost:5000`). Assertions:

- **Discovery (always runs):** `GET /.well-known/agent.json` → 200, `protocolVersion ==
  "0.3.0"` (the chat UI's A2A client targets 0.3.0 — flag drift early), agent name matches.
- **Queue / happy path (needs LLM):** a `message/send` builds the queue and surfaces known
  seeded IDs / `flagged_orders > 0`.
- **Deterministic-scoring invariant (needs LLM):** returned scores equal what Python computed
  for the seed rows — guards *the LLM never computes*; it must relay, not recompute.
  - **Golden covers ALL seeded orders, not a sample.** A live smoke test caught the model
    rendering a credit-blocked order as "100/100 fully ready" and dropping the flagged count
    by one — while a two-order golden (`{first, last}`) passed green, because the corrupted
    order was in the middle. Assert every seeded order's score, so a mis-relayed middle order
    can't hide.
  - **Add a flagged-never-shown-ready guard.** A dedicated assertion (e.g.
    `test_flagged_order_never_shown_ready`) that a known flagged order's segment contains its
    real score and does **not** say it's ready. This catches presentation-layer relabelling
    that a numeric-equality golden can miss. See `guidelines-sample-data.md` § "The LLM relays
    deterministic results".
    - **Build the guard on structure, not a regex over the JSON dump.** Pull the answer from
      `result.artifacts[].parts[].text` (real, unescaped newlines) — not `json.dumps(result)`,
      whose `\n` are escaped so line-splitting silently no-ops and the "segment" becomes the
      whole response. Then bound the order to **its own segment**: from its id up to the next
      *different* order id. A fixed-width window (`text[idx:idx+600]`) or an unsegmented blob
      bleeds into a genuinely-clean order's "fully ready / no action" and false-positives.
      Assert with plain substring checks on that bounded segment.
- **HITL guardrail (needs LLM):** a turn asking to release a credit block **without**
  confirmation is refused / asks for `confirmed=true`.
- **contextId threading (needs LLM):** a follow-up reusing the returned `contextId` is accepted.

### `test_ui_proxy_e2e.py` — drives the UI's same-origin `/agent/*` reverse proxy

Parameterized on `UI_URL` (default `http://localhost:3000`). Assertions:

- **UI serves the page (always runs):** `GET /` → 200, HTML.
- **Proxy forwards the card (always runs):** `GET /agent/.well-known/agent.json` reaches the
  agent and returns its card (proves `AGENT_URL` binding + `/agent` prefix strip + same-origin).
- **Queue through the proxy (needs LLM):** a `message/send` POSTed to `UI_URL + "/agent/"`
  returns the same ranked queue.

## The `needs_llm` split

LLM-dependent assertions are `@pytest.mark.skipif(not os.environ.get("AICORE_CLIENT_ID"))`.
This is deliberate: **without AI Core creds in hand, the non-LLM assertions (discovery,
proxy-forwarding, page-serve) still run and still gate** — they catch the wiring and version
regressions, which are the ones most likely to break on CF. The LLM assertions light up
automatically once `AICORE_*` is set.

## Run twice, zero code change — the go/no-go gate

1. **Local convergence gate** (before `mbt build`): boot the agent + UI locally, run both
   files against `localhost`. Non-LLM green is the minimum bar to deploy.
2. **CF re-run** (after deploy): re-run both with `AGENT_URL` / `UI_URL` set to the CF routes.

```bash
# local
AGENT_URL=http://localhost:5000 pytest tests/e2e/test_a2a_e2e.py -v
UI_URL=http://localhost:3000    pytest tests/e2e/test_ui_proxy_e2e.py -v
# CF
AGENT_URL=https://<agent-route> pytest tests/e2e/test_a2a_e2e.py -v
UI_URL=https://<ui-route>        pytest tests/e2e/test_ui_proxy_e2e.py -v
```

The `deploy-plan` skill ships both files as templates (`templates/e2e/`) so every dropped-in
agent inherits this layer by default.
