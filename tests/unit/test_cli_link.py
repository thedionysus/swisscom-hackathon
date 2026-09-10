from swiss_grounding.cli.main import _link


def test_link_appends_anchor():
    assert _link("https://x/y", "art_6") == "https://x/y#art_6"


def test_link_keeps_existing_fragment():
    assert _link("https://x/y#art_6", "art_6") == "https://x/y#art_6"


def test_link_without_anchor():
    assert _link("https://x/y", None) == "https://x/y"
