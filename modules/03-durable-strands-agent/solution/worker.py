import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from activities import get_filings, get_news, get_quote, publish_memo
from config import TASK_QUEUE
from model import make_model, require_env
from workflow import ResearchWorkflow


async def main() -> None:
    require_env()
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[StrandsPlugin(models={"litellm": make_model})],
    )
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ResearchWorkflow],
        activities=[get_quote, get_filings, get_news, publish_memo],
    )
    print(f"Worker started on task queue {TASK_QUEUE}. Ctrl+C to stop.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
