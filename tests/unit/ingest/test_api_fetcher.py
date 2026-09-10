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
