# Agent Outcome Report — [ClientName] [Use Case]

> The formal governance evidence file. Every L0–L10 control marked; every gap documented.
> **Never delivered blank.** (SAP Agent solution-doc standard)
>
> Flag key: ✅ Satisfied · ⚠️ Partial · ❌ Not satisfied · ⏭️ Skipped — N/A (scope)
> Rule: every ⚠️ / ❌ MUST carry a **To resolve:** note.

## 1. Summary
- **Agent:** [TODO]
- **Build path:** [CoE / KG / AI Factory]
- **Overall verdict:** [GO / CONDITIONAL-GO / NO-GO] — see §7

## 2. L0–L10 control status
| Pillar | Control | Status | Evidence / To resolve |
|---|---|---|---|
| L0-1 | AI feature & agent onboarding | ⬜ | |
| L0-2 | LLM selection & benchmarking | ⬜ | |
| L0-3 | Document grounding & RAG quality | ⬜ | |
| L0-4 | Commercialization & metering | ⬜ | |
| L0-5 | Responsible AI & safety | ⬜ | |
| L0-6 | Agent dev & deployment | ⬜ | |
| L0-7 | Release validation & go-live | ⬜ | |
| L0-8 | Design classification & performance | ⬜ | |
| L0-9 | Knowledge & data grounding | ⬜ | |
| L0-10 | Dependency & change resilience | ⬜ | |

> Fill each row ✅/⚠️/❌/⏭️. Expand to the 70-control detail from `AGENT_CHECKLIST.md`
> where the engagement needs line-item evidence.

## 3. What works (verified)
- [INFER from the build + passing tests]

## 4. Flagged items (must resolve before production)
| Item | Pillar | Severity | To resolve |
|---|---|---|---|
| [INFER] | | | |

## 5. Scope exclusions (⏭️ with justification)
- [CLIENT INPUT / INFER]

## 6. Cost & metering
- Token budget per run: [from config.py `TOKEN_BUDGET_PER_RUN`]
- Measured actual vs estimate: [VERIFY — Phase 5]

## 7. Summary scorecard
| Dimension | Verdict |
|---|---|
| Functional | [ ] |
| Security (auth, no writes, no secrets) | [ ] |
| Governance (L0–L10) | [ ] |
| Deployment readiness | [ ] |
| **Overall** | **[GO / CONDITIONAL-GO / NO-GO]** |
