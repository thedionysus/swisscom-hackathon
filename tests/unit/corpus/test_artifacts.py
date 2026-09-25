from pathlib import Path

from swiss_grounding.corpus.artifacts import save_artifact


def test_same_url_and_bytes_reuse_one_file(tmp_path):
    a = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<x/>", ".xml")
    b = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<x/>", ".xml")
    assert a == b
    assert a.startswith(str(tmp_path / "raw" / "fedlex"))
    assert Path(a).read_bytes() == b"<x/>"


def test_a_new_version_at_the_same_url_never_overwrites_the_old_bytes(tmp_path):
    """#12: the superseded or withdrawn document keeps pointing at the bytes it was parsed from."""
    old = save_artifact(tmp_path, "x", "https://x/a.pdf", b"%PDF-old", ".pdf")
    new = save_artifact(tmp_path, "x", "https://x/a.pdf", b"%PDF-new", ".pdf")
    assert old != new
    assert Path(old).read_bytes() == b"%PDF-old" and Path(new).read_bytes() == b"%PDF-new"


def test_an_explicit_version_names_the_file_instead_of_the_bytes(tmp_path):
    """HTML differs between fetches (tokens, timestamps) while its text does not: one file per version."""
    a = save_artifact(tmp_path, "x", "https://x/p", b"<p>t</p><!-- 1 -->", ".html", version="abc123")
    b = save_artifact(tmp_path, "x", "https://x/p", b"<p>t</p><!-- 2 -->", ".html", version="abc123")
    assert a == b
    assert Path(a).read_bytes() == b"<p>t</p><!-- 2 -->"


def test_write_is_atomic_no_leftover_temp_files(tmp_path):
    save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<x/>", ".xml")
    folder = tmp_path / "raw" / "fedlex"
    names = [p.name for p in folder.iterdir()]
    assert len(names) == 1
    assert not names[0].startswith(".tmp")
