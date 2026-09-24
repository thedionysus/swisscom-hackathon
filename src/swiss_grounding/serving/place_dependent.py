"""Does a placeless question depend on where the asker lives? Decided from the evidence.

ADR 0013 step 2 (amended 2026-09-24): with no place given, the search spans all of Switzerland,
and the relevant pages show who publishes the answer. When two or more different places each hold
their own page on the subject, the subject is set locally (dog tax at Zürich and Bern, cardboard
collection at Bern, Zürich and Chur). Then the server asks for the municipality unless a federal
passage answers by itself (the AHV reference age is 65 everywhere, even though AHV branch offices
in two cities have pages too).

Whether a federal passage answers or defers ("register with your commune", "the calendar of all
cantons shows when holidays start") is not yet stored on the chunk. Until the describe step writes
that flag, two stand-ins decide it at query time: deferral phrases in the federal passage, and the
short written list of subjects below, which never decides on its own -- the corpus has to show the
spread first.
"""
import re
from collections.abc import Sequence
from dataclasses import dataclass

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.models import ScoredGroup

# Words within `NEAR` characters of each other count as one phrase ("Karton ... abgeholt").
NEAR = 40
APOSTROPHE = r"['’]"


def _near(a: str, b: str) -> str:
    """`a` followed by `b` within NEAR characters, or the other way round."""
    return rf"(?:{a}).{{0,{NEAR}}}(?:{b})|(?:{b}).{{0,{NEAR}}}(?:{a})"


@dataclass(frozen=True)
class PlaceDependentKind:
    id: str
    reason: str                       # completes "The answer depends on the place: {reason}."
    patterns: tuple[str, ...]         # any match (case-insensitive) is enough ...
    guards: tuple[str, ...] = ()      # ... unless one of these matches: the question is federal

    def matches(self, question: str) -> bool:
        if any(re.search(g, question, re.IGNORECASE) for g in self.guards):
            return False
        return any(re.search(p, question, re.IGNORECASE) for p in self.patterns)


# Subjects that are federal even when the verbs look municipal.
CUSTOMS = r"\b(?:zoll|douane|dogana|customs|marchandises|merci\b|goods|einfuhr|import)"
ABROAD = r"\bausland|abroad|étranger|estero|exteriur\b"
SOCIAL_INSURANCE = r"\b(?:ahv|avs|iv\b|ai\b|alv|pensionskasse|caisse de pension|cassa pensioni|pension fund)"
COMPANY = r"\b(?:firma|gesellschaft|unternehmen|handelsregister|société|entreprise|registre du commerce|" \
          r"società|impresa|registro di commercio|company|business|commercial register)"
EMPLOYMENT = r"\b(?:arbeitgeber|arbeitnehmer|anspruch|bezahlt|employeur|employé|salarié|droit à|payé|" \
             r"datore|dipendente|diritto|pagat|employer|employee|entitled|paid)"
DOCUMENTS = r"\b(?:papiere|ausweis|carta d['’]identità|carta di soggiorno|carte d['’]identité|identity card|" \
            r"passport|passeport|passaporto|permit|permis|permesso|fahrzeugpapiere)"

