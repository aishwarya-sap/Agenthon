# ADR-0003: Advisory-only with a HITL gate on all side effects

**Status:** Accepted · **Date:** 2026-10-27

## Context

The agent operates against SAP procurement data. The engagement constraint is that it must not autonomously change SAP business objects; any side effect must be explicitly approved by a human.

## Decision

The agent is **advisory-only**: no POST/PATCH/DELETE to SAP business objects anywhere. The three write tools — `trigger_escalation_workflow`, `write_intervention_outcome_to_memory`, `update_po_delivery_date_or_create_expedite_po` — are **HITL-gated** in `app/domain/hitl.py`: they return `confirmation_required` and only execute once a human approval keyword sets `confirmed=true`. Alternate sourcing is additionally restricted to the Purchase HoD role.

## Alternatives

- **Full write automation** — rejected by engagement policy; irreversible mutations without human sign-off are unacceptable here.
- **No writes at all** — too limited; the agent still needs to log outcomes and raise escalations, which the HITL gate allows safely.

## Consequences

- Safe-by-construction: three enforcement layers (system-prompt mandatory rule, `hitl.py` gate, no SAP write path in any tool).
- Maps to SEC-381.4 (human oversight). Side effects are limited to the agent's own memory + notifications.
- Emergency-stop (SEC-381.7) and hash-chained audit (SEC-381.5) remain pending hardening items.
