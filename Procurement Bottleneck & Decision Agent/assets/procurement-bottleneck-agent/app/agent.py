"""Agent core — orchestration + consequence reasoning for the Procurement
Bottleneck & Decision Agent.

Design classification (L0-8): user/event/scheduled triggers; an **orchestrated
graph** with a deterministic tool/skill core and two LLM touch-points (intent
framing + final natural-language verdict polish). The quantitative work
(simulation, recommendation) is deterministic and cost-bounded. All SAP access is
read-only (advisory). Business milestones are instrumented.

# Milestones emitted at runtime (static-check grep: M1.achieved … M9.achieved /
# M1.missed … M9.missed) — see app/observability.py:MILESTONES.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from . import config
from .hitl import (ApprovalStore, PendingApproval, evaluate_checkpoints, extract_lifnr,
                   get_approval_store, is_approval, is_rejection)
from .mcp_tools import get_mcp_tools
from .memory import DecisionRecord, get_memory_store
from .observability import get_logger, log_event, log_milestone, tracer
from .resilience import CircuitBreaker, ToolError, call_tool_safely
from .sanitize import sanitize_rows
from .simulation import Scorecard, SimulationInput
from .skills import SourceReadiness, critical_path_flag, recommend_next_action, run_consequence_simulation

logger = get_logger()

# --- Mandatory decorators (exactly three; @agent_config = temperature only) ---
try:
    from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
except Exception:  # offline/local fallback — real package is present in the SAP runtime
    def agent_model(*_a, **_k):
        def _wrap(fn):
            return fn
        return _wrap

    def agent_config(*_a, **_k):
        def _wrap(fn):
            return fn
        return _wrap

    def prompt_section(*_a, **_k):
        def _wrap(fn):
            return fn
        return _wrap


SYSTEM_PROMPT = """
You are the Procurement Bottleneck & Decision Agent, operating on SAP S/4HANA
Sourcing & Procurement data for the Purchasing Head of Department.

MANDATORY RULES:
1. Never fabricate SAP document numbers, amounts, or statuses — always retrieve live data first.
2. Set top=100 on every tool call that accepts it (prevents context overflow); tell the user when the limit is applied.
3. Present both the drivers AND the costs before stating any net exposure figure — never partial analysis.
4. Never execute write, update, or delete operations on SAP systems — this agent is advisory/read-only.
   The only side effects are (a) logging a decision record to the agent's own institutional memory and
   (b) raising an SAP Build Process Automation notification — both strictly after explicit human approval.
5. When data is missing, state this explicitly, label the affected figures as estimates, and continue
   with a partial simulation plus the disclaimer. Only call a finding "live" when the tool returned live data.
6. End every quantitative output with: "These are estimates based on available SAP data.
   Validate with your finance and procurement teams before acting."

