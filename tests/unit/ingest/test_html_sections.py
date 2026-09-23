from pathlib import Path

from bs4 import BeautifulSoup

from swiss_grounding.ingest.html_sections import extract_links, html_to_page

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "html"
HTML = (FIXTURES / "zh_hunde.html").read_text()
HTML_TIERE = (FIXTURES / "zh_tiere.html").read_text()
HTML_UMWELT = (FIXTURES / "zh_umwelt.html").read_text()


def test_title_and_language():
    page = html_to_page(HTML, url="https://www.zh.ch/de/umwelt-tiere/tiere/hunde.html", default_language="fr")
    assert page.title == "Hunde im Kanton Zürich"
    assert page.language == "de"


def test_sections_follow_headings_with_paths_and_anchors():
    page = html_to_page(HTML, url="https://www.zh.ch/x", default_language="de")
    paths = [s.heading_path for s in page.sections]
    assert paths == [
        "Hunde im Kanton Zürich",
        "Hunde im Kanton Zürich > Leinenpflicht",
        "Hunde im Kanton Zürich > Leinenpflicht > Bussen",
        "Hunde im Kanton Zürich > Hundesteuer",
    ]
    assert page.sections[1].anchor == "leinenpflicht"
    assert "Leinenpflicht für Hunde" in page.sections[1].text
    assert "Wanderwegen" in page.sections[1].text            # list items kept


def test_nav_footer_script_are_dropped():
    page = html_to_page(HTML, url="https://www.zh.ch/x", default_language="de")
    joined = " ".join(s.text for s in page.sections)
    assert "Impressum" not in joined and "console.log" not in joined and "Home" not in joined


def test_extract_links_resolves_relative_and_keeps_all():
    links = extract_links(HTML, base_url="https://www.zh.ch/de/umwelt-tiere/tiere/hunde.html")
    assert "https://www.zh.ch/de/umwelt-tiere/tiere/katzen.html" in links
    assert "https://www.stadt-zuerich.ch/hunde" in links
    assert "https://www.zh.ch/en/other.html" in links


def test_page_without_headings_is_one_section_titled_by_title():
    page = html_to_page("<html><head><title>T</title></head><body><p>Hello</p></body></html>",
                        url="https://x/", default_language="en")
    assert len(page.sections) == 1
    assert page.sections[0].heading_path == "T"
    assert page.sections[0].text == "Hello"


def test_empty_body_yields_no_sections():
    page = html_to_page("<html><body></body></html>", url="https://x/", default_language="en")
    assert page.sections == ()


def test_title_ignores_hidden_nav_and_footer_h1():
    # Real zh.ch pages carry a visually-hidden <h1>Navigation</h1> in the nav and a
    # <h1>Fussbereich</h1> in the footer, ahead of / behind the real content h1 in <main>.
    tiere = html_to_page(HTML_TIERE, url="https://www.zh.ch/de/umwelt-tiere/tiere.html", default_language="fr")
    assert tiere.title == "Tiere"
    assert tiere.title not in ("Navigation", "Fussbereich")

    umwelt = html_to_page(HTML_UMWELT, url="https://www.zh.ch/de/umwelt-tiere.html", default_language="fr")
    assert umwelt.title == "Umwelt & Tiere"
    assert umwelt.title not in ("Navigation", "Fussbereich")


def test_title_falls_back_to_title_tag_stripped_of_site_suffix_when_root_has_no_h1():
    html = """<html><head><title>Katzen | Kanton Zürich</title></head><body>
    <nav><h1 class="visuallyhidden">Navigation</h1></nav>
    <main><p>Katzen brauchen Auslauf.</p></main>
    </body></html>"""
    page = html_to_page(html, url="https://x/", default_language="de")
    assert page.title == "Katzen"


