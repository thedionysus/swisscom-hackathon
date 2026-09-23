"""A11 site adaptations: language switchers, the federal Nuxt payload, extensionless PDF links,
a content selector, and sitemap seeding -- driven by trimmed copies of the live pages."""
import gzip
from pathlib import Path

import httpx

from swiss_grounding.corpus.connectors.html import CrawlPolicy, HtmlConnector
from swiss_grounding.corpus.models import KnownState, SourceSpec

FIXTURES = Path(__file__).parents[2] / "fixtures" / "corpus"
CHCH_DE = "https://www.ch.ch/de/gesundheit/krankenkasse/kosten-fur-krankenkasse/"
CHCH_FR = "https://www.ch.ch/fr/assurances/assurance-maladie/couts-de-l-assurance-maladie/"
BAG_DE = "https://www.bag.admin.ch/de/krankenversicherung"
BAG_FR = "https://www.bag.admin.ch/fr/assurance-maladie"
AHV_PAGE = "https://www.ahv-iv.ch/de/merkblaetter/beitraege"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _spec(languages=("de", "fr"), **config) -> SourceSpec:
    return SourceSpec(id="s", name="S", publisher="S", authority="official_info", level="federal",
                      extent_id="CH", connector="html", tier=1, languages=languages, config=config)


