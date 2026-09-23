from datetime import date

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.candidates import EMB_TABLE, ArmQuery, gather_candidates
from tests.integration.serving.corpus_fixture import EMB, add_doc

pytestmark = pytest.mark.integration
PATH_ZH = ("CH", "CH-ZH", "CH-ZH-261")


def _query(text, **kw):
    return ArmQuery(question=text, question_lang=kw.get("lang"), question_vec=EMB.embed([text])[0], question_sparse=kw.get("sparse"),
                    translations={}, translation_vecs={}, extent_path=kw.get("path", PATH_ZH),
                    local_extents=kw.get("local", ("CH-ZH", "CH-ZH-261")), as_of=kw.get("as_of"),
                    per_arm=10, top_n=kw.get("top_n", 30), local_quota=kw.get("quota", 10))


def test_finds_a_chunk_on_the_path_by_keyword_and_vector(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="g1", lang="de", text="Kündigungsfrist für Wohnungen drei Monate")
        found = gather_candidates(conn, _query("Kündigungsfrist Wohnungen"), index="bge-m3", ef_search=100)
    assert found[0].translation_group_id == "g1"
    assert {"dense", "kw_de"} <= found[0].arms


def test_off_path_extents_are_filtered_out(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="bern", lang="de", text="Hundesteuer Bern", extent="CH-BE-351", source="bern")
        found = gather_candidates(conn, _query("Hundesteuer"), index="bge-m3", ef_search=100)
    assert found == []


def test_boilerplate_and_superseded_are_filtered_out(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="b", lang="de", text="Cookie Hinweis Datenschutz", chunk_status="boilerplate")
        add_doc(conn, group="s", lang="de", text="Cookie Hinweis alt", status="superseded")
        found = gather_candidates(conn, _query("Cookie Hinweis"), index="bge-m3", ef_search=100)
    assert found == []


def test_as_of_selects_the_version_valid_on_that_day(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="v", lang="de", text="Frist alt", status="superseded", align="a",
                valid_from=date(2020, 1, 1), valid_to=date(2026, 1, 1))
        add_doc(conn, group="v", lang="de", text="Frist neu", align="a", valid_from=date(2026, 1, 1))
        old = gather_candidates(conn, _query("Frist", as_of=date(2025, 6, 1)), index="bge-m3", ef_search=100)
    assert [c.text for c in old] == ["Frist alt"]


def test_as_of_keeps_undated_current_pages(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="page", lang="de", text="Frist Merkblatt")
        found = gather_candidates(conn, _query("Frist", as_of=date(2025, 6, 1)), index="bge-m3", ef_search=100)
    assert [c.text for c in found] == ["Frist Merkblatt"]


def test_identifiers_reach_other_language_stores(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="sr", lang="fr", text="Art. 266c CO délai", align="266c")
        found = gather_candidates(conn, _query("Was sagt Artikel 266c?", lang="de"), index="bge-m3", ef_search=100)
    assert "kw_fr" in found[0].arms


def test_local_quota_keeps_municipal_chunks_in_the_pool(corpus_db):
    with connect(corpus_db) as conn:
        for i in range(5):
            add_doc(conn, group=f"fed{i}", lang="de", text=f"Abfall Bund Regel {i} Abfall")
        add_doc(conn, group="city", lang="de", text="Karton Sammlung Stadt", extent="CH-ZH-261", source="zh")
        found = gather_candidates(conn, _query("Abfall", top_n=3, quota=1), index="bge-m3", ef_search=100)
    assert "city" in {c.translation_group_id for c in found}
    assert len(found) == 3


def test_empty_path_searches_all_of_switzerland(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="bern", lang="de", text="Hundesteuer Bern", extent="CH-BE-351", source="bern")
        found = gather_candidates(conn, _query("Hundesteuer", path=(), local=()), index="bge-m3", ef_search=100)
    assert [c.extent_id for c in found] == ["CH-BE-351"]


def test_translation_is_searched_in_its_own_store(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="g", lang="fr", text="délai de congé logement", align="x")
        q = _query("Kündigungsfrist Wohnung")
        vec = EMB.embed(["délai de congé logement"])[0]
        q = q.__class__(**{**q.__dict__, "translations": {"fr": "délai de congé logement"},
                           "translation_vecs": {"fr": vec}})
        found = gather_candidates(conn, q, index="bge-m3", ef_search=100)
    assert {"dense_fr", "kw_fr"} <= found[0].arms
    assert "fr" in found[0].query_langs


def test_sparse_arm_finds_chunks_by_lexical_weights(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="rent", lang="de", text="Mietzins Anpassung", sparse={7: 0.9})
        found = gather_candidates(conn, _query("Mietzins", sparse={7: 1.0}), index="bge-m3", ef_search=100)
    assert "sparse" in found[0].arms


def test_local_scope_gives_no_extra_rrf_score(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="city", lang="de", text="Karton Sammlung Stadt", extent="CH-ZH-261", source="zh")
        with_local = gather_candidates(conn, _query("Karton"), index="bge-m3", ef_search=100)
        without = gather_candidates(conn, _query("Karton", local=()), index="bge-m3", ef_search=100)
    assert with_local[0].rrf == without[0].rrf
    assert with_local[0].arms == without[0].arms


def test_unknown_index_names_the_allowed_ones(corpus_db):
    with connect(corpus_db) as conn, pytest.raises(ValueError, match=", ".join(sorted(EMB_TABLE))):
        gather_candidates(conn, _query("Frist"), index="nope", ef_search=100)
