from importlib import resources

import yaml
from pydantic import ValidationError

from swiss_grounding.registry.models import Source


def load_source_yaml(text: str) -> Source:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("source definition must be a mapping")  # noqa: TRY004
    try:
        return Source.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid source definition: {exc}") from exc


def load_seed_sources() -> tuple[Source, ...]:
    folder = resources.files("swiss_grounding.registry").joinpath("sources")
    files = sorted(p for p in folder.iterdir() if p.name.endswith(".yaml"))
    return tuple(load_source_yaml(p.read_text()) for p in files)
