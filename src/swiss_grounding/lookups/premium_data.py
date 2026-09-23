"""Read the BAG premium table and premium regions; load them into serving.premium*.

Column names and codes are those of the 2026 BAG export (`Prämien_CH.csv`, inside
`Archiv_Praemien_2026.zip` on https://opendata.swiss/de/dataset/health-insurance-premiums,
served from opendata.bagnet.ch): comma-delimited, UTF-8 with a BOM. The premium-region
list (`Anhang der EDI Verordnung über die Prämienregionen`, published as XLSX only on
https://www.bag.admin.ch/de/krankenversicherung-praemienregionen) was converted to a
semicolon-delimited CSV with:

    uv run --with openpyxl python -c "
    import openpyxl, csv
    wb = openpyxl.load_workbook('data/premium/regions_2026.xlsx', data_only=True)
    ws = wb['Anhang EDI Ver. über die PR']
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    header_idx = next(i for i, r in enumerate(rows) if r[0] and 'Kanton' in str(r[0]))
    data = rows[header_idx + 1:]
    with open('data/premium/regions_2026.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['Kanton', 'BFS-Nr.', 'Gemeinde', 'Region'])
        for r in data:
            if r[0] is not None and r[1] is not None:
                w.writerow([r[0], r[1], r[2], r[3]])
    "

No insurer-name list ships in the premium dataset: `Versicherer` is a numeric code
everywhere (`Prämien_CH.csv`, `Tarife.csv`, `Einzugsgebiete.csv`, `Versichertenbestand_CH.csv`).
Callers that want names pass an external map (e.g. the BAG insurer register) via
`insurer_names`; unmapped codes fall back to the code itself.
"""
import csv
from collections.abc import Iterator, Mapping
from dataclasses import astuple, dataclass
from pathlib import Path

import psycopg

SOURCE_URL = "https://opendata.swiss/de/dataset/health-insurance-premiums"
COLUMNS = {"insurer": "Versicherer", "canton": "Kanton", "region": "Region", "age": "Altersklasse",
           "accident": "Unfalleinschluss", "year": "Geschäftsjahr", "model": "Tariftyp",
           "label": "Tarifbezeichnung", "deductible": "Franchise", "premium": "Prämie"}
AGE = {"AKL-KIN": "child", "AKL-JUG": "young_adult", "AKL-ERW": "adult"}
MODEL = {"TAR-BASE": "standard", "TAR-HAM": "family_doctor", "TAR-HMO": "hmo", "TAR-DIV": "other"}
CHILD_MAX_AGE = 18
YOUNG_ADULT_MAX_AGE = 25
PREMIUM_DELIMITER = ","   # Prämien_CH.csv, as published by BAG
REGION_DELIMITER = ";"    # our conversion of the XLSX region list


@dataclass(frozen=True)
class PremiumRow:
    year: int
    insurer_id: str
    insurer_name: str
    canton: str
    region: int
    age_class: str
    accident: bool
    model: str
    model_label: str
    deductible: int
    premium_chf: float
    source_url: str = SOURCE_URL


@dataclass(frozen=True)
class RegionRow:
    year: int
    bfs_id: int
    canton: str
    region: int


def age_class(age: int) -> str:
    if age <= CHILD_MAX_AGE:
        return "child"
    return "young_adult" if age <= YOUNG_ADULT_MAX_AGE else "adult"


def _rows(path: Path, delimiter: str) -> Iterator[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f, delimiter=delimiter)


def _model(code: str, label: str) -> str:
    model = MODEL.get(code, "other")
    return "telmed" if model == "other" and "tel" in label.lower() else model


def read_premiums(path: Path, insurer_names: Mapping[str, str]) -> Iterator[PremiumRow]:
    c = COLUMNS
    for r in _rows(path, PREMIUM_DELIMITER):
        insurer = r[c["insurer"]].strip()
        yield PremiumRow(
            year=int(r[c["year"]]), insurer_id=insurer, insurer_name=insurer_names.get(insurer, insurer),
            canton=r[c["canton"]].strip(), region=int(r[c["region"]].rsplit("CH", 1)[1]),
            age_class=AGE[r[c["age"]].strip()], accident=r[c["accident"]].strip() == "MIT-UNF",
            model=_model(r[c["model"]].strip(), r[c["label"]]), model_label=r[c["label"]].strip(),
            deductible=int(r[c["deductible"]].removeprefix("FRA-")), premium_chf=float(r[c["premium"]]))


def read_regions(path: Path, year: int) -> Iterator[RegionRow]:
    for r in _rows(path, REGION_DELIMITER):
        yield RegionRow(year, int(r["BFS-Nr."]), r["Kanton"].strip(), int(r["Region"]))


def load_premiums(conn: psycopg.Connection, premiums: Path, regions: Path, year: int,
                  insurer_names: Mapping[str, str]) -> tuple[int, int]:
    conn.execute("delete from serving.premium where year = %s", (year,))
    conn.execute("delete from serving.premium_region where year = %s", (year,))
    prem = [astuple(p) for p in read_premiums(premiums, insurer_names) if p.year == year]
    regs = [astuple(r) for r in read_regions(regions, year)]
    with conn.cursor() as cur:
        cur.executemany("insert into serving.premium (year, insurer_id, insurer_name, canton, region, age_class, "
                        "accident, model, model_label, deductible, premium_chf, source_url) "
                        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", prem)
        cur.executemany("insert into serving.premium_region (year, bfs_id, canton, region) values (%s,%s,%s,%s)",
                        regs)
    return len(prem), len(regs)
