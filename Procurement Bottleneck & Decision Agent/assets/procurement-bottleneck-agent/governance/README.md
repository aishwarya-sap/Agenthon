# Governance Artifacts — Index

Deliverables produced to close the offline-completable portion of the SAP BTP AI
Agent Checklist (v5) for `procurement-bottleneck-agent`. Each maps to a checklist
item. Items requiring the live BTP tenant or a human governance sign-off are marked
accordingly — they are **not** code defects.

| Item | Artifact | Status |
|---|---|---|
| 2.1 | `../eval/eval_dataset.jsonl` + `../tests/test_eval.py` | ✅ dataset built + executed |
| 2.6 | `2.6-frontier-model-justification.md` | ⏳ artifact done, dual sign-off pending |
| 2.7 | `2.7-model-update-retraining-governance.md` | ✅ policy defined |
| 3.3 | `3.3-rag-evaluation-scorecard.md` + `../eval/rag_eval.py` | ✅ offline scorecard 8/8; RagEval on live pending |
| 4.5 | `4.5-customer-token-consumption-forecast.md` | ⏳ token envelope done, cost needs LLM Calculator |
| 4.6 | `4.6-cost-per-transaction-baseline.md` | ✅ baseline + instrumentation wired |
| 5.2 | `5.2-bias-fairness-assessment.md` | ✅ assessment done; RAI cadence at go-live |
| 5.3 | `5.3-redteam-report.md` + `../tests/test_redteam.py` | ✅ battery passing; human red team pending |
| 5.5 | `5.5-gdpr-euaiact-compliance.md` | ⏳ record done, Legal classification pending |
| 5.6 | `app/sanitize.py` + `../tests/test_sanitize.py` | ✅ injection gate live + tested |
| 5.7 | `5.7-ip-data-ownership-governance.md` | ⏳ artefact done, confirm SAP terms |
| 6.1/6.2 | `6.1-6.2-agent-builder-exception.md` | ⏳ exception filed; security review + re-register pending |
| 8.4 | `8.4-performance-slas.md` | ⏳ targets set, live p50/p95/p99 pending |
| 10.2 | `10.2-dependency-map.md` | ✅ complete |
| 10.3/10.4/10.5 | `10.3-10.4-10.5-drift-detection-design.md` | ⏳ design done, monitors stand up post-go-live |

**Legend:** ✅ complete (offline) · ⏳ artifact complete, needs tenant/human sign-off to fully close.

See `../agent-outcome-report.md` for the full L0-1→L0-10 status against the v5 checklist.
