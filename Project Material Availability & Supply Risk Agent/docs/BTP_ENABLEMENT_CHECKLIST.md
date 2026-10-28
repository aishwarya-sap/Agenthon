# BTP Enablement Checklist — Material Availability & Supply Risk Agent (one pager)

**Principle:** do every step in **BAI (our env) first and prove it**, then repeat the
**identical** step in the **Adarsh** landscape. Only tenant URLs, the S/4 system, and
hop-2 auth type differ. Tick BAI before touching Adarsh.

Legend: `[ ]` to do · **Gate** = don't proceed until this passes · Owner in (brackets)

---

### Phase A — Agent + real data (no identity yet)
- [ ] A1. `cf push -f manifest.yml` to the BAI CF space; `GET /.well-known/agent.json` returns the card. (us) **Gate: card resolves, protocolVersion 0.3.0.**
- [ ] A2. Set `IBD_LIVE_S4=1`, `S4_SERVICE_PROFILE=cloud`, `S4_BASE_URL`, `S4_API_KEY` (env only); run an analysis turn → report built from **real** sandbox data. (us) **Gate: real stock/PO/supplier data in the report.**
- [ ] A3. The custom chat UI (`material-risk-ui`) is up so a functional consultant can click through the CF agent before Joule is ready. (us)
- [ ] A4. Functional consultant signs off on the agent's output quality. (consultant)

### Phase B — Identity + Joule (hop 1)
- [ ] B1. Confirm IAS tenant is trusted by the subaccount (Security → Trust Configuration). (BTP admin)
- [ ] B2. In IAS, create **A2A_Proxy_App** (expose `a2a_proxy_app_api`) + **A2A_Custom_Agent_App** (expose `a2a_custom_agent_app_api`). (IAS admin)
- [ ] B3. Dependencies: `joule-to-proxy` on the Joule app → Proxy; `proxy-to-material-risk` on Proxy → Custom-Agent. Add a client secret on the Proxy app. (IAS admin)
- [ ] B4. Create inbound destination `MATERIAL_RISK_AGENT` = `OAuth2JWTBearer` (Proxy app creds, `apptoapp=true`, `x_user_token.jwks_uri`, `resource=...:proxy-to-material-risk`). (BTP admin)
- [ ] B5. Set agent env `AGENT_AUTH_MODE=ias`, `IAS_ISSUER`, `IAS_AUDIENCE`, `IAS_REQUIRED_API`; redeploy. (us)
- [ ] B6. Deploy the Joule capability from `joule/` (`joule login --no-app-tid` → `joule capability deploy --path ./da.sapdas.yaml`). (us) **Gate: scenario appears in Joule.**
- [ ] B7. Ask the agent via Joule; `ENABLE_WHOAMI=1` → `/whoami` shows a valid IAS token (correct aud/iss/mail) and boundary validation **pass**. (us) **Gate: identity reaches the agent as the real user.**

### Phase C — S/4 as the user (hop 2)
- [ ] C1. Bind `destination` + `connectivity` + `identity` service instances to the agent app. (BTP admin)
- [ ] C2. Outbound destination to S/4: **public cloud → OAuth2SAMLBearerAssertion** (BAI) / **Adarsh on-prem → PrincipalPropagation + ProxyType=OnPremise via Cloud Connector**. `x_user_token.jwks_uri` set. (BTP admin)
- [ ] C3. (On-prem only) Cloud Connector principal propagation: system cert + trust, CA in STRUST, cert→user mapping rule, `icm/HTTPS/verify_client`, OData services active (`/IWFND/MAINT_SERVICE`). Switch agent to `S4_SERVICE_PROFILE=onprem`. (Basis + us)
- [ ] C4. Demo users exist in the S/4 client (ADV client 100) with **emails matching their IAS logins**, and hold the read authorizations. (Basis)
- [ ] C5. `/whoami` S/4 canary returns data; the S/4 access log shows the **human's** id, not a technical user. (us) **Gate: no `authTokens[0].error`; data filtered by the user's roles.**

### Phase D — Replicate on Adarsh + go-live
- [ ] D1. Repeat A1–C5 in the Adarsh subaccount `ADARSH-CUSTOM-AI` (Tokyo region, space `AI-DEV`; their IAS/Joule/CF/S4/Cloud Connector; `S4_SERVICE_PROFILE=onprem`). (us + Adarsh)
- [ ] D2. Switch `ENABLE_WHOAMI` **off**; confirm advisory-only + HITL still enforced. (us)
- [ ] D3. Demo dry-run end to end in Adarsh DEV. (all)

### Phase E — Decision/approval persistence (HANA Cloud)
- [ ] E1. HANA Cloud instance + schema available in the subaccount (provision if absent). (Adarsh DBA / BTP admin)
- [ ] E2. Create `ZAGENT_DECISION_LOG` (+ vector table) under a technical user with an **INSERT/SELECT-only** role. (Adarsh DBA)
- [ ] E3. Enable the HANA Cloud Vector Engine (semantic recall of prior decisions). (Adarsh DBA)
- [ ] E4. Share HANA service key or bind the HANA (HDI/schema) service to the CF app; set `MEMORY_BACKEND=hana`. (us + Adarsh)

---

**What goes in the Adarsh confirmation mail = the prerequisites behind B1–B4, C2–C4** (IAS
tenant+admin, Joule entitlement/A2A-in-region, roles/Booster, service instances, Cloud
Connector principal propagation, OData activation, user email mapping, model-in-catalog,
CF Space Developer). Send it only after Phases A–C pass in BAI, so we ask from experience.

> **Adarsh handover gaps flagged (2026-10-20):** the handover listed infra only — no IAS
> tenant, no BTP↔IAS trust, no Joule entitlement/instance/roles. The whole identity + Joule
> layer is absent and blocks Phase B. "CC reachable" = technical reachability only, NOT
> principal propagation (still needs ABAP trust + cert→user mapping + OData activation).
