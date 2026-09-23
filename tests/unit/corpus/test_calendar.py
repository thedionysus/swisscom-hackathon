from datetime import date

from swiss_grounding.corpus.calendar import OPENERZ_SOURCE, calendar_document

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
