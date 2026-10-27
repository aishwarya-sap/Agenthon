# BTP Enablement Checklist — Procurement Bottleneck Agent (one pager)

**Principle:** do every step in **BAI (our env) first and prove it**, then repeat the
**identical** step in the **Adarsh** landscape. Only tenant URLs, the S/4 system, and
hop-2 auth type differ. Tick BAI before touching Adarsh.

Legend: `[ ]` to do · **Gate** = don't proceed until this passes · Owner in (brackets)

---

### Phase A — Agent + real data (no identity yet)
- [ ] A1. `cf push` the agent to the BAI CF space; `GET /.well-known/agent.json` returns the card. (us) **Gate: card resolves.**
- [ ] A2. Set `SAP_MODE=accelerator_hub`, `S4_BASE_URL`, `S4_API_KEY` (env only); run an analysis turn → report built from **real** sandbox data. (us) **Gate: real PO/supplier data in the report.**
- [x] A3. Joule-style chat UI stood up (served at the agent's root URL, no `/ui` suffix) so a functional consultant can click through the CF agent before Joule is ready. (us) **Done — redeploy with `cf push` to pick it up.**
- [ ] A4. Functional consultant signs off on the agent's output quality. (consultant)

### Phase B — Identity + Joule (hop 1)
- [ ] B1. Confirm IAS tenant is trusted by the subaccount (Security → Trust Configuration). (BTP admin)
- [ ] B2. In IAS, create **A2A_Proxy_App** (expose `a2a_proxy_app_api`) + **A2A_Custom_Agent_App** (expose `a2a_custom_agent_app_api`). (IAS admin)
- [ ] B3. Dependencies: `joule-to-proxy` on the Joule app → Proxy; `proxy-to-target` on Proxy → Custom-Agent. Add a client secret on the Proxy app. (IAS admin)
- [ ] B4. Create inbound destination `PROCUREMENT_AGENT` = `OAuth2JWTBearer` (Proxy app creds, `apptoapp=true`, `x_user_token.jwks_uri`, `resource=...:proxy-to-target`). (BTP admin)
- [ ] B5. Set agent env `AGENT_AUTH_MODE=ias`, `IAS_ISSUER`, `IAS_AUDIENCE`, `IAS_REQUIRED_API`; redeploy. (us)
- [ ] B6. Deploy the Joule capability from `joule/` (`joule login --no-app-tid` → `joule deploy -c -n ...`). (us) **Gate: scenario appears in Joule.**
- [ ] B7. Ask the agent via Joule; `ENABLE_WHOAMI=1` → `/whoami` shows a valid IAS token (correct aud/iss/mail) and boundary validation **pass**. (us) **Gate: identity reaches the agent as the real user.**

### Phase C — S/4 as the user (hop 2)
- [ ] C1. Bind `destination` + `connectivity` + `identity` service instances to the agent app. (BTP admin)
- [ ] C2. Outbound destination to S/4: **public cloud → OAuth2SAMLBearerAssertion** (BAI) / **Adarsh on-prem → PrincipalPropagation + ProxyType=OnPremise via Cloud Connector**. `x_user_token.jwks_uri` set. (BTP admin)
- [ ] C3. (On-prem only) Cloud Connector principal propagation: system cert + trust, CA in STRUST, cert→user mapping rule, `icm/HTTPS/verify_client`, OData services active (`/IWFND/MAINT_SERVICE`). (Basis)
- [ ] C4. Demo users exist in the S/4 client with **emails matching their IAS logins**, and hold the read authorizations. (Basis)
- [ ] C5. `/whoami` S/4 canary returns data; the S/4 access log shows the **human's** id, not a technical user. (us) **Gate: no `authTokens[0].error`; data filtered by the user's roles.**

### Phase D — Replicate on Adarsh + go-live
- [ ] D1. Repeat A1–C5 in the Adarsh subaccount (their IAS/Joule/CF/S4/Cloud Connector; services use `OP_*` names). (us + Adarsh)
- [ ] D2. Switch `ENABLE_WHOAMI` **off**; confirm advisory-only + HITL still enforced. (us)
- [ ] D3. Demo dry-run end to end in Adarsh DEV. (all)
- [ ] D4. Close the tenant-side checklist items (benchmarking, safety dashboard, cross-functional sign-off — see `ADARSH_AGENTHON_REFERENCE.md` §9). (Adarsh AI governance)

---

**What goes in the Adarsh confirmation mail = the prerequisites behind B1–B4, C2–C4** (IAS
tenant+admin, Joule entitlement/A2A-in-region, roles/Booster, service instances, Cloud
Connector principal propagation, OData activation, user email mapping, model-in-catalog,
CF Space Developer). Send it only after Phases A–C pass in BAI, so we ask from experience.
