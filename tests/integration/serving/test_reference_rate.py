from datetime import timedelta

import httpx
import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.reference_rate import reference_rate
from tests.unit.lookups.test_reference_rate import HTML

pytestmark = pytest.mark.integration
URL = "https://www.bwo.admin.ch/de/referenzzinssatz"


def test_live_value_is_cached_and_returned_when_the_source_is_down(serving_db):
    up = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=HTML)))
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with connect(serving_db) as conn:
        assert reference_rate(conn, up, URL)["rate_percent"] == 1.25
        assert reference_rate(conn, down, URL)["status"] == "results"        # fresh cache, no fetch
        out = reference_rate(conn, down, URL, max_age=timedelta(0))          # stale: fetch fails
    assert out["status"] == "source_unavailable" and out["rate_percent"] == 1.25
    assert "last value" in out["message"]


def test_down_without_cache(serving_db):
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with connect(serving_db) as conn:
        out = reference_rate(conn, down, URL)
    assert out["status"] == "source_unavailable" and "rate_percent" not in out
