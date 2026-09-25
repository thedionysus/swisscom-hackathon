from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.scope import (
    DECLARED,
    LISTED_PER_CANTON,
    SCOPE_CANTONS,
    SCOPE_MUNICIPALITIES,
    covered_levels,
    scope_from_extents,
    scope_statement,
)

CH = Location("CH", None, Level.COUNTRY, None, None, {"de": "Schweiz"})
AG = Location("CH-AG", "CH", Level.CANTON, 19, None, {"de": "Aargau"})
FR = Location("CH-FR", "CH", Level.CANTON, 10, None, {"de": "Freiburg", "en": "Fribourg"})
FR_COMMUNES = tuple(Location(f"CH-FR-{2100 + i}", "CH-FR", Level.MUNICIPALITY, 2100 + i, None, {"de": f"Gemeinde {i}"})
                    for i in range(LISTED_PER_CANTON + 1))
GE = Location("CH-GE", "CH", Level.CANTON, 25, None, {"de": "Genf", "en": "Geneva"})
VERNIER = Location("CH-GE-6643", "CH-GE", Level.MUNICIPALITY, 6643, None, {"fr": "Vernier"})
TREE = LocationTree.from_locations([CH, AG, FR, *FR_COMMUNES, GE, VERNIER])


def test_scope_lists_six_cantons_and_seven_municipalities():
    assert SCOPE_CANTONS == ("CH-ZH", "CH-BE", "CH-VD", "CH-GE", "CH-TI", "CH-GR")
    assert len(SCOPE_MUNICIPALITIES) == 7 and "CH-GR-3762" in SCOPE_MUNICIPALITIES


def test_municipality_in_scope_covers_every_level():
    assert covered_levels(("CH", "CH-GR", "CH-GR-3762")) == ("federal", "cantonal", "municipal")


def test_neighbourhood_of_a_scope_city_is_covered():
    assert covered_levels(("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3")) == ("federal", "cantonal", "municipal")


def test_other_municipality_in_a_scope_canton_is_cantonal_only():
    assert covered_levels(("CH", "CH-ZH", "CH-ZH-230")) == ("federal", "cantonal")


def test_basel_is_federal_only():
    assert covered_levels(("CH", "CH-BS", "CH-BS-2701")) == ("federal",)


def test_statement_names_what_is_not_covered():
    text = scope_statement()
    for phrase in ("commercial register", "tax bills", "weather forecasts", "Scuol"):
        assert phrase in text


def test_without_passages_beyond_the_floor_the_scope_is_the_declared_one():
    assert scope_from_extents(["CH", "CH-ZH", "CH-GR-3762"], TREE) == DECLARED


def test_a_canton_and_a_municipality_with_passages_are_added_and_named():
    scope = scope_from_extents(["CH", "CH-AG", "CH-GE-6643", "CH-XX-9999"], TREE)   # the last is not in the tree
    assert set(SCOPE_CANTONS) < scope.cantons and "CH-AG" in scope.cantons
    assert "CH-GE-6643" in scope.municipalities and not any("XX" in m for m in scope.municipalities)
    assert covered_levels(("CH", "CH-AG"), scope) == ("federal", "cantonal")
    text = scope_statement(scope)
    assert "Graubünden and Aargau;" in text and "Scuol and Vernier;" in text


def test_a_municipality_with_passages_of_its_own_is_covered_without_its_canton():
    scope = scope_from_extents(["CH-FR-2100"], TREE)
    assert covered_levels(("CH", "CH-FR", "CH-FR-2100"), scope) == ("federal", "municipal")


def test_a_canton_with_many_municipalities_is_counted_not_listed():
    text = scope_statement(scope_from_extents([c.id for c in FR_COMMUNES], TREE))
    assert f"Scuol and {LISTED_PER_CANTON + 1} municipalities in Fribourg;" in text and "Gemeinde 0" not in text
