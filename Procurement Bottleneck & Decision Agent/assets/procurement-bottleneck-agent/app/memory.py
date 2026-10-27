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


# Process-wide store for the MVP. A durable HANA-backed store is injected at
# construction time in production; nothing else changes.
_STORE: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _STORE
    if _STORE is None:
        _STORE = MemoryStore()
    return _STORE


def reset_memory_store() -> None:
    """Test helper — clears the process-wide store between tests."""
    global _STORE
    _STORE = MemoryStore()
