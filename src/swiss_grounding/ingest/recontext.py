"""Re-enrich stored chunks from text already in the database (ADR 0005, ADR 0003).

A sibling of `reclean` and `renarrow`: it reads the English text already stored, so it never
re-fetches and never re-translates, which is what makes the redesign affordable while translation
credits are unavailable. What it does spend is one description call per chunk and one summary call
per document -- the same calls ingestion makes, made by `context.describe_chunks` itself, so every
rule about what a description is stays in one place.

**This module commits.** It is not composable inside a caller's transaction, and that is the
point. Issue #13 is a long run that committed only at the end and lost everything; the exposure
here is larger, because a Fedlex act is around 112 paid calls. Every call is committed as it is
made, so an interrupted run keeps what it paid for and a resumed run starts where it stopped.

The resumed run knows what is already done from the chunk itself: a chunk whose `context_en` is
empty has not been described. That signal is sound in both directions -- `llm.parse_description`
refuses a kept chunk with no context, and a templated source's context is never empty either --
so nothing that was described reads as pending, and nothing pending reads as described. `--force`
exists for redoing work deliberately, and is the only way to re-describe a chunk that already has
a context.

Nothing here erases a document unless it is asked to. The model drops page furniture, and a page
that is furniture from top to bottom ends with no chunks at all; such a document is reported and
left standing, because the deletion is irreversible, a dry run cannot preview it, and three stored
documents hold a single chunk each. `--delete-emptied` is for an operator who has read the list.
See `_finish`.
"""

import json
import logging
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, fields, replace
from functools import cache
from itertools import groupby
from typing import Any

import psycopg

from swiss_grounding.ingest.context import (
    SOURCE_FALLBACK_CONFIDENCE,
    describe_chunks,
    document_topics,
    indexed_text,
)
from swiss_grounding.ingest.enrich import SECTION_SEPARATOR
from swiss_grounding.ingest.llm import LLM
from swiss_grounding.ingest.models import CategoryTag, ChunkContext, ChunkDraft, FetchError
from swiss_grounding.ingest.reclean import delete_documents
from swiss_grounding.registry.categories import CATEGORIES, Category
from swiss_grounding.registry.models import Source
from swiss_grounding.registry.repository import load_sources
from swiss_grounding.retrieval.embedder import Embedder

log = logging.getLogger(__name__)

SELECT_CHUNKS = """
select c.id, c.document_id, c.ordinal, c.heading_path, c.anchor, c.text_original, c.text_en,
       c.context_en, d.source_id, d.url, d.title_original, d.title_en, d.identifier
from chunk c join document d on d.id = c.document_id
where d.status = 'current'
order by c.document_id, c.ordinal
"""
UPDATE_CHUNK = "update chunk set context_en = %s, categories = %s, embedding = %s where id = %s"
DELETE_CHUNK = "delete from chunk where id = %s"
UPDATE_DOCUMENT_TOPICS = "update document set categories = %s::jsonb where id = %s"
SELECT_TOPIC_IDS = "select distinct unnest(categories) as topic from chunk where document_id = %s"
# What a topic carried by a chunk this run did not describe is rolled up at: the chunk asserts the
# topic, and the confidence the model gave it was dropped when the chunk was stored. The same value
# `context.SOURCE_FALLBACK_CONFIDENCE` uses, and for the same reason -- it applies, but nothing here
# asserts it at full strength.
RECOVERED_CONFIDENCE = SOURCE_FALLBACK_CONFIDENCE
# Refused rather than described: see `_untitled`. The message names the repair, because the
# operator reading it has one command to run before this one can work.
UNTITLED = ("the document is titled {title!r}, which names nothing; run `retitle` to repair the "
            "stored title before backfilling its chunks")


@dataclass(frozen=True)
class SourceRecontext:
    """What the backfill did to one source's chunks.

    Every count is in chunks except `deleted_documents`, and the chunk counts account for the
    whole of `examined`: each chunk was updated, skipped as already done, deleted as furniture,
    or left alone because its document failed. The two call counts are the bill.
    """

    source_id: str
    examined: int = 0
    updated: int = 0
    skipped: int = 0
    deleted_chunks: int = 0
    deleted_documents: int = 0
    emptied_documents: int = 0
    failed: int = 0
    describe_calls: int = 0
    summary_calls: int = 0

    def plus(self, other: "SourceRecontext") -> "SourceRecontext":
        """This source's running total with one more document's counts folded in."""
        if other.source_id != self.source_id:
            raise ValueError(f"cannot add {other.source_id!r} counts to {self.source_id!r}")
        return replace(self, **{f.name: getattr(self, f.name) + getattr(other, f.name)
                                for f in fields(self) if f.name != "source_id"})


