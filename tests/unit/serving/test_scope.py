from swiss_grounding.serving.scope import (
    SCOPE_CANTONS,
    SCOPE_MUNICIPALITIES,
    covered_levels,
    scope_statement,
)


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
