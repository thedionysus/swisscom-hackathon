import httpx

from swiss_grounding.lookups.connections import find_connections

REPLY = {"connections": [{
    "from": {"station": {"name": "Zürich HB"}, "departure": "2026-09-24T10:02:00+0200", "platform": "7"},
    "to": {"station": {"name": "Bern"}, "arrival": "2026-09-24T10:58:00+0200", "platform": "5"},
    "duration": "00d00:56:00", "transfers": 0, "products": ["IC 1"]}]}


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://transport.opendata.ch/v1")


def test_returns_trimmed_connections_with_the_source():
    def handler(request):
        assert request.url.params["from"] == "Zürich HB" and request.url.params["limit"] == "4"
        return httpx.Response(200, json=REPLY)
    out = find_connections(client(handler), origin="Zürich HB", destination="Bern", date=None, time=None, limit=4)
    assert out["status"] == "results"
    assert out["connections"][0] == {"departure": "2026-09-24T10:02:00+0200", "arrival": "2026-09-24T10:58:00+0200",
                                     "from": "Zürich HB", "to": "Bern", "platform": "7", "duration": "00d00:56:00",
                                     "transfers": 0, "products": ["IC 1"]}
    assert out["source_url"].startswith("https://transport.opendata.ch")


def test_timeout_is_source_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("slow")
    out = find_connections(client(handler), origin="A", destination="B", date=None, time=None, limit=4)
    assert out["status"] == "source_unavailable" and "timetable service" in out["message"]


def test_no_connection_is_no_evidence():
    out = find_connections(client(lambda r: httpx.Response(200, json={"connections": []})),
                           origin="A", destination="B", date=None, time=None, limit=4)
    assert out["status"] == "no_evidence"
