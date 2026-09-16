"""Read probe YAML files. Ids must be unique within a file (enforced by ProbeFile) and across files."""
from collections import Counter
from pathlib import Path

import yaml
from pydantic import ValidationError

from swiss_grounding.evals.probe_models import Probe, ProbeFile, Tier

PROBE_DIR = Path(__file__).resolve().parents[3] / "evals" / "probes"


def load_probe_file(path: Path) -> ProbeFile:
    """Parse one probe file. Raises ValueError naming the file for bad YAML, wrong shape, or invalid probes."""
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")  # noqa: TRY004
    try:
        return ProbeFile.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"{path}: invalid probe file: {exc}") from exc


def load_all_probes(directory: Path = PROBE_DIR) -> tuple[tuple[Tier, Probe], ...]:
    """Every probe in every YAML file under directory, paired with its tier."""
    if not directory.is_dir():
        raise ValueError(f"probe directory not found: {directory}")
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise ValueError(f"no probe files (*.yaml) in {directory}")
    pairs: list[tuple[Tier, Probe]] = []
    for path in paths:
        pf = load_probe_file(path)
        pairs.extend((pf.tier, p) for p in pf.probes)
    counts = Counter(p.id for _, p in pairs)
    dupes = sorted(i for i, n in counts.items() if n > 1)
    if dupes:
        raise ValueError(f"probe ids duplicated across files: {dupes}")
    return tuple(pairs)
