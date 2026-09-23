"""CMS marker noise seen on live pages: TYPO3SEARCH_begin/end comments, bracket runs left over
from Start_Module/End_Module includes -- must never end up in a chunk's text."""
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


def test_marker_stripping_does_not_touch_ordinary_bracketed_text():
    html = """<html lang="de"><body><main><h1>T</h1>
    <p>Siehe Anhang [1] für Details. Das ist [wichtig].</p>
    </main></body></html>"""
    page = parse_crawled_page(html, "https://www.be.ch/de/", _spec(), pdf_patterns=())
    text = " ".join(s.text for s in page.sections)
    assert "[1]" in text and "[wichtig]" in text
