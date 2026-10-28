# Adarsh Agenthon — Procurement Bottleneck & Decision Agent — Master Reference

> Single reference for the engagement: what's built, how Joule + principal propagation
> work, first-timer BTP enablement steps, the BAI end-to-end test with the SAP Business
> Accelerator Hub, test/demo workflows, and the SAP BTP checklist status with what's
> pending. Last updated 2026-10-21.
>
> **Secrets rule:** no API keys, passwords, or client secrets live in this file or the
> repo — only via `.env` (gitignored) / Cloud Foundry `VCAP_SERVICES`. The Accelerator
> Hub API key and the BTP password were shared in chat → **rotate both** after the event.

---

## 1. Engagement snapshot

- **Client:** Adarsh Developers (India). Real-estate developer. (Not JCI — template leftover.)
- **Event:** Agenthon, 28 Oct 2026, SAP Labs Bangalore.
- **This agent:** Critical-Path Procurement Consequence Agent (a.k.a. "Procurement Bottleneck & Decision"). Advisory, read-only. Built mock-first, SAP Agent Golden Path layout.
- **Second agent (separate repo):** Project Material Availability & Supply Risk (built; see its own memory/repo).
- **Build status:** 124 tests passing, ~92% coverage. IAS inbound auth + `/whoami` diagnostic added 2026-10-20. Live S/4 reads pending wiring to the Accelerator Hub (API list now provided).

### Environments
| | BAI (our dev/test) | Adarsh client DEV |
|---|---|---|
| Purpose | build + end-to-end test first | integration + demo |
| AI Core creds | `/Users/I778959/Documents/MaxForum/BAI-AICore-Credentials.md` (used at `cf push`, never copied into repo) | Adarsh AI Core (plan Extended, RG `grounding`) |
| S/4 data | **SAP Business Accelerator Hub sandbox** (APIKey) | S/4HANA **on-prem** ABAP (SID ADV, client 100) via Cloud Connector |
| Region | (BAI) | **Tokyo (ap)** — chosen because India BTP region is thin on AI/Joule services; confirm Joule A2A is live in-tenant + prod data-residency |

---

## 2. Architecture

```
          Joule (orchestrator)                 Our agent (Cloud Foundry)
 user ──► routes to capability ──A2A──► A2A server (Starlette/JSON-RPC)
          scenario+function                │
                                           ├─ deterministic core: 13 tools, 3 skills,
                                           │  4-dim consequence simulation, 9 HITL checkpoints
                                           ├─ 2 bounded LLM touch-points (intent, verdict) via AI Core
                                           └─ reads S/4 (advisory, read-only)
```

- **Advisory-only:** no POST/PATCH/DELETE to SAP, no `BAPI_PO_CREATE1`. Only side effects (after HITL approval) are an institutional-memory decision log + a mock SPA notification.
- **Connectivity modes** (`app/mcp_tools.py` / `app/tools.py`): `mock` (IBD_TESTING, offline) | `gateway` | `cloud`/`onprem`. We are adding an **Accelerator Hub** read path for BAI end-to-end.
- **Inbound auth** (`app/agent_executor.py` + `app/auth_ias.py`): `AGENT_AUTH_MODE` = `mock` | `ias` | `xsuaa`. Joule sends an **IAS** token → use `ias`.
- **Diagnostics:** `GET /whoami` (gated by `ENABLE_WHOAMI`, off in prod) shows the inbound token claims, boundary-validation result, and an S/4 canary — to pinpoint which identity hop breaks.

---

## 3. How Joule 1.0 integration actually works (re-analysed from the 3 blogs + the Integration PDF)

Sources: `Agenthon/Savic+Adarsh/files/blog.docx` (B1 Connect, B2 Propagate) + B3 "Secure with IAS" + SAP PDF "Integrating Joule with SAP Solutions".

### 3.1 You do NOT paste a skill into a UI (pro-code route)
- The agent (business logic) stays on **Cloud Foundry**.
- What goes "into Joule" is a thin **capability** authored as YAML and deployed via the **Joule CLI**:
  - **scenario** = the skill's entry shell; its *description* drives Joule's intent routing.
  - **function** = the step that calls our agent (`action: agent-request` → `system_alias` → BTP destination → remote agent).
