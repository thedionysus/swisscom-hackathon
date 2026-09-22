import logging
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

log = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://fedlex.data.admin.ch/sparqlendpoint"
LANGUAGE_URI = {
    "de": "http://publications.europa.eu/resource/authority/language/DEU",
    "fr": "http://publications.europa.eu/resource/authority/language/FRA",
    "it": "http://publications.europa.eu/resource/authority/language/ITA",
}
XML_FORMAT_URI = "http://publications.europa.eu/resource/authority/file-type/XML"
# The language a Fedlex source is read in unless it says otherwise. Named because `retitle` has
# to ask the endpoint the same question in the same language this fetcher would.
DEFAULT_LANGUAGE = "de"
DOC_TITLE_TAG = "docTitle"  # the act's own heading in the Akoma Ntoso preface

# Current consolidation of one SR number in one language, with the Akoma Ntoso file URL and the
# act's title. The title lives on the ConsolidationAbstract's language expression (jolux:title on
# <.../eli/cc/2008/414/de>); the consolidation's own expression carries none, which is why an
# earlier OPTIONAL against ?expr never bound and every act was titled by its SR number.
QUERY = """
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?abstract ?consolidation ?dateApplicability ?dateEndApplicability ?title ?fileUrl WHERE {
  ?abstract a jolux:ConsolidationAbstract ;
            jolux:classifiedByTaxonomyEntry ?entry .
  ?entry skos:notation ?sr .
  FILTER(str(?sr) = "%(sr)s")
  ?consolidation jolux:isMemberOf ?abstract ;
                 jolux:dateApplicability ?dateApplicability ;
                 jolux:isRealizedBy ?expr .
  OPTIONAL { ?consolidation jolux:dateEndApplicability ?dateEndApplicability }
  ?expr jolux:language <%(lang)s> ;
        jolux:isEmbodiedBy ?manif .
  OPTIONAL {
    ?abstract jolux:isRealizedBy ?abstractExpr .
    ?abstractExpr jolux:language <%(lang)s> ;
                  jolux:title ?title .
  }
  ?manif jolux:format <%(xml)s> ;
         jolux:isExemplifiedBy ?fileUrl .
  FILTER(!bound(?dateEndApplicability) || ?dateEndApplicability >= now())
}
ORDER BY DESC(?dateApplicability)
LIMIT 1
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


def parse_act_title(xml: str) -> str | None:
    """The act's own name from the Akoma Ntoso preface, for when the endpoint names no title."""
    node = BeautifulSoup(xml, "xml").find(DOC_TITLE_TAG)
    return (node.get_text(" ", strip=True) if node else "") or None


def sr_label(sr: str) -> str:
    """The identifier a stored document carries for one SR number. Public because `retitle` reads
    stored identifiers back, and both sides must spell it the same way."""
    return f"SR {sr}"


def _value(binding: dict[str, Any], key: str) -> str | None:
    node = binding.get(key)
    return node["value"] if node else None


def _title(binding: dict[str, Any], xml: str, sr: str) -> str:
    """The act's name, from the endpoint or from the document itself; the SR number only if neither
    names it, which leaves a document titled by a number and is worth a line in the log."""
    title = _value(binding, "title") or parse_act_title(xml)
    if title:
        return title
    log.warning("no act title for SR %s; falling back to the SR number", sr)
    return sr_label(sr)


def _page_url(abstract_uri: str, date_applicability: str, lang: str) -> str:
    # https://fedlex.data.admin.ch/eli/cc/2008/414 -> https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de
    path = abstract_uri.split("fedlex.data.admin.ch", 1)[1]
    return f"https://www.fedlex.admin.ch{path}/{date_applicability.replace('-', '')}/{lang}"


class FedlexFetcher:
    """Resolve SR numbers to their current consolidation and parse the Akoma Ntoso XML."""

    def __init__(self, http: httpx.Client, endpoint: str = SPARQL_ENDPOINT,
                 retry: RetryPolicy = DEFAULT_RETRY_POLICY, sleep: Sleep = time.sleep):
        self._http = http
        self._endpoint = endpoint
        self.retry = retry
        self._sleep = sleep

    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult:
        lang = source.fetch_config.get("language", DEFAULT_LANGUAGE)
        documents, unchanged, errors = [], [], []
        for sr in source.fetch_config.get("sr_numbers", ()):
            try:
                binding = self._current_with_retry(sr, lang)
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(FetchError(url=self._endpoint, reason=f"SR {sr}: {exc}"))
                continue
            if binding is None:
                # The endpoint answers an empty set both for a transient outage and for a law with no
                # consolidation, so after exhausting retries we can only say the result stayed empty.
                errors.append(FetchError(url=self._endpoint, reason=(
                    f"SR {sr}: empty SPARQL result after {self.retry.attempts} attempts "
                    "(upstream outage or no current consolidation)")))
                continue
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
                source_id=source.id, url=url, identifier=sr_label(sr),
                title=_title(binding, xml.text, sr), language=lang, sections=sections,
                valid_from=date.fromisoformat(date_app), valid_to=date.fromisoformat(end) if end else None,
                in_force=end is None,
            ))
        return FetchResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))

    def current_consolidation(self, sr: str, lang: str) -> dict[str, Any] | None:
        """The current consolidation binding for one SR number, retried; None if it stays empty.

        The public entry `retitle` uses: it wants the act's title out of the binding and nothing
        else, and downloading the Akoma Ntoso file to get it would be a crawl this repair does not
        need. Free and read-only, which is why the dry run may make the call too.
        """
        return self._current_with_retry(sr, lang)

    def _current_with_retry(self, sr: str, lang: str) -> dict[str, Any] | None:
        """Retry the SPARQL lookup on transport errors, 5xx, timeouts, and empty result sets."""
        return retry(
            lambda: self._current(sr, lang),
            policy=self.retry,
            retry_on=(httpx.TransportError, _ServerError),
            retry_if=lambda binding: binding is None,
            sleep=self._sleep,
        )

    def _current(self, sr: str, lang: str) -> dict[str, Any] | None:
        query = QUERY % {"sr": sr, "lang": LANGUAGE_URI[lang], "xml": XML_FORMAT_URI}
        response = self._http.post(
            self._endpoint, data={"query": query},
            headers={"accept": "application/sparql-results+json"},
        )
        if response.is_server_error:
            raise _ServerError(f"SPARQL endpoint returned HTTP {response.status_code}", request=response.request,
                               response=response)
        response.raise_for_status()
        bindings = response.json().get("results", {}).get("bindings", [])
        return bindings[0] if bindings else None


class _ServerError(httpx.HTTPStatusError):
    """A 5xx from the SPARQL endpoint: transient by assumption, hence retried."""
