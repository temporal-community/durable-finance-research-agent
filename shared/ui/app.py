"""Workshop test UI (port 8000). Module 1 and 2 run the learner's agent in a subprocess.
Module 3 starts, watches and signals the durable Workflow. SAMPLE DATA, not financial advice."""
import asyncio
import os
import socket
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from temporalio.client import Client

ROOT = Path(os.environ.get("WORKSHOP_ROOT", Path(__file__).resolve().parents[2]))
VARIANT = os.environ.get("WORKSHOP_VARIANT", "exercise")  # exercise or solution
TEMPORAL = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
UI_URL = os.environ.get("TEMPORAL_UI_URL", "http://localhost:8233")
TASK_QUEUE = "finance-research-tq"
MODULES = {1: "01-strands-agent-basics", 2: "02-strands-finance-research-agent", 3: "03-durable-strands-agent"}

def agent_env() -> dict:
    """Environment for the learner's agent subprocess. Routes LLM traffic through the network plane
    (so the control panel can cut it) when the proxy is up. Local traffic bypasses it via NO_PROXY."""
    env = dict(os.environ)
    with socket.socket() as sock:
        sock.settimeout(0.3)
        proxy_up = sock.connect_ex(("127.0.0.1", 8888)) == 0
    if proxy_up:
        proxy = "http://127.0.0.1:8888"
        env.update(HTTP_PROXY=proxy, HTTPS_PROXY=proxy, NO_PROXY="127.0.0.1,localhost")
        for bundle in (ROOT / ".run" / "ca-bundle.pem", Path("/etc/ssl/certs/ca-certificates.crt")):
            if bundle.exists():
                env.update(SSL_CERT_FILE=str(bundle), REQUESTS_CA_BUNDLE=str(bundle))
                break
    return env


app = FastAPI(title="Workshop UI")
_client: Client | None = None


async def client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(TEMPORAL)
    return _client


class Run(BaseModel):
    module: int
    prompt: str


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/config")
def config():
    return {"variant": VARIANT, "temporal_ui": UI_URL}


@app.post("/api/run")
async def run(body: Run):
    if body.module not in MODULES:
        raise HTTPException(400, "module must be 1, 2 or 3")
    if body.module == 3:
        wf_id = f"research-{uuid.uuid4().hex[:8]}"
        try:
            await (await client()).start_workflow("ResearchWorkflow", body.prompt, id=wf_id, task_queue=TASK_QUEUE)
        except Exception as e:
            raise HTTPException(502, f"Cannot reach Temporal at {TEMPORAL}: {e}")
        return {"workflow_id": wf_id, "link": f"{UI_URL}/namespaces/default/workflows/{wf_id}" if UI_URL else None}
    cwd = ROOT / "modules" / MODULES[body.module] / VARIANT
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "run.py", body.prompt, cwd=cwd, env=agent_env(),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError:
        proc.kill()
        return {"output": "Timed out after 180s. Is the LLM gateway cut? A plain script gives up; a Workflow keeps retrying."}
    return {"output": out.decode(errors="replace"), "exit_code": proc.returncode}


@app.get("/api/workflow/{wf_id}")
async def workflow_state(wf_id: str):
    handle = (await client()).get_workflow_handle(wf_id)
    desc = await handle.describe()
    state = {"workflow_id": wf_id, "run_status": desc.status.name if desc.status else None,
             "link": f"{UI_URL}/namespaces/default/workflows/{wf_id}" if UI_URL else None}
    if state["run_status"] == "RUNNING":
        try:
            state["status"] = await handle.query("status")
            state["memo"] = await handle.query("memo")
        except Exception:
            state["status"] = "starting"
    elif state["run_status"] == "COMPLETED":
        result = await handle.result()
        state.update(status=result["outcome"], memo=result["memo"])
    return state


@app.post("/api/workflow/{wf_id}/{action}")
async def decide(wf_id: str, action: str):
    if action not in ("approve", "reject"):
        raise HTTPException(400, "action must be approve or reject")
    await (await client()).get_workflow_handle(wf_id).signal(action)
    return {"ok": True}
