"""Why `swiss_search` found nothing, told apart so a calling model can act on it.

`search.FILTER` has three exclusion arms, and an empty result means one of them emptied
it. Each arm comes from a different decision, and they compose (ADR 0003's consequences
say so explicitly):

- **The place is uncovered** (ADR 0001, the extent arm). Nothing on the extent path could
  be retrieved, whatever the subject and whatever the date. Neither of the other two arms
  got the chance to exclude anything, so naming one would misdirect the caller into
  rephrasing a subject, or moving a date, that was never the problem. The useful next
  move is a different place, or telling the user this place is not covered.
- **The date excluded everything** (D2, the `as_of` arm). Documents are indexed on the
  path and an `as_of` was supplied. The index holds current consolidations only, so a
  document that records no `valid_from` cannot be shown to have been in force on that
  date and is excluded -- and most of what is indexed records no `valid_from`. The useful
  next move is a different `as_of`, or none.
- **The subject is uncovered** (ADR 0003, the topic arm). Documents are indexed on the
  path, no date was asked for, and no chunk carries the question's topic. The place is
  fine; the index simply holds nothing on this subject for it. The useful next move is a
  different subject -- and explicitly *not* answering from the on-path evidence that is
  there, because a chunk that does not carry the topic is not evidence for this question.

Collapsing these into one sentence is what makes a caller guess, so each message names
its own cause, and only the topic one blames the topic. The coverage signal rides along
on all three responses either way: it reports what *is* indexed for each extent on the
path, and it is about places, not topics or dates.
"""

from collections.abc import Sequence
from datetime import date
from typing import Literal

from swiss_grounding.retrieval.models import CoverageRow

Cause = Literal["place", "date", "subject"]

# Kept as the opening clause of the place message rather than reworded, because it is
# the sentence this server has always returned for an uncovered place.
_PLACE = (
    "No indexed evidence for {label} or its parent jurisdictions. Nothing on that "
    "jurisdiction path could be retrieved at all, whatever the subject; the coverage "
    "signal in this response says which levels hold documents. Tell the user the place "
    "is not covered, or ask about a larger place -- rephrasing the subject will not help."
)

_SUBJECT = (
    "Documents are indexed on the jurisdiction path for {label}, but none of them carry "
    "the topic {topics}. The place is covered; this subject is not. Tell the user nothing "
    "on this subject is indexed for this place, or search again with a different topic. "
    "Do not answer from evidence on another subject."
)

# The mirror of `_PLACE`'s closing advice, for the arm `_PLACE` cannot speak for. Every
# sentence here is one the server can stand behind: it does not claim the date is the
# *only* thing that excluded these rows -- a topic may have been applied too, and telling
# the two apart would take a second query -- but a document the date excluded is not
# recovered by any change of topic, so pointing the caller at the topic is wrong either
# way. The undated-index asymmetry is spelled out because a caller who does not know
# that most of the corpus records no date reads an empty dated result as "this place has
# no law", which is the misreading D2 exists to stop.
_DATED = (
    "Documents are indexed on the jurisdiction path for {label}, but none of them were "
    "retrievable as at the as_of date {as_of}{topic_clause}. Only current consolidations "
    "are indexed, so a document that records no validity date cannot be shown to have "
    "been in force on {as_of} and is excluded -- which is most of what is indexed, "
    "including calendar records and municipal pages. {advice} Do not tell the user this "
    "place or this subject is uncovered -- tell them the index cannot answer as at that "
    "date here."
)
_DATED_TOPIC_CLAUSE = ", and they may well carry the topic {topics}"
# The topic sentence is dropped when no topic was applied, rather than left standing as
# advice about a filter that was never in play.
_DATED_TOPIC_ADVICE = (
    "Widening or narrowing the topic will not bring back a document the date excluded; a "
    "different as_of may, and searching without as_of shows what applies now."
)
_DATED_ADVICE = "A different as_of may help, and searching without as_of shows what applies now."


def no_evidence_cause(
    coverage: Sequence[CoverageRow], topics: Sequence[str], as_of: date | None,
) -> Cause:
    """Which of `search.FILTER`'s three arms to report for an empty result.

    Each arm is read from the thing that drives it -- the extent arm from `coverage`, the
    `as_of` arm from `as_of`, the topic arm from `topics` -- and deliberately not inferred
    from `coverage` alone. `coverage.COUNTS_SQL` counts `status = 'current'` documents and
    applies no date at all, so the coverage signal structurally cannot see the `as_of`
    arm; inferring from it reported a date wipeout as an uncovered subject, telling a
    calling model to say the index holds nothing on a subject it holds plenty on.

    The extent arm is tested first because it dominates: with nothing retrievable on the
    path, neither the date nor the topic got the chance to exclude anything, so blaming
    either would misdirect. The date arm is tested before the topic arm because a topic
    change cannot recover a row the date excluded, so the topic is never the move to
    offer while a date is in play.

    **A known gap, not an oversight.** Documents on the path that hold no chunks -- what
    `recontext` can leave behind -- look identical here to documents whose chunks are all
    off-topic, because `CoverageRow` counts documents and nothing counts chunks. With no
    topic supplied that state reads as `place`, which is right. With a topic supplied it
    reads as `subject`, which is true of the chunks (there are none, so none carry the
    topic) but points the caller at the subject when the cause is an indexing gap.
    Closing it needs a chunk count the coverage signal does not carry, which means a new
    `CoverageRow` field; that is out of scope here and left deliberately, not silently.
    """
    if not any(row.documents for row in coverage):
        return "place"
    if as_of is not None:
        return "date"
    if topics:
        return "subject"
    return "place"


def no_evidence_message(
    label: str, coverage: Sequence[CoverageRow], topics: Sequence[str],
    as_of: date | None = None,
) -> str:
    """The message for an empty result, naming which of the three causes applies.

    The wording is the contract: a calling model acts on it, so each cause must be
    reachable only for itself and must not assert anything the server cannot stand
    behind. `no_evidence_cause` decides which; this only renders it.
    """
    cause = no_evidence_cause(coverage, topics, as_of)
    if cause == "place":
        return _PLACE.format(label=label)
    if cause == "date":
        clause = _DATED_TOPIC_CLAUSE.format(topics=", ".join(topics)) if topics else ""
        advice = _DATED_TOPIC_ADVICE if topics else _DATED_ADVICE
        return _DATED.format(label=label, as_of=as_of, topic_clause=clause, advice=advice)
    return _SUBJECT.format(label=label, topics=", ".join(topics))
