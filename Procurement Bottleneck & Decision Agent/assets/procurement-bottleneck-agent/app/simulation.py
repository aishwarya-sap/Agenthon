"""Four-dimension consequence simulation (deterministic skill core).

Quantifies the downstream business consequence of an unconfirmed critical-path
purchase order. Pure Python — no LLM, no network — so it is deterministic,
cheap, and fully unit-testable. Mirrors the design's `run_consequence_simulation`
skill and the customer-ontology exposure formula:

    consequence_exposure ≈ schedule_slip_days × daily_idle_resource_cost
                            + KONP penalty (KBETR) prorated to milestone breach probability

Inputs are drawn from EKPO.EINDT / EKPO.NETPR, AFVV float, MLST milestone dates +
FRGKZ, KONP.KBETR, the confirmed supplier silence duration, and the project
resource calendar (daily team cost rates from CATS/HR-PS). Every figure is an
estimate; the agent appends the standard financial disclaimer downstream.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from . import config


@dataclass
class SimulationInput:
    po_number: str
    material_category: str
    po_net_value_eur: float
    silence_duration_days: int
    available_float_days: int           # AFVV: EFAVD - SSAVD for the dependent activity
    expected_lead_time_days: int        # PInfoRecord PLIFZ
    days_since_due: int                 # today - EKPO.EINDT (negative = not yet due)
    idle_teams: int                     # resource teams blocked downstream
    daily_team_cost_rate_eur: float     # CATS/project resource calendar
    milestone_at_risk: bool             # MLST milestone release blocked by this material
    milestone_penalty_eur: float        # KONP.KBETR for the milestone clause
    milestone_breach_probability: float = 0.6  # prorating factor for the penalty
    horizon_hours: int = 24


@dataclass
class Scorecard:
    po_number: str
    horizon_hours: int
    schedule_slip_days: int
    idle_resource_cost_eur: float
    penalty_exposure_eur: float
    emergency_sourcing_premium_eur: float
    total_consequence_exposure_eur: float
    drivers: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _predicted_delay_days(inp: SimulationInput) -> int:
    """How many days late the material is predicted to arrive if the supplier stays
    silent across the horizon. Grounded in observed silence + overdue + the horizon."""
    horizon_days = max(1, inp.horizon_hours // 24)
    # Delay accrues from how overdue it already is plus the look-ahead horizon,
    # with a floor from the silence itself (a supplier silent for N days is unlikely
    # to deliver on time).
    base = max(inp.days_since_due, 0) + horizon_days
    silence_signal = max(inp.silence_duration_days - config.SILENCE_TOLERANCE_DAYS, 0)
    return max(base, silence_signal)


def run_consequence_simulation(inp: SimulationInput) -> Scorecard:
    """Compute the four-dimension consequence scorecard for one PO at one horizon."""
    drivers: list[str] = []

    # 1) Schedule slip — delay beyond the activity's available float.
    predicted_delay = _predicted_delay_days(inp)
    schedule_slip_days = max(predicted_delay - max(inp.available_float_days, 0), 0)
    if schedule_slip_days > 0:
        drivers.append(
            f"{predicted_delay}d predicted delivery delay vs {inp.available_float_days}d float "
            f"→ {schedule_slip_days}d schedule slip"
        )

    # 2) Idle resource cost — slip days × teams × daily rate.
    idle_resource_cost = schedule_slip_days * max(inp.idle_teams, 0) * max(inp.daily_team_cost_rate_eur, 0.0)
    if idle_resource_cost > 0:
        drivers.append(
            f"{inp.idle_teams} team(s) idled × {schedule_slip_days}d × "
            f"€{inp.daily_team_cost_rate_eur:,.0f}/day"
        )

    # 3) Milestone payment risk — prorated penalty if the milestone is blocked.
    penalty_exposure = 0.0
    if inp.milestone_at_risk and schedule_slip_days > 0:
        prob = min(max(inp.milestone_breach_probability, 0.0), 1.0)
        penalty_exposure = round(inp.milestone_penalty_eur * prob, 2)
        if penalty_exposure > 0:
            drivers.append(
                f"milestone penalty €{inp.milestone_penalty_eur:,.0f} × "
                f"{prob:.0%} breach probability"
            )

    # 4) Emergency sourcing premium — spot-market uplift on the PO value.
    premium_pct = config.emergency_premium_pct(inp.material_category)
    emergency_premium = round(max(inp.po_net_value_eur, 0.0) * premium_pct, 2)
    if emergency_premium > 0:
        drivers.append(
            f"emergency re-source premium {premium_pct:.0%} of €{inp.po_net_value_eur:,.0f}"
        )

    total = round(idle_resource_cost + penalty_exposure + emergency_premium, 2)

    return Scorecard(
        po_number=inp.po_number,
        horizon_hours=inp.horizon_hours,
        schedule_slip_days=schedule_slip_days,
        idle_resource_cost_eur=round(idle_resource_cost, 2),
        penalty_exposure_eur=penalty_exposure,
        emergency_sourcing_premium_eur=emergency_premium,
        total_consequence_exposure_eur=total,
        drivers=drivers,
    )


def simulate_horizons(inp: SimulationInput, horizons_hours: tuple[int, ...] = (24, 48)) -> list[Scorecard]:
    """Run the simulation across horizons (default 24h and 48h) to show the live
    cost of inaction, as the design specifies."""
    cards = []
    for h in horizons_hours:
        card_input = SimulationInput(**{**inp.__dict__, "horizon_hours": h})
        cards.append(run_consequence_simulation(card_input))
    return cards


def is_material(scorecard: Scorecard) -> bool:
    """True when exposure crosses the configured materiality threshold."""
    return scorecard.total_consequence_exposure_eur >= config.MATERIALITY_EXPOSURE_EUR


def needs_penalty_confirmation(scorecard: Scorecard) -> bool:
    """True when penalty exposure requires the dedicated HoD confirmation gate."""
    return scorecard.penalty_exposure_eur >= config.PENALTY_EXPOSURE_HITL_EUR
