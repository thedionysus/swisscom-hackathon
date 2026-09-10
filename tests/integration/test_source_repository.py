import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import load_sources, upsert_sources

pytestmark = pytest.mark.integration


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        upsert_locations(conn, seed_locations())
    return u


def test_upsert_and_load_sources(url):
    seeds = load_seed_sources()
    with connect(url) as conn:
        upsert_sources(conn, seeds)
        upsert_sources(conn, seeds)
        loaded = load_sources(conn)
    assert {s.id for s in loaded} == {s.id for s in seeds}
    fedlex = next(s for s in loaded if s.id == "fedlex")
    assert fedlex.fetch_config["sr_numbers"][0] == "451"
    assert fedlex.allow_narrowing is False
