"""Evaluation-dataset driver (L0-2.1) + RAG scorecard gate (L0-3.3).

Loads eval/eval_dataset.jsonl and drives each record through the appropriate layer
(decision skill / critical-path skill / full agent), asserting the documented
expectation. Also runs the offline RAG scorecard runner and asserts every metric
meets its threshold. This is the executable form of the submitted evaluation
dataset — it keeps the dataset honest (any record whose expectation regresses
fails CI) and produces eval/rag_scorecard.json as the archived evidence artefact.
"""
import json
import os

import pytest

from app.memory import get_memory_store
from app.simulation import Scorecard
from app.skills import (ABSORB, ESCALATE, SOURCE_SWITCH, SourceReadiness,
                        critical_path_flag, recommend_next_action)

pytestmark = pytest.mark.eval

_HERE = os.path.dirname(__file__)
_DATASET = os.path.join(os.path.dirname(_HERE), "eval", "eval_dataset.jsonl")


def _load_dataset():
    rows = []
    with open(_DATASET, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


DATASET = _load_dataset()


def test_dataset_is_non_empty_and_well_formed():
    assert len(DATASET) >= 15
    categories = {r["category"] for r in DATASET}
    assert {"golden", "edge", "adversarial", "multilingual"} <= categories
    for r in DATASET:
        assert r["id"] and r["layer"] in {"decision", "skill", "agent", "rag"}
        assert "expect" in r and "input" in r


def _mk_scorecard(inp):
    return Scorecard("PO-EVAL", 48, inp.get("slip_days", 8), 100000.0,
                     inp.get("penalty_eur", 0.0), 32400.0, inp["total_exposure_eur"], ["d"])


def _run_decision(inp):
    readiness = SourceReadiness(
        alternative_available=inp["alt_available"],
        alternative_contracted=inp.get("alt_contracted", False),
        alternative_lifnr="LIFNR-0010099",
        alternative_on_time_rate=0.94,
        has_pinfo_record=inp.get("has_pinfo_record", True),
        purchasing_blocked=inp.get("purchasing_blocked", False),
    )
    return recommend_next_action(
        worst_scorecard=_mk_scorecard(inp),
        is_critical_path=inp["is_critical_path"],
        supplier_delivery_risk_score=inp["supplier_delivery_risk_score"],
        source_readiness=readiness,
        repeat_offender_count=inp.get("repeat_offender_count", 0),
        has_contract=inp.get("has_contract", True),
    )


@pytest.mark.parametrize("rec", [r for r in DATASET if r["layer"] == "decision"],
                         ids=[r["id"] for r in DATASET if r["layer"] == "decision"])
def test_decision_layer_records(rec):
    actions = _run_decision(rec["input"])
    exp = rec["expect"]
    if "action" in exp:
        assert actions[0].action == exp["action"]
    if "priority_contains" in exp:
        assert exp["priority_contains"] in actions[0].priority
    if "min_confidence" in exp:
        assert actions[0].confidence >= exp["min_confidence"]
    if "evidence_contains" in exp:
        assert any(exp["evidence_contains"] in e.lower() for a in actions for e in a.evidence)


@pytest.mark.parametrize("rec", [r for r in DATASET if r["layer"] == "skill"],
                         ids=[r["id"] for r in DATASET if r["layer"] == "skill"])
def test_skill_layer_records(rec):
    assert critical_path_flag(rec["input"]["available_float_days"]) is rec["expect"]["critical_path"]


@pytest.mark.parametrize("rec", [r for r in DATASET if r["layer"] == "agent"],
                         ids=[r["id"] for r in DATASET if r["layer"] == "agent"])
async def test_agent_layer_records(rec, agent):
    inp = rec["input"]
    if "prompt_repeat" in inp:
        prompt = inp["prompt_repeat"]["text"] * inp["prompt_repeat"]["times"]
    else:
        prompt = inp["prompt"]
    res = await agent.handle(prompt, context_id=f"eval-{rec['id']}")
    exp = rec["expect"]
    if exp.get("completes"):
        assert res.get("content")
    if exp.get("report_produced"):
        assert "Procurement Blockers" in res["content"]
    if "action" in exp:
        assert res.get("action") == exp["action"]
    if "pending" in exp:
        assert res["pending"] is exp["pending"]
    if exp.get("no_write"):
        assert len(get_memory_store().all()) == 0
    if exp.get("no_sap_write_claim"):
        assert "BAPI_PO_CREATE1" not in res["content"]


def test_rag_scorecard_meets_thresholds():
    from eval.rag_eval import evaluate
    result = evaluate()
    assert result["queries_evaluated"] >= 2
    failed = [m for m, v in result["metrics"].items() if not v["pass"]]
    assert not failed, f"RAG metrics below threshold: {failed}"
    assert result["overall_pass"] is True
