import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.contrib.strands import TemporalAgent
from temporalio.contrib.strands.workflow import activity_as_tool
from strands import tool
from strands.hooks import AfterToolCallEvent, HookProvider

with workflow.unsafe.imports_passed_through():
    from activities import get_filings, get_news, get_quote, publish_memo
    from prompts import SYSTEM_PROMPT

DEFAULT_APPROVAL_TIMEOUT_SECONDS = 4 * 3600
TOOL_RETRY = RetryPolicy(initial_interval=timedelta(seconds=1), maximum_interval=timedelta(seconds=10))


@tool
def percent_change(old: float, new: float) -> str:
    """Return the percent change from old to new, to one decimal place."""
    # Pure computation, so it runs inline in the Workflow. No activity needed.
    return f"{(new - old) / old * 100:.1f}%" if old else "n/a (old value is zero)"


class ToolErrorReasons(HookProvider):
    """Provided, you do not write this. Gives the model the real reason a tool failed (Strands alone sees "Activity task failed")."""

    def register_hooks(self, registry, **kwargs) -> None:
        registry.add_callback(AfterToolCallEvent, self._explain)

    def _explain(self, event: AfterToolCallEvent) -> None:
        cause = getattr(event.exception, "__cause__", None)
        if isinstance(cause, ApplicationError):
            event.result = {
                "status": "error",
                "toolUseId": event.tool_use["toolUseId"],
                "content": [{"text": f"Error: {cause.message}"}],
            }


@workflow.defn
class ResearchWorkflow:
    def __init__(self) -> None:
        self._decision: str | None = None
        self._status = "researching"
        self._memo = ""

    @workflow.signal
    def approve(self) -> None:
        self._decide("approved")

    @workflow.signal
    def reject(self) -> None:
        self._decide("rejected")

    def _decide(self, decision: str) -> None:
        # Only a memo that is waiting for review can be decided, and the first decision wins.
        if self._status == "awaiting_approval" and self._decision is None:
            self._decision = decision
        else:
            workflow.logger.warning("Ignoring %s: status is %s", decision, self._status)

    @workflow.query
    def status(self) -> str:
        return self._status

    @workflow.query
    def memo(self) -> str:
        return self._memo

    @workflow.run
    async def run(self, prompt: str, approval_timeout_seconds: int = DEFAULT_APPROVAL_TIMEOUT_SECONDS) -> dict:
        # Bounded tool retries: after 2 minutes the model is told the data is missing instead of hanging.
        tool_opts = dict(
            start_to_close_timeout=timedelta(seconds=15),
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=TOOL_RETRY,
        )
        agent = TemporalAgent(
            model="litellm",
            # No retry_policy: model calls retry with Temporal's default (unbounded) backoff, so an LLM outage
            # leaves the Workflow Running and the model Activity retrying. That is the Break It scene.
            start_to_close_timeout=timedelta(seconds=90),
            system_prompt=SYSTEM_PROMPT,
            tools=[
                activity_as_tool(get_quote, **tool_opts),
                activity_as_tool(get_filings, **tool_opts),
                activity_as_tool(get_news, **tool_opts),
                percent_change,
            ],
            hooks=[ToolErrorReasons()],
        )
        self._memo = str(await agent.invoke_async(prompt))

        # TODO 2: uncomment the block below. The Workflow waits for a human decision, and gives up after the timeout.
        # self._status = "awaiting_approval"
        # try:
        #     await workflow.wait_condition(lambda: self._decision is not None, timeout=timedelta(seconds=approval_timeout_seconds))
        # except asyncio.TimeoutError:
        #     self._status = "escalated"
        #     return {"outcome": "escalated", "memo": self._memo}
        # if self._decision == "rejected":
        #     self._status = "rejected"
        #     return {"outcome": "rejected", "memo": self._memo}

        key = ""
        # TODO 3: uncomment the line below. The Workflow ID is the same on every retry and replay, so it dedupes the publish.
        # key = workflow.info().workflow_id
        result = await workflow.execute_activity(
            publish_memo, args=[self._memo, key], start_to_close_timeout=timedelta(seconds=30)
        )
        self._status = result
        return {"outcome": result, "memo": self._memo}
