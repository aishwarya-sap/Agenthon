# CF Deployment + Joule 1.0/2.0 Integration Guide

**Project:** Material Availability & Supply Risk Agent — Agenthon (demo Oct 28, 2026)  
**Audience:** Functional consultant / DevOps first-timer  
**Scope:** SAP BTP service enablement → CF deploy → Joule integration → principal propagation to S/4

---

## Overview of what we're wiring up

```
User (IAS login)
  ↓  Joule chat panel
  ↓  [Joule selects our capability by intent-matching]
  ↓  [OAuth2JWTBearer via BTP Destination "MATERIAL_RISK_AGENT"]
CF Agent (material-risk-agent)          ← our app
  ↓  [A2A message/send · protocolVersion 0.3.0]
  ↓  [IBD_TESTING=0 → Agent Gateway MCP calls]
S/4HANA (stock, POs, GRs, vendor master)
```

For the October 28 demo, steps 1–5 (CF deploy + chat UI) are sufficient to hand the app to functional consultants. Joule integration (steps 6–9) is the follow-on step.

---

## Part 1 — BTP Subaccount & Service Prerequisites

### Step 1 — Verify / create the BTP subaccount

> You need **Global Account Administrator** or **Subaccount Administrator** in the BTP cockpit.

1. Open [BTP Cockpit](https://cockpit.btp.cloud.sap)
2. Navigate to your Global Account
3. Either reuse an existing subaccount (e.g. `BAI-DEV`) or create a new one:
   - **Region:** us10 (matches the BAI AI Core service key provided)
   - **Environment:** Cloud Foundry enabled
4. In the subaccount, go to **Cloud Foundry → Spaces**
5. Create a space called `AI-DEV` (or reuse if it exists)

### Step 2 — Subscribe to required BTP services

In the subaccount **Service Marketplace**, subscribe / create instances for:

| Service | Plan | Why |
|---------|------|-----|
| **SAP AI Core** | `extended` | Hosts Claude models (GenAI Hub) |
| **SAP Generative AI Hub** | (included with AI Core extended) | Serves `claude-4.5-sonnet` |
| **Cloud Foundry Runtime** | `standard` | Runs our Python agent + UI |
| **SAP Authorization and Trust Management (XSUAA)** | `broker` | Secures CF apps |
| **SAP Connectivity Service** | `lite` | Connects CF to on-prem S/4 via Cloud Connector |
| **SAP Destination Service** | `lite` | Stores BTP destinations (agent URL, S/4 OData) |
| **SAP Cloud Identity Services (IAS)** | `application` (free) | Principal propagation for Joule |

For Joule integration (can be done after the CF demo is working):

| Service | Plan | Why |
|---------|------|-----|
| **SAP Build Work Zone** | `standard` | Hosts Joule panel |
| **SAP Joule** | (entitlement from contract) | The Joule conversational AI |

**How to create a service instance (example: Destination Service):**
1. BTP Cockpit → Subaccount → **Services → Service Marketplace**
2. Search "Destination"
3. Click **Create** → plan `lite` → instance name `destination-service`
4. After creation: go to **Instances and Subscriptions**, find it, click the instance
5. **Create Service Key** → name `destination-sk` (you'll use this later)

### Step 3 — Enable AI Core resource group and model

1. Download the AI Core service key (from Instances → `aicore` → Service Keys)
2. In **Generative AI Hub** (accessible from BTP Cockpit → Services):
   - Create resource group `default` (or use the one in the service key)
   - Deploy model: `anthropic--claude-4-5-sonnet` (check available models in your region)
   - Deploy fallback: `anthropic--claude-3-5-haiku`
3. Note the values — they're already in `/Users/I778959/Documents/MaxForum/BAI-AICore-Credentials.md`

### Step 4 — Create the `aicore-creds` user-provided service

This project ships AI Core credentials via `.env` + `cf push` (see Part 2) — the
simplest path, and the one the sibling agents use. The alternative below (a bound
user-provided service) is only needed if you prefer secrets in CF's vault instead
of the pushed `.env`. **Either way, never put real credentials in a tracked file** —
pull them from `/Users/I778959/Documents/MaxForum/BAI-AICore-Credentials.md` at the
moment you run the command.

```bash
# OPTIONAL (only if NOT using the .env path): bind a user-provided service.
# Replace every <...> with the values from BAI-AICore-Credentials.md — do not commit them.
cf create-user-provided-service aicore-creds -p '{
  "AICORE_AUTH_URL": "<auth-url>",
  "AICORE_BASE_URL": "<base-url>",
  "AICORE_CLIENT_ID": "<client-id>",
  "AICORE_CLIENT_SECRET": "<client-secret>",
  "AICORE_RESOURCE_GROUP": "default"
}'
```

> **Security note:** credentials belong only in `.env` (git-ignored) or CF's encrypted
> vault — never in a tracked file. The default `manifest.yml` path reads them from the
> pushed `.env`; no UPS is required.

---

## Part 2 — CF CLI Setup and Deploy

### Step 5 — Install tools and login

```bash
# 1. Install cf CLI (if not already)
brew install cloudfoundry/tap/cf-cli@8       # macOS

# 2. Install MTA plugin
cf install-plugin -f https://github.com/cloudfoundry/multiapps-cli-plugin/releases/latest/download/mta_plugin_darwin_amd64

# 3. Install MBT (Cloud MBT build tool)
npm install -g mbt

# 4. Login
cf login -a https://api.cf.us10-001.hana.ondemand.com   # us10 endpoint
# Enter your SAP BTP email and password
# Select org and space when prompted
```

### Step 6 — Build and deploy the MTA

```bash
# From the project root (where mta.yaml lives)
cd "/Users/I778959/Documents/SAP VsCode/Agenthon/Savic+Adarsh/Project Material Availability & Supply Risk Agent"

# Build the MTA archive
mbt build

# Deploy (cf deploy requires the MTA plugin)
cf deploy mta_archives/*.mtar --strategy rolling

# Watch the deploy logs
cf logs material-risk-agent --recent
cf logs material-risk-ui --recent

# Verify
curl -s https://material-risk-agent.<cf-domain>/.well-known/agent.json | python3 -m json.tool
# Expect: {"protocolVersion": "0.3.0", "name": "material-risk-agent", ...}
```

### Step 7 — Hand to functional consultant

At this point the app is live. Share the **UI route**:

```
https://material-risk-ui.<cf-domain>/
```

The UI asks "What materials are at risk for the next activity?" and the agent returns the 7-section report. No Joule needed for this path — pure A2A via the custom chat UI.

To switch from mock data to **live S/4 Business Accelerator Hub sandbox**:

```bash
# One-time: add the S4 API key to CF env (or bind as a UPS)
cf set-env material-risk-agent IBD_TESTING ""         # turn off mock
cf set-env material-risk-agent IBD_LIVE_S4 "1"
cf set-env material-risk-agent S4_API_KEY "<your-business-accelerator-hub-apikey>"
cf set-env material-risk-agent S4_BASE_URL "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap"
cf set-env material-risk-agent S4_PLANT "1710"
cf restage material-risk-agent
```

---

## Part 3 — Joule 2.0 Integration (pro-code A2A path)

This section follows the architecture from SAP Community blog by Felix Bartler and the official "Integrating Joule with SAP Solutions" PDF.

### Prerequisite check

- [ ] CF agent is deployed and card returns HTTP 200
- [ ] BTP subaccount has Joule entitlement + Build Work Zone Standard
- [ ] Cloud Identity Services (IAS) tenant exists and is trusted by the subaccount

### Step 8 — Configure IAS trust in BTP subaccount

1. BTP Cockpit → Subaccount → **Security → Trust Configuration**
2. Add your IAS tenant (`https://<ias-tenant>.accounts.ondemand.com`)
3. Set as **Default Identity Provider** for the subaccount
4. Download the IAS metadata XML (from IAS admin → Applications & Resources → Tenant Settings → Metadata)
5. Upload it as the **Custom Identity Provider** in BTP trust config

### Step 9 — Create two IAS apps (Proxy + Custom Agent)

Open the **IAS Admin Console** (`https://<ias-tenant>.accounts.ondemand.com/admin`).

#### App 1: A2A Proxy App (reusable across all agents)

1. **Applications & Resources → Applications → Create Application**
   - Type: **OpenID Connect**
   - Name: `A2A_Proxy_App`
2. In the app, go to **APIs → Add API**
   - Name: `a2a_proxy_app_api`
   - Save
3. Go to **Dependencies → Add Dependency**
   - Name: `joule-to-proxy` (**exact name — this is MANDATORY**)
   - Target: Joule's own IAS app (SAP-managed — find it in the IAS app list)

#### App 2: Custom Agent App (one per agent)

1. Create another OIDC app: `A2A_Custom_Agent_App` (or `Material_Risk_Agent_App`)
2. Add API: `a2a_custom_agent_app_api`
3. Note the **Client ID** — this becomes `IAS_AUDIENCE` in the agent's env
4. In App 1 (Proxy), go to **Dependencies → Add Dependency**
   - Name: `proxy-to-material-risk` (**this name must match the `tokenService.body.resource` URN suffix in the BTP destination**)
   - Target: `A2A_Custom_Agent_App`

### Step 10 — Create BTP Destination for Joule → Agent

In BTP Cockpit → Subaccount → **Connectivity → Destinations**:

```
Name:                MATERIAL_RISK_AGENT
Type:                HTTP
URL:                 https://material-risk-agent.<cf-domain>
Authentication:      OAuth2JWTBearer
Client ID:           <A2A_Proxy_App client ID>          ← from IAS App 1
Client Secret:       <A2A_Proxy_App client secret>
Token Service URL:   https://<ias-tenant>/oauth2/token
Additional Properties:
  apptoapp:                  true
  x_user_token.jwks_uri:     https://<ias-tenant>/oauth2/certs    ← CRITICAL — omitting silently drops to technical auth
  tokenService.body.resource: urn:sap:identity:application:provider:name:proxy-to-material-risk
```

> **Top gotcha:** If `x_user_token.jwks_uri` is missing, the user's identity is silently dropped and you get a service-to-service (technical) call instead of a user-propagated call. The agent won't error — it'll just see `sub="service-account"`. Always include this property.

Test the destination: click **Check Connection** — expect HTTP 200 (the agent card).

### Step 11 — Configure IAS auth in the agent

**Shortcut:** use the interactive helper script (prompts for IAS tenant + Client ID):

```bash
./scripts/setup-ias-env.sh
```

Or run the commands manually:

```bash
cf set-env material-risk-agent AGENT_AUTH_MODE      "ias"
cf set-env material-risk-agent IAS_JWKS_URI         "https://<ias-tenant>/oauth2/certs"
cf set-env material-risk-agent IAS_ISSUER           "https://<ias-tenant>"
cf set-env material-risk-agent IAS_AUDIENCE         "<A2A_Custom_Agent_App client ID>"
cf set-env material-risk-agent IAS_REQUIRED_API     "a2a_custom_agent_app_api"
cf restage material-risk-agent
```

### Step 12 — Deploy the Joule capability

**Shortcut:** use the helper script (validates agent card reachability first):

```bash
BTP_SUBACCOUNT_ID=<subaccount-GUID> ./scripts/deploy-joule-capability.sh
```

Or run the CLI command directly:

```bash
# Requires Joule CLI (install from SAP Tooling page)
cd "/Users/I778959/Documents/SAP VsCode/Agenthon/Savic+Adarsh/Project Material Availability & Supply Risk Agent/joule"

joule capability deploy \
  --path ./da.sapdas.yaml \
  --subaccount <subaccount-GUID>

# The subaccount GUID is in BTP Cockpit → Subaccount overview → "ID" field
```

After deploy, open the Joule panel and type:  
> "Will the structural steel for the Level 3 Slab Pour be available on time?"

You should see the 7-section risk report returned in the Joule chat.

---

## Part 4 — Hop 2: Principal Propagation to S/4HANA

This only applies once the Agent Gateway MCP path is active (production mode — no `IBD_TESTING`, no `IBD_LIVE_S4`).

### On-premise S/4HANA (your scenario — e.g. Adarsh Tokyo → ADV client 100)

1. **Cloud Connector side (SCC Admin Console → `https://localhost:8443`)**:
   - Add system mapping: Virtual host `material-risk-s4:443` → Real host `<S4-hostname>:443`
   - Expose OData services: `/sap/opu/odata/sap/API_MATERIAL_STOCK_SRV/` (and others)
   - Set "Principal Type" to `X.509 Certificate` with **Distinguished Name** propagation

2. **BTP Destination for S/4**:
   ```
   Name:          S4_MATERIAL_RISK
   Type:          HTTP
   URL:           https://material-risk-s4:443
   Authentication: PrincipalPropagation
   ProxyType:     OnPremise
   ```

3. **S/4HANA ABAP side (requires Basis access)**:
   - STRUST → upload Cloud Connector's CA certificate
   - CERTRULE → map certificate DN to S/4 user (by email field)
   - `/IWFND/MAINT_SERVICE` → activate and publish each OData service
   - `icm/HTTPS/verify_client` → set to `1` (require client cert)
   - Demo users must exist in S/4 (SU01) with email matching IAS login

4. **Agent agent code already handles hop 2**: `s4_client.py` reads `S4_DESTINATION`, uses BTP Destination Service to exchange the user's IAS JWT for an S/4-scoped token via the destination's PrincipalPropagation auth.

### Public Cloud S/4HANA

Use `Authentication: OAuth2SAMLBearerAssertion` in the BTP destination instead. The SAML assertion carries the user identity to S/4's Communication System (SAP_COM_0008).

---

## Part 5 — Quick-Reference Service Table

| Service | BTP Service Name | Plan | Created via |
|---------|-----------------|------|-------------|
| AI Core | `aicore` | `extended` | Service Marketplace → Create |
| Destination | `destination` | `lite` | Service Marketplace → Create |
| Connectivity | `connectivity` | `lite` | Service Marketplace → Create |
| XSUAA | `xsuaa` | `broker` | Service Marketplace → Create |
| IAS | `identity` | `application` | Service Marketplace → Create |
| Cloud Connector | (on-prem tool) | — | Download + install on-prem |
| Joule | `joule` | (entitled) | Service Marketplace → Subscribe |

---

## Part 6 — Troubleshooting Checklist

| Symptom | Most likely cause | Fix |
|---------|-------------------|-----|
| `cf push` fails on buildpack | Node/Python version mismatch | Check `runtime.txt` (must be `python-3.11.x`) and `package.json` engines |
| Agent card returns 503 | `sap_cloud_sdk` import error at boot | Check CF logs: `cf logs material-risk-agent --recent`; the try/except shim should catch it |
| Joule shows "no capability matched" | Scenario description too narrow | Edit `material_risk_capability/scenarios/material_risk_scenario.yaml` — broaden intent description |
| Destination check fails (HTTP 401) | Missing `x_user_token.jwks_uri` or wrong audience | Re-check destination Additional Properties |
| `/whoami` returns `sub: unknown` | `AGENT_AUTH_MODE` not set to `ias` | `cf set-env material-risk-agent AGENT_AUTH_MODE ias && cf restage` |
| S/4 OData returns 403 | Principal propagation not configured | Verify Cloud Connector mapping + STRUST + CERTRULE in S/4 |
| `IBD_LIVE_S4` returns 401 from sandbox | Wrong `S4_API_KEY` | Verify key in Business Accelerator Hub account |

---

*Last updated: 2026-10-21 | Owner: SAP BTP Build Team*
