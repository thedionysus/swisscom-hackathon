from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from swiss_grounding.locations.models import Level
from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.registry.official_domains import classify_domain, law_platform_extent


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


LAW_EXTENT_LEVEL: Mapping[Authority, Level] = {
    Authority.FEDERAL_LAW: Level.COUNTRY,
    Authority.CANTONAL_LAW: Level.CANTON,
    Authority.MUNICIPAL_LAW: Level.MUNICIPALITY,
}


def extent_level_from_id(extent_id: str) -> Level:
    """Level encoded in a location id: CH, CH-ZH, CH-ZH-261, CH-ZH-261-K3 (and deeper)."""
    depth = extent_id.count("-")
    if depth == 0:
        return Level.COUNTRY
    if depth == 1:
        return Level.CANTON
    if depth == 2:
        return Level.MUNICIPALITY
    return Level.NEIGHBORHOOD


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
    # When false, enrich() skips llm.classify and tags from `categories` alone; _merge_tags never
    # drops an LLM tag outside those defaults, so this only suits a single-category feed like a
    # waste calendar, not a source whose documents span several categories.
    llm_tagging: bool = True
    license: str | None = None
    origin: str = "seed"
    # Why a source on a non-government host still carries official_info (e.g. it re-serves a city's
    # open-data export). Required in that case; ignored otherwise. Validation-time only.
    authority_reason: str | None = None

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

    @model_validator(mode="after")
    def _authority_follows_the_publisher(self) -> "Source":
        """ADR 0003: a law authority only from a registered official law platform, at the platform's
        own jurisdiction and level; official_info only from an official domain unless a reason says why."""
        if self.authority in LAW_AUTHORITIES:
            platform = law_platform_extent(self.base_url)
            if platform is None:
                raise ValueError(
                    f"{self.authority.value} requires base_url on a registered official law platform "
                    f"(registry.official_domains.LAW_PLATFORM_HOSTS); {self.base_url!r} is not one")
            level = extent_level_from_id(self.default_extent_id)
            if level != LAW_EXTENT_LEVEL[self.authority]:
                raise ValueError(
                    f"{self.authority.value} must land at {LAW_EXTENT_LEVEL[self.authority].value} level, "
                    f"but default_extent_id {self.default_extent_id!r} is {level.value} level")
            if platform != self.default_extent_id:
                raise ValueError(
                    f"{self.base_url!r} publishes the law of {platform}, not of {self.default_extent_id!r}")
        elif self.authority is Authority.OFFICIAL_INFO:
            if classify_domain(self.base_url) != "official" and not (self.authority_reason or "").strip():
                raise ValueError(
                    f"official_info on non-government host {self.base_url!r} needs an authority_reason "
                    "(who the official publisher is), or use institutional")
        return self
