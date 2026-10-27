# Requirements — [ClientName] [Use Case]

> The contract between architect and dev team: scope, APIs, acceptance criteria, exclusions.
> [CLIENT INPUT] = from the client, never fabricate · [INFER] = derived · [VERIFY] = confirm.
> (SAP Agent solution-doc standard)

## 1. Problem statement
[CLIENT INPUT — from use case brief / meeting notes]

## 2. Intended users
[CLIENT INPUT — role, geography, volume estimate]

## 3. Agent scope
### In scope
- [CLIENT INPUT]
### Explicitly out of scope
- [CLIENT INPUT]
### Write access (if any)
- [CLIENT INPUT — default: advisory-only, no POST/PATCH/DELETE]

## 4. SAP systems & APIs
| System | Version | API / Entity Set | Hub listing | Clean Core Level |
|---|---|---|---|---|
| [CLIENT INPUT] | [VERIFY] | [CLIENT INPUT] | [VERIFY] | [VERIFY] |

## 5. Grounding strategy
- [ ] OData live reads (Agent Gateway)
- [ ] Document Grounding Service
- [ ] Custom RAG / KG — justification: [CLIENT INPUT if chosen]
- [ ] Mock only (sandbox / demo)

## 6. Non-functional requirements
- Latency SLO: [CLIENT INPUT / default: < 5s P95]
- Concurrency: [CLIENT INPUT]
- Data residency: [CLIENT INPUT — region, sovereign cloud flag]
- PII handling: [CLIENT INPUT]

## 7. Acceptance criteria
| Scenario | Expected behaviour | Test method |
|---|---|---|
| [CLIENT INPUT] | [CLIENT INPUT] | Golden Q&A / automated |

## 8. Assumptions & dependencies
[CLIENT INPUT]

## 9. Open items / risks
[INFER from input + governance gap flags]
