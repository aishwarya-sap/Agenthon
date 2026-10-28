"""Per-run invocation state for the Material Risk orchestration graph.

The ReAct graph built by ``create_agent()`` manages its own message state
(LangGraph ``MessagesState``) internally, so there is no custom turn-state TypedDict
to carry here. What every run *does* need is the invocation config: the checkpoint
thread key (user identity + Joule context id, so each conversation resumes its own
memory) and the recursion budget. Building it here keeps the orchestrator and the
agent on one definition.
"""
from __future__ import annotations

from typing import Any

from .orchestrator import DEFAULT_RECURSION_LIMIT


def make_run_config(
    context_id: str, user_sub: str | None, recursion_limit: int = DEFAULT_RECURSION_LIMIT
) -> dict[str, Any]:
    """Per-run graph config: checkpoint ``thread_id`` (``user:context``) + recursion cap.

    The thread id binds the checkpointer's saved history to one user + one Joule
    context, so a follow-up turn resumes the same conversation and never crosses users.
    The caller resolves ``user_sub`` (from the request's identity) and passes it in.
    """
    return {
        "configurable": {"thread_id": f"{user_sub}:{context_id}"},
        "recursion_limit": recursion_limit,
    }
