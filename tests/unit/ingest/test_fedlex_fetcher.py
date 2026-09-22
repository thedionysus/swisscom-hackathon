import json
from datetime import date
from pathlib import Path
from urllib.parse import unquote_plus

import httpx

from swiss_grounding.ingest.fetchers.fedlex import LANGUAGE_URI, FedlexFetcher, parse_akoma_ntoso
from swiss_grounding.ingest.fetchers.retry import RetryPolicy
from swiss_grounding.ingest.models import FetchError, KnownUrl
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


# --- official English editions -------------------------------------------------------------------

def _row(lang: str, date_applicability: str = "2022-01-01"):
    """The fixture's binding, re-labelled with a language URI, a date and a language-specific XML URL."""
    base = SPARQL["results"]["bindings"][0]
    return {**base,
            "lang": {"type": "uri", "value": LANGUAGE_URI[lang]},
            "dateApplicability": {"type": "literal", "value": date_applicability},
            "fileUrl": {"type": "uri", "value": f"https://fedlex.data.admin.ch/filestore/x/{lang}/xml/sr455.xml"}}


def _sparql(*rows):
    return {"results": {"bindings": list(rows)}}


def english_source(fallback="de"):
    cfg = {"sr_numbers": ["455"], "language": "en"}
    if fallback:
        cfg["fallback_language"] = fallback
    return Source(id="fedlex", name="Fedlex", base_url="https://www.fedlex.admin.ch", default_extent_id="CH",
                  authority="federal_law", categories=("dogs",), fetch_strategy="fedlex_sparql", fetch_config=cfg)


def test_english_edition_is_chosen_when_it_matches_the_current_consolidation():
    handler, _ = flaky_sparql([httpx.Response(200, json=_sparql(_row("en"), _row("de")))])
    result = FedlexFetcher(http=httpx.Client(transport=httpx.MockTransport(handler))).fetch(english_source(), {})
    assert result.errors == () and len(result.documents) == 1
    d = result.documents[0]
    assert d.language == "en"
    assert d.url == "https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/en"


def test_falls_back_to_german_when_the_act_has_no_english_edition():
    handler, calls = flaky_sparql([httpx.Response(200, json=_sparql(_row("de")))])
    result = FedlexFetcher(http=httpx.Client(transport=httpx.MockTransport(handler)), retry=NO_SLEEP).fetch(
        english_source(), {})
    assert result.errors == () and result.documents[0].language == "de"
    assert result.documents[0].url.endswith("/de")
    assert calls.count("sparql") == 1  # one query covers both languages; no retry for a missing edition


def test_falls_back_when_the_english_edition_lags_the_current_consolidation():
    handler, _ = flaky_sparql([httpx.Response(200, json=_sparql(_row("de", "2022-01-01"), _row("en", "2020-01-01")))])
    result = FedlexFetcher(http=httpx.Client(transport=httpx.MockTransport(handler))).fetch(english_source(), {})
    d = result.documents[0]
    assert d.language == "de" and d.valid_from == date(2022, 1, 1)


def test_no_fallback_and_no_english_edition_is_reported_as_empty():
    handler, _ = flaky_sparql([httpx.Response(200, json=_sparql(_row("de")))] * 3)
    result = FedlexFetcher(http=httpx.Client(transport=httpx.MockTransport(handler)), retry=NO_SLEEP).fetch(
        english_source(fallback=None), {})
    assert result.documents == () and "SR 455" in result.errors[0].reason


def test_query_asks_for_both_languages_when_a_fallback_is_configured():
    seen = []

    def handler(request):
        if "sparqlendpoint" in str(request.url):
            seen.append(request.content.decode())
            return httpx.Response(200, json=_sparql(_row("en"), _row("de")))
        return handler_xml(request)

    FedlexFetcher(http=httpx.Client(transport=httpx.MockTransport(handler))).fetch(english_source(), {})
    body = unquote_plus(seen[0])  # form-encoded POST body
    assert LANGUAGE_URI["en"] in body and LANGUAGE_URI["de"] in body


def test_unknown_language_is_a_source_level_error_not_a_crash():
    handler, calls = flaky_sparql([])
    cfg = {"sr_numbers": ["455"], "language": "xx"}
    src = Source(id="fedlex", name="Fedlex", base_url="https://www.fedlex.admin.ch", default_extent_id="CH",
                 authority="federal_law", fetch_strategy="fedlex_sparql", fetch_config=cfg)
    result = FedlexFetcher(http=httpx.Client(transport=httpx.MockTransport(handler))).fetch(src, {})
    assert result.documents == () and "unknown language" in result.errors[0].reason and calls == []
