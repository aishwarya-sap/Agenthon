# Token Calculation — Material Risk Agent (Sprint 3)

Token estimates per interaction type, using the SAP GenAI Hub cost formula.

---

## Cost Formula

```
Cost per call (EUR) =
    (Input_Tokens / 1000 × Input_Rate)
  + (Output_Tokens / 1000 × Output_Rate)
  + (Cached_Read_Tokens / 1000 × Cache_Read_Rate)

Capacity Units (CU) per call = Total_EUR_tokens × 1.90385
Monthly cost = ROUND(Total_CU/month) × EUR/CU
```

Rates (SAP AI Core, Claude claude-4.5-sonnet, observed July 2026 — verify current rates in SAP AI Core calculator):

| Token type | Rate (USD/1k) |
|-----------|--------------|
| Input | $3.00 |
| Output | $15.00 |
| Cache read | $0.30 |
| Cache write | $3.75 |

---

## Interaction Type Estimates

| Interaction | Input tokens | Output tokens | Cache read | Est. cost (USD) | Est. CU |
|-------------|-------------|--------------|------------|-----------------|---------|
| Simple query (stock check) | 2,000 | 500 | 1,500 | $0.012 | 0.02 |
| Standard risk report (1 material) | 8,000 | 2,000 | 5,000 | $0.057 | 0.11 |
| Full project supply risk (P-ALPHA-01) | 15,000 | 4,000 | 8,000 | $0.109 | 0.21 |
| Multi-material + supplier history | 20,000 | 6,000 | 10,000 | $0.153 | 0.29 |
| HITL approval + escalation write | 8,000 | 1,500 | 5,000 | $0.048 | 0.09 |

Notes:
- Cache read tokens are the system prompt + tool schemas (static; cached after first call)
- System prompt: ~1,000 tokens; tool schemas: ~4,000 tokens for 15 tools
- These are estimates; run actual metering after Sprint 3 deployment

---

## Monthly Estimate

Assumptions: 50 active users, 10 interactions/user/day, 22 working days/month = 11,000 calls/month.

| Scenario | Calls/month | Avg cost/call | Monthly cost (USD) | Monthly CU |
|----------|-------------|--------------|-------------------|------------|
| Light use (simple queries) | 11,000 | $0.012 | $132 | 251 |
| Standard use (mix) | 11,000 | $0.070 | $770 | 1,465 |
| Heavy use (full reports) | 11,000 | $0.120 | $1,320 | 2,511 |

---

## Sprint 3 Metering TODO

- [ ] Enable structured logging: `prompt_tokens` + `completion_tokens` per turn (done in `agent_executor.py` — Sprint 3: wire to actual LiteLLM usage callback)
- [ ] Run LiteLLM `UsageTrackingCallback` in `agent.py` to capture real token counts
- [ ] After 1 week of GenAI Hub data: update this table with actuals
- [ ] Set budget ceiling alert in SAP AI Core at 120% of estimated monthly cost
- [ ] Confirm L0-4.3 AI Scenario Metering Integration with SAP team

---

## How to get actual token counts (Sprint 3)

```python
# In agent.py SampleAgent.__init__(), add a LiteLLM callback:
from litellm import callbacks
from litellm.integrations.custom_logger import CustomLogger

class TokenLogger(CustomLogger):
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        usage = response_obj.get("usage", {})
        import logging
        logging.getLogger(__name__).info(
            "token_usage model=%s prompt_tokens=%d completion_tokens=%d",
            kwargs.get("model"), usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
        )

callbacks.append(TokenLogger())
```
