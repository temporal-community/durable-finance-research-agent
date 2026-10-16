"""Start a research Workflow: uv run python start.py "Write a memo on GLBX" """
import argparse
import asyncio
import os
import uuid

from temporalio.client import Client

from config import TASK_QUEUE
from workflow import DEFAULT_APPROVAL_TIMEOUT_SECONDS, ResearchWorkflow


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--approval-timeout", type=int, default=DEFAULT_APPROVAL_TIMEOUT_SECONDS, help="seconds")
    a = ap.parse_args()
    prompt = " ".join(a.prompt) or "Write a research memo on ACME."
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    wf_id = f"research-{uuid.uuid4().hex[:8]}"
    await client.start_workflow(
        ResearchWorkflow.run, args=[prompt, a.approval_timeout], id=wf_id, task_queue=TASK_QUEUE
    )
    ui = os.environ.get("TEMPORAL_UI_URL", "http://localhost:8233")
    where = f"Temporal UI: {ui}/namespaces/default/workflows/{wf_id}" if ui else f"Find it in the Temporal UI tab: {wf_id}"
    print(f"Started {wf_id}\n{where}")
    print(f"Approve: just approve {wf_id}")


if __name__ == "__main__":
    asyncio.run(main())
