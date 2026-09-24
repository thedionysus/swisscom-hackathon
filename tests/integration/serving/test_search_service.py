from datetime import date

import pytest

from swiss_grounding.app import load_location_tree
from swiss_grounding.db.connection import connect
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.serving.models import SearchRequest
from swiss_grounding.serving.relevance import FEATURES, ProvisionalRelevance
from swiss_grounding.serving.reranker import OverlapReranker, passage_text
from swiss_grounding.serving.search_service import SearchService, query_embedder
from tests.integration.serving.corpus_fixture import EMB, add_doc

pytestmark = pytest.mark.integration


class CountingReranker:
    """Wraps OverlapReranker and records every passage handed to `score`, call by call."""
    name = "overlap"

    def __init__(self):
        self._inner = OverlapReranker()
        self.scored_passages: list[str] = []

    def score(self, question, passages):
        self.scored_passages.extend(passages)
        return self._inner.score(question, passages)


class TreeResolver:
    """Resolves exact names from the tree only; no GeoAdmin calls in tests."""
    def __init__(self, tree):
        self.tree = tree

    def resolve(self, text):
        everything = self.tree.find(text)
        found = [f for f in everything if f.level.value == "municipality"] or list(everything)
        if len(found) != 1:
            return None
        return ResolvedLocation(found[0], self.tree.path(found[0].id), "alias", text)


def service(url, threshold=0.3):
    with connect(url) as conn:
        tree = load_location_tree(conn)
    return SearchService(database_url=url, tree=tree, resolver=TreeResolver(tree), embed=query_embedder(EMB),
                         reranker=OverlapReranker(), relevance=ProvisionalRelevance(threshold), index="bge-m3",
                         rerank_candidates=30, local_quota=10, ef_search=100, today=lambda: date(2026, 9, 24))


def test_national_question_without_a_place_answers_from_federal_law(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c",
                breadcrumb=("SR 220 OR", "Art. 266c"))
        add_doc(conn, group="or", lang="fr", text="délai de congé habitation trois mois", align="art_266_c")
    resp = service(serving_db).search(SearchRequest(question="Kündigungsfrist Wohnung?"))
    assert resp.status == "results"
    [place] = resp.places
    assert place.citations[0].language == "de" and place.citations[0].other_languages == ("fr",)
    assert place.citations[0].corroboration is not None


def test_foreign_place_needs_no_search(serving_db):
    resp = service(serving_db).search(SearchRequest(question="Rundfunkbeitrag?", locations=("Konstanz",)))
    assert resp.status == "outside_scope" and "Covered:" in resp.scope


def test_local_question_without_a_place_asks_for_it(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="zh", lang="de", text="Karton Abfuhr Termine", extent="CH-ZH-261", source="zh")
        add_doc(conn, group="be", lang="de", text="Karton Abfuhr Termine Bern", extent="CH-BE-351", source="be")
    resp = service(serving_db).search(SearchRequest(question="Wann ist die Karton Abfuhr?"))
    assert resp.status == "needs_location"


def test_two_places_are_answered_separately(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="zh", lang="de", text="Anmeldung Einwohner Zürich", extent="CH-ZH-261", source="zh")
        add_doc(conn, group="be", lang="de", text="Anmeldung Einwohner Bern", extent="CH-BE-351", source="be")
    resp = service(serving_db).search(SearchRequest(question="Anmeldung Einwohner?",
                                                    locations=("Zürich", "Bern")))
    zh, be = resp.places
    assert {c.extent_id for c in zh.citations} == {"CH-ZH-261"}
    assert {c.extent_id for c in be.citations} == {"CH-BE-351"}


def test_nothing_relevant_is_no_evidence_with_the_scope_statement(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="x", lang="de", text="Hundesteuer")
    resp = service(serving_db).search(SearchRequest(question="Wetter morgen?"))
    assert resp.status == "no_evidence" and "weather" in resp.scope


def test_placeless_question_cites_only_federal_evidence(serving_db):
    """ADR 0013: a placeless answer must never mix in a passage that applies to one place only."""
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c",
                breadcrumb=("SR 220 OR", "Art. 266c"))
        add_doc(conn, group="zh", lang="de", text="Kündigungsfrist Wohnung Zürich Formular",
                extent="CH-ZH-261", source="zh")
    resp = service(serving_db).search(SearchRequest(question="Kündigungsfrist Wohnung?"))
    assert resp.status == "results"
    [place] = resp.places
    assert place.citations
    assert all(c.extent_id == "CH" for c in place.citations)


