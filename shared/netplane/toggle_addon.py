"""mitmproxy addon: returns 503 for the LLM gateway when the 'llm' service is toggled off.

State file (NETPLANE_STATE, default shared/netplane/state.json): {"kill_all": false, "services": {"llm": true}}
true means ALLOWED. LLM hosts come from NETPLANE_LLM_HOSTS (comma separated) or the host in LITELLM_API_BASE.
A 503 makes Temporal activities retry instead of fail.
"""
import json
import os
from urllib.parse import urlparse

from mitmproxy import http

STATE_FILE = os.environ.get("NETPLANE_STATE", os.path.join(os.path.dirname(__file__), "state.json"))


def _llm_hosts():
    hosts = [h.strip() for h in os.environ.get("NETPLANE_LLM_HOSTS", "").split(",") if h.strip()]
    base = os.environ.get("LITELLM_API_BASE", "")
    if base and (h := urlparse(base).hostname):
        hosts.append(h)
    return hosts or ["api.openai.com"]


def _load():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"kill_all": False, "services": {"llm": True}}


def request(flow: http.HTTPFlow) -> None:
    state = _load()
    host = flow.request.pretty_host
    blocked = state.get("kill_all") or (
        not state.get("services", {}).get("llm", True) and host in _llm_hosts()
    )
    if blocked:
        flow.response = http.Response.make(
            503, b"[Workshop proxy] LLM gateway is currently disabled.", {"Content-Type": "text/plain"}
        )
