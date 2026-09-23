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


def test_english_falls_back_to_newest_consolidation_when_none_in_force(tmp_path):
    """Review fix: when English has no in-force row (a stale official translation that was never
    updated), fall back to its newest consolidation regardless of end date, reported as
    status='current' with its real (past) valid_to and is_authentic=False."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = request.content.decode()
            if "ENG" not in body:
                return httpx.Response(200, json={"results": {"bindings": [_binding("2025-07-01", "https://f/de.xml")]}})
            if "dateEndApplicability >=" in body:
                return httpx.Response(200, json={"results": {"bindings": []}})
            return httpx.Response(200, json={"results": {"bindings": [
                _binding("2020-01-01", "https://f/en-old.xml", title="Code of Obligations")]}})
        if "en-old" in str(request.url):
            return httpx.Response(200, text=XML)
        return httpx.Response(200, text=XML)

    connector = FedlexConnector(httpx.Client(transport=httpx.MockTransport(handler)),
                                today=lambda: date(2026, 9, 24), data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(SPEC, known={})
    assert result.errors == ()
    en = next(d for d in result.documents if d.language == "en")
    assert en.status == "current"
    assert en.is_authentic is False
    assert en.title == "Code of Obligations"


def test_partial_known_triggers_full_language_group_redownload(tmp_path):
    """Review fix: if any language version of a SR+status is new, every language version of that
    group is re-downloaded (even ones already `known`), so split_paragraphs stays aligned even
    when only one language actually changed upstream this run."""
    from swiss_grounding.corpus.chunker import MAX_CHARS

    de_xml = _akn_with_article_text("x" * 1700)
    fr_xml = _akn_with_article_text("y" * (MAX_CHARS + 100))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = request.content.decode()
            lang = "fr" if "FRA" in body else "de"
            return httpx.Response(200, json={"results": {"bindings": [_binding("2025-07-01", f"https://f/{lang}.xml")]}})
        if "fr" in str(request.url):
            return httpx.Response(200, text=fr_xml)
        return httpx.Response(200, text=de_xml)

    spec = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                      level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de", "fr"),
                      config={"sr_numbers": ["220"]})
    connector = FedlexConnector(httpx.Client(transport=httpx.MockTransport(handler)),
                                today=lambda: date(2026, 9, 24), data_dir=tmp_path, sleep=lambda s: None)
    de_url = "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/20250701/de"
    result = connector.run(spec, known={de_url: KnownState(None, None, "h")})
    assert result.unchanged_urls == ()
    by_lang = {d.language: d for d in result.documents}
    assert set(by_lang) == {"de", "fr"}
    assert by_lang["de"].sections[0].split_paragraphs is True
    assert by_lang["fr"].sections[0].split_paragraphs is True


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


def test_probe_counts_in_force_consolidations(tmp_path):
    bindings = {"de": [_binding("2025-07-01", "https://f/a.xml"), _binding("2027-01-01", "https://f/b.xml")]}
    connector = FedlexConnector(httpx.Client(transport=_transport(bindings)), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    assert connector.probe("220", "de") == 2
    assert connector.probe("220", "en") == 0


# --- robots.txt: fetch the act files where Fedlex allows it ------------------------------------------

DATA_FILE = ("https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/27/317_321_377/20250701/de/xml/"
             "fedlex-data-admin-ch-eli-cc-27-317_321_377-20250701-de-xml.xml")
WWW_FILE = DATA_FILE.replace("https://fedlex.data.admin.ch/filestore/", "https://www.fedlex.admin.ch/filestore/")


def _recording_transport(bindings_by_lang, robots_by_host, seen):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "POST":
            lang = "en" if "ENG" in request.content.decode() else "de"
            return httpx.Response(200, json={"results": {"bindings": bindings_by_lang.get(lang, [])}})
        seen.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=robots_by_host.get(request.url.host, "User-agent: *\nAllow: /\n"))
        return httpx.Response(200, text=XML)
    return httpx.MockTransport(handler)


def test_act_files_are_downloaded_from_the_www_host_that_robots_allows(tmp_path):
    """fedlex.data.admin.ch/robots.txt disallows /filestore/* for every crawler; the same files
    (byte-identical, checked 2026-09-24) are served under www.fedlex.admin.ch, whose robots.txt
    allows them. The document's identity (its page URL) does not change."""
    seen: list[str] = []
    robots = {"fedlex.data.admin.ch": "User-agent: *\nDisallow: /filestore/*\n",
              "www.fedlex.admin.ch": "User-agent: *\nAllow: /\nDisallow: /*?print=*\n"}
    connector = FedlexConnector(httpx.Client(transport=_recording_transport({"de": [_binding("2025-07-01", DATA_FILE)]},
                                                                            robots, seen)),
                                today=lambda: date(2026, 9, 24), data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(SPEC, known={})
    assert result.errors == ()
    assert WWW_FILE in seen and DATA_FILE not in seen
    [doc] = result.documents
    assert doc.url == "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/20250701/de"


def test_act_file_disallowed_by_robots_is_an_error_not_a_download(tmp_path):
    seen: list[str] = []
    robots = {"www.fedlex.admin.ch": "User-agent: *\nDisallow: /filestore/\n"}
    connector = FedlexConnector(httpx.Client(transport=_recording_transport({"de": [_binding("2025-07-01", DATA_FILE)]},
                                                                            robots, seen)),
                                today=lambda: date(2026, 9, 24), data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(SPEC, known={})
    assert result.documents == ()
    assert WWW_FILE not in seen
    [(_, message)] = result.errors
    assert message == f"RobotsDisallowed: {WWW_FILE} disallowed by robots.txt"


def test_robots_is_not_read_when_switched_off(tmp_path):
    seen: list[str] = []
    robots = {"www.fedlex.admin.ch": "User-agent: *\nDisallow: /\n"}
    connector = FedlexConnector(httpx.Client(transport=_recording_transport({"de": [_binding("2025-07-01", DATA_FILE)]},
                                                                            robots, seen)),
                                today=lambda: date(2026, 9, 24), data_dir=tmp_path, sleep=lambda s: None,
                                respect_robots=False)
    result = connector.run(SPEC, known={})
    assert len(result.documents) == 1
    assert not any(u.endswith("/robots.txt") for u in seen)
