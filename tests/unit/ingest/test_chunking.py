import pytest

from swiss_grounding.ingest.chunking import ChunkLimits, chunk_sections
from swiss_grounding.ingest.models import EnrichmentError, Section


def sec(path, text, anchor=None):
    return Section(heading_path=path, anchor=anchor, text=text)


def test_one_chunk_per_section_when_small():
    original = (sec("A", "kurz", "a"), sec("B", "auch kurz", "b"))
    english = (sec("A", "short", "a"), sec("B", "also short", "b"))
    chunks = chunk_sections(original, english, ChunkLimits(max_chars=100, overlap_chars=10))
    assert [c.ordinal for c in chunks] == [0, 1]
    assert chunks[0].text_original == "kurz" and chunks[0].text_en == "short"
    assert chunks[1].anchor == "b" and chunks[1].heading_path == "B"


def test_long_section_is_split_with_overlap_on_english_and_original_kept_whole():
    long_en = " ".join(f"sentence{i}." for i in range(60))
    original = (sec("A", "orig text", "a"),)
    english = (sec("A", long_en, "a"),)
    chunks = chunk_sections(original, english, ChunkLimits(max_chars=200, overlap_chars=40))
    assert len(chunks) > 1
    assert all(len(c.text_en) <= 200 for c in chunks)
    assert chunks[1].text_en[:40].strip() in chunks[0].text_en      # overlap
    assert all(c.text_original == "orig text" for c in chunks)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_split_pieces_cover_the_whole_text():
    long_en = " ".join(f"w{i}." for i in range(300))
    chunks = chunk_sections((sec("A", "o"),), (sec("A", long_en),), ChunkLimits(max_chars=120, overlap_chars=20))
    assert chunks[0].text_en.startswith("w0.") and chunks[-1].text_en.endswith("w299.")


def test_mismatched_section_counts_raise():
    with pytest.raises(ValueError, match="section count"):
        chunk_sections((sec("A", "x"),), (), ChunkLimits())


def test_empty_sections_are_skipped():
    chunks = chunk_sections((sec("A", "  "), sec("B", "y")), (sec("A", "  "), sec("B", "y")), ChunkLimits())
    assert len(chunks) == 1 and chunks[0].heading_path == "B" and chunks[0].ordinal == 0


def test_invalid_limits_raise():
    with pytest.raises(ValueError):
        ChunkLimits(max_chars=10, overlap_chars=10)


def test_a_dropped_section_is_an_error_not_a_silent_loss():
    """An article whose translation came back empty must fail the document, not vanish from it."""
    with pytest.raises(EnrichmentError):
        chunk_sections(original=(sec("Art. 1", "Text"),), english=(sec("Art. 1", "   "),), limits=ChunkLimits())


def test_a_section_empty_in_both_languages_is_still_skipped():
    """Nothing was lost: the source section carries no text either."""
    chunks = chunk_sections((sec("A", "  "), sec("B", "y")), (sec("A", "  "), sec("B", "y")), ChunkLimits())
    assert len(chunks) == 1 and chunks[0].heading_path == "B"
