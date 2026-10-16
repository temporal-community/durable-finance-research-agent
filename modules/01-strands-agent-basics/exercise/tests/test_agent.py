import os

os.environ.setdefault("LITELLM_API_KEY", "test-key")
os.environ.setdefault("LITELLM_API_BASE", "http://127.0.0.1:4000")

from agent import build_agent, percent_change


def test_build_agent_has_tool_and_prompt():
    agent = build_agent()
    assert "percent_change" in agent.tool_names
    assert "sample data" in agent.system_prompt.lower()


def test_percent_change_tool():
    assert percent_change(old=100, new=110) == "10.0%"
