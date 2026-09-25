"""Chat providers built from Settings, for the commands that let the user pick the model."""
from swiss_grounding.config import Settings
from swiss_grounding.corpus.providers import ApertusLLM


def apertus_llm(settings: Settings, *, timeout_seconds: float | None = None, max_retries: int = 2) -> ApertusLLM:
    if not settings.apertus_api_key:
        raise ValueError("APERTUS_API_KEY is not set")
    return ApertusLLM(settings.apertus_api_key, base_url=settings.apertus_base_url, model=settings.apertus_model,
                      timeout_seconds=timeout_seconds or settings.apertus_timeout_seconds, max_retries=max_retries)
