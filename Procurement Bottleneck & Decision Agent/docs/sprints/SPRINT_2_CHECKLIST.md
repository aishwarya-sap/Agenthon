# Sprint 2 Checklist — Live SAP Data

**Goal:** Agent reads from live S/4HANA (via SAP Accelerator Hub sandbox or direct OData).  
**Gate:** End-to-end report with real data, functional sign-off.

---

## Pre-sprint
- [ ] SAP Accelerator Hub API key received from client (via secure channel)
- [ ] API key verified working against sandbox (`/sap/opu/odata/...`)
- [ ] Live entity set names verified in `/IWFND/MAINT_SERVICE` (not assumed)
- [ ] IBD_TESTING=0 environment confirmed in CF

## Development
- [ ] MCP provider updated to call live OData endpoints
- [ ] All API calls include `$top=100` guard
- [ ] Error handling: 404, empty result, API unavailable — all return clean messages
- [ ] Advisory boundary enforced: no POST/PATCH/DELETE calls
- [ ] Token budget measured on a real turn (update TOKEN_BUDGET_PER_RUN if needed)
- [ ] RAG similarity gate tested with real contract data

## Testing
- [ ] Golden Q&A test set (minimum 12 Q&A pairs) passes
- [ ] Empty result case: query with no matching data → "No data found for X"
- [ ] 404 case: invalid record ID → "Record not found in SAP"
- [ ] Advisory boundary: "Please update PO" → refused
- [ ] Disclaimer: financial query → ends with standard disclaimer
- [ ] Test coverage ≥ 80%

## Deployment
- [ ] IBD_TESTING=0 in manifest.yml (or CF env)
- [ ] Live turn produces valid response
- [ ] No credentials in code (all via env vars or service binding)

## Sign-off
- [ ] Functional SPOC tested live data query and confirmed accuracy
- [ ] At least one real project/PO scenario demonstrated

---
**Sprint 2 complete date:** ___________  
**Signed off by:** ___________
