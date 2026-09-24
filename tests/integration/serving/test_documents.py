import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.documents import get_document
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration


def _law(conn, lang, url):
    doc, c1 = add_doc(conn, group="or", lang=lang, text=f"Abs 1 {lang}", align="art_336_c/para_1", url=url)
    conn.execute("update corpus.document set identifier = 'SR 220' where id = %s", (doc,))
    conn.execute("update corpus.chunk set anchor = 'art_336_c' where id = %s", (c1,))
    c2 = conn.execute(
        "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, "
        "text, extent_id, authority, status, chunk_hash, anchor) values (%s,%s,'or','art_336_c/para_2',1,"
        "'{Art. 336c}',%s,'CH','federal_law','current','c2','art_336_c') returning id",
        (doc, lang, f"Abs 2 {lang}")).fetchone()["id"]
    return doc, c1, c2


def test_chunk_id_returns_the_whole_article(corpus_db):
    with connect(corpus_db) as conn:
        doc, c1, _ = _law(conn, "de", "https://fedlex/or/de")
        out = get_document(conn, document_id=doc, chunk_id=c1)
    assert [c["text"] for c in out["chunks"]] == ["Abs 1 de", "Abs 2 de"]


def test_reference_finds_the_article_in_the_requested_language(corpus_db):
    with connect(corpus_db) as conn:
        _law(conn, "de", "https://fedlex/or/de")
        _law(conn, "fr", "https://fedlex/or/fr")
        out = get_document(conn, reference="Art. 336c OR", language="fr")
    assert out["document"]["language"] == "fr"
    assert [c["text"] for c in out["chunks"]] == ["Abs 1 fr", "Abs 2 fr"]
    assert out["available_languages"] == ["de", "fr"]


def test_language_switch_maps_the_chunk_by_align_key(corpus_db):
    with connect(corpus_db) as conn:
        doc, c1, _ = _law(conn, "de", "https://fedlex/or/de")
        _law(conn, "fr", "https://fedlex/or/fr")
        out = get_document(conn, document_id=doc, chunk_id=c1, language="fr")
    assert out["document"]["language"] == "fr" and out["chunks"][0]["text"] == "Abs 1 fr"


def test_unknown_reference_is_an_error_not_an_exception(corpus_db):
    with connect(corpus_db) as conn:
        out = get_document(conn, reference="Art. 999 OR")
    assert "error" in out
