"""LangGraph ReAct agent — the core intelligence layer.

Uses langchain-openai ChatOpenAI pointed at SAP AI Core's OpenAI-compatible endpoint.
DO NOT switch to generative-ai-hub-sdk: it pins pydantic==2.10.6 which conflicts
with a2a-sdk>=0.2.7 (requires pydantic>=2.11.3).
"""
from __future__ import annotations

import json
import os
from typing import Any, AsyncIterable, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from app.config import is_mock_mode
from app.tools import get_tools


class ResponseFormat(BaseModel):
    """Structured output schema — maps directly to A2A TaskState."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


def get_llm():  # pragma: no cover
    """Build ChatOpenAI from AI Core service binding.

    Reads AICORE_SERVICE_KEY (local dev) or VCAP_SERVICES.aicore[0] (CF).
    Fetches an OAuth2 client-credentials token, then points ChatOpenAI at
    AI Core's /v2/inference/deployments OpenAI-compatible endpoint.
    """
    import httpx
    from langchain_openai import ChatOpenAI

    aicore_key = os.getenv("AICORE_SERVICE_KEY")
    if aicore_key:
        creds = json.loads(aicore_key)
    else:
        vcap = json.loads(os.getenv("VCAP_SERVICES", "{}"))
        bindings = vcap.get("aicore", [])
        if not bindings:
            raise RuntimeError(
                "No AI Core service binding. "
                "Set AICORE_SERVICE_KEY for local dev or bind an aicore service in CF."
            )
        creds = bindings[0]["credentials"]

    token_resp = httpx.post(
        creds["url"] + "/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(creds["clientid"], creds["clientsecret"]),
        timeout=30,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    api_url = creds["serviceurls"]["AI_API_URL"]
    model_name = os.getenv("AGENT_MODEL", "sap/anthropic--claude-4-5-sonnet")
    resource_group = os.getenv("AICORE_RESOURCE_GROUP", "default")

    return ChatOpenAI(
        model=model_name,
        base_url=f"{api_url}/v2/inference/deployments",
        api_key=access_token,
        max_tokens=4096,
        default_headers={"AI-Resource-Group": resource_group},
    )


SYSTEM_INSTRUCTION = """You are a [DOMAIN] assistant built on SAP BTP, powered by SAP AI Core.
You help [USER_ROLE] with [PRIMARY_TASK] by reading live data from SAP systems.

MANDATORY RULES:
1. [TODO: fill in domain-specific rule 1 — e.g. "Only answer about procurement data for the authenticated user's company code"]
2. [TODO: fill in domain-specific rule 2 — e.g. "When a purchase order is mentioned, always include its status and last change date"]
3. [TODO: fill in domain-specific rule 3]
4. Never execute write, update, or delete operations on SAP systems — advisory and read-only only.
5. When data is missing or unavailable, state that explicitly and label any estimates as estimates.
6. End every quantitative output with: "These are estimates based on available SAP data. Verify before making financial decisions."

When you complete the request, set status to "completed".
When you need more information from the user, set status to "input_required" and ask your question.
If an error occurs, set status to "error" and explain what went wrong.
"""

RESPONSE_FORMAT_INSTRUCTION = """Always respond using the ResponseFormat schema.
Set 'status' to indicate the task state and 'message' for your response text."""

_memory = MemorySaver()


class StarterKitAgent:
    """LangGraph ReAct agent with A2A-compatible response format.

    In mock mode (IBD_TESTING=1) the LLM and graph are never instantiated,
    so tests run fully offline without any credentials.
    """

    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self) -> None:
        self._mock = is_mock_mode()
        if not self._mock:  # pragma: no cover
            model = get_llm()
            self.graph = create_react_agent(
                model,
                tools=get_tools(),
                checkpointer=_memory,
                prompt=SYSTEM_INSTRUCTION,
                response_format=(RESPONSE_FORMAT_INSTRUCTION, ResponseFormat),
            )

    def invoke(self, query: str, session_id: str) -> dict[str, Any]:
        if self._mock:
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"[MOCK] Received: {query!r}. (IBD_TESTING=1 — no SAP calls)",
            }
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}  # pragma: no cover
        self.graph.invoke({"messages": [("user", query)]}, config)  # pragma: no cover
        return self._get_response(config)  # pragma: no cover

    async def stream(  # pragma: no cover
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        if self._mock:
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"[MOCK] Received: {query!r}. (IBD_TESTING=1 — no SAP calls)",
            }
            return
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        inputs = {"messages": [("user", query)]}

        for item in self.graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if isinstance(message, AIMessage) and message.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing your request...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Analyzing results...",
                }

        yield self._get_response(config)

    def _get_response(self, config: RunnableConfig) -> dict[str, Any]:  # pragma: no cover
        state = self.graph.get_state(config)
        structured = state.values.get("structured_response")

        if structured and isinstance(structured, ResponseFormat):
            if structured.status in ("input_required", "error"):
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured.message,
                }
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": structured.message,
            }

        messages = state.values.get("messages", [])
        if messages:
            last = messages[-1]
            if hasattr(last, "content"):
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": str(last.content),
                }

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": "I couldn't process your request. Could you rephrase?",
        }
