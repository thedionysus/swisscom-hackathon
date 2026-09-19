import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.seed import seed_locations

pytestmark = pytest.mark.integration


def test_seeded_tree_resolves_winterthur_by_alias_and_postal_code():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        upsert_locations(conn, seed_locations())
        tree = load_tree(conn)
    assert tree.find("Winterthur")[0].id == "CH-ZH-230"
    assert tree.find("8400")[0].id == "CH-ZH-230"
    assert {n.id for n in tree.find("Wil")} == {"CH-ZH-71", "CH-SG-3427"}
