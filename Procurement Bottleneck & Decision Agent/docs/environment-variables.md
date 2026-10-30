# Environment Variables — Procurement Bottleneck & Decision Agent

All configuration is read from the **process environment** (`os.environ`). There is no
`.env` file and no credential file in this repo.

- **Local development:** `IBD_TESTING=1` runs fully offline on mock data — no credentials.
- **Cloud Foundry (client deployment):** credentials arrive from **bound service instances**
  (`VCAP_SERVICES`) and **BTP Destinations**; non-secret config via `mta.yaml` / `cf set-env`.
  No secret is ever stored in a committed file.

## Run mode
| Variable | Default | Purpose |
|---|---|---|
| `IBD_TESTING` | unset | `1` = offline mock mode (no credentials needed) |
| `SAP_MODE` | `gateway` | `mock` \| `accelerator_hub` (sandbox APIKey) \| `onprem` (destination + Cloud Connector) \| `gateway` (SAP Cloud SDK) |
| `PROJECT_DATA_SOURCE` | `SAP_PS` | `SAP_PS` \| `EXCEL` (Phase 1 upload) |

## S/4HANA (on-prem via BTP Destination + Cloud Connector — `SAP_MODE=onprem`)
| Variable | Default | Purpose |
|---|---|---|
| `S4_DESTINATION` | `S4HANA_DEV_HTTP` | BTP destination name (OnPremise, BasicAuthentication) |
| `S4_SAP_CLIENT` | `150` | Client number appended to on-prem OData calls |
| `S4_SCC_LOCATION_ID` | unset | Cloud Connector Location ID (only if your SCC uses one) |
| `S4_BASE_URL` / `S4_API_KEY` | unset | Accelerator Hub sandbox path only (`SAP_MODE=accelerator_hub`) |

Bind the **`destination`** and **`connectivity`** service instances. Credentials (tech user,
URL, sap-client) live in the destination — never in the repo.

## AI Core (bound service instance)
Bind an `aicore` service instance. `app/main.py` maps its credentials
(`clientid`/`clientsecret`/`url`/`serviceurls.AI_API_URL`) into `AICORE_*` at startup —
no secret in the repo.

## Identity / Joule
| Variable | Purpose |
|---|---|
| `AGENT_AUTH_MODE` | `mock` \| `ias` \| `xsuaa` (Joule delivers IAS) |
| `IAS_ISSUER` / `IAS_AUDIENCE` / `IAS_REQUIRED_API` / `IAS_JWKS_URI` | IAS inbound token validation |
| `ENABLE_WHOAMI` | `1` exposes `/whoami` identity-chain + S/4 canary — **never in production** |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins — lock to the Joule/BTP origin for prod |

## Decision/approval persistence — HANA Cloud
| Variable | Default | Purpose |
|---|---|---|
| `MEMORY_BACKEND` | `in_memory` | `in_memory` \| `hana` |
| `HANA_SCHEMA` | (binding) | Schema for the audit table |
| `HANA_DECISION_TABLE` | `ZAGENT_DECISION_LOG` | Append-only audit table |
| `HANA_VECTOR_TABLE` | `ZAGENT_DECISION_VEC` | Vector table (semantic recall — later) |

When `MEMORY_BACKEND=hana`, connection params (`host`/`port`/`user`/`password`/`schema`) come
from the bound **`hana`** service (`VCAP_SERVICES`) or `HANA_HOST`/`HANA_USER`/`HANA_PASSWORD`.
Create the table first with `docs/hana/ZAGENT_DECISION_LOG.sql`. The default `in_memory` needs
no HANA at all.
