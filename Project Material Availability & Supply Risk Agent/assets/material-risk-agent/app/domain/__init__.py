"""Deterministic business logic for the Project Material Risk agent.

All scoring, gap analysis, simulation, prediction, recommendation, memory and
HITL logic lives here as pure-stdlib Python — no LLM, no SAP SDK, no network.
The LLM orchestrates *which* tool to call; the arithmetic that drives the
business outcome is computed here and relayed verbatim ("LLM never computes").
"""
