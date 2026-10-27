"""Business-data safety gate (checklist 5.6 indirect prompt injection + PII).

RAG content ingests supplier email threads that may carry (a) indirect prompt
injection and (b) personal contact details. Before retrieved rows reach the
model we scan fail-closed for injection and redact PII. This complements the
template's tool-result wrapper (prompt_injection_detector.wrap_tool), giving an
explicit, testable control at the retrieval boundary.
"""
from __future__ import annotations

import re

# Indirect-injection patterns (fail-closed: any match removes the row).
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"your\s+new\s+role\s+is", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|above)", re.I),
    re.compile(r"\bnew\s+instructions?\b", re.I),
    re.compile(r"approve\s+(every|all)\b", re.I),
    re.compile(r"without\s+human\s+review", re.I),
    re.compile(r"\bexfiltrat", re.I),
    re.compile(r"reveal\s+(the\s+)?(system\s+)?prompt", re.I),
]

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def scan_injection(text: str) -> bool:
    """True if the text contains an indirect-injection attempt."""
    return any(p.search(text or "") for p in _INJECTION_PATTERNS)


def redact_pii(text: str) -> str:
    """Keep the email domain, drop the local part; mask phone numbers."""
    t = _EMAIL.sub(lambda m: f"<email@{m.group(1)}>", text or "")
    t = _PHONE.sub("<phone-redacted>", t)
    return t


def sanitize_chunks(chunks: list[dict], similarity_gate: float = 0.82) -> tuple[list[dict], list[dict]]:
    """Apply the similarity gate, drop injection rows (fail-closed), redact PII.

    Returns (clean_chunks, flagged_chunks). Flagged rows never reach the model.
    """
    clean: list[dict] = []
    flagged: list[dict] = []
    for c in chunks:
        if float(c.get("similarity", 0.0)) < similarity_gate:
            continue  # below the retrieval gate — silently dropped
        if scan_injection(c.get("text", "")):
            flagged.append({**c, "_injection_matched": True})
            continue
        clean.append({**c, "text": redact_pii(c.get("text", ""))})
    return clean, flagged
