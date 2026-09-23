"""swiss_reference_rate: the mortgage reference interest rate from BWO, with its effective date."""
import json
import re
from datetime import UTC, date, datetime, timedelta

import httpx
import psycopg
from bs4 import BeautifulSoup

CACHE_KEY = "reference_rate"
CACHE_MAX_AGE = timedelta(hours=24)
RATE = re.compile(r"Referenzzinssatz[^%]{0,80}?(\d+[.,]\d{1,2})\s*%", re.IGNORECASE)
MONTHS = {m: i for i, m in enumerate(["januar", "februar", "märz", "april", "mai", "juni", "juli", "august",
                                      "september", "oktober", "november", "dezember"], start=1)}
DATE_WORDS = re.compile(r"(\d{1,2})\.\s*(" + "|".join(MONTHS) + r")\s+(\d{4})", re.IGNORECASE)
DATE_DOTS = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
UNAVAILABLE = "The BWO page could not be reached ({reason}); showing the last value retrieved on {when}."
UNAVAILABLE_NO_CACHE = "The BWO page could not be reached ({reason}) and no earlier value is stored."


def _first_date(text: str) -> date | None:
    if m := DATE_WORDS.search(text):
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
    if m := DATE_DOTS.search(text):
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def parse_rate(html: str) -> tuple[float, date | None] | None:
    text = " ".join(BeautifulSoup(html, "html.parser").get_text(" ").split())
    m = RATE.search(text)
    if m is None:
        return None
    return float(m.group(1).replace(",", ".")), _first_date(text[m.end(): m.end() + 200])


def _cached(conn) -> dict | None:
    return conn.execute("select value, reference_date, source_url, fetched_at from serving.lookup_cache "
                        "where key = %s", (CACHE_KEY,)).fetchone()


def reference_rate(conn: psycopg.Connection, client: httpx.Client, url: str,
                   max_age: timedelta = CACHE_MAX_AGE) -> dict:
    """The rate changes at most quarterly: a value younger than max_age is served without a fetch."""
    row = _cached(conn)
    if row is not None and max(datetime.now(UTC) - row["fetched_at"], timedelta(0)) < max_age:
        return {"status": "results", **row["value"], "effective_date": row["reference_date"],
                "source_url": row["source_url"], "retrieved_at": row["fetched_at"],
                "publisher": "Bundesamt für Wohnungswesen BWO"}
    try:
        response = client.get(url)
        response.raise_for_status()
        parsed = parse_rate(response.text)
        if parsed is None:
            raise ValueError("page no longer states the rate")
    except (httpx.HTTPError, ValueError) as exc:
        reason = type(exc).__name__ if isinstance(exc, httpx.HTTPError) else str(exc)
        row = _cached(conn)
        if row is None:
            return {"status": "source_unavailable", "message": UNAVAILABLE_NO_CACHE.format(reason=reason),
                    "source_url": url}
        return {"status": "source_unavailable", **row["value"], "effective_date": row["reference_date"],
                "source_url": row["source_url"], "retrieved_at": row["fetched_at"],
                "message": UNAVAILABLE.format(reason=reason, when=row["fetched_at"].date().isoformat())}
    rate, effective = parsed
    conn.execute("insert into serving.lookup_cache (key, value, reference_date, source_url, fetched_at) "
                 "values (%s, %s, %s, %s, now()) on conflict (key) do update set value = excluded.value, "
                 "reference_date = excluded.reference_date, source_url = excluded.source_url, fetched_at = now()",
                 (CACHE_KEY, json.dumps({"rate_percent": rate}), effective, url))
    return {"status": "results", "rate_percent": rate, "effective_date": effective, "source_url": url,
            "publisher": "Bundesamt für Wohnungswesen BWO"}
