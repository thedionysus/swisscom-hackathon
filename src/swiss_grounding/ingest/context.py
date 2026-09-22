"""Generated per-chunk context and per-chunk topics (ADR 0005, ADR 0003).

A stored chunk says nothing about what it belongs to: the article setting penalties for
mistreating animals reads, in the index, as a bare sentence about penalties. This step gives
each chunk a short generated description of what its document is about and what the chunk
itself covers, decides the chunk's own topics, and drops the chunk when it is page furniture.

`context_en` is indexed and never cited. The guard on that is one-directional and lives
downstream: `persist` embeds `indexed_text(...)` while writing `text_en` and `text_original`
unchanged, and `retrieval/cite.py` builds a snippet from those two columns alone. Nothing here
may ever fold context into `text_en`; the chunk text a citation quotes is passed through
untouched, which is why `describe_chunks` returns copies rather than rebuilt chunks.

This sits between chunking and persistence because context is per chunk -- it needs text that
only exists once a document has been split -- while the document summary it quotes is per
document. `enrich` runs before chunking and has no chunks to describe; chunking is a pure text
split with no model calls in it, and putting a paid call there would make it untestable as one.
"""

from collections.abc import Sequence
from dataclasses import replace

from swiss_grounding.ingest.boilerplate import is_boilerplate
from swiss_grounding.ingest.llm import LLM
from swiss_grounding.ingest.models import CategoryTag, ChunkDraft
from swiss_grounding.registry.categories import Category
from swiss_grounding.registry.models import Source

# Written only when the model named no topic for this chunk; a fallback, not a certainty.
SOURCE_FALLBACK_CONFIDENCE = 0.5
# One space, so the last word of the context cannot fuse with the first word of the text.
# `db/schema.sql` joins the same two columns the same way for `tsv`; the two must agree.
CONTEXT_SEPARATOR = " "
# A templated record already describes itself, so its context restates only what it belongs to.
TEMPLATED_CONTEXT = "From {source_name}. {title_en}"


def indexed_text(context_en: str, text_en: str) -> str:
    """What retrieval sees for a chunk: its generated context ahead of its own text.

    Kept in one place because two indexes read it -- the embedding, built here, and the `tsv`
    generated column, built by `db/schema.sql` from the same two columns with the same separator.
    An empty context contributes nothing, not a leading separator, so a chunk described by
    nothing indexes exactly as it did before ADR 0005.
    """
    return CONTEXT_SEPARATOR.join(part for part in (context_en, text_en) if part)


def merge_topics(defaults: Sequence[str], model_topics: Sequence[CategoryTag]) -> tuple[CategoryTag, ...]:
    """The model's per-chunk judgement always wins. A source's declared categories are used only
    as a fallback, when the model named nothing for this chunk at all -- and then at a confidence
    below certainty, because a source-level default is not a per-chunk assertion (ADR 0003)."""
    topics = {t.id: t for t in model_topics}
    if not topics:
        topics = {cid: CategoryTag(id=cid, confidence=SOURCE_FALLBACK_CONFIDENCE) for cid in defaults}
    return _sorted(topics.values())


def document_topics(chunks: Sequence[ChunkDraft]) -> tuple[CategoryTag, ...]:
    """What a document asserts: the union of its chunks' topics, each at its strongest confidence.

    Derived rather than decided, so `document.categories` cannot disagree with the chunks under
    it. ADR 0003 moved the judgement to the chunk; this is the roll-up, and it costs no call.
    """
    strongest: dict[str, CategoryTag] = {}
    for chunk in chunks:
        for topic in chunk.topics:
            if topic.confidence > strongest.get(topic.id, CategoryTag(topic.id, -1.0)).confidence:
                strongest[topic.id] = topic
    return _sorted(strongest.values())


def _sorted(topics) -> tuple[CategoryTag, ...]:
    return tuple(sorted(topics, key=lambda t: (-t.confidence, t.id)))


def _from_template(chunk: ChunkDraft, source: Source, title_en: str) -> ChunkDraft:
    """Context for a source whose records are rendered from a template and describe themselves.

    `open_erz` renders "Waste collection cardboard in 8003 on 2026-09-25" as both the title and
    the text of a one-section document; a model asked what it is about could only restate it.
    Eighty-nine of the corpus's chunks come this way, and paying for them is pure waste.
    """
    return replace(
        chunk,
        context_en=TEMPLATED_CONTEXT.format(source_name=source.name, title_en=title_en),
        topics=merge_topics(source.categories, ()),
    )


def describe_chunks(
    chunks: Sequence[ChunkDraft],
    *,
    source: Source,
    title_en: str,
    document_text_en: str,
    llm: LLM,
    categories: Sequence[Category],
) -> tuple[ChunkDraft, ...]:
    """Give every chunk its context and its topics; drop the chunks that are page furniture.

    One summary call per document and one description call per chunk. The summary exists to make
    the per-chunk call affordable: without it each chunk's prompt would have to carry a document
    excerpt of its own, and a hundred-article act would pay for that excerpt a hundred times.

    Page furniture is dropped in two stages, cheapest first. The heading rules of Task 1 name two
    headings that are furniture beyond argument, and a chunk carrying one is dropped before any
    call is made -- the model could only agree, and asking costs a call per navigation menu. The
    model's verdict is the general one, covering everything the heading rules cannot see. It
    supersedes the heuristic in reach, not in authority over those two headings.

    A document left with no chunks is returned empty, which `persist` records as skipped. That is
    the intended outcome for a page that is entirely furniture, not a failure to retry.
    """
    kept = tuple(c for c in chunks if not is_boilerplate(c.heading_path, c.text_en))
    if not kept:
        return ()
    if not source.llm_tagging:
        return tuple(_from_template(c, source, title_en) for c in kept)
    summary = llm.summarise(title_en, document_text_en)
    described = []
    for chunk in kept:
        context = llm.describe(summary_en=summary, heading_path=chunk.heading_path,
                               text_en=chunk.text_en, text_original=chunk.text_original,
                               categories=categories)
        if context.boilerplate:
            continue
        described.append(replace(chunk, context_en=context.context_en,
                                 topics=merge_topics(source.categories, context.topics)))
    return tuple(described)
