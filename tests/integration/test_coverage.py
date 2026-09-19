"""Coverage signal on search results (ADR 0001): setup mirrors test_probes_structural."""
import os
from datetime import date
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import normalize
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.models import QueryRequest
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights

pytestmark = pytest.mark.integration
CORPUS = Path(__file__).parent.parent / "fixtures" / "probe_corpus.json"
FROZEN_TODAY = date(2026, 9, 16)
EMBEDDING_DIM = 8

CANNED_GEOADMIN: dict[str, tuple[GeoAdminHit, ...]] = {
    "wiedikon": (GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),),
    "zug": (GeoAdminHit(bfs_id=1711, label="Zug (ZG)"),),
}


class CannedGeo:
    def search_communes(self, text: str) -> tuple[GeoAdminHit, ...]:
        key = normalize(text)
        if key not in CANNED_GEOADMIN:
            raise KeyError(f"no canned GeoAdmin answer for {text!r}")
        return CANNED_GEOADMIN[key]


@pytest.fixture(scope="module")
def core():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=EMBEDDING_DIM)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, CORPUS, FakeEmbedder(dim=EMBEDDING_DIM))
        tree = load_tree(conn)
    return QueryCore(
        database_url=url, tree=tree, resolver=LocationResolver(tree, CannedGeo()),
        embedder=FakeEmbedder(dim=EMBEDDING_DIM), weights=RerankWeights(),
        today=lambda: FROZEN_TODAY,
    )


def test_results_carry_one_coverage_row_per_extent_on_the_path(core):
    resp = core.query(QueryRequest(question="dog leash", location="Wiedikon", categories=("dogs",)))
    assert [r.extent_id for r in resp.coverage] == [
        "CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3", "CH-ZH-261-K3-ALT-WIEDIKON",
    ]
    counts = {r.extent_id: r.documents for r in resp.coverage}
    assert counts["CH"] > 0
    assert counts["CH-ZH-261-K3-ALT-WIEDIKON"] == 0
    assert "no documents" in resp.resolution_note.lower()


def test_coverage_rows_survive_the_mcp_dict(core):
    from swiss_grounding.mcp_server.server import _response_to_dict

    resp = core.query(QueryRequest(question="dog leash", location="Zug"))
    data = _response_to_dict(resp, "concise")
    assert data["coverage"][0]["extent_id"] == "CH"
