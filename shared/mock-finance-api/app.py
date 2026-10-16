"""Mock finance API. SAMPLE DATA ONLY: fictional companies, made-up numbers, not financial advice."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Mock Finance API (sample data)")

DISCLAIMER = "SAMPLE DATA. Fictional company and numbers. Not financial advice."

QUOTES = {
    "ACME": {"name": "Acme Robotics", "price": 112.40, "change_pct": 1.8, "pe": 31.2, "market_cap_b": 48.0},
    "GLBX": {"name": "Globex Semiconductors", "price": 287.15, "change_pct": -0.6, "pe": 44.9, "market_cap_b": 210.5},
    "INIT": {"name": "Initech Cloud", "price": 64.02, "change_pct": 0.3, "pe": 22.4, "market_cap_b": 19.7},
}
FILINGS = {
    "ACME": [{"form": "10-K", "period": "FY2025", "highlight": "Revenue up 14% year over year; warehouse automation backlog at record."}],
    "GLBX": [{"form": "10-Q", "period": "Q2 2026", "highlight": "Data-center revenue up 52%; gross margin 71%; export-license risk noted."}],
    "INIT": [{"form": "10-K", "period": "FY2025", "highlight": "Net revenue retention 118%; one customer is 17% of revenue."}],
}
NEWS = {
    "ACME": [{"headline": "Acme opens second robotics plant", "date": "2026-09-30"}],
    "GLBX": [{"headline": "Globex announces next-generation accelerator", "date": "2026-10-05"},
             {"headline": "Regulators review Globex export licenses", "date": "2026-10-08"}],
    "INIT": [{"headline": "Initech wins government cloud contract", "date": "2026-10-02"}],
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
