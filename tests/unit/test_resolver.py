import pytest

from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.models import AmbiguousLocation, Level, Location
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree


def _loc(id_, parent_id, level, names, aliases=()):
    return Location(
        id=id_, parent_id=parent_id, level=level, bfs_id=None, lindas_uri=None,
        names=names, aliases=aliases,
    )


def small_tree() -> LocationTree:
    locations = [
        _loc("CH", None, Level.COUNTRY, {"en": "Switzerland", "de": "Schweiz"}),
        _loc("CH-ZH", "CH", Level.CANTON, {"en": "Zurich", "de": "Zürich"}),
        _loc("CH-SG", "CH", Level.CANTON, {"en": "St. Gallen", "de": "St. Gallen"}),
        _loc("CH-ZH-261", "CH-ZH", Level.MUNICIPALITY, {"en": "Zurich", "de": "Zürich"}),
        _loc("CH-ZH-34", "CH-ZH", Level.MUNICIPALITY, {"en": "Wil", "de": "Wil"}, ("Wil ZH",)),
        _loc("CH-SG-3427", "CH-SG", Level.MUNICIPALITY, {"en": "Wil", "de": "Wil"}, ("Wil SG",)),
        _loc("CH-ZH-2", "CH-ZH", Level.MUNICIPALITY,
             {"en": "Affoltern am Albis", "de": "Affoltern am Albis"}),
        _loc("CH-ZH-261-K1", "CH-ZH-261", Level.NEIGHBORHOOD, {"en": "Kreis 1", "de": "Kreis 1"}),
        _loc("CH-ZH-261-K1-CITY", "CH-ZH-261-K1", Level.NEIGHBORHOOD, {"en": "City", "de": "City"}),
        _loc("CH-ZH-261-K11", "CH-ZH-261", Level.NEIGHBORHOOD, {"en": "Kreis 11", "de": "Kreis 11"}),
        _loc(
            "CH-ZH-261-K11-AFFOLTERN", "CH-ZH-261-K11", Level.NEIGHBORHOOD,
            {"en": "Affoltern", "de": "Affoltern"},
        ),
    ]
    return LocationTree.from_locations(locations)


@pytest.fixture
def resolver() -> LocationResolver:
    return LocationResolver(small_tree(), FakeGeo(()))


def test_bare_wil_is_ambiguous_across_cantons(resolver):
    result = resolver.resolve("Wil")
    assert isinstance(result, AmbiguousLocation)
    assert {c.id for c in result.candidates} == {"CH-ZH-34", "CH-SG-3427"}


def test_wil_with_canton_suffix_resolves(resolver):
    assert resolver.resolve("Wil ZH").location.id == "CH-ZH-34"


def test_bare_affoltern_is_ambiguous_between_quartier_and_commune(resolver):
    assert isinstance(resolver.resolve("Affoltern"), AmbiguousLocation)


def test_common_word_quartier_needs_a_marker(resolver):
    assert isinstance(resolver.resolve("City"), AmbiguousLocation)
    assert resolver.resolve("Quartier City").location.id == "CH-ZH-261-K1-CITY"


def test_marker_restricts_level(resolver):
    assert resolver.resolve("Kanton Zürich").location.id == "CH-ZH"
    assert resolver.resolve("Stadt Zürich").location.id == "CH-ZH-261"
    assert resolver.resolve("Gemeinde Zürich").location.id == "CH-ZH-261"


def test_city_and_canton_same_name_stays_most_specific(resolver):
    r = resolver.resolve("Zürich")
    assert r.location.id == "CH-ZH-261" and [a.id for a in r.alternatives] == ["CH-ZH"]


class FakeGeo:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def search_communes(self, text):
        self.calls.append(text)
        return self.hits


def tree():
    return LocationTree.from_locations(seed_locations())


def test_alias_hit_does_not_call_geoadmin():
    geo = FakeGeo(())
    r = LocationResolver(tree(), geo).resolve("Wiedikon")
    assert r.location.id == "CH-ZH-261-K3-ALT-WIEDIKON"
    assert r.method == "alias"
    assert r.path[-1] == r.location.id
    assert geo.calls == []


def test_ambiguous_alias_picks_most_specific_and_lists_alternatives():
    r = LocationResolver(tree(), FakeGeo(())).resolve("Zürich")
    assert r.location.id == "CH-ZH-261"
    assert [a.id for a in r.alternatives] == ["CH-ZH"]


def test_geoadmin_known_commune():
    # Exercise _resolve_via_geoadmin directly: since "Zurich" is itself a tree alias,
    # resolve() would short-circuit through the scan before ever reaching GeoAdmin
    # (see test_alias_found_in_text_short_circuits_geoadmin).
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    r = LocationResolver(tree(), geo)._resolve_via_geoadmin("Zurich")
    assert r.location.id == "CH-ZH-261"
    assert r.method == "geoadmin"


def test_alias_found_in_text_short_circuits_geoadmin():
    """A recognisable alias inside the text resolves via the scan, never reaching GeoAdmin."""
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Zurich centre")
    assert r.location.id == "CH-ZH-261"
    assert r.method == "alias_scan"
    assert geo.calls == []


def test_geoadmin_hit_without_token_overlap_is_rejected():
    geo = FakeGeo((GeoAdminHit(bfs_id=7, label="Stans (NW)"),))
    assert LocationResolver(tree(), geo).resolve("nowhere") is None


