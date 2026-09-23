"""Candidate generation over the corpus schema: dense, sparse and per-language keyword arms."""
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
import psycopg
from pgvector import SparseVector

from swiss_grounding.corpus.providers import BGE_M3_VOCAB
from swiss_grounding.serving.models import LANGS, Candidate
from swiss_grounding.serving.rrf import fuse, select_with_quota

COLUMNS = (
    "c.id as chunk_id, c.language, c.document_id, c.translation_group_id, c.align_key, c.extent_id, "
    "c.authority, d.url, c.anchor, d.title, d.publisher, c.breadcrumb, c.text, d.is_authentic, "
    "d.valid_from, d.valid_to, d.modified_at, d.fetched_at, d.extraction"
)
CURRENT = "d.status = 'current' and c.status = 'current'"
# Dated documents (law) must be valid on the day; undated ones (most web pages) count when current.
AS_OF = ("c.status <> 'boilerplate' and ("
         "(d.valid_from is null and d.status = 'current') or "
         "(d.status in ('current','scheduled','superseded') and d.valid_from <= %(as_of)s "
         "and (d.valid_to is null or d.valid_to > %(as_of)s)))")
EMB_TABLE = {"bge-m3": ("corpus.emb_bge_m3", "vector"), "openai-3l": ("corpus.emb_openai_3l", "halfvec")}
IDENTIFIER = re.compile(r"\b\d+[a-z]?(?:\.\d+)*\b", re.IGNORECASE)


@dataclass(frozen=True)
class ArmQuery:
    question: str
    question_lang: str | None
    question_vec: np.ndarray
    question_sparse: Mapping[int, float] | None
    translations: Mapping[str, str]
    translation_vecs: Mapping[str, np.ndarray]
    extent_path: Sequence[str]
    local_extents: Sequence[str]
    as_of: date | None
    per_arm: int
    top_n: int
    local_quota: int


def filters(as_of: date | None, extents: Sequence[str]) -> str:
    """Validity filter, plus the extent filter unless the search spans all of Switzerland (no place)."""
    validity = AS_OF if as_of else CURRENT
    return validity + " and c.extent_id = any(%(extents)s)" if extents else validity


def _base(q: ArmQuery, extents: Sequence[str]) -> dict:
    return {"extents": list(extents), "as_of": q.as_of, "n": q.per_arm}


def _vector_arm(conn, q: ArmQuery, index: str, vec, extents, lang: str | None) -> list[dict]:
    table, cast = EMB_TABLE[index]
    lang_clause = " and c.language = %(lang)s" if lang else ""
    sql = (f"select {COLUMNS} from {table} e join corpus.chunk c on c.id = e.chunk_id and c.language = e.language "
           f"join corpus.document d on d.id = c.document_id where {filters(q.as_of, extents)}{lang_clause} "
           f"order by e.embedding <=> %(vec)s::{cast} limit %(n)s")
    return conn.execute(sql, {**_base(q, extents), "vec": vec, "lang": lang}).fetchall()


def _sparse_arm(conn, q: ArmQuery, extents) -> list[dict]:
    sql = (f"select {COLUMNS} from corpus.emb_bge_m3 e join corpus.chunk c on c.id = e.chunk_id "
           f"and c.language = e.language join corpus.document d on d.id = c.document_id "
           f"where e.sparse is not null and {filters(q.as_of, extents)} order by e.sparse <#> %(sparse)s limit %(n)s")
    sparse = SparseVector(dict(q.question_sparse), BGE_M3_VOCAB)
    return conn.execute(sql, {**_base(q, extents), "sparse": sparse}).fetchall()


def _keyword_arm(conn, q: ArmQuery, lang: str, text: str, extents) -> list[dict]:
    sql = (f"select {COLUMNS} from corpus.chunk c join corpus.document d on d.id = c.document_id "
           f"where c.language = %(lang)s and {filters(q.as_of, extents)} "
           f"and c.tsv @@ websearch_to_tsquery(corpus.ts_config(%(lang)s), %(text)s) "
           f"order by ts_rank_cd(c.tsv, websearch_to_tsquery(corpus.ts_config(%(lang)s), %(text)s)) desc "
           f"limit %(n)s")
    return conn.execute(sql, {**_base(q, extents), "lang": lang, "text": text}).fetchall()


def keyword_texts(q: ArmQuery) -> dict[str, str]:
    """What each language store's keyword arm searches for.

    websearch_to_tsquery ANDs every word, so a German question sent to the French store matches
    nothing but identifiers. Each store gets its translation when the client sent one, the question
    itself when it is in that store's language (or the language is unknown), and otherwise only the
    question's identifiers (SR numbers, article numbers, postal codes) joined by OR.
    """
    identifiers = " OR ".join(dict.fromkeys(IDENTIFIER.findall(q.question)))
    texts = {}
    for lang in LANGS:
        if lang in q.translations:
            texts[lang] = q.translations[lang]
        elif q.question_lang in (None, lang):
            texts[lang] = q.question
        elif identifiers:
            texts[lang] = identifiers
    return texts


def _arms(conn, q: ArmQuery, index: str, extents) -> dict[str, list[dict]]:
    arms = {"dense": _vector_arm(conn, q, index, q.question_vec, extents, None)}
    if q.question_sparse and index == "bge-m3":
        arms["sparse"] = _sparse_arm(conn, q, extents)
    for lang, text in keyword_texts(q).items():
        arms[f"kw_{lang}"] = _keyword_arm(conn, q, lang, text, extents)
    for lang, vec in q.translation_vecs.items():
        arms[f"dense_{lang}"] = _vector_arm(conn, q, index, vec, extents, lang)
    return arms


def _query_lang(arm: str, q: ArmQuery) -> str | None:
    """The language of the text an arm searched with: a translation's language, else the question's."""
    if arm.startswith("dense_"):
        return arm.split("_", 1)[1]
    if arm.startswith("kw_") and arm.split("_", 1)[1] in q.translations:
        return arm.split("_", 1)[1]
    return q.question_lang


def gather_candidates(conn: psycopg.Connection, q: ArmQuery, *, index: str, ef_search: int) -> list[Candidate]:
    conn.execute("select set_config('hnsw.ef_search', %s, true)", (str(ef_search),))
    conn.execute("select set_config('hnsw.iterative_scan', 'relaxed_order', true)")
    rows: dict[tuple[int, str], dict] = {}
    lists: dict[str, list[tuple[int, str]]] = {}
    scopes = {"": q.extent_path, "local_": q.local_extents} if q.local_extents else {"": q.extent_path}
    for prefix, extents in scopes.items():
        for arm, found in _arms(conn, q, index, extents).items():
            keys = [(r["chunk_id"], r["language"]) for r in found]
            rows.update({k: r for k, r in zip(keys, found, strict=True)})
            lists[prefix + arm] = keys
    fused = fuse(lists)
    local = set(q.local_extents)
    chosen = select_with_quota([k for k, _, _ in fused], is_local=lambda k: rows[k]["extent_id"] in local,
                               n=q.top_n, quota=q.local_quota)
    info = {k: (score, arms) for k, score, arms in fused}
    out = []
    for rank, key in enumerate(chosen, start=1):
        score, arms = info[key]
        plain = frozenset(a.removeprefix("local_") for a in arms)
        langs = frozenset(filter(None, (_query_lang(a, q) for a in plain)))
        row = rows[key]
        out.append(Candidate(**{**row, "breadcrumb": tuple(row["breadcrumb"]), "rrf": score, "rrf_rank": rank,
                                "arms": plain, "query_langs": langs}))
    return out
