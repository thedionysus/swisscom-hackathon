import httpx

from swiss_grounding.corpus.connectors.html import CrawlPolicy, HtmlConnector
from swiss_grounding.corpus.models import KnownState, SourceSpec

PAGES = {
    "https://www.x.ch/de/": """<html lang="de"><head><link rel="alternate" hreflang="fr" href="https://www.x.ch/fr/">
      </head><body><main><h1>Start</h1><p>Willkommen.</p><a href="/de/hund">Hund</a>
      <a href="/de/merkblatt.pdf">Merkblatt</a><a href="https://elsewhere.ch/">x</a></main></body></html>""",
    "https://www.x.ch/fr/": """<html lang="fr"><head><link rel="alternate" hreflang="de" href="https://www.x.ch/de/">
      </head><body><main><h1>Accueil</h1><p>Bienvenue.</p></main></body></html>""",
    "https://www.x.ch/de/hund": """<html lang="de"><body><main><h1>Hund</h1><h2>Leine</h2><p>Leinenpflicht im Wald.</p>
      </main></body></html>""",
}


def _spec(**config):
    base = {"start_urls": ["https://www.x.ch/de/"], "allow_prefixes": ["https://www.x.ch/de/", "https://www.x.ch/fr/"]}
    base.update(config)
    return SourceSpec(id="x", name="X", publisher="X", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de", "fr"), config=base)


def _client(robots="User-agent: *\nAllow: /\n", seen=None, pages=None, robots_response=None,
           conditional_etag=None, redirects=None):
    pages = pages if pages is not None else PAGES
    redirects = redirects or {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url.endswith("/robots.txt"):
            if robots_response is not None:
                return robots_response(request)
            return httpx.Response(200, text=robots)
        if url in redirects:
            return httpx.Response(302, headers={"location": redirects[url]})
        if url in pages:
            if conditional_etag is not None and request.headers.get("if-none-match") == conditional_etag:
                return httpx.Response(304)
            return httpx.Response(200, text=pages[url], headers={"content-type": "text/html", "etag": '"e1"'})
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_crawls_pages_and_groups_language_versions():
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(), known={})
    by_url = {d.url: d for d in result.documents}
    assert set(by_url) == set(PAGES)
    assert by_url["https://www.x.ch/de/"].work_key == by_url["https://www.x.ch/fr/"].work_key
    hund = by_url["https://www.x.ch/de/hund"]
    assert hund.sections[0].breadcrumb == ("Hund", "Leine")
    assert hund.sections[0].align_key == "de:0"
    assert hund.etag == '"e1"'


def test_pdf_links_are_discovered_not_fetched():
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(), known={})
    assert [p.url for p in result.pdfs] == ["https://www.x.ch/de/merkblatt.pdf"]
    assert result.pdfs[0].title_hint == "Merkblatt"


def test_robots_disallow_is_respected_only_when_switched_on():
    robots = "User-agent: *\nDisallow: /de/hund\n"
    on = HtmlConnector(_client(robots), CrawlPolicy(True, 0)).run(_spec(), known={})
    off = HtmlConnector(_client(robots), CrawlPolicy(False, 0)).run(_spec(), known={})
    assert "https://www.x.ch/de/hund" not in {d.url for d in on.documents}
    assert "https://www.x.ch/de/hund" in {d.url for d in off.documents}


def test_robots_file_is_not_requested_when_switched_off():
    seen: list[str] = []
    HtmlConnector(_client(seen=seen), CrawlPolicy(False, 0)).run(_spec(), known={})
    assert not any(u.endswith("/robots.txt") for u in seen)


def test_new_pages_are_visited_before_known_ones_are_rechecked():
    known = {f"https://www.x.ch/de/old{i}": KnownState(None, None, "h") for i in range(5)}
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(max_pages=3), known=known)
    assert {d.url for d in result.documents} == set(PAGES)


def test_known_page_gone_is_reported():
    known = {"https://www.x.ch/de/old": KnownState(None, None, "h")}
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(), known=known)
    assert "https://www.x.ch/de/old" in result.gone_urls


