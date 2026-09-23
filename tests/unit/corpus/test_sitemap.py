import httpx

from swiss_grounding.corpus.connectors import sitemap
from swiss_grounding.corpus.connectors.politeness import HostThrottle
from swiss_grounding.corpus.connectors.sitemap import collect_sitemap_urls


def _collect(client: httpx.Client, url: str):
    return collect_sitemap_urls(client, [url], [], 10, accept=lambda u: True, fetchable=lambda u: True,
                                before=lambda u: None, throttle=HostThrottle(), sleep=lambda s: None)


def test_plain_sitemap_over_the_size_cap_is_an_error(monkeypatch):
    monkeypatch.setattr(sitemap, "MAX_SITEMAP_BYTES", 100)
    body = b"<urlset>" + b"<url><loc>https://x.ch/a</loc></url>" * 20 + b"</urlset>"
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))
    seeds = _collect(client, "https://x.ch/sitemap.xml")
    assert seeds.urls == ()
    assert seeds.errors == (("https://x.ch/sitemap.xml", "sitemap larger than 100 bytes"),)


def test_sitemap_under_the_cap_is_read():
    body = b"<urlset><url><loc>https://x.ch/a</loc></url></urlset>"
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))
    assert _collect(client, "https://x.ch/sitemap.xml").urls == ("https://x.ch/a",)


def test_sitemap_429_is_retried_after_retry_after():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "2"})
        return httpx.Response(200, content=b"<urlset><url><loc>https://x.ch/a</loc></url></urlset>")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleeps: list[float] = []
    seeds = collect_sitemap_urls(client, ["https://x.ch/sitemap.xml"], [], 10, accept=lambda u: True,
                                 fetchable=lambda u: True, before=lambda u: None, throttle=HostThrottle(),
                                 sleep=sleeps.append)
    assert seeds.urls == ("https://x.ch/a",)
    assert calls["n"] == 2
    assert 2.0 in sleeps


def test_sitemap_three_429s_become_an_error():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"retry-after": "1"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    seeds = collect_sitemap_urls(client, ["https://x.ch/sitemap.xml"], [], 10, accept=lambda u: True,
                                 fetchable=lambda u: True, before=lambda u: None, throttle=HostThrottle(),
                                 sleep=lambda s: None)
    assert seeds.urls == ()
    assert calls["n"] == 3
    assert any("HTTP 429" in reason for _, reason in seeds.errors)
