# Chat UI — Design Guidelines & Rationale

The **why** behind the chat UI. Read this before changing the UI or the A2A client.

## Stack

- **Node.js + Express**, static file serving + a single reverse proxy.
- **`http-proxy-middleware`** proxies `/agent/*` → the agent, stripping the `/agent` prefix.
- Plain HTML/CSS/JS in `public/` — no build step, no framework, no bundler.

### Why this stack (over the alternatives)

- **No Next.js / App Router.** A router adds a build step, a server runtime, and a
  second buildpack concern for zero benefit here — the UI is one page that talks to one
  endpoint. Static files + a proxy is the smallest thing that ships on the CF
  `nodejs_buildpack` with **one** buildpack per app.
- **No direct browser → agent calls.** The browser calls same-origin `/agent/*`; the
  server proxies to `AGENT_URL`. This avoids CORS entirely and keeps the agent URL out of
  client code, so the same static bundle works in local dev and on CF unchanged.

## The `AGENT_URL` contract

- **Never hardcode the agent URL.** `server.js` reads `process.env.AGENT_URL`.
- **On CF**, the MTA wires it via `provides`/`requires` + `~{agent-api/agent-url}` — see
  `guidelines-cf-deployment.md`.
- **Locally**, it defaults to `http://localhost:5000` (the agent's `container.port`).
- **Never set `PORT`.** CF injects `$PORT`; `server.js` reads it with a `3000` fallback.

## A2A protocol (v0.3.0) — the client contract

`public/app.js` speaks **SAP A2A v0.3.0**. Getting this shape wrong is the single most
common failure, so it is pinned here:

- **Method** is `message/send` (JSON-RPC 2.0).
- **`messageId` is required** on the message object — generate a fresh UUID per turn.
- Parts use **`kind: 'text'`**, *not* `type: 'text'`. This changed across versions; the
  old `type` key is silently dropped by the v0.3.0 agent.
- **Response text** lives at `result.artifacts[].parts[].text`. Streaming chunks put it at
  `result.status.message.parts[].text`. `extractContent()` handles both.

### Version discovery (do this before trusting the client shape)

The agent publishes its card at **`/.well-known/agent.json`** with a `protocolVersion`
field. Before assuming v0.3.0, curl it:

```bash
curl -s $AGENT_URL/.well-known/agent.json | grep -i protocolVersion
```

If the deployed agent reports a different version, reconcile `app.js`'s request/response
shape with that version rather than assuming.

## Functional vs. decorative (by design)

**Functional:** the message input, the send button, message rendering, streaming, retry,
and session continuity.

**Decorative only** (intentionally not wired): the `+` and `@` input buttons, the left-rail
nav icons (chat/layers/code), the bell, the "View Prompt Library" link, the grid/apps and
expand icons. They exist to match the Joule reference look. Do not wire them unless a real
feature needs them — leaving them inert is a deliberate scope decision, not an oversight.

## The 7 under-the-hood behaviors

Invisible in a static screenshot, active in use:

1. **Markdown rendering** — agent text is escaped first, then a safe markdown subset is
   applied (XSS-safe). Never `innerHTML` raw agent output. See "Rendering agent markdown"
   below for what the subset covers.
2. **Progressive streaming** — stream chunks append to the live bubble; the typing dots
   clear on the first token.
3. **Responsive layout** — max-width centering (not fixed `%` padding); the rail collapses
   under ~900px and toggles via the topbar button.
4. **Dark mode** — `prefers-color-scheme`. Light mode is the exact reference-image match;
   dark is derived from it.
5. **Error handling** — network vs. 5xx vs. 4xx are distinguished, each with a Retry
   affordance that re-sends the last user turn.
6. **Session continuity** — a stable `contextId` (A2A 0.3.0) is threaded across turns so
   the agent can keep conversational state.
7. **Input cap** — a soft character limit with a near-cap warning.

## Rendering agent markdown (tables, headings, SAP status icons)

`renderMarkdown()` in `public/app.js` is a **hand-rolled, escape-first** renderer — no
markdown library, no bundler, fully offline (deliberate: a CDN/`npm` fetch is the biggest
corporate-proxy risk, and this UI has no build step). It escapes the whole string first,
then applies a safe subset, so it is XSS-safe by construction.

The subset covers: `#`–`######` headings, **GFM tables** (with `:---`/`:---:`/`---:`
column alignment), unordered lists, bold/italic, inline + fenced code, and http(s) links.
Real agents emit pipe tables and `##` headings routinely — without table/heading support
they render as literal `| … |` / `##` text in the bubble (the failure this fixes). Table
parsing is **structural**: the line loop looks ahead for a header row followed by a
delimiter row, then consumes contiguous `| … |` body rows — do not regex the whole blob.
Standalone thematic breaks (`---`, `***`, `___`) are **dropped**, not rendered as `<hr>` —
headings and tables already give section spacing, so a rule is redundant noise (the branch is
guarded so real list items `- x` and table delimiters `|---|` are untouched).

**SAP-standard status icons, not generic emojis.** Agents tend to use traffic-light emojis
(🔴🟠🟡🟢), ✅, 🚨, ⚡, 📊 as status markers. An `ICONS` map + `replaceIcons()` swap each
for an **inline SVG** drawn to SAP Fiori Horizon semantic conventions (ObjectStatus dots +
success check / error alert / urgent bolt / info chart), tinted with Horizon semantic
colors — negative `#D20A0A`, critical `#E76500`, caution `#E9A200`, positive `#188918`,
information `#0070F2`. Inline SVG (not an `SAP-icons.woff2` icon-font) keeps the zero-
dependency, offline property and matches this UI's all-inline-SVG idiom. `replaceIcons()`
runs **right after** `escapeHtml` — emojis survive escaping, and the injected SVG must not
be re-escaped; the SVG markup contains no `` ` ``/`*`/`[`/`|` so it is inert to the
downstream inline-markdown and table passes. Add a new status marker by extending the
`ICONS` map; style hooks live in `.sap-status` / `.md-table` in `style.css`.

## Agent reply style (no trailing follow-up question)

This is an **agent system-prompt** concern, not a UI one — the chat UI renders whatever text
the agent emits, so a chatty closing line can only be removed in the agent's prompt. Agents
built on this template should end each reply with the **answer itself** (the queue, the result,
the requested content) and **not** append an offer/follow-up question — "Would you like me
to…?", "Shall I…?", "Can I help with anything else?" — nor a decorative closing emoji. The
user drives the next turn; a trailing prompt is noise in a task UI. Encode this as an explicit
directive in the agent's `get_system_prompt()` (keep within the `@prompt_section` `max_length`).
This is the agent-output analogue of the markdown/icon rules above: both keep the rendered
bubble clean and task-focused.

**Tunable, not absolute (opt-in).** This is a sensible *default* for a task UI, but it is a
tone preference, not a correctness rule — some conversational/assistant-style deployments
legitimately want a closing offer. Treat it as opt-in per agent, easy to relax. And it must
**never** suppress a *genuine clarifying question*: when required details are missing to complete
the request (e.g. material, quantity, delivery date), the agent still asks for them — that ask is
required, not an unsolicited follow-up. Word the directive to draw that line explicitly.

One table-formatting corollary: if the agent emits a ranked/numbered table, tell it the
**rank/index column must be a plain integer for every row** — never a status emoji or word. The
emoji→SVG renderer converts a ✅ in *any* cell (including a rank cell) into the SAP status icon,
so a stray ✅ in the first column shows up as a tick where the row number should be. Keep status
glyphs to a dedicated status/dimensions column.

## Visual reference

The target look is the Joule reference (`build/Data/joule ui.png` in the original repo):
left icon rail, faceted violet diamond logo, "Working late? I've got you." welcome with a
violet speech-bubble icon, wide rounded input with "Message Joule..." placeholder, "View
Prompt Library" link, "Joule uses AI. Verify results." footer, and a faint lavender/pink
gradient across the bottom. Keep light mode 100% faithful to it.
