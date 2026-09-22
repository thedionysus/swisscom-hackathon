"""Local topic classifier: the fallback when the caller supplies no topic (ADR 0004).

Uses the real bge-m3 embedder (already required by the rest of the suite, no API key
needed) rather than a fake one. A fake bag-of-hashed-tokens embedder would either share
no vocabulary with the category descriptions (every question would sit near the floor
for the wrong reason) or would have to be hand-tuned per test case, which proves nothing
about the classifier and everything about the fixture. The real embedder is the only
thing that gives these floor/margin numbers any meaning.
"""

import pytest

from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.topics import classify_topics

embedder = build_embedder("sentence_transformers", model_name="BAAI/bge-m3", dim=1024)


@pytest.mark.parametrize(
    "question,expected",
    [
        ("How much is the dog tax?", {"dogs"}),
        ("When is cardboard collected?", {"waste"}),
        ("Who maintains the hiking trails?", {"hiking"}),
        ("Which cantonal rules apply to dogs on hiking trails?", {"dogs", "hiking"}),
    ],
)
def test_classifies_within_the_margin_band(question, expected):
    assert expected <= classify_topics(question, embedder)


def test_an_unrelated_question_filters_on_nothing():
    """Below the confidence floor, return no topics rather than the nearest by accident."""
    assert classify_topics("What is the capital of Peru?", embedder) == frozenset()
