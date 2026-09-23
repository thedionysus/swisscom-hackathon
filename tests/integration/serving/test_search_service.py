from datetime import date

import pytest

from swiss_grounding.app import load_location_tree
from swiss_grounding.db.connection import connect
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.serving.models import SearchRequest
from swiss_grounding.serving.relevance import ProvisionalRelevance
from swiss_grounding.serving.reranker import OverlapReranker
from swiss_grounding.serving.search_service import SearchService, query_embedder
from tests.integration.serving.corpus_fixture import EMB, add_doc

pytestmark = pytest.mark.integration


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
