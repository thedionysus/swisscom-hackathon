"""The causes of an empty result, told apart.

A calling model has to act differently on each: an uncovered extent means ask about a
different place, an `as_of` wipeout means move or drop the date, an uncovered topic means
ask about a different topic and do *not* answer from the on-path evidence that is there.

So the discrimination is the behaviour under test -- and so is the truth of the wording,
because every sentence here is one a calling model repeats to a user. Two reviews have
now found a message asserting something the server could not know. The routing input is
a census of what each arm of `search.FILTER` would have returned on its own, precisely so
that each claim is checked rather than inferred.
"""

from datetime import date

import pytest

from swiss_grounding.retrieval.no_evidence import no_evidence_cause, no_evidence_message
from swiss_grounding.retrieval.search import PathEvidence

AS_OF = date(2020, 1, 1)


def census(without_as_of=0, without_topics=0, earliest=date(1987, 1, 1)):
    """A `PathEvidence` reading. Each count is what one arm of `FILTER`, dropped on its
    own, would have returned; the defaults describe a path neither drop recovers."""
    return PathEvidence(
        chunks_without_as_of=without_as_of, chunks_without_topics=without_topics,
        earliest_valid_from=earliest,
    )


# Nothing retrievable on the path at all -- whether because no chunk is there, because
# `recontext` took the chunks and left the documents, or because every document on it is
# withdrawn. All three read identically here, which is the point: no single change to the
# request recovers any of them.
NOTHING_ON_PATH = census(without_as_of=0, without_topics=0, earliest=None)


# --- the extent arm -------------------------------------------------------------------

def test_an_uncovered_extent_is_reported_as_an_extent_problem():
    message = no_evidence_message("Geneva", NOTHING_ON_PATH, ("dogs",), None)
    assert "Geneva" in message
    # Neither other arm got the chance to exclude anything, so naming one would send the
    # caller off to rephrase a topic, or move a date, that was never the problem.
    assert "dogs" not in message


def test_a_dated_query_on_an_uncovered_extent_is_still_an_extent_problem():
    assert (
        no_evidence_message("Geneva", NOTHING_ON_PATH, ("dogs",), AS_OF)
        == no_evidence_message("Geneva", NOTHING_ON_PATH, ("dogs",), None)
    )


def test_documents_that_hold_no_chunks_are_an_extent_problem_whatever_else_was_asked():
    """The gap the previous commit documented instead of closing, now closed. `recontext`
    can leave documents on the path holding no chunks; the coverage signal counts
    documents and still calls the path covered, so the old routing blamed whichever of
    the other two arms happened to be in play. A chunk census sees it directly: nothing is
    retrievable there, so neither the topic nor the date can be at fault."""
    for topics in ((), ("waste",)):
        for as_of in (None, AS_OF):
            assert no_evidence_cause(NOTHING_ON_PATH, topics, as_of) == "extent"


def test_a_path_whose_chunks_are_all_unretrievable_is_an_extent_problem():
    """Chunks exist on the path but no arm can reach them -- every document withdrawn,
    say. Dropping the topic does not help and dropping the date does not help, so the
    honest report is the extent one, which claims only that nothing could be retrieved."""
    assert no_evidence_cause(census(without_as_of=0, without_topics=0),
                             ("waste",), AS_OF) == "extent"


# --- the topic arm --------------------------------------------------------------------

def test_a_covered_extent_with_no_on_topic_chunk_is_reported_as_a_topic_problem():
    message = no_evidence_message("Zurich", census(without_topics=4), ("schools",), None)
    assert "schools" in message
    assert "Zurich" in message


def test_every_topic_is_named_so_the_caller_can_narrow_or_widen():
    message = no_evidence_message("Zurich", census(without_topics=4), ("dogs", "hiking"), None)
    assert "dogs" in message
    assert "hiking" in message


