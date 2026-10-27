# Requirements Traceability Matrix

Maps functional requirements (FS) to their technical implementation (TS: `app/` modules) and tests.

## Coverage Summary

### Coverage by Type
All 9 functional requirements implemented and test-covered. 134 tests, coverage ≥ 70%.

## Forward Traceability (FS → TS → Test)

| FR | Requirement | Implementation (`app/`) | Test |
|---|---|---|---|
| FR-1 | Daily Blockers dashboard | `demo/index.html` (renderDashboard), `agent._quick_list` | `tests/test_server.py` |
| FR-2 | Supplier-silence detection | `s4_client.detect_supplier_silence`, `config` thresholds | `tests/test_s4_client.py` |
| FR-3 | Consequence simulation | `simulation.py`, `skills.run_consequence_simulation` | `tests/test_simulation.py`, `test_skills.py` |
| FR-4 | Ranked recommendation | `skills.recommend_next_action`, `agent._STEP_LABELS` | `tests/test_skills.py` |
| FR-5 | Alternate-supplier lookup | `agent._alternate_suppliers_report`, `s4_client.get_source_and_contract_dependencies` | `tests/test_agent.py` |
| FR-6 | Delivery-performance history | `agent._business_answer` (perf branch), `s4_client.get_vendor_delivery_performance` | `tests/test_agent.py::test_delivery_performance_question_not_open_po_list` |
| FR-7 | Free-form Q&A | `agent._llm_contextual_answer`, `_business_answer` | `tests/test_agent.py` |
| FR-8 | HITL approval gate | `hitl.py`, `agent._resolve_approval` | `tests/test_hitl.py` |
| FR-9 | Honest failure (no fabrication) | `agent._backend_error_report`, `resilience.QuotaExceeded` | `tests/test_agent.py::test_backend_failure_is_honest_not_hallucinated` |

## Backward Traceability (TS → FS)

| Module | Serves |
|---|---|
| `agent.py` | FR-1,4,5,6,7,8,9 (orchestration + routing) |
| `s4_client.py` | FR-2,5,6 (live OData) |
| `simulation.py` / `skills.py` | FR-3,4 |
| `hitl.py` | FR-8 |
| `resilience.py` | FR-9 (terminal quota handling) |
| `sanitize.py` / `auth_ias.py` / `observability.py` | cross-cutting security + guardrails (FS §2.3) |

Non-functional + security requirements (FS §2.3, §5) are evaluated in `docs/quality-gate-report.md`
and `docs/code-review-report.md` against the QG/CR checklists.
