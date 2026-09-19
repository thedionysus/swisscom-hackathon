import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import load_tree, prune_locations, upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources

pytestmark = pytest.mark.integration

FAKE_ID = "CH-ZH-999999"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document, location restart identity cascade")
    return u


def _insert_fake_commune(conn, id_=FAKE_ID, bfs_id=999999):
    conn.execute(
        """
        insert into location (id, parent_id, level, bfs_id, lindas_uri, names, path)
        values (%(id)s, 'CH-ZH', 'municipality', %(bfs_id)s, null, '{"labels": {}, "aliases": []}'::jsonb,
                array['CH', 'CH-ZH', %(id)s])
        """,
        {"id": id_, "bfs_id": bfs_id},
    )


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


def test_prune_deletes_unreferenced_stale_commune(url):
    locs = seed_locations()
    with connect(url) as conn:
        upsert_locations(conn, locs)
        _insert_fake_commune(conn)
        report = prune_locations(conn, [loc.id for loc in locs])
        remaining = conn.execute(
            "select count(*) as n from location where id = %s", (FAKE_ID,)
        ).fetchone()["n"]
    assert FAKE_ID in report.deleted
    assert report.kept_referenced == ()
    assert remaining == 0


def test_prune_keeps_referenced_stale_commune(url):
    locs = seed_locations()
    with connect(url) as conn:
        upsert_locations(conn, locs)
        upsert_sources(conn, load_seed_sources())
        _insert_fake_commune(conn)
        source_id = conn.execute("select id from source limit 1").fetchone()["id"]
        conn.execute(
            """
            insert into document (source_id, url, title_original, title_en, language,
                                  extent_id, authority, content_hash)
            values (%s, 'https://example.test/fake', 't', 't', 'en', %s, 'official_info', 'hash123')
            """,
            (source_id, FAKE_ID),
        )
        report = prune_locations(conn, [loc.id for loc in locs])
        remaining = conn.execute(
            "select count(*) as n from location where id = %s", (FAKE_ID,)
        ).fetchone()["n"]
    assert FAKE_ID not in report.deleted
    assert FAKE_ID in report.kept_referenced
    assert remaining == 1


def test_prune_never_touches_seeded_locations(url):
    locs = seed_locations()
    with connect(url) as conn:
        upsert_locations(conn, locs)
        report = prune_locations(conn, [loc.id for loc in locs])
        count = conn.execute("select count(*) as n from location").fetchone()["n"]
    assert report.deleted == ()
    assert report.kept_referenced == ()
    assert count == len(locs)
    assert "CH-ZH-261" in {loc.id for loc in locs}
