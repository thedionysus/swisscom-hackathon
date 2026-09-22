"""Local topic classifier: the fallback when the caller supplies no topic (ADR 0004).

Uses the real bge-m3 embedder (already required by the rest of the suite, no API key
needed) rather than a fake one. A fake bag-of-hashed-tokens embedder would either share
no vocabulary with the category descriptions (every question would sit near the floor
for the wrong reason) or would have to be hand-tuned per test case, which proves nothing
about the classifier and everything about the fixture. The real embedder is the only
thing that gives these floor/margin numbers any meaning.

The embedder is a session-scoped fixture, not a module-level variable: a module-level
`build_embedder(...)` call pays the ~0.9s model-load cost at collection time for the
whole `tests/unit` directory, even for a run that never selects a test from this file
(e.g. `pytest tests/unit -k test_rrf`). A fixture only pays it when a test that requests
it is actually selected.
"""

import pytest

from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.topics import classify_topics


@pytest.fixture(scope="session")
def embedder():
    return build_embedder("sentence_transformers", model_name="BAAI/bge-m3", dim=1024)


@pytest.mark.parametrize(
    "question,expected",
    [
        ("How much is the dog tax?", {"dogs"}),
        ("When is cardboard collected?", {"waste"}),
        ("Who maintains the hiking trails?", {"hiking"}),
        ("Which cantonal rules apply to dogs on hiking trails?", {"dogs", "hiking"}),
    ],
)
def test_classifies_within_the_margin_band(question, expected, embedder):
    assert expected <= set(classify_topics(question, embedder))


def test_an_unrelated_question_filters_on_nothing(embedder):
    """Below the confidence floor, return no topics rather than the nearest by accident."""
    assert classify_topics("What is the capital of Peru?", embedder) == ()


def test_the_floor_no_longer_sits_on_the_cliff(embedder):
    """'Quellensteuer' (withholding tax) is a genuine, unambiguous taxes question that
    scores 0.4465 for `taxes` against this embedder — below the plan's original
    TOPIC_FLOOR of 0.45, which would have silently returned no topics for it. TOPIC_FLOOR
    was moved to 0.42 precisely so a real on-topic question this close to the old edge
    still classifies. This test fails again if TOPIC_FLOOR is moved back to 0.45.
    """
    assert {"taxes"} <= set(classify_topics("Quellensteuer", embedder))


def test_a_saturated_band_collapses_to_no_topics(embedder):
    """'Tell me about Hamlet' clears TOPIC_FLOOR (best score 0.4466, for `taxes`) but its
    margin band spans all ten categories once you lower the floor to admit it — the
    classifier has no real opinion, not ten. TOPIC_MAX_TOPICS is what actually keeps this
    question from being reported as classified once TOPIC_FLOOR alone lets it through.
    """
    assert classify_topics("Tell me about Hamlet", embedder) == ()


def test_an_ambiguous_on_topic_question_also_collapses(embedder):
    """'Wo ist das nächste Polizeirevier?' (where is the nearest police station) is a
    real Swiss-admin question, but its best score (0.4606) is spread almost evenly
    across eight of the ten categories. Reporting eight categories under a hard topic
    filter (Task 8) would exclude every untagged chunk just as one category would, while
    giving the caller no way to tell this apart from a confident narrow match — so this
    collapses to no filter too, the same as a genuinely unrelated question.
    """
    assert classify_topics("Wo ist das nächste Polizeirevier?", embedder) == ()


def test_empty_question_is_rejected(embedder):
    """Nothing to compare against category descriptions — a caller error, not a result."""
    with pytest.raises(ValueError):
        classify_topics("", embedder)
    with pytest.raises(ValueError):
        classify_topics("   ", embedder)
