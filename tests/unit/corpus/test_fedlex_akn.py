from pathlib import Path

from swiss_grounding.corpus.connectors.fedlex_akn import parse_akn

FIXTURES = Path(__file__).parents[2] / "fixtures" / "corpus"
XML = (FIXTURES / "akn_or.xml").read_text()
PRETTY_XML = (FIXTURES / "akn_or_pretty.xml").read_text()
INLINE_MARKUP_XML = (FIXTURES / "akn_inline_markup.xml").read_text()


def _by_key(sections):
    return {s.align_key: s for s in sections}


def test_breadcrumb_carries_act_containers_and_article():
    s = _by_key(parse_akn(XML, act_title="Obligationenrecht", sr="220"))["art_336_c"]
    assert s.breadcrumb == ("SR 220 Obligationenrecht", "Zehnter Titel: Der Arbeitsvertrag",
                            "Erster Abschnitt: Der Einzelarbeitsvertrag", "Art. 336c Kündigung zur Unzeit")
    assert s.anchor == "art_336_c"


def test_paragraph_and_letter_labels_are_kept_and_footnotes_dropped():
    s = _by_key(parse_akn(XML, act_title="Obligationenrecht", sr="220"))["art_336_c"]
    assert s.text.startswith("1 Nach Ablauf der Probezeit")
    assert "\na. während die andere Partei" in s.text
    assert "\nb. während der Arbeitnehmer" in s.text
    assert "\n2 Die Kündigung" in s.text
    assert "Fassung gemäss" not in s.text and "Fassung gemäss" not in " ".join(s.breadcrumb)
    assert [k for k, _ in s.paragraphs] == ["art_336_c/para_1", "art_336_c/para_2"]


def test_top_level_article_has_only_the_act_above_it():
    s = _by_key(parse_akn(XML, act_title="Obligationenrecht", sr="220"))["art_1"]
    assert s.breadcrumb == ("SR 220 Obligationenrecht", "Art. 1 Abschluss des Vertrages")
    assert s.text.startswith("Zum Abschlusse eines Vertrages")


def test_pretty_printed_whitespace_between_num_and_content_does_not_break_lines():
    """Amendment A10: newlines/indent between <num>1</num> and <content> must not split them."""
    s = _by_key(parse_akn(PRETTY_XML, act_title="Obligationenrecht", sr="220"))["art_336_c"]
    assert s.text.startswith("1 Nach Ablauf der Probezeit")
    assert "\na. während die andere Partei" in s.text
    assert "\nb. während der Arbeitnehmer" in s.text
    assert "\n2 Die Kündigung" in s.text


def test_inline_markup_does_not_split_words_and_removed_footnotes_leave_no_stray_space():
    """Review fix: <i>/<sup> used inline (e.g. 'Artikel 64<i>c</i>') must stay fused into one
    word instead of gaining a space from the renderer's separator, and a space left behind by a
    decomposed <authorialNote> must not survive before trailing punctuation."""
    s = _by_key(parse_akn(INLINE_MARKUP_XML, act_title="Test", sr="1"))["art_64_c"]
    assert "Artikel 64c Absatz 1" in s.text
    assert "Art. 12bis" in s.text
    assert " ." not in s.text
    assert "Grenzkodex." in s.text
