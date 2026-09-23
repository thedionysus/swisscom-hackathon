from swiss_grounding.corpus.artifacts import save_artifact


def test_saves_under_source_with_stable_name(tmp_path):
    a = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<x/>", ".xml")
    b = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<y/>", ".xml")
    assert a == b
    assert a.startswith(str(tmp_path / "raw" / "fedlex"))
    assert open(a, "rb").read() == b"<y/>"
