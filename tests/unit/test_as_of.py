"""Refusing an `as_of` the index cannot answer for.

The index holds current consolidations only, so `as_of` can subtract and never reach
back. Asking what the law said in 2020 against an index whose oldest version entered
into force in 2023 is not a narrow question -- it is an unanswerable one, and the old
behaviour answered it anyway with whatever undated pages happened to survive the filter.

What is under test is the discrimination and what the message hands the caller to act
on: the boundary date itself. The wording around it is not.
"""

from datetime import date

import pytest

from swiss_grounding.retrieval.as_of import as_of_rejection, reachable_from

EARLIEST = date(2023, 9, 1)


def test_no_as_of_is_never_refused():
    assert as_of_rejection(None, EARLIEST) is None
    assert as_of_rejection(None, None) is None


def test_an_as_of_before_the_earliest_indexed_version_is_refused():
    rejection = as_of_rejection(date(2020, 1, 1), EARLIEST)
    assert rejection is not None
    message = rejection.message
    assert "2020-01-01" in message
    # The boundary date is the actionable part: it is what the caller moves the date to.
    assert "2023-09-01" in message


def test_the_earliest_indexed_version_itself_is_answerable():
    """The boundary is inclusive: a version that entered into force on a date was in
    force on that date, so refusing it would refuse a question the index can answer."""
    assert as_of_rejection(EARLIEST, EARLIEST) is None


def test_an_as_of_after_the_earliest_indexed_version_is_answerable():
    assert as_of_rejection(date(2026, 9, 16), EARLIEST) is None


def test_an_index_with_no_dated_document_refuses_every_as_of():
    """`earliest` is null when nothing indexed records a validity date. Then no date can
    be answered for at all, and the refusal may not name a boundary that does not exist."""
    rejection = as_of_rejection(date(2026, 9, 16), None)
    assert rejection is not None
    message = rejection.message
    assert "2026-09-16" in message
    assert "None" not in message


def test_the_two_refusals_do_not_share_a_message():
    """One is fixed by moving the date forward, the other only by dropping `as_of`, so a
    caller that cannot tell them apart cannot act on either."""
    assert (as_of_rejection(date(2020, 1, 1), EARLIEST).message
            != as_of_rejection(date(2020, 1, 1), None).message)


@pytest.mark.parametrize("earliest", [EARLIEST, None])
def test_a_refusal_always_names_the_date_that_was_asked_for(earliest):
    assert "2019-07-04" in as_of_rejection(date(2019, 7, 4), earliest).message


def test_a_refusal_carries_the_boundary_as_a_date_not_only_as_prose():
    """`QueryCore` renders the message; the `no_evidence` date branch needs the date
    itself. Handing back both from one place stops the two drifting apart."""
    rejection = as_of_rejection(date(2020, 1, 1), EARLIEST)
    assert rejection.earliest == EARLIEST
    assert as_of_rejection(date(2020, 1, 1), None).earliest is None


def test_reachable_from_names_the_boundary_when_there_is_one():
    assert "2023-09-01" in reachable_from(EARLIEST)


def test_reachable_from_refuses_to_promise_a_boundary_that_does_not_exist():
    """"Try a different as_of" is false when nothing on the path records a date at all.
    This is the live shape of the index, not a corner case."""
    sentence = reachable_from(None)
    assert "None" not in sentence
    assert "no as_of can be answered" in sentence
    assert sentence != reachable_from(EARLIEST)
