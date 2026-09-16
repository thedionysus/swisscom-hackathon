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
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights

pytestmark = pytest.mark.integration
CORPUS = Path(__file__).parent.parent / "fixtures" / "probe_corpus.json"
FROZEN_TODAY = date(2026, 9, 16)
EMBEDDING_DIM = 8


class NoGeo:
    """Structural probes never call GeoAdmin; anything not in the tree must be unresolvable."""

    def search_communes(self, text):
        return ()


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
        database_url=url, tree=tree, resolver=LocationResolver(tree, NoGeo()),
        embedder=FakeEmbedder(dim=EMBEDDING_DIM), weights=RerankWeights(),
        today=lambda: FROZEN_TODAY,
    )


def _params():
    for tier, probe in load_all_probes(PROBE_DIR):
        if probe.kind != "structural":
            continue
        marks = (
            [pytest.mark.xfail(strict=True, reason=f"red: {probe.failure_class}")]
            if probe.status == "red" else []
        )
        yield pytest.param(probe, id=f"{tier}/{probe.id}", marks=marks)


@pytest.mark.parametrize("probe", list(_params()))
def test_structural_probe(core, probe):
    result = run_probe(probe, core, FROZEN_TODAY, git_commit=None)
    assert result.passed, "\n".join(result.failures)
