from datetime import date

import httpx
import pytest

from swiss_grounding.corpus.connectors.html import CrawlPolicy
from swiss_grounding.corpus.connectors.json_api import (
    JsonConnector,
    RecordError,
    dig,
    parse_date,
    render,
)
from swiss_grounding.corpus.models import SourceSpec

API = "https://data.x.ch/records"
HOLIDAYS = [{"year": "2026/27", "name": "Herbstferien", "start": "2026-09-26", "end": "2026-10-11"},
            {"year": "2026/27", "name": "Weihnachtsferien", "start": "2026-12-24", "end": "2027-01-06"},
            {"year": "2026/27", "name": "Sportferien", "start": "2027-02-06", "end": "2027-02-21"}]
PAGES = {API + "?limit=2&offset=0": {"total_count": 3, "results": HOLIDAYS[:2]},
         API + "?limit=2&offset=2": {"total_count": 3, "results": HOLIDAYS[2:]}}


def _spec(**config):
    base = {"url": API + "?limit={size}&offset={offset}", "paging": {"style": "offset", "size": 2},
            "records_path": "results", "id_template": "{year}-{name}", "title_template": "{name} {year}",
            "text_template": "{name} {year}: {start} bis {end}", "cite_url": "https://data.x.ch/explore/holidays/"}
    base.update(config)
    return SourceSpec(id="x_holidays", name="X", publisher="X", authority="official_info", level="cantonal",
                      extent_id="CH-SZ", connector="json", tier=2, languages=("de",), config=base)


def _client(responses, robots="User-agent: *\nAllow: /\n", seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=robots)
        if url in responses:
            return httpx.Response(200, json=responses[url])
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


def _run(spec, client, respect_robots=True):
    return JsonConnector(client, CrawlPolicy(respect_robots, 0), sleep=lambda _: None).run(spec, known={})


def test_offset_paging_reads_every_page_and_stops_at_a_short_page():
    seen = []
    result = _run(_spec(), _client(PAGES, seen=seen))
    assert [u for u in seen if not u.endswith("robots.txt")] == list(PAGES)
    assert [d.title for d in result.documents] == ["Herbstferien 2026/27", "Weihnachtsferien 2026/27",
                                                   "Sportferien 2026/27"]
    first = result.documents[0]
    assert first.url == "https://data.x.ch/explore/holidays/#2026%2F27-Herbstferien"
    assert first.work_key == "json:x_holidays:2026/27-Herbstferien"
    assert first.identifier == "2026/27-Herbstferien"
    assert first.language == "de"
    [section] = first.sections
    assert section.text == "Herbstferien 2026/27: 2026-09-26 bis 2026-10-11"
    assert section.breadcrumb == ("Herbstferien 2026/27",)
    assert section.align_key == "de:0"
    assert result.errors == ()
    assert result.gone_urls == ()


def test_offset_paging_stops_at_an_empty_page():
    pages = {API + "?limit=3&offset=0": {"results": HOLIDAYS}, API + "?limit=3&offset=3": {"results": []}}
    seen = []
    result = _run(_spec(paging={"style": "offset", "size": 3}), _client(pages, seen=seen))
    assert len(result.documents) == 3
    assert [u for u in seen if not u.endswith("robots.txt")] == list(pages)


def test_next_paging_follows_the_link_until_it_is_missing():
    first = "https://api.x.ch/@search?b_size=2"
    second = "https://api.x.ch/@search?b_size=2&b_start=2"
    pages = {first: {"items": HOLIDAYS[:2], "batching": {"next": second}},
             second: {"items": HOLIDAYS[2:], "batching": {"last": second}}}
    result = _run(_spec(url="https://api.x.ch/@search?b_size={size}", paging={"style": "next", "size": 2},
                        records_path="items"), _client(pages))
    assert len(result.documents) == 3


def test_max_records_caps_the_run():
    seen = []
    result = _run(_spec(max_records=2), _client(PAGES, seen=seen))
    assert len(result.documents) == 2
    assert API + "?limit=2&offset=2" not in seen


