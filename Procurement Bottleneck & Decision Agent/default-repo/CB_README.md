# [ClientName] — [Use Case Name] Agent

**Engagement date:** [CLIENT INPUT]
**Prepared by:** [CLIENT INPUT]
**Status:** [Draft / Review / Final]

> Client-facing executive summary. Written for the client sponsor and dev-team leads.
> Template fields: [CLIENT INPUT] = from the client, never fabricate · [INFER] = derived ·
> [VERIFY] = needs confirmation from client or SAP. (SAP Agent solution-doc standard)

## What was built
[2–3 sentences: the agent, what SAP systems it touches, what it answers/does]

## Architecture
- **Agent type:** [ReAct / Plan-Act / RAG / Skill-only]
- **Build path:** [CoE / KG / AI Factory]
- **Runtime:** [AI Core + Cloud Foundry — [VERIFY region: us10 / eu10 / ap20]]
- **SAP connectivity:** [Mock / Agent Gateway / Direct Destination]
- **Joule integration:** [Capability bundle published / Joule skill / not applicable]

## APIs consumed
| API / Service | SAP Accelerator Hub listing | Clean Core Level | Status |
|---|---|---|---|
| [CLIENT INPUT] | [VERIFY URL] | [A/B/C] | [Live / Mock / [VERIFY]] |

## Governance verdict
| Pillar | Status | Notes |
|---|---|---|
| API Policy (current) | ✅ / ⚠️ / ❌ | ATQ sign-off: [VERIFY] |
| Clean Core | ✅ / ⚠️ / ❌ | [Level A target / exceptions noted] |
| Safety Dashboard | ✅ / ⚠️ / ⏭️ | [Run / Deferred — sandbox only] |
| Cross-functional sign-off | ✅ / ⏭️ | [Recorded / Demo only] |

## Go / No-Go
**Verdict:** ✅ Go for [demo / UAT / production] · ❌ Not for production until: [list blockers]

## Handover checklist
- [ ] Repo shared with dev team via Git
- [ ] Work tracker / epic created with all tickets
- [ ] `.env.example` filled and reviewed
- [ ] Mock mode verified offline (IBD_TESTING=1)
- [ ] Cost estimate reviewed and ceiling set
