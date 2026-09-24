"""OpenERZ (Stadt Zürich waste collection) as corpus documents: one per postal code."""
from collections.abc import Sequence
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import httpx

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec

SWISS_TZ = ZoneInfo("Europe/Zurich")
OPENERZ_URL = "https://openerz.metaodi.ch/api/calendar"
ZURICH_ZIPS: tuple[int, ...] = (8001, 8002, 8003, 8004, 8005, 8006, 8008, 8032, 8037, 8038, 8041, 8044, 8045,
                                8046, 8047, 8048, 8049, 8050, 8051, 8052, 8053, 8055, 8057, 8064)
WASTE_DE: dict[str, str] = {
    "cardboard": "Karton", "paper": "Papier", "organic": "Grüngut", "textile": "Textilien",
    "special": "Sonderabfall (Mobil)", "mobile": "Sonderabfall (Mobil)", "cargotram": "Cargo-Tram",
    "etram": "E-Tram", "waste": "Kehricht", "incombustibles": "Unbrennbares", "metal": "Metall",
    "bulky_goods": "Sperrgut", "chipping_service": "Häckseldienst",
}
OPENERZ_SOURCE = SourceSpec(
    id="open_erz", name="Abfuhrkalender Stadt Zürich (OpenERZ)", publisher="Entsorgung + Recycling Zürich",
    authority="official_info", level="municipal", extent_id="CH-ZH-261", connector="html", tier=1,
    languages=("de",), config={"kind": "openerz"}, retrieved_via="openerz.metaodi.ch")
MAX_DATES = 26


def _format(d: str) -> str:
    return date.fromisoformat(d).strftime("%d.%m.%Y")


def _valid_events(events: Sequence[dict]) -> list[dict]:
    """Drop events missing `date`/`waste_type` or whose date is not a valid ISO date.

    OpenERZ is an external API; malformed rows are quarantined here rather than raised, so
    one bad row does not fail an entire zip's calendar.
    """
    valid = []
    for e in events:
        raw_date, waste_type = e.get("date"), e.get("waste_type")
        if not raw_date or not waste_type:
            continue
        try:
            date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            continue
        valid.append(e)
    return valid


def calendar_document(zip_code: int, events: Sequence[dict], today: date) -> ParsedDocument | None:
    by_type: dict[str, list[str]] = {}
    for e in sorted(_valid_events(events), key=lambda e: e["date"]):
        if date.fromisoformat(e["date"]) >= today:
            by_type.setdefault(e["waste_type"], []).append(e["date"])
    if not by_type:
        return None
    sections = []
    for waste, dates in sorted(by_type.items()):
        label = WASTE_DE.get(waste, waste)
        text = (f"{label}-Abfuhr in Zürich, Postleitzahl {zip_code}. Nächste Termine: "
                f"{', '.join(_format(d) for d in dates[:MAX_DATES])}. Am Abfuhrtag bis 7 Uhr bereitstellen.")
        sections.append(ParsedSection(align_key=waste, breadcrumb=("Abfuhrkalender Stadt Zürich", f"PLZ {zip_code}",
                                                                    label), anchor=waste, text=text))
    return ParsedDocument(source_id=OPENERZ_SOURCE.id, url=f"{OPENERZ_URL}?region=zurich&zip={zip_code}",
                           language="de", work_key=f"openerz-{zip_code}",
                           title=f"Abfuhrkalender Stadt Zürich, PLZ {zip_code}", sections=tuple(sections),
                           modified_at=today)


def fetch_events(client: httpx.Client, zip_code: int, start: date) -> list[dict]:
    params = {"region": "zurich", "zip": zip_code, "start": start.isoformat(), "sort": "date", "limit": 500}
    response = client.get(OPENERZ_URL, params=params)
    response.raise_for_status()
    return response.json()["result"]


def now() -> datetime:
    return datetime.now(UTC)


def swiss_today(at: datetime | None = None) -> date:
    """The civil date in Zürich, used as the future/past cutoff for calendar events.

    A UTC instant close to midnight can fall on a different calendar date in Zürich (e.g.
    22:30 UTC is already the next day in Swiss summer time), so the cutoff must be computed
    in local time rather than from `now().date()`.
    """
    instant = at if at is not None else now()
    return instant.astimezone(SWISS_TZ).date()
