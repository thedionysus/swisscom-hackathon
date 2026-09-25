"""Raw fetched bytes kept on disk, so re-chunking and citation checks need no re-crawl (issue #12)."""
import hashlib
import os
import tempfile
from pathlib import Path


def save_artifact(data_dir: Path | str, source_id: str, url: str, content: bytes, suffix: str,
                  version: str | None = None) -> str:
    """Write `content` under raw/<source>/ and return its path.

    The name is a hash of the URL plus a hash of the version -- `version` when given, else the bytes
    themselves -- so a new version at the same URL never overwrites the bytes an older, superseded or
    withdrawn document still points at, and an identical re-fetch reuses the same file. A file already
    there is left as it is (writes are atomic, so it is complete): same bytes, or the first bytes of that
    `version`.
    """
    folder = Path(data_dir) / "raw" / source_id
    folder.mkdir(parents=True, exist_ok=True)
    tag = version or hashlib.sha256(content).hexdigest()
    path = folder / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}-{tag[:16]}{suffix}"
    if path.exists():
        return str(path)
    fd, tmp_name = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return str(path)
