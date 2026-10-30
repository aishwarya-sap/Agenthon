# Adarsh Developers — Client Prerequisites for Go-Live

**Agents:** Procurement Bottleneck & Decision Agent · Project Material Availability & Supply Risk Agent  
**Landscape:** SAP S/4HANA on-prem (Tokyo release) + SAP BTP Cloud Foundry us10

---

## P0 — Must be done before any demo or deployment

### 1. BTP Subaccount access
| Item | Action |
|---|---|
| BTP subaccount for Adarsh | Confirm subaccount ID and region (must be us10 to match CF apps) |
| CF space for agents | Create space `PROD` (or `STAGING`) in the subaccount |
| CF org developer role | Grant `<sap-team>` SpaceDeveloper + OrgManager |
| AI Core service instance | `cf create-service aicore …` or confirm existing instance |

### 2. SAP AI Core credentials
- [ ] AI Core service instance created in the CF space
- [ ] Service key exported (`cf create-service-key aicore-instance aicore-key`)
- [ ] Credentials shared with delivery team via **secure channel only** (never email/chat)
- [ ] `clientid`, `clientsecret`, `url` (auth), `serviceurls.AI_API_URL` confirmed working

### 3. SAP Accelerator Hub / S4 OData
- [ ] SAP Accelerator Hub sandbox API key created at [api.sap.com](https://api.sap.com)  
  *(used for our environment test phase; replaced by on-prem in Phase C)*
- [ ] API key shared with delivery team via secure channel

---

## P1 — Required before IAS + Joule integration (Phase B)

### 4. IAS tenant access
| Item | Needed for |
|---|---|
| IAS tenant URL (`https://<tenant>.accounts.ondemand.com`) | Joule CLI login + A2A trust |
| IAS Application Administrator role | Creating A2A_Proxy_App + A2A_Custom_Agent_App |
| Joule IAS application name in the tenant | Wiring `joule-to-proxy` dependency |

**Who to contact at Adarsh:** IAS admin / Security team  
**Estimated effort:** 15–30 minutes in IAS admin panel (one-time)

### 5. BTP↔IAS trust
- [ ] IAS tenant registered as trusted IdP in the BTP subaccount  
  `BTP cockpit → Security → Trust Configuration → Add trust`
- [ ] Test: user can log into BTP with IAS credentials

---

## P2 — Required before S/4 on-prem connectivity (Phase C)

### 6. SAP Cloud Connector (SCC)
- [ ] SCC installed and running on the Adarsh network (v2.15+)
- [ ] SCC connected to the BTP subaccount  
  `SCC admin panel → Cloud → Add BTP Subaccount`
- [ ] Confirm connection shows **Connected** in BTP cockpit → Connectivity → Cloud Connectors

### 7. S/4HANA system exposure in SCC
Expose the following in SCC → Cloud To On-Premise → Access Control:

| Back-End Type | Protocol | Internal Host | Internal Port | Virtual Host | Virtual Port |
|---|---|---|---|---|---|
| ABAP System | HTTPS | `<s4-host>` | 443 | `adarsh-s4-prod` | 443 |

- [ ] Resources exposed (minimum):  
  `/sap/opu/odata/sap/MM_PUR_PO_MAINT_V2_SRV/*`  
  `/sap/opu/odata/sap/ME_PURCHASEREQ_MANAGE_SRV/*`  
  `/sap/opu/odata/sap/API_GOODSMVT_SRV/*`  
  `/sap/opu/odata/sap/PS_PROJECTDEF_SRV/*`  
  `/sap/opu/odata/sap/API_PROJECT_NETWORK_ACTV_SRV/*`
- [ ] Resources accessible: test with `ping` from SCC admin panel

### 8. Principal Propagation in S/4HANA (Basis task)
This is the step that maps a Joule/IAS user identity through to an S/4 named user.

- [ ] **System certificate generated** in SCC (`Administration → System Certificate`)
- [ ] **System cert imported into S/4 STRUST** (`STRUST → SSL client (Standard) → Import`)
- [ ] **Rule-based certificate-to-user mapping** configured in SCC:
  - Certificate attribute: `CN` → S/4 user ID mapping (or email-based)
- [ ] **SNC/SSL** enabled on the ICM in S/4 (`RZ10 → icm/server_port_*`)
- [ ] **OData services activated** in `/n/IWFND/MAINT_SERVICE` for all exposed APIs above

### 9. BTP Destination for on-prem S/4
Once SCC is connected, update (or create) the `MATERIAL_RISK_AGENT` and `PROCUREMENT_AGENT` destinations:

```
Name:              S4_ONPREM
Type:              HTTP
URL:               https://adarsh-s4-prod:443
ProxyType:         OnPremise
Authentication:    PrincipalPropagation
```

*(delivery team will do this in BTP cockpit → Destinations)*

---

## P3 — Demo users and data

### 10. S/4 user accounts
For go-live testing, create named users in S/4 with emails matching their IAS logins:

| Role | S/4 User | IAS Email |
|---|---|---|
| Purchasing HoD | `PROCUREMENT_HOD` | `<name>@adarsh.in` |
| Project Manager | `PROJECT_MGR_01` | `<name>@adarsh.in` |
| Read-only tester | `AGENT_VIEWER` | `<name>@adarsh.in` |

- [ ] Authorizations: MM, PS, standard procurement display roles
- [ ] Users can access OData APIs (test via `/sap/opu/odata/sap/MM_PUR_PO_MAINT_V2_SRV/$metadata`)

### 11. Sample data
- [ ] At least 2 active S/4 projects with open POs/PRs in overdue state (for realistic demo)
- [ ] At least 1 supplier with delayed GRN (to trigger the bottleneck detection scenario)
- [ ] Excel/CSV material requirement file (Phase 1 fallback) ready for upload if PS data is thin

---

## P4 — Decision/approval persistence (HANA Cloud)

The agent persists every recommendation and HoD approval to an **append-only** audit table on
**HANA Cloud** (`ZAGENT_DECISION_LOG`), and optionally uses the **HANA Cloud Vector Engine** for
semantic recall of prior decisions. This is the durable backend behind the agent's institutional
memory (today it runs in-process for the mock/demo; `MEMORY_BACKEND=hana` switches it over).

### 12. HANA Cloud instance + audit schema (DBA / BTP admin task)
- [ ] HANA Cloud instance available in the BTP subaccount (or provision one)
- [ ] Schema created for the agent (e.g. `ADARSH_AGENT`)
- [ ] Audit table `ZAGENT_DECISION_LOG` created (+ a vector table for semantic recall)
- [ ] **Technical user with an INSERT/SELECT-only role** on that schema (no UPDATE/DELETE — preserves
  the append-only audit guarantee)
- [ ] HANA Cloud **Vector Engine** enabled (needed for semantic recall)
- [ ] Credentials shared via a HANA **service key**, or the HANA instance **bound to the CF app**
  as an HDI-container / schema service (preferred — credentials arrive via `VCAP_SERVICES`, no secret
  in env)
- [ ] Any data-residency / retention policy for stored decisions confirmed

---

## Summary checklist by phase

```
Phase A — Infra ready
  [ ] P0.1  BTP subaccount + CF space
  [ ] P0.2  AI Core credentials shared
  [ ] P0.3  Accelerator Hub API key shared

Phase B — Joule integration
  [ ] P1.1  IAS admin access (15 min for our environment to configure IAS apps)
  [ ] P1.2  BTP↔IAS trust configured

Phase C — S/4 on-prem connectivity
  [ ] P2.1  SCC installed + connected to BTP
  [ ] P2.2  S/4 resources exposed in SCC
  [ ] P2.3  Principal propagation configured (Basis)
  [ ] P2.4  OData services activated
  [ ] P3.1  Demo users created
  [ ] P3.2  Sample data confirmed

Phase D — Decision persistence
  [ ] P4.1  HANA Cloud instance + schema
  [ ] P4.2  ZAGENT_DECISION_LOG (+ vector table) + INSERT/SELECT-only role
  [ ] P4.3  HANA service key shared or bound to CF app
```

---

## Who does what

| Action | Done by |
|---|---|
| BTP subaccount setup | Adarsh IT / SAP BTP admin |
| AI Core + API key | Adarsh IT or SAP account team |
| SCC install + S/4 exposure | Adarsh Basis team |
| Principal propagation (STRUST/SNC) | Adarsh Basis team |
| IAS app configuration (B2/B3) | Adarsh IAS admin (or delivery team with admin access) |
| HANA Cloud instance + schema + INSERT/SELECT role | Adarsh DBA / BTP admin |
| CF agent deployment, Joule YAML deploy | our team |
| Demo user creation | Adarsh Basis / security team |

---

*Document version: 2026-10-21. Owner: delivery team. Share with Adarsh IT and Basis teams.*
