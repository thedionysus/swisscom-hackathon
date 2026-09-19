"""Fetch the commune register from the BFS AGVCH API and postal codes from LINDAS.

Network only; the result is written to the committed snapshot by the CLI."""
import csv
import io
from collections.abc import Mapping, Sequence
from datetime import date

import httpx

from swiss_grounding.locations.register import Commune

AGVCH_URL = "https://www.agvchapp.bfs.admin.ch/api/communes/snapshot"
LINDAS_URL = "https://ld.admin.ch/query"
LINDAS_PLZ_QUERY = """
PREFIX schema: <http://schema.org/>
SELECT ?id ?postalCode WHERE {
  ?m a <https://schema.ld.admin.ch/PoliticalMunicipality> ; schema:identifier ?id ; schema:postalCode ?postalCode .
}
"""
LEVEL_CANTON, LEVEL_COMMUNE = "1", "3"
TIMEOUT = 60.0
MAX_PARENT_HOPS = 5


def parse_agvch(text: str) -> tuple[Commune, ...]:
    """Communes from an AGVCH snapshot; canton found by walking Parent to the Level 1 row."""
    rows = list(csv.DictReader(io.StringIO(text)))
    by_hist = {r["HistoricalCode"]: r for r in rows}

    def parent_of(row: Mapping[str, str]) -> Mapping[str, str]:
        parent = by_hist.get(row["Parent"])
        if parent is None:
            raise ValueError(f"AGVCH row {row['BfsCode']} {row['Name']}: parent {row['Parent']!r} not in snapshot")
        return parent

    def canton_of(row: Mapping[str, str]) -> str:
        current = row
        for _ in range(MAX_PARENT_HOPS):
            if current["Level"] == LEVEL_CANTON:
                return current["ShortName"]
            current = parent_of(current)
        raise ValueError(f"AGVCH row {row['BfsCode']} {row['Name']}: parent {row['Parent']!r} not in snapshot")

    communes = []
    for r in rows:
        if r["Level"] != LEVEL_COMMUNE:
            continue
        district = parent_of(r)["Name"]
        communes.append(Commune(bfs_id=int(r["BfsCode"]), name=r["Name"], canton=canton_of(r),
                                district=district, postal_codes=()))
    return tuple(sorted(communes, key=lambda c: c.bfs_id))


def parse_lindas_plz(text: str) -> dict[int, tuple[str, ...]]:
    grouped: dict[int, list[str]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        if not r["postalCode"]:
            continue
        grouped.setdefault(int(r["id"]), []).append(r["postalCode"])
    return {k: tuple(sorted(set(v))) for k, v in grouped.items()}


def merge_snapshot(communes: Sequence[Commune], plz: Mapping[int, tuple[str, ...]]) -> tuple[Commune, ...]:
    return tuple(Commune(c.bfs_id, c.name, c.canton, c.district, plz.get(c.bfs_id, ())) for c in communes)


def fetch_register(snapshot_date: date) -> tuple[Commune, ...]:
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as http:
        agvch = http.get(AGVCH_URL, params={"date": snapshot_date.strftime("%d-%m-%Y")})
        agvch.raise_for_status()
        lindas = http.post(LINDAS_URL, data={"query": LINDAS_PLZ_QUERY}, headers={"Accept": "text/csv"})
        lindas.raise_for_status()
    communes = parse_agvch(agvch.text)
    if not communes:
        raise ValueError("AGVCH snapshot returned no communes")
    plz = parse_lindas_plz(lindas.text)
    if not plz:
        raise ValueError("LINDAS returned no postal codes")
    return merge_snapshot(communes, plz)
