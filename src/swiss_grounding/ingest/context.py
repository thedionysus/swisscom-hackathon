"""Generated per-chunk context and per-chunk topics.

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
from dataclasses import dataclass, replace

from swiss_grounding.ingest.boilerplate import is_boilerplate
from swiss_grounding.ingest.llm import LLM
from swiss_grounding.ingest.models import CategoryTag, ChunkDraft
from swiss_grounding.registry.categories import Category
from swiss_grounding.registry.models import Source

# Written only where `_fallback_applies` lets a source's declaration stand in for a chunk the
# model named nothing for; a fallback, not a certainty.
SOURCE_FALLBACK_CONFIDENCE = 0.5
# One space, so the last word of the context cannot fuse with the first word of the text.
# `db/schema.sql` joins the same two columns the same way for `tsv`. The two must agree, and
# `tests/integration/test_schema_context.py` is what makes them rather than merely asking.
CONTEXT_SEPARATOR = " "
# A templated record already describes itself, so its context restates only what it belongs to.
TEMPLATED_CONTEXT = "From {source_name}. {title_en}"


def indexed_text(context_en: str, text_en: str) -> str:
    """What retrieval sees for a chunk: its generated context ahead of its own text.

    Kept in one place because two indexes read it -- the embedding, built here, and the `tsv`
    generated column, built by `db/schema.sql` from the same two columns with the same separator.
    An empty context contributes nothing, not a leading separator, so a chunk described by
    nothing indexes on its text alone, exactly as it did before chunks had a context.
    """
    return CONTEXT_SEPARATOR.join(part for part in (context_en, text_en) if part)


def _fallback_applies(source: Source) -> bool:
    """Whether this source's declared categories may stand in for a chunk the model tagged with
    nothing.

    `source.categories` says what the source *covers*. Only a declaration of exactly one category
    also says anything about an individual chunk of it: `open_erz` declaring `waste` does tell you
    what every record of a waste calendar is about, while `fedlex` declaring five does not tell
    you that a definitions article is about all five. Writing all five onto a chunk the model
    named nothing for is the defect per-chunk topics exist to remove -- 563 chunks each asserting
    dogs, hiking, safety, transport and waste -- re-entered through the fallback, and at chunk
    granularity an empty answer is far commoner than it ever was per document, because a
    definitions article or a penalty clause genuinely has no topic.

    A templated source is the exception: there is no model judgement to defer to, so what it
    declares is the whole judgement, however many categories that is.
    """
    if not source.llm_tagging:
        return True
    return len(source.categories) == 1


def merge_topics(source: Source, model_topics: Sequence[CategoryTag]) -> tuple[CategoryTag, ...]:
    """The topics of one chunk: the model's judgement, or a constrained fallback, or nothing.

    The model's per-chunk judgement always wins. Where it named nothing, `source.categories` may
    stand in, but only under `_fallback_applies` and then below certainty, because a source-level
    default is not a per-chunk assertion.

    A chunk of a multi-category source that the model tagged with nothing therefore ends with no
    topics at all. Under the hard topic filter this is deliberate and accepted, not an oversight:
    such a chunk is unreachable, which is the honest outcome, and better than reaching it under
    topics that are false of it -- a false topic surfaces wrong evidence, while a missing one
    surfaces none. The topic filter should meet this as a decision rather than a surprise.
    """
    topics = {t.id: t for t in model_topics}
    if not topics and _fallback_applies(source):
        topics = {cid: CategoryTag(id=cid, confidence=SOURCE_FALLBACK_CONFIDENCE)
                  for cid in source.categories}
    return _sorted(topics.values())


def document_topics(chunks: Sequence[ChunkDraft]) -> tuple[CategoryTag, ...]:
    """What a document asserts: the union of its chunks' topics, each at its strongest confidence.

    Derived rather than decided, so `document.categories` cannot disagree with the chunks under
    it. The judgement is made per chunk; this is the roll-up, and it costs no call.
    """
    strongest: dict[str, CategoryTag] = {}
    for chunk in chunks:
        for topic in chunk.topics:
            if topic.confidence > strongest.get(topic.id, CategoryTag(topic.id, -1.0)).confidence:
                strongest[topic.id] = topic
    return _sorted(strongest.values())


def _sorted(topics) -> tuple[CategoryTag, ...]:
    return tuple(sorted(topics, key=lambda t: (-t.confidence, t.id)))


@dataclass(frozen=True)
class DescribedChunks:
    """What became of a document's chunks: the ones to store, and the ones judged page furniture.

    The dropped ones are returned rather than left to be inferred. `recontext` has to
    delete chunks already stored that are now judged furniture, and the only other way to find
    them is to notice which ordinals are missing from `kept` -- a contract written down nowhere
    and broken silently by anything that renumbers. Every chunk passed in comes back in exactly
    one of the two.
    """
    kept: tuple[ChunkDraft, ...]
    dropped: tuple[ChunkDraft, ...]


def _from_template(chunk: ChunkDraft, source: Source, title_en: str) -> ChunkDraft:
    """Context for a source whose records are rendered from a template and describe themselves.

    `open_erz` renders "Waste collection cardboard in 8003 on 2026-09-25" as both the title and
    the text of a one-section document; a model asked what it is about could only restate it.
    Eighty-nine of the corpus's chunks come this way, and paying for them is pure waste.
    """
    return replace(
        chunk,
        context_en=TEMPLATED_CONTEXT.format(source_name=source.name, title_en=title_en),
        topics=merge_topics(source, ()),
    )


def describe_chunks(
    chunks: Sequence[ChunkDraft],
    *,
    source: Source,
    title_en: str,
    document_text_en: str,
    llm: LLM,
    categories: Sequence[Category],
) -> DescribedChunks:
    """Give every chunk its context and its topics; drop the chunks that are page furniture.

    One summary call per document and one description call per chunk. The summary exists to make
    the per-chunk call affordable: without it each chunk's prompt would have to carry a document
    excerpt of its own, and a hundred-article act would pay for that excerpt a hundred times.

    Page furniture is dropped in two stages, cheapest first. The rules in `boilerplate` name two
    headings that are furniture beyond argument, and a chunk carrying one is dropped before any
    call is made -- the model could only agree, and asking costs a call per navigation menu. The
    model's verdict is the general one, covering everything the heading rules cannot see. It
    supersedes the heuristic in reach, not in authority over those two headings.

    A document left with nothing to keep is the intended outcome for a page that is entirely
    furniture, not a failure to retry; `persist` records it as skipped.

    A chunk whose section was split carries the whole section's original text, which is not its
    own, so it is described from its English alone -- see `ChunkDraft.original_is_parallel`.
    """
    furniture = [c for c in chunks if is_boilerplate(c.heading_path, c.text_en)]
    candidates = tuple(c for c in chunks if c not in furniture)
    if not candidates:
        return DescribedChunks(kept=(), dropped=tuple(chunks))
    if not source.llm_tagging:
        return DescribedChunks(kept=tuple(_from_template(c, source, title_en) for c in candidates),
                               dropped=tuple(furniture))
    summary = llm.summarise(title_en, document_text_en)
    kept = []
    for chunk in candidates:
        context = llm.describe(
            summary_en=summary, heading_path=chunk.heading_path, text_en=chunk.text_en,
            text_original=chunk.text_original if chunk.original_is_parallel else None,
            categories=categories,
        )
        if context.boilerplate:
            furniture.append(chunk)
            continue
        kept.append(replace(chunk, context_en=context.context_en,
                            topics=merge_topics(source, context.topics)))
    return DescribedChunks(kept=tuple(kept), dropped=tuple(furniture))
