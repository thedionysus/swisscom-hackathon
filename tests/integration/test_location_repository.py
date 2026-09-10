import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.seed import seed_locations

pytestmark = pytest.mark.integration


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    return u


def test_upsert_and_load_roundtrip(url):
    locs = seed_locations()
    with connect(url) as conn:
        upsert_locations(conn, locs)
        tree = load_tree(conn)
    assert len(tree.all()) == len(locs)
    assert tree.path("CH-ZH-261-K3") == ("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3")
    assert tree.find("Wiedikon")[0].id == "CH-ZH-261-K3-ALT-WIEDIKON"


def test_upsert_is_idempotent(url):
    locs = seed_locations()
    with connect(url) as conn:
        upsert_locations(conn, locs)
        upsert_locations(conn, locs)
        count = conn.execute("select count(*) as n from location").fetchone()["n"]
    assert count == len(locs)
