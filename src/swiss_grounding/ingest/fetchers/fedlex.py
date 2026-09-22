import time
from collections.abc import Mapping
from datetime import date
from typing import Any

import httpx
from bs4 import BeautifulSoup

from swiss_grounding.ingest.fetchers.retry import DEFAULT_RETRY_POLICY, RetryPolicy, Sleep, retry
from swiss_grounding.ingest.models import (
    FetchedDocument,
    FetchError,
    FetchResult,
    KnownUrl,
    Section,
)
from swiss_grounding.registry.models import Source

SPARQL_ENDPOINT = "https://fedlex.data.admin.ch/sparqlendpoint"
LANGUAGE_URI = {
    "de": "http://publications.europa.eu/resource/authority/language/DEU",
    "fr": "http://publications.europa.eu/resource/authority/language/FRA",
    "it": "http://publications.europa.eu/resource/authority/language/ITA",
    # Official English editions exist for a minority of acts (292 with XML on 2026-09-22). They are
    # marked non-binding in the document text itself; enrich() skips translation for language "en".
    "en": "http://publications.europa.eu/resource/authority/language/ENG",
}
XML_FORMAT_URI = "http://publications.europa.eu/resource/authority/file-type/XML"

# Current consolidations of one SR number in the requested languages, with the Akoma Ntoso file URL,
# newest first. The caller picks the preferred language among the rows at the newest date.
QUERY = """
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?abstract ?consolidation ?dateApplicability ?dateEndApplicability ?title ?fileUrl ?lang WHERE {
  VALUES ?lang { %(langs)s }
  ?abstract a jolux:ConsolidationAbstract ;
            jolux:classifiedByTaxonomyEntry ?entry .
  ?entry skos:notation ?sr .
  FILTER(str(?sr) = "%(sr)s")
  ?consolidation jolux:isMemberOf ?abstract ;
                 jolux:dateApplicability ?dateApplicability ;
                 jolux:isRealizedBy ?expr .
  OPTIONAL { ?consolidation jolux:dateEndApplicability ?dateEndApplicability }
  ?expr jolux:language ?lang ;
        jolux:isEmbodiedBy ?manif .
  OPTIONAL { ?expr jolux:title ?title }
  ?manif jolux:format <%(xml)s> ;
         jolux:isExemplifiedBy ?fileUrl .
  FILTER(!bound(?dateEndApplicability) || ?dateEndApplicability >= now())
}
ORDER BY DESC(?dateApplicability)
LIMIT 20
"""


def parse_akoma_ntoso(xml: str) -> tuple[Section, ...]:
    """One section per <article>: heading_path 'Art. N Heading', anchor = eId, text = paragraphs."""
    soup = BeautifulSoup(xml, "xml")
    sections = []
    for article in soup.find_all("article"):
        num = article.find("num", recursive=False)
        heading = article.find("heading", recursive=False)
        label = " ".join(x.get_text(" ", strip=True) for x in (num, heading) if x)
        paragraphs = [p.get_text(" ", strip=True) for p in article.find_all("content")]
        text = "\n".join(t for t in paragraphs if t)
        if text:
            sections.append(Section(heading_path=label or article.get("eId", ""), anchor=article.get("eId"), text=text))
    return tuple(sections)


def _value(binding: dict[str, Any], key: str) -> str | None:
    node = binding.get(key)
    return node["value"] if node else None


def _page_url(abstract_uri: str, date_applicability: str, lang: str) -> str:
    # https://fedlex.data.admin.ch/eli/cc/2008/414 -> https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de
    path = abstract_uri.split("fedlex.data.admin.ch", 1)[1]
    return f"https://www.fedlex.admin.ch{path}/{date_applicability.replace('-', '')}/{lang}"


def _language_of(binding: dict[str, Any], default: str) -> str:
    """Language code of a result row, from the ?lang URI; `default` when the row carries none."""
    uri = _value(binding, "lang")
    for code, known in LANGUAGE_URI.items():
        if uri == known:
            return code
    return default


def _choose(bindings: list[dict[str, Any]], preferred: str, fallback: str | None) -> tuple[dict[str, Any], str] | None:
    """The row to ingest and its language.

    Only rows at the newest consolidation date qualify: an English edition that lags the current
    German consolidation would present superseded law, so the fallback language wins in that case.
    Among the qualifying rows the preferred language wins, then the fallback.
    """
    if not bindings:
        return None
    newest = max(_value(b, "dateApplicability") or "" for b in bindings)
    current = [b for b in bindings if (_value(b, "dateApplicability") or "") == newest]
    for lang in (preferred, fallback):
        if lang is None:
            continue
        for binding in current:
            if _language_of(binding, preferred) == lang:
                return binding, lang
    return None


