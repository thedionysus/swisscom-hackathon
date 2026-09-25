"""What the question's place is. No list of foreign places is kept."""
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from swiss_grounding.locations.models import AmbiguousLocation, Location, ResolvedLocation
from swiss_grounding.locations.question_scan import resolve_from_question
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.scope import DECLARED, Scope, covered_levels

PlaceKind = Literal["none", "resolved", "ambiguous", "foreign", "unresolved"]
# Country names only (de/fr/it/en/rm). Complete by construction; no foreign *places* are listed.
FOREIGN_COUNTRY_WORDS: frozenset[str] = frozenset({
    "deutschland", "germany", "allemagne", "germania",
    "frankreich", "france", "francia", "frantscha",
    "italien", "italy", "italie", "italia",
    "österreich", "oesterreich", "austria", "autriche",
    "liechtenstein",
})
# In a question (not a place argument) a country only counts when it is where the question is about:
# "in/nach/à/en/a/in <country>". "Permis étranger" or "Umzug ins Ausland" are Swiss federal topics.
LOCATIVE = re.compile(r"\b(?:in|im|nach|en|au|aux|à|a|in|da|per)\s+(?:der\s+|dem\s+|la\s+|l')?([a-zà-ÿ]+)",
                      re.IGNORECASE)
SWISS_SUFFIX = re.compile(r",?\s*\b(schweiz|switzerland|suisse|svizzera|svizra|ch)\s*$", re.IGNORECASE)
WORD = re.compile(r"[a-zà-ÿ]+")


class Resolver(Protocol):
    def resolve(self, text: str) -> ResolvedLocation | AmbiguousLocation | None: ...


@dataclass(frozen=True)
class PlaceOutcome:
    kind: PlaceKind
    text: str | None = None
    resolved: ResolvedLocation | None = None
    candidates: tuple[Location, ...] = ()
    covered: tuple[str, ...] = ()


def _foreign_word(text: str) -> str | None:
    """A country name anywhere in a place argument."""
    for raw in WORD.findall(text.lower()):
        if raw in FOREIGN_COUNTRY_WORDS:
            start = text.lower().find(raw)
            return text[start:start + len(raw)]
    return None


def _foreign_locative(question: str) -> str | None:
    """A country name used as the place of the question ("in Deutschland", "en France")."""
    for m in LOCATIVE.finditer(question):
        if m.group(1).lower() in FOREIGN_COUNTRY_WORDS:
            return m.group(1)
    return None


def _from_resolution(text: str, found: ResolvedLocation | AmbiguousLocation | None,
                     scope: Scope = DECLARED) -> PlaceOutcome:
    if isinstance(found, AmbiguousLocation):
        return PlaceOutcome("ambiguous", text, candidates=found.candidates)
    if found is None:
        return PlaceOutcome("unresolved", text)
    return PlaceOutcome("resolved", text, resolved=found, covered=covered_levels(found.path, scope))


def _from_argument(text: str, resolver: Resolver, scope: Scope = DECLARED) -> PlaceOutcome:
    if _foreign_word(text):
        return PlaceOutcome("foreign", text.strip())
    cleaned = SWISS_SUFFIX.sub("", text).strip()
    return _from_resolution(text.strip(), resolver.resolve(cleaned), scope)


def place_names(tree: LocationTree, extents: Sequence[str]) -> tuple[str, ...]:
    """Every name and alias of the places at `extents`, in every language the tree has."""
    return tuple(name for extent in extents for name in tree.get(extent).all_names())


def place_outcomes(question: str, locations: Sequence[str], resolver: Resolver,
                   tree: LocationTree, scope: Scope = DECLARED) -> tuple[PlaceOutcome, ...]:
    """One outcome per place argument; one outcome for the question when no argument was sent."""
    if locations:
        return tuple(_from_argument(t, resolver, scope) for t in locations)
    scanned = resolve_from_question(tree, question)
    if scanned is not None:
        return (_from_resolution(scanned.input_text, scanned, scope),)
    foreign = _foreign_locative(question)
    if foreign:
        return (PlaceOutcome("foreign", foreign),)
    return (PlaceOutcome("none"),)
