"""Supplier delivery prediction (FR-SD-003/004)."""
from domain import prediction


def test_predict_from_chronic_history():
    gr = [{"delay_days": d} for d in (9, 12, 8, 8)]
    p = predict_delivery = prediction.predict_delivery(gr, "2026-10-30")
    assert p["sample_size"] == 4
    assert p["mean_overrun_days"] == 9.2 or round(p["mean_overrun_days"], 1) == 9.2
    assert p["on_time_probability"] == 0.0
    # predicted window starts no earlier than the confirmed date
    assert p["predicted_delivery_low"] >= "2026-10-30"
    assert p["predicted_delivery_high"] >= p["predicted_delivery_low"]


def test_predict_empty_history_is_on_time():
    p = prediction.predict_delivery([], "2026-10-30")
    assert p["sample_size"] == 0
    assert p["on_time_probability"] == 1.0
    assert p["predicted_delivery_low"] == "2026-10-30"


def test_predict_low_never_precedes_confirmed_date():
    gr = [{"delay_days": d} for d in (-2, -1, 0, 1)]
    p = prediction.predict_delivery(gr, "2026-11-05")
    assert p["predicted_delivery_low"] >= "2026-11-05"
