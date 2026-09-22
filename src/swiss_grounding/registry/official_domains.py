from urllib.parse import urlparse

from swiss_grounding.locations.seed import CANTONS

# exact host (without leading www.) -> extent id
CITY_DOMAINS: dict[str, str] = {
    "stadt-zuerich.ch": "CH-ZH-261",
    "geneve.ch": "CH-GE-6621",
}
FEDERAL_DOMAINS: tuple[str, ...] = ("ch.ch",)
FEDERAL_SUFFIXES: tuple[str, ...] = (".admin.ch",)
CANTON_DOMAINS: dict[str, str] = {f"{abbr.lower()}.ch": f"CH-{abbr}" for _, abbr, *_ in CANTONS}
SWISS_TLDS: tuple[str, ...] = (".ch", ".swiss")

# Official law platforms (ADR 0007): the host that publishes the legal text itself, mapped to the
# jurisdiction whose law it holds. A law authority is accepted only from one of these, at that
# jurisdiction. Cantonal collections hosted by a vendor (clex.ch, silgeneve.ch) are listed
# explicitly because their host does not carry the canton's domain. Verified 2026-09-22.
LAW_PLATFORM_HOSTS: dict[str, str] = {
    "fedlex.admin.ch": "CH",
    "fedlex.data.admin.ch": "CH",
    "zh.ch": "CH-ZH",                        # zhlex
    "gesetzessammlung.bs.ch": "CH-BS",
    "belex.sites.be.ch": "CH-BE",
    "bl.clex.ch": "CH-BL",
    "srl.lu.ch": "CH-LU",
    "bgs.zg.ch": "CH-ZG",
    "gesetze.gl.ch": "CH-GL",
    "rechtsbuch.tg.ch": "CH-TG",
    "ar.clex.ch": "CH-AR",
    "ai.clex.ch": "CH-AI",
    "sh.clex.ch": "CH-SH",
    "gesetze.nw.ch": "CH-NW",
    "gdb.ow.ch": "CH-OW",
    "rechtsbuch.ur.ch": "CH-UR",
    "gesetzessammlung.sg.ch": "CH-SG",
    "gesetzessammlungen.ag.ch": "CH-AG",
    "gr-lex.gr.ch": "CH-GR",
    "bgs.so.ch": "CH-SO",
    "lex.vs.ch": "CH-VS",
    "rsn.ne.ch": "CH-NE",
    "rsju.jura.ch": "CH-JU",
    "bdlf.fr.ch": "CH-FR",
    "silgeneve.ch": "CH-GE",
    "prestations.vd.ch": "CH-VD",
    "www3.ti.ch": "CH-TI",
    "stadt-zuerich.ch": "CH-ZH-261",         # the city's own compilation (Amtliche Sammlung)
    "geneve.ch": "CH-GE-6621",
}


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


def law_platform_extent(url: str) -> str | None:
    """Jurisdiction of the official law platform behind `url`, or None if the host is not one."""
    return LAW_PLATFORM_HOSTS.get(_host(url))
