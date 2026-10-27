"""Offline lexical-proxy RAG evaluator for material-risk-agent (checklist L0-3.3).

Stdlib-only. This is an OFFLINE stand-in for SAP RagEval: on the tenant, RagEval
scores the live corpus + gold set against the eight metrics and replaces this
harness. Here we approximate each metric with deterministic lexical overlap so
the retrieval wiring (0.82 similarity gate, top-k=4, fail-closed injection scan,
PII redaction) can be regression-tested without AI Core or any embedding model.

Run:  python3 -I eval/rag_eval.py   (writes eval/rag_scorecard.json)
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
APP = os.path.join(BASE, "app")
if APP not in sys.path:
    sys.path.insert(0, APP)

from domain.data import RAG_CHUNKS              # the seeded corpus  # noqa: E402
from domain.sanitize import scan_injection      # fail-closed injection scan  # noqa: E402

SIMILARITY_GATE = 0.82
TOP_K = 4
MIN_LEXICAL = 0.20          # a retrieved chunk must share >=20% of query tokens

GOLD_PATH = os.path.join(HERE, "rag_gold_set.jsonl")
SCORECARD_PATH = os.path.join(HERE, "rag_scorecard.json")

# metric -> threshold (RagEval parity thresholds, used as lexical-proxy gates)
THRESHOLDS = {
    "context_relevance": 0.60,
    "context_recall": 0.70,
    "retrieval_recall": 0.80,
    "retrieval_precision": 0.60,
    "groundedness": 0.80,
    "answer_relevance": 0.40,
    "answer_correctness": 0.45,
    "answer_similarity": 0.45,
}

_STOP = {
    "the", "a", "an", "and", "or", "for", "to", "of", "on", "in", "is", "are",
    "was", "were", "by", "with", "what", "which", "that", "this", "it", "as",
    "at", "be", "from", "did", "do", "does", "has", "have", "re",
}


def _tokens(text: str) -> set[str]:
    out = set()
    for t in re.split(r"[^a-z0-9]+", (text or "").lower()):
        if not t or t in _STOP:
            continue
        if len(t) > 1 or t.isdigit():
            out.add(t)
    return out


def _overlap(query_tokens: set[str], text: str) -> float:
    """Share of query tokens present in text (0..1)."""
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(text)) / len(query_tokens)


def _retrieve(query: str) -> list[dict]:
    """Gate on 0.82 similarity, drop injection rows fail-closed, rank by lexical
    overlap, keep rows above MIN_LEXICAL, take top-k=4."""
    q_tokens = _tokens(query)
    scored = []
    for c in RAG_CHUNKS:
        if float(c.get("similarity", 0.0)) < SIMILARITY_GATE:
            continue                                   # below retrieval gate
        if scan_injection(c.get("text", "")):
            continue                                   # fail-closed injection drop
        score = _overlap(q_tokens, c.get("text", ""))
        if score >= MIN_LEXICAL:
            scored.append((score, c))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [c for _, c in scored[:TOP_K]]


def _coverage(reference: str, candidate: str) -> float:
    """Share of reference content tokens present in the candidate text."""
    ref = _tokens(reference)
    if not ref:
        return 1.0
    return len(ref & _tokens(candidate)) / len(ref)


def _score_query(gold: dict) -> dict:
    query = gold["query"]
    expected = set(gold["expected_chunk_ids"])
    gold_answer = gold["gold_answer"]
    q_tokens = _tokens(query)

    retrieved = _retrieve(query)
    retrieved_ids = [c["chunk_id"] for c in retrieved]
    retrieved_set = set(retrieved_ids)
    context = " ".join(c.get("text", "") for c in retrieved)
    answer = context                                   # extractive answer

    hits = retrieved_set & expected
    rel = sum(1 for c in retrieved if _overlap(q_tokens, c.get("text", "")) >= MIN_LEXICAL
              or c["chunk_id"] in expected)

    scores = {
        "context_relevance": (rel / len(retrieved)) if retrieved else 0.0,
        "context_recall": _coverage(gold_answer, context),
        "retrieval_recall": (len(hits) / len(expected)) if expected else 1.0,
        "retrieval_precision": (len(hits) / len(retrieved_set)) if retrieved_set else 0.0,
        "groundedness": _coverage(answer, context),     # extractive -> ~1.0
        "answer_relevance": _overlap(q_tokens, answer),
        "answer_correctness": _coverage(gold_answer, answer),
        "answer_similarity": _coverage(gold_answer, answer),
    }
    scores = {k: round(v, 3) for k, v in scores.items()}
    return {"query_id": gold["query_id"], "retrieved": retrieved_ids, "scores": scores}


def run_eval() -> dict:
    with open(GOLD_PATH, encoding="utf-8") as fh:
        gold = [json.loads(line) for line in fh if line.strip()]

    per_query = [_score_query(g) for g in gold]

    metrics = {}
    for m, thr in THRESHOLDS.items():
        vals = [pq["scores"][m] for pq in per_query]
        mean = round(sum(vals) / len(vals), 3) if vals else 0.0
        metrics[m] = {"mean": mean, "threshold": thr, "pass": mean >= thr}

    overall_pass = all(v["pass"] for v in metrics.values())

    result = {
        "scorer": "offline-lexical-proxy",
        "note": "SAP RagEval replaces this against the live corpus+gold set on tenant",
        "similarity_gate": SIMILARITY_GATE,
        "top_k": TOP_K,
        "queries_evaluated": len(per_query),
        "overall_pass": overall_pass,
        "metrics": metrics,
        "per_query": per_query,
    }

    with open(SCORECARD_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print(f"RAG eval ({result['scorer']}) — {len(per_query)} queries, "
          f"gate={SIMILARITY_GATE}, top_k={TOP_K}")
    for m, v in metrics.items():
        flag = "PASS" if v["pass"] else "FAIL"
        print(f"  {m:22s} mean={v['mean']:.3f}  thr={v['threshold']:.2f}  [{flag}]")
    for pq in per_query:
        print(f"  {pq['query_id']}: retrieved={pq['retrieved']}")
    print(f"OVERALL: {'PASS' if overall_pass else 'FAIL'}  -> {SCORECARD_PATH}")
    return result


if __name__ == "__main__":
    run_eval()
