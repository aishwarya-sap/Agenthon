"""Consequence simulation unit tests (deterministic math)."""
import pytest

from app import config
from app.simulation import (SimulationInput, is_material, needs_penalty_confirmation,
                            run_consequence_simulation, simulate_horizons)

pytestmark = pytest.mark.unit


def _base(**over):
    d = dict(po_number="PO1", material_category="STEEL", po_net_value_eur=180000.0,
             silence_duration_days=11, available_float_days=0, expected_lead_time_days=21,
             days_since_due=0, idle_teams=2, daily_team_cost_rate_eur=8500.0,
             milestone_at_risk=True, milestone_penalty_eur=40000.0)
    d.update(over)
    return SimulationInput(**d)


def test_schedule_slip_consumes_float():
    # float 6 absorbs most of the predicted delay
    card = run_consequence_simulation(_base(available_float_days=6, horizon_hours=24))
    low = run_consequence_simulation(_base(available_float_days=0, horizon_hours=24))
    assert card.schedule_slip_days < low.schedule_slip_days


def test_idle_cost_scales_with_teams_and_slip():
    card = run_consequence_simulation(_base(horizon_hours=24))
    assert card.idle_resource_cost_eur == card.schedule_slip_days * 2 * 8500.0


def test_penalty_prorated_by_breach_probability():
    card = run_consequence_simulation(_base(milestone_penalty_eur=40000.0, milestone_breach_probability=0.5,
                                            horizon_hours=24))
    assert card.penalty_exposure_eur == pytest.approx(20000.0)


def test_emergency_premium_uses_category_rate():
    card = run_consequence_simulation(_base(material_category="ELECTRICAL", horizon_hours=24))
    assert card.emergency_sourcing_premium_eur == pytest.approx(180000.0 * config.emergency_premium_pct("ELECTRICAL"))


def test_no_slip_when_float_exceeds_delay():
    card = run_consequence_simulation(_base(silence_duration_days=3, available_float_days=30, horizon_hours=24))
    assert card.schedule_slip_days == 0
    assert card.idle_resource_cost_eur == 0


def test_simulate_two_horizons_and_materiality():
    cards = simulate_horizons(_base())
    assert [c.horizon_hours for c in cards] == [24, 48]
    worst = max(cards, key=lambda c: c.total_consequence_exposure_eur)
    assert is_material(worst) is True
    assert needs_penalty_confirmation(worst) is True
