from datetime import UTC, date, datetime

from swiss_grounding.corpus.calendar import OPENERZ_SOURCE, calendar_document, swiss_today

EVENTS = [
    {"date": "2026-09-17", "waste_type": "cardboard", "zip": 8003},
    {"date": "2026-10-01", "waste_type": "cardboard", "zip": 8003},
    {"date": "2026-09-16", "waste_type": "organic", "zip": 8003},
    {"date": "2026-08-01", "waste_type": "paper", "zip": 8003},
]


def test_one_document_per_zip_one_section_per_waste_type_future_dates_only():
    doc = calendar_document(8003, EVENTS, today=date(2026, 9, 10))
    assert doc.source_id == OPENERZ_SOURCE.id and doc.language == "de"
    assert doc.work_key == "openerz-8003"
    keys = [s.align_key for s in doc.sections]
    assert keys == ["cardboard", "organic"]
    cardboard = doc.sections[0]
    assert "Karton" in cardboard.text and "17.09.2026" in cardboard.text and "01.10.2026" in cardboard.text
    assert cardboard.breadcrumb == ("Abfuhrkalender Stadt Zürich", "PLZ 8003", "Karton")


def test_no_future_events_gives_no_document():
    assert calendar_document(8003, EVENTS, today=date(2027, 1, 1)) is None


def test_swiss_today_rolls_over_before_utc_midnight_in_summer():
    # 22:30 UTC in July is CEST (UTC+2): already the next day in Zürich.
    at = datetime(2026, 7, 15, 22, 30, tzinfo=UTC)
    assert swiss_today(at=at) == date(2026, 7, 16)


def test_calendar_document_skips_malformed_events():
    events = [
        {"date": "2026-09-17", "waste_type": "cardboard", "zip": 8003},
        {"waste_type": "organic", "zip": 8003},          # missing date
        {"date": "2026-09-18", "zip": 8003},              # missing waste_type
        {"date": "not-a-date", "waste_type": "paper", "zip": 8003},  # unparseable date
    ]
    doc = calendar_document(8003, events, today=date(2026, 9, 10))
    assert [s.align_key for s in doc.sections] == ["cardboard"]
