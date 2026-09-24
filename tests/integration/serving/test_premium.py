from pathlib import Path

import pytest

from swiss_grounding.app import load_location_tree
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.premium import cheapest_premiums
from swiss_grounding.lookups.premium_data import load_premiums

pytestmark = pytest.mark.integration
FIX = Path("tests/fixtures/premium")


def test_cheapest_premiums_for_lugano_adult_2500(serving_db):
    with connect(serving_db) as conn:
        load_premiums(conn, FIX / "premiums_sample.csv", FIX / "regions_sample.csv", 2026, {})
        tree = load_location_tree(conn)
        out = cheapest_premiums(conn, tree, location_id="CH-TI-5192", age=30, deductible=2500, accident=False,
                                model="any", year=2026, limit=5)
    assert out["status"] == "results" and out["premium_region"] == 1
    assert [o["premium_chf"] for o in out["premiums"]] == [330.55, 345.00]


def test_a_canton_without_premium_regions_uses_its_single_region(serving_db):
    """BAG's region list names only the cantons divided into regions; Genève's canton has one, region 0."""
    with connect(serving_db) as conn:
        load_premiums(conn, FIX / "premiums_sample.csv", FIX / "regions_sample.csv", 2026, {})
        tree = load_location_tree(conn)
        out = cheapest_premiums(conn, tree, location_id="CH-GE-6621", age=30, deductible=2500, accident=False,
                                model="any", year=2026, limit=5)
    assert out["status"] == "results" and (out["canton"], out["premium_region"]) == ("GE", 0)
    assert [o["premium_chf"] for o in out["premiums"]] == [480.00]


def test_a_commune_missing_from_a_divided_canton_has_no_evidence(serving_db):
    """Ticino is divided into regions, so a commune the list does not name has no known region."""
    with connect(serving_db) as conn:
        load_premiums(conn, FIX / "premiums_sample.csv", FIX / "regions_sample.csv", 2026, {})
        tree = load_location_tree(conn)
        out = cheapest_premiums(conn, tree, location_id="CH-TI-5113", age=30, deductible=2500, accident=False,
                                model="any", year=2026, limit=5)
    assert out["status"] == "no_evidence" and "Locarno" in out["message"]


def test_a_canton_is_refused(serving_db):
    with connect(serving_db) as conn:
        tree = load_location_tree(conn)
        out = cheapest_premiums(conn, tree, location_id="CH-TI", age=30, deductible=2500, accident=False,
                                model="any", year=2026, limit=5)
    assert out["status"] == "invalid_request" and "municipality" in out["message"]


def test_invalid_deductible_is_explained(serving_db):
    with connect(serving_db) as conn:
        load_premiums(conn, FIX / "premiums_sample.csv", FIX / "regions_sample.csv", 2026, {})
        tree = load_location_tree(conn)
        out = cheapest_premiums(conn, tree, location_id="CH-TI-5192", age=30, deductible=750, accident=False,
                                model="any", year=2026, limit=5)
    assert out["status"] == "invalid_request" and "2500" in out["message"]
