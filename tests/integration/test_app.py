import os

import pytest

from swiss_grounding.app import build_query_core
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations

pytestmark = pytest.mark.integration


def test_build_query_core_loads_tree_from_db():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        upsert_locations(conn, seed_locations())
    settings = Settings(database_url=url, embedding_backend="fake", embedding_dim=8)
    core = build_query_core(settings)
    assert core.tree.by_bfs_id(261).id == "CH-ZH-261"
    assert core.embedder.dim == 8