def test_a_missing_or_empty_field_is_a_record_error_not_an_exception():
    records = [HOLIDAYS[0], {**HOLIDAYS[1], "end": None}, {k: v for k, v in HOLIDAYS[2].items() if k != "end"}]
    result = _run(_spec(paging={"style": "none"}, url=API), _client({API: {"results": records}}))
    assert [d.title for d in result.documents] == ["Herbstferien 2026/27"]
    assert [reason for _, reason in result.errors] == ["field 'end' is empty", "missing field 'end'"]


def test_a_duplicate_record_is_reported_once():
    result = _run(_spec(paging={"style": "none"}, url=API), _client({API: {"results": [HOLIDAYS[0], HOLIDAYS[0]]}}))
    assert len(result.documents) == 1
    assert "duplicate" in result.errors[0][1]


BACKEND = "https://backend.x.ch/steuerbuch"
TREE = [
    {"@id": BACKEND, "title": "Steuerbuch", "UID": "b"},
    {"@id": BACKEND + "/abzuege", "title": "Abzüge", "UID": "c1"},
    {"@id": BACKEND + "/abzuege/periode-2026", "title": "Steuerperiode 2026", "UID": "c2"},
    {"@id": BACKEND + "/abzuege/periode-2026/periode-2026", "title": "Steuerperiode 2026", "UID": "p1",
     "modified": "2026-01-14T13:59:52+00:00",
     "text": {"data": "<p>Der Abzug gilt pro Person.</p><h3>Beispiel</h3><p>Fr. 3000.</p>"}},
]


def test_a_tree_of_records_gives_breadcrumbs_and_html_sections():
    spec = _spec(url=BACKEND + "/@search?fullobjects=1", paging={"style": "none"}, records_path="items",
                 id_template="{UID}", title_template="{_parent}: {title}", text_template=None,
                 html_path="text.data", url_template="{@id}", url_replace=[BACKEND, "https://www.x.ch/steuerbuch"],
                 breadcrumbs={"id_path": "@id", "title_path": "title"}, modified_path="modified", cite_url=None)
    result = _run(spec, _client({BACKEND + "/@search?fullobjects=1": {"items": TREE}}))
    [doc] = result.documents  # the book and the chapters have no text: levels of the tree, not documents
    assert doc.url == "https://www.x.ch/steuerbuch/abzuege/periode-2026/periode-2026"
    assert doc.title == "Abzüge: Steuerperiode 2026"
    assert doc.modified_at == date(2026, 1, 14)
    assert [s.breadcrumb for s in doc.sections] == [("Steuerbuch", "Abzüge", "Steuerperiode 2026"),
                                                    ("Steuerbuch", "Abzüge", "Steuerperiode 2026", "Beispiel")]
    assert [s.text for s in doc.sections] == ["Der Abzug gilt pro Person.", "Fr. 3000."]
    assert result.errors == ()


def test_robots_txt_is_respected_by_default_and_can_be_switched_off():
    refused = _run(_spec(), _client(PAGES, robots="User-agent: *\nDisallow: /\n"))
    assert refused.documents == ()
    assert refused.errors == ((API + "?limit=2&offset=0", "disallowed by robots.txt"),)
    allowed = _run(_spec(), _client(PAGES, robots="User-agent: *\nDisallow: /\n"), respect_robots=False)
    assert len(allowed.documents) == 3


def test_an_http_error_is_reported_and_ends_the_source():
    result = _run(_spec(), _client({}))
    assert result.documents == ()
    assert result.errors == ((API + "?limit=2&offset=0", "HTTP 404"),)


def test_dig_render_and_parse_date():
    record = {"meta": {"title": "T", "none": None}, "items": [{"x": 1}]}
    assert dig(record, "meta.title") == "T"
    assert dig(record, "items.0.x") == 1
    assert dig(record, "meta.missing") is None
    assert render("{meta[title]}!", record) == "T!"
    with pytest.raises(RecordError, match="empty"):
        render("{meta[none]}", record)
    assert parse_date("2026-01-14T13:59:52+00:00") == date(2026, 1, 14)
    assert parse_date("2026-09-26") == date(2026, 9, 26)
    assert parse_date("05.01.2023") == date(2023, 1, 5)
    assert parse_date("31.02.2023") is None
    assert parse_date("soon") is None
