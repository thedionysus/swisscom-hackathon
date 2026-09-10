from collections.abc import Mapping
from typing import Protocol

from swiss_grounding.ingest.models import FetchResult, KnownUrl
from swiss_grounding.registry.models import Source


class Fetcher(Protocol):
    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult: ...
