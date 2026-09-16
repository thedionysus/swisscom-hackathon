"""Read probe YAML files. Ids must be unique within a file (enforced by ProbeFile) and across files."""
from collections import Counter
from pathlib import Path

import yaml

from swiss_grounding.evals.probe_models import Probe, ProbeFile, Tier

PROBE_DIR = Path(__file__).resolve().parents[3] / "evals" / "probes"


def load_probe_file(path: Path) -> ProbeFile:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")  # noqa: TRY004
    return ProbeFile.model_validate(raw)


def load_all_probes(directory: Path = PROBE_DIR) -> tuple[tuple[Tier, Probe], ...]:
    """Every probe in every YAML file under directory, paired with its tier."""
    pairs: list[tuple[Tier, Probe]] = []
    for path in sorted(directory.glob("*.yaml")):
        pf = load_probe_file(path)
        pairs.extend((pf.tier, p) for p in pf.probes)
    counts = Counter(p.id for _, p in pairs)
    dupes = sorted(i for i, n in counts.items() if n > 1)
    if dupes:
        raise ValueError(f"probe ids duplicated across files: {dupes}")
    return tuple(pairs)
