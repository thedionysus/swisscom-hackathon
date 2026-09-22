import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

import httpx

from swiss_grounding.ingest.fetchers.fedlex import FedlexFetcher, parse_act_title, parse_akoma_ntoso
from swiss_grounding.ingest.fetchers.retry import RetryPolicy
from swiss_grounding.ingest.models import FetchError, KnownUrl
from swiss_grounding.registry.models import Source

FIX = Path(__file__).parent.parent.parent / "fixtures" / "fedlex"
SPARQL = json.loads((FIX / "sparql_455.json").read_text())
XML = (FIX / "sr455.xml").read_text()
# Verified against the live endpoint: jolux:title on the abstract's language expression.
ACT_TITLE = "Tierschutzgesetz vom 16. Dezember 2005 (TSchG)"
DOC_TITLE = "Tierschutzgesetz"  # the <docTitle> in the Akoma Ntoso preface


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
    assert d.title == ACT_TITLE and d.language == "de"
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
    result = FedlexFetcher(http=http, retry=NO_SLEEP).fetch(source(), {})
    assert result.documents == () and result.errors[0].url.endswith("sparqlendpoint")


EMPTY = {"results": {"bindings": []}}
NO_SLEEP = RetryPolicy(attempts=3, backoff_seconds=0)


def handler_xml(request):
    if str(request.url).endswith(".xml"):
        return httpx.Response(200, text=XML, headers={"content-type": "application/xml"})
    return httpx.Response(404)


def flaky_sparql(responses):
    """SPARQL replies are served from `responses` in order; XML is always served."""
    calls = []
    queue = list(responses)

    def handler(request):
        if "sparqlendpoint" in str(request.url):
            calls.append("sparql")
            return queue.pop(0)
        return handler_xml(request)

    return handler, calls


def test_empty_sparql_result_is_retried_then_succeeds():
    handler, calls = flaky_sparql([httpx.Response(200, json=EMPTY), httpx.Response(200, json=EMPTY),
                                   httpx.Response(200, json=SPARQL)])
    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = FedlexFetcher(http=http, retry=NO_SLEEP).fetch(source(), {})
    assert result.errors == () and len(result.documents) == 1
    assert calls.count("sparql") == 3


def test_persistently_empty_sparql_result_is_reported_distinctly():
    handler, calls = flaky_sparql([httpx.Response(200, json=EMPTY)] * 3)
    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = FedlexFetcher(http=http, retry=NO_SLEEP).fetch(source(), {})
    assert result.documents == ()
    assert result.errors == (FetchError(
        url="https://fedlex.data.admin.ch/sparqlendpoint",
        reason="SR 455: empty SPARQL result after 3 attempts (upstream outage or no current consolidation)"),)
    assert calls.count("sparql") == 3


def test_server_error_is_retried_then_succeeds():
    handler, calls = flaky_sparql([httpx.Response(503), httpx.Response(200, json=SPARQL)])
    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = FedlexFetcher(http=http, retry=NO_SLEEP).fetch(source(), {})
    assert result.errors == () and len(result.documents) == 1
    assert calls.count("sparql") == 2


def test_retry_backoff_uses_injected_sleep():
    slept = []
    handler, _ = flaky_sparql([httpx.Response(200, json=EMPTY), httpx.Response(200, json=SPARQL)])
    http = httpx.Client(transport=httpx.MockTransport(handler))
    FedlexFetcher(http=http, retry=RetryPolicy(attempts=3, backoff_seconds=0.25), sleep=slept.append).fetch(source(), {})
    assert slept == [0.25]


# The live endpoint carries jolux:title on the ConsolidationAbstract's language expression, not on
# the consolidation's own expression. A query that asks the consolidation for a title gets nothing
# back, which is how five acts came to be titled by their SR number.
ABSTRACT_EXPRESSION = "?abstract jolux:isRealizedBy"


def posted_query(request):
    return parse_qs(request.content.decode())["query"][0]


def live_like_sparql(request):
    """Stand in for the endpoint: ?title binds only when the query reaches the abstract's expression."""
    if "sparqlendpoint" not in str(request.url):
        return handler_xml(request)
    binding = dict(SPARQL["results"]["bindings"][0])
    if ABSTRACT_EXPRESSION not in posted_query(request):
        binding.pop("title", None)
    return httpx.Response(200, json={"results": {"bindings": [binding]}})


def fetch_one(handler):
    result = FedlexFetcher(http=httpx.Client(transport=httpx.MockTransport(handler))).fetch(source(), {})
    assert result.errors == () and len(result.documents) == 1
    return result.documents[0]


def test_fedlex_title_is_the_act_title_not_the_sr_number():
    assert fetch_one(live_like_sparql).title == ACT_TITLE


def test_parse_act_title_reads_the_akoma_ntoso_doc_title():
    assert parse_act_title(XML) == DOC_TITLE
    assert parse_act_title("<akomaNtoso><act><preface><p/></preface></act></akomaNtoso>") is None


def test_title_falls_back_to_the_act_heading_when_the_endpoint_binds_none():
    def untitled(request):
        if "sparqlendpoint" not in str(request.url):
            return handler_xml(request)
        binding = {k: v for k, v in SPARQL["results"]["bindings"][0].items() if k != "title"}
        return httpx.Response(200, json={"results": {"bindings": [binding]}})

    assert fetch_one(untitled).title == DOC_TITLE
