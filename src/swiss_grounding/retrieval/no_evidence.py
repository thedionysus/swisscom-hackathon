"""Why `swiss_search` found nothing, told apart so a calling model can act on it.

There are two reasons, they come from two different decisions, and they compose (ADR
0003's consequences say so explicitly):

- **The place is uncovered** (ADR 0001). Nothing on the extent path could be retrieved,
  whatever the subject. No topic could have matched, so naming one would misdirect the
  caller into rephrasing the subject when the subject was never the problem. The useful
  next move is a different place, or telling the user this place is not covered.
- **The subject is uncovered** (ADR 0003). Documents are indexed on the path, but no
  chunk carries the question's topic. The place is fine; the index simply holds nothing
  on this subject for it. The useful next move is a different subject -- and explicitly
  *not* answering from the on-path evidence that is there, because a chunk that does not
  carry the topic is not evidence for this question.

Collapsing these into one sentence is what makes a caller guess, so each message names
its own cause, and only the second names the topics. The coverage signal rides along on
both responses either way: it reports what *is* indexed for each extent on the path, and
it is about places, not topics.
"""

from collections.abc import Sequence

from swiss_grounding.retrieval.models import CoverageRow

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


def no_evidence_message(
    label: str, coverage: Sequence[CoverageRow], topics: Sequence[str],
) -> str:
    """The message for an empty result, naming which of the two causes applies.

    `coverage` decides: it is the same per-extent document count the response carries and
    `swiss_coverage` returns, so the message can never contradict the signal beside it.
    A path with no documents is the place cause even when topics were supplied, because
    the topic never got the chance to exclude anything.

    An empty result on a covered path with no topic filter -- documents that hold no
    chunks, which `recontext` can leave behind -- is reported as the place cause too:
    there is nothing to retrieve there and no topic to blame it on. The place message is
    worded to stay true of that case as well as of a path with no documents at all, and
    defers the per-level detail to the coverage signal rather than restating it.
    """
    if not topics or not any(row.documents for row in coverage):
        return _PLACE.format(label=label)
    return _SUBJECT.format(label=label, topics=", ".join(topics))
