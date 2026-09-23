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
