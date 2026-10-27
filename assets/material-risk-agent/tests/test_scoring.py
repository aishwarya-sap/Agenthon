"""Gap analysis + risk-band business rules (FSD §10)."""
from domain import data, scoring


def _assess(material):
    a = data.get_activities(material=material)[0]
    stock = data.get_stock(material)
    orders = data.get_orders(material=material)
    po = next((o for o in orders if o["doc_type"] == "PO"), None)
    gr = data.get_gr_history(po["vendor"], material) if po else []
    return scoring.assess_material(a, stock, orders, gr)


def test_net_available_excludes_late_po_and_qi_blocked():
    # 10 unrestricted; PO of 50 confirmed AFTER the required date must not count.
    orders = [{"doc_type": "PO", "qty": 50.0, "confirmed_delivery_date": "2026-10-30"}]
    net = scoring.net_available_qty(10.0, orders, "2026-10-16")
    assert net == 10.0


def test_net_available_counts_on_time_supply():
    orders = [{"doc_type": "PO", "qty": 40.0, "confirmed_delivery_date": "2026-10-15"}]
    assert scoring.net_available_qty(10.0, orders, "2026-10-16") == 50.0


def test_gap_quantity_and_delivery_gap():
    assert scoring.gap_quantity(50.0, 10.0) == 40.0
    assert scoring.gap_quantity(50.0, 60.0) == 0.0
    assert scoring.delivery_gap_days("2026-10-30", "2026-10-16") == 14
    assert scoring.delivery_gap_days("2026-10-10", "2026-10-16") == -6


def test_risk_bands_by_float():
    assert scoring.risk_band(-3, True) == scoring.CRITICAL
    assert scoring.risk_band(0, True) == scoring.CRITICAL
    assert scoring.risk_band(2, True) == scoring.HIGH
    assert scoring.risk_band(6, True) == scoring.MEDIUM
    assert scoring.risk_band(15, True) == scoring.LOW
    assert scoring.risk_band(-3, False) == scoring.NONE  # no gap -> no band


def test_chronic_late_and_on_time_rate():
    late = [{"delay_days": d} for d in (9, 12, 8, 8)]
    assert scoring.is_chronic_late(late) is True
    assert scoring.on_time_rate(late) == 0.0
    mixed = [{"delay_days": d} for d in (0, 1, -1, 2)]
    assert scoring.is_chronic_late(mixed) is False
    assert scoring.on_time_rate(mixed) == 0.5


def test_chronic_elevates_one_band_capped_at_critical():
    assert scoring.elevate_for_pattern(scoring.MEDIUM, True) == scoring.HIGH
    assert scoring.elevate_for_pattern(scoring.HIGH, True) == scoring.CRITICAL
    assert scoring.elevate_for_pattern(scoring.CRITICAL, True) == scoring.CRITICAL
    assert scoring.elevate_for_pattern(scoring.MEDIUM, False) == scoring.MEDIUM


def test_structural_steel_scenario_is_critical():
    r = _assess("1000234")
    assert r["risk_band"] == scoring.CRITICAL
    assert r["gap_qty"] == 40.0
    assert r["delivery_gap_days"] == 14
    assert r["critical_path"] is True
    assert r["chronic_late"] is True
    assert r["on_time_rate"] == 0.0


def test_copper_medium_elevated_to_high_by_chronic_supplier():
    r = _assess("1000890")
    assert r["base_band"] == scoring.MEDIUM
    assert r["chronic_late"] is True
    assert r["risk_band"] == scoring.HIGH


def test_clean_material_not_at_risk():
    r = _assess("1001234")
    assert r["at_risk"] is False
    assert r["risk_band"] == scoring.NONE
