# Material Risk Agent — Flow Diagrams (Sprint 2)

## End-to-End Agent Flow

```
User (Joule / Chat UI)
        │
        │  A2A message/send (JSON-RPC, A2A 0.3.0)
        ▼
  material-risk-ui
  (Node.js Express)
        │
        │  POST /agent/  (reverse proxy)
        ▼
  material-risk-agent
  (Python, CF)
        │
        ├─ JWTContextMiddleware
        │   ├─ Mock mode (IBD_TESTING=1): skip validation
        │   └─ IAS mode (Sprint 3): validate Joule IAS token
        │
        ├─ AgentExecutor.execute()
        │   ├─ get_mcp_tools() → 15 tools (mock | direct-S4 | agent-gateway)
        │   └─ SampleAgent.stream()
        │       ├─ LangGraph (LangChain create_agent)
        │       ├─ ChatLiteLLM → SAP GenAI Hub → Claude claude-4.5-sonnet
        │       ├─ Tool calls → domain/ logic
        │       └─ SummarizationMiddleware (30k token trigger)
        │
        └─ A2A response → artifacts[].parts[].text
                │
                ▼
        User sees report
```

---

## Sprint 2: S/4HANA Connectivity Flow

```
material-risk-agent
        │
        ├─ s4_client._odata_get()
        │   ├─ cloud profile (IBD_LIVE_S4=1):
        │   │   Headers: { APIKey: <BAH key> }
        │   │   URL:     https://sandbox.api.sap.com/s4hanacloud/...
        │   │
        │   └─ onprem profile (S4_SERVICE_PROFILE=onprem, Sprint 2):
        │       Headers: { X-user-token: <user JWT> }
        │       URL:     BTP Destination → Cloud Connector → S/4HANA on-prem
        │
        ├─ 7 OData services (verified entity names):
        │   ├─ API_MATERIAL_STOCK_SRV       → A_MatlStkInAcctMod
        │   ├─ API_PURCHASEORDER_PROCESS_SRV → A_PurchaseOrder (3-entity join)
        │   ├─ API_PURCHASEREQ_PROCESS_SRV  → A_PurchaseRequisitionItem
        │   ├─ API_BUSINESS_PARTNER         → A_Supplier
        │   ├─ API_INFORECORD_PROCESS_SRV   → A_PurgInfoRecdOrgPlantData
        │   ├─ API_PURCHASECONTRACT_PROCESS_SRV → A_PurchaseContractItem
        │   └─ API_MATERIAL_DOCUMENT_SRV    → A_MaterialDocumentHeader
        │
        └─ _parse_odata_date() → handles /Date(epochMillis)/ V2 dates
```

---

## Sprint 3: Principal Propagation Flow (IAS)

```
User
  │  (authenticates with IAS)
  ▼
Joule (SAP BTP)
  │  Issues IAS user token (JWT RS256)
  │  Adds app2app dependency: A2A Proxy IAS app → Custom-Agent IAS app
  ▼
A2A Proxy (SAP managed)
  │  JWT-Bearer exchange: forwards user token to agent
  ▼
material-risk-agent
  │  JWTContextMiddleware (AGENT_AUTH_MODE=ias)
  │  Calls validate_ias_token():
  │    - Fetches JWKS from IAS_JWKS_URI
  │    - Verifies RS256 signature + issuer + expiry
  │    - Checks ias_apis claim OR aud
  ├─ /whoami endpoint: shows identity chain (debug only)
  └─ Forwards user JWT as X-user-token → BTP Destination → S/4 (on-prem only)
```

---

## Adarsh Client Landscape (Sprint 2/3)

```
Adarsh BTP (Tokyo → SEA migration)
  ├─ CF Space: AI-DEV
  ├─ AI Core Extended (resource group: grounding)
  ├─ Destination: MATERIAL_RISK_AGENT → CF agent route
  ├─ IAS Tenant (to be configured Sprint 3)
  └─ Cloud Connector
       └─ S/4HANA on-prem: SID=ADV, client=100, vhost=vhdvladvci:44300
            ├─ OData services activated (OP_* prefix)
            ├─ STRUST: BTP certificate trusted
            └─ CERTRULE: user mapping rule active
```
