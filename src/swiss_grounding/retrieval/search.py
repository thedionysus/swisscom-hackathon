from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
import psycopg

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.embedder import Embedder
from swiss_grounding.retrieval.models import ChunkRecord, Hit

CHUNK_COLUMNS = """
    c.id as chunk_id, c.document_id, c.ordinal, c.text_original, c.text_en, c.heading_path,
    c.anchor, c.extent_id, c.authority, c.categories,
    d.url, d.identifier, d.title_original, d.title_en, d.language, d.valid_from, d.retrieved_at,
    d.source_id, s.license, d.event_date
"""

# One predicate, shared by both retrieval arms below, so the dense and the lexical arm
# can never disagree about what counts as evidence.
#
# The topic clause is ADR 0003: a chunk that does not carry one of the question's topics
# is not evidence for that question, the same way a chunk off the extent path is not.
# `&&` is array overlap, so a chunk qualifies by carrying *any* one of the topics, not
# all of them -- the classifier returns a margin band precisely because a near-tie is not
# evidence for its top entry alone.
#
# `null`, not an empty array, is what "no topic was supplied" looks like here, and it
# makes the clause a no-op. The two are deliberately different queries: `c.categories &&
# '{}'` is false for every row, so an empty array would filter *on nothing* and return
# nothing. That matters because both ends of this can legitimately be empty -- the
# classifier returns no topics for a question it cannot place (`topics.py`), and a chunk
# may carry no categories at all (`ingest/context.py`) -- and "no opinion" must not be
# spelled the same way as "an opinion nothing satisfies".
#
# The `as_of` arm is D2. `d.valid_from is not null` is the load-bearing half: a document
# that records no start date cannot be shown to have been in force on the asked-for date,
# and the clause used to read `d.valid_from is null or ...`, which let every undated
# document satisfy every date. A question about 2020 then came back holding the undated
# municipal pages that bypassed the filter, with every act that does carry a date
# excluded around them. `d.valid_to is null` stays a pass, and is not the same case: a
# document with no recorded end has not ended, which is a fact about it rather than an
# absence of one. What this costs is real and deliberate -- most of the index carries no
# `valid_from`, so a dated query retrieves very little, and `no_evidence.py` reports an
# empty dated result from a census of these arms rather than guessing between them.
#
# The three arms are named separately because two other queries in this module have to
# apply *exactly* these predicates with one arm left out. Sharing the strings is what
# makes that true; a comment saying "copied from FILTER" was not enough, and a review
# found the boundary query's status set drifting free with nothing to catch it.
EXTENT_ARM = "c.extent_id = any(%(path)s)"
TOPIC_ARM = "(%(topics)s::text[] is null or c.categories && %(topics)s::text[])"
# The statuses `as_of` can reach. A `withdrawn` or `pending_enrichment` document is
# unreachable at every date, so it may not shape a boundary or a count either.
AS_OF_STATUSES = "d.status in ('current', 'superseded')"
# What the `as_of` arm becomes when no date is supplied -- which is also what "drop the
# date" means for the census below, so it is spelled once.
UNDATED_ARM = "d.status = 'current'"
AS_OF_ARM = f"""(
        (%(as_of)s::date is null and {UNDATED_ARM})
        or (%(as_of)s::date is not null
            and {AS_OF_STATUSES}
            and d.valid_from is not null and d.valid_from <= %(as_of)s::date
            and (d.valid_to is null or d.valid_to > %(as_of)s::date))
    )"""
FILTER = f"""
    {EXTENT_ARM}
    and {TOPIC_ARM}
    and {AS_OF_ARM}
"""

# The oldest date `as_of` can answer for, and it is a property of the corpus rather than
# a constant: only current consolidations are ingested, so the index holds no version
# older than the oldest `valid_from` in it and a date before that reaches nothing.
#
# `AS_OF_STATUSES` is the shared string, not a copy: this has to be the minimum over
# exactly the rows FILTER's `as_of` arm admits, or the boundary `query_core` reports
# would not be the boundary retrieval actually has -- it would promise a reach into
# withdrawn documents that no date can retrieve.
#
# Deliberately not restricted to an extent path: the number goes into a refusal the
# caller has to act on, and a boundary that moved with the place would make the same date
# answerable in Zurich and refused in Bern for reasons the message could not explain.
# `PATH_EVIDENCE_SQL` computes the path-scoped boundary separately, for the message that
# does want a local one.
EARLIEST_VERSION_SQL = f"""
select min(d.valid_from) as earliest
from document d
where {AS_OF_STATUSES} and d.valid_from is not null
"""

DENSE_SQL = f"""
select {CHUNK_COLUMNS}, c.embedding <=> %(vector)s as distance
from chunk c join document d on d.id = c.document_id join source s on s.id = d.source_id
where {FILTER}
order by distance asc
limit %(top_n)s
"""

LEXICAL_SQL = f"""
select {CHUNK_COLUMNS}, ts_rank_cd(c.tsv, q) as rank
from chunk c join document d on d.id = c.document_id join source s on s.id = d.source_id,
     websearch_to_tsquery('english', %(question)s) q
where {FILTER} and c.tsv @@ q
order by rank desc
limit %(top_n)s
"""


