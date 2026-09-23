"""Collapse candidates into translation groups; corroboration over authentic versions."""
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date

import psycopg

from swiss_grounding.serving.candidates import COLUMNS, filters
from swiss_grounding.serving.models import Candidate, GroupHit

Key = tuple[str, str]
VERSIONS_SQL = (
    f"select {COLUMNS} from corpus.chunk c join corpus.document d on d.id = c.document_id "
    "where (c.translation_group_id, c.align_key) in "
    "(select * from unnest(%(groups)s::text[], %(aligns)s::text[])) and {validity}"
)


def aligned_versions(conn: psycopg.Connection, keys: Sequence[Key], as_of: date | None) -> dict[Key, tuple[Candidate, ...]]:
    """Every live chunk sharing a (translation_group_id, align_key) with the given keys."""
    if not keys:
        return {}
    sql = VERSIONS_SQL.format(validity=filters(as_of, ()))
    rows = conn.execute(sql, {"groups": [k[0] for k in keys], "aligns": [k[1] for k in keys],
                              "as_of": as_of}).fetchall()
    out: dict[Key, list[Candidate]] = {}
    for r in rows:
        c = Candidate(**{**r, "breadcrumb": tuple(r["breadcrumb"])})
        out.setdefault((c.translation_group_id, c.align_key), []).append(c)
    return {k: tuple(v) for k, v in out.items()}


def _representative(found: Sequence[Candidate], versions: Sequence[Candidate], question_lang: str | None) -> Candidate:
    """The question-language version, else the best authentic candidate, else the best candidate.
    It always carries the group's best RRF score and rank, so grouping never demotes a group."""
    best = found[0]
    wanted = next((c for c in found if c.language == question_lang), None)
    wanted = wanted or next((v for v in versions if v.language == question_lang), None)
    wanted = wanted or next((c for c in found if c.is_authentic), best)
    return replace(wanted, rrf=best.rrf, rrf_rank=best.rrf_rank)


def _diverges(a: Candidate, b: Candidate) -> bool:
    return a.valid_from is not None and b.valid_from is not None and a.valid_from != b.valid_from


def _corroboration(rep: Candidate, others: Sequence[Candidate],
                   found: Sequence[Candidate]) -> tuple[float | None, str | None, bool]:
    """Share of the group's other authentic versions present among the found candidates.

    A version whose valid_from differs from the representative's is divergent: it never counts
    as corroborating, but its presence still flags the group as divergent. `basis` is
    "independent" when every corroborating version was itself found by text in its own
    language (never through translation or another language's arm), else "cross_lingual".
    """
    authentic = [v for v in others if v.is_authentic]
    if not authentic:
        return None, None, False
    diverge = any(_diverges(rep, v) for v in authentic)
    found_by_lang = {c.language: c for c in found}
    hits = [v for v in authentic if v.language in found_by_lang and not _diverges(rep, v)]
    share = len(hits) / len(authentic)
    if not hits:
        return share, None, diverge
    independent = all(v.language in found_by_lang[v.language].query_langs for v in hits)
    return share, "independent" if independent else "cross_lingual", diverge


def collapse(candidates: Sequence[Candidate], versions: Mapping[Key, Sequence[Candidate]],
             question_lang: str | None) -> list[GroupHit]:
    """Group candidates by (translation_group_id, align_key), in first-seen order, and score
    each group once through its representative version (ADR 0012)."""
    order: list[Key] = []
    by_key: dict[Key, list[Candidate]] = {}
    for c in candidates:
        key = (c.translation_group_id, c.align_key)
        if key not in by_key:
            order.append(key)
        by_key.setdefault(key, []).append(c)
    groups = []
    for key in order:
        found = by_key[key]
        all_versions = tuple(versions.get(key) or found)
        rep = _representative(found, all_versions, question_lang)
        others = tuple(v for v in all_versions if v.language != rep.language)
        share, basis, diverge = _corroboration(rep, others, found)
        groups.append(GroupHit(rep, others, share, basis, diverge))
    return groups
