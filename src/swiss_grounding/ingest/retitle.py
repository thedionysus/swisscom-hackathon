"""Repair stored Fedlex titles from the SPARQL endpoint, without re-crawling anything.

Five stored acts are titled `SR 455` and one carries no title at all. The query that would have
named them was fixed in Task 4, but no re-ingest reaches these rows: `fetchers/fedlex.py`
short-circuits on the URL alone before downloading, `persist` returns unchanged on a matching
content hash, and `hashing.content_hash` deliberately excludes titles from that hash. Three
independent blocks, any one of them sufficient. So the repair is a command of its own.

It is a different operation from `recontext` with a different failure mode -- it talks to an
upstream endpoint and buys one translation per act, where `recontext` reads only stored text and
buys a call per chunk -- and it has to run first, because `recontext` writes the document's title
into every chunk it describes. `recontext` refuses an untitled document rather than trusting the
ordering (see `recontext._untitled`).

The SPARQL query is free and read-only; the five translations are the only cost. Like `recontext`
this module commits per document, so an interrupted run keeps the titles it has already repaired
and a resumed run asks no model about them again -- a title that already matches the endpoint is
skipped.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import psycopg

from swiss_grounding.ingest.fetchers.fedlex import DEFAULT_LANGUAGE, sr_label
from swiss_grounding.ingest.llm import LLM
from swiss_grounding.ingest.models import FetchError
from swiss_grounding.registry.models import FetchStrategy

log = logging.getLogger(__name__)

SELECT_DOCUMENTS = """
select d.id, d.url, d.identifier, d.title_original, d.title_en, s.id as source_id, s.fetch_config
from document d join source s on s.id = d.source_id
where d.status = 'current' and s.fetch_strategy = %s
order by d.id
"""
UPDATE_TITLE = "update document set title_original = %s, title_en = %s where id = %s"
# The endpoint answers an empty set both for an outage and for a law with no current
# consolidation, exactly as `FedlexFetcher.fetch` says; neither is something to write a title from.
NO_CONSOLIDATION = "empty SPARQL result: an upstream outage, or no current consolidation"
NO_TITLE = "the endpoint named no title for this act, and a title is not worth guessing"
UNLISTED = "identifier %r is not one of the SR numbers its source lists; left alone"


class ConsolidationSource(Protocol):
    """Whatever can answer "what is the current consolidation of this SR number?".

    Narrower than the fetcher that implements it, because this command wants one binding and not
    a crawl: no document is downloaded here, and nothing is parsed out of Akoma Ntoso.
    """

    def current_consolidation(self, sr: str, lang: str) -> Mapping[str, Any] | None: ...


@dataclass(frozen=True)
class TitleChange:
    """One act's title before and after, so an operator can read what the run actually did."""

    identifier: str
    before: str
    after: str


@dataclass(frozen=True)
class RetitleReport:
    """What the repair touched: the titles rewritten, and the acts it could not rewrite."""

    examined: int
    changes: tuple[TitleChange, ...] = ()
    skipped: int = 0
    failed: int = 0
    errors: tuple[FetchError, ...] = ()

    @property
    def updated(self) -> int:
        return len(self.changes)


def _sr_number(document: Mapping[str, Any]) -> str | None:
    """The SR number this stored document stands for, or None if its source no longer lists it.

    The stored `identifier` is what `fedlex.sr_label` wrote, so the registry's own list of SR
    numbers is what turns it back into one. Reading the number out of the identifier's text
    instead would accept an SR number the source has since dropped, and re-title a document from
    a law we no longer track.
    """
    listed = {sr_label(sr): sr for sr in document["fetch_config"].get("sr_numbers", ())}
    return listed.get((document["identifier"] or "").strip())


def _endpoint_title(binding: Mapping[str, Any] | None) -> str:
    """The act's own name as the endpoint gives it. Raises when it gives none."""
    if binding is None:
        raise ValueError(NO_CONSOLIDATION)
    node = binding.get("title")
    title = (node or {}).get("value", "").strip()
    if not title:
        raise ValueError(NO_TITLE)
    return title


def _needs_repair(document: Mapping[str, Any], title: str) -> bool:
    """Whether this document's stored titles still differ from what the endpoint says.

    Both columns are checked, not just the original: one stored act has a `title_en` of `''`, and
    a run that compared the original alone would call it repaired and leave the English blank --
    which is the column `recontext` and every citation actually read.
    """
    return document["title_original"] != title or not document["title_en"].strip()


def _repair(conn: psycopg.Connection, document: Mapping[str, Any], title: str, language: str,
            llm: LLM) -> TitleChange:
    """Translate the act's name and store both titles. Committed on its own, like `recontext`."""
    title_en = llm.translate(title, language)
    conn.execute(UPDATE_TITLE, (title, title_en, document["id"]))
    conn.commit()
    return TitleChange(identifier=document["identifier"], before=document["title_original"],
                       after=title)


def _retitle_document(conn: psycopg.Connection, document: Mapping[str, Any], sr: str,
                      language: str, consolidations: ConsolidationSource,
                      llm: LLM, dry_run: bool) -> TitleChange | None:
    """One act: ask the endpoint, and rewrite the stored titles unless they already match."""
    title = _endpoint_title(consolidations.current_consolidation(sr, language))
    if not _needs_repair(document, title):
        return None
    if dry_run:
        return TitleChange(identifier=document["identifier"], before=document["title_original"],
                           after=title)
    return _repair(conn, document, title, language, llm)


def retitle_all(conn: psycopg.Connection, consolidations: ConsolidationSource, llm: LLM,
                dry_run: bool = False) -> RetitleReport:
    """Re-query the endpoint for every stored Fedlex act and rewrite the titles that are wrong.

    One SPARQL query per act, free, and one translation per act whose title actually changes. With
    `dry_run=True` the endpoint is still asked -- that is how the run knows what it would change,
    and it costs nothing -- but nothing is translated and nothing is written.

    A failure is per act: an outage on one law, or a translation that cannot be bought, leaves the
    acts already repaired repaired.
    """
    documents = conn.execute(SELECT_DOCUMENTS, (FetchStrategy.FEDLEX_SPARQL.value,)).fetchall()
    changes: list[TitleChange] = []
    errors: list[FetchError] = []
    skipped = 0
    for document in documents:
        sr = _sr_number(document)
        if sr is None:
            log.info(UNLISTED, document["identifier"])
            skipped += 1
            continue
        language = document["fetch_config"].get("language", DEFAULT_LANGUAGE)
        try:
            change = _retitle_document(conn, document, sr, language, consolidations, llm, dry_run)
        except Exception as exc:
            conn.rollback()
            log.exception("retitle failed sr=%s url=%s", sr, document["url"])
            errors.append(FetchError(url=document["url"], reason=f"SR {sr}: {exc}"))
            continue
        if change is None:
            skipped += 1
        else:
            changes.append(change)
    return _report(documents, changes, skipped, errors)


def _report(documents: Sequence[Mapping[str, Any]], changes: Sequence[TitleChange], skipped: int,
            errors: Sequence[FetchError]) -> RetitleReport:
    return RetitleReport(examined=len(documents), changes=tuple(changes), skipped=skipped,
                         failed=len(errors), errors=tuple(errors))
