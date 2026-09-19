from swiss_grounding.locations.markers import strip_marker
from swiss_grounding.locations.models import Level


def test_strip_marker_recognises_german_and_english_markers():
    assert strip_marker("Gemeinde Winterthur") == (Level.MUNICIPALITY, "Winterthur")
    assert strip_marker("Stadt Zürich") == (Level.MUNICIPALITY, "Zürich")
    assert strip_marker("Kanton Zürich") == (Level.CANTON, "Zürich")
    assert strip_marker("Canton of Zurich") == (Level.CANTON, "Zurich")
    assert strip_marker("Quartier Hard") == (Level.NEIGHBORHOOD, "Hard")
    assert strip_marker("Kreis 3") == (Level.NEIGHBORHOOD, "Kreis 3")


def test_strip_marker_leaves_bare_names_alone():
    assert strip_marker("Winterthur") == (None, "Winterthur")
    assert strip_marker("Zürich, Switzerland") == (None, "Zürich, Switzerland")