def _client(pages: dict[str, str], raw: dict[str, tuple[bytes, str]] | None = None,
            seen: list[str] | None = None) -> httpx.Client:
    """`pages` answer as text/html; `raw` answers with (body, content-type); anything else is 404."""
    raw = raw or {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if url in raw:
            body, content_type = raw[url]
            return httpx.Response(200, content=body, headers={"content-type": content_type})
        if url in pages:
            return httpx.Response(200, text=pages[url], headers={"content-type": "text/html; charset=utf-8"})
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


def _run(client: httpx.Client, spec: SourceSpec):
    return HtmlConnector(client, CrawlPolicy(True, 0)).run(spec, known={})


# --- A1 grouping with the new alternate sources ----------------------------------------------

def test_chch_language_switcher_groups_de_and_fr():
    pages = {CHCH_DE: _fixture("chch_kk_de.html"), CHCH_FR: _fixture("chch_kk_fr.html")}
    spec = _spec(start_urls=[CHCH_DE], allow_prefixes=[CHCH_DE, CHCH_FR],
                 language_links_selector="nav#language a[href]")
    by_url = {d.url: d for d in _run(_client(pages), spec).documents}
    assert set(by_url) == {CHCH_DE, CHCH_FR}  # fr was reached through the switcher, not hreflang
    assert by_url[CHCH_DE].work_key == by_url[CHCH_FR].work_key == "html:" + CHCH_DE
    assert by_url[CHCH_FR].language == "fr"


def test_switcher_alternate_is_fetched_next_even_though_it_is_also_a_page_link():
    """The switcher's links are ordinary <a href>s too; the fr version must not wait behind the
    dozens of other in-scope links the page carries."""
    pages = {CHCH_DE: _fixture("chch_kk_de.html"), CHCH_FR: _fixture("chch_kk_fr.html")}
    spec = _spec(start_urls=[CHCH_DE], allow_prefixes=["https://www.ch.ch/de/", "https://www.ch.ch/fr/"],
                 language_links_selector="nav#language a[href]", max_pages=2)
    assert {d.url for d in _run(_client(pages), spec).documents} == {CHCH_DE, CHCH_FR}


def test_chch_without_selector_keeps_pages_apart():
    pages = {CHCH_DE: _fixture("chch_kk_de.html"), CHCH_FR: _fixture("chch_kk_fr.html")}
    spec = _spec(start_urls=[CHCH_DE, CHCH_FR], allow_prefixes=[CHCH_DE, CHCH_FR])
    by_url = {d.url: d for d in _run(_client(pages), spec).documents}
    assert by_url[CHCH_DE].work_key != by_url[CHCH_FR].work_key


def test_bag_nuxt_translation_pages_group_de_and_fr():
    pages = {BAG_DE: _fixture("bag_kv_de.html"), BAG_FR: _fixture("bag_kv_fr.html")}
    spec = _spec(start_urls=[BAG_DE], allow_prefixes=["https://www.bag.admin.ch/de/", "https://www.bag.admin.ch/fr/"])
    by_url = {d.url: d for d in _run(_client(pages), spec).documents}
    assert BAG_FR in by_url
    assert by_url[BAG_DE].work_key == by_url[BAG_FR].work_key
    assert by_url[BAG_DE].title == "Krankenversicherung"


# --- extensionless PDF links and the content selector ----------------------------------------

def test_pdf_link_patterns_discover_pdfs_and_never_crawl_them_as_pages():
    seen: list[str] = []
    spec = _spec(languages=("de",), start_urls=[AHV_PAGE], allow_prefixes=["https://www.ahv-iv.ch/"],
                 pdf_link_patterns=[r"^https://www\.ahv-iv\.ch/p/"], max_pdfs=3)
    result = _run(_client({AHV_PAGE: _fixture("ahv_merkblaetter_de.html")}, seen=seen), spec)
    assert [p.url for p in result.pdfs] == ["https://www.ahv-iv.ch/p/2.01.d", "https://www.ahv-iv.ch/p/2.02.d",
                                            "https://www.ahv-iv.ch/p/2.03.d"]
    assert result.pdfs[0].title_hint.startswith("2.01 - Lohnbeiträge")
    assert not any("/p/" in u for u in seen)


def test_content_selector_drops_navigation_outside_the_content_root():
    pages = {AHV_PAGE: _fixture("ahv_merkblaetter_de.html")}
    plain = _spec(languages=("de",), start_urls=[AHV_PAGE], allow_prefixes=[AHV_PAGE])
    narrowed = _spec(languages=("de",), start_urls=[AHV_PAGE], allow_prefixes=[AHV_PAGE],
                     content_selector="#dnn_ContentPane")
    [before] = _run(_client(pages), plain).documents
    [after] = _run(_client(pages), narrowed).documents
    # The breadcrumb's own heading ("Brotkrumennavigation") is a visually-hidden <h2
    # class="sr-only">, so it is dropped everywhere now, with or without a content selector; the
    # breadcrumb LINK TEXT (not a heading) is still page noise without the narrower selector.
    assert not any("Brotkrumennavigation" in s.breadcrumb for s in before.sections)
    assert any("Startseite" in s.text for s in before.sections)
    assert not any("Startseite" in s.text for s in after.sections)
    assert after.title == "Beiträge AHV/IV/EO/ALV"
    assert "Lohnbeiträge" in after.sections[0].text


# --- sitemap seeding ---------------------------------------------------------------------------

def _page(title: str, lang: str = "de") -> str:
    return f'<html lang="{lang}"><body><main><h1>{title}</h1><p>Text zu {title}.</p></main></body></html>'


def _urlset(*urls: str) -> bytes:
    # ch.ch style: image:loc entries inside each url must not be taken for pages.
    body = "".join(f"<url><loc>{u}</loc><image:image><image:loc>https://img.x.ch/{i}.png</image:loc>"
                   f"</image:image></url>" for i, u in enumerate(urls))
    return (f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            f'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">{body}</urlset>').encode()


def _index(*urls: str) -> bytes:
    body = "".join(f"<sitemap><loc>{u}</loc></sitemap>" for u in urls)
    return (f'<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{body}</sitemapindex>").encode()


def test_sitemap_urls_matching_include_are_queued_after_start_urls():
    seen: list[str] = []
    pages = {f"https://www.s.ch/de/{slug}": _page(slug)
             for slug in ("start", "krankenversicherung", "krankenversicherung-praemien", "tabak")}
    # Served as text/html, like ch.ch's /sitemap.xml.
    raw = {"https://www.s.ch/sitemap.xml": (_urlset(*pages, "https://other.ch/de/krankenversicherung"),
                                            "text/html")}
    spec = _spec(languages=("de",), start_urls=["https://www.s.ch/de/start"], allow_prefixes=["https://www.s.ch/de/"],
                 sitemap_urls=["https://www.s.ch/sitemap.xml"], sitemap_include=["krankenversicherung"])
    result = _run(_client(pages, raw, seen), spec)
    assert [d.url for d in result.documents] == ["https://www.s.ch/de/start", "https://www.s.ch/de/krankenversicherung",
                                                 "https://www.s.ch/de/krankenversicherung-praemien"]
    assert not any("img.x.ch" in u or "other.ch" in u for u in seen)


def test_sitemap_index_with_gzip_children_is_followed():
    pages = {"https://www.s.ch/de/a": _page("A"), "https://www.s.ch/de/b": _page("B")}
    raw = {
        "https://www.s.ch/sitemap.xml": (_index("https://www.s.ch/sitemap-1.xml.gz"), "application/xml"),
        "https://www.s.ch/sitemap-1.xml.gz": (gzip.compress(_urlset(*pages)), "application/x-gzip"),
    }
    spec = _spec(languages=("de",), start_urls=[], allow_prefixes=["https://www.s.ch/de/"],
                 sitemap_urls=["https://www.s.ch/sitemap.xml"])
    assert {d.url for d in _run(_client(pages, raw), spec).documents} == set(pages)


def test_sitemap_seeding_stops_at_max_pages():
    seen: list[str] = []
    first = [f"https://www.s.ch/de/p{i}" for i in range(3)]
    pages = {u: _page(u[-2:]) for u in first}
    raw = {
        "https://www.s.ch/sitemap.xml": (_index("https://www.s.ch/sm1.xml", "https://www.s.ch/sm2.xml"),
                                         "application/xml"),
        "https://www.s.ch/sm1.xml": (_urlset(*first), "application/xml"),
        "https://www.s.ch/sm2.xml": (_urlset("https://www.s.ch/de/q"), "application/xml"),
    }
    spec = _spec(languages=("de",), start_urls=[], allow_prefixes=["https://www.s.ch/de/"],
                 sitemap_urls=["https://www.s.ch/sitemap.xml"], max_pages=2)
    result = _run(_client(pages, raw, seen), spec)
    assert len(result.documents) == 2
    assert "https://www.s.ch/sm2.xml" not in seen


def test_unreadable_sitemap_is_an_error_not_a_failed_run():
    pages = {"https://www.s.ch/de/start": _page("Start")}
    raw = {"https://www.s.ch/broken.xml": (b"\x1f\x8bnot really gzip", "application/x-gzip")}
    spec = _spec(languages=("de",), start_urls=["https://www.s.ch/de/start"], allow_prefixes=["https://www.s.ch/de/"],
                 sitemap_urls=["https://www.s.ch/missing.xml", "https://www.s.ch/broken.xml"])
    result = _run(_client(pages, raw), spec)
    assert [d.url for d in result.documents] == ["https://www.s.ch/de/start"]
    failed = {url for url, reason in result.errors if "sitemap" in reason}
    assert failed == {"https://www.s.ch/missing.xml", "https://www.s.ch/broken.xml"}


def test_language_alternates_jump_the_queue_so_pairs_complete_within_max_pages():
    """The BAG page links dozens of in-scope pages; its fr version must still be fetched second."""
    pages = {BAG_DE: _fixture("bag_kv_de.html"), BAG_FR: _fixture("bag_kv_fr.html")}
    spec = _spec(start_urls=[BAG_DE], allow_prefixes=["https://www.bag.admin.ch/de/", "https://www.bag.admin.ch/fr/"],
                 max_pages=2)
    by_url = {d.url: d for d in _run(_client(pages), spec).documents}
    assert set(by_url) == {BAG_DE, BAG_FR}
    assert by_url[BAG_DE].work_key == by_url[BAG_FR].work_key


def test_alternate_already_queued_behind_other_links_is_pulled_forward():
    """de/a links fr/b (queued at the back behind de/x); when de/b is fetched and lists fr/b as its
    alternate, fr/b must come next rather than wait behind de/x."""
    def page(lang, title, links, alt):
        anchors = "".join(f'<a href="{u}">{u}</a>' for u in links)
        return (f'<html lang="{lang}"><head><link rel="alternate" hreflang="{alt[0]}" href="{alt[1]}"></head>'
                f"<body><main><h1>{title}</h1><p>{title} text.</p>{anchors}</main></body></html>")
    pages = {
        "https://www.s.ch/de/a": page("de", "A", ["https://www.s.ch/de/x", "https://www.s.ch/fr/b"],
                                      ("de", "https://www.s.ch/de/a")),
        "https://www.s.ch/de/b": page("de", "B", [], ("fr", "https://www.s.ch/fr/b")),
        "https://www.s.ch/fr/b": page("fr", "Bf", [], ("de", "https://www.s.ch/de/b")),
    }
    spec = _spec(start_urls=["https://www.s.ch/de/a", "https://www.s.ch/de/b"],
                 allow_prefixes=["https://www.s.ch/"], max_pages=3)
    by_url = {d.url: d for d in _run(_client(pages), spec).documents}
    assert set(by_url) == set(pages)
    assert by_url["https://www.s.ch/de/b"].work_key == by_url["https://www.s.ch/fr/b"].work_key


def test_sitemap_seed_budget_goes_to_urls_not_already_known_or_queued():
    known_urls = [f"https://www.s.ch/de/old{i}" for i in range(3)]
    new = "https://www.s.ch/de/fresh"
    pages = {u: _page(u[-4:]) for u in [*known_urls, new, "https://www.s.ch/de/start"]}
    raw = {"https://www.s.ch/sitemap.xml": (_urlset("https://www.s.ch/de/start", *known_urls, new), "application/xml")}
    spec = _spec(languages=("de",), start_urls=["https://www.s.ch/de/start"], allow_prefixes=["https://www.s.ch/de/"],
                 sitemap_urls=["https://www.s.ch/sitemap.xml"], max_pages=2)
    known = {u: KnownState(None, None, "h") for u in known_urls}
    result = HtmlConnector(_client(pages, raw), CrawlPolicy(True, 0)).run(spec, known=known)
    assert [d.url for d in result.documents] == ["https://www.s.ch/de/start", new]


def test_alternate_matching_pdf_patterns_is_not_crawled_as_a_page():
    seen: list[str] = []
    html = """<html lang="de"><head><link rel="alternate" hreflang="fr" href="https://www.s.ch/p/doc.f"></head>
      <body><main><h1>A</h1><p>Text.</p></main></body></html>"""
    spec = _spec(start_urls=["https://www.s.ch/de/a"], allow_prefixes=["https://www.s.ch/"],
                 pdf_link_patterns=[r"^https://www\.s\.ch/p/"])
    _run(_client({"https://www.s.ch/de/a": html}, seen=seen), spec)
    assert "https://www.s.ch/p/doc.f" not in seen
