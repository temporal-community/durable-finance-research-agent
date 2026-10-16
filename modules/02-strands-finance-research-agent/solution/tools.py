"""Finance tools backed by the mock finance API. SAMPLE DATA, not financial advice."""
import os

import httpx
from strands import tool

API = os.environ.get("MARKET_DATA_URL", "http://127.0.0.1:8001")


def http_get(path: str) -> dict:
    """GET from the market data API. Raises httpx.HTTPStatusError on 4xx/5xx."""
    r = httpx.get(f"{API}{path}", timeout=10)
    r.raise_for_status()
    return r.json()


@tool
def get_quote(ticker: str) -> dict:
    """Get the latest price, change, P/E and market cap for a ticker (sample data)."""
    return http_get(f"/quote/{ticker}")


@tool
def get_filings(ticker: str) -> dict:
    """Get recent SEC-style filing highlights for a ticker (sample data)."""
    return http_get(f"/filings/{ticker}")


@tool
def get_news(ticker: str) -> dict:
    """Get recent news headlines for a ticker (sample data)."""
    return http_get(f"/news/{ticker}")


@tool
def percent_change(old: float, new: float) -> str:
    """Return the percent change from old to new, to one decimal place."""
    return f"{(new - old) / old * 100:.1f}%"
