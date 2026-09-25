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
    ("<title>Erreur 404 - Page introuvable</title>", ""),
    ("<title>Stadt Bern | 404 Not Found</title>", ""),
    ("<title>Oops! Page not found</title>", ""),
])
def test_error_page_served_with_200_is_recognised_by_its_title_or_h1(head, h1):
    html = f"""<html lang="de"><head>{head}</head><body><main>{f"<h1>{h1}</h1>" if h1 else ""}
      <p>Die gewünschte Seite existiert nicht.</p></main></body></html>"""
    assert parse_crawled_page(html, "https://www.be.ch/de/x", _spec(), pdf_patterns=()).soft_404


@pytest.mark.parametrize(("head", "h1", "body"), [
    ("<title>Art. 404 OR</title>", "Art. 404 OR – Widerruf und Kündigung", "<p>Der Auftrag kann jederzeit ...</p>"),
    ("<title>Buslinie 404</title>", "Buslinie 404", "<p>Fahrplan.</p>"),
    ("<title>Hilfe</title>", "Hilfe", "<p>Was tun, wenn eine Seite nicht gefunden wird? Page not found?</p>"),
    # Flagged by the first pattern (audit of PR #77): the words appear, but the page is not an error page.
    ("<title>Help</title>", "Help: Why is my address not found?", "<p>Check the spelling.</p>"),
    ("<title>Fundbüro</title>", "Not found? Contact the lost property office", "<p>Opening hours.</p>"),
    ("<title>Linie 404 – Fehler im Fahrplan</title>", "Linie 404", "<p>Korrigierter Fahrplan.</p>"),
    ("<title>Richtlinie 2018/404 Fehler</title>", "Richtlinie", "<p>Text der Richtlinie.</p>"),
])
def test_ordinary_page_mentioning_404_or_not_found_is_not_an_error_page(head, h1, body):
    html = f'<html lang="de"><head>{head}</head><body><main><h1>{h1}</h1>{body}</main></body></html>'
    assert parse_crawled_page(html, "https://www.be.ch/de/x", _spec(), pdf_patterns=()).soft_404 is None


def test_a_long_title_of_repeated_error_words_is_checked_without_backtracking():
    """A pattern that could read "page not found" two ways took exponential time on this title."""
    from swiss_grounding.corpus.connectors.html_page import _SOFT_404
    assert _SOFT_404.match("page not found " * 100 + "x") is None


_NEUCHATEL = """<html lang="fr"><head>
  <link rel="alternate" hreflang="fr" href="https://www.neuchatelville.ch/fr/votre-commune/reglementation">
  <link rel="alternate" hreflang="de" href="https://www.neuchatelville.ch/votre-commune/reglementation">
  </head><body><main><h1>Réglementation</h1><p>Règlements communaux.</p>
  <a href="/fileadmin/sites/ne_ville/fichiers/votre_commune/reglementation/12_21_A_interChiens.pdf">Chiens</a>
  </main></body></html>"""


def _neuchatel_spec(languages):
    return SourceSpec(id="ne", name="NE", publisher="NE", authority="municipal_law", level="municipal",
                      extent_id="CH-NE-6458", connector="html", tier=2, languages=languages,
                      config={"start_urls": ["https://www.neuchatelville.ch/votre-commune/reglementation"],
                              "allow_prefixes": ["https://www.neuchatelville.ch/votre-commune/reglementation"]})


def test_html_lang_wins_when_a_language_link_names_the_page_in_an_undeclared_language():
    """www.neuchatelville.ch (#56): <html lang="fr">, but its hreflang links call it the German
    version. The source declares only French, so the page and its 79 PDFs were dropped."""
    page = parse_crawled_page(_NEUCHATEL, "https://www.neuchatelville.ch/votre-commune/reglementation",
                              _neuchatel_spec(("fr",)), pdf_patterns=())
    assert (page.language, page.emit) == ("fr", True)
    assert len(page.pdf_links) == 1


def test_language_link_still_wins_when_the_source_declares_both_languages():
    page = parse_crawled_page(_NEUCHATEL, "https://www.neuchatelville.ch/votre-commune/reglementation",
                              _neuchatel_spec(("fr", "de")), pdf_patterns=())
    assert (page.language, page.emit) == ("de", True)


def test_marker_stripping_does_not_touch_ordinary_bracketed_text():
    html = """<html lang="de"><body><main><h1>T</h1>
    <p>Siehe Anhang [1] für Details. Das ist [wichtig].</p>
    </main></body></html>"""
    page = parse_crawled_page(html, "https://www.be.ch/de/", _spec(), pdf_patterns=())
    text = " ".join(s.text for s in page.sections)
    assert "[1]" in text and "[wichtig]" in text
