import logging

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InternalError, Part, TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from agent import SampleAgent
from mcp_providers.agw import get_mcp_tools

logger = logging.getLogger(__name__)


class AgentExecutor(A2AAgentExecutor):
    def __init__(self):
        self.agent = SampleAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        tools = []
        try:
            tools = await get_mcp_tools()
            if tools:
                logger.info("Loaded %d tool(s): %s", len(tools), [t.name for t in tools])
        except Exception as exc:
            logger.error("Failed to load tools: %s", exc)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        import time
        start = time.time()
        try:
            async for item in self.agent.stream(query, task.context_id, tools=tools):
                is_task_complete = item["is_task_complete"]
                require_user_input = item["require_user_input"]
                content = item["content"]

                if require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(content, task.context_id, task.id),
                        final=True,
                    )
                    break
                elif is_task_complete:
                    latency_ms = int((time.time() - start) * 1000)
                    logger.info(
                        "turn_complete context_id=%s latency_ms=%d prompt_tokens=0 completion_tokens=0",
                        task.context_id, latency_ms,
                    )
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))], name="agent-response"
                    )
                    await updater.complete()
                    break
                else:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(content, task.context_id, task.id),
                    )
        except Exception as exc:
            logger.exception("Agent execution error")
            raise ServerError(error=InternalError()) from exc

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())
