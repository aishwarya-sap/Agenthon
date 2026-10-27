# ADR-0001: Advisory, read-only agent (no SAP writes)

- **Status:** Accepted
- **Date:** 2026-10-17

## Context
The agent operates on live procurement data (POs, contracts, suppliers). The client needs
decision-support, not automation, and must not risk an agent mutating business objects.

## Decision
The agent is strictly **advisory and read-only**. It issues only OData GET requests. It performs no
POST/PATCH/DELETE and no BAPI writes against any SAP business object. The two "action" tools
(`write_decision_record`, `trigger_escalation_notification`) write only to the agent's own
institutional-memory log and raise mocked notifications — never to SAP.

## Consequences
- Source-switch / escalation are produced as HITL-approved *recommendations*, not executed.
- The system prompt explicitly forbids writes; the A2A boundary never exposes a mutation path.
- Lower integration risk and simpler authorization (read scopes only).
