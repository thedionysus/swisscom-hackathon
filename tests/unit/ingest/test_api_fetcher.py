from datetime import date

import httpx

from swiss_grounding.ingest.fetchers.api import ApiFetcher
from swiss_grounding.ingest.models import KnownUrl
from swiss_grounding.registry.models import Source

FEED = {"result": {"records": [
    {"id": "8003-cardboard", "zip": "8003", "type": "cardboard", "date": "2026-10-02", "note": "Karton bündeln"},
    {"id": "8003-paper", "zip": "8003", "type": "paper", "date": "2026-10-09", "note": ""},
]}}


def source():
    return Source(id="open_erz", name="Open ERZ", base_url="https://openerz.example",
                  default_extent_id="CH-ZH-261", authority="official_info", categories=("waste",),
                  fetch_strategy="api",
                  fetch_config={
                      "url": "https://openerz.example/api/calendar?zip=8003",
                      "records_path": "result.records",
                      "id_field": "id",
                      "title_template": "Waste collection {type} in {zip}",
                      "text_template": "Collection of {type} in postal code {zip} on {date}. {note}",
                      "language": "en",
                  })


def test_each_record_becomes_a_document():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=FEED)))
    result = ApiFetcher(http=http).fetch(source(), {})
    assert len(result.documents) == 2
    d = result.documents[0]
    assert d.url == "https://openerz.example/api/calendar?zip=8003#8003-cardboard"
    assert d.title == "Waste collection cardboard in 8003"
    assert d.sections[0].text == "Collection of cardboard in postal code 8003 on 2026-10-02. Karton bündeln"
    assert d.language == "en"


def test_records_no_longer_present_are_gone():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=FEED)))
    known = {"https://openerz.example/api/calendar?zip=8003#old": KnownUrl(None, None, "h")}
    result = ApiFetcher(http=http).fetch(source(), known)
    assert result.gone_urls == ("https://openerz.example/api/calendar?zip=8003#old",)


def test_bad_payload_is_error():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"nope": 1})))
    result = ApiFetcher(http=http).fetch(source(), {})
    assert result.documents == () and "records_path" in result.errors[0].reason


def test_missing_template_field_is_error_not_crash():
    feed = {"result": {"records": [{"id": "x", "zip": "8003"}]}}
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=feed)))
    result = ApiFetcher(http=http).fetch(source(), {})
    assert result.documents == () and "type" in result.errors[0].reason


def test_id_template_builds_composite_ids():
    feed = {"result": [{"date": "2026-10-02", "waste_type": "cardboard", "zip": 8003},
                       {"date": "2026-10-02", "waste_type": "paper", "zip": 8003}]}
    cfg = {"url": "https://erz.example/api", "records_path": "result", "id_template": "{waste_type}-{date}",
           "title_template": "{waste_type} in {zip}", "text_template": "{waste_type} on {date}", "language": "en"}
    src = Source(id="erz", name="ERZ", base_url="https://erz.example", default_extent_id="CH-ZH-261",
                 authority="official_info", categories=("waste",), fetch_strategy="api", fetch_config=cfg)
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=feed)))
    result = ApiFetcher(http=http).fetch(src, {})
    assert [d.url for d in result.documents] == ["https://erz.example/api#cardboard-2026-10-02",
                                                 "https://erz.example/api#paper-2026-10-02"]


def _dated_source():
    return Source(id="erz", name="ERZ", base_url="https://erz.example", default_extent_id="CH-ZH-261",
                  authority="official_info", categories=("waste",), fetch_strategy="api",
                  fetch_config={"url": "https://erz.example/api?start={today}&limit=5", "records_path": "result",
                                "id_template": "{waste_type}-{date}", "title_template": "{waste_type}",
                                "text_template": "{waste_type} on {date}", "language": "en"})


def test_today_placeholder_is_rendered_into_the_request_url():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"result": []})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    ApiFetcher(http=http, today=lambda: date(2026, 9, 12)).fetch(_dated_source(), {})
    assert calls == ["https://erz.example/api?start=2026-09-12&limit=5"]


def test_document_identity_does_not_change_with_the_date():
    feed = {"result": [{"date": "2026-09-17", "waste_type": "cardboard"}]}
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=feed)))
    known = {"https://erz.example/api?limit=5#paper-2026-09-01": KnownUrl(None, None, "h")}
    result = ApiFetcher(http=http, today=lambda: date(2026, 9, 12)).fetch(_dated_source(), known)
    # Placeholder parameters are dropped from the stored url: stable identity and a working link.
    assert result.documents[0].url == "https://erz.example/api?limit=5#cardboard-2026-09-17"
    assert result.gone_urls == ("https://erz.example/api?limit=5#paper-2026-09-01",)


def _event_source(**cfg):
    base = source()
    return Source(**{**base.__dict__, "fetch_config": {**base.fetch_config, **cfg}})


def test_event_date_field_is_parsed_into_event_date():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=FEED)))
    result = ApiFetcher(http=http).fetch(_event_source(event_date_field="date"), {})
    assert [d.event_date for d in result.documents] == [date(2026, 10, 2), date(2026, 10, 9)]


def test_event_date_is_none_when_missing_or_malformed():
    feed = {"result": {"records": [
        {"id": "a", "zip": "8003", "type": "paper", "date": "not-a-date", "note": ""},
        {"id": "b", "zip": "8003", "type": "paper", "date": "2026-01-01", "note": ""},
    ]}}
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=feed)))
    result = ApiFetcher(http=http).fetch(_event_source(event_date_field="date"), {})
    assert [d.event_date for d in result.documents] == [None, date(2026, 1, 1)]
    assert result.errors == ()
    plain = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=FEED)))
    assert ApiFetcher(http=plain).fetch(source(), {}).documents[0].event_date is None
