import pytest

from swiss_grounding.config import Settings
from swiss_grounding.corpus.llm_factory import apertus_llm, eval_llm, eval_model
from swiss_grounding.corpus.providers import AnthropicLLM, ApertusLLM, OpenAILLM


def _settings(**overrides) -> Settings:
    return Settings(**{"database_url": "postgresql://x", "apertus_api_key": "k", "_env_file": None, **overrides})


def test_apertus_llm_uses_the_configured_model():
    llm = apertus_llm(_settings(apertus_model="swiss-ai/Apertus-v1.5-8B"))
    assert isinstance(llm, ApertusLLM) and llm.model == "swiss-ai/Apertus-v1.5-8B"


def test_eval_llm_defaults_to_openai_with_the_doc_model():
    llm, model = eval_llm(_settings(openai_api_key="o"))
    assert isinstance(llm, OpenAILLM) and model == "gpt-5-mini"


def test_eval_llm_can_be_apertus():
    llm, model = eval_llm(_settings(eval_llm_provider="apertus"))
    assert isinstance(llm, ApertusLLM) and model == "swiss-ai/Apertus-v1.5-70B"


def test_eval_llm_can_be_anthropic():
    llm, model = eval_llm(_settings(eval_llm_provider="anthropic", anthropic_api_key="a"))
    assert isinstance(llm, AnthropicLLM) and model == "claude-haiku-4-5-20251001"


def test_eval_llm_names_the_missing_key():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        eval_llm(_settings(openai_api_key=None))


def test_eval_model_needs_no_keys_and_matches_eval_llm():
    assert eval_model(_settings(openai_api_key=None)) == "gpt-5-mini"
    assert eval_model(_settings(eval_llm_provider="apertus", apertus_api_key=None)) == "swiss-ai/Apertus-v1.5-70B"
    assert eval_model(_settings(eval_llm_provider="anthropic", anthropic_api_key=None)) == "claude-haiku-4-5-20251001"
