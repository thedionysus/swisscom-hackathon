"""Insert small corpus documents for serving tests. Embeddings come from FakeEmbeddings(1024)."""
from datetime import UTC, date, datetime

from pgvector import SparseVector

from swiss_grounding.corpus.providers import BGE_M3_VOCAB, FakeEmbeddings

EMB = FakeEmbeddings(1024)
NOW = datetime(2026, 9, 20, tzinfo=UTC)


def add_source(conn, source_id="src", extent="CH", level="federal", authority="federal_law"):
    conn.execute(
        "insert into corpus.source (id, name, publisher, authority, level, extent_id, connector, tier, languages) "
        "values (%s,%s,%s,%s,%s,%s,'html',1,'{de,fr,it,en}') on conflict (id) do nothing",
        (source_id, source_id, f"Publisher {source_id}", authority, level, extent))


def add_group(conn, group_id):
    conn.execute("insert into corpus.translation_group (id, work_key) values (%s,%s) on conflict do nothing",
                 (group_id, group_id))


def add_doc(conn, *, group, lang, text, extent="CH", source="src", authority="federal_law",
            align="art-1", authentic=True, status="current", valid_from=None, valid_to=None,
            chunk_status="current", sparse=None, url=None, title="Title", breadcrumb=("Art. 1",)):
    add_source(conn, source, extent, "federal" if extent == "CH" else "municipal", authority)
    add_group(conn, group)
    doc_id = conn.execute(
        "insert into corpus.document (source_id, url, language, translation_group_id, title, publisher, "
        "authority, extent_id, is_authentic, valid_from, valid_to, status, fetched_at, last_seen_at, content_hash) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'h') returning id",
        (source, url or f"https://example.ch/{group}/{lang}/{align}", lang, group, title, f"Publisher {source}",
         authority, extent, authentic, valid_from, valid_to, status, NOW, NOW)).fetchone()["id"]
    chunk_id = conn.execute(
        "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, "
        "text, extent_id, authority, status, chunk_hash) values (%s,%s,%s,%s,0,%s,%s,%s,%s,%s,'c') returning id",
        (doc_id, lang, group, align, list(breadcrumb), text, extent, authority, chunk_status)).fetchone()["id"]
    vec = EMB.embed([text])[0]
    conn.execute(
        "insert into corpus.emb_bge_m3 (chunk_id, language, text_hash, embedding, sparse) values (%s,%s,'t',%s,%s)",
        (chunk_id, lang, vec, SparseVector(sparse, BGE_M3_VOCAB) if sparse else None))
    return doc_id, chunk_id


DAY = date(2026, 1, 1)
