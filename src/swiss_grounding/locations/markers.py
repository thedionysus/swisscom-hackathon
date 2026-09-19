"""Level markers fix which level a place name means: "Stadt Zürich" is marked, "Zürich" is bare."""
import re

from swiss_grounding.locations.models import Level

MARKERS: dict[str, Level] = {
    "kanton": Level.CANTON, "canton": Level.CANTON, "canton of": Level.CANTON, "cantone": Level.CANTON,
    "stadt": Level.MUNICIPALITY, "gemeinde": Level.MUNICIPALITY, "commune": Level.MUNICIPALITY,
    "comune": Level.MUNICIPALITY, "city of": Level.MUNICIPALITY, "municipality of": Level.MUNICIPALITY,
    "quartier": Level.NEIGHBORHOOD, "quartiere": Level.NEIGHBORHOOD,
}
KREIS = re.compile(r"^\s*kreis\s+\d{1,2}\s*$", re.IGNORECASE)
_PATTERN = re.compile(
    r"^\s*(" + "|".join(sorted(map(re.escape, MARKERS), key=len, reverse=True)) + r")\s+(.+?)\s*$",
    re.IGNORECASE,
)


def strip_marker(text: str) -> tuple[Level | None, str]:
    """(level named by a leading marker, remaining name). Kreis N keeps its marker: it is the name."""
    if KREIS.match(text):
        return Level.NEIGHBORHOOD, text.strip()
    m = _PATTERN.match(text)
    if not m:
        return None, text.strip()
    return MARKERS[m.group(1).lower()], m.group(2)
