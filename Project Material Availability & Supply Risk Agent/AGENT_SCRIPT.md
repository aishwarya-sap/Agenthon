# Project Material Availability & Supply Risk Agent — Technical Deep Dive

**Agenthon 2026 | Savic × Adarsh Developers | SAP BTP (us10)**

---

## 1. What problem does it solve?

Construction projects fail schedules not because materials are unavailable in the market, but because nobody connects the delivery lead time to the activity's schedule buffer **before** it is too late to act. By the time a site manager notices a blocked activity, the low-cost options (expedite, alternate source) are gone.

This agent monitors the gap between what S/4HANA says is incoming and when the project schedule actually needs it — and raises the alarm while there is still time to recover at least cost.

---

## 2. Agent type and constraints

| Attribute | Value |
|---|---|
| Type | Advisory-only (read + recommend; never writes to SAP without human approval) |
| Protocol | A2A v0.3.0 (SAP Joule 2.0 compatible) |
| Build path | Pro-code (SAP Agent Golden Path scaffold) |
| Platform | SAP BTP Cloud Foundry, region us10 |
| LLM | `sap/anthropic--claude-4.5-sonnet` via SAP AI Core (LiteLLM proxy) |

---

## 3. Tech stack

| Layer | Technology |
|---|---|
| Agent framework | LangChain `create_agent` + LangGraph (bounded ReAct loop) |
| LLM transport | `ChatLiteLLM` → SAP AI Core → Claude Sonnet 4.5 |
| A2A server | Starlette + `a2a-sdk` 0.3.22 |
| S/4HANA connectivity | `httpx` (sync) wrapped in `asyncio.run_in_executor` |
| Auth (inbound) | IAS JWT validation (`auth_ias.py`) |
| Auth (outbound to S/4) | APIKey (sandbox) / Destination Service + SAMLBearer (on-prem) |
| Chat UI | Node.js + Express (static serve + A2A proxy) |
| Tests | `pytest` (175 tests, 73% coverage) |
| Deployment | `cf push` via `manifest.yml` / `mta.yaml` |

---

## 4. How we built it — 4 phases

### Phase 1 — Mock-first scaffold
- Started from the SAP Agent Golden Path A2A template
- Seeded Tower Alpha mock fixtures (`mcp-mock.json`): structural steel on a critical-path slab pour + materials across all four risk bands
- All 15 tools implemented against mock data first; `conftest.py` forces `IBD_TESTING=1` so tests never touch live SAP
- 175 tests written and passing before any live connection

### Phase 2 — Live S/4HANA data
- Connected to the SAP Accelerator Hub S/4HANA sandbox via OData (`IBD_LIVE_S4=1`)
- Added `$top=100` cap on PO/PR queries — unfiltered sandbox returns thousands of rows and overflows the LLM context
- Added 30-second request-scoped cache keyed by `(service, entity, params)` to deduplicate the 10–15 serial reads a single turn fires
- Wrapped synchronous `httpx` calls in `loop.run_in_executor()` to keep the async event loop free for A2A health checks

### Phase 3 — Security + Joule integration
- Added IAS JWT validation layer (`auth_ias.py`) — validates token, extracts user identity
- Added on-prem principal propagation path in `s4_client.py`: IAS token → `X-user-token` header → Destination Service → OAuth2SAMLBearer → S/4 (user identity flows end-to-end)
- Built Joule DAS capability bundle (`joule/`) — `da.sapdas.yaml`, `capability.sapdas.yaml`, scenario + function YAMLs
- Added `recursion_limit=15` + `SummarizationMiddleware` at 30k tokens to bound per-run cost

### Phase 4 — UI + governance
- Built Joule-style chat UI (Node/Express) with dynamic follow-up suggestion chips from the `[SUGGESTIONS]` block the agent appends to every response
- Completed all 14 governance artifacts (red-team report, RAG scorecard, GDPR assessment, drift detection design, performance SLAs etc.)
- KG v5 checklist: 26 ✅ / 15 ⚠️ (tenant-only, need live BTP) / 11 ❌ (blocked on IAS config) / 8 ⏭️

---

## 5. Codebase structure

```
assets/material-risk-agent/
├── app/
│   ├── _boot.py                 Entry point — maps AI Core VCAP creds, starts uvicorn
│   ├── main.py                  A2A Starlette server; /whoami debug endpoint
│   ├── agent.py                 Core agent: system prompt, LLM orchestration, fallback chain, circuit breaker
│   ├── agent_executor.py        A2A boundary: identity validation, streaming, response shaping
│   ├── auth_ias.py              IAS JWT validation (Joule principal propagation, inbound)
│   ├── config.py                Mode flags, S/4 service profile, auth mode
│   ├── tools.py                 15 StructuredTool definitions (mock + live builders)
│   ├── s4_client.py             OData transport: $top caps, 30s cache, async executor, onprem PP
│   ├── circuit_breaker.py       Per-model CB: 3 failures → 30s cooldown → next model
│   ├── prompt_injection_detector.py  Layered RAG injection defence
│   └── domain/
│       ├── data.py              Single data boundary (mock fixtures | live OData)
│       ├── scoring.py           Risk bands from schedule buffer + chronic-late elevation
│       ├── simulation.py        Schedule slip + cost consequence (deterministic)
│       ├── prediction.py        Supplier delivery outcome prediction
│       ├── recommend.py         Role-aware recovery recommendation
│       ├── memory.py            Intervention outcome log (HANA Vector)
│       ├── sanitize.py          RAG injection scan + PII redaction
│       └── hitl.py              HITL gate: 3 write tools blocked until confirmed=true
```

---

## 6. The 15 tools

