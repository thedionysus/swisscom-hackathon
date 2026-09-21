from pathlib import Path

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
    page = html_to_page(HTML_UMWELT, url="https://www.zh.ch/x", default_language="de")
    paths = [s.heading_path for s in page.sections]
    assert len(paths) > 1
    assert any(" > " in p for p in paths)
    assert "Umwelt & Tiere > Umweltschutz > Wir sind für nachfolgende Generationen verantwortlich" in paths
    assert "Umwelt & Tiere > Umweltschutz > Umweltschutz funktioniert nur ganzheitlich" in paths


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
    html = """<html><head><title>Fallback</title></head><body>
    <nav><h1 class="visuallyhidden">Navigation</h1></nav>
    <h1>Body Heading</h1><p>Body text.</p>
    <footer><h1 class="visuallyhidden">Fussbereich</h1></footer>
    </body></html>"""
    page = html_to_page(html, url="https://x/", default_language="de")
    assert page.title == "Body Heading"
    assert len(page.sections) == 1
    assert page.sections[0].heading_path == "Body Heading"
    assert page.sections[0].text == "Body text."


def test_extract_links_reads_href_from_custom_elements_but_not_head_resources():
    html = """<html><head><link rel="stylesheet" href="/static/site.css"><base href="/"></head><body>
    <stzh-card-navigation href="/de/stadtleben/kultur.html">Kultur</stzh-card-navigation>
    <stzh-link href="/de/service/impressum.html" label="Impressum"></stzh-link>
    </body></html>"""
    links = extract_links(html, base_url="https://www.stadt-zuerich.ch/de/stadtleben.html")
    assert links == ("https://www.stadt-zuerich.ch/de/stadtleben/kultur.html",
                     "https://www.stadt-zuerich.ch/de/service/impressum.html")
