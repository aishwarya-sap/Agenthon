"""Schedule-consequence simulation engine."""
from domain.simulation import SimulationInput, simulate


def test_critical_path_gap_drives_cost_exposure():
    inp = SimulationInput(
        material="1000234", supply_gap_days=14, float_remaining_days=-3,
        successor_count=2, daily_idle_cost=12000.0, po_value=45000.0,
        supplier_responsiveness=0.6, alt_lead_time_days=10,
    )
    sc = simulate(inp)
    d = sc.as_dict()
    assert d["on_critical_path"] is True
    assert d["cascade_slip_days"] == 14
    assert d["cost_exposure"] == 14 * 12000.0
    assert d["disclaimer"]
    # three recovery options when an alternative source exists
    actions = {o["action"] for o in d["recovery_options"]}
    assert actions == {"expedite", "split_delivery", "alternative_source"}


def test_no_alternative_when_none_available():
    inp = SimulationInput(material="1000567", supply_gap_days=3, float_remaining_days=2,
                          po_value=9000.0, alt_lead_time_days=None)
    actions = {o["action"] for o in simulate(inp).as_dict()["recovery_options"]}
    assert "alternative_source" not in actions


def test_best_option_prefers_cheapest_that_restores_float():
    inp = SimulationInput(material="1000234", supply_gap_days=10, float_remaining_days=-1,
                          po_value=45000.0, alt_lead_time_days=10, supplier_responsiveness=0.5)
    best = simulate(inp).best_option()
    assert best is not None
    assert best.restores_float is True


def test_gap_within_float_stays_off_critical_path():
    inp = SimulationInput(material="x", supply_gap_days=2, float_remaining_days=6, po_value=1000.0)
    sc = simulate(inp)
    assert sc.on_critical_path is False
    assert sc.cascade_slip_days == 0
    assert sc.cost_exposure == 0.0
