"""Why `swiss_search` found nothing, told apart so a calling model can act on it.

`search.FILTER` has three arms, and an empty result means one or more of them emptied it.
Each arm comes from a different decision, and they compose:

- **The extent arm**. Nothing on the extent path could be retrieved, whatever
  the topic and whatever the date. Neither other arm got the chance to exclude anything,
  so naming one would misdirect the caller into rephrasing a topic, or moving a date,
  that was never the problem. The useful next move is a different place.
- **The `as_of` arm**. On-topic evidence *is* indexed on the path, and the date
  excluded all of it -- most often because the index holds current consolidations only
  and a document recording no `valid_from` cannot be shown to have been in force on any
  date. The useful next move is a different `as_of`, or none.
- **The topic arm**. In-force evidence is indexed on the path and no chunk
  carries the question's topic. The useful next move is a different topic -- and
  explicitly *not* answering from the on-path evidence that is there.

**Each cause is established, never inferred.** That is the whole design of this module
and it was learned twice over. The first version routed on the coverage signal, which
counts `status = 'current'` *documents* and applies neither the topic nor the date; it
was blind to two arms and reported an `as_of` wipeout as an uncovered topic. The second
version added a date cause but fired it for *any* dated empty result on a covered path,
so a query the topic alone emptied was blamed on the date -- the same falsehood, one arm
over, and "the topic is not the problem" is not a sentence a server may assert on a
guess. The routing now runs on `search.PathEvidence`, a census of what each arm would
have returned alone, so every claim in every message below is one the census establishes.

A fourth case follows from doing this honestly: when the date and the topic each exclude
evidence the other would have returned, neither is *the* cause and dropping either one
alone recovers something. Naming one would be true and would still stop short of what
the caller needs, so that state says both.
"""

from collections.abc import Sequence
from datetime import date
from typing import Literal

from swiss_grounding.retrieval.as_of import reachable_from
from swiss_grounding.retrieval.search import PathEvidence

# Named for the arm of `search.FILTER` each one reports, in the project's own vocabulary:
# *extent* and *topic*, never "region" or "subject area".
Cause = Literal["extent", "as_of", "topic", "as_of_and_topic"]

# Kept as the opening clause of the extent message rather than reworded, because it is
# the sentence this server has always returned for an uncovered place. It stays true of
# every state routed here: no chunks on the path at all, documents whose chunks are gone,
# and a path whose chunks no arm can reach.
_EXTENT = (
    "No indexed evidence for {label} or its parent jurisdictions. Nothing on that "
    "jurisdiction path could be retrieved at all, whatever the subject; the coverage "
    "signal in this response says which levels hold documents. Tell the user the place "
    "is not covered, or ask about a larger place -- rephrasing the subject will not help."
)

_TOPIC = (
    "Documents are indexed on the jurisdiction path for {label}, but none of them carry "
    "the topic {topics}. The place is covered; this subject is not. Tell the user nothing "
    "on this subject is indexed for this place, or search again with a different topic. "
    "Do not answer from evidence on another subject."
)

# Reached only when `chunks_without_as_of > 0`, so "searching without as_of returns this
# evidence" is a fact about this query, not a hope. That count is what licenses the topic
# clause too: the chunks it counts carry the topic by construction.
_AS_OF = (
    "Evidence is indexed on the jurisdiction path for {label}{topic_clause}, but none of "
    "it was in force on the as_of date {as_of}. {reach} Only current consolidations are "
    "indexed, so a document that records no validity date cannot be shown to have been in "
    "force on any date and is excluded -- which is most of what is indexed, including "
    "calendar records and municipal pages. Searching again without as_of returns this "
    "evidence. Tell the user the index cannot answer as at that date for this place."
)
_AS_OF_TOPIC_CLAUSE = " carrying the topic {topics}"

# Both arms exclude evidence the other would have returned. Every clause is a count.
_AS_OF_AND_TOPIC = (
    "Evidence is indexed on the jurisdiction path for {label}, but nothing on it both "
    "carries the topic {topics} and was in force on the as_of date {as_of}. Either "
    "constraint on its own would have returned something: there are on-topic documents "
    "the date excludes, and in-force documents the topic excludes. {reach} Ask the user "
    "which they meant -- this subject as it stands now, or whatever applied on that date "
    "-- and search again with one of the two constraints, not both."
)


def no_evidence_cause(
    evidence: PathEvidence, topics: Sequence[str], as_of: date | None,
) -> Cause:
    """Which arm of `search.FILTER` to report for an empty result.

    The question each branch answers is "would dropping this one constraint have returned
    evidence?", because that is both the honest test of causation and the only advice
    worth giving. The census answers it directly; nothing here is inferred from anything
    else.

    The extent arm needs no test of its own, and deliberately has none: a path with
    nothing retrievable on it has both counts at zero, so it falls through to the same
    answer. An explicit `chunks_on_path == 0` branch in front of this was removed after a
    mutation of it changed no behaviour at all -- it could not, because both counts are
    taken over subsets of those same rows.
    """
    dropping_as_of_helps = as_of is not None and evidence.chunks_without_as_of > 0
    dropping_topics_helps = bool(topics) and evidence.chunks_without_topics > 0
    if dropping_as_of_helps and dropping_topics_helps:
        return "as_of_and_topic"
    if dropping_as_of_helps:
        return "as_of"
    if dropping_topics_helps:
        return "topic"
    # Neither single change recovers anything, so neither arm may be blamed for it, and
    # the extent message is the only one that claims no more than that. Everything the
    # coverage signal used to misreport lands here: a path with no chunks, documents whose
    # chunks `recontext` removed, and a path whose every document is withdrawn. Each has
    # both counts at zero, so none of them needs -- or gets -- a branch of its own.
    return "extent"


def no_evidence_message(
    label: str, evidence: PathEvidence, topics: Sequence[str], as_of: date | None,
) -> str:
    """The message for an empty result, naming the cause the census established.

    Every argument is required, `as_of` included. It carried a default once, and a default
    on this argument is exactly how a caller silently gets back the routing that could not
    see the date arm -- the defect reported against this module twice.
    """
    cause = no_evidence_cause(evidence, topics, as_of)
    if cause == "extent":
        return _EXTENT.format(label=label)
    if cause == "topic":
        return _TOPIC.format(label=label, topics=", ".join(topics))
    reach = reachable_from(evidence.earliest_valid_from)
    if cause == "as_of_and_topic":
        return _AS_OF_AND_TOPIC.format(
            label=label, topics=", ".join(topics), as_of=as_of, reach=reach,
        )
    clause = _AS_OF_TOPIC_CLAUSE.format(topics=", ".join(topics)) if topics else ""
    return _AS_OF.format(label=label, topic_clause=clause, as_of=as_of, reach=reach)
