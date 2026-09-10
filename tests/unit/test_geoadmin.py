import httpx
import pytest

from swiss_grounding.locations.geoadmin import GeoAdminClient, GeoAdminHit

SAMPLE = {
    "results": [
        {"attrs": {"origin": "gg25", "label": "<b>Uster (ZH)</b>", "featureId": "198",
                   "detail": "uster zh", "lat": 47.35, "lon": 8.72}},
        {"attrs": {"origin": "address", "label": "Bahnhofstrasse 1 Uster", "featureId": "x"}},
    ]
}


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="https://geo.test")
    return GeoAdminClient(http=http)


def test_parses_commune_hits_only():
    def handler(request):
        assert request.url.path == "/rest/services/api/SearchServer"
        assert request.url.params["searchText"] == "Uster"
        return httpx.Response(200, json=SAMPLE)

    hits = make_client(handler).search_communes("Uster")
    assert hits == (GeoAdminHit(bfs_id=198, label="Uster (ZH)"),)


def test_http_error_raises_clear_message():
    def handler(request):
        return httpx.Response(503)

    with pytest.raises(RuntimeError, match="GeoAdmin"):
        make_client(handler).search_communes("Uster")


def test_malformed_payload_is_skipped():
    def handler(request):
        return httpx.Response(200, json={"results": [{"attrs": {"origin": "gg25"}}]})

    assert make_client(handler).search_communes("x") == ()
