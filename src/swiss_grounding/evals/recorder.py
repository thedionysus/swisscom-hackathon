"""Write observed blocks back into a probe YAML file. Comments and flow-style mappings are not
preserved; list indentation is."""
import os
from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import ValidationError

from swiss_grounding.evals.probe_loader import load_probe_file
from swiss_grounding.evals.probe_models import Observed, ProbeFile


class _IndentedDumper(yaml.SafeDumper):
    """Indent list items under their key, matching the hand-written probe files."""

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


def _with_observed(probe_raw: Mapping, observed: Observed | None) -> dict:
    if observed is None:
        return dict(probe_raw)
    without = {k: v for k, v in probe_raw.items() if k != "observed"}
    return {**without, "observed": observed.model_dump(mode="json")}


def _write_atomically(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def record_observed(path: Path, observed_by_id: Mapping[str, Observed]) -> None:
    """Rewrite path with an observed block on each probe named in observed_by_id.

    Raises ValueError, and leaves the file untouched, when an id is unknown or the
    result would not validate as a probe file."""
    if not observed_by_id:
        return
    load_probe_file(path)
    raw = yaml.safe_load(path.read_text())
    known = {p["id"] for p in raw["probes"]}
    unknown = sorted(set(observed_by_id) - known)
    if unknown:
        raise ValueError(f"{path}: unknown probe ids {unknown}")
    updated = {**raw, "probes": [_with_observed(p, observed_by_id.get(p["id"])) for p in raw["probes"]]}
    try:
        ProbeFile.model_validate(updated)
    except ValidationError as exc:
        raise ValueError(f"{path}: recording would produce an invalid probe file: {exc}") from exc
    text = yaml.dump(updated, Dumper=_IndentedDumper, sort_keys=False, allow_unicode=True, width=120)
    _write_atomically(path, text)
