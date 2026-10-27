"""A2A protocol bridge — connects the LangGraph agent to the a2a-sdk request lifecycle."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)

from app.agent import StarterKitAgent


class AgentStarterKitExecutor(AgentExecutor):
    """Bridges the LangGraph StarterKitAgent to the A2A protocol."""

    def __init__(self) -> None:
        self.agent = StarterKitAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        user_input = context.get_user_input()
        task = context.current_task

        if not task:
            task = Task(
                id=context.task_id or str(uuid4()),
                contextId=context.context_id or str(uuid4()),
                status=TaskStatus(
                    state=TaskState.submitted,
                    timestamp=datetime.now().isoformat(),
                ),
            )
            event_queue.enqueue_event(task)

        response = self.agent.invoke(user_input, task.contextId)
        parts = [Part(root=TextPart(text=response["content"]))]
        task.status.timestamp = datetime.now().isoformat()

        if response["require_user_input"]:
            task.status.state = TaskState.input_required
            msg = Message(messageId=str(uuid4()), role=Role.agent, parts=parts)
            task.status.message = msg
            task.history = (task.history or []) + [msg]
        else:
            task.status.state = TaskState.completed
            task.status.message = None
            task.artifacts = (task.artifacts or []) + [
                Artifact(parts=parts, artifactId=str(uuid4()))
            ]

        event_queue.enqueue_event(task)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = context.current_task
        if task:
            task.status = TaskStatus(
                state=TaskState.canceled,
                timestamp=datetime.now().isoformat(),
            )
            event_queue.enqueue_event(task)
