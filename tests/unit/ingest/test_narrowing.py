from swiss_grounding.ingest.narrowing import narrow_extent
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree

TREE = LocationTree.from_locations(seed_locations())


def test_narrows_to_single_descendant():
    text = "The Uetliberg trail starts in Zurich. Dogs must be leashed in Zurich forests."
    extent, reason = narrow_extent(TREE, default_extent_id="CH", text=text)
    assert extent == "CH-ZH-261"
    assert reason.startswith("narrowed:")


def test_narrows_to_deepest_common_ancestor_of_several_mentions():
    text = "Parks in Wiedikon and Altstetten, both in Zurich, have off-leash zones."
    extent, _ = narrow_extent(TREE, default_extent_id="CH", text=text)
    assert extent == "CH-ZH-261"


def test_keeps_default_when_mentions_span_siblings():
    text = "Rules differ between Basel and Geneva."
    assert narrow_extent(TREE, "CH", text) == ("CH", "source_default")


def test_never_widens():
    text = "This page mentions Switzerland and Bern."
    assert narrow_extent(TREE, "CH-ZH", text) == ("CH-ZH", "source_default")


def test_ignores_two_letter_abbreviations_and_lowercase_words():
    text = "So be it: we ai for the best. The city is nice."
    assert narrow_extent(TREE, "CH", text) == ("CH", "source_default")


def test_no_mentions_keeps_default():
    assert narrow_extent(TREE, "CH-ZH", "Nothing geographic here.") == ("CH-ZH", "source_default")


def test_canton_default_narrows_to_city_on_city_mention():
    text = "Stadt Zürich: Hunde in Parks an der Leine führen."
    extent, _ = narrow_extent(TREE, "CH-ZH", text)
    assert extent == "CH-ZH-261"
