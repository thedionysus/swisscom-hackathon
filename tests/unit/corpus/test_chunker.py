from swiss_grounding.corpus.chunker import HARD_MAX_CHARS, MAX_CHARS, chunk_document
from swiss_grounding.corpus.models import ParsedDocument, ParsedSection

CRUMB = ("SR 220 Obligationenrecht", "Art. 336c Kündigung zur Unzeit")


def _doc(*sections):
    return ParsedDocument(source_id="s", url="u", language="de", work_key="k", title="OR", sections=sections)


def test_short_article_is_one_chunk():
    s = ParsedSection("art_336_c", CRUMB, "art_336_c", "1 Kurz.\n2 Auch kurz.",
                      paragraphs=(("art_336_c/para_1", "1 Kurz."), ("art_336_c/para_2", "2 Auch kurz.")))
    [chunk] = chunk_document(_doc(s))
    assert chunk.align_key == "art_336_c"
    assert chunk.text == "1 Kurz.\n2 Auch kurz."
    assert chunk.breadcrumb == CRUMB


def test_long_article_splits_per_paragraph_with_paragraph_keys():
    p1, p2 = "1 " + "A" * 1000 + ".", "2 " + "B" * 1000 + "."
    s = ParsedSection("art_336_c", CRUMB, "art_336_c", p1 + "\n" + p2,
                      paragraphs=(("art_336_c/para_1", p1), ("art_336_c/para_2", p2)))
    chunks = chunk_document(_doc(s))
    assert [c.align_key for c in chunks] == ["art_336_c/para_1", "art_336_c/para_2"]
    assert [c.ordinal for c in chunks] == [0, 1]
    assert chunks[0].text == p1
    assert all(c.anchor == "art_336_c" for c in chunks)


def test_long_prose_splits_into_overlapping_windows():
    text = " ".join(f"Satz {i} hat einige Wörter." for i in range(200))
    chunks = chunk_document(_doc(ParsedSection("de:3", ("Seite", "Abschnitt"), None, text)))
    assert len(chunks) > 1
    assert all(len(c.text) <= MAX_CHARS for c in chunks)
    assert [c.align_key for c in chunks] == [f"de:3#{i}" for i in range(len(chunks))]
    assert chunks[0].text[-100:] in text and chunks[1].text[:40] in chunks[0].text  # overlap


def test_huge_paragraph_is_windowed_under_its_own_key():
    big = "1 " + "Wort. " * 700
    s = ParsedSection("art_9", CRUMB, "art_9", big, paragraphs=(("art_9/para_1", big),))
    chunks = chunk_document(_doc(s))
    assert len(big) > HARD_MAX_CHARS
    assert chunks[0].align_key == "art_9/para_1#0"


def test_ocr_page_is_one_empty_chunk():
    s = ParsedSection("de:p2", ("Merkblatt", "p. 2"), "page=2", "", needs_ocr=True, ocr_image="/tmp/p2.png")
    [chunk] = chunk_document(_doc(s))
    assert chunk.needs_ocr and chunk.text == "" and chunk.ocr_image == "/tmp/p2.png"


def test_empty_sections_are_dropped():
    assert chunk_document(_doc(ParsedSection("de:0", ("T",), None, "   "))) == ()
