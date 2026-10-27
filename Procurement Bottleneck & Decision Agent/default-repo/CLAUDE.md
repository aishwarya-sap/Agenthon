# CLAUDE.md — Project Standards (this agent)

> **This file is self-contained and authoritative for this repo.** It encodes the SAP
> engineering standards and governance controls every agent built from this starter kit
> must follow. You do not need any other repository to use it. The standards below
> operationalize two public authorities:
>
> - **SAP Agent Golden Path** — SAP's published blueprint for building A2A agents on BTP
>   (Agent Gateway, AI Core / GenAI Hub, Joule, Cloud Foundry).
> - **Quality Gate + Code Review checklists** — the authoritative GDH AI Factory go-live gates
>   (Quality Gate: `QG-SA/TE/DA/AC/LQ`; Code Review: `CR-AR/SR/A2/PR`), shipped in this repo as a
>   condensed [`AGENT_CHECKLIST.md`](AGENT_CHECKLIST.md) and in full under `docs/checklists/`; results
>   recorded in `docs/quality-gate-report.md` + `docs/code-review-report.md`.
>
> **This repo's design rationale:** see [`DESIGN_RATIONALE.md`](DESIGN_RATIONALE.md) — why
> every file and convention exists, traced to its authority.

---

## Standards this repo follows (SAP Agent Golden Path §2 principles)

### Architecture
- **Clean Core first.** Target Level A (Released) APIs from SAP Business Accelerator Hub.
  Never Level D. Document a justification + migration plan for any Level C dependency.
- **Endorsed architectures only.** A2A via SAP Agent Gateway; MCP via Integration Suite;
  LLMs via SAP AI Core / GenAI Hub. No community MCP wrappers, no ungoverned direct OData.
- **Advisory-only default.** Every agent starts read-only. Any write action (POST/PATCH/
  DELETE) requires a separately reviewed, approved use case recorded in `REQUIREMENTS.md`.
- **Switchable-code (Joule 2.0-ready).** Expose an A2A surface + `asset.yaml` ORD IDs so the
  Joule 2.0 migration is an infra swap, not a rewrite.
- **Model isolation.** One env var (`AGENT_MODEL`, e.g. `sap/anthropic--claude-...`). Never
  hard-code a model name in logic.
- **Mock-first always.** Build and test fully offline (`IBD_TESTING=1`, `mcp-mock.json`)
  before connecting live SAP. Gate: tests green offline before `cf push`.

### Security
- JWT validated at the A2A boundary (JWKS, `aud`, `iss`, `exp`) before any tool runs.
- Principal propagation: the end-user identity flows to the SAP backend unless a documented
  service-user justification exists.
- Rate limiting + resilience: back off on 429; circuit-break after 3 consecutive failures.
- No secrets in code, logs, or markdown — `.env` (gitignored) locally, VCAP_SERVICES in CF.

### Grounding & data
- Structured grounding via OData / Agent Gateway. Direct Destination only with justification.
- RAG: evaluate SAP Document Grounding Service first; build custom only if you need custom
  chunking, structure-aware extraction, chunk-level ACL, or vector-store control.
- Cap context to the model window minus ~20% headroom; summarize tool payloads > 8 KB.

### Deployment
- Cloud Foundry (BTP), manifest-driven (`manifest.yml`), port 8080, entry `python -m app`.
- VCAP_SERVICES is the credential store in CF. Coverage gate ≥ 70% before any deploy.

---

## Project facts (fill per engagement)

| Field | Value |
|---|---|
| Client | [CLIENT INPUT] |
| Use case | [CLIENT INPUT] |
| Agent name | [TODO: after `./rename.sh`] |
| Build path | [CoE / KG / AI Factory] |
| CF region / org / space | [VERIFY] |
| SAP connectivity mode | [Mock / Agent Gateway / Direct Destination] |
| Write access | advisory-only (no POST/PATCH/DELETE) unless [CLIENT INPUT] says otherwise |

## Hard rules for this project

1. Mock-first: `IBD_TESTING=1` tests must pass before any live SAP connection.
2. JWT validated at the A2A boundary before any tool runs.
3. No secrets in the repo — only `.env` (gitignored) / VCAP bindings.
4. Never fabricate API endpoint names, OData entity sets, or SAP feature IDs. If unconfirmed,
   write "**[VERIFY]** — not confirmed, placeholder only."
5. Every Quality-Gate (`QG-*`) and Code-Review (`CR-*`) check recorded in
   `docs/quality-gate-report.md` / `docs/code-review-report.md` — none silently skipped; mark
   framework-gated checks `N/A` honestly rather than faking a pass.
6. Re-verify Joule schema versions and AI Core model names against the target tenant — see
   `DESIGN_RATIONALE.md` → "What you MUST re-verify per engagement."
