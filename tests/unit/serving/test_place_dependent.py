import pytest

from swiss_grounding.serving.place_dependent import KINDS, place_dependent_kind, street_named

# Golden-set questions that must ask for the place before any search.
GOLDEN_PLACELESS = [
    ("de", "Wann wird bei uns das nächste Mal Karton abgeholt?", "waste_collection"),
    ("de", "Wann wird bei mir der Hauskehricht abgeholt?", "waste_collection"),
    ("fr", "Comment m'annoncer à la commune après un déménagement?", "residence_registration"),
    ("it", "Quando iniziano le vacanze scolastiche?", "school_holidays"),
    ("de", "Wie hoch ist die Hundesteuer?", "dog_tax"),
]

# One phrasing per kind and language, so every language column of the list is exercised.
PER_LANGUAGE = [
    ("fr", "Combien coûte la taxe sur les chiens ?", "dog_tax"),
    ("it", "Quanto costa la tassa sui cani?", "dog_tax"),
    ("rm", "Quant custa la taxa da chauns?", "dog_tax"),
    ("en", "How much is the dog tax?", "dog_tax"),
    ("fr", "Quand a lieu le ramassage du papier et du carton ?", "waste_collection"),
    ("it", "Quando viene ritirata la carta e il cartone?", "waste_collection"),
    ("rm", "Cura vegn ramassà il palpiri e cartun?", "waste_collection"),
    ("en", "When is cardboard collected?", "waste_collection"),
    ("de", "Wie melde ich meinen Umzug bei der Gemeinde an?", "residence_registration"),
    ("it", "Come mi annuncio al comune dopo un trasloco?", "residence_registration"),
    ("rm", "Co ma poss jau annunziar tar la vischnanca suenter la midada?", "residence_registration"),
    ("en", "How do I register with the commune after moving?", "residence_registration"),
    ("de", "Wann sind die Herbstferien?", "school_holidays"),
    ("fr", "Quelles sont les dates des vacances scolaires ?", "school_holidays"),
    ("rm", "Cura èn las vacanzas d'atun?", "school_holidays"),
    ("en", "When are the school holidays?", "school_holidays"),
    ("de", "Wie hoch ist der Steuerfuss?", "municipal_tax_rate"),
    # Phrasings the review asked for.
    ("de", "Was kostet der Abfallsack?", "waste_collection"),
    ("de", "Wie hoch ist die Kehrichtgebühr?", "waste_collection"),
    ("de", "Ich ziehe um. Wo muss ich mich anmelden?", "residence_registration"),
    ("de", "Muss ich meinen Hund bei der Gemeinde anmelden?", "residence_registration"),
    ("fr", "Combien coûtent les taxes sur les chiens ?", "dog_tax"),
    ("fr", "Quelles sont les dates des vacances d’été ?", "school_holidays"),
    ("en", "How much does a dog licence cost?", "dog_tax"),
    ("en", "When is bin collection day?", "waste_collection"),
    ("en", "What is the communal tax rate?", "municipal_tax_rate"),
    ("fr", "Quel est le coefficient d'impôt communal ?", "municipal_tax_rate"),
    ("it", "Qual è il moltiplicatore d'imposta comunale?", "municipal_tax_rate"),
    ("en", "What is the municipal tax rate?", "municipal_tax_rate"),
]

