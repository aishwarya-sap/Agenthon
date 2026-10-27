## Design Brief: procurement-bottleneck-decision-agent

**Client:** Adarsh Developers (real-estate / construction).
**Primary user:** Purchasing Head of Department (HoD) and procurement officers.
**Agent type:** Advisory, read-only decision-support agent embedded via SAP Joule (A2A).

### Problem

Adarsh's procurement teams discover supplier silence on critical-path purchase orders only *after*
it has already slipped the project schedule. Material delays (e.g. structural steel for a slab pour)
cascade into idle crews, milestone penalties, and emergency-sourcing premiums. The signals needed to
catch this early — PO confirmation gaps, goods-receipt history, project float, vendor track record —
are spread across S/4 and nobody watches them continuously.

### What the agent does

Gives the Purchasing HoD a real-time, consequence-aware view across active purchase orders:

1. Traces the PR → PO → confirmation chain and detects supplier silence (days since PO issue / last GRN).
2. Links the PO to its project activity and critical-path float.
3. Quantifies the downstream consequence (schedule slip, idle-resource cost, milestone-penalty exposure).
4. Recalls how similar past situations were resolved (institutional memory).
5. Presents a ranked recommendation (contact supplier / line up a backup source / hold and monitor)
   and routes it through a Human-in-the-Loop approval gate.

### Scope boundaries

- **Advisory / read-only (C-01):** the agent performs **no** POST/PATCH/DELETE against SAP business
  objects. "Write" tools only append to the agent's own decision log and raise mocked notifications.
- Project-schedule data comes from SAP Project System (Phase 2) or a PMO Excel/CSV adapter (Phase 1).
- Penalty clauses and vendor on-time metrics are not in standard OData and are labelled "simulated"
  until a KPI source is connected.

### Success criteria

Correct, business-readable, question-specific answers grounded only in verified SAP data (never
fabricated), with every quantitative output disclaimed and every recommended action gated on HoD
approval.
