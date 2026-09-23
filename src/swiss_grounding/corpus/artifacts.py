"""Raw fetched bytes kept on disk, so re-chunking and citation checks need no re-crawl (issue #12)."""
import hashlib
from pathlib import Path


def save_artifact(data_dir: Path | str, source_id: str, url: str, content: bytes, suffix: str) -> str:
    folder = Path(data_dir) / "raw" / source_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (hashlib.sha256(url.encode()).hexdigest()[:24] + suffix)
    path.write_bytes(content)
    return str(path)
