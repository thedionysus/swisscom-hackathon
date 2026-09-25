from swiss_grounding.locations.models import AmbiguousLocation, Level, Location, ResolvedLocation
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.places import place_outcomes

CH = Location("CH", None, Level.COUNTRY, None, None, {"de": "Schweiz"})
GR = Location("CH-GR", "CH", Level.CANTON, 18, None, {"de": "Graubünden"}, ("GR",))
SCUOL = Location("CH-GR-3762", "CH-GR", Level.MUNICIPALITY, 3762, None, {"de": "Scuol"})
BS = Location("CH-BS", "CH", Level.CANTON, 12, None, {"de": "Basel-Stadt"})
BASEL = Location("CH-BS-2701", "CH-BS", Level.MUNICIPALITY, 2701, None, {"de": "Basel"})
TREE = LocationTree.from_locations([CH, GR, SCUOL, BS, BASEL])


class StubResolver:
    def __init__(self, answers):
        self.answers = answers

    def resolve(self, text):
        return self.answers.get(text.strip())


def resolved(loc):
    return ResolvedLocation(loc, TREE.path(loc.id), "alias", loc.label())


def test_unknown_place_argument_is_unresolved():
    [o] = place_outcomes("Rundfunkbeitrag nach dem Umzug?", ("Konstanz",), StubResolver({}), TREE)
    assert o.kind == "unresolved" and o.text == "Konstanz"


def test_argument_with_a_foreign_country_is_foreign():
    [o] = place_outcomes("Rundfunkbeitrag?", ("Konstanz, Deutschland",), StubResolver({}), TREE)
    assert o.kind == "foreign"


def test_swiss_suffix_is_ignored():
    [o] = place_outcomes("q", ("Scuol, Schweiz",), StubResolver({"Scuol": resolved(SCUOL)}), TREE)
    assert o.kind == "resolved" and o.covered == ("federal", "cantonal", "municipal")


def test_swiss_place_outside_scope_is_resolved_with_federal_cover_only():
    [o] = place_outcomes("Hundesteuer?", ("Basel",), StubResolver({"Basel": resolved(BASEL)}), TREE)
    assert o.kind == "resolved" and o.covered == ("federal",)


def test_ambiguous_argument():
    amb = AmbiguousLocation("Wil", (SCUOL, BASEL), "two places")
    [o] = place_outcomes("q", ("Wil",), StubResolver({"Wil": amb}), TREE)
    assert o.kind == "ambiguous" and len(o.candidates) == 2


def test_question_naming_a_swiss_place_resolves_from_the_question():
    [o] = place_outcomes("Cura èn las vacanzas d'atun a Scuol?", (), StubResolver({}), TREE)
    assert o.kind == "resolved" and o.resolved.location.id == "CH-GR-3762"


def test_question_naming_only_a_foreign_country_is_foreign():
    [o] = place_outcomes("Wie melde ich mich in Deutschland an?", (), StubResolver({}), TREE)
    assert o.kind == "foreign" and o.text == "Deutschland"


def test_moving_from_a_swiss_place_abroad_stays_swiss():
    [o] = place_outcomes("Abmelden in Scuol vor dem Umzug nach Deutschland?", (), StubResolver({}), TREE)
    assert o.kind == "resolved"


def test_foreign_licence_is_a_swiss_question_not_a_foreign_place():
    [o] = place_outcomes("Combien de temps puis-je conduire avec un permis étranger?", (), StubResolver({}), TREE)
    assert o.kind == "none"


def test_no_place_at_all():
    [o] = place_outcomes("Kündigungsfrist Mietwohnung?", (), StubResolver({}), TREE)
    assert o.kind == "none"


def test_three_places_give_three_outcomes():
    r = StubResolver({"Scuol": resolved(SCUOL), "Basel": resolved(BASEL)})
    kinds = [o.kind for o in place_outcomes("q", ("Scuol", "Basel", "Lindau (Bodensee)"), r, TREE)]
    assert kinds == ["resolved", "resolved", "unresolved"]


def test_bare_argument_the_question_calls_a_canton_resolves_as_the_canton():
    r = StubResolver({"Basel": resolved(BASEL), "Kanton Basel": resolved(BS)})
    [o] = place_outcomes("Tax calculator for a company in the Canton of Basel?", ("Basel",), r, TREE)
    assert o.resolved.location.id == "CH-BS"
    [o] = place_outcomes("Tax office in Basel?", ("Basel",), r, TREE)
    assert o.resolved.location.id == "CH-BS-2701"


def test_question_naming_two_places_gives_two_outcomes():
    outcomes = place_outcomes("Umzug von Scuol nach Basel: wer bewilligt?", (), StubResolver({}), TREE)
    assert [o.resolved.location.id for o in outcomes] == ["CH-GR-3762", "CH-BS-2701"]
