"""Fedlex SPARQL connector: every manifest language, current and scheduled consolidations."""
import dataclasses
import logging
import time
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

import httpx
from protego import Protego

from swiss_grounding.corpus.artifacts import save_artifact
from swiss_grounding.corpus.chunker import MAX_CHARS
from swiss_grounding.corpus.connectors.fedlex_akn import parse_akn
from swiss_grounding.corpus.connectors.html import ROBOTS_USER_AGENT, load_robots
from swiss_grounding.corpus.models import ConnectorResult, KnownState, ParsedDocument, SourceSpec

log = logging.getLogger(__name__)

ENDPOINT = "https://fedlex.data.admin.ch/sparqlendpoint"
LANGUAGE_URI = {
    "de": "http://publications.europa.eu/resource/authority/language/DEU",
    "fr": "http://publications.europa.eu/resource/authority/language/FRA",
    "it": "http://publications.europa.eu/resource/authority/language/ITA",
    "en": "http://publications.europa.eu/resource/authority/language/ENG",
}
XML_FORMAT_URI = "http://publications.europa.eu/resource/authority/file-type/XML"
OPTIONAL_LANGUAGES = frozenset({"en"})   # English exists for ~290 acts only; its absence is not an error
# `%(today)s` is filled with an xsd:date literal from the injected clock rather than SPARQL `now()`,
# so a fixed `today` (as used in tests, and for reproducible re-runs) is what decides "in force".
QUERY = """
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
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
  %(end_filter)s
}
"""
# Only rows still in force as of `today`; omitted entirely for the optional-language fallback
# query, which needs every consolidation ever published, ended or not.
IN_FORCE_FILTER = 'FILTER(!bound(?dateEndApplicability) || ?dateEndApplicability >= "%(today)s"^^xsd:date)'
ATTEMPTS = 3
# SPARQL returns file URLs under fedlex.data.admin.ch/filestore/, which that host's robots.txt
# disallows for every crawler. www.fedlex.admin.ch serves the same files (byte-identical, checked
# 2026-09-24 on SR 704 and SR 741.21) and its robots.txt allows /filestore/. Downloads use that host;
# the document's identity is its page URL (`_page_url`), so it does not change.
DATA_FILESTORE = "https://fedlex.data.admin.ch/filestore/"
WWW_FILESTORE = "https://www.fedlex.admin.ch/filestore/"


class RobotsDisallowed(Exception):
    """The act file's host forbids fetching it in robots.txt; reported as an error, never fetched."""


