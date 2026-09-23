import pytest

from swiss_grounding.corpus.topics import TOPIC_IDS, TOPICS, sr_prior


def test_twenty_topics_with_unique_ids():
    assert len(TOPICS) == 20
    assert len(TOPIC_IDS) == 20


@pytest.mark.parametrize("sr,article,expected", [
    ("220", 336, ("work",)),
    ("220", 270, ("housing",)),
    ("220", 1, ("business",)),
    ("220", None, ("business",)),
    ("832.10", None, ("health",)),
    ("831.10", None, ("social_security",)),
    ("814.600", None, ("waste",)),
    ("814.01", None, ("environment",)),
    ("142.20", None, ("residence",)),
    ("143.1", None, ("travel",)),
    ("161.1", None, ("politics",)),
    ("741.51", None, ("transport",)),
    ("455", None, ("animals",)),
    ("922.0", None, ("animals",)),
    ("921.0", None, ("environment",)),
    ("704", None, ("outdoors",)),
    ("211.412.11", None, ("building",)),
    ("210", None, ("family",)),
    ("999.9", None, ()),
])
def test_sr_prior_uses_the_longest_matching_prefix(sr, article, expected):
    assert sr_prior(sr, article) == expected
