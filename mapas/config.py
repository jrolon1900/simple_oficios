"""Shared model configuration for every agent.

Any OpenAI-compatible provider works. Production (Vercel): set LLM_API_KEY, LLM_BASE_URL and
LLM_MODEL as environment variables. Local development can keep using FreeLLMAPI through the
FREELLM_* variables, which are the fallback.
"""
import os

from dotenv import load_dotenv
from strands.models.openai import OpenAIModel

load_dotenv()


def get_model() -> OpenAIModel:
    api_key = os.getenv("LLM_API_KEY") or os.environ["FREELLM_API_KEY"]
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("FREELLM_BASE_URL", "http://localhost:3001/v1")
    model_id = os.getenv("LLM_MODEL") or os.getenv("FREELLM_MODEL", "auto")
    return OpenAIModel(
        client_args={"api_key": api_key, "base_url": base_url},
        model_id=model_id,
        params={"temperature": 0.3, "max_tokens": 1024},
    )
