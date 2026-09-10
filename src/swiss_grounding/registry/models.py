from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from swiss_grounding.registry.categories import CATEGORY_IDS


class Authority(StrEnum):
    FEDERAL_LAW = "federal_law"
    CANTONAL_LAW = "cantonal_law"
    MUNICIPAL_LAW = "municipal_law"
    OFFICIAL_INFO = "official_info"
    INSTITUTIONAL = "institutional"


LAW_AUTHORITIES = frozenset({Authority.FEDERAL_LAW, Authority.CANTONAL_LAW, Authority.MUNICIPAL_LAW})

AUTHORITY_RANK: Mapping[Authority, float] = {
    Authority.FEDERAL_LAW: 1.0,
    Authority.CANTONAL_LAW: 0.9,
    Authority.MUNICIPAL_LAW: 0.8,
    Authority.OFFICIAL_INFO: 0.6,
    Authority.INSTITUTIONAL: 0.4,
}


class FetchStrategy(StrEnum):
    FEDLEX_SPARQL = "fedlex_sparql"
    HTML_CRAWL = "html_crawl"
    PDF = "pdf"
    API = "api"


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    base_url: str
    default_extent_id: str
    authority: Authority
    categories: tuple[str, ...] = ()
    fetch_strategy: FetchStrategy
    fetch_config: dict[str, Any] = {}
    allow_narrowing: bool = False
    license: str | None = None
    origin: str = "seed"

    @field_validator("categories")
    @classmethod
    def _known_categories(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = [c for c in value if c not in CATEGORY_IDS]
        if unknown:
            raise ValueError(f"unknown category ids: {unknown}")
        return value

    @model_validator(mode="after")
    def _law_never_narrows(self) -> "Source":
        if self.authority in LAW_AUTHORITIES and self.allow_narrowing:
            raise ValueError("allow_narrowing must be false for law sources")
        return self
