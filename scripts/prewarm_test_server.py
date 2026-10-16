"""Download the Temporal time-skipping test server once, so offline tests need no network afterwards."""
import asyncio

from temporalio.testing import WorkflowEnvironment


async def main() -> None:
    async with await WorkflowEnvironment.start_time_skipping():
        print("test server ready")


if __name__ == "__main__":
    asyncio.run(main())
