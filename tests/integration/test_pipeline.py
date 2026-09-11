import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.llm import FakeLLM
from swiss_grounding.ingest.models import FetchedDocument, FetchError, FetchResult, Section
from swiss_grounding.ingest.pipeline import run_ingest
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import load_sources, upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration


class StubFetcher:
    def __init__(self, result):
        self.result = result
        self.known_seen = None

    def fetch(self, source, known):
        self.known_seen = dict(known)
        return self.result


class BrokenLLM(FakeLLM):
    def translate(self, text, source_language):
        raise RuntimeError("llm down")


def page(url, text, language="de"):
    return FetchedDocument(source_id="zh_ch", url=url, title="Hunde", language=language,
                           sections=(Section("Hunde", None, text),))


@pytest.fixture
def ctx():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document, fetch_state restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        tree = load_tree(conn)
        source = next(s for s in load_sources(conn) if s.id == "zh_ch")
    return u, tree, source


def test_full_run_persists_and_reports(ctx):
    u, tree, source = ctx
    result = FetchResult(documents=(page("https://www.zh.ch/a", "Hunde in Zürich."), page("https://www.zh.ch/b", "Katzen.")),
                         errors=(FetchError("https://www.zh.ch/c", "timeout"),))
    with connect(u) as conn:
        report = run_ingest(conn, source, StubFetcher(result), FakeLLM(), FakeEmbedder(8), tree, run_id="r1")
        docs = conn.execute("select url, extent_id, status from document order by url").fetchall()
    assert (report.added, report.modified, report.unchanged, report.withdrawn, report.failed) == (2, 0, 0, 0, 1)
    assert [d["extent_id"] for d in docs] == ["CH-ZH-261", "CH-ZH"]     # narrowed for the Zürich page
    assert report.errors[0].reason == "timeout"


def test_second_run_passes_known_urls_and_handles_unchanged_and_gone(ctx):
    u, tree, source = ctx
    first = FetchResult(documents=(page("https://www.zh.ch/a", "Hunde."), page("https://www.zh.ch/b", "Katzen.")))
    with connect(u) as conn:
        run_ingest(conn, source, StubFetcher(first), FakeLLM(), FakeEmbedder(8), tree, run_id="r1")
        fetcher = StubFetcher(FetchResult(documents=(page("https://www.zh.ch/a", "Hunde neu."),),
                                          unchanged_urls=(), gone_urls=("https://www.zh.ch/b",)))
        report = run_ingest(conn, source, fetcher, FakeLLM(), FakeEmbedder(8), tree, run_id="r2")
        statuses = {r["url"]: r["status"] for r in conn.execute("select url, status from document where version = 1").fetchall()}
    assert set(fetcher.known_seen) == {"https://www.zh.ch/a", "https://www.zh.ch/b"}
    assert (report.added, report.modified, report.withdrawn) == (0, 1, 1)
    assert statuses["https://www.zh.ch/a"] == "superseded" and statuses["https://www.zh.ch/b"] == "withdrawn"


def test_enrichment_failure_isolates_document(ctx):
    u, tree, source = ctx
    result = FetchResult(documents=(page("https://www.zh.ch/a", "Hunde."), page("https://www.zh.ch/en", "Dogs.", language="en")))
    with connect(u) as conn:
        report = run_ingest(conn, source, StubFetcher(result), BrokenLLM(), FakeEmbedder(8), tree, run_id="r1")
        docs = conn.execute("select url from document").fetchall()
    assert report.failed == 1 and report.added == 1
    assert [d["url"] for d in docs] == ["https://www.zh.ch/en"]
    assert "llm down" in report.errors[0].reason
