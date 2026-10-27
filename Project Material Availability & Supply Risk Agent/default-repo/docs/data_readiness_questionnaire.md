# Data Readiness Questionnaire

Confirm these items with the client before Sprint 2. Send the email template in `client_sprint1_email.md`.

---

## 1. SAP System Access

| Question | Client Answer |
|----------|--------------|
| Is there a development / sandbox S/4HANA system available? | |
| What is the S/4HANA release (e.g. 2022, 2023)? | |
| Can you provide OData service read access (no write permissions needed for Sprint 2)? | |
| Is the system on-premise or cloud? | |
| If on-premise: is SAP Cloud Connector already configured for BTP? | |

---

## 2. Data Availability

| Question | Client Answer |
|----------|--------------|
| Are the target OData services activated in the dev system? | |
| Is there representative test data in the dev system? | |
| Are the relevant SAP roles assigned to the technical user we'll use for the BTP Destination? | |
| Are there any data classification restrictions (personal data, confidential)? | |

---

## 3. BTP Environment

| Question | Client Answer |
|----------|--------------|
| Has AI Core Extended been provisioned in the BTP subaccount? | |
| Has Cloud Foundry been enabled in the subaccount? | |
| Is there an existing CF space we can use, or should we create a new one? | |
| Who is the BTP Global Account admin we should coordinate with? | |

---

## 4. Joule (Sprint 3+)

| Question | Client Answer |
|----------|--------------|
| Is Joule enabled in the BTP subaccount? | |
| Is IAS (SAP Cloud Identity Services) configured and linked to BTP? | |
| Is there an existing Joule instance, or does one need to be created? | |
| Who is the Joule admin contact? | |

---

## 5. HANA Cloud — decision/approval persistence (Sprint 4)

The agent persists its recommendations and approvals to an append-only backend table on
HANA Cloud (the audit trail), and optionally uses the HANA Cloud Vector Engine for semantic
recall of prior decisions. Confirm the following so this can be provisioned.

| Question | Client Answer |
|----------|--------------|
| Is a HANA Cloud instance available (or should one be provisioned) in the BTP subaccount? | |
| Can a schema be created for the agent (e.g. `ADARSH_AGENT`)? | |
| Approval to create the audit table `ZAGENT_DECISION_LOG` (+ a vector table for recall)? | |
| Can a technical user be created with an **INSERT/SELECT-only** role on that schema (no update/delete)? | |
| Will credentials be shared via a HANA service key, or bound to CF as an HDI-container / schema service? | |
| Is the HANA Cloud Vector Engine enabled (needed for semantic recall of past decisions)? | |
| Any data-residency / retention requirements for the stored decisions? | |

---

## 6. Stakeholders

| Role | Name | Contact |
|------|------|---------|
| Business sponsor | | |
| Technical lead / BTP admin | | |
| S/4HANA basis admin | | |
| HANA Cloud / DB admin | | |
| Functional consultant (data sign-off) | | |
