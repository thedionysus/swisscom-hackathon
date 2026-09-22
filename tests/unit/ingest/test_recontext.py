"""The pure parts of the backfill: what it would cost, what it refuses, and what it reconstructs."""

import pytest

from swiss_grounding.ingest.recontext import (
    SourceRecontext,
    _drafts,
    _projected,
    _StoredDocument,
    _untitled,
)
from swiss_grounding.registry.models import Source

SPLIT_ORIGINAL = "Wer ein Tier hält, muss es angemessen nähren, pflegen und beschäftigen."


def source(**overrides) -> Source:
    base = {"id": "fedlex", "name": "Fedlex", "base_url": "https://www.fedlex.admin.ch",
            "default_extent_id": "CH", "authority": "federal_law",
            "categories": ("hiking", "dogs"), "fetch_strategy": "fedlex_sparql"}
    return Source(**{**base, **overrides})


def row(chunk_id: int, ordinal: int, text_original: str, text_en: str = "English.") -> dict:
    return {"id": chunk_id, "ordinal": ordinal, "heading_path": f"Art. {ordinal}", "anchor": None,
            "text_original": text_original, "text_en": text_en, "context_en": ""}


def document(title_en: str, identifier: str | None = None,
             title_original: str | None = None) -> _StoredDocument:
    return _StoredDocument(id=1, source_id="fedlex", url="https://example.ch/a",
                           title_original=title_original if title_original is not None else title_en,
                           title_en=title_en, identifier=identifier, chunks=())


def test_pieces_of_one_split_section_are_not_read_beside_their_original():
    # `chunk_sections` attaches the whole section's original to every piece it split off, and the
    # only trace left in the database is that the pieces share it.
    stored = _drafts([row(1, 0, SPLIT_ORIGINAL), row(2, 1, SPLIT_ORIGINAL)])
    assert [c.draft.original_is_parallel for c in stored] == [False, False]


def test_a_section_that_was_never_split_keeps_its_own_original():
    stored = _drafts([row(1, 0, "Art. 1 im Original."), row(2, 1, "Art. 2 im Original.")])
    assert [c.draft.original_is_parallel for c in stored] == [True, True]
    assert [c.id for c in stored] == [1, 2]


def test_a_document_titled_by_its_own_sr_number_is_untitled():
    assert _untitled(document(title_en="SR 455", identifier="SR 455")) is True
    assert _untitled(document(title_en="  ", identifier="SR 455")) is True
    assert _untitled(document(title_en="Tierschutzgesetz", identifier="SR 455")) is False
    assert _untitled(document(title_en="Dogs in Zurich", identifier=None)) is False


def test_a_translated_sr_number_is_caught_by_the_original_it_was_translated_from():
    # `SR 455` through a translator can come back as anything; `title_original` is what the
    # fetcher actually wrote, so it is the honest test.
    translated = document(title_en="Systematic Compilation 455", title_original="SR 455",
                          identifier="SR 455")
    assert _untitled(translated) is True


def test_a_document_with_no_identifier_is_untitled_only_when_it_has_no_title():
    assert _untitled(document(title_en="", title_original="", identifier=None)) is True
    assert _untitled(document(title_en="Hiking with a dog", title_original="", identifier=None)) is False


def test_a_dry_run_bills_one_description_per_chunk_and_one_summary_per_document():
    pending = _drafts([row(1, 0, "a"), row(2, 1, "b"), row(3, 2, "c")])
    counts = SourceRecontext(source_id="fedlex", examined=3)
    assert _projected(counts, source(), pending) == SourceRecontext(
        source_id="fedlex", examined=3, updated=3, describe_calls=3, summary_calls=1)


def test_a_templated_source_is_billed_nothing():
    pending = _drafts([row(1, 0, "a"), row(2, 1, "b")])
    counts = SourceRecontext(source_id="open_erz", examined=2)
    projected = _projected(counts, source(id="open_erz", llm_tagging=False), pending)
    assert (projected.describe_calls, projected.summary_calls) == (0, 0)
    assert projected.updated == 2


def test_one_documents_counts_fold_into_its_sources_running_total():
    total = SourceRecontext(source_id="fedlex", examined=2, updated=1, deleted_chunks=1,
                            describe_calls=2, summary_calls=1)
    more = SourceRecontext(source_id="fedlex", examined=3, updated=3, describe_calls=3,
                           summary_calls=1)
    assert total.plus(more) == SourceRecontext(
        source_id="fedlex", examined=5, updated=4, deleted_chunks=1, describe_calls=5,
        summary_calls=2)


def test_counts_of_two_different_sources_are_never_added_together():
    with pytest.raises(ValueError, match="ch_ch"):
        SourceRecontext(source_id="fedlex").plus(SourceRecontext(source_id="ch_ch"))