# Placeless golden-set questions that are answered from federal sources: the gate must stay silent.
FEDERAL = [
    "Wie lange ist die Kündigungsfrist für eine Mietwohnung?",
    "Ab welchem Alter darf man in der Schweiz heiraten?",
    "Ab welchem Alter erhalte ich eine AHV-Altersrente?",
    "Bis zu welchem Warenwert muss ich bei der Einreise in die Schweiz keine Mehrwertsteuer zahlen?",
    "Wie oft im Jahr finden eidgenössische Volksabstimmungen statt?",
    "Qui finance la réduction des primes d'assurance-maladie pour les personnes à revenu modeste?",
    "A partire da quale età ci si può sposare in Svizzera?",
    "Co ha da far in partida per vegnir integrada en il register federal da las partidas?",
    "Nua chattain ins las explicaziuns dal Cussegl federal davart ils object da votar dals ultims onns?",
    "What does Swiss unemployment insurance (ALV) cover?",
    "What is the purpose of the Swiss occupational pension (second pillar)?",
    "Welche Quelle belegt die Frist von 12 Monaten für den Umtausch des ausländischen Führerausweises?",
    "Wie hoch ist der aktuelle Referenzzinssatz für Mieten?",
    # Registration words without a move: AHV and company registrations are federal.
    "Wie melde ich mich bei der AHV an?",
    "Comment inscrire ma société au registre du commerce ?",
    # Taxes in general are federal and cantonal law, not the municipal multiplier.
    "Kann ich Krankenkassenprämien von der Steuer abziehen?",
    # Documents are collected, not waste.
    "Kann ich meine Fahrzeugpapiere beim Strassenverkehrsamt abholen?",
    "Wo kann ich meine Papiere abholen?",
    "Come posso ritirare la carta d'identità?",
    "Come posso ritirare la carta di soggiorno?",
    "Which papers do I need to collect for a work permit?",
    # Customs and moving abroad are federal.
    "Dois-je déclarer mes marchandises à l'arrivée en Suisse ?",
    "Devo notificare le merci all'arrivo in dogana?",
    "Do I need to report goods on arrival at customs?",
    "Comment déclarer mes impôts si j'ai changé de domicile ?",
    "Do I have to report to the AHV when moving abroad?",
    "Muss ich mich bei der AHV abmelden, wenn ich meinen Wohnsitz ins Ausland verlege?",
    "Wer ist für die Entsorgung von radioaktivem Abfall zuständig?",
    "Where do I register my company address?",
    # Employee holidays are the Code of Obligations, not the school calendar.
    "Darf mein Arbeitgeber mir die Sommerferien verweigern?",
    "Ai-je droit à des vacances d'été payées ?",
    "Am I entitled to summer holidays as an employee?",
]


@pytest.mark.parametrize(("lang", "question", "kind"), GOLDEN_PLACELESS + PER_LANGUAGE)
def test_place_dependent_questions_are_recognised(lang, question, kind):
    found = place_dependent_kind(question)
    assert found is not None and found.id == kind, f"{lang}: {question!r}"


@pytest.mark.parametrize("question", FEDERAL)
def test_federal_questions_are_not_gated(question):
    assert place_dependent_kind(question) is None


def test_matching_ignores_case_and_surrounding_text():
    assert place_dependent_kind("HUNDESTEUER?").id == "dog_tax"
    assert place_dependent_kind("Ich frage mich, wie hoch die Hundesteuer wohl ist.").id == "dog_tax"


def test_every_kind_has_a_reason_for_the_user():
    for kind in KINDS:
        assert kind.reason and kind.reason[0].islower() and not kind.reason.endswith(".")


def test_empty_question_is_not_gated():
    assert place_dependent_kind("") is None


@pytest.mark.parametrize(("question", "street"), [
    ("When is the next cardboard collection at Bahnhofstrasse?", "Bahnhofstrasse"),
    ("Wann wird an der Kirchgasse Karton abgeholt?", "Kirchgasse"),
    ("Parking à la rue de la Gare ?", "rue de la Gare"),
    ("Raccolta carta in Via Nassa?", "Via Nassa"),
])
def test_street_named(question, street):
    assert street_named(question) == street


@pytest.mark.parametrize("question", [
    "Öffnungszeiten Strassenverkehrsamt?",
    "Horaires des chemins de fer?",
    "Can I travel via Zürich with a B permit?",
    "When is the next cardboard collection?",
])
def test_no_street_named(question):
    assert street_named(question) is None
