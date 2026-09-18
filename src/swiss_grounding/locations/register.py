"""The commune register: every Swiss commune as a Location under its canton.

Read from the committed snapshot `data/communes.csv`; regenerate it with
`swiss-grounding locations fetch-register`. Pure: no network, no database."""
import csv
import io
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from swiss_grounding.locations.models import Level, Location

SNAPSHOT = Path(__file__).resolve().parent / "data" / "communes.csv"
COLUMNS = ("bfs_id", "name", "canton", "district", "postal_codes")
PLZ_SEPARATOR = "|"
CANTON_SUFFIX = re.compile(r"\s*\(([A-Z]{2})\)\s*$")
LINDAS_MUNICIPALITY = "https://ld.admin.ch/municipality/{bfs_id}"


@dataclass(frozen=True)
class Commune:
    bfs_id: int
    name: str            # as in the register, e.g. "Wil (SG)"
    canton: str          # two-letter abbreviation
    district: str
    postal_codes: tuple[str, ...]


def parse_register_csv(text: str) -> tuple[Commune, ...]:
    reader = csv.DictReader(io.StringIO(text))
    missing = set(COLUMNS) - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"register snapshot lacks columns {sorted(missing)}")
    communes = tuple(
        Commune(bfs_id=int(r["bfs_id"]), name=r["name"], canton=r["canton"], district=r["district"],
                postal_codes=tuple(p for p in r["postal_codes"].split(PLZ_SEPARATOR) if p))
        for r in reader
    )
    return tuple(sorted(communes, key=lambda c: c.bfs_id))


def write_register_csv(path: Path, communes: Iterable[Commune]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for c in sorted(communes, key=lambda c: c.bfs_id):
        writer.writerow({"bfs_id": c.bfs_id, "name": c.name, "canton": c.canton,
                         "district": c.district, "postal_codes": PLZ_SEPARATOR.join(c.postal_codes)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue())


def load_register(path: Path = SNAPSHOT) -> tuple[Commune, ...]:
    return parse_register_csv(path.read_text())


def _bare_name(name: str) -> str:
    return CANTON_SUFFIX.sub("", name).strip()


def _aliases(c: Commune, bare: str, unique_plz: frozenset[str]) -> tuple[str, ...]:
    marked = (f"Gemeinde {bare}", f"Stadt {bare}", f"{bare} {c.canton}", f"{bare} ({c.canton})")
    plz = tuple(p for p in c.postal_codes if p in unique_plz)
    return tuple(dict.fromkeys(marked + plz))


def commune_locations(communes: Sequence[Commune], skip_bfs_ids: set[int]) -> tuple[Location, ...]:
    """One Location per commune, id CH-<canton>-<bfs>, name without the canton suffix.

    A postal code becomes an alias only when exactly one commune carries it."""
    plz_counts = Counter(p for c in communes for p in c.postal_codes)
    unique_plz = frozenset(p for p, n in plz_counts.items() if n == 1)
    nodes = []
    for c in communes:
        if c.bfs_id in skip_bfs_ids:
            continue
        bare = _bare_name(c.name)
        nodes.append(Location(
            id=f"CH-{c.canton}-{c.bfs_id}", parent_id=f"CH-{c.canton}", level=Level.MUNICIPALITY,
            bfs_id=c.bfs_id, lindas_uri=LINDAS_MUNICIPALITY.format(bfs_id=c.bfs_id),
            names={"de": bare}, aliases=_aliases(c, bare, unique_plz),
        ))
    return tuple(nodes)
