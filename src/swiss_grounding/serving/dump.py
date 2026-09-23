"""Split, checksum and reassemble the prebuilt database dump (ADR 0017)."""
import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path

PART_BYTES = 1_900 * 1024 * 1024        # under GitHub's 2 GiB per release asset
MANIFEST_NAME = "corpus.manifest.json"
CHUNK = 1024 * 1024
# Table data left out of the default dump: legacy public-schema tables, the OpenAI vectors (optional asset),
# and per-installation logs.
EXCLUDE_DATA = ("public.chunk", "public.document", "public.document_change", "public.eval_run",
                "corpus.emb_openai_3l*", "serving.call_log", "serving.lookup_cache")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def split_file(src: Path, out_dir: Path, part_bytes: int = PART_BYTES) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    with src.open("rb") as f:
        index = 0
        while data := f.read(part_bytes):
            part = out_dir / f"{src.name}.part{index:02d}"
            part.write_bytes(data)
            parts.append(part)
            index += 1
    return parts


def build_manifest(parts: Sequence[Path], meta: Mapping) -> dict:
    return {"parts": [{"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p)} for p in parts],
            **dict(meta)}


def verify_parts(directory: Path, manifest: Mapping) -> None:
    for part in manifest["parts"]:
        path = directory / part["name"]
        if not path.exists() or _sha256(path) != part["sha256"]:
            raise ValueError(f"checksum mismatch or missing part: {part['name']}; delete it and re-run setup")


def join_parts(directory: Path, manifest: Mapping, target: Path) -> Path:
    with target.open("wb") as out:
        for part in manifest["parts"]:
            with (directory / part["name"]).open("rb") as f:
                while block := f.read(CHUNK):
                    out.write(block)
    return target
