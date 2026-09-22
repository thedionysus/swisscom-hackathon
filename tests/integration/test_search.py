import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.search import hybrid_search

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
    return u


def test_search_filters_by_extent_path(url):
    embedder = FakeEmbedder(dim=8)
    with connect(url) as conn:
        hits = hybrid_search(
            conn, embedder, question="Do I need to leash my dog?",
            extent_path=("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"), as_of=None, top_n=50,
        )
    extents = {h.chunk.extent_id for h in hits}
    assert "CH-BS" not in extents
    assert {"CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"} >= extents
    assert len(hits) >= 5


def test_search_country_only_returns_only_ch(url):
    with connect(url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="leash dog hiking",
            extent_path=("CH",), as_of=None, top_n=50,
        )
    assert {h.chunk.extent_id for h in hits} == {"CH"}


def test_search_as_of_excludes_future_valid_from(url):
    from datetime import date

    with connect(url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="animal welfare",
            extent_path=("CH",), as_of=date(2000, 1, 1), top_n=50,
        )
    identifiers = {h.chunk.identifier for h in hits}
    assert "SR 455 Art. 6" not in identifiers       # valid_from 2008
    assert "SR 704 Art. 1" in identifiers           # valid_from 1987


def test_hit_carries_document_fields(url):
    with connect(url) as conn:
        hits = hybrid_search(conn, FakeEmbedder(dim=8), question="dog", extent_path=("CH",), as_of=None, top_n=5)
    h = hits[0]
    assert h.chunk.url.startswith("https://")
    assert h.chunk.title_en
    assert h.chunk.retrieved_at is not None


def test_search_uses_document_status_not_the_chunk_copy(url):
    """chunk.document_status can drift; the document table is the single source of truth."""
    with connect(url) as conn:
        doc_id = conn.execute(
            "select id from document where extent_id = 'CH' order by id limit 1"
        ).fetchone()["id"]
        conn.execute("update document set status = 'withdrawn' where id = %s", (doc_id,))
        conn.execute(
            "update chunk set document_status = 'current' where document_id = %s", (doc_id,)
        )
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="leash dog hiking",
            extent_path=("CH",), as_of=None, top_n=50,
        )
    assert doc_id not in {h.chunk.document_id for h in hits}


def test_as_of_does_not_admit_a_document_that_records_no_valid_from(url):
    """The D2 defect: `d.valid_from is null or ...` let an undated document satisfy every
    `as_of`. A question about what applied in 2000 came back holding undated web pages,
    presented as the answer, with the acts that do carry dates filtered out around them.

    The second half is the control: those same documents are retrievable when no date is
    asked for, so this is the date filter excluding them and not the query missing them.
    """
    from datetime import date

    with connect(url) as conn:
        dated = hybrid_search(
            conn, FakeEmbedder(dim=8), question="hiking with a dog",
            extent_path=("CH",), as_of=date(2000, 1, 1), top_n=50,
        )
        undated = hybrid_search(
            conn, FakeEmbedder(dim=8), question="hiking with a dog",
            extent_path=("CH",), as_of=None, top_n=50,
        )

    assert all(h.chunk.valid_from is not None for h in dated)
    assert "Hiking with a dog" not in {h.chunk.title_en for h in dated}
    assert "Hiking with a dog" in {h.chunk.title_en for h in undated}


def test_earliest_indexed_version_is_the_oldest_date_as_of_can_answer_for(url):
    """It is a property of the corpus, never a constant: the index holds only current
    consolidations, so the oldest `valid_from` is the furthest back any date can reach."""
    from datetime import date

    from swiss_grounding.retrieval.search import earliest_indexed_version

    with connect(url) as conn:
        assert earliest_indexed_version(conn) == date(1987, 1, 1)


def test_earliest_indexed_version_is_none_when_nothing_records_a_date(url):
    """Then no `as_of` is answerable at all, and the caller has to be told that rather
    than handed a boundary that does not exist."""
    from swiss_grounding.retrieval.search import earliest_indexed_version

    with connect(url) as conn:
        conn.execute("update document set valid_from = null")
        assert earliest_indexed_version(conn) is None


def test_every_hit_carries_a_distance_including_the_lexical_only_ones(url):
    """Task 9: the tier is decided by the chunk's cosine distance, so a hit that only the
    lexical arm retrieved still needs one. A one-word question (`websearch_to_tsquery`
    ANDs its terms, so a sentence matches nothing here) with a tiny `top_n` makes the two
    arms disagree, and at least one hit reaches the caller without a dense rank."""
    with connect(url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="dog",
            extent_path=("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"), as_of=None, top_n=2,
        )
    assert any(h.dense_rank is None for h in hits), "fixture no longer yields a lexical-only hit"
    assert all(h.distance is not None for h in hits)
    assert all(0.0 <= h.distance <= 2.0 for h in hits)


def test_a_dense_hit_keeps_the_distance_the_dense_arm_measured(url):
    """The backfill must agree with `DENSE_SQL` to the bit, or a citation's distance would
    depend on which arm happened to retrieve it."""
    from swiss_grounding.retrieval.search import distances_for

    embedder = FakeEmbedder(dim=8)
    vector = embedder.embed(["dog"])[0]
    with connect(url) as conn:
        hits = hybrid_search(
            conn, embedder, question="dog",
            extent_path=("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"), as_of=None, top_n=50,
        )
        dense = [h for h in hits if h.dense_rank is not None]
        refetched = distances_for(conn, vector, [h.chunk.chunk_id for h in dense])
    assert dense
    assert {h.chunk.chunk_id: h.distance for h in dense} == refetched


def test_distances_for_omits_an_id_it_finds_no_row_for(url):
    """A missing id gets no entry rather than a fabricated distance: the caller has to see
    "not measured" as its own outcome, which is what `Hit.distance is None` means."""
    from swiss_grounding.retrieval.search import distances_for

    vector = FakeEmbedder(dim=8).embed(["leash"])[0]
    with connect(url) as conn:
        assert distances_for(conn, vector, []) == {}
        assert distances_for(conn, vector, [10**9]) == {}
