"""Builds the LLM client. Runs on the worker, so credentials never enter a Workflow."""
import os

from dotenv import load_dotenv
from strands.models.litellm import LiteLLMModel

load_dotenv()


def require_env() -> None:
    """Fail fast with a clear message instead of retrying a misconfigured model forever."""
    missing = [k for k in ("LITELLM_API_BASE", "LITELLM_API_KEY") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Set {', '.join(missing)} in .env (see .env.example), then restart.")


def make_model() -> LiteLLMModel:
    return LiteLLMModel(
        client_args={
            "api_key": os.environ["LITELLM_API_KEY"],
            "api_base": os.environ["LITELLM_API_BASE"],
            "use_litellm_proxy": True,
        },
        model_id=os.environ.get("MODEL_ID", "gpt-4o"),
    )
