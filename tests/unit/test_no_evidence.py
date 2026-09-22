"""The two causes of an empty result, told apart (ADR 0001 composed with ADR 0003).

A calling model has to act differently on each: an uncovered place means ask about a
different place, an uncovered subject means ask about a different subject and do *not*
answer from the on-path evidence that is there. So the discrimination is the behaviour
under test, not the wording.
"""

import pytest

from swiss_grounding.retrieval.models import CoverageRow
from swiss_grounding.retrieval.no_evidence import no_evidence_message

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