def earliest_indexed_version(conn: psycopg.Connection) -> date | None:
    """The oldest `valid_from` retrieval can reach, or None when nothing records one.

    None is not an error and not zero: it means no indexed document carries a validity
    date, so no `as_of` is answerable at all. The caller has to tell those two apart --
    one is fixed by moving the date forward, the other only by dropping the date.

    Known and deliberate: this ignores `valid_to`, which FILTER's `as_of` arm applies. A
    document that has already expired can therefore raise the boundary above the oldest
    date anything is actually retrievable at. Zero impact today -- no indexed document
    carries a `valid_to` -- and it only becomes reachable once version history is
    ingested, at which point the boundary wants to be the oldest date with *coverage*
    rather than the oldest start date, which is a different query.
    """
    row = conn.execute(EARLIEST_VERSION_SQL).fetchone()
    return row["earliest"] if row else None


@dataclass(frozen=True)
class PathEvidence:
    """What each arm of `FILTER` would have returned on the extent path, on its own.

    The routing in `no_evidence.py` runs on this, and the reason is worth stating plainly:
    an empty result names a cause, a calling model repeats that cause to a user, and the
    only honest way to name it is to check. The coverage signal cannot do it -- it counts
    *documents* with `status = 'current'` and applies neither the topic nor the date, so
    it is blind to two of the three arms and cannot see a document that holds no chunks.

    Two counts and a date, and every one of them is read by the routing. There is
    deliberately no raw "chunks on this path" count: it would be redundant, because both
    counts below are taken over subsets of exactly those rows and are therefore zero
    whenever it would be, and a field the routing never reads is a field that rots.

    - `chunks_without_as_of`: what the same request would have returned undated. Greater
      than zero is what licenses blaming the date.
    - `chunks_without_topics`: what it would have returned with no topic. Greater than
      zero is what licenses blaming the topic.
    - `earliest_valid_from`: the oldest date *this path and topic* can answer for, or None
      when nothing there records one. The global boundary drives the refusal; this drives
      the message, which would otherwise offer "try another as_of" for a path no date
      reaches.
    """

    chunks_without_as_of: int
    chunks_without_topics: int
    earliest_valid_from: date | None


# One round trip, four conditional aggregates, each one an arm of FILTER left out. Run
# only on an empty result, so it never touches the path that returns evidence.
PATH_EVIDENCE_SQL = f"""
select
    count(*) filter (where {TOPIC_ARM} and {UNDATED_ARM}) as chunks_without_as_of,
    count(*) filter (where {AS_OF_ARM}) as chunks_without_topics,
    min(d.valid_from) filter (where {TOPIC_ARM} and {AS_OF_STATUSES}) as earliest_valid_from
from chunk c join document d on d.id = c.document_id
where {EXTENT_ARM}
"""


def path_evidence(
    conn: psycopg.Connection,
    extent_path: tuple[str, ...],
    as_of: date | None,
    topics: tuple[str, ...],
) -> PathEvidence:
    """Census the extent path with one arm of `FILTER` dropped at a time.

    `topics` follows the same null-versus-empty-array rule as `hybrid_search`: an empty
    tuple is *no constraint*, which is null here, never an empty array that nothing
    overlaps.
    """
    row = conn.execute(PATH_EVIDENCE_SQL, {
        "path": list(extent_path), "as_of": as_of,
        "topics": list(topics) if topics else None,
    }).fetchone()
    return PathEvidence(
        chunks_without_as_of=row["chunks_without_as_of"],
        chunks_without_topics=row["chunks_without_topics"],
        earliest_valid_from=row["earliest_valid_from"],
    )


# One primary-key lookup. The `<=>` expression is character-for-character the one in
# DENSE_SQL, so a chunk gets the same number whichever arm retrieved it.
DISTANCE_SQL = """
select c.id as chunk_id, c.embedding <=> %(vector)s as distance
from chunk c
where c.id = any(%(ids)s)
"""


def distances_for(
    conn: psycopg.Connection, vector: np.ndarray, chunk_ids: Sequence[int],
) -> dict[int, float]:
    """Cosine distance from `vector` to each named chunk, keyed by chunk id.

    This exists because only the dense arm measures a distance: a chunk the lexical arm
    found and the dense arm did not has never been compared to the query vector, and
    Task 9 needs a distance for every hit -- it is what decides whether a chunk may claim
    a specificity tier, and it is published on every citation.

    **An id with no row is simply absent from the result.** Every id passed here came out
    of a select on this same connection moments earlier, so the only way to lose one is a
    concurrent delete. The caller turns that into `Hit.distance is None`, meaning *not
    measured*, and a chunk with no measured distance claims no tier (`rerank`). Nothing
    fabricates a distance for a row it could not find, because a made-up number here would
    be indistinguishable from a real one downstream.
    """
    ids = list(dict.fromkeys(chunk_ids))
    if not ids:
        return {}
    rows = conn.execute(DISTANCE_SQL, {"vector": vector, "ids": ids}).fetchall()
    return {row["chunk_id"]: row["distance"] for row in rows}


