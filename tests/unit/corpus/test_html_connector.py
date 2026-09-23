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


def _client(robots="User-agent: *\nAllow: /\n", seen=None, pages=None):
    pages = pages if pages is not None else PAGES

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=robots)
        if url in pages:
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