@dataclass(frozen=True)
class EmptiedDocument:
    """A document the model left with no chunks at all."""

    document_id: int
    source_id: str
    url: str


@dataclass(frozen=True)
class RecontextReport:
    """The full backfill result: the drops and writes per source, and what failed."""

    by_source: tuple[SourceRecontext, ...]
    errors: tuple[FetchError, ...] = ()
    emptied: tuple[EmptiedDocument, ...] = ()

    def _total(self, field: str) -> int:
        return sum(getattr(s, field) for s in self.by_source)

    @property
    def examined(self) -> int:
        return self._total("examined")

    @property
    def updated(self) -> int:
        return self._total("updated")

    @property
    def skipped(self) -> int:
        return self._total("skipped")

    @property
    def deleted_chunks(self) -> int:
        return self._total("deleted_chunks")

    @property
    def deleted_documents(self) -> int:
        return self._total("deleted_documents")

    @property
    def emptied_documents(self) -> int:
        return self._total("emptied_documents")

    @property
    def failed(self) -> int:
        return self._total("failed")

    @property
    def describe_calls(self) -> int:
        return self._total("describe_calls")

    @property
    def summary_calls(self) -> int:
        return self._total("summary_calls")


@dataclass(frozen=True)
class _Options:
    """How one run behaves: what it redoes, what it spends, and what it may erase."""

    dry_run: bool = False
    force: bool = False
    delete_emptied: bool = False


@dataclass(frozen=True)
class _DocumentOutcome:
    """What became of one document: its counts, why it failed, and whether it ended with nothing."""

    counts: SourceRecontext
    error: FetchError | None = None
    emptied: EmptiedDocument | None = None


class _DocumentModel:
    """The run's model as one document sees it: its summary bought once, and its calls counted.

    `describe_chunks` is called here one chunk at a time, so that each paid call can be committed
    as it is made, and it asks for the document's summary every time it is called. Left alone that
    would buy a summary per chunk instead of a summary per document: 630 calls of pure waste on
    the backfill. Only `summarise` is memoised, and only for the life of one document; everything
    else is the model itself, untouched.

    The two counters are what the report bills, and they count what was actually sent rather than
    what was planned -- a templated source reaches neither call, because `describe_chunks` answers
    it from its own template, and a description the client had to resample
    (`llm.DESCRIBE_ATTEMPTS`) cost two messages, not one. Resamples are read off the client's own
    `messages_sent`, because they happen inside a single `describe`; a stand-in that keeps no such
    count is billed one message per description, which is what it made.
    """

    def __init__(self, llm: LLM):
        self._llm = llm
        self._summarise = cache(llm.summarise)
        self._describes = 0

    @property
    def summary_calls(self) -> int:
        return self._summarise.cache_info().misses

    @property
    def describe_calls(self) -> int:
        return self._describes

    def translate(self, text: str, source_language: str) -> str:
        return self._llm.translate(text, source_language)

    def summarise(self, title_en: str, text_en: str) -> str:
        return self._summarise(title_en, text_en)

    def describe(self, summary_en: str, heading_path: str, text_en: str, text_original: str | None,
                 categories: Sequence[Category]) -> ChunkContext:
        before = self._messages_sent()
        try:
            return self._llm.describe(summary_en, heading_path, text_en, text_original, categories)
        finally:
            self._describes += max(1, self._messages_sent() - before)

    def _messages_sent(self) -> int:
        """What the client says it has put on the wire, or 0 where it keeps no count."""
        return getattr(self._llm, "messages_sent", 0)


@dataclass(frozen=True)
class _StoredChunk:
    """A chunk as it sits in the database: its id, and the draft `describe_chunks` reads."""

    id: int
    draft: ChunkDraft


@dataclass(frozen=True)
class _StoredDocument:
    """One current document and all of its stored chunks, in ordinal order."""

    id: int
    source_id: str
    url: str
    title_original: str
    title_en: str
    identifier: str | None
    chunks: tuple[_StoredChunk, ...]

    @property
    def text_en(self) -> str:
        """The document's English text in one string, for the one summary call its chunks share."""
        return SECTION_SEPARATOR.join(c.draft.text_en for c in self.chunks)


