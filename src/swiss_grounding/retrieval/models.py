from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from swiss_grounding.registry.models import Authority


@dataclass(frozen=True)
class ChunkRecord:
    """A chunk as loaded from the database, with the document fields needed for citation."""
    chunk_id: int
    document_id: int
    ordinal: int
    text_original: str
    text_en: str
    heading_path: str
    anchor: str | None
    extent_id: str
    authority: Authority
    categories: tuple[str, ...]
    url: str
    identifier: str | None
    title_original: str
    title_en: str
    language: str
    valid_from: date | None
    retrieved_at: datetime
    license: str | None
    source_id: str
    event_date: date | None = None


@dataclass(frozen=True)
class Hit:
    chunk: ChunkRecord
    rrf_score: float
    dense_rank: int | None
    lexical_rank: int | None
    distance: float | None = None
    """Raw cosine distance between the chunk's embedding and the vector that was searched,
    lower being nearer. `None` means *not measured*, not *far*: nothing may read it as a
    large distance. `search.hybrid_search` fills it in for every hit it returns, including
    the lexically-retrieved ones the dense arm never scored, so `None` survives only for a
    chunk deleted underneath the query."""


@dataclass(frozen=True)
class ScoredHit:
    hit: Hit
    score: float
    specificity: float
    category_overlap: float
    authority_score: float
    tier: int | None = None
    """Hops from the question's node up to the chunk's extent: 0 is the question's own
    node, rising to the federal root. `None` is *no tier claimed* -- the chunk's distance
    did not clear the relevance floor, was never measured, or its extent is not on the
    question's path. A chunk that claims no tier ranks after every chunk that does, and is
    never dropped for it (`rerank`)."""


@dataclass(frozen=True)
class Citation:
    chunk_id: int
    document_id: int
    source_id: str
    title_en: str
    title_original: str
    url: str
    anchor: str | None
    identifier: str | None
    snippet_en: str
    snippet_original: str
    language: str
    heading_path: str
    extent_id: str
    extent_label: str
    authority: str
    categories: tuple[str, ...]
    valid_from: date | None
    retrieved_at: datetime
    license: str | None
    tier: int | None
    """How specific this evidence is. 0 is the jurisdiction the question resolved to, 1 is
    its parent, rising to the federal root. `None` means the chunk claimed no tier -- it is
    still evidence, it simply earned no claim to be the *local* answer.

    Citations are ordered by it, with one exception, so read the field rather than inferring
    it from position. `rerank` orders strictly by tier and puts every unclaimed one last;
    `diversify` may then move a single chunk out of that order, because guaranteeing that
    the most specific extent is represented at all takes precedence over a tidy sequence.
    A citation with no tier can therefore sit above ones that have a tier.
    `tests/unit/test_diversify.py` holds the worked case.

    Replaces the former `score`, which moved with the question's extent: the same chunk
    measured 1.1918 asked about `CH` and 0.8168 asked about `8003`, entirely on the
    specificity term, so no caller could compare it across calls.
    """
    distance: float | None
    """Cosine distance from the chunk to the vector that was searched, lower being nearer.
    Steady across calls that change only the location, since the location does not enter
    the query vector; it does move when a caller rewords the topic.

    **It is not a relevance threshold, and nothing filters on it.** On the corpus as it
    stands it does not separate relevant from irrelevant -- on one measured question a
    download link sat at 0.5115 and the page's only on-topic sentence at 0.5257 -- so it
    is published for the caller's information only. `None` means it was never measured.
    """
    event_date: date | None = None      # calendar-style records: the date the event happens


@dataclass(frozen=True)
class CoverageRow:
    """Document count for one extent on a resolved location's path."""
    extent_id: str
    label: str
    documents: int


@dataclass(frozen=True)
class QueryRequest:
    """One search, as the calling model is asked to state it.

    Three fields carry text and they are not interchangeable. `question` is what the user
    wrote, in whatever language they wrote it, and it is what the keyword index is asked
    for. `question_en` is the same question in English, and `topic_en` a short English
    description of the subject; together they are what gets embedded, because everything
    in the index is English. `retrieval/query_text.py` is the single place that decides
    which text reaches which index, and what happens when the English fields are absent.

    `topics` is the caller's statement of what the question is about, drawn from the fixed
    category ids, and it is a hard filter: a chunk that does not carry one of them is not
    evidence for this question. An empty tuple means *no constraint*, never *a constraint
    nothing satisfies* -- `topics.resolve_topics` is where that distinction is made.

    `categories` is a **deprecated alias for `topics`**: identical meaning, identical hard
    filter, read only when `topics` is empty. It exists because the MCP tool carried it
    before `topics` existed and a registered client that has not been updated sends it;
    dropping it would turn every such call into a schema error rather than a graceful
    degrade. Nothing reads it except `resolve_topics`'s second rung, and `QueryResponse`
    reports when a request came in on it. New code writes `topics`.
    """
    question: str
    question_en: str | None = None
    topic_en: str | None = None
    location: str | None = None
    topics: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    as_of: date | None = None
    limit: int = 8


NOTICE = "Retrieved public information from Swiss sources. Not legal advice."

ResponseStatus = Literal["results", "needs_location", "no_evidence", "invalid_request"]


@dataclass(frozen=True)
class QueryResponse:
    status: ResponseStatus
    citations: tuple[Citation, ...] = ()
    resolved_location_id: str | None = None
    resolved_location_label: str | None = None
    resolution_method: str | None = None
    alternatives: tuple[str, ...] = ()
    message: str = ""
    field: str | None = None      # the offending request field when status is invalid_request
    notice: str = NOTICE
    categories_used: tuple[str, ...] = ()
    coverage: tuple[CoverageRow, ...] = ()
    resolution_note: str = ""
    query_fields: tuple[str, ...] = ()
    """Which request fields composed the text that was embedded, in the order they were
    joined: `("question_en", "topic_en")` for a caller on the full contract, and
    `("question",)` for one that supplied no English -- meaning the user's own language
    was matched against an index that is entirely English. Before this field, nothing
    in the response revealed which of those happened; this is that field.

    `()` means no query was built at all, which is the case for every refused or
    unresolved request. It is deliberately distinguishable from `("question",)`: the
    first says nothing was searched, the second says something was searched badly."""
    topic_decided_by: str = ""
    """Who chose the topic filter `categories_used` reports: `"topics"` (the caller said
    so), `"categories"` (the caller said so on the deprecated field), or `"classifier"`
    (nobody said, so the server guessed from the question). `""` when no topic was
    resolved, i.e. the request never got that far.

    `categories_used` says *what* was filtered on and this says *who decided it*, which
    are different facts: an empty `categories_used` with `"classifier"` here means the
    local classifier declined to place the question and no topic filter was applied."""
