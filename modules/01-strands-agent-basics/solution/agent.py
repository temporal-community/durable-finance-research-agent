"""Module 1: a simple Strands agent. SAMPLE DATA workshop, not financial advice."""
import os

from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.litellm import LiteLLMModel

load_dotenv()

SYSTEM_PROMPT = (
    "You are a concise assistant on a research desk. Use tools for arithmetic. "
    "Everything here is sample data and not financial advice."
)


@tool
def percent_change(old: float, new: float) -> str:
    """Return the percent change from old to new, to one decimal place."""
    return f"{(new - old) / old * 100:.1f}%"


def build_agent() -> Agent:
    # LiteLLMModel pointed at the LiteLLM gateway, then the Agent.
    model = LiteLLMModel(
        client_args={
            "api_key": os.environ["LITELLM_API_KEY"],
            "api_base": os.environ["LITELLM_API_BASE"],
            "use_litellm_proxy": True,
        },
        model_id=os.environ.get("MODEL_ID", "gpt-4o"),
    )
    return Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=[percent_change])
