import json
from datetime import UTC, datetime

import pytest

from swiss_grounding.corpus.budget import cost_usd, spent
from swiss_grounding.corpus.embed import (
    MAX_EMBED_CHARS,
    TEXT_HASH_SQL,
    build_vector_indexes,
    embed_local,
    embed_openai_batch,
    pending_for_index,
    resume_embed_batches,
    reuse_embeddings,
)
from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.corpus.providers import INDEXES, FakeEmbeddings
from swiss_grounding.corpus.runner import BatchRunner
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
SPEC = SourceSpec(id="s", name="S", publisher="P", authority="official_info", level="federal", extent_id="CH",
                  connector="html", tier=1, languages=("de",), config={})


def _seed(conn, url="u", text="Leinenpflicht im Wald.", day=24):
    upsert_source(conn, SPEC)
    persist_document(conn, ParsedDocument(source_id="s", url=url, language="de", work_key="k", title="T",
                     sections=(ParsedSection("de:0", ("T",), None, text),)),
                     SPEC, datetime(2026, 9, day, tzinfo=UTC))
    conn.execute("update corpus.chunk set description = 'Hunde an der Leine' where description = ''")


@pytest.mark.parametrize("index", ["bge-m3", "openai-3l"])
def test_local_embedding_fills_the_index_once(corpus_db, index):
    with connect(corpus_db) as conn:
        _seed(conn)
        assert len(pending_for_index(conn, INDEXES[index], require_description=True, limit=None)) == 1
    written = embed_local(corpus_db, INDEXES[index], FakeEmbeddings(INDEXES[index].dim), batch_size=8)
    with connect(corpus_db) as conn:
        assert written == 1
        assert pending_for_index(conn, INDEXES[index], require_description=True, limit=None) == []
        conn.execute("update corpus.chunk set description = 'geändert'")
        assert len(pending_for_index(conn, INDEXES[index], require_description=True, limit=None)) == 1


class FakeSparseBge:
    dim = 1024

    def embed_with_sparse(self, texts):
        return [(FakeEmbeddings(1024).embed([t])[0], {7: 0.9, 42: 0.3}) for t in texts]


