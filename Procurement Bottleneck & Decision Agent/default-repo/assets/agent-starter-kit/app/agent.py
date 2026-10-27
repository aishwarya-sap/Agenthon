"""Generic SAP A2A agent — Sprint 1 scaffold.

This is the default repo shared with every client at engagement start.
Replace [Agent Name] and the system prompt with your domain specifics in Sprint 2.
"""
import os

try:
    from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
except Exception:
    def _noop_decorator(*_a, **_k):
        def _wrap(fn):
            return fn
        return _wrap
    agent_model = agent_config = prompt_section = _noop_decorator

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from typing import AsyncGenerator, Literal, Sequence
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Exactly 3 decorators — cookbook mandate.
# @agent_model  : which model to use
# @agent_config : temperature only (the one allowed @agent_config parameter)
# @prompt_section : the full system prompt
# ---------------------------------------------------------------------------

@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return os.environ.get("AGENT_MODEL", "sap/anthropic--claude-4.5-sonnet")


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls response randomness (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The agent's role, rules, and output format",
)
def get_system_prompt() -> str:
    return """You are the [Agent Name] agent, an AI assistant built on SAP BTP.

## MANDATORY RULES
1. Never fabricate SAP document numbers, amounts, or statuses — retrieve live data first.
2. Set top=100 on every tool call that accepts it (prevents context overflow on large datasets).
3. Present both benefits AND costs before stating a net figure — never partial analysis.
4. Never execute write or delete operations on SAP systems — advisory only.
5. When data is missing, state this explicitly; continue with partial simulation + disclaimer.
6. End every financial output with: "These are estimates based on available SAP data. Validate with your finance team before acting."

## Role
[Replace this with your domain-specific agent role and workflow instructions.]

Always call tools for data and numbers — never compute values yourself. If a tool returns an
error, report it plainly without inventing a result."""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(
            model=get_model_name(),
            temperature=get_temperature(),
        )
        self._system_prompt = get_system_prompt()

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Thinking...",
        }
        try:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
            graph = create_agent(
                self.llm,
                tools=list(tools or []),
                system_prompt=self._system_prompt,
                checkpointer=checkpointer,
            )
            config = {"configurable": {"thread_id": context_id}}
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=query)]}, config
            )
            messages = result.get("messages", []) if isinstance(result, dict) else []
            content = ""
            for msg in reversed(messages):
                text = getattr(msg, "content", "") or ""
                if isinstance(text, list):
                    text = "".join(b.get("text", "") for b in text if isinstance(b, dict))
                if text.strip():
                    content = text
                    break
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": content or "No response.",
            }
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Agent error")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "An error occurred. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(status="error", message=last.get("content", "Unknown error"))
