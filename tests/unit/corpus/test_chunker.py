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


def test_split_paragraphs_flag_forces_per_paragraph_split_even_if_short():
    s = ParsedSection("art_5", CRUMB, "art_5", "1 Kurz.\n2 Auch kurz.",
                      paragraphs=(("art_5/para_1", "1 Kurz."), ("art_5/para_2", "2 Auch kurz.")),
                      split_paragraphs=True)
    chunks = chunk_document(_doc(s))
    assert [c.align_key for c in chunks] == ["art_5/para_1", "art_5/para_2"]
    assert chunks[0].text == "1 Kurz."


def test_windows_do_not_start_mid_word():
    words = [f"Wort{i}xyzabc" for i in range(300)]  # varying lengths so windows can't land on aligned boundaries
    text = " ".join(words)
    chunks = chunk_document(_doc(ParsedSection("de:3", ("Seite", "Abschnitt"), None, text)))
    assert len(chunks) > 1
    word_set = set(words)
    for c in chunks[1:]:
        first_token = c.text.split(" ", 1)[0].rstrip(".")
        assert first_token in word_set


def test_sentence_cut_skips_legal_abbreviations():
    # the only ". " occurrences before the MAX_CHARS boundary are legal abbreviations; a naive
    # rfind(". ") would cut right after "lit. ", splitting mid-reference
    padding = "Wort " * 190
    abbrev_clause = "Art. 5 Abs. 2 lit. a regelt die Kündigung zur Unzeit gemäss diesem Gesetz und dessen Anhang"
    filler = " Wort" * 260
    text = padding + abbrev_clause + filler
    chunks = chunk_document(_doc(ParsedSection("de:9", ("Seite",), None, text)))
    assert len(chunks) > 1
    for c in chunks:
        stripped = c.text.rstrip()
        assert not stripped.endswith("Art.")
        assert not stripped.endswith("Abs.")
        assert not stripped.endswith("lit.")
