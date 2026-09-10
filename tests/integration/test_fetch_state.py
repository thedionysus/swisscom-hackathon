import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fetch_state import forget_known, load_known, save_known, touch_known
from swiss_grounding.ingest.models import KnownUrl
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources

pytestmark = pytest.mark.integration


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate fetch_state")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    return u


def test_save_and_load_known_urls_per_source(url):
    with connect(url) as conn:
        save_known(conn, "zh_ch", "https://www.zh.ch/a", KnownUrl(etag='"1"', last_modified="L", content_hash="h1"))
        save_known(conn, "zh_ch", "https://www.zh.ch/a", KnownUrl(etag='"2"', last_modified="L", content_hash="h1"))
        save_known(conn, "ch_ch", "https://www.ch.ch/b", KnownUrl(None, None, "h2"))
        zh = load_known(conn, "zh_ch")
    assert zh == {"https://www.zh.ch/a": KnownUrl(etag='"2"', last_modified="L", content_hash="h1")}


def test_touch_and_forget(url):
    with connect(url) as conn:
        save_known(conn, "zh_ch", "https://www.zh.ch/a", KnownUrl(None, None, "h1"))
        conn.execute("update fetch_state set last_seen_at = '2000-01-01' where url = 'https://www.zh.ch/a'")
        touch_known(conn, "https://www.zh.ch/a")
        year = conn.execute("select extract(year from last_seen_at) as y from fetch_state").fetchone()["y"]
        forget_known(conn, "https://www.zh.ch/a")
        remaining = load_known(conn, "zh_ch")
    assert year > 2000 and remaining == {}
