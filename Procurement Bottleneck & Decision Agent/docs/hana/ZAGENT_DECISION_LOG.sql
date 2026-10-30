-- ZAGENT_DECISION_LOG — append-only audit store for agent recommendations & approvals.
-- Run once in the HANA Cloud instance the agent binds to (MEMORY_BACKEND=hana).
--
-- Security model: the agent's technical user gets INSERT + SELECT only (no UPDATE/DELETE),
-- which preserves the append-only audit guarantee at the database level.
--
-- Replace <SCHEMA> with the agent's schema and <AGENT_TECH_USER> with the bound
-- HANA technical user before running.

CREATE SCHEMA "<SCHEMA>";

CREATE COLUMN TABLE "<SCHEMA>"."ZAGENT_DECISION_LOG" (
    "RECORD_ID"    NVARCHAR(32)  PRIMARY KEY,
    "MEM_TYPE"     NVARCHAR(40)  NOT NULL,
    "CREATED_UTC"  NVARCHAR(32)  NOT NULL,
    "VENDOR"       NVARCHAR(20),
    "MATERIAL"     NVARCHAR(40),
    "PAYLOAD"      NCLOB                       -- full record as JSON
);

-- Optional: vector table for semantic recall (HANA Cloud Vector Engine).
-- Enable the Vector Engine on the instance first; dimension matches your embedding model.
CREATE COLUMN TABLE "<SCHEMA>"."ZAGENT_DECISION_VEC" (
    "RECORD_ID"    NVARCHAR(32)  PRIMARY KEY,
    "EMBEDDING"    REAL_VECTOR(1536),
    "NOTE"         NCLOB
);

-- Append-only role: INSERT + SELECT only, no UPDATE/DELETE.
CREATE ROLE "ZAGENT_AUDIT_WRITER";
GRANT INSERT, SELECT ON "<SCHEMA>"."ZAGENT_DECISION_LOG" TO "ZAGENT_AUDIT_WRITER";
GRANT INSERT, SELECT ON "<SCHEMA>"."ZAGENT_DECISION_VEC" TO "ZAGENT_AUDIT_WRITER";
GRANT "ZAGENT_AUDIT_WRITER" TO "<AGENT_TECH_USER>";
