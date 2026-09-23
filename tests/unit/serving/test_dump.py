import pytest

from swiss_grounding.serving.dump import build_manifest, join_parts, split_file, verify_parts


def test_split_join_round_trip_with_checksums(tmp_path):
    src = tmp_path / "corpus.dump"
    src.write_bytes(bytes(range(256)) * 40)
    parts = split_file(src, tmp_path / "out", part_bytes=3000)
    assert len(parts) == 4
    manifest = build_manifest(parts, meta={"git_commit": "abc"})
    verify_parts(tmp_path / "out", manifest)
    joined = join_parts(tmp_path / "out", manifest, tmp_path / "joined.dump")
    assert joined.read_bytes() == src.read_bytes()


def test_corrupt_part_is_refused(tmp_path):
    src = tmp_path / "corpus.dump"
    src.write_bytes(b"x" * 5000)
    parts = split_file(src, tmp_path / "out", part_bytes=3000)
    manifest = build_manifest(parts, meta={})
    parts[0].write_bytes(b"y" * 3000)
    with pytest.raises(ValueError, match="checksum"):
        verify_parts(tmp_path / "out", manifest)
