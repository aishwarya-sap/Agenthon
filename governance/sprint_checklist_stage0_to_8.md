# Engineering Build Checklist — Stage 0 to Stage 8

Based on the SAP Agent-PathToProd cookbook. Run through these stages in order.
`[code]` items are verified by the automated test harness; `[deploy]` items are developer-verified.

---

## Stage 0 — Pre-build

- [ ] `[deploy]` Use-case approved and Design Narrative signed off
- [ ] `[deploy]` BTP subaccount, CF space, and AI Core instance provisioned
- [ ] `[deploy]` AI Core Extended plan confirmed (required for Joule A2A agents)
- [ ] `[deploy]` Accelerator Hub API key obtained (or SAP Cloud Connector configured for on-prem)
- [ ] `[deploy]` Access to a development S/4HANA system confirmed (for Sprint 2)

---

## Stage 1 — Scaffold & Mock

- [ ] `[code]` Agent card returns valid JSON at `GET /.well-known/agent.json`
- [ ] `[code]` `protocolVersion: "0.3.0"` in agent card
- [ ] `[code]` `POST /` accepts A2A JSON-RPC and returns a response
- [ ] `[code]` `IBD_TESTING=1` mock mode works end-to-end (chat UI → agent → mock tools → response)
- [ ] `[deploy]` Tests pass; coverage ≥ 70%; `test_report.json` written
- [ ] `[code]` System prompt contains all 6 MANDATORY RULES
- [ ] `[code]` Exactly 3 `@agent_*` decorators (`@agent_model`, `@agent_config`, `@prompt_section`)

---

## Stage 2 — SAP Connectivity

- [ ] `[code]` Live S/4HANA tool call succeeds (at least one OData entity read)
- [ ] `[code]` All tool calls use `top=100` (enforced by system prompt)
- [ ] `[code]` `_parse_odata_date()` handles `/Date(epochMs)/` V2 dates
- [ ] `[deploy]` OData entity names verified against `$metadata` (never guessed)
- [ ] `[deploy]` Functional consultant confirms data accuracy

---

## Stage 3 — Auth & Resilience

- [ ] `[code]` JWT validated at A2A boundary (`AGENT_AUTH_MODE=ias` for Joule integration)
- [ ] `[code]` Identity never taken from client-supplied metadata — only from validated JWT
- [ ] `[code]` Circuit breaker configured for LLM fallback chain
- [ ] `[code]` Tool error → graceful reply (no raw stack trace to user)
- [ ] `[deploy]` `/whoami` endpoint confirms IAS identity chain end-to-end

---

## Stage 4 — Observability & Security

- [ ] `[code]` Structured log per turn: `context_id`, `latency_ms`, `prompt_tokens`, `completion_tokens`
- [ ] `[code]` No PII in logs (SAP user IDs, vendor names, email addresses scrubbed)
- [ ] `[code]` No raw SAP error payloads returned to users
- [ ] `[code]` Prompt injection scanner on all tool results
- [ ] `[deploy]` Sonar scan completed with no critical/blocker issues

---

## Stage 5 — CF Deployment

- [ ] `[deploy]` `cf push -f manifest.yml` succeeds without errors
- [ ] `[deploy]` Both agent and UI apps show `started` in `cf apps`
- [ ] `[deploy]` `GET /.well-known/agent.json` returns 200 on the live route
- [ ] `[deploy]` Chat UI sends a message and receives a response
- [ ] `[deploy]` Health check interval confirmed in CF dashboard

---

## Stage 6 — Joule Registration

- [ ] `[deploy]` BTP Destination `<AGENT_NAME>` created pointing to CF agent route
- [ ] `[deploy]` Joule capability YAML (`da.sapdas.yaml`) imported into Joule Studio
- [ ] `[deploy]` Capability activated; test prompt sent via Joule → agent responds
- [ ] `[deploy]` IAS app-to-app dependency configured (A2A Proxy → Custom-Agent IAS app)

---

## Stage 7 — Production Readiness

- [ ] `[deploy]` All 60 L0-pillar checklist items reviewed
- [ ] `[deploy]` UAT completed with representative users
- [ ] `[deploy]` Runbook written (common failures + escalation contacts)
- [ ] `[deploy]` Rollback procedure tested
- [ ] `[deploy]` Production deployment approved by sponsor

---

## Stage 8 — Joule 2.0 / Post-Launch

- [ ] `[deploy]` Advisory & governance: no POST/PATCH/DELETE; top=100; no fabrication; financial disclaimer
- [ ] `[deploy]` Token metering integrated (cost per transaction baselined)
- [ ] `[deploy]` Monitoring alerts configured (latency, error rate, cost ceiling)
- [ ] `[deploy]` Model upgrade path documented and tested
- [ ] `[deploy]` Next-sprint improvements backlogged
