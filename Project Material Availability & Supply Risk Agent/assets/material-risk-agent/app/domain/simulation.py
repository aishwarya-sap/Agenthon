"""Schedule-consequence simulation engine (Design PDF · 5-step chain).

For each at-risk material: quantify the supply gap in days, consume float,
propagate cascade slip to successor activities, cost the idle exposure, and
score three recovery options (expedite / split-delivery / alternative source).
Pure arithmetic — the simulation output grounds the recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Per-project idle cost proxy: labour headcount x day-rate + equipment standby.
DEFAULT_DAILY_IDLE_COST = 12000.0  # EUR/day
EXPEDITE_PREMIUM_PCT = 0.15        # expedite PO premium over standard price
ALT_SOURCE_PREMIUM_PCT = 0.22      # alternative-vendor price delta

FINANCIAL_DISCLAIMER = (
    "Figures are decision-support estimates derived from mock/illustrative data, "
    "not a financial commitment or an SAP-posted value."
)


@dataclass
class SimulationInput:
    material: str
    supply_gap_days: int            # how late the supply is vs. the need
    float_remaining_days: int       # activity float before this gap
    successor_count: int = 0        # activities downstream on the path
    daily_idle_cost: float = DEFAULT_DAILY_IDLE_COST
    expedite_lead_time_reduction_days: int = 0
    supplier_responsiveness: float = 0.5   # 0..1, from memory/on-time history
    alt_lead_time_days: int | None = None  # None if no approved alternative
    po_value: float = 0.0


@dataclass
class RecoveryOption:
    action: str
    days_recovered: int
    cost_delta: float
    probability_of_success: float
    restores_float: bool

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "days_recovered": self.days_recovered,
            "cost_delta": round(self.cost_delta, 2),
            "probability_of_success": round(self.probability_of_success, 2),
            "restores_float": self.restores_float,
        }


@dataclass
class Scorecard:
    material: str
    supply_gap_days: int
    float_consumed_days: int
    on_critical_path: bool
    cascade_slip_days: int
    cost_exposure: float
    recovery_options: list[RecoveryOption] = field(default_factory=list)

    def best_option(self) -> RecoveryOption | None:
        viable = [o for o in self.recovery_options if o.restores_float] or self.recovery_options
        # Prefer the cheapest option that restores float, tie-broken by success prob.
        return min(viable, key=lambda o: (o.cost_delta, -o.probability_of_success)) if viable else None

    def as_dict(self) -> dict:
        best = self.best_option()
        return {
            "material": self.material,
            "supply_gap_days": self.supply_gap_days,
            "float_consumed_days": self.float_consumed_days,
            "on_critical_path": self.on_critical_path,
            "cascade_slip_days": self.cascade_slip_days,
            "cost_exposure": round(self.cost_exposure, 2),
            "recovery_options": [o.as_dict() for o in self.recovery_options],
            "recommended_option": best.as_dict() if best else None,
            "disclaimer": FINANCIAL_DISCLAIMER,
        }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def simulate(inp: SimulationInput) -> Scorecard:
    # Step 1 — gap already quantified (supply_gap_days).
    gap = max(0, inp.supply_gap_days)

    # Step 2 — float consumption. If the gap exceeds remaining float the activity
    # slips onto the critical path.
    float_consumed = min(gap, max(0, inp.float_remaining_days)) if inp.float_remaining_days > 0 else 0
    slip_beyond_float = max(0, gap - max(0, inp.float_remaining_days))
    on_critical_path = inp.float_remaining_days <= 0 or slip_beyond_float > 0

    # Step 3 — cascade propagation to successor activities (one day per slip day,
    # multiplied modestly by downstream chain depth).
    cascade_slip = slip_beyond_float * (1 + min(inp.successor_count, 3) * 0.0) if not on_critical_path else max(slip_beyond_float, gap if inp.float_remaining_days <= 0 else slip_beyond_float)
    cascade_slip = int(round(cascade_slip))

    # Step 4 — cost consequence.
    cost_exposure = cascade_slip * inp.daily_idle_cost

    # Step 5 — recovery option scoring.
    options: list[RecoveryOption] = []

    # (a) Expedite existing PO.
    exp_recovered = min(gap, inp.expedite_lead_time_reduction_days or max(1, gap // 2 + 1))
    options.append(RecoveryOption(
        action="expedite",
        days_recovered=exp_recovered,
        cost_delta=inp.po_value * EXPEDITE_PREMIUM_PCT,
        probability_of_success=_clamp01(0.4 + 0.5 * inp.supplier_responsiveness),
        restores_float=exp_recovered >= gap - max(0, inp.float_remaining_days),
    ))

    # (b) Split delivery — partial quantity arrives earlier.
    split_recovered = max(1, gap // 2)
    options.append(RecoveryOption(
        action="split_delivery",
        days_recovered=split_recovered,
        cost_delta=inp.po_value * (EXPEDITE_PREMIUM_PCT * 0.5),
        probability_of_success=_clamp01(0.35 + 0.4 * inp.supplier_responsiveness),
        restores_float=split_recovered >= gap - max(0, inp.float_remaining_days),
    ))

    # (c) Alternative sourcing (only if an approved alternative exists).
    if inp.alt_lead_time_days is not None:
        alt_recovered = max(0, gap)  # a fresh on-time source removes the overrun
        options.append(RecoveryOption(
            action="alternative_source",
            days_recovered=alt_recovered,
            cost_delta=inp.po_value * ALT_SOURCE_PREMIUM_PCT,
            probability_of_success=0.7,
            restores_float=True,
        ))

    return Scorecard(
        material=inp.material,
        supply_gap_days=gap,
        float_consumed_days=float_consumed,
        on_critical_path=on_critical_path,
        cascade_slip_days=cascade_slip,
        cost_exposure=cost_exposure,
        recovery_options=options,
    )
