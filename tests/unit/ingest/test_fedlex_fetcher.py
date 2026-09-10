import json
from datetime import date
from pathlib import Path

import httpx

from swiss_grounding.ingest.fetchers.fedlex import FedlexFetcher, parse_akoma_ntoso
from swiss_grounding.ingest.models import KnownUrl
from swiss_grounding.registry.models import Source

FIX = Path(__file__).parent.parent.parent / "fixtures" / "fedlex"
SPARQL = json.loads((FIX / "sparql_455.json").read_text())
XML = (FIX / "sr455.xml").read_text()


def source():
    return Source(id="fedlex", name="Fedlex", base_url="https://www.fedlex.admin.ch", default_extent_id="CH",
                  authority="federal_law", categories=("dogs",), fetch_strategy="fedlex_sparql",
                  fetch_config={"sr_numbers": ["455"], "language": "de"})


def handler(request):
    if "sparqlendpoint" in str(request.url):
        assert "455" in (request.content.decode() or str(request.url))
        return httpx.Response(200, json=SPARQL)
    if str(request.url).endswith(".xml"):
        return httpx.Response(200, text=XML, headers={"content-type": "application/xml"})
    return httpx.Response(404)


def test_parse_akoma_ntoso_articles():
    sections = parse_akoma_ntoso(XML)
    assert [s.anchor for s in sections] == ["art_1", "art_6"]
    assert sections[1].heading_path == "Art. 6 Allgemeine Anforderungen"
    assert "Wer ein Tier hält" in sections[1].text and "Der Bundesrat erlässt" in sections[1].text
    assert sections[0].text.startswith("Zweck dieses Gesetzes")


def test_fetch_builds_document_with_dates_and_identifier():
    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = FedlexFetcher(http=http).fetch(source(), {})
    assert len(result.documents) == 1
    d = result.documents[0]
    assert d.url == "https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de"
    assert d.identifier == "SR 455"
    assert d.title == "Tierschutzgesetz (TSchG)" and d.language == "de"
    assert d.valid_from == date(2022, 1, 1) and d.valid_to is None and d.in_force is True
    assert d.sections[1].anchor == "art_6"


def test_known_consolidation_is_unchanged_without_refetching_xml():
    calls = []

    def counting(request):
        calls.append(str(request.url))
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(counting))
    known = {"https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de": KnownUrl(None, None, "h")}
    result = FedlexFetcher(http=http).fetch(source(), known)
    assert result.unchanged_urls == ("https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de",)
    assert not any(u.endswith(".xml") for u in calls)


def test_sparql_failure_is_error():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    result = FedlexFetcher(http=http).fetch(source(), {})
    assert result.documents == () and result.errors[0].url.endswith("sparqlendpoint")
