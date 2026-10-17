"""Mock finance API. SAMPLE DATA ONLY: invented tickers for private companies, invented numbers, not financial advice."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Mock Finance API (sample data)")

DISCLAIMER = "DEMO ONLY. SAMPLE DATA. The ticker and company are not publicly listed; all numbers, filings and news are invented. Not financial advice."

# market_cap_b is billions, in the same currency as the quote ("currency"). All values are invented.
# None of these companies is publicly listed; the tickers are invented.
QUOTES = {
    "TWS": {"name": "TrainWithShubham", "currency": "INR", "price": 1412.40, "change_pct": 1.8, "pe": 27.2, "market_cap_b": 9.2},
    "KAVERI": {"name": "Kaveri Labs", "currency": "USD", "price": 287.15, "change_pct": -0.6, "pe": 34.9, "market_cap_b": 26.5},
    "CLOUD": {"name": "CloudAdhar", "currency": "INR", "price": 364.02, "change_pct": 0.3, "pe": 22.4, "market_cap_b": 1.1},
}
FILINGS = {
    "TWS": [{"form": "Investor Update", "period": "FY2025", "highlight": "Revenue up 14% year over year; learner community at a record."}],
    "KAVERI": [{"form": "Investor Update", "period": "Q2 2026", "highlight": "Usage up 30%; gross margin steady; customer concentration noted as a general risk."}],
    "CLOUD": [{"form": "Investor Update", "period": "FY2025", "highlight": "Revenue up 9%; training lab capacity expanded; hiring steady."}],
}
NEWS = {
    "TWS": [{"headline": "TrainWithShubham opens a new DevOps cohort", "date": "2026-09-30"}],
    "KAVERI": [{"headline": "Kaveri Labs announces a community workshop series", "date": "2026-10-05"},
              {"headline": "Kaveri Labs publishes a new product release", "date": "2026-10-08"}],
    "CLOUD": [{"headline": "CloudAdhar opens a new training lab", "date": "2026-10-02"}],
}

# fault mode: ok | unavailable (503) | rate_limited (429 + Retry-After)
STATE = {"fault": os.environ.get("MOCK_FAULT", "ok")}
RETRY_AFTER_SECONDS = 2


class Fault(BaseModel):
    mode: str


def _gate():
    if STATE["fault"] == "unavailable":
        raise HTTPException(503, "Market data provider unavailable")
    if STATE["fault"] == "rate_limited":
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429,
                            headers={"Retry-After": str(RETRY_AFTER_SECONDS)})
    return None


def _lookup(table, ticker):
    t = ticker.upper()
    if t not in table:
        raise HTTPException(404, f"Unknown ticker '{ticker}'")
    return t


@app.get("/healthz")
def healthz():
    return {"ok": True, "fault": STATE["fault"]}


@app.get("/quote/{ticker}")
def quote(ticker: str):
    if (r := _gate()):
        return r
    t = _lookup(QUOTES, ticker)
    return {"ticker": t, **QUOTES[t], "disclaimer": DISCLAIMER}


@app.get("/filings/{ticker}")
def filings(ticker: str):
    if (r := _gate()):
        return r
    t = _lookup(FILINGS, ticker)
    return {"ticker": t, "filings": FILINGS[t], "disclaimer": DISCLAIMER}


@app.get("/news/{ticker}")
def news(ticker: str):
    if (r := _gate()):
        return r
    t = _lookup(NEWS, ticker)
    return {"ticker": t, "news": NEWS[t], "disclaimer": DISCLAIMER}


@app.get("/admin/fault")
def get_fault():
    return STATE


@app.post("/admin/fault")
def set_fault(f: Fault):
    if f.mode not in ("ok", "unavailable", "rate_limited"):
        raise HTTPException(400, "mode must be ok, unavailable or rate_limited")
    STATE["fault"] = f.mode
    return STATE
