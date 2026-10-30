"""Institutional memory (Design PDF · 3 memory types).

Append-only store (mirrors a HANA INSERT/SELECT-only role — no update/delete):
  1. intervention_outcome  — what an expedite/split/escalation actually recovered
  2. supplier_comm_pref    — which channel a vendor responds to fastest
  3. escalation_pattern    — gap x float combinations that self-corrected vs slipped

Used at inference time to weight supplier responsiveness and escalation calibration.
In production this is a HANA Cloud table + vector recall; here it is in-process.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import config

INTERVENTION_OUTCOME = "intervention_outcome"
SUPPLIER_COMM_PREF = "supplier_comm_pref"
ESCALATION_PATTERN = "escalation_pattern"
_TYPES = (INTERVENTION_OUTCOME, SUPPLIER_COMM_PREF, ESCALATION_PATTERN)


class MemoryStore:
    """Thread-safe, append-only, in-process memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[dict] = []

    def record(self, mem_type: str, payload: dict) -> dict:
        if mem_type not in _TYPES:
            raise ValueError(f"Unknown memory type: {mem_type}")
        rec = {
            "record_id": uuid.uuid4().hex[:12].upper(),
            "mem_type": mem_type,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self._lock:
            self._records.append(rec)
        return dict(rec)

    def recall(self, mem_type: str | None = None, **filters) -> list[dict]:
        with self._lock:
            rows = list(self._records)
        if mem_type:
            rows = [r for r in rows if r["mem_type"] == mem_type]
        for k, v in filters.items():
            rows = [r for r in rows if r.get(k) == v]
        return rows

    def supplier_responsiveness(self, vendor: str, material: str | None = None) -> float:
        """0..1 responsiveness score from prior intervention outcomes; 0.5 if unknown."""
        rows = self.recall(INTERVENTION_OUTCOME, vendor=vendor)
        if material:
            rows = [r for r in rows if r.get("material") in (None, material)]
        if not rows:
            return 0.5
        recovered = [1.0 if int(r.get("days_recovered", 0)) > 0 else 0.0 for r in rows]
        return round(sum(recovered) / len(recovered), 2)

    def repeat_offender(self, vendor: str, material: str | None = None) -> int:
        rows = self.recall(ESCALATION_PATTERN, vendor=vendor)
        if material:
            rows = [r for r in rows if r.get("material") in (None, material)]
        return len(rows)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


def _hana_credentials() -> dict:
    """Resolve HANA Cloud connection params from the bound 'hana' service (VCAP) or HANA_* env.

    Expects host / port / user / password (+ optional schema) — the standard hdbcli
    connection shape. Raises with guidance when nothing is bound/configured.
    """
    import json
    import os

    raw = os.environ.get("VCAP_SERVICES")
    if raw:
        try:
            services = json.loads(raw)
        except (ValueError, TypeError):
            services = {}
        for name in ("hana", "hanacloud"):
            binds = services.get(name) or []
            if binds:
                c = binds[0].get("credentials") or {}
                host = c.get("host") or c.get("hostname")
                if host and c.get("user") and c.get("password"):
                    return {
                        "host": host,
                        "port": int(c.get("port") or 443),
                        "user": c["user"],
                        "password": c["password"],
                        "schema": c.get("schema") or config.HANA_SCHEMA or c["user"],
                    }
    # Fallback: explicit HANA_* env (local validation / cf set-env).
    host = os.environ.get("HANA_HOST")
    if host and os.environ.get("HANA_USER") and os.environ.get("HANA_PASSWORD"):
        return {
            "host": host,
            "port": int(os.environ.get("HANA_PORT") or 443),
            "user": os.environ["HANA_USER"],
            "password": os.environ["HANA_PASSWORD"],
            "schema": os.environ.get("HANA_SCHEMA") or os.environ["HANA_USER"],
        }
    raise RuntimeError(
        "HANA Cloud is not configured. Bind a 'hana' service (host/user/password/schema) "
        "to the CF app, or set HANA_HOST/HANA_USER/HANA_PASSWORD. "
        "Create ZAGENT_DECISION_LOG first — see docs/hana/ZAGENT_DECISION_LOG.sql."
    )


class HanaMemoryStore(MemoryStore):
    """Durable HANA Cloud audit store for the decision/intervention log.

    Persists each record to ``<schema>.<HANA_DECISION_TABLE>`` (append-only — INSERT/SELECT
    only, no update/delete) behind the same ``MemoryStore`` interface, so business logic
    and tests are unchanged. Selected only when ``MEMORY_BACKEND=hana``. The free-text
    payload is stored as JSON; ``HANA_VECTOR_TABLE`` (Vector Engine) semantic recall is a
    later enhancement — recall here is attribute-filtered SELECT, same contract as in-memory.

    Requires the ``hdbcli`` driver and a provisioned/bound HANA Cloud instance. Create the
    table with docs/hana/ZAGENT_DECISION_LOG.sql.
    """

    def __init__(self) -> None:
        import threading as _threading

        from hdbcli import dbapi  # lazy — only imported when MEMORY_BACKEND=hana

        self._lock = _threading.Lock()
        self._records = []  # unused; kept so inherited helpers never attribute-error
        creds = _hana_credentials()
        self._schema = creds["schema"]
        self._table = config.HANA_DECISION_TABLE
        self._conn = dbapi.connect(
            address=creds["host"], port=creds["port"],
            user=creds["user"], password=creds["password"],
            encrypt=True, sslValidateCertificate=True, autocommit=True,
        )

    def _qualified_table(self) -> str:
        return f'"{self._schema}"."{self._table}"'

    def record(self, mem_type: str, payload: dict) -> dict:
        import json
        import uuid
        from datetime import datetime, timezone

        if mem_type not in _TYPES:
            raise ValueError(f"Unknown memory type: {mem_type}")
        rec = {
            "record_id": uuid.uuid4().hex[:12].upper(),
            "mem_type": mem_type,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                f'INSERT INTO {self._qualified_table()} '
                '("RECORD_ID","MEM_TYPE","CREATED_UTC","VENDOR","MATERIAL","PAYLOAD") '
                "VALUES (?,?,?,?,?,?)",
                (rec["record_id"], mem_type, rec["created_utc"],
                 str(payload.get("vendor") or ""), str(payload.get("material") or ""),
                 json.dumps(payload)),
            )
            cur.close()
        return dict(rec)

    def recall(self, mem_type: str | None = None, **filters) -> list[dict]:
        import json

        sql = (f'SELECT "RECORD_ID","MEM_TYPE","CREATED_UTC","PAYLOAD" '
               f'FROM {self._qualified_table()}')
        params: list = []
        if mem_type:
            sql += ' WHERE "MEM_TYPE" = ?'
            params.append(mem_type)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        out: list[dict] = []
        for record_id, mt, created_utc, payload_json in rows:
            payload = json.loads(payload_json) if payload_json else {}
            rec = {"record_id": record_id, "mem_type": mt,
                   "created_utc": created_utc, **payload}
            if all(rec.get(k) == v for k, v in filters.items()):
                out.append(rec)
        return out

    def clear(self) -> None:  # append-only: no delete in production
        raise NotImplementedError("HANA audit store is append-only; clear() is disabled.")


_STORE: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _STORE
    if _STORE is None:
        if config.memory_backend() == "hana":
            _STORE = HanaMemoryStore()  # placeholder — raises until implemented
        else:
            _STORE = MemoryStore()
            _seed(_STORE)
    return _STORE


def reset_memory_store() -> None:
    """Test helper — reset to a freshly seeded store."""
    global _STORE
    _STORE = None


def _seed(store: MemoryStore) -> None:
    """One prior outcome + comm preference for ABC Steel on structural steel."""
    store.record(INTERVENTION_OUTCOME, {
        "vendor": "1001", "material": "1000234", "action_type": "expedite",
        "days_recovered": 6, "float_restored": True, "outcome_date": "2026-05-20",
    })
    store.record(SUPPLIER_COMM_PREF, {
        "vendor": "1001", "preferred_channel": "phone", "avg_response_hours": 6,
        "last_contact": "2026-05-15",
    })
    store.record(ESCALATION_PATTERN, {
        "vendor": "1001", "material": "1000234", "supply_gap_days": 12,
        "float_remaining": -3, "self_corrected": False,
    })
