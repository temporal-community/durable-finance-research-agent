"""Send the approval decision: uv run python decide.py approve|reject <workflow-id>"""
import argparse
import asyncio
import os

from temporalio.client import Client

from workflow import ResearchWorkflow


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["approve", "reject"])
    ap.add_argument("workflow_id")
    a = ap.parse_args()
    action, wf_id = a.action, a.workflow_id
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    handle = client.get_workflow_handle(wf_id)
    await handle.signal(ResearchWorkflow.approve if action == "approve" else ResearchWorkflow.reject)
    print(f"Sent {action} to {wf_id}")


if __name__ == "__main__":
    asyncio.run(main())
