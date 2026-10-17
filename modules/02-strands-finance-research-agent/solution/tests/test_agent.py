import os

os.environ.setdefault("LITELLM_API_KEY", "test-key")
os.environ.setdefault("LITELLM_API_BASE", "http://127.0.0.1:4000")

import tools


def test_tools_call_the_right_paths(monkeypatch):
    seen = []
    monkeypatch.setattr(tools, "http_get", lambda p: seen.append(p) or {"ok": True})
    tools.get_quote("TWS"); tools.get_filings("TWS"); tools.get_news("TWS")
    assert seen == ["/quote/TWS", "/filings/TWS", "/news/TWS"]


def test_agent_has_all_tools():
    from agent import build_agent
    assert {"get_quote", "get_filings", "get_news", "percent_change"} <= set(build_agent().tool_names)


def test_prompt_covers_requirements():
    from agent import SYSTEM_PROMPT
    p = SYSTEM_PROMPT.lower()
    for needle in ("sources", "sample data", "demo only", "financial advice", "get_quote", "get_filings", "get_news"):
        assert needle in p, needle
