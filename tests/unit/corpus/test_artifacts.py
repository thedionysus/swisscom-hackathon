from pathlib import Path

from swiss_grounding.corpus.artifacts import save_artifact


def test_saves_under_source_with_stable_name(tmp_path):
    a = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<x/>", ".xml")
    b = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<y/>", ".xml")
    assert a == b
    assert a.startswith(str(tmp_path / "raw" / "fedlex"))
    assert Path(a).read_bytes() == b"<y/>"


def test_write_is_atomic_no_leftover_temp_files(tmp_path):
    save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<x/>", ".xml")
    folder = tmp_path / "raw" / "fedlex"
    names = [p.name for p in folder.iterdir()]
    assert len(names) == 1
    assert not names[0].startswith(".tmp")
