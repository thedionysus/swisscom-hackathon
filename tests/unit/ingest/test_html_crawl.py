import httpx

from swiss_grounding.ingest.fetchers.html_crawl import CrawlLimits, HtmlCrawlFetcher
from swiss_grounding.ingest.models import FetchError, KnownUrl
from swiss_grounding.registry.models import Source

PAGE_A = """<html lang="de"><head><title>A</title></head><body><main><h1>A</h1><p>Seite A.</p></main>
<nav><a href="/de/tiere/b.html">B</a><a href="/de/tiere/c.pdf">C</a><a href="/fr/x.html">FR</a>
<a href="https://other.example/x">ext</a><a href="/de/tiere/download">DL</a></nav></body></html>"""
PAGE_B = """<html lang="de"><head><title>B</title></head><body><main><h1>B</h1><p>Seite B.</p>
<a href="/de/tiere/a.html">A</a></main></body></html>"""
ROBOTS = "User-agent: *\nDisallow: /de/tiere/secret\n"


DEFAULT_LIMITS = CrawlLimits(max_pages=10, delay_seconds=0)


def source(**overrides) -> Source:
    base = {"id": "zh_ch", "name": "ZH", "base_url": "https://www.zh.ch", "default_extent_id": "CH-ZH",
            "authority": "official_info", "categories": ("dogs",), "fetch_strategy": "html_crawl",
            "fetch_config": {"path_allowlist": ["/de/tiere"], "start_paths": ["/de/tiere/a.html"]},
            "allow_narrowing": True}
    return Source(**{**base, **overrides})


def make(handler, known=None, limits=DEFAULT_LIMITS):
    http = httpx.Client(transport=httpx.MockTransport(handler), headers={"user-agent": "t"})
    return HtmlCrawlFetcher(http=http, limits=limits), (known or {})


def routes(request, calls):
    calls.append((request.method, str(request.url), request.headers.get("if-none-match")))
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(200, text=ROBOTS)
    if path == "/de/tiere/a.html":
        return httpx.Response(200, text=PAGE_A, headers={"etag": '"a1"', "last-modified": "Mon, 01 Sep 2026 00:00:00 GMT"})
    if path == "/de/tiere/b.html":
        if request.headers.get("if-none-match") == '"b1"':
            return httpx.Response(304)
        return httpx.Response(200, text=PAGE_B, headers={"etag": '"b1"'})
    if path == "/de/tiere/gone.html":
        return httpx.Response(404)
    if path == "/de/tiere/download":
        return httpx.Response(200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"})
    return httpx.Response(404)


def test_crawls_allowlisted_same_domain_html_only():
    calls = []
    fetcher, known = make(lambda r: routes(r, calls))
    result = fetcher.fetch(source(), known)
    urls = sorted(d.url for d in result.documents)
    assert urls == ["https://www.zh.ch/de/tiere/a.html", "https://www.zh.ch/de/tiere/b.html"]
    fetched_paths = {httpx.URL(u).path for _, u, _ in calls}
    assert "/fr/x.html" not in fetched_paths and "/de/tiere/c.pdf" not in fetched_paths
    assert not any("other.example" in u for _, u, _ in calls)
    a = next(d for d in result.documents if d.url.endswith("a.html"))
    assert a.etag == '"a1"' and a.language == "de" and a.title == "A"
    assert a.sections[0].text == "Seite A."


def test_conditional_request_yields_unchanged():
    calls = []
    fetcher, known = make(lambda r: routes(r, calls),
                          known={"https://www.zh.ch/de/tiere/b.html": KnownUrl(etag='"b1"', last_modified=None, content_hash="h")})
    result = fetcher.fetch(source(), known)
    assert "https://www.zh.ch/de/tiere/b.html" in result.unchanged_urls
    assert all(not d.url.endswith("b.html") for d in result.documents)
    assert any(etag == '"b1"' for _, u, etag in calls if u.endswith("b.html"))


def test_known_url_that_is_gone_is_reported():
    calls = []
    fetcher, known = make(lambda r: routes(r, calls),
                          known={"https://www.zh.ch/de/tiere/gone.html": KnownUrl(None, None, "h")})
    result = fetcher.fetch(source(), known)
    assert result.gone_urls == ("https://www.zh.ch/de/tiere/gone.html",)


def test_respects_robots_and_max_pages():
    calls = []
    fetcher, known = make(lambda r: routes(r, calls), limits=CrawlLimits(max_pages=1, delay_seconds=0))
    result = fetcher.fetch(source(fetch_config={"path_allowlist": ["/de/tiere"], "start_paths": ["/de/tiere/a.html", "/de/tiere/secret/x.html"]}), known)
    assert len(result.documents) == 1
    assert not any("/secret/" in u for _, u, _ in calls)


def test_non_html_content_type_is_fetched_but_not_parsed():
    calls = []
    fetcher, known = make(lambda r: routes(r, calls))
    result = fetcher.fetch(source(), known)
    assert any(u.endswith("/de/tiere/download") for _, u, _ in calls)
    assert not any(d.url.endswith("/de/tiere/download") for d in result.documents)
    assert not any(e.url.endswith("/de/tiere/download") for e in result.errors)


def test_http_errors_become_fetch_errors_not_exceptions():
    def boom(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="")
        raise httpx.ConnectError("down")

    fetcher, known = make(boom)
    result = fetcher.fetch(source(), known)
    assert result.documents == ()
    assert result.errors and "down" in result.errors[0].reason


def test_blocked_start_path_is_reported_as_error():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        return httpx.Response(403)

    fetcher, known = make(handler)
    result = fetcher.fetch(source(fetch_config={"path_allowlist": ["/de/tiere"], "start_paths": ["/de/tiere"]}), known)
    assert result.documents == ()
    assert result.errors == (FetchError(url="https://www.zh.ch/de/tiere", reason="HTTP 403"),)


def test_first_time_404_is_reported_as_error_not_gone():
    calls = []
    fetcher, known = make(lambda r: routes(r, calls))
    result = fetcher.fetch(source(fetch_config={"path_allowlist": ["/de/tiere"], "start_paths": ["/de/tiere/gone.html"]}), known)
    assert result.gone_urls == ()
    assert result.errors == (FetchError(url="https://www.zh.ch/de/tiere/gone.html", reason="HTTP 404"),)
