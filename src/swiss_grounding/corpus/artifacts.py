"""Raw fetched bytes kept on disk, so re-chunking and citation checks need no re-crawl (issue #12)."""
import hashlib
import os
import tempfile
from pathlib import Path


def save_artifact(data_dir: Path | str, source_id: str, url: str, content: bytes, suffix: str) -> str:
    folder = Path(data_dir) / "raw" / source_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (hashlib.sha256(url.encode()).hexdigest()[:24] + suffix)
    fd, tmp_name = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return str(path)