def test_a_dated_query_the_topic_alone_empties_is_still_a_topic_problem():
    """THE CRITICAL DEFECT. No chunk on the path carries the topic, so the topic is the
    sole cause -- and it stays the sole cause when an `as_of` rides along. The previous
    routing returned "as_of" for any dated empty result on a covered path, so the server
    told the truth undated and asserted the opposite one query later."""
    undated = no_evidence_message("Zurich", census(without_as_of=0, without_topics=4),
                                  ("waste",), None)
    dated = no_evidence_message("Zurich", census(without_as_of=0, without_topics=4),
                                ("waste",), AS_OF)
    assert no_evidence_cause(census(without_as_of=0, without_topics=4), ("waste",), AS_OF) == "topic"
    assert dated == undated


# --- the as_of arm --------------------------------------------------------------------

def test_the_as_of_cause_needs_evidence_the_date_actually_excluded():
    """`as_of` is only the cause when dropping it would have returned something. That is
    what `chunks_without_as_of` counts, and it is the check whose absence let the message
    claim the on-path documents "may well carry the topic" when none of them did."""
    assert no_evidence_cause(census(without_as_of=3, without_topics=0), ("waste",), AS_OF) == "as_of"
    assert no_evidence_cause(census(without_as_of=0, without_topics=0), ("waste",), AS_OF) != "as_of"


def test_the_as_of_cause_is_unreachable_without_a_date():
    """No date was applied, so no date can have excluded anything, whatever the census."""
    assert no_evidence_cause(census(without_as_of=3, without_topics=0), ("waste",), None) != "as_of"


def test_the_as_of_message_claims_only_what_the_census_establishes():
    message = no_evidence_message("Zurich", census(without_as_of=3, without_topics=0),
                                  ("waste",), AS_OF)
    assert "2020-01-01" in message
    assert "waste" in message              # verified: on-topic chunks exist on the path
    assert "1987-01-01" in message         # the boundary this path can answer for
    assert "none of them carry the topic" not in message


def test_the_as_of_message_names_no_topic_when_none_was_applied():
    message = no_evidence_message("Zurich", census(without_as_of=3, without_topics=0), (), AS_OF)
    assert "topic" not in message
    assert "2020-01-01" in message


def test_the_as_of_message_says_so_when_the_path_records_no_date_at_all():
    """Then "try a different as_of" is false -- no date reaches this path -- and the only
    repair is to drop it. This is the live shape: 99 of 104 documents record no date."""
    message = no_evidence_message("Zurich", census(without_as_of=3, earliest=None), ("waste",), AS_OF)
    assert "None" not in message
    assert "no as_of can be answered" in message


# --- both arms ------------------------------------------------------------------------

def test_when_either_change_alone_would_help_the_message_says_so():
    """On-topic chunks the date excludes, and in-force chunks the topic excludes, with no
    chunk that is both. Naming one arm would be true but would hand the caller advice that
    stops short: either constraint alone is enough to recover evidence."""
    evidence = census(without_as_of=2, without_topics=5)
    assert no_evidence_cause(evidence, ("waste",), AS_OF) == "as_of_and_topic"
    message = no_evidence_message("Zurich", evidence, ("waste",), AS_OF)
    assert "waste" in message
    assert "2020-01-01" in message


# --- discrimination, and the contract ---------------------------------------------------

def test_the_four_causes_never_produce_the_same_message():
    messages = {
        no_evidence_message("Zurich", NOTHING_ON_PATH, ("waste",), AS_OF),
        no_evidence_message("Zurich", census(without_topics=4), ("waste",), None),
        no_evidence_message("Zurich", census(without_as_of=3), ("waste",), AS_OF),
        no_evidence_message("Zurich", census(without_as_of=2, without_topics=5), ("waste",), AS_OF),
    }
    assert len(messages) == 4


@pytest.mark.parametrize("evidence", [NOTHING_ON_PATH, census(without_topics=4), census(without_as_of=3)])
@pytest.mark.parametrize("topics", [(), ("waste",)])
@pytest.mark.parametrize("as_of", [None, AS_OF])
def test_the_message_always_names_the_place(evidence, topics, as_of):
    assert "Lugano" in no_evidence_message("Lugano", evidence, topics, as_of)


def test_as_of_is_a_required_argument():
    """A caller that forgets it must fail loudly rather than silently getting the routing
    back that could not see the date arm -- which is the defect this module has now had
    reported against it twice."""
    with pytest.raises(TypeError):
        no_evidence_message("Zurich", census(), ("waste",))