def test_work_key_only_shared_between_symmetric_alternates():
    """A1: fr alternate points every German page at the same French homepage, which lists only
    one of them back. The two German pages must not be grouped into one translation group, while
    the genuinely symmetric de/fr pair still is."""
    pages = {
        "https://www.y.ch/de/a": """<html lang="de"><head>
          <link rel="alternate" hreflang="fr" href="https://www.y.ch/fr/"></head>
          <body><main><h1>A</h1><p>Text A.</p></main></body></html>""",
        "https://www.y.ch/de/b": """<html lang="de"><head>
          <link rel="alternate" hreflang="fr" href="https://www.y.ch/fr/"></head>
          <body><main><h1>B</h1><p>Text B.</p></main></body></html>""",
        "https://www.y.ch/fr/": """<html lang="fr"><head>
          <link rel="alternate" hreflang="de" href="https://www.y.ch/de/a"></head>
          <body><main><h1>Accueil</h1><p>Bienvenue.</p></main></body></html>""",
    }
    spec = SourceSpec(id="y", name="Y", publisher="Y", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de", "fr"),
                      config={"start_urls": ["https://www.y.ch/de/a", "https://www.y.ch/de/b"],
                              "allow_prefixes": ["https://www.y.ch/"]})
    result = HtmlConnector(_client(pages=pages), CrawlPolicy(True, 0)).run(spec, known={})
    by_url = {d.url: d for d in result.documents}
    assert by_url["https://www.y.ch/de/a"].work_key == by_url["https://www.y.ch/fr/"].work_key
    assert by_url["https://www.y.ch/de/b"].work_key != by_url["https://www.y.ch/de/a"].work_key
    assert by_url["https://www.y.ch/de/b"].work_key == "html:https://www.y.ch/de/b"


def test_work_key_falls_back_when_symmetric_component_shares_a_language():
    """A1: even a genuinely mutual pair falls back to per-page keys if both members are the
    same language (never a real translation group)."""
    pages = {
        "https://www.z.ch/de/a": """<html lang="de"><head>
          <link rel="alternate" hreflang="de" href="https://www.z.ch/de/b"></head>
          <body><main><h1>A</h1><p>Text A.</p></main></body></html>""",
        "https://www.z.ch/de/b": """<html lang="de"><head>
          <link rel="alternate" hreflang="de" href="https://www.z.ch/de/a"></head>
          <body><main><h1>B</h1><p>Text B.</p></main></body></html>""",
    }
    spec = SourceSpec(id="z", name="Z", publisher="Z", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",),
                      config={"start_urls": ["https://www.z.ch/de/a"], "allow_prefixes": ["https://www.z.ch/"]})
    result = HtmlConnector(_client(pages=pages), CrawlPolicy(True, 0)).run(spec, known={})
    by_url = {d.url: d for d in result.documents}
    assert by_url["https://www.z.ch/de/a"].work_key == "html:https://www.z.ch/de/a"
    assert by_url["https://www.z.ch/de/b"].work_key == "html:https://www.z.ch/de/b"


# --- 304 must not kill discovery -------------------------------------------------------------

def test_known_start_page_still_discovers_its_linked_page():
    """A start-page URL that is also `known` must be fetched in full, not conditionally: a 304
    from the server would otherwise stop us from ever seeing the pages it links to."""
    known = {"https://www.x.ch/de/": KnownState(etag='"e1"', last_modified=None, content_hash="h")}
    result = HtmlConnector(_client(conditional_etag='"e1"'), CrawlPolicy(True, 0)).run(_spec(), known=known)
    assert "https://www.x.ch/de/hund" in {d.url for d in result.documents}


def test_known_page_reached_only_via_revisit_queue_is_sent_conditionally():
    """A page that is known but not reachable from start_urls or any link this run goes through
    the revisit queue and gets conditional headers, so an unmodified page is reported unchanged."""
    known = {"https://www.x.ch/de/hund": KnownState(etag='"e1"', last_modified=None, content_hash="h")}
    spec = SourceSpec(id="x", name="X", publisher="X", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de", "fr"),
                      config={"start_urls": [], "allow_prefixes": ["https://www.x.ch/de/", "https://www.x.ch/fr/"]})
    result = HtmlConnector(_client(conditional_etag='"e1"'), CrawlPolicy(True, 0)).run(spec, known=known)
    assert "https://www.x.ch/de/hund" in result.unchanged_urls
    assert "https://www.x.ch/de/hund" not in {d.url for d in result.documents}


# --- redirects ---------------------------------------------------------------------------------

def test_offsite_redirect_is_not_stored():
    pages = {"https://www.r.ch/de/": """<html lang="de"><body><main><h1>Start</h1>
             <p>Hi.</p><a href="/de/away">Away</a></main></body></html>"""}
    spec = SourceSpec(id="r", name="R", publisher="R", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",),
                      config={"start_urls": ["https://www.r.ch/de/"], "allow_prefixes": ["https://www.r.ch/de/"]})
    client = _client(pages=pages, redirects={"https://www.r.ch/de/away": "https://elsewhere.ch/landing"})
    result = HtmlConnector(client, CrawlPolicy(True, 0)).run(spec, known={})
    assert {d.url for d in result.documents} == {"https://www.r.ch/de/"}
    assert any("redirected outside scope" in reason for _, reason in result.errors)


