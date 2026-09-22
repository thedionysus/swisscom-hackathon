"""Generated context steers retrieval and never reaches a citation (ADR 0005).

This is the guard on the whole design. A wrong description only misfiles a chunk; a description
that reaches a citation is generated prose presented to a caller as sourced evidence. The ADR
is explicit: "Citations must draw only on `text_original` and `text_en`. A future change that
quotes the indexed text would leak generated prose into an answer presented as sourced."

The tests below come in pairs, and both halves matter. The behavioural half runs a real search
and asserts the snippet is the chunk's own text, character for character. The structural half
asserts no field carrying generated text exists on the records a citation is built from, so the
leak cannot be introduced by adding a field and forgetting there was ever a rule.

Do not weaken either half. If a snippet legitimately needs to change, the text it draws on does
not: `text_en` and `text_original` are the only two columns a citation may read.
"""

import os
from dataclasses import fields
from datetime import date

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.context import indexed_text
from swiss_grounding.ingest.models import ChunkDraft, EnrichedDocument, FetchedDocument, Section
from swiss_grounding.ingest.persist import persist_document
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.cite import build_citation
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.models import ChunkRecord, Citation
from swiss_grounding.retrieval.rerank import RerankWeights, rerank
from swiss_grounding.retrieval.search import hybrid_search

pytestmark = pytest.mark.integration

EMB = FakeEmbedder(dim=8)
URL = "https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de"
# A phrase that exists only in the generated context: not in either stored text, and not in the
# document title either, so finding it anywhere on a citation means generated prose leaked.
GENERATED = "Sets penalties for mistreating animals"
CONTEXT = f"From the Animal Welfare Act. {GENERATED}."
TEXT_EN = "Anyone who intentionally, provided Article 26 is not applicable, is punished."
TEXT_ORIGINAL = "Wer vorsätzlich, sofern Artikel 26 nicht anwendbar ist, wird bestraft."


def _document() -> EnrichedDocument:
    section = Section("Art. 28", "art_28", TEXT_ORIGINAL)
    fetched = FetchedDocument(source_id="fedlex", url=URL, title="SR 455", language="de",
                              sections=(section,), identifier="SR 455", valid_from=date(2022, 1, 1))
    return EnrichedDocument(fetched=fetched, title_en="Animal Welfare Act",
                            sections_en=(Section("Art. 28", "art_28", TEXT_EN),),
                            extent_id="CH", extent_reason="source_default")


def _chunk() -> ChunkDraft:
    return ChunkDraft(ordinal=0, heading_path="Art. 28", anchor="art_28",
                      text_original=TEXT_ORIGINAL, text_en=TEXT_EN, context_en=CONTEXT)


@pytest.fixture
def stored():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document, fetch_state restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        outcome = persist_document(conn, _document(), (_chunk(),), EMB, run_id="r1")
        tree = load_tree(conn)
    return u, tree, outcome.document_id


def _citation(url, tree) -> Citation:
    with connect(url) as conn:
        hits = hybrid_search(conn, EMB, question="penalties for animals",
                             extent_path=("CH",), as_of=None)
    scored = rerank(hits, tree, query_node_id="CH", query_categories=(), weights=RerankWeights())
    assert scored, "the stored chunk was not retrieved at all"
    return build_citation(scored[0], tree)


def test_the_index_sees_the_generated_context(stored):
    """Without this the rest is vacuous: context must actually be reaching retrieval."""
    url, _, document_id = stored
    with connect(url) as conn:
        row = conn.execute(
            "select context_en, tsv @@ to_tsquery('english', 'welfare') as keyword_hit "
            "from chunk where document_id = %s", (document_id,),
        ).fetchone()
    assert row["context_en"] == CONTEXT
    assert row["keyword_hit"] is True      # "welfare" appears only in the generated context


def test_the_embedded_vector_is_of_the_context_and_the_text_together(stored):
    url, _, document_id = stored
    with connect(url) as conn:
        stored_vector = conn.execute(
            "select embedding from chunk where document_id = %s", (document_id,)).fetchone()["embedding"]
    assert stored_vector.to_list() == pytest.approx(EMB.embed([indexed_text(CONTEXT, TEXT_EN)])[0])
    assert stored_vector.to_list() != pytest.approx(EMB.embed([TEXT_EN])[0])


def test_a_citation_quotes_the_chunk_text_and_not_one_word_of_the_context(stored):
    url, tree, _ = stored
    citation = _citation(url, tree)
    assert GENERATED not in citation.snippet_en
    assert GENERATED not in citation.snippet_original
    assert citation.snippet_en == TEXT_EN
    assert citation.snippet_original == TEXT_ORIGINAL


def test_no_part_of_the_citation_carries_the_generated_phrase(stored):
    """Not just the snippet: no field of the citation may carry generated prose."""
    url, tree, _ = stored
    citation = _citation(url, tree)
    for field in fields(Citation):
        value = getattr(citation, field.name)
        assert GENERATED not in value if isinstance(value, str) else True, field.name


def test_the_records_a_citation_is_built_from_have_nowhere_to_put_generated_text():
    """The structural half. `hybrid_search` never selects `context_en`, so `ChunkRecord` has no
    field for it and `build_citation` cannot reach it even by mistake. Adding one to either type
    is how the leak would arrive, and it has to fail here first."""
    for record in (ChunkRecord, Citation):
        names = {f.name for f in fields(record)}
        assert "context_en" not in names and "context" not in names, record.__name__
