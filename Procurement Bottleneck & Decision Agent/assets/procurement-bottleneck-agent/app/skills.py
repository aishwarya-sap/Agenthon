"""Deterministic Skills — bounded functions with no LLM reasoning.

Three skills from the design, kept deterministic so they are cheap, repeatable,
and fully unit-testable:

* ``critical_path_flag``        — AFVV network-float evaluation.
* ``run_consequence_simulation``— the four-dimension model (delegates to simulation.py).
* ``recommend_next_action``     — the configurable decision matrix → ranked actions.

The decision matrix thresholds live in ``config`` and are, in production,
externalized to SAP Build Process Automation — Business Rules (editable by the
Procurement CoE without a code deployment).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from . import config
from .simulation import Scorecard, SimulationInput, simulate_horizons

# Action codes (design: escalate / source switch / absorb).
ESCALATE = "escalate"
SOURCE_SWITCH = "source_switch"
ABSORB = "absorb"

PRIORITY_URGENT = "🔴 URGENT"
PRIORITY_HIGH = "🟡 HIGH"
PRIORITY_RECOMMENDED = "🟢 RECOMMENDED"


def critical_path_flag(available_float_days: int) -> bool:
    """TRUE when the dependent WBS activity is on the critical path.

    float == 0 → critical (TRUE). float greater than the configurable buffer →
    FALSE (watch list). Values in between are treated as critical to stay safe.
    """
    if available_float_days <= 0:
        return True
    if available_float_days > config.CRITICAL_PATH_FLOAT_BUFFER_DAYS:
        return False
    return True


def run_consequence_simulation(inp: SimulationInput) -> list[Scorecard]:
    """Skill wrapper — run the 24h/48h consequence simulation."""
    return simulate_horizons(inp)


@dataclass
class SourceReadiness:
    alternative_available: bool
    alternative_contracted: bool          # negotiated contract exists (preferred over spot)
    alternative_lifnr: str = ""
    alternative_on_time_rate: float = 0.0  # 0..1
    has_pinfo_record: bool = True
    purchasing_blocked: bool = False       # LFM1.SPERM / LFA1.SPERR


@dataclass
class RankedAction:
    action: str
    priority: str
    confidence: float          # 0..1
    responsible_area: str
    rationale: str
    evidence: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def recommend_next_action(
    *,
    worst_scorecard: Scorecard,
    is_critical_path: bool,
    supplier_delivery_risk_score: int,   # 0..100
    source_readiness: SourceReadiness,
    repeat_offender_count: int,
    has_contract: bool,
) -> list[RankedAction]:
    """Apply the decision matrix (exposure × source readiness × supplier risk ×
    memory pattern) and return a ranked action set with confidence and evidence.

    Advisory-only: a ``source_switch`` is a *recommendation* for a human to execute
    in SAP — the agent never writes the source list or creates a replacement PO.
    """
    exposure = worst_scorecard.total_consequence_exposure_eur
    material = exposure >= config.MATERIALITY_EXPOSURE_EUR
    high_risk = supplier_delivery_risk_score >= config.VENDOR_RISK_HIGH

    evidence = [
        f"total consequence exposure €{exposure:,.0f} ({worst_scorecard.horizon_hours}h horizon)",
        f"schedule slip {worst_scorecard.schedule_slip_days}d",
        f"supplier delivery risk {supplier_delivery_risk_score}/100",
        f"critical path: {'yes' if is_critical_path else 'no'}",
    ]
    if repeat_offender_count > 0:
        evidence.append(f"repeat silence pattern: {repeat_offender_count} prior event(s)")

    actions: list[RankedAction] = []

    # Confidence rises with materiality, critical-path status, and repeat patterns.
    base_conf = 0.55
    if material:
        base_conf += 0.15
    if is_critical_path:
        base_conf += 0.10
    if repeat_offender_count > 0:
        base_conf += min(0.10, 0.03 * repeat_offender_count)
    base_conf = round(min(base_conf, 0.95), 2)

    switch_viable = (
        source_readiness.alternative_available
        and source_readiness.has_pinfo_record
        and not source_readiness.purchasing_blocked
    )

    if material and high_risk and switch_viable:
        # Prefer a contracted alternative; rank source switch first.
        prio = PRIORITY_URGENT if is_critical_path else PRIORITY_HIGH
        contracted = " (contracted)" if source_readiness.alternative_contracted else " (uncontracted — flag spend)"
        actions.append(RankedAction(
            SOURCE_SWITCH, prio, base_conf, "Purchasing HoD",
            f"High-risk supplier on a material exposure of €{exposure:,.0f}; approved alternative "
            f"{source_readiness.alternative_lifnr}{contracted} available "
            f"({source_readiness.alternative_on_time_rate:.0%} on-time).",
            evidence + [f"alternative {source_readiness.alternative_lifnr}{contracted}"],
        ))
        actions.append(RankedAction(
            ESCALATE, PRIORITY_HIGH, round(base_conf - 0.1, 2), "Purchasing HoD → Supplier / PMs",
            "Escalate to the supplier with the consequence summary in parallel while the source "
            "switch is prepared.", evidence,
        ))
    elif material:
        prio = PRIORITY_URGENT if is_critical_path else PRIORITY_HIGH
        actions.append(RankedAction(
            ESCALATE, prio, base_conf, "Purchasing HoD → Supplier / Project Managers",
            f"Material exposure (€{exposure:,.0f}) with no ready alternative source; escalate to the "
            f"supplier and notify affected project managers with the quantified cost of inaction.",
            evidence + ([] if switch_viable else ["no eligible alternative source ready"]),
        ))
        if switch_viable:
            actions.append(RankedAction(
                SOURCE_SWITCH, PRIORITY_HIGH, round(base_conf - 0.15, 2), "Purchasing HoD",
                "A source switch is a fallback if the supplier does not respond to escalation.",
                evidence,
            ))
    else:
        actions.append(RankedAction(
            ABSORB, PRIORITY_RECOMMENDED, base_conf, "Purchasing HoD (watch list)",
            f"Exposure (€{exposure:,.0f}) is below the materiality threshold "
            f"(€{config.MATERIALITY_EXPOSURE_EUR:,.0f}); monitor and re-evaluate on the next scan.",
            evidence,
        ))

    if not has_contract:
        for a in actions:
            a.evidence.append("⚠ supplier has no contract — uncontracted spend, no penalty protection")

    return actions
