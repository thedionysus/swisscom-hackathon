from pathlib import Path

from swiss_grounding.locations.models import Level
from swiss_grounding.locations.register import (
    Commune,
    commune_locations,
    parse_register_csv,
    write_register_csv,
)
from swiss_grounding.locations.register_fetch import merge_snapshot, parse_agvch, parse_lindas_plz

FIX = Path(__file__).parent.parent.parent / "fixtures"


def test_parse_agvch_yields_communes_with_canton_abbreviation():
    communes = parse_agvch((FIX / "agvch_sample.csv").read_text())
    by_id = {c.bfs_id: c for c in communes}
    assert by_id[230] == Commune(bfs_id=230, name="Winterthur", canton="ZH", district="Bezirk Winterthur", postal_codes=())
    assert by_id[3427].canton == "SG"
    assert len(communes) == 5


def test_parse_lindas_plz_groups_codes_by_bfs_id():
    plz = parse_lindas_plz((FIX / "lindas_plz_sample.csv").read_text())
    assert plz[230] == ("8400", "8404")
    assert plz[261] == ("8001",)


def test_merge_snapshot_attaches_postal_codes():
    communes = parse_agvch((FIX / "agvch_sample.csv").read_text())
    plz = parse_lindas_plz((FIX / "lindas_plz_sample.csv").read_text())
    merged = merge_snapshot(communes, plz)
    assert next(c for c in merged if c.bfs_id == 230).postal_codes == ("8400", "8404")


def test_register_csv_roundtrip(tmp_path: Path):
    communes = merge_snapshot(parse_agvch((FIX / "agvch_sample.csv").read_text()),
                              parse_lindas_plz((FIX / "lindas_plz_sample.csv").read_text()))
    path = tmp_path / "communes.csv"
    write_register_csv(path, communes)
    assert parse_register_csv(path.read_text()) == tuple(sorted(communes, key=lambda c: c.bfs_id))


def test_commune_locations_builds_nodes_under_canton_with_aliases():
    communes = (
        Commune(bfs_id=230, name="Winterthur", canton="ZH", district="Bezirk Winterthur", postal_codes=("8400", "8404")),
        Commune(bfs_id=3427, name="Wil (SG)", canton="SG", district="Wahlkreis Wil", postal_codes=("9500",)),
        Commune(bfs_id=71, name="Wil (ZH)", canton="ZH", district="Bezirk Winterthur", postal_codes=("8196",)),
        Commune(bfs_id=261, name="Zürich", canton="ZH", district="Bezirk Zürich", postal_codes=("8001",)),
    )
    nodes = commune_locations(communes, skip_bfs_ids={261})
    by_id = {n.id: n for n in nodes}
    w = by_id["CH-ZH-230"]
    assert w.parent_id == "CH-ZH" and w.level is Level.MUNICIPALITY and w.bfs_id == 230
    assert w.names == {"de": "Winterthur"}
    assert w.lindas_uri == "https://ld.admin.ch/municipality/230"
    assert set(w.aliases) == {"Gemeinde Winterthur", "Stadt Winterthur", "Winterthur ZH", "Winterthur (ZH)", "8400", "8404"}
    wil = by_id["CH-SG-3427"]
    assert wil.names == {"de": "Wil"}
    assert "Wil" in wil.all_names() and "Wil SG" in wil.aliases and "Wil (SG)" in wil.aliases
    assert "CH-ZH-261" not in by_id


def test_shared_postal_codes_are_not_aliases():
    communes = (
        Commune(bfs_id=1, name="A", canton="ZH", district="d", postal_codes=("8000",)),
        Commune(bfs_id=2, name="B", canton="ZH", district="d", postal_codes=("8000", "8001")),
    )
    nodes = {n.id: n for n in commune_locations(communes, skip_bfs_ids=set())}
    assert "8000" not in nodes["CH-ZH-1"].aliases and "8000" not in nodes["CH-ZH-2"].aliases
    assert "8001" in nodes["CH-ZH-2"].aliases
