from datetime import date
from typing import Sequence

import psycopg

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.embedder import Embedder
from swiss_grounding.retrieval.models import ChunkRecord, Hit

CHUNK_COLUMNS = """
    c.id as chunk_id, c.document_id, c.ordinal, c.text_original, c.text_en, c.heading_path,
    c.anchor, c.extent_id, c.authority, c.categories,
    d.url, d.identifier, d.title_original, d.title_en, d.language, d.valid_from, d.retrieved_at,
    d.source_id, s.license
"""

FILTER = """
    c.extent_id = any(%(path)s)
    and (
        (%(as_of)s::date is null and c.document_status = 'current')
        or (%(as_of)s::date is not null
            and d.status in ('current', 'superseded')
            and (d.valid_from is null or d.valid_from <= %(as_of)s::date)
            and (d.valid_to is null or d.valid_to > %(as_of)s::date))
    )
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
    )


def hybrid_search(
    conn: psycopg.Connection,
    embedder: Embedder,
    question: str,
    extent_path: tuple[str, ...],
    as_of: date | None,
    top_n: int = 50,
) -> tuple[Hit, ...]:
    """Dense and lexical retrieval restricted to the extent path, fused with RRF."""
    vector = embedder.embed([question])[0]
    params = {"path": list(extent_path), "as_of": as_of, "top_n": top_n}
    dense_rows = conn.execute(DENSE_SQL, {**params, "vector": vector}).fetchall()
    lexical_rows = conn.execute(LEXICAL_SQL, {**params, "question": question}).fetchall()
    records = {r["chunk_id"]: _record(r) for r in [*dense_rows, *lexical_rows]}
    fused = reciprocal_rank_fusion(
        dense=[r["chunk_id"] for r in dense_rows],
        lexical=[r["chunk_id"] for r in lexical_rows],
        with_ranks=True,
    )
    return tuple(
        Hit(chunk=records[cid], rrf_score=score, dense_rank=dr, lexical_rank=lr)
        for cid, score, dr, lr in fused
    )
