"""Network control panel (port 5050). Toggles the LLM gateway via the proxy state file
and the mock market-data API via its /admin/fault endpoint."""
import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

HERE = Path(__file__).parent
STATE_FILE = Path(os.environ.get("NETPLANE_STATE", HERE / "state.json"))
MOCK_API = os.environ.get("MOCK_API_URL", "http://127.0.0.1:8001")

app = FastAPI(title="Workshop network control panel")


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"kill_all": False, "services": {"llm": True}}


def write_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    os.replace(tmp, STATE_FILE)  # atomic, so the proxy never reads a half-written file


class Enabled(BaseModel):
    enabled: bool


class Mode(BaseModel):
    mode: str


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/state")
def get_state():
    state = read_state()
    try:
        fault = httpx.get(f"{MOCK_API}/admin/fault", timeout=2).json()["fault"]
    except Exception:
        fault = "unreachable"
    return {**state, "market_data_fault": fault}


@app.post("/api/llm")
def set_llm(body: Enabled):
    state = read_state()
    state.setdefault("services", {})["llm"] = body.enabled
    write_state(state)
    return {"ok": True, "llm": body.enabled}


@app.post("/api/market_data")
def set_market_data(body: Mode):
    if body.mode not in ("ok", "unavailable", "rate_limited"):
        raise HTTPException(400, "mode must be ok, unavailable or rate_limited")
    r = httpx.post(f"{MOCK_API}/admin/fault", json={"mode": body.mode}, timeout=2)
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()


@app.post("/api/kill_all")
def kill_all(body: Enabled):
    state = read_state()
    state["kill_all"] = body.enabled
    write_state(state)
    return {"ok": True, "kill_all": body.enabled}
