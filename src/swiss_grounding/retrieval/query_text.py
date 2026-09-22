"""The two queries one request produces, and which of its fields made them (ADR 0004).

Everything is indexed in English -- the embedding is built from `context_en` and `text_en`,
and `db/schema.sql` builds `tsv` from the same two columns -- while questions arrive in
German, French and Italian. The server cannot translate at query time: a model call while
answering is forbidden, and the README promises search keeps working on an empty credit
balance. So `swiss_search` asks the calling model, which already read the user's question
and is already paying for its own tokens, for the English rendering.

That leaves two different texts for two different indexes, and this module is the one
place that decides which goes where:

- the **dense** query is the caller's English text, because an English index is the only
  thing it can usefully be compared against;
- the **lexical** query is the question exactly as the user wrote it, because a keyword
  index matches literal terms and the caller's own words are the ones worth matching.

It also reports the request fields it used. A caller that supplies no `question_en` still
gets a search (ADR 0004's degrade path), and nothing else in the response would reveal
that the answer came from matching a German vector against an English index -- which is
precisely the unevenness ADR 0004 exists to remove. `SearchQuery.fields` is what makes a
degraded answer tell you so.

This module is pure string work with no database, no embedder and no model: it is the
boundary where a request's free text is normalised, and every field it reads is untrusted
caller input.
"""

from dataclasses import dataclass

from swiss_grounding.retrieval.models import QueryRequest

# One space, and deliberately the same separator `ingest/context.py` joins a chunk's
# generated context to its text with (`CONTEXT_SEPARATOR`) and `db/schema.sql` joins the
# same two columns with for `tsv`. The query should be assembled the way the thing it is
# compared against was assembled; a second convention here would be a difference with no
# reason behind it. It is restated rather than imported because importing
# `ingest.context` would pull the ingestion model client into the retrieval import path,
# and the server must import without one (the offline guarantee).
QUERY_SEPARATOR = " "


@dataclass(frozen=True)
class SearchQuery:
    """What retrieval is asked, split by which index asks it."""

    dense: str
    """Embedded and compared against chunk embeddings. English whenever the caller
    supplied English; the verbatim question otherwise."""
    lexical: str
    """Handed to `websearch_to_tsquery`. Always the question as the user wrote it."""
    fields: tuple[str, ...]
    """The `QueryRequest` fields whose text composed `dense`, in the order they were
    joined -- `("question_en", "topic_en")` at best, `("question",)` when the caller
    supplied no English. Published on the response so a caller can tell a full answer
    from a degraded one."""


def _text(value: str | None) -> str:
    """A caller-supplied field as usable text, or the empty string.

    `None`, `""` and `"   "` all mean *not supplied*. A client that sends the key with
    nothing in it has supplied nothing, and treating a blank as present would put a
    stray separator in the query and -- worse -- report a field as used that contributed
    nothing. The report is the only guard against a silent degrade, so it may not lie.
    """
    return value.strip() if value else ""


def build_search_query(request: QueryRequest) -> SearchQuery:
    """Split one request's text into the dense and the lexical query.

    The dense query is `question_en` followed by `topic_en`, joined by QUERY_SEPARATOR,
    with absent parts simply left out -- never a placeholder and never a dangling
    separator. Absent `question_en`, the verbatim `question` takes its place so an
    un-updated client degrades instead of sending an empty vector; a `topic_en` supplied
    without it is still appended, because English text about the subject can only help
    against an English index and `fields` makes the mixed-language join visible.

    Returns a new object and reads `request` without touching it: the same request is
    read again by `topics.resolve_topics`, which must see it exactly as the caller sent it.

    `request.question` is assumed non-empty; `query_core._validate` rejects an empty one
    before this is reached, and that is the only guard in front of it.
    """
    question = _text(request.question)
    question_en = _text(request.question_en)
    topic_en = _text(request.topic_en)
    head = ("question_en", question_en) if question_en else ("question", question)
    parts = (head, ("topic_en", topic_en)) if topic_en else (head,)
    return SearchQuery(
        dense=QUERY_SEPARATOR.join(text for _, text in parts),
        lexical=question,
        fields=tuple(name for name, _ in parts),
    )
