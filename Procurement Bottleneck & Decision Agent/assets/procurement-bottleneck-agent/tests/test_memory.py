"""Institutional-memory unit tests."""
import pytest

from app.memory import DecisionRecord, get_memory_store

pytestmark = pytest.mark.unit


def _rec(**o):
    d = dict(supplier_lifnr="LIFNR-0010045", material_group="STEEL", plant="1710",
             po_reference="4500000123", silence_duration_at_detection=11,
             consequence_exposure_at_decision=192400.0, action_taken="escalate",
             hod_reviewer_id="HOD-ADARSH", approval_keyword_received="approve")
    d.update(o)
    return DecisionRecord(**d)


def test_append_and_all():
    store = get_memory_store()
    rid = store.append(_rec())
    assert rid
    assert len(store.all()) == 1


def test_recall_ranks_same_supplier_and_material_first():
    store = get_memory_store()
    store.append(_rec(annotation="held once; alt confirmed"))
    store.append(_rec(supplier_lifnr="LIFNR-9999999", material_group="CONCRETE"))
    results = store.recall("LIFNR-0010045", "STEEL", 11)
    assert results[0]["supplier_lifnr"] == "LIFNR-0010045"
    assert results[0]["similarity"] >= results[-1]["similarity"]


def test_repeat_offender_count():
    store = get_memory_store()
    store.append(_rec())
    store.append(_rec())
    assert store.repeat_offender("LIFNR-0010045", "STEEL") == 2


def test_append_outcome_writeback():
    store = get_memory_store()
    rid = store.append(_rec())
    assert store.append_outcome(rid, "alternative_confirmed", 2) is True
    rec = store.all()[0]
    assert rec.resolution_outcome == "alternative_confirmed"
    assert rec.days_to_resolution == 2


def test_no_update_or_delete_methods():
    store = get_memory_store()
    assert not hasattr(store, "update")
    assert not hasattr(store, "delete")
