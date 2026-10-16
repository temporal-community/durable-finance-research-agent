"""Activities: every call that touches the outside world lives here, never in the Workflow."""
import os
from datetime import timedelta
from pathlib import Path

import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

API = os.environ.get("MARKET_DATA_URL", "http://127.0.0.1:8001")


def classify_http_error(resp: httpx.Response) -> None:
    """Turn a failed HTTP response into the right Temporal failure. Returns None on success."""
    # 404 is permanent, 429 carries the server's delay, 5xx is worth retrying. Until you do the TODO below,
    # every failure looks the same and Temporal retries all of them.
    # TODO 1: uncomment the block below.
    # if resp.status_code < 400:
    #     return
    # if resp.status_code == 404:
    #     raise ApplicationError(f"Unknown ticker: {resp.text}", type="UnknownTicker", non_retryable=True)
    # if resp.status_code == 429:
    #     try:
    #         delay = min(float(resp.headers.get("Retry-After", "1")), 30.0)
    #     except ValueError:  # HTTP-date form: fall back to a short fixed delay
    #         delay = 5.0
    #     raise ApplicationError("Rate limited", type="RateLimited", next_retry_delay=timedelta(seconds=delay))
    # if resp.status_code >= 500:
    #     raise ApplicationError(f"Market data error {resp.status_code}", type="MarketDataError")
    # raise ApplicationError(f"Bad request {resp.status_code}", type="BadRequest", non_retryable=True)
    resp.raise_for_status()


async def _get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API}{path}")
    classify_http_error(resp)
    return resp.json()


@activity.defn
async def get_quote(ticker: str) -> dict:
    """Get the latest price, change, P/E and market cap for a ticker (sample data)."""
    return await _get(f"/quote/{ticker}")


@activity.defn
async def get_filings(ticker: str) -> dict:
    """Get recent filing highlights for a ticker (sample data)."""
    return await _get(f"/filings/{ticker}")


@activity.defn
async def get_news(ticker: str) -> dict:
    """Get recent news headlines for a ticker (sample data)."""
    return await _get(f"/news/{ticker}")


@activity.defn
async def publish_memo(memo: str, idempotency_key: str) -> str:
    """Publish a memo once per idempotency key (dedupes within one key only). Stands in for an email or CMS call."""
    if not idempotency_key or "/" in idempotency_key or ".." in idempotency_key:
        raise ApplicationError("idempotency_key must be a plain, non-empty string", non_retryable=True)
    out = Path(os.environ.get("PUBLISH_DIR", "published"))
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / f".{idempotency_key}.{os.getpid()}.tmp"
    tmp.write_text(memo)
    try:
        os.link(tmp, out / f"{idempotency_key}.md")  # atomic: fails if this key was already published
    except FileExistsError:
        return "already-published"
    finally:
        tmp.unlink(missing_ok=True)
    return "published"
