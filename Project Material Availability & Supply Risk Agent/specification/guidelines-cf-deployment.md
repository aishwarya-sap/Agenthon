# Cloud Foundry Deployment — Pre-flight & Rationale

The **why** behind the CF deployment files. Read this before changing `mta.yaml`, the
buildpack, or the agent's runtime files.

## What gets deployed

Two MTA modules from one `mta.yaml`:

- **Agent** (`type: python`, `python_buildpack`) — the Joule-generated A2A agent.
- **UI** (`type: nodejs`, `nodejs_buildpack`) — the Express chat UI (`cf-deploy` assumes
  `/chat-ui` already created it).

## Pre-flight files (and why each is required)

These are added into the **agent** asset folder. Without them the build silently uses the
wrong defaults and fails at runtime, not build time — which is why they are automated.

### `runtime.txt` → `python-3.11.x`

The CF `python_buildpack` defaults to **Python 3.10**. `sap-cloud-sdk` (and other SAP
packages the agent pulls in) require **≥ 3.11**. Without `runtime.txt` the app installs
but crashes on import. Pinning `python-3.11.x` fixes it.

### `Procfile` → `web: python app/_boot.py` (LLM agent) · `web: python app/main.py` (no-LLM echo)

The buildpack cannot auto-detect the entry point for a plain-Python (non-framework) app.
The `Procfile` names the web process explicitly. Without it the app stages but never
starts a web process, and the health check times out.

For an agent that calls the LLM, the web process is **`app/_boot.py`**, not `app/main.py`:
`_boot.py` maps the bound `aicore-creds` service's values into `AICORE_*` env vars and then
execs `app/main.py` unchanged (see § AI Core credentials). A **no-LLM echo agent** (hello-world)
has no credentials to map, so it points the `Procfile` straight at `app/main.py` and drops
`_boot.py`. `/cf-deploy` writes the right one based on whether the agent invokes the model.

## MTA rules (the ones that bite)

- **Never set `PORT`.** CF injects `$PORT` into every app; the code must read it. Setting
  a fixed `PORT` in `mta.yaml` breaks the platform's port binding.
- **A module cannot `~{}` its own `provides`.** The agent exposes its own URL to *other*
  modules via `provides: agent-api / agent-url: ${default-url}`, and references its own URL
  (if needed) with `${default-url}` directly — not `~{agent-api/agent-url}`.
- **Inter-module URL wiring** is `provides` + `requires` + `~{name/property}`: the agent
  `provides` `agent-api` with `agent-url: ${default-url}`; the UI `requires: agent-api` and
  reads `AGENT_URL: ~{agent-api/agent-url}`. This is how the UI learns the agent's deployed
  URL without anyone hardcoding it.
- **One buildpack per app.** The agent is python-only; the UI is nodejs-only. Don't mix.
- **Health check** for the agent is HTTP on **`/.well-known/agent.json`** (the A2A agent
  card is always served there), not `/`.

## AI Core credentials (bind a shared service; the SDK won't read VCAP)

If the agent calls the LLM (`ChatLiteLLM` / `set_aicore_config()` — anything beyond a plain
echo agent), it needs four values at **every turn**:

- `AICORE_CLIENT_ID`
- `AICORE_CLIENT_SECRET`
- `AICORE_AUTH_URL`
- `AICORE_BASE_URL`

**The trap:** `set_aicore_config()` **does not raise** when these are absent — it logs
`No value found for AICORE_*, using default` and continues, so the app **deploys green**, the
health check passes, and `/.well-known/agent.json` serves the card. The failure only surfaces on
the first chat turn, when the LLM call cannot authenticate. Deploy success is *not* evidence the
agent works; a chat turn is.

**How the SDK resolves creds (this dictates everything below).** `set_aicore_config()` reads,
in order: (1) mounted secret files under `SERVICE_BINDING_ROOT` / `/etc/secrets/appfnd/...` — an
**App Foundation / Kyma** convention — then (2) the `AICORE_*` **environment variables**. It does
**not** parse `VCAP_SERVICES`. So on **classic CF** a plain `cf bind-service` lands the creds in
`VCAP_SERVICES` where **nothing reads them** — the binding alone does nothing.

**The pattern: bind a shared service + a generic launcher shim.** Creds are present on the first
start (no restart) and reused by every agent, with no secret in any tracked file:

