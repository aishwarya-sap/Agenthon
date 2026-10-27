"""RAG evaluation scorecard gate (checklist 3.3) — offline lexical proxy.

The authoritative score comes from SAP RagEval against the live corpus + gold
set on the tenant; this asserts the offline proxy pipeline (similarity gate,
injection drop, 8 metrics) stays green so regressions surface in CI.
"""
import sys
from pathlib import Path

_EVAL = Path(__file__).resolve().parent.parent / "eval"
if str(_EVAL) not in sys.path:
    sys.path.insert(0, str(_EVAL))

import rag_eval  # noqa: E402


def test_rag_scorecard_passes():
    result = rag_eval.run_eval()
    assert result["overall_pass"] is True
    assert result["similarity_gate"] == 0.82
    assert result["top_k"] == 4
    assert result["queries_evaluated"] >= 2
    for name, m in result["metrics"].items():
        assert m["pass"], f"metric {name} below threshold: {m}"
