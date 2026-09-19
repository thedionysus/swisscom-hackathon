"""Pure tests of resolution_note's sentence-building, independent of the database."""
from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.coverage import resolution_note
from swiss_grounding.retrieval.models import CoverageRow


def _loc(node_id, parent, level, name, bfs=None):
    return Location(id=node_id, parent_id=parent, level=level, bfs_id=bfs, lindas_uri=None,
                    names={"en": name}, aliases=())


def _tree() -> LocationTree:
    return LocationTree.from_locations([
        _loc("CH", None, Level.COUNTRY, "Switzerland"),
        _loc("CH-ZH", "CH", Level.CANTON, "Zurich", 1),
        _loc("CH-SG", "CH", Level.CANTON, "St. Gallen", 17),
        _loc("CH-ZH-230", "CH-ZH", Level.MUNICIPALITY, "Winterthur", 230),
        _loc("CH-ZH-198", "CH-ZH", Level.MUNICIPALITY, "Wil", 198),
        _loc("CH-SG-3427", "CH-SG", Level.MUNICIPALITY, "Wil", 3427),
    ])


def test_winterthur_empty_extent_names_the_place():
    tree = _tree()
    rows = (
        CoverageRow(extent_id="CH", label="Switzerland", documents=5),
        CoverageRow(extent_id="CH-ZH", label="Zurich", documents=3),
        CoverageRow(extent_id="CH-ZH-230", label="Winterthur", documents=0),
    )
    note = resolution_note(rows, tree, "Winterthur", tree.get("CH-ZH-230"), "alias", ())
    assert note == "No documents indexed for Winterthur; evidence comes from parent jurisdictions."


def test_approximate_resolution_names_the_input_and_the_canton():
    tree = _tree()
    rows = (
        CoverageRow(extent_id="CH", label="Switzerland", documents=5),
        CoverageRow(extent_id="CH-ZH", label="Zurich", documents=3),
    )
    note = resolution_note(rows, tree, "Wetzikon", tree.get("CH-ZH"), "geoadmin_approximate", ())
    assert note == "'Wetzikon' was not recognised below canton level; answered at Zurich (canton)."


def test_alternative_reading_names_input_alt_and_chosen():
    tree = _tree()
    rows = (
        CoverageRow(extent_id="CH", label="Switzerland", documents=5),
        CoverageRow(extent_id="CH-ZH", label="Zurich", documents=3),
        CoverageRow(extent_id="CH-ZH-198", label="Wil", documents=2),
    )
    note = resolution_note(
        rows, tree, "Wil", tree.get("CH-ZH-198"), "alias", (tree.get("CH-SG-3427"),),
    )
    assert note == (
        "'Wil' could also mean Wil (municipality, St. Gallen); "
        "this answer used Wil (municipality, Zurich)."
    )
