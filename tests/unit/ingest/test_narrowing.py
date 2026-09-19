import pytest

from swiss_grounding.ingest.narrowing import narrow_extent
from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree


def _loc(id, parent_id, level, name, *aliases):
    return Location(id=id, parent_id=parent_id, level=level, bfs_id=None, lindas_uri=None,
                     names={"en": name, "de": name}, aliases=aliases)


@pytest.fixture
def tree():
    locations = [
        _loc("CH", None, Level.COUNTRY, "Switzerland"),
        _loc("CH-ZH", "CH", Level.CANTON, "Zürich"),
        _loc("CH-BE", "CH", Level.CANTON, "Bern"),
        _loc("CH-ZH-261", "CH-ZH", Level.MUNICIPALITY, "Zürich"),
        _loc("CH-ZH-261-K1", "CH-ZH-261", Level.NEIGHBORHOOD, "Kreis 1"),
        _loc("CH-ZH-261-K1-CITY", "CH-ZH-261-K1", Level.NEIGHBORHOOD, "City"),
        _loc("CH-ZH-261-K3", "CH-ZH-261", Level.NEIGHBORHOOD, "Kreis 3", "8003"),
        _loc("CH-ZH-261-K3-ALT-WIEDIKON", "CH-ZH-261-K3", Level.NEIGHBORHOOD, "Alt-Wiedikon", "Wiedikon"),
        _loc("CH-ZH-261-K8", "CH-ZH-261", Level.NEIGHBORHOOD, "Kreis 8"),
        _loc("CH-ZH-261-K8-SEEFELD", "CH-ZH-261-K8", Level.NEIGHBORHOOD, "Seefeld"),
        _loc("CH-BE-351", "CH-BE", Level.MUNICIPALITY, "Bern", "Stadt Bern"),
        _loc("CH-ZH-295", "CH-ZH", Level.MUNICIPALITY, "Wald"),
        _loc("CH-ZH-241", "CH-ZH", Level.MUNICIPALITY, "Affoltern am Albis"),
        _loc("CH-ZH-261-K11", "CH-ZH-261", Level.NEIGHBORHOOD, "Kreis 11"),
        _loc("CH-ZH-261-K11-AFFOLTERN", "CH-ZH-261-K11", Level.NEIGHBORHOOD, "Affoltern"),
    ]
    return LocationTree.from_locations(locations)


def test_bare_ancestor_name_in_body_never_narrows(tree):
    extent, reason = narrow_extent(tree, "CH-ZH", title="Hunde", headings=(), text="Im Kanton Zürich gilt ... Zürich ...")
    assert extent == "CH-ZH" and reason == "source_default"


def test_marker_in_body_narrows(tree):
    extent, reason = narrow_extent(tree, "CH-ZH", title="Hunde", headings=(), text="In der Stadt Zürich gilt Leinenpflicht.")
    assert extent == "CH-ZH-261" and reason.startswith("narrowed:marker:")


def test_bare_name_in_title_narrows(tree):
    extent, reason = narrow_extent(tree, "CH-ZH-261", title="Hundezone Wiedikon", headings=(), text="...")
    assert extent == "CH-ZH-261-K3-ALT-WIEDIKON" and reason.startswith("narrowed:title:")


def test_bare_name_in_heading_narrows(tree):
    extent, _ = narrow_extent(tree, "CH-ZH-261", title="Parks", headings=("Seefeld",), text="...")
    assert extent == "CH-ZH-261-K8-SEEFELD"


def test_common_word_quartier_needs_marker_even_in_title(tree):
    assert narrow_extent(tree, "CH-ZH-261", title="City Guide", headings=(), text="")[0] == "CH-ZH-261"
    assert narrow_extent(tree, "CH-ZH-261", title="Quartier City", headings=(), text="")[0] == "CH-ZH-261-K1-CITY"


def test_bare_postal_code_in_body_never_narrows(tree):
    extent, reason = narrow_extent(tree, "CH", title="Info", headings=(), text="Im Jahr 1846 und 2026 geschah etwas.")
    assert extent == "CH" and reason == "source_default"


def test_postal_code_with_context_in_body_narrows(tree):
    assert narrow_extent(tree, "CH-ZH-261", title="Sammlung", headings=(), text="PLZ 8003")[0] == "CH-ZH-261-K3"


def test_postal_code_in_title_narrows(tree):
    assert narrow_extent(tree, "CH-ZH-261", title="Sammlung 8003", headings=(), text="")[0] == "CH-ZH-261-K3"


def test_canton_marker_in_body_narrows_country_page_to_canton(tree):
    extent, reason = narrow_extent(tree, "CH", title="Info", headings=(), text="Im Kanton Zürich gilt ...")
    assert extent == "CH-ZH"
    assert "marker:Kanton Zürich" in reason


def test_english_markers_narrow_translated_text(tree):
    extent, reason = narrow_extent(tree, "CH-ZH", title="Info", headings=(), text="In the municipality of Wald, rules apply.")
    assert extent == "CH-ZH-295"
    assert "marker:municipality of Wald" in reason


def test_two_word_marker_selects_by_level_not_deepest(tree):
    extent, reason = narrow_extent(tree, "CH-ZH-261", title="Info", headings=(), text="canton of Zurich has rules")
    assert extent == "CH-ZH-261" and reason == "source_default"


def test_district_marker_narrows_like_kreis(tree):
    extent, reason = narrow_extent(tree, "CH-ZH-261", title="Info", headings=(), text="District 3 collects waste on Fridays.")
    assert extent == "CH-ZH-261-K3"
    assert "marker:District 3" in reason


def test_three_word_marker_name_beats_one_word_quartier(tree):
    extent, reason = narrow_extent(tree, "CH-ZH", title="Gemeinde Affoltern am Albis", headings=(), text="")
    assert extent == "CH-ZH-241"
    assert "marker:Gemeinde Affoltern am Albis" in reason


def test_two_mentions_narrow_to_common_ancestor(tree):
    extent, _ = narrow_extent(tree, "CH-ZH-261", title="Wiedikon und Seefeld", headings=(), text="")
    assert extent == "CH-ZH-261"


def test_common_word_commune_needs_marker_even_in_heading(tree):
    assert narrow_extent(tree, "CH-ZH", title="Info", headings=("Wald",), text="")[0] == "CH-ZH"
    assert narrow_extent(tree, "CH-ZH", title="Info", headings=("Gemeinde Wald",), text="")[0] == "CH-ZH-295"


def test_never_widens_or_moves_sideways(tree):
    assert narrow_extent(tree, "CH-ZH-261", title="Kanton Zürich", headings=(), text="")[0] == "CH-ZH-261"
    assert narrow_extent(tree, "CH-ZH", title="Stadt Bern", headings=(), text="")[0] == "CH-ZH"
