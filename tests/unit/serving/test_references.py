import pytest

from swiss_grounding.serving.documents import Reference, parse_reference


@pytest.mark.parametrize(("text", "expected"), [
    ("Art. 336c OR", Reference(sr="220", article="art_336_c")),
    ("art. 266c CO", Reference(sr="220", article="art_266_c")),
    ("SR 741.51 Art. 44", Reference(sr="741.51", article="art_44")),
    ("Artikel 12bis AIG", Reference(sr="142.20", article="art_12_bis")),
    ("https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_336_c",
     Reference(url="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de", article="art_336_c")),
    ("SR 220", Reference(sr="220")),
    ("Art. 8 BV", Reference(sr="101", article="art_8")),
    ("Art. 44 VZV", Reference(sr="741.51", article="art_44")),
])
def test_parses_references(text, expected):
    assert parse_reference(text) == expected


def test_unknown_abbreviation_is_none():
    assert parse_reference("Art. 5 XYZ") is None