1. **Reuse the shared service if present; create it only if absent** (secrets typed at the CLI):
   ```bash
   cf services | grep aicore-creds        # present in THIS space? → reuse as-is
   # only if absent in this space:
   cf create-user-provided-service aicore-creds -p \
     '{"AICORE_CLIENT_ID":"<id>","AICORE_CLIENT_SECRET":"<secret>","AICORE_AUTH_URL":"<auth-url>","AICORE_BASE_URL":"<base-url>"}'
   ```
   A **user-provided service** is the pragmatic choice (you already hold the creds; a managed
   `aicore` instance gives no auto-consumption edge here since the SDK ignores VCAP anyway).
   It is **space-scoped and shared across every agent in the space** — `mta.yaml` declares it as
   an `existing-service`, so a UPS created for a *prior* agent in the same space is reused with
   zero changes and is **not** a blocker. It is only missing when you deploy into a *different*
   space than the one it was created in (UPS instances do not cross spaces).
2. **Bind it** — `mta.yaml` carries a `resources: aicore-creds` (`existing-service`, so
   redeploy/undeploy never touches the shared creds) and the agent module's `requires: aicore-creds`.
3. **Map it to env** — `app/_boot.py` copies the bound credentials from `VCAP_SERVICES` into
   `AICORE_*` at startup, then execs `app/main.py` unchanged. If `AICORE_*` are already set, it
   respects them and does nothing.

**Locally**, `export` the four vars in your shell (never a tracked file); `_boot.py` is a no-op
off-CF:

```bash
export AICORE_CLIENT_ID=<id>
export AICORE_CLIENT_SECRET=<secret>
export AICORE_AUTH_URL=<auth-url>
export AICORE_BASE_URL=<base-url>
```

**If the SDK version reads `VCAP_SERVICES` itself** (confirm via `cf ssh` on the SDK source or
its changelog), the binding alone suffices — drop `_boot.py` and point the `Procfile` back at
`app/main.py`. As of `sap-cloud-sdk 0.53.0` this is unconfirmed, so `_boot.py` is the safe default
(harmless even if the SDK does read VCAP — it only fills unset vars).

**Fallback — `cf set-env` (one-off override).** For a quick override on an already-running app,
`cf set-env <AGENT_NAME> AICORE_*` then `cf restart` (**not** `cf restage` — the vars are
runtime-read, and restage hits the quota wall on a memory-tight org; see the note below). Never
commit these secrets to `mta.yaml` or any tracked file.

## Memory sizing

The template defaults the agent module to **`memory: 1G`**. A langchain/langgraph agent with
summarization middleware does not fit comfortably in 512M — it stages fine but the worker is
OOM-killed under load, which reads as intermittent 502s, not an obvious memory error. A
no-LLM echo agent (hello-world) genuinely runs in 512M; drop it back only for that case.

## No-auth demo: the `get_user_sub()` trap (IBD_TESTING)

An agent generated for the managed runtime often extracts a JWT subject to key its
conversation state — e.g. `get_user_sub()` reading the `Authorization: Bearer` token. On a
**no-XSUAA demo** no token ever arrives, and that call typically **raises** (`No user token
in context — cannot extract sub claim`) — which surfaces as *every chat turn failing* even
though the agent booted green and authenticated to AI Core fine.

The usual off-platform escape hatch is **`IBD_TESTING=1`**, which makes the subject degrade
to a stable `"unknown"` (conversation threads still separate by their own `contextId`). Set
it as an agent-module property in `mta.yaml` for the demo, and drop it for the production
tier where XSUAA supplies the JWT. Before relying on it, confirm the flag doesn't also toggle
mock tool-loading you don't want — grep the app for `IBD_TESTING`.

## Model choice is a code default off-platform

On the managed runtime the model is a config key (`@agent_model(key="config.model")`) an
operator can override. **On plain CF there is no config service, so that decorator is a
no-op and the function's hardcoded `return` is the effective model** — and an `AGENT_MODEL`
env var is *not* read unless the code explicitly reads it. To change the model for a plain-CF
deploy, edit the default return in `get_model_name()` (and the summarization model if
present); setting `cf set-env AGENT_MODEL` alone does nothing. Verify the target model string
(e.g. `sap/anthropic--claude-4.6-sonnet`) is actually available in the bound AI Core tenant.

## Don't pip-install at MTA build time — let the buildpack do it

