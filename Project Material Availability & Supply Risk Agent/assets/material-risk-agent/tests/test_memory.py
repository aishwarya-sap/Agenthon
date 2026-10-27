"""Institutional memory (3 append-only types)."""
from domain import memory


def test_seeded_memory_has_three_types():
    store = memory.get_memory_store()
    assert store.recall(memory.INTERVENTION_OUTCOME)
    assert store.recall(memory.SUPPLIER_COMM_PREF)
    assert store.recall(memory.ESCALATION_PATTERN)


def test_append_only_and_recall_filter():
    store = memory.get_memory_store()
    before = len(store.recall(memory.INTERVENTION_OUTCOME))
    rec = store.record(memory.INTERVENTION_OUTCOME, {
        "vendor": "1002", "material": "1000567", "action_type": "expedite", "days_recovered": 4})
    assert rec["record_id"]
    assert len(store.recall(memory.INTERVENTION_OUTCOME)) == before + 1
    assert store.recall(memory.INTERVENTION_OUTCOME, vendor="1002")


def test_unknown_type_rejected():
    store = memory.get_memory_store()
    try:
        store.record("bogus", {})
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_supplier_responsiveness_from_outcomes():
    store = memory.get_memory_store()
    # seeded ABC Steel outcome recovered 6 days -> responsiveness 1.0
    assert store.supplier_responsiveness("1001", "1000234") == 1.0
    # unknown vendor -> neutral 0.5
    assert store.supplier_responsiveness("9999") == 0.5
