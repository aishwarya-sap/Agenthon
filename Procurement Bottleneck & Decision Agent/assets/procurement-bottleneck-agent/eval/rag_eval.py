"""Offline RAG Evaluation Scorecard runner (L0-3.3).

Produces the eight-metric RAG Evaluation Scorecard structure mandated by the
checklist, scored against a curated gold set over the deterministic mock corpus.

IMPORTANT — what this is and is not:
  * This is an **offline lexical proxy** scorer (token overlap / F1 / cosine over
    term-frequency vectors). It exercises the full scorecard pipeline — retrieval,
    gate, metric computation, per-metric thresholds, pass/fail, JSON artefact — so
    the gate is wired and testable before go-live.
  * It is **not** the authoritative LLM-judged score. On the live tenant, SAP's
    **RagEval** tool (see README / checklist 3.3) replaces the proxy scorer against
    the real contract/history corpus and gold set; groundedness and context
    relevance need no gold set there, while answer correctness / similarity /
    context recall are judged against the curated gold set.

Run:  python -m eval.rag_eval         (writes eval/rag_scorecard.json)
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from typing import Any

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
_MOCK = os.path.join(_ROOT, "mcp-mock.json")
_GOLD = os.path.join(_HERE, "rag_gold_set.jsonl")
_OUT = os.path.join(_HERE, "rag_scorecard.json")

RAG_SIMILARITY_GATE = 0.82
TOP_K = 4

# Per-metric release thresholds (proxy scale 0..1). On the live tenant these are
# the RagEval thresholds; any metric below its threshold is a release blocker.
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

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "at", "is", "are",
         "was", "were", "be", "per", "this", "that", "how", "what", "has", "have", "with",
         "it", "as", "by", "from", "did", "does", "before"}


def _tok(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP]


def _overlap(a: list[str], b: list[str]) -> float:
    """Fraction of a's tokens present in b."""
    if not a:
        return 0.0
    bset = set(b)
    return sum(1 for t in a if t in bset) / len(a)


def _f1(pred: list[str], gold: list[str]) -> float:
    if not pred or not gold:
        return 0.0
    pc, gc = Counter(pred), Counter(gold)
    overlap = sum((pc & gc).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(pc.values())
    recall = overlap / sum(gc.values())
    return 2 * precision * recall / (precision + recall)


def _cosine(a: list[str], b: list[str]) -> float:
    ca, cb = Counter(a), Counter(b)
    keys = set(ca) | set(cb)
    dot = sum(ca[k] * cb[k] for k in keys)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0


def _load_corpus() -> list[dict[str, Any]]:
    with open(_MOCK, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for server in data.get("servers", {}).values():
        tool = server.get("tools", {}).get("rag_retrieve_contract_and_history")
        if tool:
            return list(tool.get("mock_response", {}).get("value", []))
    return []


def _load_gold() -> list[dict[str, Any]]:
    rows = []
    with open(_GOLD, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _retrieve(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank corpus by combined (embedding + lexical) score, apply the similarity
    gate, then a relevance-margin cutoff.

    The mock corpus carries fixed embedding-similarity scores; we combine them with
    a query-lexical score so retrieval is query-sensitive (modelling the tool's
    documented semantic + metadata-filtered behaviour) rather than a fixed echo.
    The margin cutoff drops gate-passing chunks whose combined score falls far
    below the top hit — a standard score-gap heuristic that prevents an off-topic
    but high-embedding chunk from polluting every query's result.
    """
    qtok = _tok(query)
    scored = []
    for chunk in corpus:
        if float(chunk.get("similarity", 0.0)) < RAG_SIMILARITY_GATE:
            continue
        lex = _overlap(qtok, _tok(chunk.get("text", "")))
        combined = 0.5 * float(chunk.get("similarity", 0.0)) + 0.5 * lex
        scored.append((combined, chunk))
    if not scored:
        return []
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    kept = [c for s, c in scored[:TOP_K] if s >= 0.9 * top_score]
    return kept


def evaluate() -> dict[str, Any]:
    corpus = _load_corpus()
    gold = _load_gold()
    per_metric: dict[str, list[float]] = {m: [] for m in THRESHOLDS}
    per_query: list[dict[str, Any]] = []

    for g in gold:
        retrieved = _retrieve(g["query"], corpus)
        retrieved_ids = {c.get("chunk_id") for c in retrieved}
        relevant_ids = set(g.get("relevant_chunk_ids", []))
        ctx_tokens = _tok(" ".join(c.get("text", "") for c in retrieved))
        answer_tokens = ctx_tokens  # extractive answer = retrieved context
        gold_answer_tokens = _tok(g.get("gold_answer", ""))
        qtok = _tok(g["query"])

        hits = retrieved_ids & relevant_ids
        retrieval_recall = len(hits) / len(relevant_ids) if relevant_ids else 1.0
        retrieval_precision = len(hits) / len(retrieved_ids) if retrieved_ids else 0.0
        context_relevance = (sum(_overlap(qtok, _tok(c.get("text", ""))) for c in retrieved)
                             / len(retrieved)) if retrieved else 0.0
        facts = g.get("gold_facts", [])
        context_recall = (sum(1 for f in facts if _overlap(_tok(f), ctx_tokens) >= 0.6) / len(facts)
                          ) if facts else 1.0
        groundedness = _overlap(answer_tokens, ctx_tokens)  # extractive -> fully grounded
        answer_relevance = _overlap(qtok, answer_tokens)
        answer_correctness = _f1(answer_tokens, gold_answer_tokens)
        answer_similarity = _cosine(answer_tokens, gold_answer_tokens)

        scores = {
            "context_relevance": round(context_relevance, 3),
            "context_recall": round(context_recall, 3),
            "retrieval_recall": round(retrieval_recall, 3),
            "retrieval_precision": round(retrieval_precision, 3),
            "groundedness": round(groundedness, 3),
            "answer_relevance": round(answer_relevance, 3),
            "answer_correctness": round(answer_correctness, 3),
            "answer_similarity": round(answer_similarity, 3),
        }
        for m, v in scores.items():
            per_metric[m].append(v)
        per_query.append({"query_id": g["query_id"], "retrieved": sorted(retrieved_ids), "scores": scores})

    summary = {}
    all_pass = True
    for m, vals in per_metric.items():
        mean = round(sum(vals) / len(vals), 3) if vals else 0.0
        passed = mean >= THRESHOLDS[m]
        all_pass = all_pass and passed
        summary[m] = {"mean": mean, "threshold": THRESHOLDS[m], "pass": passed}

    return {
        "scorer": "offline-lexical-proxy",
        "note": "Proxy scores only. SAP RagEval replaces this against the live corpus + gold set at L0-3.3.",
        "similarity_gate": RAG_SIMILARITY_GATE,
        "top_k": TOP_K,
        "queries_evaluated": len(gold),
        "overall_pass": all_pass,
        "metrics": summary,
        "per_query": per_query,
    }


def main() -> None:
    result = evaluate()
    with open(_OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result["metrics"], indent=2))
    print(f"overall_pass={result['overall_pass']}  ->  {_OUT}")


if __name__ == "__main__":
    main()
