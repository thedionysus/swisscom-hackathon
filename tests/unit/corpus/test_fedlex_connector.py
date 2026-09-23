from datetime import date
from pathlib import Path

import httpx

from swiss_grounding.corpus.connectors.fedlex import FedlexConnector, choose_consolidations
from swiss_grounding.corpus.models import KnownState, SourceSpec

XML = (Path(__file__).parents[2] / "fixtures" / "corpus" / "akn_or.xml").read_text()
ABSTRACT = "https://fedlex.data.admin.ch/eli/cc/27/317_321_377"
SPEC = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                  level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de", "en"),
                  config={"sr_numbers": ["220"]})


def _binding(applicability, file_url, title="Obligationenrecht"):
    return {"abstract": {"value": ABSTRACT}, "dateApplicability": {"value": applicability},
            "title": {"value": title}, "fileUrl": {"value": file_url}}


def _transport(bindings_by_lang):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = request.content.decode()
            lang = "en" if "ENG" in body else "de"
            return httpx.Response(200, json={"results": {"bindings": bindings_by_lang.get(lang, [])}})
        return httpx.Response(200, text=XML)
    return httpx.MockTransport(handler)


def test_choose_current_and_scheduled():
    rows = [
        {"applicability": date(2024, 1, 1)}, {"applicability": date(2025, 7, 1)}, {"applicability": date(2027, 1, 1)},
    ]
    current, scheduled = choose_consolidations(rows, today=date(2026, 9, 24))
    assert current["applicability"] == date(2025, 7, 1)
    assert scheduled["applicability"] == date(2027, 1, 1)


def test_fetches_current_and_scheduled_in_german_and_skips_missing_english(tmp_path):
    bindings = {"de": [_binding("2025-07-01", "https://f/de-2025.xml"), _binding("2027-01-01", "https://f/de-2027.xml")]}
    connector = FedlexConnector(httpx.Client(transport=_transport(bindings)), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(SPEC, known={})
    assert result.errors == ()
    by_status = {d.status: d for d in result.documents}
    assert set(by_status) == {"current", "scheduled"}
    current = by_status["current"]
    assert current.url == "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/20250701/de"
    assert current.work_key == ABSTRACT
    assert current.valid_from == date(2025, 7, 1)
    assert current.identifier == "SR 220"
    assert current.is_authentic is True
    assert any(s.align_key == "art_336_c" for s in current.sections)
    assert Path(current.artifact_path).exists()


def test_english_is_not_authentic(tmp_path):
    bindings = {"de": [_binding("2025-07-01", "https://f/de.xml")],
                "en": [_binding("2025-07-01", "https://f/en.xml", title="Code of Obligations")]}
    connector = FedlexConnector(httpx.Client(transport=_transport(bindings)), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    en = [d for d in connector.run(SPEC, known={}).documents if d.language == "en"]
    assert len(en) == 1 and en[0].is_authentic is False and en[0].title == "Code of Obligations"


def test_known_url_is_unchanged_without_download(tmp_path):
    bindings = {"de": [_binding("2025-07-01", "https://f/de.xml")]}
    connector = FedlexConnector(httpx.Client(transport=_transport(bindings)), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    url = "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/20250701/de"
    result = connector.run(SPEC, known={url: KnownState(None, None, "h")})
    assert result.unchanged_urls == (url,)
    assert result.documents == ()


def test_missing_german_is_an_error(tmp_path):
    connector = FedlexConnector(httpx.Client(transport=_transport({})), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(SPEC, known={})
    assert result.errors and "SR 220" in result.errors[0][1]


def test_split_paragraphs_aligns_across_languages_when_any_version_overflows(tmp_path):
    """An article split into chunks in one language must split the same way in every language,
    so aligned chunks stay aligned; the connector marks split_paragraphs=True on the shared
    align_key in every version once ANY version's article text exceeds chunker.MAX_CHARS."""
    from swiss_grounding.corpus.chunker import MAX_CHARS

    de_xml = _akn_with_article_text("x" * 1700)
    fr_xml = _akn_with_article_text("y" * (MAX_CHARS + 100))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = request.content.decode()
            lang = "fr" if "FRA" in body else "de"
            file_url = f"https://f/{lang}.xml"
            return httpx.Response(200, json={"results": {"bindings": [_binding("2025-07-01", file_url)]}})
        if "fr" in str(request.url):
            return httpx.Response(200, text=fr_xml)
        return httpx.Response(200, text=de_xml)

    spec = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                      level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de", "fr"),
                      config={"sr_numbers": ["220"]})
    connector = FedlexConnector(httpx.Client(transport=httpx.MockTransport(handler)),
                                today=lambda: date(2026, 9, 24), data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(spec, known={})
    assert result.errors == ()
    by_lang = {d.language: d for d in result.documents}
    de_section = by_lang["de"].sections[0]
    fr_section = by_lang["fr"].sections[0]
    assert de_section.align_key == fr_section.align_key == "art_336_c"
    assert de_section.split_paragraphs is True
    assert fr_section.split_paragraphs is True


def _akn_with_article_text(body_text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act name="act">
    <preface><p><docTitle>Obligationenrecht</docTitle></p></preface>
    <body>
      <article eId="art_336_c"><num>Art. 336c</num><heading>Kündigung zur Unzeit</heading>
        <paragraph eId="art_336_c/para_1"><num>1</num><content><p>{body_text}</p></content></paragraph>
      </article>
    </body>
  </act>
</akomaNtoso>"""
