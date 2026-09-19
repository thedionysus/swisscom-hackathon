from swiss_grounding.locations.models import Level
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree


def test_seed_has_country_and_26_cantons():
    locs = seed_locations()
    assert sum(1 for l in locs if l.level == Level.COUNTRY) == 1
    assert sum(1 for l in locs if l.level == Level.CANTON) == 26


def test_seed_has_zurich_city_12_kreise_34_quartiere():
    locs = seed_locations()
    tree = LocationTree.from_locations(locs)
    assert tree.by_bfs_id(261).id == "CH-ZH-261"
    kreise = [l for l in locs if l.parent_id == "CH-ZH-261"]
    assert len(kreise) == 12
    quartiere = [l for l in locs if l.level == Level.NEIGHBORHOOD and l.parent_id.startswith("CH-ZH-261-K")]
    assert len(quartiere) == 34


def test_seed_ids_are_unique_and_parents_exist():
    locs = seed_locations()
    ids = [l.id for l in locs]
    assert len(ids) == len(set(ids))
    for l in locs:
        assert l.parent_id is None or l.parent_id in ids


def test_seed_aliases_resolve():
    tree = LocationTree.from_locations(seed_locations())
    assert tree.find("Wiedikon")[0].id == "CH-ZH-261-K3-ALT-WIEDIKON"
    assert tree.find("Kreis 3")[0].id == "CH-ZH-261-K3"
    assert tree.find("8003")[0].id == "CH-ZH-261-K3"
    assert tree.find("Genève")[0].id == "CH-GE-6621"
    assert tree.find("Kanton Genf")[0].id == "CH-GE"
    assert tree.find("Basel")[0].id == "CH-BS-2701"
    assert tree.find("Kanton Basel-Stadt")[0].id == "CH-BS"


def test_seed_includes_every_commune_under_its_canton():
    from swiss_grounding.locations.register import load_register
    from swiss_grounding.locations.seed import seed_locations
    locs = {l.id: l for l in seed_locations()}
    register = load_register()
    assert len(register) > 2000
    for c in register:
        if c.bfs_id == 261:
            assert locs["CH-ZH-261"].level.value == "municipality"
            continue
        node = locs[f"CH-{c.canton}-{c.bfs_id}"]
        assert node.parent_id == f"CH-{c.canton}"
    assert locs["CH-ZH-230"].names["de"] == "Winterthur"
    assert "8400" in locs["CH-ZH-230"].aliases
