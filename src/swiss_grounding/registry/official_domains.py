from urllib.parse import urlparse

from swiss_grounding.locations.seed import CANTONS

# exact host (without leading www.) -> extent id
CITY_DOMAINS: dict[str, str] = {
    "stadt-zuerich.ch": "CH-ZH-261",
}
FEDERAL_DOMAINS: tuple[str, ...] = ("ch.ch",)
FEDERAL_SUFFIXES: tuple[str, ...] = (".admin.ch",)
CANTON_DOMAINS: dict[str, str] = {f"{abbr.lower()}.ch": f"CH-{abbr}" for _, abbr, *_ in CANTONS}
SWISS_TLDS: tuple[str, ...] = (".ch", ".swiss")


def _host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def extent_for_domain(url: str) -> str | None:
    host = _host(url)
    if host in CITY_DOMAINS:
        return CITY_DOMAINS[host]
    if host in CANTON_DOMAINS:
        return CANTON_DOMAINS[host]
    if host in FEDERAL_DOMAINS or host.endswith(FEDERAL_SUFFIXES):
        return "CH"
    return None


def classify_domain(url: str) -> str:
    """'official' for known government domains, 'swiss' for .ch/.swiss, else 'other'."""
    if extent_for_domain(url) is not None:
        return "official"
    return "swiss" if _host(url).endswith(SWISS_TLDS) else "other"
