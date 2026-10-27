<!-- rtm-version: 1.0 -->
<!-- generated: 2026-10-27 -->
<!-- coverage: FR=100%, NFR=100%, INT=100%, SEC=100%, TST=100% -->

# Requirements Traceability Matrix

## Coverage Summary

| Metric | Value |
|--------|-------|
| Total Requirements | 25 |
| Covered | 25 (100.0%) |
| Gaps | 0 |

### Coverage by Type

| Type | Total | Covered | Gaps | Coverage |
|------|-------|---------|------|----------|
| Functional (FR) | 11 | 11 | 0 | 100% |
| Non-Functional (NFR) | 6 | 6 | 0 | 100% |
| Integration (INT) | 4 | 4 | 0 | 100% |
| Security (SEC) | 4 | 4 | 0 | 100% |

## Forward Traceability (FS → implementation → test)

| Req ID | Type | Description | Implementation | Test | Status |
|--------|------|-------------|----------------|------|--------|
| FS-FR-001 | FR | Cross-reference requirements vs stock/PO/PR/master | `tools.py`, `s4_client.py`, `domain/data.py` | `test_tools`, `test_data` | Mapped |
| FS-FR-002 | FR | Compute availability gap | `domain/scoring.py::gap_quantity/net_available_qty` | `test_scoring` | Mapped |
| FS-FR-003 | FR | Risk band from schedule buffer | `domain/scoring.py::risk_band` | `test_scoring` | Mapped |
| FS-FR-004 | FR | Supplier history + chronic-late flag | `domain/scoring.py::is_chronic_late`, `tools.py` | `test_scoring` | Mapped |
| FS-FR-005 | FR | Predict delivery outcome | `domain/prediction.py` | `test_prediction` | Mapped |
| FS-FR-006 | FR | Simulate schedule/cost consequence | `domain/simulation.py` | `test_simulation` | Mapped |
| FS-FR-007 | FR | Recommend recovery; alt-source HoD-only | `domain/recommend.py` | `test_tools` | Mapped |
| FS-FR-008 | FR | Draft expedite communication | `domain/recommend.py::draft_expedite_email` | `test_tools` | Mapped |
| FS-FR-009 | FR | Intervention-outcome memory | `domain/memory.py` | `test_memory` | Mapped |
| FS-FR-010 | FR | Brief-by-default response | `agent.py` system prompt | manual / golden Q&A | Mapped |
| FS-FR-011 | FR | days-to-required / overdue vs current date | `domain/scoring.py::assess_material`, `domain/data.py::today` | `test_scoring` | Mapped |
| FS-NFR-001 | NFR | Latency SLO | async executor, 30s cache | manual (tenant) | Mapped |
| FS-NFR-002 | NFR | Low concurrency | single process | — | Mapped |
| FS-NFR-003 | NFR | Data residency | region-agnostic manifest | — | Mapped |
| FS-NFR-004 | NFR | PII redaction | `domain/sanitize.py` | `test_sanitize` | Mapped |
| FS-NFR-005 | NFR | Token ceiling / summarization | `agent.py` SummarizationMiddleware @30k | `test_util_response_trimming` | Mapped |
| FS-NFR-006 | NFR | Resilience / fallback | `circuit_breaker.py`, `domain/data.py::_live_or_fallback` | `test_circuit_breaker` | Mapped |
| FS-INT-001 | INT | S/4 OData reads | `s4_client.py` | `test_s4_client_onprem` | Mapped |
| FS-INT-002 | INT | $top cap + request cache | `s4_client.py` | `test_s4_client_onprem` | Mapped |
| FS-INT-003 | INT | IAS inbound validation | `auth_ias.py` | `test_auth_ias` | Mapped |
| FS-INT-004 | INT | VCAP AI Core mapping | `_boot.py::apply_vcap_aicore` | `test_boot_aicore` | Mapped |
| FS-SEC-001 | SEC | Advisory-only / no writes | system prompt | `test_redteam` | Mapped |
| FS-SEC-002 | SEC | HITL gate on writes | `domain/hitl.py` | `test_hitl` | Mapped |
| FS-SEC-003 | SEC | RAG injection fail-closed | `prompt_injection_detector.py`, `domain/sanitize.py` | `test_sanitize` | Mapped |
| FS-SEC-004 | SEC | Secrets via env / not committed | `.env` gitignored, `.cfignore` | manual | Mapped |