def download_url(file_url: str) -> str:
    """Where an act file is fetched from: the robots-allowed www host for filestore URLs."""
    if file_url.startswith(DATA_FILESTORE):
        return WWW_FILESTORE + file_url[len(DATA_FILESTORE):]
    return file_url


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
                 sleep: Callable[[float], None] = time.sleep, respect_robots: bool = True):
        self._http = http
        self._today = today
        self._data_dir = data_dir
        self._sleep = sleep
        self._respect_robots = respect_robots
        self._robots: dict[str, Protego] = {}

    def _with_retry[T](self, call: Callable[[], T]) -> T:
        for attempt in range(1, ATTEMPTS + 1):
            try:
                return call()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                transient = isinstance(exc, httpx.TransportError) or (
                    exc.response.status_code >= 500 or exc.response.status_code == 429)
                if attempt == ATTEMPTS or not transient:
                    raise
                self._sleep(attempt * 1.0)
        raise AssertionError("unreachable")

    def _rows(self, sr: str, lang: str, today: date, *, in_force_only: bool) -> list[dict]:
        end_filter = IN_FORCE_FILTER % {"today": today.isoformat()} if in_force_only else ""

        def call() -> list[dict]:
            response = self._http.post(
                ENDPOINT, data={"query": QUERY % {"sr": sr, "lang": LANGUAGE_URI[lang], "xml": XML_FORMAT_URI,
                                                   "end_filter": end_filter}},
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

    def probe(self, sr: str, lang: str) -> int:
        """Number of in-force consolidations of one SR number in one language (check-manifest)."""
        return len(self._rows(sr, lang, self._today(), in_force_only=True))

    def _rows_for_language(self, sr: str, lang: str, today: date) -> dict[str, dict]:
        """{status: row} for one SR/language: in-force consolidations first; for an OPTIONAL
        language with none in force, fall back to its newest consolidation regardless of end
        date, reported as `current` (English translations can lag the in-force text)."""
        rows = self._rows(sr, lang, today, in_force_only=True)
        if rows:
            current, scheduled = choose_consolidations(rows, today)
            statuses = {}
            if current is not None:
                statuses["current"] = current
            if scheduled is not None:
                statuses["scheduled"] = scheduled
            return statuses
        if lang not in OPTIONAL_LANGUAGES:
            return {}
        any_rows = self._rows(sr, lang, today, in_force_only=False)
        if not any_rows:
            return {}
        newest = max(any_rows, key=lambda r: r["applicability"])
        log.info("SR %s [%s]: no in-force consolidation; using newest available consolidation "
                 "(%s, ended %s)", sr, lang, newest["applicability"], newest["end"])
        return {"current": newest}

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        documents, unchanged, errors = [], [], []
        today = self._today()
        for sr in spec.config["sr_numbers"]:
            by_lang: dict[str, dict[str, dict]] = {}
            for lang in spec.languages:
                if lang not in LANGUAGE_URI:
                    continue
                try:
                    statuses = self._rows_for_language(sr, lang, today)
                except (httpx.HTTPError, KeyError, ValueError) as exc:
                    errors.append((f"SR {sr} [{lang}]", f"SR {sr} [{lang}] SPARQL failed: {exc}"))
                    continue
                if not statuses and lang not in OPTIONAL_LANGUAGES:
                    errors.append((f"SR {sr} [{lang}]", f"SR {sr} [{lang}]: no in-force consolidation found"))
                    continue
                if statuses:
                    by_lang[lang] = statuses
                self._sleep(0.5)

            statuses_present = {status for per_lang in by_lang.values() for status in per_lang}
            sr_documents: list[ParsedDocument] = []
            for status in statuses_present:
                group = [(lang, per_lang[status]) for lang, per_lang in by_lang.items() if status in per_lang]
                urls = {lang: _page_url(row["abstract"], row["applicability"], lang) for lang, row in group}
                if group and all(url in known for url in urls.values()):
                    # Every language version of this SR+status is unchanged: skip the whole group.
                    unchanged.extend(urls.values())
                    continue
                # At least one language version is new: re-download every language version of this
                # SR+status (even the "known" ones), so split-paragraph alignment
                # always sees every language, not just the ones that changed upstream this run.
                for lang, row in group:
                    url = urls[lang]
                    try:
                        xml = self._with_retry(lambda u=row["file_url"]: self._fetch_xml(u))
                        title = row["title"] or f"SR {sr}"
                        sections = parse_akn(xml, act_title=title, sr=sr)
                        if not sections:
                            raise ValueError("no articles parsed")
                        artifact_path = save_artifact(self._data_dir, spec.id, url, xml.encode(), ".xml")
                    except Exception as exc:  # noqa: BLE001 - one bad URL must not abort the rest of the run
                        errors.append((url, f"{type(exc).__name__}: {exc}"))
                        continue
                    sr_documents.append(ParsedDocument(
                        source_id=spec.id, url=url, language=lang, work_key=row["abstract"], title=title,
                        sections=sections, identifier=f"SR {sr}", is_authentic=lang != "en",
                        valid_from=row["applicability"], valid_to=row["end"], status=status,
                        artifact_path=artifact_path))
            documents.extend(_mark_split_paragraphs(sr_documents))
        return ConnectorResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))

    def _robots_allow(self, url: str) -> bool:
        if not self._respect_robots:
            return True
        parts = httpx.URL(url)
        root = f"{parts.scheme}://{parts.host}"
        if root not in self._robots:
            self._robots[root], _problem = load_robots(self._http, root)
        return self._robots[root].can_fetch(url, ROBOTS_USER_AGENT)

    def _fetch_xml(self, file_url: str) -> str:
        url = download_url(file_url)
        if not self._robots_allow(url):
            raise RobotsDisallowed(f"{url} disallowed by robots.txt")
        response = self._http.get(url, follow_redirects=True, timeout=60)
        response.raise_for_status()
        return response.text