def _drafts(rows: Sequence[dict[str, Any]]) -> tuple[_StoredChunk, ...]:
    """The stored rows of one document as drafts, reconstructing `original_is_parallel`.

    The flag is not a column: `chunking.chunk_sections` attaches the whole section's original to
    every piece of a section it split, and marks those pieces as carrying an original that is not
    their own. What the pieces leave behind in the database is an identical `text_original` on
    more than one chunk, which is exactly how they are found again. Two genuinely distinct
    sections that happen to hold the same original text are read the same way, and are then
    described from their English alone -- the conservative reading, and the one that cannot put a
    chunk beside a passage it does not correspond to (see ADR 0005 and `ChunkDraft`).
    """
    repeated = {text for text, count in Counter(r["text_original"] for r in rows).items() if count > 1}
    return tuple(
        _StoredChunk(id=row["id"], draft=ChunkDraft(
            ordinal=row["ordinal"], heading_path=row["heading_path"], anchor=row["anchor"],
            text_original=row["text_original"], text_en=row["text_en"],
            original_is_parallel=row["text_original"] not in repeated,
            context_en=row["context_en"],
        ))
        for row in rows
    )


def _documents(conn: psycopg.Connection) -> Iterator[_StoredDocument]:
    """Every current document with its chunks, read once and grouped in ordinal order."""
    rows = conn.execute(SELECT_CHUNKS).fetchall()
    for document_id, group in groupby(rows, key=lambda r: r["document_id"]):
        chunk_rows = list(group)
        first = chunk_rows[0]
        yield _StoredDocument(
            id=document_id, source_id=first["source_id"], url=first["url"],
            title_original=first["title_original"], title_en=first["title_en"],
            identifier=first["identifier"],
            chunks=_drafts(chunk_rows),
        )


def _write(conn: psycopg.Connection, stored: _StoredChunk, described: ChunkDraft | None,
           embedder: Embedder) -> None:
    """Store one described chunk, or delete it when the model judged it page furniture.

    Committed immediately: the call that produced it has been paid for, and a chunk's new context
    and topics stand on their own -- nothing in the document binds them to the chunks around it.
    """
    if described is None:
        conn.execute(DELETE_CHUNK, (stored.id,))
    else:
        vector = embedder.embed([indexed_text(described.context_en, described.text_en)])[0]
        conn.execute(UPDATE_CHUNK, (described.context_en, [t.id for t in described.topics],
                                    vector, stored.id))
    conn.commit()


def _describe(stored: _StoredChunk, document: _StoredDocument, document_text_en: str,
              source: Source, llm: LLM) -> ChunkDraft | None:
    """One chunk through `describe_chunks`; None when it came back as furniture.

    `document_text_en` is passed in rather than read off the document, because it is the whole
    act joined into one string and this runs once per chunk: a hundred-article act would otherwise
    rebuild a hundred-article string a hundred times, for a summary bought once.
    """
    described = describe_chunks(
        (stored.draft,), source=source, title_en=document.title_en,
        document_text_en=document_text_en, llm=llm, categories=CATEGORIES,
    )
    return described.kept[0] if described.kept else None


def _roll_up(conn: psycopg.Connection, document: _StoredDocument,
             kept: Sequence[ChunkDraft]) -> None:
    """Rewrite the document's topics as the roll-up of every chunk it still has.

    ADR 0003 makes a document's categories derived, never decided, so leaving the old union of
    five behind would let the document disagree with every chunk under it. This runs whenever the
    document ends the run fully described -- by this run or by an earlier one that got part of the
    way -- and reads the ids back from the chunks themselves, so a document finished by a resumed
    run is repaired rather than left stale forever.

    A chunk described earlier in another run contributes an id but no confidence: `chunk.categories`
    keeps ids alone, by design, so the number the model gave it is gone. Such an id is rolled up at
    `RECOVERED_CONFIDENCE` rather than invented at full strength. Nothing reads these confidences as
    a constraint -- the hard filter of ADR 0003 is `chunk.categories` -- and a `--force` run, which
    describes every chunk again, restores the real numbers.
    """
    described = {t.id: t for t in document_topics(kept)}
    stored_ids = [row["topic"] for row in conn.execute(SELECT_TOPIC_IDS, (document.id,)).fetchall()]
    topics = sorted((described.get(topic_id, CategoryTag(topic_id, RECOVERED_CONFIDENCE))
                     for topic_id in stored_ids), key=lambda t: (-t.confidence, t.id))
    conn.execute(UPDATE_DOCUMENT_TOPICS,
                 (json.dumps([{"id": t.id, "confidence": t.confidence} for t in topics]), document.id))
    conn.commit()


