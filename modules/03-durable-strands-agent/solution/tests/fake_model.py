"""Scripted model so tests need no network and no API key."""
import json

from strands.models import Model


class FakeModel(Model):
    seen: list = []  # every message list the model was given

    def __init__(self):
        self.config = {}

    def update_config(self, **kw):
        self.config.update(kw)

    def get_config(self):
        return self.config

    async def structured_output(self, *a, **k):
        raise NotImplementedError
        yield

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kw):
        FakeModel.seen.append(messages)
        used_tool = any("toolResult" in b for m in messages for b in m["content"])
        yield {"messageStart": {"role": "assistant"}}
        if not used_tool:
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "t1", "name": "get_quote"}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps({"ticker": "TWS"})}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": "## Summary\nTWS memo. Demo only. Invented sample data, not real. Not financial advice."}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}, "metrics": {"latencyMs": 1}}}
