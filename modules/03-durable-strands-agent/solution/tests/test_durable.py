import asyncio
import uuid
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.contrib.strands import StrandsPlugin
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import Worker

import activities
from tests.fake_model import FakeModel
from workflow import ResearchWorkflow


# ---- TODO 1: error classification (pure function, no server) ----

def _classify(status, headers=None):
    with pytest.raises(ApplicationError) as e:
        activities.classify_http_error(
            httpx.Response(status, headers=headers or {}, text="x", request=httpx.Request("GET", "http://x"))
        )
    return e.value


def test_404_is_non_retryable():
    assert _classify(404).non_retryable is True


def test_429_honors_retry_after():
    err = _classify(429, {"Retry-After": "2"})
    assert err.non_retryable is False
    assert err.next_retry_delay == timedelta(seconds=2)


def test_503_is_retryable():
    assert _classify(503).non_retryable is False


# ---- Workflow tests (time-skipping server, scripted model, stubbed data activities) ----

@activity.defn(name="get_quote")
async def fake_quote(ticker: str) -> dict:
    """Get the latest price, change, P/E and market cap for a ticker (sample data)."""
    return {"ticker": ticker, "price": 1.0}


@activity.defn(name="get_filings")
async def fake_filings(ticker: str) -> dict:
    """Get recent filing highlights for a ticker (sample data)."""
    return {}


@activity.defn(name="get_news")
async def fake_news(ticker: str) -> dict:
    """Get recent news headlines for a ticker (sample data)."""
    return {}


@pytest.fixture
async def env():
    async with await WorkflowEnvironment.start_time_skipping() as e:
        yield e


async def _run(env, tmp_path, monkeypatch, body, quote=None):
    monkeypatch.setenv("PUBLISH_DIR", str(tmp_path))
    cfg = env.client.config()
    cfg["plugins"] = [StrandsPlugin(models={"litellm": FakeModel})]
    client = Client(**cfg)
    tq = f"tq-{uuid.uuid4().hex[:6]}"
    async with Worker(
        client, task_queue=tq, workflows=[ResearchWorkflow],
        activities=[quote or fake_quote, fake_filings, fake_news, activities.publish_memo],
    ):
        handle = await client.start_workflow(
            ResearchWorkflow.run, args=["memo on TWS", 3600], id=f"wf-{uuid.uuid4().hex[:6]}", task_queue=tq
        )
        return await body(handle)


async def _wait_status(handle, want, seconds=30):
    last = None
    for _ in range(seconds * 10):
        desc = await handle.describe()
        if desc.status != WorkflowExecutionStatus.RUNNING:
            raise AssertionError(f"workflow ended ({desc.status.name}) before status {want!r}; last seen: {last}")
        try:
            last = await handle.query(ResearchWorkflow.status)
            if last == want:
                return True
        except Exception as e:  # query fails until the first Workflow Task completes
            last = repr(e)
        await asyncio.sleep(0.1)
    raise AssertionError(f"never reached status {want!r}; last seen: {last}")


async def test_waits_for_approval_before_publishing(env, tmp_path, monkeypatch):
    async def body(handle):
        await _wait_status(handle, "awaiting_approval")
        assert list(tmp_path.iterdir()) == [], "nothing may be published before approval"
        await handle.signal(ResearchWorkflow.approve)
        return await handle.result()

    result = await _run(env, tmp_path, monkeypatch, body)
    assert result["outcome"] == "published"


async def test_publish_uses_workflow_id_as_idempotency_key(env, tmp_path, monkeypatch):
    async def body(handle):
        await _wait_status(handle, "awaiting_approval")
        await handle.signal(ResearchWorkflow.approve)
        await handle.result()
        return handle.id

    wf_id = await _run(env, tmp_path, monkeypatch, body)
    assert [p.name for p in tmp_path.iterdir()] == [f"{wf_id}.md"]


async def test_reject_does_not_publish(env, tmp_path, monkeypatch):
    async def body(handle):
        await _wait_status(handle, "awaiting_approval")
        await handle.signal(ResearchWorkflow.reject)
        return await handle.result()

    result = await _run(env, tmp_path, monkeypatch, body)
    assert result["outcome"] == "rejected" and list(tmp_path.iterdir()) == []


async def test_timeout_escalates_without_publishing(env, tmp_path, monkeypatch):
    async def body(handle):
        await _wait_status(handle, "awaiting_approval")
        return await handle.result()  # time-skipping server fast-forwards the approval timer

    result = await _run(env, tmp_path, monkeypatch, body)
    assert result["outcome"] == "escalated" and list(tmp_path.iterdir()) == []


@activity.defn(name="get_quote")
async def unknown_ticker(ticker: str) -> dict:
    """Get the latest price, change, P/E and market cap for a ticker (sample data)."""
    raise ApplicationError("Unknown ticker 'ZZZZ'", type="UnknownTicker", non_retryable=True)


async def test_unknown_ticker_reaches_the_model_with_its_reason(env, tmp_path, monkeypatch):
    FakeModel.seen.clear()

    async def body(handle):
        await _wait_status(handle, "awaiting_approval")  # the tool failure did not fail the Workflow
        await handle.signal(ResearchWorkflow.reject)
        await handle.result()

    await _run(env, tmp_path, monkeypatch, body, quote=unknown_ticker)
    assert "Unknown ticker 'ZZZZ'" in str(FakeModel.seen[-1])


@activity.defn(name="get_quote")
async def always_unavailable(ticker: str) -> dict:
    """Get the latest price, change, P/E and market cap for a ticker (sample data)."""
    raise ApplicationError("Market data error 503", type="MarketDataError")


async def test_exhausted_tool_retries_reach_the_model_with_the_last_failure(env, tmp_path, monkeypatch):
    FakeModel.seen.clear()

    async def body(handle):
        return await handle.result()  # the time-skipping server fast-forwards the retries, then the approval timer

    result = await _run(env, tmp_path, monkeypatch, body, quote=always_unavailable)
    assert result["outcome"] == "escalated"
    assert "Market data error 503" in str(FakeModel.seen[-1])  # the last failure, after the 2 minute cap


async def test_approve_before_review_is_ignored(env, tmp_path, monkeypatch):
    async def body(handle):
        await handle.signal(ResearchWorkflow.approve)  # sent while the agent is still researching
        await _wait_status(handle, "awaiting_approval")
        assert list(tmp_path.iterdir()) == []
        await handle.signal(ResearchWorkflow.reject)
        return await handle.result()

    assert (await _run(env, tmp_path, monkeypatch, body))["outcome"] == "rejected"


async def test_publish_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLISH_DIR", str(tmp_path))
    ae = ActivityEnvironment()
    assert await ae.run(activities.publish_memo, "memo", "k1") == "published"
    assert await ae.run(activities.publish_memo, "memo", "k1") == "already-published"
