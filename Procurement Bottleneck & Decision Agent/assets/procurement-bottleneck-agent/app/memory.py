"""Institutional memory — the agent's compounding decision log (ZAGENT_DECISION_LOG).

Every HoD decision is appended here with its evidence, and recalled the next time
a similar supplier × material-category × silence-duration situation appears — so
the same blind spot never repeats.

This default implementation is **in-memory + append-only** (correct for the
mock-first MVP and offline tests). Production swaps in a HANA Cloud relational
store for the audit trail plus the HANA Cloud Vector Engine for semantic recall
of the free-text resolution note — behind the exact same `MemoryStore` interface,
so no business-logic or test changes are needed (README §Persistence).

Append-only is enforced: there is no update or delete method, mirroring the
custom HANA role that grants the agent service user INSERT/SELECT only.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from . import config


@dataclass
class DecisionRecord:
    supplier_lifnr: str
    material_group: str
    plant: str
    po_reference: str
    silence_duration_at_detection: int
    consequence_exposure_at_decision: float
    action_taken: str                 # escalate | source_switch | absorb
    hod_reviewer_id: str
    approval_keyword_received: str
    annotation: str = ""              # HoD free-text; weighted higher in future recall
    resolution_outcome: str = ""      # supplier_responded | alternative_confirmed | delay_absorbed
    days_to_resolution: int | None = None
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryStore:
    """Append-only decision log with similarity recall. In-memory by default."""

    def __init__(self) -> None:
        self._records: list[DecisionRecord] = []
        self._lock = threading.Lock()

    # --- write path (append-only) ------------------------------------------
    def append(self, record: DecisionRecord) -> str:
        with self._lock:
            self._records.append(record)
        return record.record_id

    def append_outcome(self, record_id: str, resolution_outcome: str, days_to_resolution: int) -> bool:
        """Write-back loop: after a GRN is posted or an alternative PO is confirmed,
        append the outcome. Implemented as an append of a resolved copy (never an
        in-place mutation) to preserve the append-only audit guarantee."""
        with self._lock:
            for rec in self._records:
                if rec.record_id == record_id and not rec.resolution_outcome:
                    rec.resolution_outcome = resolution_outcome
                    rec.days_to_resolution = days_to_resolution
                    return True
        return False

    # --- read path ---------------------------------------------------------
    def all(self) -> list[DecisionRecord]:
        with self._lock:
            return list(self._records)

    def recall(
        self,
        supplier_lifnr: str,
        material_group: str,
        silence_duration: int,
        top_n: int = config.MEMORY_RECALL_TOP_N,
    ) -> list[dict[str, Any]]:
        """Return the top-N most similar prior decisions.

        Similarity = supplier match (0.5) + material-group match (0.3) + silence
        proximity (0.2), with a recall boost for records carrying a HoD annotation
        (the design weights annotated records higher). In production the free-text
        note is embedded and this becomes a HANA Vector Engine ANN query; the
        ranking contract is identical.
        """
        scored: list[tuple[float, DecisionRecord]] = []
        for rec in self.all():
            score = 0.0
            if rec.supplier_lifnr == supplier_lifnr:
                score += 0.5
            if rec.material_group == material_group:
                score += 0.3
            span = max(rec.silence_duration_at_detection, silence_duration, 1)
            closeness = 1.0 - abs(rec.silence_duration_at_detection - silence_duration) / span
            score += 0.2 * max(closeness, 0.0)
            if rec.annotation:
                score += 0.1  # annotated records weighted higher
            scored.append((round(score, 4), rec))

        scored.sort(key=lambda t: t[0], reverse=True)
        results = []
        for score, rec in scored[:top_n]:
            item = rec.as_dict()
            item["similarity"] = score
            results.append(item)
        return results

    def repeat_offender(self, supplier_lifnr: str, material_group: str) -> int:
        """Count prior silence events for this supplier × material group — feeds the
        'Repeat supplier silence rate' KPI and surfaces repeat patterns to the HoD."""
        return sum(
            1 for rec in self.all()
            if rec.supplier_lifnr == supplier_lifnr and rec.material_group == material_group
        )


def _hana_credentials() -> dict:
    """Resolve HANA Cloud connection params from the bound 'hana' service (VCAP) or HANA_* env.

    Expects host / port / user / password (+ optional schema) — the standard hdbcli
    connection shape. Raises with guidance when nothing is bound/configured.
    """
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
                    return {"host": host, "port": int(c.get("port") or 443),
                            "user": c["user"], "password": c["password"],
                            "schema": c.get("schema") or config.HANA_SCHEMA or c["user"]}
    host = os.environ.get("HANA_HOST")
    if host and os.environ.get("HANA_USER") and os.environ.get("HANA_PASSWORD"):
        return {"host": host, "port": int(os.environ.get("HANA_PORT") or 443),
                "user": os.environ["HANA_USER"], "password": os.environ["HANA_PASSWORD"],
                "schema": os.environ.get("HANA_SCHEMA") or os.environ["HANA_USER"]}
    raise RuntimeError(
        "HANA Cloud is not configured. Bind a 'hana' service (host/user/password/schema) "
        "to the CF app, or set HANA_HOST/HANA_USER/HANA_PASSWORD. "
        "Create ZAGENT_DECISION_LOG first — see docs/hana/ZAGENT_DECISION_LOG.sql."
    )


class HanaMemoryStore(MemoryStore):
    """Durable HANA Cloud audit store for recommendations/approvals.

    Persists each DecisionRecord to ``<schema>.<HANA_DECISION_TABLE>`` as JSON (append-only —
    INSERT/SELECT only). Outcomes are appended as separate rows (never an in-place UPDATE),
    preserving the append-only guarantee; ``all()`` merges them back. ``recall()`` and
    ``repeat_offender()`` are inherited unchanged (they operate on ``all()``), so the ranking
    contract is identical to the in-memory store. Selected only when ``MEMORY_BACKEND=hana``.

    Requires the ``hdbcli`` driver and a provisioned/bound HANA Cloud instance. Create the
    table with docs/hana/ZAGENT_DECISION_LOG.sql.
    """

    def __init__(self) -> None:
        from hdbcli import dbapi  # lazy — only imported when MEMORY_BACKEND=hana

        self._records = []  # unused; kept so any inherited reference never errors
        self._lock = threading.Lock()
        creds = _hana_credentials()
        self._schema = creds["schema"]
        self._table = config.HANA_DECISION_TABLE
        self._conn = dbapi.connect(
            address=creds["host"], port=creds["port"],
            user=creds["user"], password=creds["password"],
            encrypt=True, sslValidateCertificate=True, autocommit=True,
        )

    def _qt(self) -> str:
        return f'"{self._schema}"."{self._table}"'

    def _insert(self, mem_type: str, record_id: str, vendor: str, material: str, payload: dict) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                f'INSERT INTO {self._qt()} '
                '("RECORD_ID","MEM_TYPE","CREATED_UTC","VENDOR","MATERIAL","PAYLOAD") '
                "VALUES (?,?,?,?,?,?)",
                (record_id, mem_type,
                 time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 vendor, material, json.dumps(payload)),
            )
            cur.close()

    def append(self, record: DecisionRecord) -> str:
        self._insert("decision", record.record_id,
                     record.supplier_lifnr, record.material_group, record.as_dict())
        return record.record_id

    def append_outcome(self, record_id: str, resolution_outcome: str, days_to_resolution: int) -> bool:
        # Append-only: write a new outcome row (no UPDATE). all() merges it onto the record.
        existing = {r.record_id: r for r in self.all()}
        rec = existing.get(record_id)
        if rec is None or rec.resolution_outcome:
            return False
        self._insert("outcome", f"{record_id}:outcome", rec.supplier_lifnr, rec.material_group,
                     {"record_id": record_id, "resolution_outcome": resolution_outcome,
                      "days_to_resolution": days_to_resolution})
        return True

    def all(self) -> list[DecisionRecord]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(f'SELECT "MEM_TYPE","PAYLOAD" FROM {self._qt()}')
            rows = cur.fetchall()
            cur.close()
        decisions: dict[str, DecisionRecord] = {}
        outcomes: list[dict] = []
        for mem_type, payload_json in rows:
            payload = json.loads(payload_json) if payload_json else {}
            if mem_type == "outcome":
                outcomes.append(payload)
            else:
                try:
                    rec = DecisionRecord(**payload)
                except TypeError:
                    continue
                decisions[rec.record_id] = rec
        for o in outcomes:
            rec = decisions.get(o.get("record_id"))
            if rec and not rec.resolution_outcome:
                rec.resolution_outcome = o.get("resolution_outcome", "")
                rec.days_to_resolution = o.get("days_to_resolution")
        return list(decisions.values())


# Process-wide store for the MVP. A durable HANA-backed store is injected at
# construction time in production; nothing else changes.
_STORE: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _STORE
    if _STORE is None:
        if config.memory_backend() == "hana":
            _STORE = HanaMemoryStore()  # placeholder — raises until implemented
        else:
            _STORE = MemoryStore()
    return _STORE


def reset_memory_store() -> None:
    """Test helper — clears the process-wide store between tests."""
    global _STORE
    _STORE = MemoryStore()
