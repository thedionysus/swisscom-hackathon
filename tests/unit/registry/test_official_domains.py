from swiss_grounding.registry.official_domains import classify_domain, extent_for_domain


def test_admin_ch_and_ch_ch_are_federal_official():
    assert classify_domain("https://www.bafu.admin.ch/x") == "official"
    assert extent_for_domain("https://www.bafu.admin.ch/x") == "CH"
    assert extent_for_domain("https://www.ch.ch/en/dogs") == "CH"


def test_cantonal_and_city_domains():
    assert extent_for_domain("https://www.zh.ch/de/x") == "CH-ZH"
    assert extent_for_domain("https://www.bs.ch/x") == "CH-BS"
    assert extent_for_domain("https://www.stadt-zuerich.ch/x") == "CH-ZH-261"
    assert classify_domain("https://www.stadt-zuerich.ch/x") == "official"


def test_swiss_and_other():
    assert classify_domain("https://www.schweizer-wanderwege.ch/x") == "swiss"
    assert classify_domain("https://www.example.com/x") == "other"
    assert extent_for_domain("https://www.example.com/x") is None
