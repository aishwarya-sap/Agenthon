# Sprint 1 Client Email Template

> **Usage:** Send this after the Sprint 1 kickoff call. Fill in `[...]` placeholders before sending.

---

**Subject:** [Agent Name] — Sprint 1 Kickoff: Repo Access + Data Readiness Confirmation

---

Hi [Client Name],

Thank you for joining the Sprint 1 kickoff call for the **[Agent Name]** Agenthon program.

## What we delivered in Sprint 1

We have deployed a working version of the agent on SAP BTP (mock mode) that demonstrates the core agent interaction flow. The agent is accessible at:

- **Chat UI:** `[UI Route URL]`
- **Agent Card:** `[Agent Route URL]/.well-known/agent.json`

## What we need from you before Sprint 2

To connect the agent to your SAP S/4HANA development system in Sprint 2, we need the following confirmed by **[Date]**:

1. **BTP subaccount details**
   - Subaccount name / GUID: `___`
   - Region: `___`
   - Is AI Core Extended provisioned? ☐ Yes / ☐ No

2. **S/4HANA dev system access**
   - System SID: `___`
   - Client: `___`
   - Is it on-premise or cloud? ___
   - OData services activated for read access? ☐ Yes / ☐ No
   - Technical user / service account name: `___`

3. **Cloud Connector** (on-premise only)
   - Is Cloud Connector already configured and connected to the BTP subaccount? ☐ Yes / ☐ No

4. **Test data** — do you have representative data in the dev system that matches the agent's use case? ☐ Yes / ☐ No

Please complete the attached [data readiness questionnaire](data_readiness_questionnaire.md) and return it at your earliest convenience.

## Repo access

The Sprint 1 default repo has been shared with your team at: `[Repo URL / Path]`

To run it locally in mock mode:
```bash
cp .env.example .env
# Fill in AICORE_* values in .env
IBD_TESTING=1 python app/_boot.py
```

To deploy to your CF space:
```bash
./deploy.sh   # will prompt for CF domain and org
```

## Next sprint

Sprint 2 starts on **[Date]**. Goal: connect the agent to live S/4HANA data in your dev system and run technical + functional validation with your team.

Please don't hesitate to reach out if you have any questions.

Best regards,  
[Your Name]  
[Your Team]
