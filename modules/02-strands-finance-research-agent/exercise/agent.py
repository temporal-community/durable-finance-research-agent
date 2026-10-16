"""Module 2: a finance research agent. SAMPLE DATA, not financial advice."""
import os

from dotenv import load_dotenv
from strands import Agent
from strands.models.litellm import LiteLLMModel

from tools import get_filings, get_news, get_quote, percent_change

load_dotenv()

SYSTEM_PROMPT = ""
# TODO 2: uncomment the system prompt below (it replaces the empty one above). It sets the memo format, the source rules and the sample-data disclaimer.
# SYSTEM_PROMPT = """You are a research analyst on a fictional desk. All data is SAMPLE DATA and nothing you write is financial advice.
#
# Process: call get_quote, get_filings and get_news for the ticker before writing. Use percent_change for any arithmetic.
# Memo format (markdown): Summary (2 sentences), Valuation, Filings, News, Risks, Sources.
# Rules: cite every figure with its source tool in Sources; if a tool fails, say what is missing instead of guessing;
# never recommend buying or selling; end with "Sample data. Not financial advice." """


def build_agent() -> Agent:
    model = LiteLLMModel(
        client_args={
            "api_key": os.environ["LITELLM_API_KEY"],
            "api_base": os.environ["LITELLM_API_BASE"],
            "use_litellm_proxy": True,
        },
        model_id=os.environ.get("MODEL_ID", "gpt-4o"),
    )
    # TODO 3: uncomment the return. All four tools go to the agent.
    # return Agent(
    #     model=model,
    #     system_prompt=SYSTEM_PROMPT,
    #     tools=[get_quote, get_filings, get_news, percent_change],
    # )
    raise NotImplementedError("Uncomment the code above (TODO 3)")
