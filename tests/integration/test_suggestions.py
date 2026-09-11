import os

import httpx
import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import load_sources, upsert_sources
from swiss_grounding.registry.suggestions import (
    list_suggestions,
    review_suggestion,
    submit_suggestion,
)

pytestmark = pytest.mark.integration


def reachable(request):
    return httpx.Response(200 if "unreachable" not in str(request.url) else 404)


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate source_suggestion restart identity")
        conn.execute("delete from source where origin <> 'seed'")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    return u


def http():
    return httpx.Client(transport=httpx.MockTransport(reachable))


def test_official_domain_is_auto_approved_into_registry(url):
    with connect(url) as conn:
        s = submit_suggestion(conn, http(), url="https://www.bs.ch/hunde", reason="Basel dog rules",
                              suggested_by="test", proposed_categories=("dogs",))
        sources = {x.id: x for x in load_sources(conn)}
    assert s.status == "approved" and s.domain_class == "official" and s.source_id in sources
    src = sources[s.source_id]
    assert src.default_extent_id == "CH-BS" and src.authority == "official_info"
    assert src.allow_narrowing is True and src.origin == "auto_approved"
    assert src.fetch_config["path_allowlist"] == ["/hunde"] and src.categories == ("dogs",)


def test_non_official_is_pending_then_reviewable(url):
    with connect(url) as conn:
        s = submit_suggestion(conn, http(), url="https://www.sac-cas.ch/de/huetten", reason="SAC huts", suggested_by="t")
        assert s.status == "pending" and s.domain_class == "swiss"
        approved = review_suggestion(conn, s.id, approve=True, reviewer="me", note="ok",
                                     extent_id="CH", authority="institutional", categories=("hiking",))
        rejected_id = submit_suggestion(conn, http(), url="https://www.example.com/x", reason="r", suggested_by="t").id
        rejected = review_suggestion(conn, rejected_id, approve=False, reviewer="me", note="not swiss")
        pending = list_suggestions(conn, status="pending")
        sources = {x.id for x in load_sources(conn)}
    assert approved.status == "approved" and approved.source_id in sources
    assert rejected.status == "rejected" and rejected.review_note == "not swiss"
    assert pending == ()


def test_invalid_duplicate_and_unreachable_are_rejected_with_reasons(url):
    with connect(url) as conn:
        with pytest.raises(ValueError, match="URL"):
            submit_suggestion(conn, http(), url="not a url", reason="r", suggested_by="t")
        with pytest.raises(ValueError, match="already"):
            submit_suggestion(conn, http(), url="https://www.zh.ch/de/x", reason="r", suggested_by="t")
        with pytest.raises(ValueError, match="reachable"):
            submit_suggestion(conn, http(), url="https://www.example.com/unreachable", reason="r", suggested_by="t")
        with pytest.raises(ValueError, match="law"):
            submit_suggestion(conn, http(), url="https://www.sg.ch/x", reason="r", suggested_by="t", proposed_authority="cantonal_law")
