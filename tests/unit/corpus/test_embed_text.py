import pytest

from swiss_grounding.corpus.budget import cost_usd
from swiss_grounding.corpus.embed import MAX_EMBED_CHARS, embedding_text, estimate_embeddings


def test_embedding_text_joins_breadcrumb_description_and_text():
    assert embedding_text(["SR 220 OR", "Art. 336c"], "Kündigungsschutz", "1 Nach Ablauf") == \
        "SR 220 OR > Art. 336c\nKündigungsschutz\n1 Nach Ablauf"


def test_embedding_text_skips_empty_parts_and_truncates():
    assert embedding_text([], "", "x") == "x"
    assert len(embedding_text(["a"], "b", "c" * 20000)) == MAX_EMBED_CHARS


def test_estimate_embeddings_uses_the_batch_price_unless_told_otherwise():
    pending = [{"text": "x" * 300}, {"text": "y" * 600}]
    batch = estimate_embeddings(pending, "text-embedding-3-large")
    assert batch == pytest.approx(cost_usd("text-embedding-3-large", 300, 0))
    assert estimate_embeddings(pending, "text-embedding-3-large", batch=False) == pytest.approx(2 * batch)