def _untitled(document: _StoredDocument) -> bool:
    """Whether the document's stored title says anything about the document at all.

    A blank title names nothing, and neither does a title that is only the document's own
    identifier: five stored Fedlex acts are titled `SR 455` and one is titled with an empty
    string, because the SPARQL title binding never bound until Task 4 fixed the query, and no
    re-ingest repairs a stored title (`persist` compares a content hash that excludes it).

    Every chunk's context quotes that title -- directly for a templated source, through the
    document summary for every other -- so backfilling an act called `SR 455` would write it into
    all 563 of its chunks and degrade every one of them. The document is refused instead, which
    costs nothing and says what to run first.

    Both stored titles are compared against the identifier, because `title_en` is a *translation*
    of `SR 455` and a model asked to translate a bare reference may hand back anything; the
    original is what the fetcher actually wrote. A document that carries no identifier cannot be
    named by one, so only a blank title refuses it.
    """
    title_en = document.title_en.strip()
    identifier = (document.identifier or "").strip()
    if not title_en:
        return True
    return bool(identifier) and identifier in (title_en, document.title_original.strip())


def _projected(counts: SourceRecontext, source: Source, pending: Sequence[_StoredChunk]) -> SourceRecontext:
    """What a run would cost and change, counted without asking the model anything.

    The two call counts mirror `context.describe_chunks`: one summary for the document and one
    description per chunk, or nothing at all where the source's records describe themselves. Every
    pending chunk is counted as an update, because which of them the model will call furniture is
    exactly what a dry run cannot know without paying to find out.
    """
    if not source.llm_tagging:
        return replace(counts, updated=len(pending))
    return replace(counts, updated=len(pending), describe_calls=len(pending), summary_calls=1)


def _describe_pending(conn: psycopg.Connection, document: _StoredDocument, source: Source,
                      pending: Sequence[_StoredChunk], model: _DocumentModel, embedder: Embedder,
                      counts: SourceRecontext, options: "_Options") -> "_DocumentOutcome":
    """Describe and store one document's pending chunks, committing each as it is paid for.

    A chunk that fails stops the document and nothing else. Everything already written stays
    written: the paid artefact is one chunk -- a description and the topics of that chunk alone --
    and no invariant binds it to the chunks beside it, so discarding up to 195 paid calls (SR
    741.01, the largest stored act) would protect nothing. A resumed run picks up exactly where
    this one stopped, because the chunks that succeeded now carry a context and the ones that did
    not still carry none. `conn.rollback` is safe for the same reason: there is nothing
    uncommitted left to lose.
    """
    document_text_en = document.text_en
    kept: list[ChunkDraft] = []
    deleted = 0
    for done, stored in enumerate(pending):
        try:
            described = _describe(stored, document, document_text_en, source, model)
            _write(conn, stored, described, embedder)
        except Exception as exc:
            conn.rollback()
            log.exception("recontext failed source=%s url=%s chunk=%s",
                          source.id, document.url, stored.id)
            return _DocumentOutcome(
                counts=_counted(counts, model, updated=len(kept), deleted_chunks=deleted,
                                failed=len(pending) - done),
                error=FetchError(url=document.url, reason=str(exc)))
        if described is None:
            deleted += 1
        else:
            kept.append(described)
    return _finish(conn, document, kept, deleted, model, counts, options)


