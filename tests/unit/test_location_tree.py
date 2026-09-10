import pytest

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree


def small_tree() -> LocationTree:
    return LocationTree.from_locations([
        Location(id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None, lindas_uri=None,
                 names={"en": "Switzerland", "de": "Schweiz"}, aliases=("Swiss",)),
        Location(id="CH-ZH", parent_id="CH", level=Level.CANTON, bfs_id=1, lindas_uri=None,
                 names={"en": "Zurich", "de": "Zürich"}, aliases=("ZH", "Kanton Zürich")),
        Location(id="CH-ZH-261", parent_id="CH-ZH", level=Level.MUNICIPALITY, bfs_id=261,
                 lindas_uri=None, names={"en": "Zurich", "de": "Zürich"}, aliases=("Stadt Zürich",)),
        Location(id="CH-ZH-261-K3", parent_id="CH-ZH-261", level=Level.NEIGHBORHOOD, bfs_id=None,
                 lindas_uri=None, names={"de": "Kreis 3"}, aliases=("Wiedikon", "8003")),
        Location(id="CH-BS", parent_id="CH", level=Level.CANTON, bfs_id=12, lindas_uri=None,
                 names={"en": "Basel-Stadt"}, aliases=("BS",)),
    ])


def test_path_is_ancestors_including_self():
    t = small_tree()
    assert t.path("CH-ZH-261-K3") == ("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3")
    assert t.path("CH") == ("CH",)


def test_distance_between_node_and_ancestor():
    t = small_tree()
    assert t.distance("CH-ZH-261-K3", "CH-ZH-261-K3") == 0
    assert t.distance("CH-ZH-261-K3", "CH-ZH") == 2
    assert t.distance("CH-ZH-261-K3", "CH") == 3


def test_distance_to_non_ancestor_is_none():
    t = small_tree()
    assert t.distance("CH-ZH-261-K3", "CH-BS") is None


def test_find_by_alias_is_case_and_accent_insensitive():
    t = small_tree()
    assert [m.id for m in t.find("wiedikon")] == ["CH-ZH-261-K3"]
    assert [m.id for m in t.find("kanton zurich")] == ["CH-ZH"]
    assert [m.id for m in t.find("8003")] == ["CH-ZH-261-K3"]


def test_find_ambiguous_returns_most_specific_first():
    t = small_tree()
    ids = [m.id for m in t.find("Zürich")]
    assert ids == ["CH-ZH-261", "CH-ZH"]


def test_find_unknown_returns_empty():
    assert small_tree().find("Atlantis") == ()


def test_by_bfs_id():
    t = small_tree()
    assert t.by_bfs_id(261).id == "CH-ZH-261"
    assert t.by_bfs_id(999) is None


def test_unknown_id_raises():
    with pytest.raises(KeyError):
        small_tree().path("nope")
