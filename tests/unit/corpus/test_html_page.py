"""CMS marker noise seen on live pages: TYPO3SEARCH_begin/end comments, bracket runs left over
from Start_Module/End_Module includes -- must never end up in a chunk's text."""
import pytest

from swiss_grounding.corpus.connectors.html_page import parse_crawled_page
from swiss_grounding.corpus.models import SourceSpec


def _spec(**config) -> SourceSpec:
    base = {"start_urls": ["https://www.be.ch/de/"], "allow_prefixes": ["https://www.be.ch/de/"]}
    base.update(config)
    return SourceSpec(id="be", name="BE", publisher="BE", authority="official_info", level="cantonal",
                      extent_id="CH-BE", connector="html", tier=1, languages=("de",), config=base)


def test_typo3search_comments_and_bracket_runs_are_stripped_from_section_text():
    html = """<html lang="de"><body><main><h1>Steuern</h1>
    <!-- TYPO3SEARCH_begin -->
    <p>Wichtige Information zu den Steuern.</p>
    <!-- TYPO3SEARCH_end -->
    <p>[[[</p>
    <p>Start_Module</p>
    <p>Weitere Informationen folgen hier.</p>
    <p>End_Module</p>
    <p>]]]</p>
    </main></body></html>"""
    page = parse_crawled_page(html, "https://www.be.ch/de/", _spec(), pdf_patterns=())
    text = " ".join(s.text for s in page.sections)
    assert "TYPO3SEARCH" not in text
    assert "[[[" not in text and "]]]" not in text
    assert "Start_Module" not in text and "End_Module" not in text
    assert "Wichtige Information zu den Steuern." in text
    assert "Weitere Informationen folgen hier." in text


@pytest.mark.parametrize(("head", "h1"), [
    ("<title>Error Page (404)</title>", "Error Page (404)"),       # www.ch.ch/en/ in #20
    ("<title>Seite nicht gefunden | Stadt Bern</title>", ""),
    ("<title>Kanton Waadt</title>", "Page introuvable"),
    ("<title>Pagina non trovata</title>", ""),
    ("<title>404 - Page not found</title>", ""),
    ("<title>Fehler 404</title>", ""),
    ("", "404"),
])
def test_error_page_served_with_200_is_recognised_by_its_title_or_h1(head, h1):
    html = f"""<html lang="de"><head>{head}</head><body><main>{f"<h1>{h1}</h1>" if h1 else ""}
      <p>Die gewünschte Seite existiert nicht.</p></main></body></html>"""
    assert parse_crawled_page(html, "https://www.be.ch/de/x", _spec(), pdf_patterns=()).soft_404


@pytest.mark.parametrize(("head", "h1", "body"), [
    ("<title>Art. 404 OR</title>", "Art. 404 OR – Widerruf und Kündigung", "<p>Der Auftrag kann jederzeit ...</p>"),
    ("<title>Buslinie 404</title>", "Buslinie 404", "<p>Fahrplan.</p>"),
    ("<title>Hilfe</title>", "Hilfe", "<p>Was tun, wenn eine Seite nicht gefunden wird? Page not found?</p>"),
])
def test_ordinary_page_mentioning_404_or_not_found_is_not_an_error_page(head, h1, body):
    html = f'<html lang="de"><head>{head}</head><body><main><h1>{h1}</h1>{body}</main></body></html>'
    assert parse_crawled_page(html, "https://www.be.ch/de/x", _spec(), pdf_patterns=()).soft_404 is None


def test_marker_stripping_does_not_touch_ordinary_bracketed_text():
    html = """<html lang="de"><body><main><h1>T</h1>
    <p>Siehe Anhang [1] für Details. Das ist [wichtig].</p>
    </main></body></html>"""
    page = parse_crawled_page(html, "https://www.be.ch/de/", _spec(), pdf_patterns=())
    text = " ".join(s.text for s in page.sections)
    assert "[1]" in text and "[wichtig]" in text