RESPONSE FORMAT:
- Write for a Purchasing Head of Department, NOT for a developer.
- Use plain business language. Do NOT use technical field names (EKKO, EKPO, AFVV, LIFNR, WBS, float, BAPI, OData, RAG, similarity, injection).
- Respond in tables wherever possible: Project, PO #, Material, Supplier, Days Silent, Delivery Due Date.
- Dollar/Euro amounts: round to nearest thousand, no decimal places.
- Do NOT show: signal coverage tables, RAG chunks, similarity scores, injection scan counts, raw penalty_clause_eur fields, float day values, simulation model internals.
- DO show: supplier names, material numbers (not "DEFAULT"), project names, delivery dates, recommended actions.
""".strip()


@agent_model(key="config.model", label="LLM Model", description="AI Core model for intent framing and verdict synthesis")
def get_model_name() -> str:
    return os.environ.get("AGENT_MODEL", config.AGENT_MODEL)


@agent_config(key="config.temperature", label="LLM Temperature", description="Sampling temperature (deterministic)")
def get_temperature() -> float:
    return config.LLM_TEMPERATURE


@prompt_section(key="prompts.system", label="System Prompt", description="Advisory procurement-consequence agent instructions")
def get_system_prompt() -> str:
    return SYSTEM_PROMPT


def _days_since(iso_date: str) -> int:
    try:
        due = datetime.fromisoformat(iso_date).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - due).days
    except Exception:
        return 0


def _first(value: dict[str, Any] | ToolError) -> dict[str, Any]:
    """Return the first row of a tool 'value' list, or {} on error/empty."""
    if isinstance(value, ToolError) or not isinstance(value, dict):
        return {}
    rows = value.get("value") or []
    return rows[0] if rows else {}


class ProcurementConsequenceAgent:
    """Deterministic orchestration with optional LLM verdict polish."""

    def __init__(self, approvals: ApprovalStore | None = None) -> None:
        self._tools: list[Any] | None = None
        self._approvals = approvals or get_approval_store()

    async def _get_tools(self) -> list[Any]:
        if self._tools is None:
            self._tools = await get_mcp_tools()
        return self._tools

    @staticmethod
    def _by_name(tools: list[Any], name: str) -> Any | None:
        return next((t for t in tools if getattr(t, "name", "") == name), None)

    async def _call(self, tools: list[Any], name: str, breaker: CircuitBreaker, correlation_id: str,
                    **args: Any) -> Any:
        tool = self._by_name(tools, name)
        if tool is None:
            return ToolError("not_found", f"Tool {name} is not available.", name)
        # top=100 guard on list-style reads
        if "top" in tool.input_schema.get("properties", {}) and "top" not in args:
            args["top"] = 100
        return await call_tool_safely(name, tool.arun, args, breaker=breaker, correlation_id=correlation_id)

    # --- public entry -------------------------------------------------------
    async def handle(self, user_input: str, context_id: str, correlation_id: str = "") -> dict[str, Any]:
        """Handle one turn: resolve a pending approval, or run a fresh analysis.

        Approval responses are short (≤6 words). Anything longer is treated as a
        new analytical question: the pending state is cleared and a fresh analysis runs.
        This prevents the context from getting stuck after the first scorecard.
        """
        pending = self._approvals.get(context_id)
        if pending is not None:
            # Only an explicit approve/reject resolves the pending gate. Any other
            # message — even a short one like "open POs" — is a new question: clear
            # the gate and analyse fresh so a genuine query is never swallowed.
            if is_approval(user_input) or is_rejection(user_input):
                return await self._resolve_approval(pending, user_input, context_id, correlation_id)
            self._approvals.clear(context_id)
        return await self._analyze(user_input, context_id, correlation_id)

    # --- approval turn ------------------------------------------------------
    async def _resolve_approval(self, pending: PendingApproval, user_input: str, context_id: str,
                                correlation_id: str) -> dict[str, Any]:
        if is_rejection(user_input):
            self._approvals.clear(context_id)
            log_event(logger, "approval_rejected", context_id=context_id, action=pending.action)
            return {"content": "Action cancelled. The analysis stands; nothing was written or escalated.",
                    "pending": False}

        if not is_approval(user_input):
            return {"content": "Reply **approve** / **confirm** / **yes proceed** to execute, or **cancel** to abort.",
                    "pending": True}

        # Alternative-vendor confirmation must name the LIFNR (CP2).
        if pending.action == "source_switch" and not pending.payload.get("alt_vendor_confirmed"):
            lifnr = extract_lifnr(user_input)
            if not lifnr:
                return {"content": "A source switch needs the alternative vendor named explicitly. "
                                   "Reply e.g. `approve LIFNR-0010099`.", "pending": True}
            pending.payload["alt_vendor_confirmed"] = lifnr

        tools = await self._get_tools()
        breaker = CircuitBreaker()
        hod = pending.payload.get("hod_reviewer_id", "HOD-UNKNOWN")

        # 1) write the decision record to institutional memory (advisory side effect)
        rec = await self._call(
            tools, "write_decision_record", breaker, correlation_id,
            supplier_lifnr=pending.payload.get("supplier_lifnr", ""),
            material_group=pending.payload.get("material_group", ""),
            plant=pending.payload.get("plant", ""),
            po_reference=pending.payload.get("po_reference", ""),
            silence_duration_at_detection=pending.payload.get("silence_duration", 0),
            consequence_exposure_at_decision=pending.payload.get("exposure_eur", 0.0),
            action_taken=pending.action,
            hod_reviewer_id=hod,
            approval_keyword_received=user_input.strip().lower(),
            annotation=pending.payload.get("annotation", ""),
        )
        log_milestone(logger, "M8", not isinstance(rec, ToolError), "Decision record written (approved)",
                      context_id=context_id)

        # 2) raise the escalation notification (advisory side effect)
        esc = await self._call(
            tools, "trigger_escalation_notification", breaker, correlation_id,
            action=pending.action,
            pm_recipients=pending.payload.get("pm_recipients", []),
            recommended_action=pending.action,
            scorecard=pending.payload.get("scorecard", {}),
        )
        log_milestone(logger, "M9", not isinstance(esc, ToolError), "Escalation notification raised (approved)",
                      context_id=context_id)

        self._approvals.clear(context_id)
        rec_id = rec.get("record_id") if isinstance(rec, dict) else "n/a"
        task_id = esc.get("spa_task_id") if isinstance(esc, dict) else "n/a"
        content = (
            f"✅ Approved and executed (advisory):\n"
            f"- Decision record **{rec_id}** written to institutional memory (ZAGENT_DECISION_LOG).\n"
            f"- SPA notification **{task_id}** raised to the HoD and project managers "
            f"{pending.payload.get('pm_recipients', [])}.\n\n"
            f"No SAP business object was modified. {config.FINANCIAL_DISCLAIMER}"
        )
        return {"content": content, "pending": False, "record_id": rec_id, "spa_task_id": task_id}

    # --- analysis turn ------------------------------------------------------
    # Regex to detect simple list/discovery queries that should bypass the full 7-section scorecard.
    _LIST_QUERY_RE = re.compile(
        r"\b(list|show)\b.{0,60}\b(suppliers?|vendors?|pos?|purchase.orders?)\b"
        r"|\bsilent\s+(suppliers?|vendors?)\b"
        r"|\b(suppliers?|vendors?)\s+silent\b"
        r"|\bopen\s+(pos?|purchase.orders?)\b"
        r"|\bwhich\s+(suppliers?|vendors?|pos?)\b",
        re.IGNORECASE,
    )
    _CONSEQUENCE_QUERY_RE = re.compile(
        r"\b(consequence|impact|what.{0,5}if|wait|delay|48.{0,5}hours?|additional\s+days?"
        r"|how.{0,10}bad|how.{0,10}much|cost\s+us|what.{0,15}happen|worse|escalat)\b",
        re.IGNORECASE,
    )
    _CRITICAL_QUERY_RE = re.compile(
        r"\b(critical.{0,5}path|critical.{0,5}mater|on.{0,5}track|project.{0,10}risk"
        r"|materials?.{0,10}risk|at.{0,5}risk|milestone|which\s+mater)\b",
        re.IGNORECASE,
    )
    _APPROVAL_DELAY_RE = re.compile(
        r"\b(pr.{0,5}to.{0,5}po|approval.{0,10}delay|internal.{0,10}delay"
        r"|approvals?.{0,10}pending|workflow|stuck.{0,10}appro)\b",
        re.IGNORECASE,
    )
    _ALT_SUPPLIER_RE = re.compile(
        r"\b(alternate|alternative|other|another|different|backup|second)\s+"
        r"(supplier|vendor|source|sourcing)s?\b"
        r"|\bfind\s+(a\s+)?(new\s+)?(supplier|vendor|source)s?\b",
        re.IGNORECASE,
    )
    _PERF_QUERY_RE = re.compile(
        r"\b(delivery\s+performance|performance\s+history|performance\s+for|track\s+record"
        r"|on[-\s]?time|reliab\w*|delivery\s+history|supplier\s+performance|past\s+deliver\w*)\b",
        re.IGNORECASE,
    )

    async def _analyze(self, user_input: str, context_id: str, correlation_id: str) -> dict[str, Any]:
        tools = await self._get_tools()
        breaker = CircuitBreaker()
        filters = self._parse_query(user_input)

        # For simple list/discovery queries with no specific PO/supplier target,
        # return a formatted table instead of the full 7-section consequence scorecard.
        # A delivery-performance question must NOT fall in here (it mentions "supplier"
        # but wants the vendor's track record, not the open-PO list).
        if (not filters and self._LIST_QUERY_RE.search(user_input)
                and not self._PERF_QUERY_RE.search(user_input)):
            return await self._quick_list(user_input, context_id, correlation_id)

        with tracer.start_as_current_span("gather_signals"):
            chain_raw = await self._call(tools, "get_open_pr_po_chain", breaker, correlation_id, **filters)
            # Fail honestly: if the primary SAP read errors (auth, quota, outage),
            # never proceed into the LLM path — an empty context makes the model
            # invent plausible-but-fake PO details. Surface the real status instead.
            if isinstance(chain_raw, ToolError):
                return {"content": self._backend_error_report(chain_raw, filters.get("po_number")),
                        "pending": False}
            chain = _first(chain_raw)
            log_milestone(logger, "M1", bool(chain), "Delay/silence detection scan", context_id=context_id)
            po = chain.get("po_number", filters.get("po_number", ""))
            supplier = chain.get("supplier_lifnr", filters.get("supplier_lifnr", ""))
            material_cat = chain.get("material_category", "DEFAULT")

            silence = _first(await self._call(tools, "detect_supplier_silence", breaker, correlation_id,
                                              po_number=po, supplier_lifnr=supplier))
            wbs = _first(await self._call(tools, "link_po_to_project_wbs", breaker, correlation_id, po_number=po))
            log_milestone(logger, "M2", bool(wbs), "PR→PO chain + WBS traced", context_id=context_id)
            perf = _first(await self._call(tools, "get_vendor_delivery_performance", breaker, correlation_id,
                                           supplier_lifnr=supplier, material_category=material_cat))
            source = _first(await self._call(tools, "get_source_and_contract_dependencies", breaker, correlation_id,
                                             material_number=chain.get("material_number", ""),
                                             plant=wbs.get("plant", "")))
            contract = _first(await self._call(tools, "get_procurement_contract_terms", breaker, correlation_id,
                                               supplier_lifnr=supplier, material_number=chain.get("material_number", "")))
            rag = await self._call(tools, "rag_retrieve_contract_and_history", breaker, correlation_id,
                                   query=f"penalty clauses and prior escalations for {supplier}",
                                   supplier_lifnr=supplier, material_number=chain.get("material_number", ""))
            # L0-5.6 indirect prompt-injection gate: scan retrieved business data
            # before any chunk reaches the model context or the report (fail-closed).
            if isinstance(rag, dict):
                clean_rows, flagged_rows = sanitize_rows(rag.get("value", []))
                rag["value"] = clean_rows
                rag["_injection_flagged"] = flagged_rows
                if flagged_rows:
                    log_event(logger, "indirect_injection_blocked", context_id=context_id,
                              count=len(flagged_rows),
                              patterns=sorted({p for r in flagged_rows for p in r.get("_injection_matched", [])}))
            memory = await self._call(tools, "recall_supplier_memory", breaker, correlation_id,
                                      supplier_lifnr=supplier, material_group=material_cat,
                                      silence_duration=silence.get("silence_duration_days", 0))
            approval_wf = _first(await self._call(tools, "get_approval_workflow_status", breaker, correlation_id,
                                                   document_type="PR",
                                                   document_number=chain.get("pr_number", po or "")))

        silence_days = int(silence.get("silence_duration_days", 0) or 0)
        _float = wbs.get("available_float_days")
        is_critical = critical_path_flag(int(_float) if _float is not None else 99)
        log_milestone(logger, "M3", True, "Critical-path linkage resolved", context_id=context_id,
                      critical_path=is_critical)

        # Explicit user intents must always be answered, even when silence is low —
        # a direct "find alternate suppliers" or "what's the consequence" question
        # should never be swallowed by the non-issue short-circuit below. A consequence
        # question routes to a focused answer whether or not a specific PO is named;
        # an explicit "run the analysis" request still produces the full scorecard.
        wants_alt = bool(self._ALT_SUPPLIER_RE.search(user_input))
        wants_perf = bool(self._PERF_QUERY_RE.search(user_input))
        is_question = bool(re.search(r"\b(what|which|how|why|will|would|can|should|if|happens?|consequence)\b|\?",
                                     user_input, re.IGNORECASE))
        wants_analysis = bool(re.search(r"\b(analy|run|assess|review|generate|full\s+report|scorecard)\b",
                                        user_input, re.IGNORECASE))
        # Any question that isn't a full-analysis request gets a contextual LLM answer.
        # The old regex was too narrow (e.g. `\bdelay\b` missed "delayed", `\bhappen\b`
        # missed "happens") — so most user questions fell through to the short-circuit.
        wants_freeform = is_question and not wants_analysis

        # Short-circuit: silence below tolerance, not critical, and no explicit intent → log and exit.
        if (silence_days < config.SILENCE_TOLERANCE_DAYS and not is_critical
                and not wants_alt and not wants_perf and not wants_freeform):
            return {"content": self._nonissue_report(po, supplier, silence_days), "pending": False}

        with tracer.start_as_current_span("consequence_simulation"):
            sim_input = SimulationInput(
                po_number=po or "UNKNOWN",
                material_category=material_cat,
                po_net_value_eur=float(chain.get("po_net_value_eur", 0.0) or 0.0),
                silence_duration_days=silence_days,
                available_float_days=int(wbs.get("available_float_days", 0) or 0),
                expected_lead_time_days=int(chain.get("expected_lead_time_days_plifz", 0) or 0),
                days_since_due=_days_since(chain.get("delivery_due_date", "")),
                idle_teams=int(wbs.get("resource_teams", 0) or 0),
                daily_team_cost_rate_eur=float(wbs.get("daily_team_cost_rate_eur", 0.0) or 0.0),
                milestone_at_risk=bool(wbs.get("milestone_id")),
                milestone_penalty_eur=float(contract.get("penalty_clause_eur", 0.0) or 0.0),
            )
            cards = run_consequence_simulation(sim_input)
            worst = max(cards, key=lambda c: c.total_consequence_exposure_eur)
            log_milestone(logger, "M4", True, "Consequence simulation computed", context_id=context_id,
                          exposure_eur=worst.total_consequence_exposure_eur)

        repeat = memory.get("repeat_offender_count", 0) if isinstance(memory, dict) else 0
        log_milestone(logger, "M5", True, "Institutional memory recalled", context_id=context_id,
                      repeat_offender=repeat)

        alts = source.get("alternatives", []) if isinstance(source, dict) else []
        alt = alts[0] if alts else {}
        readiness = SourceReadiness(
            alternative_available=bool(alt),
            alternative_contracted=bool(alt.get("contracted")),
            alternative_lifnr=alt.get("supplier_lifnr", ""),
            alternative_on_time_rate=float(alt.get("on_time_rate", 0.0) or 0.0),
            has_pinfo_record=bool(alt.get("has_pinfo_record", True)),
            purchasing_blocked=bool(alt.get("purchasing_blocked", False)),
        )
        actions = recommend_next_action(
            worst_scorecard=worst,
            is_critical_path=is_critical,
            supplier_delivery_risk_score=int(perf.get("supplier_delivery_risk_score", 0) or 0),
            source_readiness=readiness,
            repeat_offender_count=int(repeat or 0),
            has_contract=bool(contract.get("contract_ref")),
        )
        log_milestone(logger, "M6", bool(actions), "Ranked recommendation synthesized", context_id=context_id)

        # Dedicated alternate-supplier intent: list the available alternative sources
        # (fires whether or not a specific PO/supplier was named).
        if wants_alt:
            return {"content": self._alternate_suppliers_report(
                supplier, material_cat, chain.get("material_number") or "", source, perf),
                "pending": False}

        # Free-form questions (incl. delivery-performance history) → answer the exact
        # question asked, concisely, skipping the HITL scorecard. The LLM composes the
        # reply when AI Core is available; otherwise a focused deterministic fallback.
        if wants_perf or wants_freeform:
            content = await self._llm_contextual_answer(
                user_input, chain, silence, wbs, perf, approval_wf, cards, worst, actions
            )
            return {"content": content, "pending": False}

        top_action = actions[0]
        checkpoint_ctx = {
            "action": top_action.action,
            "exposure_eur": worst.total_consequence_exposure_eur,
            "penalty_exposure_eur": worst.penalty_exposure_eur,
            "is_critical_path": is_critical,
            "days_since_due": sim_input.days_since_due,
            "no_grn": not silence.get("last_order_ack_vgabe1"),
            "has_pinfo_record": readiness.has_pinfo_record,
            "has_agreement": bool(contract.get("contract_ref")),
            "contract_source": contract.get("contract_source", "none"),
            "contract_ref": contract.get("contract_ref"),
            "alt_vendor_lifnr": readiness.alternative_lifnr,
            "alt_lead_time": alt.get("lead_time_days"),
            "alt_contract_coverage": alt.get("contracted"),
            "alt_purchasing_block": alt.get("purchasing_blocked"),
            "supplier_lifnr": supplier,
            "pm_recipients": [wbs.get("responsible_person")] if wbs.get("responsible_person") else [],
            "po_net_value_eur": sim_input.po_net_value_eur,
            "wbs_element": wbs.get("wbs_element"),
        }
        checkpoints = evaluate_checkpoints(checkpoint_ctx)
        log_milestone(logger, "M7", True, "HoD approval gate reached", context_id=context_id)

        # Register the pending approval so the next turn can execute on 'approve'.
        self._approvals.put(PendingApproval(
            context_id=context_id, action=top_action.action,
            payload={
                "supplier_lifnr": supplier, "material_group": material_cat,
                "plant": wbs.get("plant", ""), "po_reference": po,
                "silence_duration": silence_days, "exposure_eur": worst.total_consequence_exposure_eur,
                "pm_recipients": checkpoint_ctx["pm_recipients"], "scorecard": worst.as_dict(),
                "hod_reviewer_id": filters.get("hod_reviewer_id", "HOD-ADARSH"),
            },
            checkpoints=checkpoints,
        ))

        report = self._build_report(po, supplier, material_cat, silence, wbs, perf, source, contract,
                                     rag, memory, cards, worst, actions, checkpoints, is_critical,
                                     po_net_value=sim_input.po_net_value_eur,
                                     delivery_due_date=chain.get("delivery_due_date") or "",
                                     material_number=chain.get("material_number") or "",
                                     approval_wf=approval_wf)
        return {"content": report, "pending": True, "action": top_action.action,
                "exposure_eur": worst.total_consequence_exposure_eur,
                "checkpoints": [c.id for c in checkpoints]}

    async def _quick_list(self, user_input: str, context_id: str, correlation_id: str) -> dict[str, Any]:
        """Return a formatted table for list/discovery queries (no full scorecard)."""
        tools = await self._get_tools()
        breaker = CircuitBreaker()
        chain_result = await self._call(tools, "get_open_pr_po_chain", breaker, correlation_id)

        if isinstance(chain_result, ToolError):
            return {"content": self._backend_error_report(chain_result), "pending": False}

        rows = (chain_result.get("value") or []) if isinstance(chain_result, dict) else []
        if not rows and isinstance(chain_result, dict) and chain_result.get("po_number"):
            rows = [chain_result]

        if not rows:
            return {"content": "No open purchase orders found in the connected S/4 system.", "pending": False}

        days_m = re.search(r"\b(\d+)\s+days?\b", user_input)
        silence_filter = int(days_m.group(1)) if days_m else None
        asking_silence = bool(re.search(r"\bsilent\b|\bsilence\b", user_input, re.IGNORECASE))

        if asking_silence or silence_filter:
            enriched: list[dict] = []
            for row in rows:
                sil_raw = await self._call(tools, "detect_supplier_silence", breaker, correlation_id,
                                           po_number=row.get("po_number", ""),
                                           supplier_lifnr=row.get("supplier_lifnr", ""))
                srow = _first(sil_raw)
                sil_days = int(srow.get("silence_duration_days", 0) or 0)
                row = dict(row)
                row["_silence_days"] = sil_days
                if srow.get("delivery_due_date"):
                    row["_delivery_due"] = srow.get("delivery_due_date")
                if silence_filter is None or sil_days >= silence_filter:
                    enriched.append(row)
            rows = enriched

        if not rows:
            note = f" silent beyond {silence_filter} days" if silence_filter else ""
            return {"content": f"No open POs found{note} in the connected S/4 system.", "pending": False}

        header = ("### Suppliers Silent Beyond Threshold\n" if (asking_silence and silence_filter) else
                  "### Supplier Silence on Open Purchase Orders\n" if asking_silence else
                  "### Open Purchase Orders\n")
        lines = [header,
                 "| PO # | Material | Supplier | Days Silent | Delivery Due |",
                 "|---|---|---|---|---|"]
        for row in rows:
            po_no = row.get("po_number", "?")
            sup = row.get("supplier_lifnr", "?")
            # Show real material number; never show "DEFAULT"
            mat_raw = row.get("material_number") or row.get("material_category") or "—"
            mat = mat_raw if mat_raw and str(mat_raw).upper() not in ("DEFAULT", "") else "—"
            due = row.get("delivery_due_date") or row.get("_delivery_due") or "—"
            sil = row.get("_silence_days", row.get("silence_days", "—"))
            risk = "🔴" if isinstance(sil, int) and sil >= 7 else "🟡" if isinstance(sil, int) and sil >= 3 else ""
            lines.append(f"| {po_no} | {mat} | {sup} | {risk} {sil} | {due} |")

        lines.append(f"\n*{config.FINANCIAL_DISCLAIMER}*")
        return {"content": "\n".join(lines), "pending": False}

    # --- query parsing (reuse CLAUDE utility patterns) ----------------------
    @staticmethod
    def _parse_query(text: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        po = re.search(r"\b(45\d{8}|PO[-\s]?\d+)\b", text or "")
        if po:
            out["po_number"] = po.group(1).replace("PO", "").strip("- ")
        proj = re.search(r"\bP-[A-Z]+-\d+\b", text or "")
        if proj:
            out["project_code"] = proj.group(0)
        sup = re.search(r"\bLIFNR-\d{4,10}\b", text or "")
        if sup:
            out["supplier_lifnr"] = sup.group(0)
        return out

    # --- business-language answer helpers -----------------------------------
    # Business-language labels for recommended steps (no internal action codes shown to users).
    _STEP_LABELS = {
        "escalate": "Contact the supplier's account manager now and ask for a firm delivery date",
        "source_switch": "Line up an approved alternative supplier as a backup",
        "absorb": "Hold for now and keep monitoring — reschedule dependent work only if the delay grows",
    }

    @staticmethod
    def _business_answer(question: str, chain: dict, silence: dict, wbs: dict, perf: dict,
                         approval_wf: dict, worst: Scorecard, actions: list) -> str:
        """Question-aware, business-language answer rendered as a table — the deterministic
        path used offline and whenever the LLM is unavailable. No internal/technical terms."""
        po = chain.get("po_number") or "—"
        supplier_id = chain.get("supplier_lifnr") or "—"
        supplier_name = perf.get("supplier_name") or supplier_id
        silence_days = int(silence.get("silence_duration_days", 0) or 0)
        mat = chain.get("material_number") or chain.get("material_category") or "—"
        if str(mat).upper() in ("DEFAULT", ""):
            mat = "—"
        delivery_due = chain.get("delivery_due_date") or silence.get("delivery_due_date") or "—"
        project = wbs.get("activity_text") or wbs.get("wbs_element") or "Not yet linked to a project"
        exposure = worst.total_consequence_exposure_eur
        slip = worst.schedule_slip_days
        pr_delay = int(approval_wf.get("time_in_queue_days", 0) or 0) if isinstance(approval_wf, dict) else 0
        step = ProcurementConsequenceAgent._STEP_LABELS.get(
            actions[0].action if actions else "", "Keep monitoring and re-check on the next scan")

        q = (question or "").lower()
        # Delivery-performance / track-record question → focused performance answer only.
        if any(k in q for k in ("performance", "track record", "on-time", "on time",
                                 "reliab", "delivery history", "past deliver")):
            otr = perf.get("on_time_rate")
            on_time_pct = f"{float(otr) * 100:.0f}%" if isinstance(otr, (int, float)) else "—"
            deliveries = perf.get("deliveries_last_12m")
            late = perf.get("late_deliveries")
            avg_late = perf.get("avg_days_late")
            risk_score = perf.get("supplier_delivery_risk_score")
            if isinstance(risk_score, (int, float)):
                band = ("🔴 High" if risk_score >= config.VENDOR_RISK_HIGH
                        else "🟡 Medium" if risk_score >= config.VENDOR_RISK_MEDIUM else "🟢 Low")
            else:
                band = "—"
            summary = (f"Delivery track record for supplier **{supplier_name}**"
                       + (f" on **{mat}**" if mat != "—" else "") + ": "
                       + (f"**{on_time_pct}** on-time over the last 12 months"
                          f"{f' ({late} of {deliveries} deliveries late)' if deliveries and late is not None else ''}."
                          if on_time_pct != "—" else "limited delivery history on record."))
            lines = [summary, "", "| Detail | Value |", "|---|---|",
                     f"| Supplier | {supplier_name} |"]
            if deliveries is not None:
                lines.append(f"| Deliveries (last 12 months) | {deliveries} |")
            if on_time_pct != "—":
                lines.append(f"| On-time rate | {on_time_pct} |")
            if late is not None:
                lines.append(f"| Late deliveries | {late} |")
            if isinstance(avg_late, (int, float)):
                lines.append(f"| Average delay when late | {avg_late:g} day(s) |")
            lines.append(f"| Delivery-risk level | {band} |")
            lines.append(f"\n*{config.FINANCIAL_DISCLAIMER}*")
            return "\n".join(lines)

        if "absorb" in q or "accept" in q:
            summary = (f"If you accept this delay on purchase order **{po}**, the main effect is a possible "
                       f"**{slip}-day** push to dependent work"
                       + (f" and an estimated **€{exposure:,.0f}** in avoidable cost." if exposure > 0
                          else ", with no material cost impact at today's figures."))
        elif "wait" in q or "48" in q or "week" in q or "consequence" in q or "delay" in q:
            summary = (f"If supplier **{supplier_name}** stays silent longer on purchase order **{po}**, "
                       f"the delivery risk grows: a projected **{slip}-day** delay to the schedule"
                       + (f" and up to **€{exposure:,.0f}** in potential extra cost." if exposure > 0
                          else " — still within tolerance at today's figures, but worth watching."))
        elif "critical" in q or "milestone" in q or "schedule" in q or "material" in q:
            on_cp = "is on the critical path" if wbs.get("milestone_id") or slip > 0 else "is being monitored"
            summary = (f"Material **{mat}** on purchase order **{po}** {on_cp} for **{project}**. "
                       f"A delay here could move the schedule by about **{slip} day(s)**.")
        else:
            summary = (f"Here is where purchase order **{po}** with supplier **{supplier_name}** stands today.")

        lines = [summary, "",
                 "| Detail | Value |", "|---|---|",
                 f"| Purchase order | {po} |",
                 f"| Supplier | {supplier_name} |",
                 f"| Material | {mat} |",
                 f"| Project | {project} |",
                 f"| Days without supplier response | {silence_days} |",
                 f"| Delivery due | {delivery_due} |"]
        if exposure > 0:
            lines.append(f"| Estimated cost impact | €{exposure:,.0f} |")
        lines.append(f"| Possible schedule delay | {slip} day(s) |")
        if pr_delay > 0:
            lines.append(f"| Internal approval waiting time | {pr_delay} day(s) |")
        lines.append(f"| Suggested next step | {step} |")
        lines.append(f"\n*{config.FINANCIAL_DISCLAIMER}*")
        return "\n".join(lines)

    # --- report rendering ---------------------------------------------------
    def _build_report(self, po, supplier, material_cat, silence, wbs, perf, source, contract,
                      rag, memory, cards, worst, actions, checkpoints, is_critical,
                      po_net_value: float = 0.0, delivery_due_date: str = "",
                      material_number: str = "", approval_wf: dict | None = None) -> str:

        # Prefer actual material number from the PO item; fall back to material group; never "DEFAULT"
        material_display = (
            material_number if material_number and material_number.upper() not in ("DEFAULT", "")
            else (material_cat if material_cat and material_cat.upper() != "DEFAULT" else "—")
        )

        lines: list[str] = []

        # 1. Blocker table (business-user first view)
        lines.append("### Procurement Blockers")
        lines.append("| PO # | Project | Material | Supplier | Days Silent | Delivery Due | Risk |")
        lines.append("|---|---|---|---|---|---|---|")
        silence_days = int(silence.get("silence_duration_days", 0) or 0)
        project_name = wbs.get("activity_text") or wbs.get("wbs_element") or "—"
        delivery_due = (delivery_due_date or silence.get("delivery_due_date") or
                        wbs.get("delivery_due_date") or "—")
        risk_flag = "🔴 Urgent" if silence_days >= 7 else "🟡 Watch" if silence_days >= 3 else "🟢 OK"
        lines.append(f"| {po} | {project_name} | {material_display} | {supplier} | "
                     f"{silence_days} | {delivery_due} | {risk_flag} |")

        # 2. Situation (plain language)
        lines.append("\n### Situation")
        exposure = worst.total_consequence_exposure_eur
        slip_days = worst.schedule_slip_days
        lines.append(f"Supplier **{supplier}** has been unresponsive for **{silence_days} days** "
                     f"on purchase order **{po}** (material {material_display}). "
                     f"{'This delivery is on the critical path — any further delay directly impacts the project schedule.' if is_critical else 'This delivery is being monitored for schedule impact.'}")

        # 3. Business Impact (no raw penalty numbers)
        lines.append("\n### Business Impact")
        if exposure > 0:
            lines.append(f"- Estimated cost impact if no action is taken today: **€{exposure:,.0f}**")
        else:
            lines.append("- ⚠ Cost impact cannot be calculated yet — this purchase order is not linked to "
                         "project schedule and resource data. Connect Project System to enable it.")
        if slip_days > 0:
            lines.append(f"- Possible schedule delay: **{slip_days} day(s)**")
        # Surface internal PR→PO approval delay as a distinct signal
        if isinstance(approval_wf, dict):
            pr_delay = int(approval_wf.get("time_in_queue_days", 0) or 0)
            if pr_delay > 0:
                lines.append(f"- ⚠ Internal approval delay: PR has been pending PO release for "
                             f"**{pr_delay} day(s)** — workflow bottleneck adding to the overall timeline.")
        milestone_id = wbs.get("milestone_id")
        if milestone_id:
            lines.append(f"- Milestone **{milestone_id}** is at risk — contract penalty applies if missed.")
        if not contract.get("contract_ref"):
            lines.append("- ⚠ No contract on file — spend is unprotected and supplier cannot be penalised.")
        repeat = memory.get("repeat_offender_count", 0) if isinstance(memory, dict) else 0
        if int(repeat or 0) > 0:
            lines.append(f"- This supplier has a history of silence ({int(repeat)} prior instance(s) on record).")

        # 4. Recommended Actions (business language — no internal action codes)
        lines.append("\n### Recommended Next Steps")
        for a in actions:
            label = self._STEP_LABELS.get(a.action, a.action.replace("_", " ").capitalize())
            lines.append(f"- **{label}** — {a.rationale}")

        # 5. Awaiting Approval
        lines.append("\n### Awaiting Your Approval")
        lines.append("Reply **approve** to execute, or **cancel** to dismiss:")
        lines.append("- Escalation notification will be sent to the project manager.")
        lines.append("- The decision will be logged for audit purposes.")
        if checkpoints:
            for cp in checkpoints:
                lines.append(f"- {cp.description}")

        lines.append(f"\n*{config.FINANCIAL_DISCLAIMER}*")
        return "\n".join(lines)

    async def _llm_contextual_answer(self, question: str, chain: dict, silence: dict, wbs: dict,
                                      perf: dict, approval_wf: dict, cards: list,
                                      worst: Scorecard, actions: list) -> str:
        """Answer a specific question in business language. Uses the AI Core LLM when
        available; always falls back to the deterministic business table so the user
        still gets a tailored, non-technical answer if the model is unreachable."""
        fallback = self._business_answer(question, chain, silence, wbs, perf, approval_wf, worst, actions)
        # Use the LLM for reasoning whenever AI Core is configured — even when the SAP
        # DATA is mocked (IBD_TESTING). Mocking the data source must not disable the
        # model's reasoning; only the absence of creds (e.g. in tests) falls back.
        if not config.aicore_configured():
            return fallback

        po = chain.get("po_number", "—")
        supplier_name = perf.get("supplier_name") or chain.get("supplier_lifnr", "—")
        silence_days = int(silence.get("silence_duration_days", 0) or 0)
        mat = chain.get("material_number") or chain.get("material_category") or "—"
        if str(mat).upper() in ("DEFAULT", ""):
            mat = "—"
        delivery_due = chain.get("delivery_due_date") or silence.get("delivery_due_date") or "—"
        project = wbs.get("activity_text") or wbs.get("wbs_element") or "Not yet linked to a project"
        exposure = worst.total_consequence_exposure_eur
        slip = worst.schedule_slip_days
        pr_delay = int(approval_wf.get("time_in_queue_days", 0) or 0) if isinstance(approval_wf, dict) else 0
        step = self._STEP_LABELS.get(actions[0].action if actions else "", "Keep monitoring")

        ctx_lines = [
            f"- Purchase order: {po}",
            f"- Supplier: {supplier_name}",
            f"- Material: {mat}",
            f"- Project: {project}",
            f"- Days without supplier response: {silence_days}",
            f"- Delivery due: {delivery_due}",
            (f"- Estimated cost impact: €{exposure:,.0f}" if exposure > 0
             else "- Estimated cost impact: not material at today's figures"),
            f"- Possible schedule delay: {slip} day(s)",
        ]
        # Supplier delivery-performance facts (so performance/track-record questions
        # can be answered without inventing numbers).
        otr = perf.get("on_time_rate")
        if isinstance(otr, (int, float)):
            ctx_lines.append(f"- Supplier on-time rate (last 12 months): {otr * 100:.0f}%")
        if perf.get("deliveries_last_12m") is not None:
            ctx_lines.append(f"- Deliveries in last 12 months: {perf.get('deliveries_last_12m')}")
        if perf.get("late_deliveries") is not None:
            ctx_lines.append(f"- Late deliveries: {perf.get('late_deliveries')}")
        if isinstance(perf.get("avg_days_late"), (int, float)):
            ctx_lines.append(f"- Average delay when late: {perf.get('avg_days_late'):g} day(s)")
        if perf.get("supplier_delivery_risk_score") is not None:
            ctx_lines.append(f"- Supplier delivery-risk score (0-100): {perf.get('supplier_delivery_risk_score')}")
        if pr_delay > 0:
            ctx_lines.append(f"- Internal approval waiting time: {pr_delay} day(s)")
        ctx_lines.append(f"- Suggested next step: {step}")
        context_str = "\n".join(ctx_lines)

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Facts available (use ONLY the ones relevant to the question — ignore the rest):\n{context_str}\n\n"
            f"The user asked: {question}\n\n"
            "Answer ONLY what they asked — directly and briefly. Do NOT volunteer facts they "
            "did not ask about, and do NOT restate the whole situation. "
            "If the question needs a single fact or a short explanation, reply in one or two "
            "plain sentences with NO table. Include a small Markdown table ONLY when the question "
            "genuinely needs several figures side by side (e.g. a performance track record). "
            "Write for a business leader, not a developer. Do NOT use the words 'verdict', 'absorb', "
            "'escalate', 'source switch', 'confidence', 'exposure', or any SAP field names. "
            f"End with exactly this line:\n{config.FINANCIAL_DISCLAIMER}"
        )
        try:
            from langchain_litellm import ChatLiteLLM
            llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature(), max_tokens=600)
            resp = await llm.ainvoke(prompt)
            answer = (getattr(resp, "content", "") or "").strip()
            if answer:
                return answer
            log_event(logger, "llm_empty_response", status="warn", model=get_model_name())
        except Exception as exc:
            log_event(logger, "llm_call_failed", status="error", model=get_model_name(),
                      error=f"{type(exc).__name__}: {exc}")
        return fallback

    @staticmethod
    def _alternate_suppliers_report(current_supplier: str, material_cat: str, material_number: str,
                                    source: dict, perf: dict) -> str:
        """Focused answer for the 'find alternate suppliers' intent — lists available
        alternative sources from the material's purchasing info records (live BAH read)."""
        mat = material_number or material_cat
        if not mat or str(mat).upper() in ("DEFAULT", ""):
            mat = "this material"
        alts = source.get("alternatives", []) if isinstance(source, dict) else []

        lines = [f"### Alternate Supplier Options for {mat}"]
        if not alts:
            lines.append(
                f"\nNo alternative sources are currently set up in the system for {mat}. "
                f"The current supplier **{current_supplier or '—'}** appears to be the only approved source.\n\n"
                "**What you can do:**\n"
                "- Request Procurement to identify and onboard a backup supplier for this material.\n"
                "- Check whether a framework agreement exists with another vendor for this category.")
            lines.append(f"\n*{config.FINANCIAL_DISCLAIMER}*")
            return "\n".join(lines)

        lines.append("| Supplier | Under Contract | Purchasing Status | Valid Until |")
        lines.append("|---|---|---|---|")
        for a in alts:
            sup = a.get("supplier_lifnr", "—")
            contracted = "✅ Yes" if a.get("contracted") else "— No"
            status = "🔴 Blocked" if a.get("purchasing_blocked") else "🟢 Available"
            valid_to = a.get("valid_to") or "—"
            lines.append(f"| {sup} | {contracted} | {status} | {valid_to} |")

        ready = [a for a in alts if not a.get("purchasing_blocked")]
        if ready:
            top = ready[0]
            lines.append(f"\n**Recommendation:** Supplier **{top.get('supplier_lifnr')}** is available"
                         f"{' and already under contract' if top.get('contracted') else ''} — "
                         f"the fastest switch option. Any source change needs Purchasing HoD approval.")
        else:
            lines.append("\n**Note:** All listed alternatives are currently purchasing-blocked — "
                         "a block release or new vendor onboarding is required before switching.")
        lines.append(f"\n*{config.FINANCIAL_DISCLAIMER}*")
        return "\n".join(lines)

    @staticmethod
    def _backend_error_report(err: "ToolError", po: str | None = None) -> str:
        """Honest, business-readable message when the SAP read fails — never fabricate data."""
        target = f" for purchase order **{po}**" if po else ""
        detail = {
            "backend_unavailable": "The SAP system did not respond (it may be temporarily unavailable, "
                                   "or the sandbox request quota for today has been used up).",
            "quota_exceeded": "The SAP sandbox request quota has been used up for now. It resets on "
                              "SAP's schedule (typically at midnight UTC). Live data will return automatically "
                              "once the quota refreshes — or a fresh sandbox API key can be used.",
            "throttled": "The SAP system is rate-limiting requests right now.",
            "auth_expired": "The connection to SAP needs to re-authenticate.",
            "not_authorized": "This user is not authorized to read the requested SAP data.",
            "not_found": "The requested record or service was not found in SAP.",
        }.get(err.code, err.user_msg)
        return (
            f"I couldn't retrieve live data from SAP{target} right now, so I won't guess.\n\n"
            f"| Detail | Value |\n"
            f"|---|---|\n"
            f"| Status | ⚠ Live SAP data unavailable |\n"
            f"| Reason | {detail} |\n\n"
            f"No figures are shown because I only report verified SAP data — never estimates "
            f"invented without a live read. Please retry shortly; if it persists, the connection "
            f"or sandbox quota needs attention.\n\n"
            f"*{config.FINANCIAL_DISCLAIMER}*"
        )

    @staticmethod
    def _nonissue_report(po: str, supplier: str, silence_days: int) -> str:
        status = "🟢 On Track" if silence_days < config.SILENCE_TOLERANCE_DAYS else "🟡 Monitor"
        next_review = config.SILENCE_TOLERANCE_DAYS - silence_days
        return (
            f"Purchase order **{po}** is currently on track — no action required today.\n\n"
            f"| Detail | Value |\n"
            f"|---|---|\n"
            f"| Purchase Order | {po} |\n"
            f"| Supplier | {supplier or '—'} |\n"
            f"| Days Without Response | {silence_days} |\n"
            f"| Status | {status} |\n"
            f"| Monitor Again In | {max(1, next_review)} day(s) |\n\n"
            f"This order will be re-evaluated automatically. "
            f"If the supplier remains unresponsive beyond {config.SILENCE_TOLERANCE_DAYS} days, "
            f"it will move to the **Active Blockers** list for your review.\n\n"
            f"*{config.FINANCIAL_DISCLAIMER}*"
        )
