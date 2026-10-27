"""Skills unit tests: critical_path_flag + recommend_next_action decision matrix."""
import pytest

from app.simulation import Scorecard
from app.skills import (ABSORB, ESCALATE, SOURCE_SWITCH, SourceReadiness,
                        critical_path_flag, recommend_next_action)

pytestmark = pytest.mark.unit


def test_critical_path_flag_boundaries():
    assert critical_path_flag(0) is True
    assert critical_path_flag(3) is True        # within buffer -> treat as critical (safe)
    assert critical_path_flag(6) is False       # beyond 5-day buffer -> watch list


def _sc(total, penalty=0.0, slip=8):
    return Scorecard("PO1", 48, slip, 100000.0, penalty, 32400.0, total, ["d"])


def _ready(**o):
    d = dict(alternative_available=True, alternative_contracted=True, alternative_lifnr="LIFNR-0010099",
             alternative_on_time_rate=0.94, has_pinfo_record=True, purchasing_blocked=False)
    d.update(o)
    return SourceReadiness(**d)


def test_high_risk_material_with_ready_source_switches():
    actions = recommend_next_action(worst_scorecard=_sc(192400.0, 24000.0), is_critical_path=True,
                                    supplier_delivery_risk_score=78, source_readiness=_ready(),
                                    repeat_offender_count=2, has_contract=True)
    assert actions[0].action == SOURCE_SWITCH
    assert actions[0].priority.endswith("URGENT")
    assert actions[0].confidence >= 0.8  # boosted by material + critical + repeat


def test_material_without_ready_source_escalates():
    actions = recommend_next_action(worst_scorecard=_sc(192400.0), is_critical_path=True,
                                    supplier_delivery_risk_score=78,
                                    source_readiness=_ready(alternative_available=False),
                                    repeat_offender_count=0, has_contract=True)
    assert actions[0].action == ESCALATE


def test_immaterial_exposure_absorbs():
    actions = recommend_next_action(worst_scorecard=_sc(1000.0, slip=0), is_critical_path=False,
                                    supplier_delivery_risk_score=10, source_readiness=_ready(),
                                    repeat_offender_count=0, has_contract=True)
    assert actions[0].action == ABSORB


def test_uncontracted_supplier_flagged_in_evidence():
    actions = recommend_next_action(worst_scorecard=_sc(192400.0), is_critical_path=True,
                                    supplier_delivery_risk_score=78, source_readiness=_ready(),
                                    repeat_offender_count=0, has_contract=False)
    assert any("uncontracted" in e.lower() for a in actions for e in a.evidence)


def test_blocked_supplier_not_offered_as_switch():
    actions = recommend_next_action(worst_scorecard=_sc(192400.0), is_critical_path=True,
                                    supplier_delivery_risk_score=78,
                                    source_readiness=_ready(purchasing_blocked=True),
                                    repeat_offender_count=0, has_contract=True)
    assert actions[0].action == ESCALATE  # switch not viable -> escalate first
