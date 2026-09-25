"""Chat providers built from Settings, for the commands that let the user pick the model."""
from swiss_grounding.config import Settings
from swiss_grounding.corpus.providers import AnthropicLLM, ApertusLLM, LLMProvider, OpenAILLM


def apertus_llm(settings: Settings, *, timeout_seconds: float | None = None, max_retries: int = 2) -> ApertusLLM:
    if not settings.apertus_api_key:
        raise ValueError("APERTUS_API_KEY is not set")
    return ApertusLLM(settings.apertus_api_key, base_url=settings.apertus_base_url, model=settings.apertus_model,
                      timeout_seconds=timeout_seconds or settings.apertus_timeout_seconds, max_retries=max_retries,
                      tokens_per_minute=(settings.apertus_input_tokens_per_minute, settings.apertus_output_tokens_per_minute))


def eval_model(settings: Settings) -> str:
    """The model that writes eval labels and generated questions (EVAL_LLM_PROVIDER), no key needed."""
    provider = settings.eval_llm_provider
    if provider == "apertus":
        return settings.apertus_model
    if provider == "anthropic":
        return settings.corpus_anthropic_model
    return settings.corpus_doc_model


def eval_llm(settings: Settings) -> tuple[LLMProvider, str]:
    """The provider and model that write eval labels and generated questions (EVAL_LLM_PROVIDER)."""
    provider = settings.eval_llm_provider
    model = eval_model(settings)
    if provider == "apertus":
        return apertus_llm(settings), model
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set (EVAL_LLM_PROVIDER=anthropic)")
        return AnthropicLLM(settings.anthropic_api_key, settings.corpus_anthropic_model), model
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set (EVAL_LLM_PROVIDER=openai)")
    return OpenAILLM(settings.openai_api_key), model