class FedlexFetcher:
    """Resolve SR numbers to their current consolidation and parse the Akoma Ntoso XML.

    ``fetch_config.language`` is the preferred edition; ``fetch_config.fallback_language`` (optional)
    is used for acts that have no current edition in the preferred one, e.g. ``language: en`` with
    ``fallback_language: de`` ingests the official English text where Fedlex publishes one and the
    German text everywhere else.
    """

    def __init__(self, http: httpx.Client, endpoint: str = SPARQL_ENDPOINT,
                 retry: RetryPolicy = DEFAULT_RETRY_POLICY, sleep: Sleep = time.sleep):
        self._http = http
        self._endpoint = endpoint
        self.retry = retry
        self._sleep = sleep

    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult:
        preferred = source.fetch_config.get("language", "de")
        fallback = source.fetch_config.get("fallback_language")
        languages = [preferred] + ([fallback] if fallback and fallback != preferred else [])
        unknown = [code for code in languages if code not in LANGUAGE_URI]
        if unknown:
            return FetchResult(documents=(), errors=(FetchError(
                url=self._endpoint, reason=f"unknown language(s) {unknown}; known: {sorted(LANGUAGE_URI)}"),))
        documents, unchanged, errors = [], [], []
        for sr in source.fetch_config.get("sr_numbers", ()):
            try:
                bindings = self._current_with_retry(sr, languages)
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(FetchError(url=self._endpoint, reason=f"SR {sr}: {exc}"))
                continue
            chosen = _choose(bindings, preferred, fallback)
            if chosen is None:
                # The endpoint answers an empty set both for a transient outage and for a law with no
                # consolidation, so after exhausting retries we can only say the result stayed empty.
                errors.append(FetchError(url=self._endpoint, reason=(
                    f"SR {sr}: empty SPARQL result after {self.retry.attempts} attempts "
                    "(upstream outage or no current consolidation)")))
                continue
            binding, lang = chosen
            date_app = _value(binding, "dateApplicability")
            url = _page_url(_value(binding, "abstract"), date_app, lang)
            if url in known:
                unchanged.append(url)
                continue
            try:
                xml = self._http.get(_value(binding, "fileUrl"), follow_redirects=True)
                xml.raise_for_status()
                sections = parse_akoma_ntoso(xml.text)
            except httpx.HTTPError as exc:
                errors.append(FetchError(url=url, reason=str(exc)))
                continue
            if not sections:
                errors.append(FetchError(url=url, reason="no articles parsed"))
                continue
            end = _value(binding, "dateEndApplicability")
            documents.append(FetchedDocument(
                source_id=source.id, url=url, identifier=f"SR {sr}",
                title=_value(binding, "title") or f"SR {sr}", language=lang, sections=sections,
                valid_from=date.fromisoformat(date_app), valid_to=date.fromisoformat(end) if end else None,
                in_force=end is None,
            ))
        return FetchResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))

    def _current_with_retry(self, sr: str, languages: list[str]) -> list[dict[str, Any]]:
        """Retry the SPARQL lookup on transport errors, 5xx, timeouts, and empty result sets."""
        return retry(
            lambda: self._current(sr, languages),
            policy=self.retry,
            retry_on=(httpx.TransportError, _ServerError),
            retry_if=lambda bindings: not bindings,
            sleep=self._sleep,
        )

    def _current(self, sr: str, languages: list[str]) -> list[dict[str, Any]]:
        langs = " ".join(f"<{LANGUAGE_URI[code]}>" for code in languages)
        query = QUERY % {"sr": sr, "langs": langs, "xml": XML_FORMAT_URI}
        response = self._http.post(
            self._endpoint, data={"query": query},
            headers={"accept": "application/sparql-results+json"},
        )
        if response.is_server_error:
            raise _ServerError(f"SPARQL endpoint returned HTTP {response.status_code}", request=response.request,
                               response=response)
        response.raise_for_status()
        return list(response.json().get("results", {}).get("bindings", []))


class _ServerError(httpx.HTTPStatusError):
    """A 5xx from the SPARQL endpoint: transient by assumption, hence retried."""
