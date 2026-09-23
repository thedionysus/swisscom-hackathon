"""swiss_connections: public transport connections from transport.opendata.ch (keyless, live)."""
from datetime import UTC, datetime

import httpx

SOURCE_URL = "https://transport.opendata.ch"
UNAVAILABLE = ("The Swiss timetable service could not be reached ({reason}). No connection data is shown; "
               "try again later or check sbb.ch.")
MAX_LIMIT = 6


def _trim(c: dict) -> dict:
    return {"departure": c["from"]["departure"], "arrival": c["to"]["arrival"],
            "from": c["from"]["station"]["name"], "to": c["to"]["station"]["name"],
            "platform": c["from"].get("platform"), "duration": c.get("duration"),
            "transfers": c.get("transfers"), "products": c.get("products", [])}


def find_connections(client: httpx.Client, *, origin: str, destination: str, date: str | None, time: str | None,
                     limit: int) -> dict:
    params = {"from": origin, "to": destination, "limit": max(1, min(limit, MAX_LIMIT))}
    params |= {k: v for k, v in (("date", date), ("time", time)) if v}
    try:
        response = client.get("/connections", params=params)
        response.raise_for_status()
        found = response.json().get("connections", [])
    except (httpx.HTTPError, ValueError) as exc:
        return {"status": "source_unavailable", "message": UNAVAILABLE.format(reason=type(exc).__name__),
                "source_url": SOURCE_URL}
    status = "results" if found else "no_evidence"
    return {"status": status, "connections": [_trim(c) for c in found], "source_url": SOURCE_URL,
            "retrieved_at": datetime.now(UTC).isoformat()}
