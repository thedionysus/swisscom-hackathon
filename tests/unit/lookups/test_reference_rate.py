from datetime import date

from swiss_grounding.lookups.reference_rate import parse_rate

HTML = """<html><body><h1>Referenzzinssatz</h1>
<p>Der hypothekarische Referenzzinssatz beträgt 1,25 % und gilt seit dem 2. September 2025.</p>
<p>Nächste Publikation: 1. Dezember 2025</p></body></html>"""


def test_parses_rate_and_effective_date():
    assert parse_rate(HTML) == (1.25, date(2025, 9, 2))


def test_returns_none_when_the_page_changed_shape():
    assert parse_rate("<html>Wartung</html>") is None


def test_real_page_fixture_parses():
    from pathlib import Path
    parsed = parse_rate(Path("tests/fixtures/bwo_referenzzinssatz.html").read_text(encoding="utf-8"))
    assert parsed is not None and 0 < parsed[0] < 10
