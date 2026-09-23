"""Fedlex SPARQL connector: every manifest language, current and scheduled consolidations."""
import dataclasses
import time
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

import httpx

from swiss_grounding.corpus.artifacts import save_artifact
from swiss_grounding.corpus.chunker import MAX_CHARS
from swiss_grounding.corpus.connectors.fedlex_akn import parse_akn
from swiss_grounding.corpus.models import ConnectorResult, KnownState, ParsedDocument, SourceSpec

ENDPOINT = "https://fedlex.data.admin.ch/sparqlendpoint"
LANGUAGE_URI = {
    "de": "http://publications.europa.eu/resource/authority/language/DEU",
    "fr": "http://publications.europa.eu/resource/authority/language/FRA",
    "it": "http://publications.europa.eu/resource/authority/language/ITA",
    "en": "http://publications.europa.eu/resource/authority/language/ENG",
}
XML_FORMAT_URI = "http://publications.europa.eu/resource/authority/file-type/XML"
OPTIONAL_LANGUAGES = frozenset({"en"})   # English exists for ~290 acts only; its absence is not an error
QUERY = """
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?abstract ?dateApplicability ?dateEndApplicability ?title ?fileUrl WHERE {
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
"""
ATTEMPTS = 3


def choose_consolidations(rows: list[dict], today: date) -> tuple[dict | None, dict | None]:
    """(current, scheduled): latest already applicable, earliest not yet applicable."""
    past = [r for r in rows if r["applicability"] <= today]
    future = [r for r in rows if r["applicability"] > today]
    current = max(past, key=lambda r: r["applicability"]) if past else None
    scheduled = min(future, key=lambda r: r["applicability"]) if future else None
    return current, scheduled


def _page_url(abstract: str, applicability: date, lang: str) -> str:
    base = abstract.replace("https://fedlex.data.admin.ch", "https://www.fedlex.admin.ch")
    return f"{base}/{applicability:%Y%m%d}/{lang}"


def _mark_split_paragraphs(docs: list[ParsedDocument]) -> list[ParsedDocument]:
    """Chunks must split identically in every language version of the same SR number and status:
    an align_key whose article text exceeds chunker.MAX_CHARS in ANY language version gets
    `split_paragraphs=True` in every language version, not just the one where it overflowed."""
    oversized_by_status: dict[str, set[str]] = {}
    for doc in docs:
        big = {s.align_key for s in doc.sections if len(s.text) > MAX_CHARS}
        oversized_by_status.setdefault(doc.status, set()).update(big)
    result: list[ParsedDocument] = []
    for doc in docs:
        oversized = oversized_by_status.get(doc.status, set())
        if not oversized:
            result.append(doc)
            continue
        new_sections = tuple(
            dataclasses.replace(s, split_paragraphs=True) if s.align_key in oversized else s
            for s in doc.sections)
        result.append(dataclasses.replace(doc, sections=new_sections))
    return result


class FedlexConnector:
    def __init__(self, http: httpx.Client, today: Callable[[], date], data_dir: Path | str,
                 sleep: Callable[[float], None] = time.sleep):
        self._http = http
        self._today = today
        self._data_dir = data_dir
        self._sleep = sleep

    def _with_retry[T](self, call: Callable[[], T]) -> T:
        for attempt in range(1, ATTEMPTS + 1):
            try:
                return call()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                transient = isinstance(exc, httpx.TransportError) or exc.response.status_code >= 500
                if attempt == ATTEMPTS or not transient:
                    raise
                self._sleep(attempt * 1.0)
        raise AssertionError("unreachable")

    def _rows(self, sr: str, lang: str) -> list[dict]:
        def call() -> list[dict]:
            response = self._http.post(
                ENDPOINT, data={"query": QUERY % {"sr": sr, "lang": LANGUAGE_URI[lang], "xml": XML_FORMAT_URI}},
                headers={"accept": "application/sparql-results+json"}, timeout=60)
            response.raise_for_status()
            return response.json()["results"]["bindings"]
        rows = []
        for b in self._with_retry(call):
            rows.append({
                "abstract": b["abstract"]["value"],
                "applicability": date.fromisoformat(b["dateApplicability"]["value"][:10]),
                "end": date.fromisoformat(b["dateEndApplicability"]["value"][:10]) if "dateEndApplicability" in b else None,
                "title": b.get("title", {}).get("value", ""),
                "file_url": b["fileUrl"]["value"],
            })
        return rows

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        documents, unchanged, errors = [], [], []
        today = self._today()
        for sr in spec.config["sr_numbers"]:
            sr_documents: list[ParsedDocument] = []
            for lang in spec.languages:
                if lang not in LANGUAGE_URI:
                    continue
                try:
                    rows = self._rows(sr, lang)
                except (httpx.HTTPError, KeyError, ValueError) as exc:
                    errors.append((f"SR {sr} [{lang}]", f"SR {sr} [{lang}] SPARQL failed: {exc}"))
                    continue
                if not rows:
                    if lang not in OPTIONAL_LANGUAGES:
                        errors.append((f"SR {sr} [{lang}]", f"SR {sr} [{lang}]: no in-force consolidation found"))
                    continue
                for row, status in zip(choose_consolidations(rows, today), ("current", "scheduled"), strict=True):
                    if row is None:
                        continue
                    url = _page_url(row["abstract"], row["applicability"], lang)
                    if url in known:
                        unchanged.append(url)
                        continue
                    try:
                        xml = self._with_retry(lambda u=row["file_url"]: self._fetch_xml(u))
                    except httpx.HTTPError as exc:
                        errors.append((url, f"XML download failed: {exc}"))
                        continue
                    title = row["title"] or f"SR {sr}"
                    sections = parse_akn(xml, act_title=title, sr=sr)
                    if not sections:
                        errors.append((url, "no articles parsed"))
                        continue
                    sr_documents.append(ParsedDocument(
                        source_id=spec.id, url=url, language=lang, work_key=row["abstract"], title=title,
                        sections=sections, identifier=f"SR {sr}", is_authentic=lang != "en",
                        valid_from=row["applicability"], valid_to=row["end"], status=status,
                        artifact_path=save_artifact(self._data_dir, spec.id, url, xml.encode(), ".xml")))
                self._sleep(0.5)
            documents.extend(_mark_split_paragraphs(sr_documents))
        return ConnectorResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))

    def _fetch_xml(self, url: str) -> str:
        response = self._http.get(url, follow_redirects=True, timeout=60)
        response.raise_for_status()
        return response.text