def test_more_than_one_section_with_real_nested_heading_paths():
    # The real content h1 ("Umwelt & Tiere") lives inside a <header> nested in <main>, used
    # only for the page title (see test_title_ignores_hidden_nav_and_footer_h1); <header> is
    # dropped before the section split, so the shallowest heading path here starts at h2.
    page = html_to_page(HTML_UMWELT, url="https://www.zh.ch/x", default_language="de")
    paths = [s.heading_path for s in page.sections]
    assert len(paths) > 1
    assert any(" > " in p for p in paths)
    assert "Umweltschutz > Wir sind für nachfolgende Generationen verantwortlich" in paths
    assert "Umweltschutz > Umweltschutz funktioniert nur ganzheitlich" in paths


def test_heading_with_id_produces_matching_anchor():
    page = html_to_page(HTML_UMWELT, url="https://www.zh.ch/x", default_language="de")
    section = next(s for s in page.sections if s.anchor == "-845041718")
    assert section.heading_path.endswith("Wir sind für nachfolgende Generationen verantwortlich")


def test_text_under_nested_heading_is_not_attributed_to_an_earlier_heading():
    page = html_to_page(HTML_UMWELT, url="https://www.zh.ch/x", default_language="de")
    first = next(s for s in page.sections if s.anchor == "-845041718")
    second = next(s for s in page.sections if s.anchor == "-766584373")
    assert "künftige Generationen" in first.text
    assert "künftige Generationen" not in second.text
    assert "Wechselspiel" in second.text
    assert "Wechselspiel" not in first.text


def test_page_without_main_article_or_role_main_falls_back_to_body():
    # When there's no main/article/[role=main], the content root falls back to <body>, which
    # (unlike <main> on the real pages) directly contains the site <nav> with its own hidden
    # h1. That nav h1 comes first in document order, so it must still lose to the real one.
    html = """<html><head><title>Fallback</title></head><body>
    <nav><h1 class="visuallyhidden">Navigation</h1></nav>
    <h1>Body Heading</h1><p>Body text.</p>
    <footer><h1 class="visuallyhidden">Fussbereich</h1></footer>
    </body></html>"""
    page = html_to_page(html, url="https://x/", default_language="de")
    assert page.title == "Body Heading"
    assert page.title not in ("Navigation", "Fussbereich")
    assert len(page.sections) == 1
    assert page.sections[0].heading_path == "Body Heading"
    assert page.sections[0].text == "Body text."


def test_bare_text_directly_under_a_descended_wrapper_is_kept():
    # A container that itself holds no heading is buffered whole (a Tag, via _to_text). A
    # container that does hold one is descended into instead -- and NavigableStrings sitting
    # directly under it, as opposed to wrapped in a Tag, must survive that descent too.
    html = "<main><div>Intro sentence that belongs to the page.<h2>H</h2><p>Body</p></div></main>"
    page = html_to_page(html, url="https://x/", default_language="de")
    texts = [s.text for s in page.sections]
    assert any("Intro sentence that belongs to the page." in t for t in texts)
    assert any(t == "Body" for t in texts)


def test_descent_into_nested_headings_is_not_depth_bounded():
    # On the real zh.ch pages, content headings sit many wrapper-divs below <main> (a
    # page-header block, grid/cell layout divs, an AEM grid column, a richtext block, ...).
    # Confirm the fixture actually reproduces that depth, then confirm the extractor still
    # finds the heading there -- guards against ever capping the recursive descent.
    soup = BeautifulSoup(HTML_UMWELT, "lxml")
    main = soup.select_one("main")
    heading = soup.find(id="-845041718")
    depth = 0
    node = heading
    while node is not main and node is not None:
        node = node.parent
        depth += 1
    assert depth >= 6, "fixture no longer reproduces the real page's nesting depth"

    page = html_to_page(HTML_UMWELT, url="https://www.zh.ch/x", default_language="de")
    section = next(s for s in page.sections if s.anchor == "-845041718")
    assert "künftige Generationen" in section.text