def test_place_outside_scope_still_cites_only_the_federal_passage(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c")
        add_doc(conn, group="bs", lang="de", text="Kündigungsfrist Wohnung Basel Formular",
                extent="CH-BS-2701", source="bs")
    resp = service(serving_db).search(SearchRequest(question="Kündigungsfrist Wohnung?", locations=("Basel",)))
    assert resp.status == "results"
    [place] = resp.places
    assert place.uncovered_levels == ("cantonal", "municipal")
    assert place.citations
    assert all(c.extent_id == "CH" for c in place.citations)


def test_as_of_cites_the_version_valid_on_that_date(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="rent", lang="de", text="Mietzins Anpassung Regel alt", align="art_1",
                status="superseded", chunk_status="superseded",
                valid_from=date(2020, 1, 1), valid_to=date(2025, 1, 1),
                url="https://example.ch/rent/de/old")
        add_doc(conn, group="rent", lang="de", text="Mietzins Anpassung Regel neu", align="art_1",
                status="current", chunk_status="current",
                valid_from=date(2025, 1, 1), valid_to=None,
                url="https://example.ch/rent/de/new")
    resp = service(serving_db).search(
        SearchRequest(question="Mietzins Anpassung Regel?", as_of=date(2023, 6, 1)))
    assert resp.status == "results"
    [place] = resp.places
    assert place.citations
    assert all(c.valid_from == date(2020, 1, 1) for c in place.citations)


def test_limit_keeps_the_most_relevant_groups_sorted_by_relevance(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="g1", lang="de", text="Alpha Beta Gamma Delta Epsilon", align="a1")
        add_doc(conn, group="g2", lang="de", text="Alpha Beta Gamma Delta", align="a2")
        add_doc(conn, group="g3", lang="de", text="Alpha Beta Gamma", align="a3")
    resp = service(serving_db).search(SearchRequest(question="Alpha Beta Gamma Delta Epsilon", limit=2))
    assert resp.status == "results"
    [place] = resp.places
    assert len(place.citations) == 2
    assert place.citations[0].relevance >= place.citations[1].relevance
    assert place.citations[0].passage == "Alpha Beta Gamma Delta Epsilon"


def test_reranker_cache_scores_a_shared_federal_passage_once(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c",
                breadcrumb=("SR 220 OR", "Art. 266c"))
        add_doc(conn, group="zh", lang="de", text="Kündigungsfrist Wohnung Zürich Formular",
                extent="CH-ZH-261", source="zh")
        add_doc(conn, group="be", lang="de", text="Kündigungsfrist Wohnung Bern Formular",
                extent="CH-BE-351", source="be")
    with connect(serving_db) as conn:
        tree = load_location_tree(conn)
    reranker = CountingReranker()
    svc = SearchService(database_url=serving_db, tree=tree, resolver=TreeResolver(tree), embed=query_embedder(EMB),
                        reranker=reranker, relevance=ProvisionalRelevance(0.3), index="bge-m3",
                        rerank_candidates=30, local_quota=10, ef_search=100, today=lambda: date(2026, 9, 24))
    resp = svc.search(SearchRequest(question="Kündigungsfrist Wohnung?", locations=("Zürich", "Bern")))
    assert resp.status == "results"
    federal = passage_text(("SR 220 OR", "Art. 266c"), "Kündigungsfrist Wohnung drei Monate")
    assert reranker.scored_passages.count(federal) == 1


def test_scored_for_eval_yields_feature_vectors_per_group(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c",
                breadcrumb=("SR 220 OR", "Art. 266c"))
    rows = service(serving_db).scored_for_eval(SearchRequest(question="Kündigungsfrist Wohnung?"))
    assert rows
    for features, key in rows:
        assert len(features) == len(FEATURES)
        assert isinstance(key, str)


def test_duplicate_text_and_other_language_versions_are_cited_once(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="a", lang="de", text="Führerausweis Umtausch zwölf Monate", url="https://ch.ch/x/de")
        add_doc(conn, group="b", lang="de", text="Führerausweis Umtausch zwölf Monate", url="https://ch.ch/y/de")
        add_doc(conn, group="c", lang="de", text="Führerausweis Umtausch Frist Monate", align="s1",
                url="https://ch.ch/z/de")
        add_doc(conn, group="c", lang="en", text="Führerausweis Umtausch Frist Monate licence", align="s2",
                url="https://ch.ch/z/en")
    resp = service(serving_db, threshold=0.0).search(SearchRequest(question="Führerausweis Umtausch Monate?"))
    urls = [c.url for p in resp.places for c in p.citations]
    assert len([u for u in urls if u in ("https://ch.ch/x/de", "https://ch.ch/y/de")]) == 1
    assert len([u for u in urls if u.startswith("https://ch.ch/z/")]) == 1


def test_the_question_language_version_is_the_one_cited(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="v", lang="en", text="next federal elections vote elezioni", align="s1",
                url="https://ch.ch/en/v")
        add_doc(conn, group="v", lang="it", text="prossime elezioni federali", align="s9",
                url="https://ch.ch/it/v")
    resp = service(serving_db, threshold=0.0).search(SearchRequest(question="Quando sono le prossime elezioni?"))
    urls = [c.url for p in resp.places for c in p.citations if c.url.startswith("https://ch.ch/")]
    assert urls == ["https://ch.ch/it/v"]
