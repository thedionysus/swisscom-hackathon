from datetime import UTC, date, datetime

from swiss_grounding.cli.main import _citation_line, _link
from swiss_grounding.retrieval.models import Citation


def test_link_appends_anchor():
    assert _link("https://x/y", "art_6") == "https://x/y#art_6"


def test_link_keeps_existing_fragment():
    assert _link("https://x/y#art_6", "art_6") == "https://x/y#art_6"


def test_link_without_anchor():
    assert _link("https://x/y", None) == "https://x/y"


def _citation(tier: int | None, distance: float | None, event_date: date | None = None) -> Citation:
    return Citation(
        chunk_id=1, document_id=1, source_id="s", title_en="Dogs", title_original="Hunde",
        url="https://x", anchor=None, identifier=None, snippet_en="e", snippet_original="o",
        language="de", heading_path="", extent_id="CH-ZH", extent_label="Zurich",
        authority="official_info", categories=(), valid_from=None,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC), license=None,
        tier=tier, distance=distance, event_date=event_date,
    )


def test_citation_line_shows_the_tier_and_the_distance():
    """The CLI prints what the citation now carries. `score` is gone, and the two
    numbers that replace it are both lower-is-better."""
    line = _citation_line(1, _citation(tier=0, distance=0.4321))
    assert "tier 0" in line
    assert "distance 0.4321" in line
    assert "score" not in line


def test_citation_line_says_so_rather_than_printing_none():
    """An unclaimed tier and an unmeasured distance are real outcomes; printing a bare
    `None` beside a number would read as a value."""
    line = _citation_line(2, _citation(tier=None, distance=None))
    assert "None" not in line
    assert "no tier" in line
    assert "distance not measured" in line


def test_citation_line_keeps_the_event_date():
    line = _citation_line(1, _citation(tier=1, distance=0.5, event_date=date(2026, 9, 17)))
    assert "event on 2026-09-17" in line
