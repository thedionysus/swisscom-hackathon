import pytest

from swiss_grounding.corpus.db import apply_corpus_schema
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration


def _seed_one_chunk(conn, language: str, text: str) -> None:
    conn.execute("insert into corpus.source (id, name, publisher, authority, level, extent_id, connector, tier, languages) "
                 "values ('s', 'S', 'P', 'official_info', 'federal', 'CH', 'html', 1, '{de,fr}')")
    conn.execute("insert into corpus.translation_group (id, work_key) values ('g', 'k')")
    doc = conn.execute(
        "insert into corpus.document (source_id, url, language, translation_group_id, title, publisher, authority, "
        "extent_id, status, fetched_at, last_seen_at, content_hash) values "
        "('s', 'https://x', %s, 'g', 'T', 'P', 'official_info', 'CH', 'current', now(), now(), 'h') returning id",
        (language,)).fetchone()["id"]
    conn.execute(
        "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, text, "
        "extent_id, authority, status, chunk_hash) values (%s, %s, 'g', 'a', 0, '{Hundegesetz}', %s, 'CH', "
        "'official_info', 'current', 'c')", (doc, language, text))


def test_schema_is_idempotent(corpus_db):
    with connect(corpus_db) as conn:
        _seed_one_chunk(conn, "de", "Hunde müssen in Zürich an der Leine geführt werden.")

    apply_corpus_schema(corpus_db)
    apply_corpus_schema(corpus_db)

    with connect(corpus_db) as conn:
        row = conn.execute(
            "select text, tsv from corpus.chunk where document_id = "
            "(select id from corpus.document where url = 'https://x')").fetchone()
    assert row["text"] == "Hunde müssen in Zürich an der Leine geführt werden."
    assert row["tsv"] is not None
    assert len(row["tsv"]) > 0


def test_language_partitions_exist(corpus_db):
    with connect(corpus_db) as conn:
        names = {r["relname"] for r in conn.execute(
            "select c.relname from pg_inherits i join pg_class c on c.oid = i.inhrelid "
            "join pg_class p on p.oid = i.inhparent where p.relname = 'chunk'").fetchall()}
        openai_names = {r["relname"] for r in conn.execute(
            "select c.relname from pg_inherits i join pg_class c on c.oid = i.inhrelid "
            "join pg_class p on p.oid = i.inhparent where p.relname = 'emb_openai_3l'").fetchall()}
        bge_names = {r["relname"] for r in conn.execute(
            "select c.relname from pg_inherits i join pg_class c on c.oid = i.inhrelid "
            "join pg_class p on p.oid = i.inhparent where p.relname = 'emb_bge_m3'").fetchall()}
        index_names = {r["indexname"] for r in conn.execute(
            "select indexname from pg_indexes where schemaname = 'corpus' "
            "and indexname in ('emb_openai_3l_hash_idx', 'emb_bge_m3_hash_idx')").fetchall()}
    assert names == {"chunk_de", "chunk_fr", "chunk_it", "chunk_en", "chunk_rm"}
    assert openai_names == {
        "emb_openai_3l_de", "emb_openai_3l_fr", "emb_openai_3l_it", "emb_openai_3l_en", "emb_openai_3l_rm"}
    assert bge_names == {
        "emb_bge_m3_de", "emb_bge_m3_fr", "emb_bge_m3_it", "emb_bge_m3_en", "emb_bge_m3_rm"}
    assert index_names == {"emb_openai_3l_hash_idx", "emb_bge_m3_hash_idx"}


def test_ts_config_lookup_is_schema_qualified_and_ignores_search_path(corpus_db):
    with connect(corpus_db) as conn:
        conn.execute("set search_path = corpus")
        _seed_one_chunk(conn, "de", "Hunde müssen in Zürich an der Leine geführt werden.")
        row = conn.execute(
            "select tsv from corpus.chunk where document_id = "
            "(select id from corpus.document where url = 'https://x')").fetchone()
    assert row["tsv"] is not None
    assert len(row["tsv"]) > 0


def test_german_keyword_index_stems_and_folds_accents(corpus_db):
    with connect(corpus_db) as conn:
        _seed_one_chunk(conn, "de", "Hunde müssen in Zürich an der Leine geführt werden.")
        hits = conn.execute(
            "select count(*) as n from corpus.chunk where language = 'de' "
            "and tsv @@ to_tsquery('sg_german', 'zurich & hund & leine')").fetchone()["n"]
    assert hits == 1


def test_breadcrumb_is_searchable(corpus_db):
    with connect(corpus_db) as conn:
        _seed_one_chunk(conn, "de", "Der Bundesrat erlässt Vorschriften.")
        hits = conn.execute("select count(*) as n from corpus.chunk "
                            "where tsv @@ to_tsquery('sg_german', 'hundegesetz')").fetchone()["n"]
    assert hits == 1


def test_description_update_refreshes_tsv(corpus_db):
    with connect(corpus_db) as conn:
        _seed_one_chunk(conn, "fr", "Le Conseil fédéral édicte des dispositions.")
        conn.execute("update corpus.chunk set description = 'Obligation de tenir les chiens en laisse'")
        hits = conn.execute("select count(*) as n from corpus.chunk "
                            "where tsv @@ to_tsquery('sg_french', 'laisse')").fetchone()["n"]
    assert hits == 1
