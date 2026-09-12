from pathlib import Path

from swiss_grounding.ingest.html_sections import extract_links, html_to_page

HTML = (Path(__file__).parent.parent.parent / "fixtures" / "html" / "zh_hunde.html").read_text()


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


def test_extract_links_reads_href_from_custom_elements_but_not_head_resources():
    html = """<html><head><link rel="stylesheet" href="/static/site.css"><base href="/"></head><body>
    <stzh-card-navigation href="/de/stadtleben/kultur.html">Kultur</stzh-card-navigation>
    <stzh-link href="/de/service/impressum.html" label="Impressum"></stzh-link>
    </body></html>"""
    links = extract_links(html, base_url="https://www.stadt-zuerich.ch/de/stadtleben.html")
    assert links == ("https://www.stadt-zuerich.ch/de/stadtleben/kultur.html",
                     "https://www.stadt-zuerich.ch/de/service/impressum.html")