def test_bge_m3_stores_the_sparse_vector(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
    embed_local(corpus_db, INDEXES["bge-m3"], FakeSparseBge(), batch_size=8)
    with connect(corpus_db) as conn:
        row = conn.execute("select sparse::text as s from corpus.emb_bge_m3").fetchone()
    assert row["s"] == "{8:0.9,43:0.3}/250002"          # pgvector prints 1-based indices


def test_unchanged_chunk_of_a_new_version_reuses_the_vector(corpus_db):
    """RAG review E3: identical embedded text is copied, not re-embedded."""
    calls = []

    class CountingFake(FakeEmbeddings):
        def embed(self, texts):
            calls.append(len(texts))
            return super().embed(texts)

    with connect(corpus_db) as conn:
        _seed(conn)
    embed_local(corpus_db, INDEXES["bge-m3"], CountingFake(1024), batch_size=8)
    with connect(corpus_db) as conn:
        _seed(conn, url="u2", day=25)
    embed_local(corpus_db, INDEXES["bge-m3"], CountingFake(1024), batch_size=8)
    with connect(corpus_db) as conn:
        n = conn.execute("select count(*) as n from corpus.emb_bge_m3").fetchone()["n"]
    assert calls == [1] and n == 2


def test_reuse_is_one_statement_and_copies_only_identical_text(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
    embed_local(corpus_db, INDEXES["openai-3l"], FakeEmbeddings(3072), batch_size=8)
    with connect(corpus_db) as conn:
        _seed(conn, url="u2", day=25)                              # same text: reusable
        _seed(conn, url="u3", text="Anderer Text.", day=26)        # different text: must be embedded
        assert reuse_embeddings(conn, INDEXES["openai-3l"]) == 1
        pending = pending_for_index(conn, INDEXES["openai-3l"], require_description=True, limit=None)
        assert [p["text"].endswith("Anderer Text.") for p in pending] == [True]
        assert reuse_embeddings(conn, INDEXES["openai-3l"]) == 0


def test_sql_text_hash_matches_python(corpus_db):
    """reuse_embeddings and the batch writer hash in SQL; pending_for_index hashes in Python."""
    with connect(corpus_db) as conn:
        _seed(conn)
        conn.execute("update corpus.chunk set breadcrumb = array['', 'Été', 'b'], text = %s",
                     ("Ärger über Größe – «ça» " + "z" * 13000,))
        [p] = pending_for_index(conn, INDEXES["bge-m3"], require_description=True, limit=None)
        row = conn.execute(f"select {TEXT_HASH_SQL} as h from corpus.chunk c").fetchone()
    assert len(p["text"]) == MAX_EMBED_CHARS and p["text"].startswith(" > Été > b\nHunde an der Leine\nÄrger")
    assert row["h"] == p["hash"]


def test_limit_counts_only_pending_chunks(corpus_db):
    """Already-embedded chunks first in id order must not use up the limit."""
    with connect(corpus_db) as conn:
        _seed_three(conn)
    embed_local(corpus_db, INDEXES["bge-m3"], FakeEmbeddings(1024), batch_size=8)
    with connect(corpus_db) as conn:
        _seed(conn, url="u9", text="Neu.", day=28)
        [p] = pending_for_index(conn, INDEXES["bge-m3"], require_description=True, limit=1)
        assert p["text"].endswith("Neu.") and p["hash"] == conn.execute(
            f"select {TEXT_HASH_SQL} as h from corpus.chunk c where id = %s", (p["id"],)).fetchone()["h"]


def test_undescribed_chunks_wait(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        conn.execute("update corpus.chunk set description = ''")
        assert pending_for_index(conn, INDEXES["bge-m3"], require_description=True, limit=None) == []


def test_sync_openai_embeddings_record_spend_at_sync_price(corpus_db):
    class FakeOpenAIEmbeddings(FakeEmbeddings):
        model = "text-embedding-3-large"

        def __init__(self):
            super().__init__(3072)
            self.last_usage = 0

        def embed(self, texts):
            self.last_usage = 1000 * len(texts)
            return super().embed(texts)

    with connect(corpus_db) as conn:
        _seed(conn)
    embed_local(corpus_db, INDEXES["openai-3l"], FakeOpenAIEmbeddings(), batch_size=8)
    with connect(corpus_db) as conn:
        assert spent(conn, "embed") == pytest.approx(cost_usd("text-embedding-3-large", 1000, 0, batch=False))


class FakeEmbeddingBatches:
    """The openai client's files and batches resources, answering embedding lines.

    Custom ids listed in `fail` come back as error lines (status 400)."""

    def __init__(self, fail=()):
        self.submitted = []
        self.fail = set(fail)
        outer = self

        class Files:
            def create(self, file, purpose):
                outer.submitted.append([json.loads(line) for line in file.read().decode().splitlines()])
                return type("F", (), {"id": f"file-{len(outer.submitted)}"})()

            def content(self, file_id):
                n = int(file_id.split("-")[-1])
                out = []
                for r in outer.submitted[n - 1]:
                    if r["custom_id"] in outer.fail:
                        out.append({"custom_id": r["custom_id"], "response": {"status_code": 400, "body": {
                            "error": {"message": "input too long"}}}})
                        continue
                    vec = FakeEmbeddings(3072).embed([r["body"]["input"]])[0].tolist()
                    out.append({"custom_id": r["custom_id"], "response": {"status_code": 200, "body": {
                        "data": [{"embedding": vec}], "usage": {"prompt_tokens": 10, "total_tokens": 10}}}})
                return type("C", (), {"text": "\n".join(json.dumps(o) for o in out)})()

        class Batches:
            def create(self, input_file_id, endpoint, completion_window):
                return type("B", (), {"id": "batch-" + input_file_id.split("-")[-1]})()

            def retrieve(self, batch_id):
                n = batch_id.split("-")[-1]
                return type("B", (), {"status": "completed", "output_file_id": f"out-{n}", "error_file_id": None})()

        self.files, self.batches = Files(), Batches()


def _seed_three(conn):
    for i, text in enumerate(("Eins.", "Zwei.", "Drei.")):
        _seed(conn, url=f"u{i}", text=text, day=24 + i)


def test_openai_batch_writes_vectors_counts_failures_and_records_spend(corpus_db, tmp_path):
    index = INDEXES["openai-3l"]
    with connect(corpus_db) as conn:
        _seed_three(conn)
        pending = pending_for_index(conn, index, require_description=True, limit=None)
    failing = f"de|{pending[1]['id']}|{pending[1]['hash']}"
    client = FakeEmbeddingBatches(fail={failing})
    records, done = [], []
    runner = BatchRunner(client, tmp_path, max_per_file=2, poll_seconds=0, record=lambda *a: records.append(a),
                         mark_done=lambda batch_id, status: done.append(batch_id))
    report = embed_openai_batch(corpus_db, index, runner, pending)
    assert report["written"] == 2 and report["failed"] == 1
    assert [len(f) for f in client.submitted] == [2, 1]
    assert all(r[1] == "embed" for r in records) and sum(r[5] for r in records) > 0
    assert done == ["batch-1", "batch-2"]
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.emb_openai_3l").fetchone()["n"] == 2
        assert spent(conn, "embed") == pytest.approx(cost_usd(index.model, 20, 0))
        left = pending_for_index(conn, index, require_description=True, limit=None)
    assert [p["id"] for p in left] == [pending[1]["id"]]


def test_batch_result_for_changed_or_deleted_chunk_is_skipped(corpus_db, tmp_path):
    index = INDEXES["openai-3l"]
    with connect(corpus_db) as conn:
        _seed_three(conn)
        pending = pending_for_index(conn, index, require_description=True, limit=None)
    client = FakeEmbeddingBatches()
    runner = BatchRunner(client, tmp_path, poll_seconds=0)
    [(batch_id, _group)] = list(runner.submit_sequentially(
        [{"custom_id": f"{p['language']}|{p['id']}|{p['hash']}", "method": "POST", "url": "/v1/embeddings",
          "body": {"model": index.model, "input": p["text"]}} for p in pending], "embed", "/v1/embeddings"))
    with connect(corpus_db) as conn:       # the process died; meanwhile one chunk changed and one vanished
        conn.execute("update corpus.chunk set description = 'neu' where id = %s", (pending[0]["id"],))
        conn.execute("delete from corpus.document where id = (select document_id from corpus.chunk where id = %s)",
                     (pending[2]["id"],))
    report = resume_embed_batches(corpus_db, index, BatchRunner(client, tmp_path, poll_seconds=0), [batch_id])
    assert report["written"] == 1 and report["failed"] == 0 and report["stale"] == 2
    with connect(corpus_db) as conn:
        ids = [r["chunk_id"] for r in conn.execute("select chunk_id from corpus.emb_openai_3l")]
    assert ids == [pending[1]["id"]]


def test_hnsw_build_sets_maintenance_memory_and_workers(corpus_db, monkeypatch):
    """Parallel HNSW builds exhaust Docker's 64 MB /dev/shm, so workers default to 0 (serial)."""
    import contextlib

    from swiss_grounding.corpus import embed

    seen = []

    @contextlib.contextmanager
    def spying_connect(url):
        with connect(url) as conn:
            yield conn
            seen.append(conn.execute(
                "select current_setting('maintenance_work_mem') as mem, "
                "current_setting('max_parallel_maintenance_workers') as workers").fetchone())

    monkeypatch.setattr(embed, "connect", spying_connect)
    build_vector_indexes(corpus_db, INDEXES["openai-3l"])
    build_vector_indexes(corpus_db, INDEXES["openai-3l"], parallel_workers=2, maintenance_work_mem="256MB")
    assert seen == [{"mem": "1GB", "workers": "0"}, {"mem": "256MB", "workers": "2"}]


def test_hnsw_indexes_are_built_per_language(corpus_db):
    build_vector_indexes(corpus_db, INDEXES["bge-m3"])
    with connect(corpus_db) as conn:
        names = {r["indexname"] for r in conn.execute(
            "select indexname from pg_indexes where schemaname = 'corpus' and indexname like 'emb_bge_m3_%%_hnsw'")}
    assert {f"emb_bge_m3_{lang}_hnsw" for lang in ("de", "fr", "it", "en", "rm")} <= names
    with connect(corpus_db) as conn:
        sparse = {r["indexname"] for r in conn.execute(
            "select indexname from pg_indexes where schemaname = 'corpus' and indexname like '%%_sparse_hnsw'")}
    assert len(sparse) == 5