KINDS: tuple[PlaceDependentKind, ...] = (
    PlaceDependentKind("dog_tax", "the dog tax is set by each commune", (
        r"hundesteuer|hundetaxe|hundeabgabe|hundemarke",                            # de
        r"(?:taxes?|imp[oô]ts?)\b.{0,12}\bchiens?\b|m[ée]daille.{0,12}\bchiens?\b",   # fr
        r"(?:tassa|tasse|imposta)\b.{0,12}\bcan[ie]\b",                             # it
        r"\btaxa\b.{0,12}\bchauns?\b",                                              # rm
        r"\bdog\s+(?:tax|licen[cs]e(?:\s+fee)?)\b",                                 # en
    )),
    PlaceDependentKind("waste_collection", "waste collection dates and fees are set by each commune", (
        _near(r"abfuhr|abhol|abgeholt|gesammelt|sammlung|sammelt|entsorg",
              r"\bkarton\b|kehricht|grüngut|gruengut|altpapier|\bpapier\b|sperrgut|\babfall|\bmüll|\bmuell|"
              r"\bglas\b|\bmetall\b"),                                                                        # de
        (r"sackgebühr|sackgebuehr|kehrichtgebühr|kehrichtgebuehr|abfallsack|gebührensack|gebuehrensack|"
         r"abfuhrplan|abfallkalender|entsorgungskalender|abfuhrkalender|abfuhrtermin"),                      # de
        _near(r"ramass|collect|levée|tournée",
              r"déchets|ordures|\bpapier\b|\bcarton\b|encombrants|\bverre\b|compost"),                        # fr
        r"calendrier (?:des déchets|de ramassage|des collectes)|taxe au sac|sacs? taxés?",                    # fr
        _near(r"raccol|ritir",
              r"rifiuti|\bcarta\b|\bcartone\b|ingombranti|\bvetro\b|\bumido\b|scarti"),                       # it
        r"calendario (?:dei rifiuti|della raccolta)|tassa sul sacco|sacchi? ufficial",                        # it
        _near(r"ramass|rimn|tschern|cumpil|raccol",
              r"rument|palpiri|cartun|vaider"),                                                               # rm
        _near(r"collect|pick(?:ed)?[- ]?up|\bbin\b",
              r"cardboard|\bwaste\b|garbage|rubbish|trash|recycling|bulky|\bbins?\b"),                        # en
        r"waste calendar|collection calendar|bag fee|waste fee",                                              # en
    ), guards=(CUSTOMS, DOCUMENTS, r"radioakt|radioact|nucléaire|nucleare|nuclear")),
    PlaceDependentKind("residence_registration",
                       "the registration is made with the commune of residence", (
        _near(r"anmeld|ummeld|abmeld|\bmelde[nst]?\b|\bmeldet\b|umzieh|\bzieh(?:e|st|t|en)?\s+um\b|umzug|zügel|zuegel",
              r"umzug|zuzug|wegzug|wohnsitz|gemeinde|einwohner|zügel|zuegel|anmeld|ummeld"),                 # de
        _near(r"annonc|inscri|enregistr",
              r"commune|contrôle des habitants|déménag|domicile|habitants"),                                  # fr
        _near(r"annunci|notific|iscri",
              r"comune|controllo abitanti|trasloc|domicilio|abitanti"),                                       # it
        _near(r"annunzi|registr",
              r"vischnanca|vischnaunca|cumin\b|midada|domicil"),                                              # rm
        _near(r"register|registration",
              r"commune|municipality|residents|moving|\bmove\b|residence"),                                   # en
    ), guards=(CUSTOMS, ABROAD, SOCIAL_INSURANCE, COMPANY)),
    PlaceDependentKind("school_holidays", "school holidays are set by each canton", (
        (r"schulferien|schulfrei|ferienplan|ferienkalender|"
         r"(?:sommer|herbst|winter|frühlings|fruehlings|sport|weihnachts|oster)ferien"),                      # de
        (rf"vacances\s+(?:scolaires|d{APOSTROPHE}été|d{APOSTROPHE}automne|de printemps|d{APOSTROPHE}hiver|"
         r"de noël|de pâques)|calendrier scolaire"),                                                          # fr
        (r"vacanze\s+(?:scolastiche|estive|autunnali|primaverili|invernali|di natale|pasquali)|"
         r"calendario scolastico"),                                                                           # it
        rf"vacanzas\s+(?:da scola|d{APOSTROPHE}atun|da stad|da primavaira|d{APOSTROPHE}enviern|scolasticas)",  # rm
        r"school\s+(?:holidays?|vacation|break|calendar)|(?:summer|autumn|fall|spring|winter)\s+(?:holidays?|break)",  # en
    ), guards=(EMPLOYMENT,)),
    PlaceDependentKind("municipal_tax_rate", "the municipal tax multiplier is set by each commune", (
        r"steuerfuss|steuerfuß|gemeindesteuer",                                                               # de
        r"(?:taux|coefficient|centimes additionnels).{0,20}(?:communal|impôt communal)|impôts? communa",      # fr
        r"moltiplicatore|imposta comunale|imposte comunali",                                                  # it
        r"pe(?:i|s)\s+da\s+taglia\s+communal|taglia communala",                                               # rm
        r"(?:municipal|communal)\s+tax\s+(?:rate|multiplier)|commune tax rate|tax multiplier",                # en
    )),
)


