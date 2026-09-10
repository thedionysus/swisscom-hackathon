from collections.abc import Mapping
from datetime import date
from typing import Any

import httpx
from bs4 import BeautifulSoup

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
}
XML_FORMAT_URI = "http://publications.europa.eu/resource/authority/file-type/XML"

# Current consolidation of one SR number in one language, with the Akoma Ntoso file URL.
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
  OPTIONAL { ?expr jolux:title ?title }
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


def _value(binding: dict[str, Any], key: str) -> str | None:
    node = binding.get(key)
    return node["value"] if node else None


def _page_url(abstract_uri: str, date_applicability: str, lang: str) -> str:
    # https://fedlex.data.admin.ch/eli/cc/2008/414 -> https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de
    path = abstract_uri.split("fedlex.data.admin.ch", 1)[1]
    return f"https://www.fedlex.admin.ch{path}/{date_applicability.replace('-', '')}/{lang}"


class FedlexFetcher:
    """Resolve SR numbers to their current consolidation and parse the Akoma Ntoso XML."""

    def __init__(self, http: httpx.Client, endpoint: str = SPARQL_ENDPOINT):
        self._http = http
        self._endpoint = endpoint

    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult:
        lang = source.fetch_config.get("language", "de")
        documents, unchanged, errors = [], [], []
        for sr in source.fetch_config.get("sr_numbers", ()):
            try:
                binding = self._current(sr, lang)
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(FetchError(url=self._endpoint, reason=f"SR {sr}: {exc}"))
                continue
            if binding is None:
                errors.append(FetchError(url=self._endpoint, reason=f"SR {sr}: no current consolidation"))
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
                source_id=source.id, url=url, identifier=f"SR {sr}",
                title=_value(binding, "title") or f"SR {sr}", language=lang, sections=sections,
                valid_from=date.fromisoformat(date_app), valid_to=date.fromisoformat(end) if end else None,
                in_force=end is None,
            ))
        return FetchResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))

    def _current(self, sr: str, lang: str) -> dict[str, Any] | None:
        query = QUERY % {"sr": sr, "lang": LANGUAGE_URI[lang], "xml": XML_FORMAT_URI}
        response = self._http.post(
            self._endpoint, data={"query": query},
            headers={"accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        bindings = response.json().get("results", {}).get("bindings", [])
        return bindings[0] if bindings else None
