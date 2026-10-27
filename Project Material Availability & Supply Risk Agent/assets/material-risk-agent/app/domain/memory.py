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


class HanaMemoryStore(MemoryStore):
    """PLACEHOLDER — durable HANA Cloud audit store for the decision/intervention log.

    Persists each record to ``<HANA_SCHEMA>.<HANA_DECISION_TABLE>`` (append-only, backed
    by an INSERT/SELECT-only role) and uses the HANA Cloud Vector Engine
    (``HANA_VECTOR_TABLE``) for semantic recall — behind this exact ``MemoryStore``
    interface, so business logic and tests do not change.

    Not wired yet: requires the ``hdbcli`` driver and a provisioned/bound HANA Cloud
    instance. Selected only when ``MEMORY_BACKEND=hana``. See the data-readiness
    questionnaire (docs/) for what the client must provision.
    """

    def __init__(self) -> None:  # pragma: no cover - placeholder, not reachable in tests
        raise NotImplementedError(
            "HANA Cloud persistence is a placeholder. To enable MEMORY_BACKEND=hana: "
            "provision HANA Cloud, create ZAGENT_DECISION_LOG (+ vector table) under a "
            "schema with an INSERT/SELECT-only role, add the `hdbcli` dependency, and "
            "implement record()/recall() against it. See docs/ (data-readiness §HANA Cloud)."
        )


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
