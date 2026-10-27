"""Supplier delivery prediction (FR-SD-003/004).

Statistical, history-based (no ML model, no live feed): mean overrun + spread
from the last N goods receipts, projected onto the current confirmed date.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, pstdev


def _d(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def predict_delivery(gr_history: list[dict], confirmed_delivery_date) -> dict:
    """Predict delay range + on-time probability for the current PO.

    Uses the delay distribution of past deliveries (actual - promised). The
    predicted window is confirmed_date + [mean-std, mean+std], clamped so the
    low end never precedes the confirmed date.
    """
    delays = [int(g.get("delay_days", 0)) for g in gr_history]
    if not delays:
        return {
            "mean_overrun_days": 0,
            "delay_low_days": 0,
            "delay_high_days": 0,
            "on_time_probability": 1.0,
            "predicted_delivery_low": str(_d(confirmed_delivery_date)) if confirmed_delivery_date else None,
            "predicted_delivery_high": str(_d(confirmed_delivery_date)) if confirmed_delivery_date else None,
            "sample_size": 0,
        }

    m = mean(delays)
    spread = pstdev(delays) if len(delays) > 1 else 0.0
    low = max(0, round(m - spread))
    high = round(m + spread)
    on_time = sum(1 for d in delays if d <= 0) / len(delays)

    cd = _d(confirmed_delivery_date) if confirmed_delivery_date else None
    pred_low = str(cd + timedelta(days=low)) if cd else None
    pred_high = str(cd + timedelta(days=high)) if cd else None

    return {
        "mean_overrun_days": round(m, 1),
        "delay_low_days": low,
        "delay_high_days": high,
        "on_time_probability": round(on_time, 2),
        "predicted_delivery_low": pred_low,
        "predicted_delivery_high": pred_high,
        "sample_size": len(delays),
    }