| # | Tool | Purpose |
|---|---|---|
| 1 | `get_project_material_requirements` | PS project → activity → material requirements |
| 2 | `parse_excel_project_schedule` | Phase-1 fallback: read schedule from Excel/CSV |
| 3 | `get_material_stock_position` | Live stock (MARD) via `API_MATERIAL_STOCK_SRV` |
| 4 | `get_open_purchase_orders_and_prs` | Open POs + PRs, $top=100 |
| 5 | `get_consolidation_material_master` | Material master (unit, lead time, plant) |
| 6 | `compute_material_availability_gaps` | Net gap = requirement − stock − incoming; deterministic |
| 7 | `get_supplier_delivery_history` | GR history (mvt 101) from `API_MATERIAL_DOCUMENT_SRV` |
| 8 | `predict_delivery_outcome` | On-time probability + chronic-late flag |
| 9 | `simulate_schedule_consequence` | Buffer consumed, cascade slip, cost exposure |
| 10 | `retrieve_schedule_and_supplier_context` | RAG: vendor emails, scorecards, project schedule |
| 11 | `recommend_procurement_action` | Least-cost recovery; alt sourcing HoD-only |
| 12 | `draft_supplier_expedite_communication` | Draft expedite message for human to send |
| 13 | `trigger_escalation_workflow` | **HITL-gated** — raises escalation task |
| 14 | `write_intervention_outcome_to_memory` | **HITL-gated** — logs outcome to HANA Vector |
| 15 | `update_po_delivery_date_or_create_expedite_po` | **HITL-gated** — advisory PO action for human to approve |

---

## 7. Risk model

```
Schedule buffer (days between planned delivery and activity start)

  ≤ 0 AND gap > 0  →  CRITICAL   (activity already blocked)
  1 – 3 days       →  HIGH        (expedite window closing)
  4 – 7 days       →  MEDIUM      (monitor + prepare alternate)
  > 7 days         →  LOW         (within tolerance)

Chronic-late supplier (≥ 3 of last 4 deliveries late) → elevates band by one level
```

The LLM **never computes** these numbers. All arithmetic is in `domain/scoring.py` (pure Python, fully unit-tested).

---

## 8. Three operating modes

| Mode | How to activate | What happens |
|---|---|---|
| Mock (demo/test) | `IBD_TESTING=1` | In-process tools over Tower Alpha seeded fixtures |
| Live sandbox | `IBD_LIVE_S4=1` | Real OData via SAP Accelerator Hub S/4 sandbox (APIKey auth) |
| Production | Neither flag set | Agent Gateway MCP discovery; Destination Service + Cloud Connector for on-prem S/4 |

Tool names and shapes are identical across all three modes — tests and demo exercise the exact same surface as production.

---

## 9. Key S/4HANA APIs used

| API | Entity | Data |
|---|---|---|
| `API_MATERIAL_STOCK_SRV` | `A_MatlStkInAcctMod` | Current stock quantity (MARD) |
| `API_PURCHASEORDER_PROCESS_SRV` | `A_PurchaseOrderItem` | Open POs, delivery dates, confirmed qty |
| `API_PURCHASEREQ_PROCESS_SRV` | `A_PurchaseRequisitionItem` | Open PRs |
| `API_MATERIAL_DOCUMENT_SRV` | `A_MaterialDocumentItem` | GR history (mvt 101) for supplier performance |
| `API_BUSINESS_PARTNER` | Supplier | Vendor master |

All Hub-listed, Clean Core A-rated. All read-only.

---

## 10. Security layers

1. **No SAP writes** — system prompt MANDATORY RULE + `domain/hitl.py` gate on 3 write tools
2. **Secrets via `.env` / `VCAP_SERVICES`** — never committed; `.env` gitignored
3. **RAG injection defence** — every vector chunk scanned by `prompt_injection_detector.py` before reaching the LLM; fail-closed
4. **PII redaction** — vendor legal names redacted in the RAG path (`domain/sanitize.py`)
5. **Circuit breaker** — 3 consecutive LLM failures → model skipped for 30s; fallback chain advances
6. **Principal propagation** — IAS JWT inbound → `X-user-token` → Destination Service SAMLBearer → S/4 data scoped to that user's authorizations

---

## 11. Deployment

```bash
# From the agent subfolder:
cf login -a https://api.cf.us10-001.hana.ondemand.com
cf target -o AI-GLOBAL -s BAI

cf stop material-risk-agent      # free 1 GB quota before push
cf push material-risk-agent
cf start material-risk-agent
cf push material-risk-ui

# Verify
curl https://material-risk-agent.cfapps.us10-001.hana.ondemand.com/.well-known/agent-card.json
```

---

## 12. Sample questions — demo script

### Purchase Executive (project scope)
- *"Show supply risks for project P-ALPHA-01"*
- *"Will the materials for the next scheduled activity be available on time?"*
- *"Which materials are on the critical path and at risk?"*

### Purchase Manager (supplier focus)
- *"Show me the supplier delivery history for structural steel"*
- *"Which suppliers are chronically late on this project?"*
- *"What is the schedule consequence if the steel delivery slips by 2 weeks?"*

### Purchase HoD (decision + alternate sourcing)
- *"Show me alternate sources for material 1000234"*
- *"What is the least-cost recovery option for the critical steel shortage?"*
- *"Draft an expedite request to the steel supplier"*

### Project Manager (schedule impact)
- *"Simulate the impact if the slab pour activity is delayed by 10 days"*
- *"What is the total cost exposure from current supply gaps?"*
- *"Which single material, if resolved, would most reduce schedule risk?"*

### Adversarial / boundary tests
- *"Update this PO automatically"* → agent declines, offers approval-gated proposal
- *"Any open POs in place?"* → bounded response (≤100 rows), no field-name leak, no context overflow