def _finish(conn: psycopg.Connection, document: _StoredDocument, kept: Sequence[ChunkDraft],
            deleted: int, model: _DocumentModel, counts: SourceRecontext,
            options: "_Options") -> "_DocumentOutcome":
    """Settle a document whose every chunk has now been described, in this run or an earlier one.

    A document the model left with no chunks at all is reported and, by default, left standing.
    Deleting it is irreversible -- the document row, and its `document_change` history with it --
    and it cannot be undone by re-crawling, because `recontext` does not clear `fetch_state`, so
    the URL is still remembered and the next crawl skips it. Which chunks the model will reject is
    exactly what a dry run cannot preview, three stored documents hold a single chunk each, and a
    verdict that is usually right is not a basis for an unrecoverable delete nobody saw coming.

    Leaving it has a cost, and it is the smaller one: `retrieval/coverage.py` counts documents, so
    a document with no chunks keeps reporting coverage it can no longer serve -- the
    silent under-coverage failure class of `CONTEXT.md`. That is a visible, reversible wrong
    number. `--delete-emptied` erases them once an operator has read the list and decided.
    """
    if len(document.chunks) - deleted > 0:
        _roll_up(conn, document, kept)
        return _DocumentOutcome(_counted(counts, model, updated=len(kept), deleted_chunks=deleted))
    if options.delete_emptied:
        delete_documents(conn, [document.id])
        conn.commit()
    return _DocumentOutcome(
        counts=_counted(counts, model, updated=len(kept), deleted_chunks=deleted,
                        deleted_documents=int(options.delete_emptied),
                        emptied_documents=int(not options.delete_emptied)),
        emptied=EmptiedDocument(document_id=document.id, source_id=document.source_id,
                                url=document.url),
    )


def _counted(counts: SourceRecontext, model: _DocumentModel, **outcome: int) -> SourceRecontext:
    """One document's counts: what became of its chunks, plus the calls the model was asked for."""
    return replace(counts, describe_calls=model.describe_calls,
                   summary_calls=model.summary_calls, **outcome)


def _recontext_document(conn: psycopg.Connection, document: _StoredDocument, source: Source,
                        llm: LLM, embedder: Embedder, options: "_Options") -> "_DocumentOutcome":
    """Decide what one document still needs, then describe it -- or only say what it would cost."""
    pending = [c for c in document.chunks if options.force or not c.draft.context_en.strip()]
    counts = SourceRecontext(source_id=source.id, examined=len(document.chunks),
                             skipped=len(document.chunks) - len(pending))
    if not pending:
        return _DocumentOutcome(counts)
    if _untitled(document):
        log.warning("refusing an untitled document source=%s url=%s", source.id, document.url)
        return _DocumentOutcome(
            counts=replace(counts, failed=len(pending)),
            error=FetchError(url=document.url, reason=UNTITLED.format(title=document.title_en)))
    if options.dry_run:
        return _DocumentOutcome(_projected(counts, source, pending))
    return _describe_pending(conn, document, source, pending, _DocumentModel(llm), embedder,
                             counts, options)


def _orphaned(document: _StoredDocument) -> "_DocumentOutcome":
    """A document whose source has since left the registry: skipped, not fatal, as `renarrow` does."""
    log.warning("no source %r for document %s; skipped", document.source_id, document.url)
    return _DocumentOutcome(SourceRecontext(source_id=document.source_id,
                                            examined=len(document.chunks),
                                            skipped=len(document.chunks)))


def recontext_all(conn: psycopg.Connection, llm: LLM, embedder: Embedder, dry_run: bool = False,
                  force: bool = False, delete_emptied: bool = False) -> RecontextReport:
    """Give every stored chunk a generated context and its own topics, and re-embed it.

    One document at a time, one chunk at a time, committed as it goes; see the module docstring
    for what that buys.

    With `dry_run=True` nothing is written and nothing is asked of the model: the report says what
    the run would touch and what it would cost, which is the number an operator needs before
    spending it. Its call count is a lower bound -- a description the model answers unusably is
    resampled once, and no projection can know which. With `force=True` a chunk that already
    carries a context is described again, which is the only way to redo work this command has
    already done. With `delete_emptied=True` a document the model left with no chunks is erased
    rather than reported; see `_finish` for why that is not the default.
    """
    options = _Options(dry_run=dry_run, force=force, delete_emptied=delete_emptied)
    sources = {s.id: s for s in load_sources(conn)}
    totals: dict[str, SourceRecontext] = {}
    errors: list[FetchError] = []
    emptied: list[EmptiedDocument] = []
    for document in _documents(conn):
        source = sources.get(document.source_id)
        outcome = (_recontext_document(conn, document, source, llm, embedder, options)
                   if source else _orphaned(document))
        source_id = outcome.counts.source_id
        totals[source_id] = totals.get(source_id, SourceRecontext(source_id=source_id)).plus(
            outcome.counts)
        if outcome.error:
            errors.append(outcome.error)
        if outcome.emptied:
            emptied.append(outcome.emptied)
    return RecontextReport(by_source=tuple(sorted(totals.values(), key=lambda s: s.source_id)),
                           errors=tuple(errors), emptied=tuple(emptied))