- Files (already sketched in `joule/`): `da.sapdas.yaml`, `procurement_bottleneck_capability/capability.sapdas.yaml`, `scenarios/*.yaml`, `functions/*.yaml`.
- Deploy: `joule login --no-app-tid` → `joule deploy -c -n "procurement_bottleneck_test"` (sandbox assistant) → later `joule update "sap_digital_assistant" --capability-file capability.sapdas.yaml` (standard assistant).
- **Gotchas (blog-confirmed):** namespace MUST be `joule.ext` (else Tenant-Admin 5013/5014); capability schema ≥ 3.27.0; Joule CLI ≥ 2.0.2 with `--no-app-tid` (else `AUTH_FETCH_TOKEN_FAILED`); roles `end_user`, `capability_admin`, `extensibility_developer`; after editing destinations, redeploy the capability (Joule caches destinations).

### 3.2 Licensing (confirm with SAP account team — not asserted from memory)
- Need Joule **entitled** on the subaccount, **with pro-code / A2A extensibility** (not just the standard assistant).
- For pro-code A2A you do **not** need Joule Studio or SAP Build Process Automation (blog-confirmed) — those are only the low-code Skill Builder.
- Separately need **AI Core / Generative AI Hub** + AI-unit consumption for the model.

### 3.3 Identity chain (principal propagation) — two token exchanges
```
User (IAS login)
  → Joule  → [JWT-Bearer app2app]  → A2A Proxy IAS app
           → [JWT-Bearer app2app]  → Custom-Agent IAS app
  → agent (CF) validates the IAS user token
  → [HOP 2] → S/4  (as the real user; S/4 roles filter the data)
```
- Joule's own IAS app is SAP-managed (no creds) → an intermediate **Proxy IAS app** we control provides the control point.
- **Hop 1 (Joule → agent)** inbound destination = `OAuth2JWTBearer`, uses the **Proxy app** creds, `apptoapp=true`, `x_user_token.jwks_uri` (omit → silently drops to technical auth), `tokenService.body.resource=urn:sap:identity:application:provider:name:<proxy-to-target dep>`.
- **Agent validates** the IAS token: JWKS/RS256, `iss`, `exp`, and audience via the `ias_apis` claim (contains the agent app's API) or `aud`. (`app/auth_ias.py`.)
- **Hop 2 (agent → S/4) DIFFERS BY EDITION:**
  - **Public Cloud:** destination `OAuth2SAMLBearerAssertion`, Communication User/System/Arrangement, `userIdSource=mail`. Agent does a 3-call dance (dest token → resolve with `X-user-token` → call S/4 with the opaque token) and must **check `authTokens[0].error` even on HTTP 200**.
  - **Adarsh = ON-PREM ABAP:** destination `Authentication=PrincipalPropagation`, `ProxyType=OnPremise`, via **Cloud Connector**. Activate OData via `/IWFND/MAINT_SERVICE`. User mapped by **email** → ADV SU01 user.

---

## 4. First-timer BTP enablement — detailed steps

> Do these in the **BAI** subaccount first (to rehearse), then repeat in **Adarsh DEV**.
> Confidence: steps are blog/PDF-grounded; exact field names/region hosts vary — verify in your tenant. Nothing here needs real secrets written down.

### 4.1 Trust: BTP subaccount ↔ IAS
1. BTP Cockpit → your subaccount → **Security → Trust Configuration**.
2. **Establish Trust** to the IAS (SAP Cloud Identity Services) tenant (OIDC). Note the IAS tenant URL (`https://<tenant>.accounts.ondemand.com`).

### 4.2 IAS: two OIDC apps + dependencies (hop 1)
1. IAS admin panel (`<tenant>.accounts.ondemand.com/admin`) → **Applications & Resources → Applications**.
2. **Create** `A2A_Proxy_App` (OpenID Connect). Expose an API, e.g. `a2a_proxy_app_api`. *(Reusable across all agents.)*
3. **Create** `A2A_Custom_Agent_App` (OpenID Connect). Expose an API, e.g. `a2a_custom_agent_app_api`. *(Its client id = `IAS_AUDIENCE`.)*
4. On the **Joule app** (`das-ias-<subdomain>`) → **Dependencies → Add**, name exactly **`joule-to-proxy`** → `A2A_Proxy_App` + its API. (One-time.)
5. On **`A2A_Proxy_App`** → Dependencies → Add **`proxy-to-target`** → `A2A_Custom_Agent_App` + its API. *(Name must match the destination `resource` URN below.)*
6. On **`A2A_Proxy_App`** → **Client Authentication** → Add secret (tick OIDC/token boxes). Note clientId/secret (used by the inbound destination).

### 4.3 CF: service instances the agent binds
In the CF space, create + bind to the agent app: `aicore` (model), `destination`, `connectivity` (for on-prem via Cloud Connector), and an **identity** (IAS) service instance (for the agent's own service-to-service auth). XSUAA only if a component still needs it — inbound user auth is IAS.

### 4.4 Destinations
- **Inbound (hop 1, Joule → agent)** — name `PROCUREMENT_AGENT` (must match the capability `system_alias`):
  ```
  Type=HTTP  ProxyType=Internet  Authentication=OAuth2JWTBearer
  URL=<CF agent URL>
  clientId=<A2A_Proxy_App client id>   clientSecret=<A2A_Proxy_App secret>   # PROXY app
  tokenServiceURL=https://<ias-tenant>/oauth2/token   tokenServiceURLType=Dedicated
  apptoapp=true   tokenService.body.token_format=jwt
  x_user_token.jwks_uri=https://<ias-tenant>/oauth2/certs
  tokenService.body.resource=urn:sap:identity:application:provider:name:proxy-to-target
  tokenService.body.client_id=<A2A_Proxy_App client id>
  tokenService.addClientCredentialsInBody=false
  ```
- **Outbound (hop 2, agent → S/4) — Adarsh on-prem:**
  ```
  Type=HTTP  ProxyType=OnPremise  Authentication=PrincipalPropagation
  URL=https://vhdvladvci:44300        # Cloud Connector virtual host:port
  ```
- **Accelerator Hub (BAI end-to-end, APIKey)** — see §5. This is server-side APIKey, not principal propagation; it proves data-fetch + reasoning + UI end-to-end, not identity.

### 4.5 Cloud Connector principal propagation (Adarsh on-prem — Basis task on ADV)
"Reachable" in CC ≠ principal propagation. Additionally needed: CC configured for **principal propagation** (system certificate + trust); the CC CA trusted in ADV **STRUST**; **rule-based certificate→user mapping** (CERTRULE / external ID); HTTPS client certs on the ICM (`icm/HTTPS/verify_client`); procurement **OData services activated** (`/IWFND/MAINT_SERVICE`); **demo users in client 100 with emails matching their IAS logins**.

### 4.6 Joule enablement
1. Ensure a **Joule base instance** on the subaccount (run the **Joule setup Booster** if not done).
2. Assign roles: `end_user`, `capability_admin`, `extensibility_developer`.
3. Install **Joule CLI ≥ 2.0.2**. `joule login --no-app-tid` (create an IAS app for CLI creds with the `Cli2Joule` dependency, per B1).
4. Deploy the capability from `joule/` (see §3.1).

### 4.7 AI Core
Confirm `anthropic--claude-4.5-sonnet` (+ a haiku fallback) appears in Generative AI Hub for the resource group (`grounding` on Adarsh). Bind `aicore` to the agent.

---

## 5. BAI end-to-end with SAP Business Accelerator Hub

- **Base URL:** `https://sandbox.api.sap.com/s4hanacloud/...` *(confirm exact path per service)*.
- **Auth:** header `APIKey: <key>` — **env only** (`S4_API_KEY`), never committed. Key was shared in chat → rotate.
- **Env (BAI):** `IBD_TESTING` unset, `SAP_MODE=accelerator_hub` (to be added), `S4_BASE_URL`, `S4_API_KEY`.

### 5.1 Tool → OData service map (client-provided)
| Agent tool / need | OData service | Notes |
|---|---|---|
| PR→PO chain | `OP_API_ALIGN_PURREQN_SRV_0001` + `OP_PURCHASEORDER_0001` | PR to PO alignment; PO `ELIKZ` delivery-complete flag |
| PO details / approval status | `OP_PURCHASEORDER_0001`, `OP_PURCHASEREQUISITION_0001` | |
| PO change events (real-time) | `OP_PURCHASEOREVENTS` (event: `OP_PURCHASEORDEREVENTS`) | subscribe to created/changed/released |
| Supplier silence / GRN | `OP_API_MATERIAL_DOCUMENT_SRV` | GRN movement type **101** per PO → last supplier activity date → silence + vendor performance |
| Material stock | `OP_API_MATERIAL_STOCK_SRV` | |
| Vendor / supplier master | `OP_API_BUSINESS_PARTNER_SRV` | name/address/account group/purch-org; vendor performance + alt-source |
| Purchasing info record (alt source) | `OP_API_INFORECORD_PROCESS_SRV_0001` | |
| Contracts | `sap-s4-OP_PPS_PURCHASECONTRACT_0001-v1` | |
| Source of supply (EORD) | *none directly* | resolve via inforecord + contract, filter by **active validity dates** |

- **Polling vs events:** combine scheduled polling of `OP_PURCHASEORDER_0001` with the `OP_PURCHASEORDEREVENTS` subscription (fire on GRN/PO change) for silence detection.
- **Derived fields** (silence_duration_days, composite risk, float/critical-path, consequence €): computed **in-agent** from the raw reads — the standard APIs don't return them.
- **Field mapping caveat:** entity-set and property names must be confirmed against each service's `$metadata` before wiring — do NOT hardcode guessed field names. Plan: probe `$metadata` with the APIKey, then map.

### 5.2 VERIFIED against the live sandbox (2026-10-21)
The APIKey resolves the **S/4HANA Cloud `API_*`** services (200), NOT the `OP_*` on-prem names (403 in sandbox). So: **BAI test = cloud `API_*`; Adarsh prod = on-prem `OP_*`** — the connectivity layer must be config-driven (service names per env). Confirmed base + mechanics:
- Base: `https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap`; headers `APIKey: <key>`, `Accept: application/json`, `--compressed`. OData **V2**: collections in `d.results`, dates as `/Date(epochMillis)/`.
- Resolved (200): `API_PURCHASEORDER_PROCESS_SRV`, `API_PURCHASEREQ_PROCESS_SRV`, `API_MATERIAL_DOCUMENT_SRV`, `API_BUSINESS_PARTNER`, `API_INFORECORD_PROCESS_SRV`, `API_PURCHASECONTRACT_PROCESS_SRV`, `API_MATERIAL_STOCK_SRV`. (403: `API_PURCHASINGINFORECORD_PROCESS_SRV`, scheduling-agreement — not entitled.)

Verified entity/field mapping (agent field ← real OData field):
| Agent need | Entity set | Real fields |
|---|---|---|
| PR→PO chain / PO header | `A_PurchaseOrder` | PurchaseOrder, Supplier, PurchaseOrderDate, PurchasingProcessingStatus, PurchasingDocumentDeletionCode |
| PO item | `A_PurchaseOrderItem` | PurchaseOrder, PurchaseOrderItem, Material, Plant, MaterialGroup, OrderQuantity, NetPriceAmount, **IsCompletelyDelivered** (=ELIKZ), PurchaseContract, PurchasingInfoRecord, PurchaseRequisition |
| Delivery due date | `A_PurchaseOrderScheduleLine` | PurchasingDocument, PurchasingDocumentItem, **ScheduleLineDeliveryDate**, ScheduleLineOrderQuantity, ScheduleLineCommittedQuantity |
| GRN / supplier silence | `A_MaterialDocumentItem` (+ header PostingDate) | **GoodsMovementType (=101)**, PurchaseOrder, PurchaseOrderItem, Material, Supplier, QuantityInEntryUnit |
| Vendor master | `A_Supplier` / `A_SupplierPurchasingOrg` | Supplier, SupplierName, **PurchasingIsBlocked**, SupplierAccountGroup / MaterialPlannedDeliveryDurn, PurchasingIsBlockedForSupplier |
| PR item / approval | `A_PurchaseRequisitionItem` | PurchaseRequisition, PurReqnReleaseStatus, ProcessingStatus, ExternalApprovalStatus, Supplier, FixedSupplier, PurchasingInfoRecord |
| Alt source + validity | `A_PurchasingInfoRecord` | PurchasingInfoRecord, Supplier, Material, **AvailabilityStartDate/EndDate**, IsRegularSupplier, IsDeleted |
| Contract + validity | `A_PurchaseContract` / `A_PurchaseContractItem` | PurchaseContract, Supplier, **ValidityStartDate/EndDate**, PurchaseContractTargetAmount / ContractNetPriceAmount, Material |

**Fields NOT in the standard API (label "simulated" or source elsewhere):** milestone **penalty clause / liquidated damages** (not in contract OData → penalty stays mock/Excel), **vendor on-time-rate / delivery-risk score** (derive heuristically, label simulated), and **Project System / WBS** (float, milestone payment, team cost — **no PS API in the list/sandbox** → keep on the Excel/mock project adapter). PO/supplier/GRN/info-record/contract are real; project + penalty + vendor-risk are mock/derived — consistent with the agent's live/simulated labelling.

---

## 6. Test flows & workflows

### 6.1 Offline (done — CI gate)
`cd assets/procurement-bottleneck-agent && IBD_TESTING=1 pytest` → 124 tests, ≥70% coverage (currently ~92%). Covers tools, skills, simulation, HITL, resilience, memory, observability, A2A server, injection gate, red-team, IAS auth, `/whoami`.

### 6.2 BAI end-to-end (Accelerator Hub real data)
1. Set `S4_BASE_URL`, `S4_API_KEY`, `SAP_MODE=accelerator_hub`, unset `IBD_TESTING`.
2. Probe `$metadata` for each service → finalise field mapping.
3. `python -m app` → `curl /.well-known/agent.json` (card), POST a query → full 7-section report from **real** sandbox data.
4. `ENABLE_WHOAMI=1` → `GET /whoami` shows auth mode + S/4 canary reachable.

### 6.3 Functional-consultant UI testing
Host the agent + a custom chat UI on CF so a functional consultant can click through. (Use the `chat-ui` + `cf-deploy` skills.) Give them the seed/demo flow: ask about a stuck critical-path PO → review the consequence scorecard + ranked recommendation → exercise the HITL approve/cancel gate.

### 6.4 Principal-propagation layered test (BAI then Adarsh) — stop at first red
1. IAS login → user JWT (not client-credentials).
2. Agent boundary accepts it (`/whoami`: aud/iss/`ias_apis` ok).
3. Agent receives `Authorization: Bearer` with correct `mail`.
4. Destination resolves (hop 2) with no `error`.
5. S/4 returns data **as the user** (ADV access log shows the human).
6. User's S/4 authorizations correct (no 403 after identity works).

### 6.5 Demo dry-run (before 28 Oct)
Rehearse the end-to-end in BAI with the UI; have the on-prem fallback (named technical user read path) documented in case principal propagation isn't fully wired on the day.

---

## 7. Deployment sequence (CF — you run it)

1. Offline suite green (§6.1).
2. `cf login -a <api> --sso` (always SSO, never TOTP).
3. Create/bind services: `aicore`, `destination`, `connectivity`, `identity` (+ `xsuaa` if needed).
4. `cf set-env` AI Core creds from the BAI creds file (bind at push, never copy into repo); set `AGENT_AUTH_MODE`, `IAS_*`, `S4_*`; `ENABLE_WHOAMI=1` for test only.
5. `cf push` → `curl /.well-known/agent.json`.
6. Deploy the custom UI (chat-ui/cf-deploy skills); hand URL to the functional consultant.
7. In parallel: IAS apps + destinations + Joule capability deploy (§3.1) → Joule integration test.
8. Before prod: `ENABLE_WHOAMI` off; principal propagation verified; checklist §9 closed.

---

## 8. Pending — your side vs build/testing

### 8.1 Client / BTP (the email asks)
Joule entitled + **A2A enabled in Tokyo**; IAS tenant + trust + admin access (longest lead); Joule roles + Booster; licensing covers pro-code A2A; destination+connectivity+identity instances; on-prem CC principal propagation + STRUST + cert→user mapping + ICM; procurement OData activated; **demo users in client 100 with emails matching IAS logins**; `claude-4.5-sonnet` in catalog; CF Space Developer rights; which system/client (or Accelerator Hub) for demo data. **Rotate the shared API key + BTP password.**

### 8.2 Build (remaining)
- [ ] Wire the Accelerator Hub live reads (map the 8 tools to §5 services; confirm fields via `$metadata`).
- [ ] Add `SAP_MODE=accelerator_hub` connectivity path (APIKey) in `tools.py`.
- [ ] Custom chat UI (`chat-ui` skill) + CF deploy prep (`cf-deploy`/`deploy-plan`).
- [ ] Implement hop-2 on-prem PrincipalPropagation path for Adarsh (replaces `build_live_tools` stub).
- [ ] Prepare the clean sharable client repo (§ below).

### 8.3 Testing (remaining)
- [ ] BAI end-to-end with real Accelerator Hub data (§6.2).
- [ ] Functional-consultant UI pass (§6.3).
- [ ] Principal-propagation layered test in BAI, then Adarsh DEV (§6.4).
- [ ] Demo dry-run (§6.5).

### 8.4 Sharable client repo (prod-ready bar)
Clean history, no secrets (scan), `.env.example` only, README + run/deploy, all guardrails on (advisory-only, HITL, injection gate, IAS auth), governance docs in `governance/`, tests green, `/whoami` gated off by default. Build in a worktree/branch, security-review before pushing to the client remote.

---

## 9. agent build checklist (reference) — status & pending

Source: `/Users/I778959/Documents/SAP VsCode/architecture_engineering_portal/SAP BTPAIAgentChecklist-main/Agent_Checklist_Master_List_v5.md`.

**The 7 ❌ are tenant-only (cannot close offline):**
- 2.2 / 2.4 / 2.5 — model benchmarking agent + dashboard + ongoing re-eval
- 4.1 / 4.2 — LLM Calculator + metering infrastructure
- 5.1 — Responsible-AI Safety Dashboard
- 7.4 — human cross-functional sign-off

**Key ⚠️ that this phase closes or advances:**
- 3.1/3.2/3.3 — live Document Grounding + RAG (HANA vector on Adarsh; RagEval on live corpus)
- 6.1/6.2 — Agent-Builder exception + security review, tenant re-registration
- 7.1/7.2/7.5 — AET interim, **live integration (closed by `cf push` + Accelerator Hub)**, prod-parity regression env
- 8.4 — p50/p95/p99 under load
- 10.1/10.3/10.4/10.5 — drift monitors (post-go-live)

**⏭️ N/A (scope):** 1.2, 1.4, 2.3, 3.5, 4.3, 4.4, 7.3, 8.3, 9.1, 9.2.

**Checklist action items for this phase:** live integration validation (7.2) via CF + Accelerator Hub; file the 6.1/6.2 exception; stand up RAG on live data (3.x); schedule the tenant-side L0-2/L0-5 runs with the client's AI governance.

---

## 10. Key files

| Path | What |
|---|---|
| `assets/procurement-bottleneck-agent/app/` | agent code (15 modules + `auth_ias.py`) |
| `app/auth_ias.py`, `agent_executor.py` | IAS inbound auth (`AGENT_AUTH_MODE=ias`) |
| `app/main.py` → `/whoami` | identity-hop diagnostic (gated) |
| `app/tools.py`, `mcp_tools.py` | 13 tools + connectivity modes (Accelerator Hub path to add) |
| `tests/` | 120 tests |
| `joule/` | Joule pro-code capability wrapper (deploy via Joule CLI) |
| `.env.example` | all env vars incl. `AGENT_AUTH_MODE`, `IAS_*`, `S4_*`, `ENABLE_WHOAMI` |