def test_geoadmin_hit_with_token_overlap_is_accepted():
    geo = FakeGeo((GeoAdminHit(bfs_id=99999, label="Musterhausen (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("musterhausen")
    assert r.location.id == "CH-ZH"
    assert r.method == "geoadmin_approximate"


def test_geoadmin_transliteration_without_overlap_is_rejected():
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    assert LocationResolver(tree(), geo).resolve("Zueri city") is None


def test_geoadmin_unknown_commune_falls_back_to_canton_via_label():
    geo = FakeGeo((GeoAdminHit(bfs_id=99999, label="Musterhausen (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Musterhausen")
    assert r.location.id == "CH-ZH"
    assert r.method == "geoadmin_approximate"


def test_nothing_found_returns_none():
    assert LocationResolver(tree(), FakeGeo(())).resolve("Atlantis") is None


def test_geoadmin_failure_returns_none():
    class Broken:
        def search_communes(self, text):
            raise RuntimeError("GeoAdmin down")

    assert LocationResolver(tree(), Broken()).resolve("Musterhausen") is None


def test_empty_input_returns_none():
    assert LocationResolver(tree(), FakeGeo(())).resolve("   ") is None


def test_postal_code_inside_text_wins_over_city_name():
    geo = FakeGeo(())
    r = LocationResolver(tree(), geo).resolve("Zurich 8003")
    assert r.location.id == "CH-ZH-261-K3"
    assert r.method == "alias_scan"
    assert geo.calls == []


def test_postal_code_with_filler_words_resolves():
    r = LocationResolver(tree(), FakeGeo(())).resolve("Zurich postal code 8003")
    assert r.location.id == "CH-ZH-261-K3"


def test_scan_with_conflicting_places_falls_through_to_geoadmin():
    geo = FakeGeo(())
    r = LocationResolver(tree(), geo).resolve("Kreis 3 or Kreis 4")
    assert r is None
    assert geo.calls == ["Kreis 3 or Kreis 4"]


@pytest.mark.parametrize("name,commune_id,canton_id", [
    ("Zürich", "CH-ZH-261", "CH-ZH"),
    ("Bern", "CH-BE-351", "CH-BE"),
    ("Luzern", "CH-LU-1061", "CH-LU"),
])
def test_commune_sharing_canton_name_stays_most_specific(name, commune_id, canton_id):
    r = LocationResolver(tree(), FakeGeo(())).resolve(name)
    assert r.location.id == commune_id
    assert [a.id for a in r.alternatives] == [canton_id]


def test_quartier_leimbach_collides_with_aargau_commune_cross_path():
    result = LocationResolver(tree(), FakeGeo(())).resolve("Leimbach")
    assert isinstance(result, AmbiguousLocation)
    assert {c.id for c in result.candidates} == {"CH-ZH-261-K2-LEIMBACH", "CH-AG-4137"}


def test_marked_quartier_leimbach_resolves_to_the_quartier():
    r = LocationResolver(tree(), FakeGeo(())).resolve("Quartier Leimbach")
    assert r.location.id == "CH-ZH-261-K2-LEIMBACH"


def test_niederdorf_collides_with_basel_landschaft_commune_cross_path():
    result = LocationResolver(tree(), FakeGeo(())).resolve("Niederdorf")
    assert isinstance(result, AmbiguousLocation)
    assert {c.id for c in result.candidates} == {"CH-ZH-261-K1-RATHAUS", "CH-BL-2891"}


def test_geoadmin_hit_needs_every_token_covered():
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Zürich Oberland")
    assert r.location.id == "CH-ZH"
    assert r.method == "geoadmin_approximate"


def test_geoadmin_hit_with_unresolved_non_commune_label_returns_none():
    geo = FakeGeo((GeoAdminHit(bfs_id=0, label="Zürichsee (ZH)"),))
    assert LocationResolver(tree(), geo).resolve("Zürichsee") is None


def test_single_token_typo_resolves_against_the_tree():
    r = LocationResolver(tree(), FakeGeo(())).resolve("Winterthurr")
    assert r.location.id == "CH-ZH-230"
    assert r.method == "alias_fuzzy"


def test_trailing_country_name_keeps_the_most_specific():
    r = LocationResolver(tree(), FakeGeo(())).resolve("Zürich, Switzerland")
    assert r.location.id == "CH-ZH-261"
    assert [a.id for a in r.alternatives] == ["CH-ZH"]


def test_marker_naming_a_level_with_no_match_returns_none():
    assert LocationResolver(tree(), FakeGeo(())).resolve("Kanton Wil") is None
    assert LocationResolver(tree(), FakeGeo(())).resolve("Quartier Zürich") is None


def test_affoltern_collides_with_a_commune_name_start():
    result = LocationResolver(tree(), FakeGeo(())).resolve("Affoltern")
    assert isinstance(result, AmbiguousLocation)
    assert {"CH-ZH-261-K11-AFFOLTERN", "CH-ZH-2"} <= {c.id for c in result.candidates}


def test_zurich_airport_shares_one_token_falls_to_canton():
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Zurich Airport")
    assert r.location.id == "CH-ZH"
    assert r.method == "geoadmin_approximate"


def test_commune_with_unknown_suffix_downgrades_to_canton():
    geo = FakeGeo((GeoAdminHit(bfs_id=230, label="Winterthur (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Winterthur Töss")
    assert r.location.id == "CH-ZH"
    assert r.method == "geoadmin_approximate"


def test_lowercase_two_word_input_still_reaches_geoadmin():
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("zürich oberland")
    assert r.location.id == "CH-ZH"
    assert r.method == "geoadmin_approximate"
