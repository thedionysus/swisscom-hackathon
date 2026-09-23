from pathlib import Path

from swiss_grounding.lookups.premium_data import age_class, read_premiums, read_regions

FIX = Path("tests/fixtures/premium")


def test_reads_premium_rows_with_normalised_codes():
    rows = list(read_premiums(FIX / "premiums_sample.csv", insurer_names={"1509": "Kasse A"}))
    first = rows[0]
    assert (first.year, first.canton, first.region, first.age_class, first.accident, first.model,
            first.deductible, first.premium_chf) == (2026, "TI", 1, "adult", True, "standard", 2500, 401.20)
    assert first.insurer_name == "Kasse A" and rows[2].insurer_name == "0032"
    assert rows[1].model == "hmo" and rows[2].model == "family_doctor"


def test_reads_regions():
    assert {(r.bfs_id, r.region) for r in read_regions(FIX / "regions_sample.csv", year=2026)} == {(5192, 1), (5002, 2)}


def test_age_class_boundaries():
    assert [age_class(a) for a in (0, 18, 19, 25, 26, 30)] == ["child", "child", "young_adult", "young_adult",
                                                               "adult", "adult"]
