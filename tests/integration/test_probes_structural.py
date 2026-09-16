"""Every structural probe, run on the fixture corpus with a frozen clock.

Red probes are strict xfails: when the fix pass makes one pass, pytest reports XPASS(strict)
as a failure, which is the signal to flip the probe's status to green in its YAML file."""
import os
from datetime import date
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.evals.probe_loader import PROBE_DIR, load_all_probes
from swiss_grounding.evals.runner import run_probe
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import normalize
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights

pytestmark = pytest.mark.integration
CORPUS = Path(__file__).parent.parent / "fixtures" / "probe_corpus.json"
FROZEN_TODAY = date(2026, 9, 16)
EMBEDDING_DIM = 8

# What the live GeoAdmin SearchServer answered for each probe input on 2026-09-16.
# Two entries are constructed rather than captured: zurichsee uses bfs_id 0 as a
# no-commune sentinel so the resolver falls back to the (ZH) label, and nowhere
# pairs a canton label with a commune-range id to exercise the overlap rejection.
CANNED_GEOADMIN: dict[str, tuple[GeoAdminHit, ...]] = {
    "winterthur": (GeoAdminHit(bfs_id=230, label="Winterthur (ZH)"),),
    "gemeinde winterthur": (GeoAdminHit(bfs_id=230, label="Winterthur (ZH)"),),
    "uster": (GeoAdminHit(bfs_id=198, label="Uster (ZH)"),),
    "kloten": (GeoAdminHit(bfs_id=62, label="Kloten (ZH)"),),
    "wetzikon": (GeoAdminHit(bfs_id=121, label="Wetzikon (ZH)"),),
    "bulach": (GeoAdminHit(bfs_id=53, label="Bülach (ZH)"),),
    "dietikon": (GeoAdminHit(bfs_id=243, label="Dietikon (ZH)"),),
    "wil": (GeoAdminHit(bfs_id=27, label="Wil (ZH)"),),
    "wil zh": (GeoAdminHit(bfs_id=27, label="Wil (ZH)"),),
    "affoltern am albis": (GeoAdminHit(bfs_id=951, label="Affoltern im Emmental (BE)"),),
    "zurich oberland": (GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),),
    "zurichsee": (GeoAdminHit(bfs_id=0, label="Zürichsee (ZH)"),),
    "zurich airport": (GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),),
    "zurzach": (GeoAdminHit(bfs_id=4324, label="Zurzach (AG)"),),
    "nowhere": (GeoAdminHit(bfs_id=1502, label="Nidwalden (NW)"),),
    "8400": (),
    "winterthurr": (),
    "quartier hard": (),
}


class CannedGeo:
    """Replays what the live GeoAdmin SearchServer answered for each probe input on 2026-09-16.
    Two entries are constructed rather than captured: zurichsee uses bfs_id 0 as a no-commune
    sentinel so the resolver falls back to the (ZH) label, and nowhere pairs a canton label
    with a commune-range id to exercise the overlap rejection. Unlisted inputs raise so gaps
    are loud."""

    def search_communes(self, text: str) -> tuple[GeoAdminHit, ...]:
        key = normalize(text)
        if key not in CANNED_GEOADMIN:
            raise KeyError(f"no canned GeoAdmin answer for {text!r}; capture it from the live service and add it")
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


def _params():
    for tier, probe in load_all_probes(PROBE_DIR):
        if probe.kind != "structural":
            continue
        marks = (
            [pytest.mark.xfail(
                strict=True,
                reason=f"red: {probe.failure_class if probe.failure_class != 'none' else probe.id}",
            )]
            if probe.status == "red" else []
        )
        yield pytest.param(probe, id=f"{tier}/{probe.id}", marks=marks)


@pytest.mark.parametrize("probe", list(_params()))
def test_structural_probe(core, probe):
    result = run_probe(probe, core, FROZEN_TODAY, git_commit=None)
    assert result.passed, "\n".join(result.failures)