def place_dependent_kind(question: str) -> PlaceDependentKind | None:
    """The first kind whose words the question uses, or None when the question is not on the list."""
    if not question or not question.strip():
        return None
    return next((k for k in KINDS if k.matches(question)), None)


FEDERAL = "CH"
MIN_PLACES = 2                 # pages from this many different places make a subject local
FEDERAL_PASSAGES_READ = 3      # how many top federal passages are read for a deferral
LEVELS = r"(?:gemeinde|kanton|commune|canton|comune|cantone|municipalit|vischnanca|chantun)"
# A federal passage that points to the canton or commune for the actual answer.
DEFER = re.compile(
    rf"(?:{LEVELS}\w*\s+(?:legt|legen|regelt|regeln|bestimmt|bestimmen|entscheidet|entscheiden|"
    rf"ist zuständig|sind zuständig|fixe|fixent|décide|décident|règle|règlent|stabilisce|stabiliscono|"
    rf"decide|decidono|regola|regolano|sets?|decides?|regulates?|determines?)\b)"
    rf"|(?:(?:legt|legen|fest(?:gelegt|gesetzt)|fixé|fixée|fixés|stabilit[oa]|set|decided)\s+(?:jede|jeder|die|der|par la|par le|dal|dai|by (?:the|each|your))\s+{LEVELS})"
    rf"|(?:je nach|von .{{0,12}}zu|selon (?:le|la|les)|d[’']une? .{{0,10}}à l[’']autre|a seconda (?:del|dei|della)|"
    rf"da .{{0,10}}a .{{0,10}}|varies (?:by|from)|depends? on (?:the|your|each)|unterschiedlich (?:je|von))\s*{LEVELS}?"
    rf"|(?:bei (?:der|ihrer) (?:wohn)?gemeinde|auprès de (?:votre|la|sa) commune|presso il (?:proprio |vostro |suo )?comune|"
    rf"erkundigen sie sich bei|renseignez-vous auprès|informatevi presso|contact your {LEVELS}|"
    rf"(?:aller|tutti i|de tous les|of all the) {LEVELS}|(?:einzelnen|singoli|chaque|each) {LEVELS})",
    re.IGNORECASE)


def federal_defers(text: str) -> bool:
    """True when a federal passage points to the canton or commune for the actual answer."""
    return bool(DEFER.search(text))


def distinct_places(extents: Sequence[str], tree: LocationTree) -> tuple[str, ...]:
    """The local extents, with an ancestor dropped when one of its descendants is present: a
    canton and its own commune are one place, two communes or two cantons are two."""
    local = {e for e in extents if e != FEDERAL}
    paths = {e: set(tree.path(e)) for e in local}
    return tuple(sorted(e for e in local if not any(o != e and e in paths[o] for o in local)))


def answer_depends_on_place(question: str, relevant: Sequence[ScoredGroup], tree: LocationTree) -> str | None:
    """Why a placeless question must be asked back, or None when the evidence answers it.

    No federal passage at all: the local pages are one place's rules, so answering would be a
    guess (ADR 0013 amendment). Federal passages present: only when several places hold their own
    page on the subject and the federal passage defers, by its wording or by the subject list."""
    extents = [s.group.representative.extent_id for s in relevant]
    places = distinct_places(extents, tree)
    labels = ", ".join(sorted({tree.get(e).label("de") for e in places}))
    federal = [s for s in relevant if s.group.representative.extent_id == FEDERAL]
    if not federal and places:
        return f"only local pages answer it (found for: {labels})"
    if not federal or len(places) < MIN_PLACES:
        return None
    kind = place_dependent_kind(question)
    if kind is not None:
        return f"{kind.reason} (local pages found for: {labels})"
    if any(federal_defers(s.group.representative.text) for s in federal[:FEDERAL_PASSAGES_READ]):
        return f"the federal page points to the canton or commune (local pages found for: {labels})"
    return None