def test_two_urls_redirecting_to_one_page_yield_one_document():
    pages = {
        "https://www.r.ch/de/": """<html lang="de"><body><main><h1>Start</h1>
          <p>Hi.</p><a href="/de/old-a">A</a><a href="/de/old-b">B</a></main></body></html>""",
        "https://www.r.ch/de/target": """<html lang="de"><body><main><h1>Target</h1>
          <p>Landed here.</p></main></body></html>""",
    }
    spec = SourceSpec(id="r", name="R", publisher="R", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",),
                      config={"start_urls": ["https://www.r.ch/de/"], "allow_prefixes": ["https://www.r.ch/de/"]})
    client = _client(pages=pages, redirects={"https://www.r.ch/de/old-a": "https://www.r.ch/de/target",
                                             "https://www.r.ch/de/old-b": "https://www.r.ch/de/target"})
    result = HtmlConnector(client, CrawlPolicy(True, 0)).run(spec, known={})
    targets = [d for d in result.documents if d.url == "https://www.r.ch/de/target"]
    assert len(targets) == 1


def test_relative_link_resolves_against_final_redirect_url():
    pages = {
        "https://www.r.ch/de/": """<html lang="de"><body><main><h1>Start</h1>
          <p>Hi.</p><a href="/de/old">Old</a></main></body></html>""",
        "https://www.r.ch/de/sub/target": """<html lang="de"><body><main><h1>Target</h1>
          <p>Landed.</p><a href="child">Child</a></main></body></html>""",
        "https://www.r.ch/de/sub/child": """<html lang="de"><body><main><h1>Child</h1>
          <p>Leaf.</p></main></body></html>""",
    }
    spec = SourceSpec(id="r", name="R", publisher="R", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",),
                      config={"start_urls": ["https://www.r.ch/de/"], "allow_prefixes": ["https://www.r.ch/de/"]})
    client = _client(pages=pages, redirects={"https://www.r.ch/de/old": "https://www.r.ch/de/sub/target"})
    result = HtmlConnector(client, CrawlPolicy(True, 0)).run(spec, known={})
    assert "https://www.r.ch/de/sub/child" in {d.url for d in result.documents}


# --- language filtering --------------------------------------------------------------------

def test_page_with_undeclared_language_outside_languages_is_not_emitted():
    pages = {
        "https://www.l.ch/it/": """<html lang="it"><body><main><h1>Ciao</h1>
          <p>Testo italiano qui presente per il test.</p></main></body></html>""",
    }
    spec = SourceSpec(id="l", name="L", publisher="L", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de", "fr"),
                      config={"start_urls": ["https://www.l.ch/it/"], "allow_prefixes": ["https://www.l.ch/"]})
    result = HtmlConnector(_client(pages=pages), CrawlPolicy(True, 0)).run(spec, known={})
    assert result.documents == ()


def test_page_with_no_declared_language_uses_spec_default():
    pages = {"https://www.l.ch/en-fallback/": """<html><body><main><h1>Hi</h1>
             <p>No lang attribute here.</p></main></body></html>"""}
    spec = SourceSpec(id="l", name="L", publisher="L", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("fr", "de"),
                      config={"start_urls": ["https://www.l.ch/en-fallback/"], "allow_prefixes": ["https://www.l.ch/"]})
    result = HtmlConnector(_client(pages=pages), CrawlPolicy(True, 0)).run(spec, known={})
    assert result.documents[0].language == "fr"


def test_hreflang_self_entry_wins_over_html_lang_attribute():
    pages = {
        "https://www.l.ch/de/": """<html lang="de"><head>
          <link rel="alternate" hreflang="fr" href="https://www.l.ch/de/"></head>
          <body><main><h1>Hi</h1><p>Text marked fr by its own hreflang self-entry.</p></main></body></html>""",
    }
    spec = SourceSpec(id="l", name="L", publisher="L", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de", "fr"),
                      config={"start_urls": ["https://www.l.ch/de/"], "allow_prefixes": ["https://www.l.ch/"]})
    result = HtmlConnector(_client(pages=pages), CrawlPolicy(True, 0)).run(spec, known={})
    assert result.documents[0].language == "fr"


def test_alternate_language_outside_spec_languages_is_not_queued():
    pages = {
        "https://www.l.ch/de/": """<html lang="de"><head>
          <link rel="alternate" hreflang="it" href="https://www.l.ch/it/"></head>
          <body><main><h1>Hi</h1><p>German text only, it not in scope.</p></main></body></html>""",
        "https://www.l.ch/it/": """<html lang="it"><body><main><h1>Ciao</h1>
          <p>Should never be fetched.</p></main></body></html>""",
    }
    spec = SourceSpec(id="l", name="L", publisher="L", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",),
                      config={"start_urls": ["https://www.l.ch/de/"], "allow_prefixes": ["https://www.l.ch/"]})
    seen: list[str] = []
    HtmlConnector(_client(pages=pages, seen=seen), CrawlPolicy(True, 0)).run(spec, known={})
    assert "https://www.l.ch/it/" not in seen


