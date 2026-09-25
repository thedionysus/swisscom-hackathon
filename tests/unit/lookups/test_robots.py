import httpx
import pytest

from swiss_grounding.lookups import robots as robots_module
from swiss_grounding.lookups.connections import find_connections
from swiss_grounding.lookups.robots import (
    RobotsCache,
    RobotsDisallowed,
    RobotsTransport,
    robots_transport,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def robots_txt(monkeypatch):
    """Serve robots.txt from a dict {root: (status, body)} and count the fetches."""
    served, fetches = {}, []

    def fake_load(http, root):
        fetches.append(root)
        status, body = served[root]
        if status >= 500:
            return robots_module.Protego.parse("User-agent: *\nDisallow: /\n"), f"HTTP {status}"
        return robots_module.Protego.parse(body), None

    monkeypatch.setattr(robots_module, "load_robots", fake_load)
    return served, fetches


def upstream(calls):
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"connections": []})
    return httpx.MockTransport(handler)


def test_an_allowed_request_goes_through(robots_txt):
    served, _ = robots_txt
    served["https://transport.opendata.ch"] = (200, "User-agent: *\nDisallow:\n")
    calls = []
    transport = RobotsTransport(RobotsCache("ua", 5), inner=upstream(calls))
    with httpx.Client(transport=transport, base_url="https://transport.opendata.ch/v1") as client:
        assert client.get("/connections").status_code == 200
    assert calls == ["https://transport.opendata.ch/v1/connections"]


def test_a_disallowed_request_is_never_sent(robots_txt):
    served, _ = robots_txt
    served["https://transport.opendata.ch"] = (200, "User-agent: *\nDisallow: /v1\n")
    calls = []
    transport = RobotsTransport(RobotsCache("ua", 5), inner=upstream(calls))
    with httpx.Client(transport=transport, base_url="https://transport.opendata.ch/v1") as client, \
            pytest.raises(RobotsDisallowed):
        client.get("/connections")
    assert calls == []


def test_a_lookup_reports_a_disallowed_source_as_unavailable(robots_txt):
    served, _ = robots_txt
    served["https://transport.opendata.ch"] = (200, "User-agent: *\nDisallow: /\n")
    transport = RobotsTransport(RobotsCache("ua", 5), inner=upstream([]))
    with httpx.Client(transport=transport, base_url="https://transport.opendata.ch/v1") as client:
        out = find_connections(client, origin="A", destination="B", date=None, time=None, limit=4)
    assert out["status"] == "source_unavailable"
    assert "RobotsDisallowed" in out["message"]


def test_robots_txt_is_read_once_a_day_per_host(robots_txt):
    served, fetches = robots_txt
    served["https://www.bwo.admin.ch"] = (200, "User-agent: *\nDisallow:\n")
    clock = FakeClock()
    cache = RobotsCache("ua", 5, clock=clock)
    assert cache.allows("https://www.bwo.admin.ch/de/referenzzinssatz")
    assert cache.allows("https://www.bwo.admin.ch/de/other")
    assert fetches == ["https://www.bwo.admin.ch"]
    clock.now = robots_module.ROBOTS_MAX_AGE_SECONDS + 1
    cache.allows("https://www.bwo.admin.ch/de/referenzzinssatz")
    assert len(fetches) == 2


def test_an_unreachable_robots_txt_disallows_and_is_asked_again_soon(robots_txt):
    served, fetches = robots_txt
    served["https://api3.geo.admin.ch"] = (503, "")
    clock = FakeClock()
    cache = RobotsCache("ua", 5, clock=clock)
    assert not cache.allows("https://api3.geo.admin.ch/rest/services/api/SearchServer")
    served["https://api3.geo.admin.ch"] = (200, "User-agent: *\nDisallow: /dev\n")
    clock.now = robots_module.ROBOTS_RETRY_SECONDS + 1
    assert cache.allows("https://api3.geo.admin.ch/rest/services/api/SearchServer")
    assert len(fetches) == 2


def test_respect_robots_off_uses_the_default_transport():
    assert robots_transport(None) is None