def reciprocal_rank_fusion(
    dense: Sequence[int], lexical: Sequence[int], k: int = 60, with_ranks: bool = False,
) -> list:
    """Fuse two ranked id lists. Returns (id, score) or (id, score, dense_rank, lexical_rank)."""
    dense_rank = {cid: i + 1 for i, cid in enumerate(dense)}
    lexical_rank = {cid: i + 1 for i, cid in enumerate(lexical)}
    ids = list(dict.fromkeys([*dense, *lexical]))
    scored = []
    for cid in ids:
        score = 0.0
        if cid in dense_rank:
            score += 1.0 / (k + dense_rank[cid])
        if cid in lexical_rank:
            score += 1.0 / (k + lexical_rank[cid])
        scored.append((cid, score, dense_rank.get(cid), lexical_rank.get(cid)))
    scored.sort(key=lambda t: -t[1])
    if with_ranks:
        return scored
    return [(cid, score) for cid, score, _, _ in scored]


def _record(row: dict) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=row["chunk_id"], document_id=row["document_id"], ordinal=row["ordinal"],
        text_original=row["text_original"], text_en=row["text_en"],
        heading_path=row["heading_path"], anchor=row["anchor"], extent_id=row["extent_id"],
        authority=Authority(row["authority"]), categories=tuple(row["categories"]),
        url=row["url"], identifier=row["identifier"], title_original=row["title_original"],
        title_en=row["title_en"], language=row["language"], valid_from=row["valid_from"],
        retrieved_at=row["retrieved_at"], license=row["license"], source_id=row["source_id"],
        event_date=row["event_date"],
    )


def hybrid_search(
    conn: psycopg.Connection,
    embedder: Embedder,
    question: str,
    extent_path: tuple[str, ...],
    as_of: date | None,
    top_n: int = 50,
    topics: tuple[str, ...] = (),
    embedded_question: str | None = None,
) -> tuple[Hit, ...]:
    """Dense and lexical retrieval restricted to the extent path and the topics, fused with RRF.

    The two arms are asked different things (ADR 0004). `question` is the text as the
    user wrote it and it is what the lexical arm matches, because a keyword index matches
    literal terms and the caller's own words are the ones worth matching.
    `embedded_question` is what the dense arm embeds -- the caller's English rendering,
    because the embeddings and `tsv` are both built from `text_en` and an English index is
    the only thing an English vector can usefully be compared against.
    `retrieval/query_text.py` composes it; `None` means *the same text for both arms*,
    which is what a caller with only one string has and is the honest default for a test
    about the filter rather than about the query.

    `topics` is a hard filter (ADR 0003), and an empty tuple applies no filter at all
    rather than a filter nothing satisfies -- see FILTER for why the two must differ.
    Unknown topic ids are the caller's to reject; `query_core._validate` does it, and an
    unknown id reaching here simply matches no chunk.

    Every returned hit carries the cosine distance it would have had in the dense arm,
    backfilled for the lexically-retrieved ones. The plan sited that backfill after
    diversification, over the ≤25 surviving ids; it runs here instead, over the fused
    candidate set, because the distance decides the specificity tier and the tier is the
    reranker's outer ordering key -- fetching it later would mean publishing a tier that
    the ordering never used. A distance fetched after diversification cannot feed the key
    that decided what diversification was given.

    The cost of moving it is smaller than moving it looks. Only the lexical-only
    complement is passed, never the whole candidate set, so the bound is `top_n` -- ≤50,
    not ≤100 -- and it is exactly 0 whenever the dense arm already returned everything the
    lexical arm did, which is the common case and what the fixture corpus does. Measured:
    ~0.3 ms against `DENSE_SQL`'s 1.8 ms.
    """
    vector = embedder.embed([embedded_question if embedded_question is not None else question])[0]
    params = {
        "path": list(extent_path), "as_of": as_of, "top_n": top_n,
        # `list(topics) or None` would map an empty tuple to null by accident of
        # falsiness; spell the no-filter case out so it survives a later edit.
        "topics": list(topics) if topics else None,
    }
    dense_rows = conn.execute(DENSE_SQL, {**params, "vector": vector}).fetchall()
    lexical_rows = conn.execute(LEXICAL_SQL, {**params, "question": question}).fetchall()
    records = {r["chunk_id"]: _record(r) for r in [*dense_rows, *lexical_rows]}
    measured = {r["chunk_id"]: r["distance"] for r in dense_rows}
    distances = {
        **measured,
        **distances_for(conn, vector, [cid for cid in records if cid not in measured]),
    }
    fused = reciprocal_rank_fusion(
        dense=[r["chunk_id"] for r in dense_rows],
        lexical=[r["chunk_id"] for r in lexical_rows],
        with_ranks=True,
    )
    return tuple(
        Hit(chunk=records[cid], rrf_score=score, dense_rank=dr, lexical_rank=lr,
            distance=distances.get(cid))
        for cid, score, dr, lr in fused
    )
