from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree


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
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Zurich centre")
    assert r.location.id == "CH-ZH-261"
    assert r.method == "geoadmin"


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
