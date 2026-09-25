from swiss_grounding.config import Settings
from swiss_grounding.corpus.llm_factory import apertus_llm
from swiss_grounding.corpus.providers import ApertusLLM


def _settings(**overrides) -> Settings:
    return Settings(**{"database_url": "postgresql://x", "apertus_api_key": "k", **overrides})


def test_apertus_llm_uses_the_configured_model():
    llm = apertus_llm(_settings(apertus_model="swiss-ai/Apertus-v1.5-8B"))
    assert isinstance(llm, ApertusLLM) and llm.model == "swiss-ai/Apertus-v1.5-8B"
