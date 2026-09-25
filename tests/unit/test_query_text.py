"""How a request's three text fields become the two queries retrieval runs.

These are the unit-level statement of the contract `swiss_search` now advertises: the
dense arm embeds the caller's English rendering, the lexical arm keeps the verbatim
question, and the response says which fields were used so a caller can tell a full
answer from a degraded one.

No embedder and no database: `build_search_query` is pure string work, and the point of
these tests is exactly which string ends up where. A test that went through the embedder
would be asserting a hash, which is the failure mode `tests/integration/test_topic_filter.py`
already warns about.
"""

import pytest

from swiss_grounding.retrieval.models import QueryRequest
from swiss_grounding.retrieval.query_text import QUERY_SEPARATOR, build_search_query
from swiss_grounding.retrieval.topics import topic_decided_by

QUESTION = "Darf mein Hund im Wald frei laufen?"
QUESTION_EN = "May my dog run off leash in the forest?"
TOPIC_EN = "leash rules for dogs in forests and on hiking trails"


def _request(**kwargs) -> QueryRequest:
    return QueryRequest(question=QUESTION, location="8003", **kwargs)


def test_the_dense_query_is_the_english_question_then_the_topic():
    """`question_en + topic_en` is what gets embedded."""
    query = build_search_query(_request(question_en=QUESTION_EN, topic_en=TOPIC_EN))
    assert query.dense == f"{QUESTION_EN}{QUERY_SEPARATOR}{TOPIC_EN}"
    assert query.fields == ("question_en", "topic_en")


def test_the_lexical_query_stays_the_verbatim_question():
    """The original-language text is what the keyword index is asked for, even
    when the caller also supplied English. If the lexical arm followed the dense one,
    every original-language term the caller typed would stop being searched for."""
    query = build_search_query(_request(question_en=QUESTION_EN, topic_en=TOPIC_EN))
    assert query.lexical == QUESTION
    assert query.lexical != query.dense


def test_an_absent_topic_leaves_the_english_question_alone():
    """No trailing separator, and no placeholder standing in for the missing field."""
    query = build_search_query(_request(question_en=QUESTION_EN))
    assert query.dense == QUESTION_EN
    assert query.fields == ("question_en",)


def test_an_absent_english_question_degrades_to_the_verbatim_one():
    """An un-updated client sends only `question`, and must still get a search
    rather than an error or an empty query vector."""
    query = build_search_query(_request())
    assert query.dense == QUESTION
    assert query.fields == ("question",)


def test_a_topic_supplied_without_an_english_question_is_still_embedded():
    """The caller said something English about the subject; the index is English. Using
    it costs nothing and the reported fields make the mixed-language join visible."""
    query = build_search_query(_request(topic_en=TOPIC_EN))
    assert query.dense == f"{QUESTION}{QUERY_SEPARATOR}{TOPIC_EN}"
    assert query.fields == ("question", "topic_en")


@pytest.mark.parametrize("blank", ["", "   ", "\n\t"])
def test_a_blank_english_field_counts_as_absent_and_says_so(blank):
    """A client that sends the key with nothing in it has supplied nothing. Embedding
    the blank would put a stray separator in the query text and, worse, would report
    `question_en` as used when the English query was never there. Reporting is the whole
    guard against a silent degrade, so it may not be the thing that lies."""
    query = build_search_query(_request(question_en=blank, topic_en=blank))
    assert query.dense == QUESTION
    assert query.fields == ("question",)


def test_surrounding_whitespace_never_reaches_the_join():
    query = build_search_query(_request(question_en=f"  {QUESTION_EN} ", topic_en=f"\n{TOPIC_EN}\t"))
    assert query.dense == f"{QUESTION_EN}{QUERY_SEPARATOR}{TOPIC_EN}"


def test_building_a_query_does_not_touch_the_request():
    """No mutation: the request is the caller's, and it is read twice -- once here and
    once by `resolve_topics`."""
    request = _request(question_en=f" {QUESTION_EN} ", topic_en=TOPIC_EN)
    build_search_query(request)
    assert request.question_en == f" {QUESTION_EN} "
    assert request.question == QUESTION
    assert request.topic_en == TOPIC_EN


# --- where the topic filter came from (decision 1 and 3) --------------------------------
#
# `categories_used` already says *what* was filtered on. This says *who decided it*, which
# is the only way a caller can tell a topic it stated from one the server guessed, and the
# only way anyone can see that a client is still on the deprecated `categories` field.


def test_caller_supplied_topics_are_reported_as_the_decider():
    assert topic_decided_by(_request(topics=("dogs",))) == "topics"


def test_the_deprecated_categories_field_is_reported_under_its_own_name():
    """It must not be reported as `topics`. A deprecated field that looks identical in
    the response is a deprecation nobody can act on."""
    assert topic_decided_by(_request(categories=("dogs",))) == "categories"


def test_topics_outrank_categories_in_the_report_as_well_as_in_the_filter():
    assert topic_decided_by(_request(topics=("dogs",), categories=("waste",))) == "topics"


def test_saying_nothing_is_reported_as_the_local_classifier():
    """Including the case where the classifier then declines: the caller still needs to
    know the server guessed rather than was told."""
    assert topic_decided_by(_request()) == "classifier"
