"""The three causes of an empty result, told apart (ADR 0001, D2, ADR 0003).

A calling model has to act differently on each: an uncovered place means ask about a
different place, a date wipeout means move or drop the date, an uncovered subject means
ask about a different subject and do *not* answer from the on-path evidence that is
there. So the discrimination is the behaviour under test, not the wording -- except
where the wording asserts a fact the server cannot stand behind, which is the defect the
date cause exists to close and is asserted directly below.
"""

from datetime import date

import pytest

from swiss_grounding.retrieval.models import CoverageRow
from swiss_grounding.retrieval.no_evidence import no_evidence_cause, no_evidence_message

EMPTY_PATH = (
    CoverageRow(extent_id="CH", label="Switzerland", documents=0),
    CoverageRow(extent_id="CH-GE", label="Geneva", documents=0),
)
COVERED_PATH = (
    CoverageRow(extent_id="CH", label="Switzerland", documents=4),
    CoverageRow(extent_id="CH-ZH", label="Zurich", documents=1),
)


def test_an_uncovered_place_is_reported_as_a_place_problem():
    message = no_evidence_message("Geneva", EMPTY_PATH, topics=("dogs",))
    assert "Geneva" in message
    # The topic never got the chance to exclude anything, so naming it would send the
    # caller off to rephrase the subject when the subject was never the problem.
    assert "dogs" not in message


def test_a_covered_place_with_no_on_topic_chunk_is_reported_as_a_subject_problem():
    message = no_evidence_message("Zurich", COVERED_PATH, topics=("schools",))
    assert "schools" in message
    assert "Zurich" in message


def test_every_topic_is_named_so_the_caller_can_narrow_or_widen():
    message = no_evidence_message("Zurich", COVERED_PATH, topics=("dogs", "hiking"))
    assert "dogs" in message
    assert "hiking" in message


def test_the_two_causes_never_produce_the_same_message():
    assert (
        no_evidence_message("Zurich", EMPTY_PATH, topics=("schools",))
        != no_evidence_message("Zurich", COVERED_PATH, topics=("schools",))
    )


def test_an_empty_result_with_no_topic_filter_blames_no_topic():
    """Documents on the path that hold no chunks -- what `recontext` can leave behind --
    with nothing supplied to filter on. There is no subject to blame, so this reads as
    the place cause rather than inventing one."""
    message = no_evidence_message("Zurich", COVERED_PATH, topics=())
    assert message == no_evidence_message("Zurich", EMPTY_PATH, topics=())


@pytest.mark.parametrize("coverage", [EMPTY_PATH, COVERED_PATH])
@pytest.mark.parametrize("topics", [(), ("waste",)])
def test_the_message_always_names_the_place(coverage, topics):
    assert "Lugano" in no_evidence_message("Lugano", coverage, topics)

def test_each_arm_of_the_filter_is_read_from_what_drives_it():
    """`coverage` counts `status = 'current'` documents and applies no date, so it cannot
    see the `as_of` arm. Routing all three causes off it is what let a date wipeout be
    reported as an uncovered subject."""
    assert no_evidence_cause(EMPTY_PATH, topics=("waste",), as_of=date(2020, 1, 1)) == "place"
    assert no_evidence_cause(COVERED_PATH, topics=("waste",), as_of=date(2020, 1, 1)) == "date"
    assert no_evidence_cause(COVERED_PATH, topics=(), as_of=date(2020, 1, 1)) == "date"
    assert no_evidence_cause(COVERED_PATH, topics=("waste",), as_of=None) == "subject"
    assert no_evidence_cause(COVERED_PATH, topics=(), as_of=None) == "place"


def test_a_dated_query_on_a_covered_path_is_not_blamed_on_the_subject():
    """The reported defect: with every on-path document carrying `waste` and every one of
    them excluded by the date, the subject message said "none of them carry the topic
    waste" -- false, and it instructs a calling model to tell the user something untrue."""
    message = no_evidence_message("Zurich", COVERED_PATH, topics=("waste",), as_of=date(2020, 1, 1))
    assert "none of them carry the topic" not in message
    assert "this subject is not" not in message
    assert "2020-01-01" in message
    assert message != no_evidence_message("Zurich", COVERED_PATH, topics=("waste",))
    assert message != no_evidence_message("Zurich", EMPTY_PATH, topics=("waste",))


def test_the_dated_cause_sends_the_caller_to_the_date_and_not_to_the_topic():
    """The mirror of what the place message says about rephrasing the subject. A document
    the date excluded is not recovered by any change of topic, so offering the topic as
    the next move is the same misdirection in a different arm."""
    message = no_evidence_message("Zurich", COVERED_PATH, topics=("waste",), as_of=date(2020, 1, 1))
    assert "as_of" in message
    assert "topic will not bring back" in message


def test_a_dated_query_on_an_uncovered_place_is_still_a_place_problem():
    """Same reasoning as the topic cause: with no documents on the path at all, the date
    never got the chance to exclude anything, so blaming it would misdirect."""
    assert (
        no_evidence_message("Geneva", EMPTY_PATH, topics=("dogs",), as_of=date(2020, 1, 1))
        == no_evidence_message("Geneva", EMPTY_PATH, topics=("dogs",))
    )


def test_the_dated_cause_names_the_place_and_the_date_with_and_without_a_topic():
    for topics in ((), ("waste",)):
        message = no_evidence_message("Lugano", COVERED_PATH, topics=topics, as_of=date(2020, 1, 1))
        assert "Lugano" in message
        assert "2020-01-01" in message


def test_the_dated_cause_names_the_topic_only_as_one_it_may_well_carry():
    """Naming the topic is fine; blaming it is not. The date message mentions it to say
    the on-path documents may carry it and were excluded anyway."""
    message = no_evidence_message("Zurich", COVERED_PATH, topics=("waste",), as_of=date(2020, 1, 1))
    assert "waste" in message
    assert "may well carry the topic" in message
    assert "waste" not in no_evidence_message("Zurich", COVERED_PATH, topics=(), as_of=date(2020, 1, 1))


def test_the_three_causes_never_produce_the_same_message():
    place = no_evidence_message("Zurich", EMPTY_PATH, topics=("schools",))
    subject = no_evidence_message("Zurich", COVERED_PATH, topics=("schools",))
    dated = no_evidence_message("Zurich", COVERED_PATH, topics=("schools",), as_of=date(2020, 1, 1))
    assert len({place, subject, dated}) == 3


def test_documents_that_hold_no_chunks_read_as_the_subject_cause_when_a_topic_is_supplied():
    """A known gap, pinned rather than left silent (see `no_evidence_cause`). `CoverageRow`
    counts documents and nothing counts chunks, so a path whose documents hold no chunks
    is indistinguishable here from one whose chunks are all off-topic. Closing it needs a
    new `CoverageRow` field, which is out of scope; this test exists so the day someone
    adds that field, the behaviour they have to revisit is written down and fails here."""
    assert no_evidence_cause(COVERED_PATH, topics=("waste",), as_of=None) == "subject"


def test_the_dated_cause_only_advises_about_the_topic_when_one_was_applied():
    """Advice about a filter that was never in play is noise a calling model may act on."""
    with_topic = no_evidence_message("Zurich", COVERED_PATH, ("waste",), date(2020, 1, 1))
    without = no_evidence_message("Zurich", COVERED_PATH, (), date(2020, 1, 1))
    assert "narrowing the topic" in with_topic
    assert "topic" not in without