# --- robots.txt failure modes ----------------------------------------------------------------

def test_robots_403_disallows_the_whole_host():
    result = HtmlConnector(_client(robots_response=lambda r: httpx.Response(403)),
                           CrawlPolicy(True, 0)).run(_spec(), known={})
    assert result.documents == ()


def test_robots_503_disallows_the_whole_host():
    result = HtmlConnector(_client(robots_response=lambda r: httpx.Response(503)),
                           CrawlPolicy(True, 0)).run(_spec(), known={})
    assert result.documents == ()


def test_robots_redirect_then_200_is_honoured():
    calls = {"n": 0}

    def robots_response(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(301, headers={"location": "/robots-final.txt"})
        return httpx.Response(200, text="User-agent: *\nAllow: /\n")

    result = HtmlConnector(_client(robots_response=robots_response), CrawlPolicy(True, 0)).run(_spec(), known={})
    assert {d.url for d in result.documents} == set(PAGES)


# --- review fixes: discovery through known pages, redirects, per-page failures -----------------

def test_known_page_linked_from_a_fetched_page_is_fetched_in_full():
    """/de/hub is known and would answer 304 to a conditional request; it is linked from the start
    page, so it must be fetched unconditionally and the new page it links to discovered."""
    pages = {
        "https://www.k.ch/de/": """<html lang="de"><body><main><h1>Start</h1><p>Hi.</p>
          <a href="/de/hub">Hub</a></main></body></html>""",
        "https://www.k.ch/de/hub": """<html lang="de"><body><main><h1>Hub</h1><p>Hub.</p>
          <a href="/de/new">New</a></main></body></html>""",
        "https://www.k.ch/de/new": """<html lang="de"><body><main><h1>New</h1><p>New page.</p></main></body></html>""",
    }
    seen: list[str] = []
    known = {"https://www.k.ch/de/hub": KnownState(etag='"e1"', last_modified=None, content_hash="h")}
    spec = SourceSpec(id="k", name="K", publisher="K", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",),
                      config={"start_urls": ["https://www.k.ch/de/"], "allow_prefixes": ["https://www.k.ch/de/"]})
    result = HtmlConnector(_client(pages=pages, conditional_etag='"e1"', seen=seen),
                           CrawlPolicy(True, 0)).run(spec, known=known)
    urls = {d.url for d in result.documents}
    assert "https://www.k.ch/de/new" in urls
    assert "https://www.k.ch/de/hub" in urls
    assert seen.count("https://www.k.ch/de/hub") == 1


def test_known_url_that_now_redirects_is_reported_gone():
    pages = {
        "https://www.r.ch/de/": """<html lang="de"><body><main><h1>Start</h1><p>Hi.</p>
          <a href="/de/new-home">N</a></main></body></html>""",
        "https://www.r.ch/de/new-home": """<html lang="de"><body><main><h1>New</h1><p>Moved.</p></main></body></html>""",
    }
    known = {"https://www.r.ch/de/old": KnownState(None, None, "h"),
             "https://www.r.ch/de/older": KnownState(None, None, "h")}
    spec = SourceSpec(id="r", name="R", publisher="R", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",),
                      config={"start_urls": ["https://www.r.ch/de/"], "allow_prefixes": ["https://www.r.ch/de/"]})
    client = _client(pages=pages, redirects={"https://www.r.ch/de/old": "https://www.r.ch/de/new-home",
                                             "https://www.r.ch/de/older": "https://www.r.ch/de/moved"})
    result = HtmlConnector(client, CrawlPolicy(True, 0)).run(spec, known=known)
    # /de/old lands on a page already fetched this run; /de/older lands on a 404 -- both are gone.
    assert set(result.gone_urls) == {"https://www.r.ch/de/old", "https://www.r.ch/de/older"}
    assert [d.url for d in result.documents].count("https://www.r.ch/de/new-home") == 1


def test_page_that_fails_to_parse_is_an_error_not_a_failed_source(monkeypatch):
    from swiss_grounding.corpus.connectors import html_page as html_module

    real = html_module.page_meta

    def flaky(html, url, **kwargs):
        if url.endswith("/de/hund"):
            raise RecursionError("maximum recursion depth exceeded")
        return real(html, url, **kwargs)

    monkeypatch.setattr(html_module, "page_meta", flaky)
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(), known={})
    assert {d.url for d in result.documents} == {"https://www.x.ch/de/", "https://www.x.ch/fr/"}
    assert any(u == "https://www.x.ch/de/hund" and "parse failed" in reason for u, reason in result.errors)
