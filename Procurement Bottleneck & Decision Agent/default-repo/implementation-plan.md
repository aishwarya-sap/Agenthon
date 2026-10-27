# Implementation Plan — [ClientName] [Use Case]
**Revision:** 1.0 | **Date:** [DATE] | **Author:** [CLIENT INPUT]

> The engineering work plan; drives work tickets. Written for the dev team. (SAP Agent solution-doc standard)
> Phases map to the 4-sprint delivery (see README → Sprint delivery gates).

## Phase 0 — Foundations (pre-code)
- [ ] ATQ review gate triggered and sign-off received
- [ ] API Policy self-check completed
- [ ] All APIs confirmed Published on SAP Business Accelerator Hub
- [ ] Clean Core levels documented
- [ ] Idea2Value value case captured
- [ ] LLM selection: benchmark data or justification for default model
- [ ] Cost estimate reviewed; per-transaction ceiling agreed

## Phase 1 — Scaffold + Mock (IBD_TESTING=1)
- [ ] Repo cloned from default-repo; `./rename.sh <agent-name>` run
- [ ] `mcp-mock.json` authored for all in-scope entity sets
- [ ] Golden Q&A pairs authored (min. 12; edge cases: empty result, 404, ambiguous input)
- [ ] All tests green offline (IBD_TESTING=1, coverage ≥ 70%)
- [ ] No secrets in code; `.env.example` complete

## Phase 2 — Connect Live SAP
- [ ] Agent Gateway / Destination configured
- [ ] JWT validation at A2A boundary implemented (harden from the Sprint-3 TODO in main.py)
- [ ] Principal propagation decision documented (user identity vs service user + justification)
- [ ] Rate limiting + 429 backoff + circuit breaker (3 failures)
- [ ] Token window cap implemented
- [ ] Structured logs: `correlation_id`, `tool_name`, `latency_ms`, tokens — NO secrets/PII

## Phase 3 — Deploy to BTP
- [ ] `manifest.yml` complete (service bindings, `AGENT_MODEL`, `AGENT_PUBLIC_URL`)
- [ ] `cf push` to target space
- [ ] Agent card live on CF URL (public, accessible)
- [ ] VCAP_SERVICES binding verified (no `.env` in deployed app)
- [ ] Health check endpoint responding

## Phase 4 — Joule Integration (if in scope)
- [ ] Capability bundle authored (already scaffolded in `joule/`)
- [ ] Skill id in function file matches `AgentSkill(id=...)` in `agent_card.py`
- [ ] Joule schema versions re-verified against target tenant (`joule status`)
- [ ] IAS App2App `Cli2Joule` dependency confirmed with IAS admin
- [ ] `joule deploy ./joule/da.sapdas.yaml --compile -n "<assistant_name>"`
- [ ] Skill visible in Joule Studio

## Phase 5 — Govern, Test, Release
- [ ] L0–L10 checklist fully populated in `agent-outcome-report.md`
- [ ] Safety Dashboard run (or formally deferred with justification)
- [ ] Adversarial / red-team testing: prompt injection, role boundary, write refusal
- [ ] Regression suite run on each change
- [ ] Cost actual vs estimate reconciled
- [ ] Cross-functional sign-off recorded
- [ ] Cleanup: stray files, temp credentials, test data removed

## Joule 2.0 readiness (built-in to this kit)
- [ ] A2A surface exposed
- [ ] `asset.yaml` ORD IDs present
- [ ] All connectivity switchable via env (not hard-coded)