The agent module's `build-parameters` must **not** run `pip install -r requirements.txt`
locally. `mbt build` would run it under whatever Python is on the build machine; if that's
newer than a pin's supported range (e.g. build machine on Python 3.14 while `litellm==1.91.1`
caps at `<3.14`), the install can't resolve and the build fails — on a machine that never runs
the app. The CF `python_buildpack` installs `requirements.txt` at **staging** using the
`runtime.txt`-pinned Python (3.11), which is where it belongs. Use a no-op build command and
package the module directory:

```yaml
build-parameters:
  builder: custom
  commands:
    - echo "deps installed by CF python_buildpack from requirements.txt at staging"
  build-result: .
```

## Applying env vars: `cf restart`, not `cf restage`, on a memory-tight org

After `cf set-env`, you must recycle the app for it to take effect — but pick the right verb:

- **`cf restage`** rebuilds the droplet: it re-runs staging, which needs a *fresh* full
  memory allocation (e.g. another 1G) on top of the running apps. On a shared/quota-limited
  org this fails with `organization's memory limit exceeded: staging requires 1024M`.
- **`cf restart`** stops and starts the app on its **existing** droplet, reusing the memory
  already allocated — no staging headroom needed.

`AICORE_*` and `IBD_TESTING` are read at **runtime** (`set_aicore_config()`, `get_user_sub()`),
not baked at staging, so `cf restart` is sufficient to apply them and avoids the quota wall.
Reserve `cf restage` for changes that actually alter the droplet (new buildpack, changed
`requirements.txt`).

## Deploying into a memory-tight org: `cf stop` first

The same quota wall bites on **deploy/push**, not just restage. A plain `cf deploy` (or
`cf push`) stages the **new** droplet *before* stopping the old one, so for a moment the org
must hold the running app **and** its full staging allocation at once (e.g. 2×1G). On a
shared/quota-limited org this fails with `organization's memory limit exceeded: staging
requires 1024M` even though the app itself fits.

Fix: free the app's allocation first, then deploy into the freed quota:

```bash
cf stop <AGENT_NAME>              # frees its memory for staging
cf deploy mta_archives/*.mtar    # (or cf push <module>) stages into the freed quota, then starts
```

This is the deploy-time analogue of `cf restart`-not-`cf restage` above — both avoid needing
staging headroom *on top of* the running app. Pushing one module at a time (`cf push <module>`)
keeps the peak lower than a full two-module `cf deploy`.

## Deploy success ≠ change shipped — verify the deployed asset

Editing a file locally (and propagating it to the template repo) does **not** put it on CF —
only a redeploy/restart of that module does. A static-asset/UI change is the easy miss: the
agent module can be redeployed while the UI module keeps serving the **old** bundle, so a fix
looks like it never worked. After deploying, confirm the change actually shipped by fetching
the **deployed** asset and diffing it against local:

```bash
curl -s https://<ui-route>/app.js | diff - assets/<UI_NAME>/public/app.js
```

For a static-asset-only change, redeploy or `cf restart` the **UI** module (the agent module
is untouched). A green deploy of one module is not evidence the other module changed.

## Build & deploy (the user runs these)

```bash
cf target -o <org> -s <space>        # target your org/space (your step)
mbt build                            # produces mta_archives/*.mtar
cf deploy mta_archives/*.mtar        # deploys both modules
```

`mbt` (Cloud MTA Build Tool) and the `cf` CLI with the MultiApps plugin must be installed.
By default the skill **prints** these commands and the user runs them — but that is a workflow
convention, **not** a technical limitation. When the user authorizes the deploy (or asks why it
hasn't happened), run the actual pre-deploy readiness check and report the real blocker rather
than citing the convention:

- **Tooling** — `cf --version`, `mbt --version`, `cf plugins | grep multiapps`.
- **A live, unexpired session.** ⚠️ `cf target` prints the **cached** org/space even when the
  token has expired — it is not proof of a live session. Confirm with an API call
  (`cf services`); `The token expired, was revoked, or the token ID is incorrect` means the user
  must re-authenticate (`cf login --sso`), an interactive step you cannot do for them. This is the
  single most common real reason a deploy "can't proceed."
- **`aicore-creds` in the target space** — `cf services | grep aicore-creds`; reuse if present
  (a prior agent's UPS in the same space is fine), create only if absent.
- **Quota** — on a memory-tight org, `cf stop <AGENT_NAME>` before deploying (see § Deploying
  into a memory-tight org above).

With all checks green and the user's authorization, running `mbt build` + `cf deploy` yourself
is fine — the "user's step" default is only about *unattended* deploys. Deploy-green ≠ working:
finish with a real chat turn.