def test_extract_links_reads_href_from_custom_elements_but_not_head_resources():
    html = """<html><head><link rel="stylesheet" href="/static/site.css"><base href="/"></head><body>
    <stzh-card-navigation href="/de/stadtleben/kultur.html">Kultur</stzh-card-navigation>
    <stzh-link href="/de/service/impressum.html" label="Impressum"></stzh-link>
    </body></html>"""
    links = extract_links(html, base_url="https://www.stadt-zuerich.ch/de/stadtleben.html")
    assert links == ("https://www.stadt-zuerich.ch/de/stadtleben/kultur.html",
                     "https://www.stadt-zuerich.ch/de/service/impressum.html")


def test_content_selector_overrides_the_default_content_root():
    html = """<html lang="de"><body><div id="skip"><h1>Kopfzeile</h1><p>Menü Startseite Kontakt</p></div>
      <div id="content"><h1>Merkblätter</h1><p>Die Merkblätter der AHV.</p></div></body></html>"""
    default = html_to_page(html, url="https://x/", default_language="de")
    chosen = html_to_page(html, url="https://x/", default_language="de", content_selector="#content")
    assert default.title == "Kopfzeile"
    assert chosen.title == "Merkblätter"
    assert "Menü" not in " ".join(s.text for s in chosen.sections)
    assert "Die Merkblätter der AHV." in chosen.sections[0].text


def test_content_selector_that_matches_nothing_falls_back_to_the_default_root():
    html = "<html><body><main><h1>Hi</h1><p>Text.</p></main></body></html>"
    page = html_to_page(html, url="https://x/", default_language="de", content_selector="#missing")
    assert page.title == "Hi" and page.sections


# --- visually-hidden headings inside the content root itself -----------------------------------
# chur.ch's #maincontent opens with a visually-hidden <h1>Inhalt</h1> before the real title; other
# sites use "Navigation" or "Kopfzeire" the same way. Unlike the nav/footer h1s (already dropped
# because their whole tag is removed), this hidden h1 lives INSIDE the content root, so it must be
# recognised and skipped by class, not by ancestry.

def test_hidden_h1_inside_content_root_does_not_win_the_title():
    html = """<html><body><div id="maincontent">
    <h1 class="sr-only">Inhalt</h1>
    <h1>Steuererklärung</h1>
    <p>Informationen zur Steuererklärung.</p>
    </div></body></html>"""
    page = html_to_page(html, url="https://x/", default_language="de", content_selector="#maincontent")
    assert page.title == "Steuererklärung"


def test_hidden_h1_with_no_visible_h1_falls_back_to_title_tag():
    html = """<html><head><title>Neu in Chur | Stadt Chur</title></head><body>
    <div id="maincontent">
    <h1 class="sr-only">Inhalt</h1>
    <p>Willkommen in Chur.</p>
    </div></body></html>"""
    page = html_to_page(html, url="https://x/", default_language="de", content_selector="#maincontent")
    assert page.title == "Neu in Chur"


def test_hidden_heading_is_not_a_section_break_and_its_text_is_dropped():
    html = """<main>
    <h1 class="visually-hidden">Navigation</h1>
    <h2>Kopfzeile</h2>
    <p>Real content here.</p>
    </main>"""
    page = html_to_page(html, url="https://x/", default_language="de")
    joined = " ".join(s.heading_path for s in page.sections)
    assert "Navigation" not in joined
    texts = " ".join(s.text for s in page.sections)
    assert "Navigation" not in texts


def test_various_hidden_markers_are_all_recognised():
    variants = [
        '<h1 hidden>Hidden Attr</h1>',
        '<h1 aria-hidden="true">Aria Hidden</h1>',
        '<h1 style="display:none">Style Display None</h1>',
        '<h1 style="visibility: hidden;">Style Visibility Hidden</h1>',
        '<h1 class="visuallyhidden">Visually Hidden</h1>',
        '<h1 class="screen-reader-text">Screen Reader Text</h1>',
        '<h1 class="offscreen">Offscreen</h1>',
    ]
    for hidden_h1 in variants:
        html = f"<main>{hidden_h1}<h2>Real</h2><p>Body.</p></main>"
        page = html_to_page(html, url="https://x/", default_language="de")
        for banned in ("Hidden", "Aria", "Style", "Visually", "Screen", "Offscreen"):
            assert banned not in page.title, hidden_h1
