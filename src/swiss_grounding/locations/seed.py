from swiss_grounding.locations.models import Level, Location

# (bfs_id, abbreviation, de, fr, it, en, extra aliases)
CANTONS: tuple[tuple[int, str, str, str, str, str, tuple[str, ...]], ...] = (
    (1, "ZH", "Zürich", "Zurich", "Zurigo", "Zurich", ("Kanton Zürich", "Canton of Zurich")),
    (2, "BE", "Bern", "Berne", "Berna", "Bern", ("Kanton Bern", "Canton of Bern")),
    (3, "LU", "Luzern", "Lucerne", "Lucerna", "Lucerne", ("Kanton Luzern",)),
    (4, "UR", "Uri", "Uri", "Uri", "Uri", ("Kanton Uri",)),
    (5, "SZ", "Schwyz", "Schwytz", "Svitto", "Schwyz", ("Kanton Schwyz",)),
    (6, "OW", "Obwalden", "Obwald", "Obvaldo", "Obwalden", ("Kanton Obwalden",)),
    (7, "NW", "Nidwalden", "Nidwald", "Nidvaldo", "Nidwalden", ("Kanton Nidwalden",)),
    (8, "GL", "Glarus", "Glaris", "Glarona", "Glarus", ("Kanton Glarus",)),
    (9, "ZG", "Zug", "Zoug", "Zugo", "Zug", ("Kanton Zug",)),
    (10, "FR", "Freiburg", "Fribourg", "Friburgo", "Fribourg", ("Kanton Freiburg", "Canton de Fribourg")),
    (11, "SO", "Solothurn", "Soleure", "Soletta", "Solothurn", ("Kanton Solothurn",)),
    (12, "BS", "Basel-Stadt", "Bâle-Ville", "Basilea Città", "Basel-Stadt", ("Basel", "Kanton Basel-Stadt")),
    (13, "BL", "Basel-Landschaft", "Bâle-Campagne", "Basilea Campagna", "Basel-Landschaft", ("Baselland", "Kanton Basel-Landschaft")),
    (14, "SH", "Schaffhausen", "Schaffhouse", "Sciaffusa", "Schaffhausen", ("Kanton Schaffhausen",)),
    (15, "AR", "Appenzell Ausserrhoden", "Appenzell Rhodes-Extérieures", "Appenzello Esterno", "Appenzell Ausserrhoden", ()),
    (16, "AI", "Appenzell Innerrhoden", "Appenzell Rhodes-Intérieures", "Appenzello Interno", "Appenzell Innerrhoden", ()),
    (17, "SG", "St. Gallen", "Saint-Gall", "San Gallo", "St. Gallen", ("Kanton St. Gallen", "Sankt Gallen")),
    (18, "GR", "Graubünden", "Grisons", "Grigioni", "Grisons", ("Kanton Graubünden", "Grischun")),
    (19, "AG", "Aargau", "Argovie", "Argovia", "Aargau", ("Kanton Aargau",)),
    (20, "TG", "Thurgau", "Thurgovie", "Turgovia", "Thurgau", ("Kanton Thurgau",)),
    (21, "TI", "Tessin", "Tessin", "Ticino", "Ticino", ("Kanton Tessin", "Cantone Ticino")),
    (22, "VD", "Waadt", "Vaud", "Vaud", "Vaud", ("Kanton Waadt", "Canton de Vaud")),
    (23, "VS", "Wallis", "Valais", "Vallese", "Valais", ("Kanton Wallis", "Canton du Valais")),
    (24, "NE", "Neuenburg", "Neuchâtel", "Neuchâtel", "Neuchâtel", ("Kanton Neuenburg", "Canton de Neuchâtel")),
    (25, "GE", "Genf", "Genève", "Ginevra", "Geneva", ("Kanton Genf", "Canton de Genève", "Geneve")),
    (26, "JU", "Jura", "Jura", "Giura", "Jura", ("Kanton Jura", "Canton du Jura")),
)

# Kreis number -> (quartiere, plz aliases that lie fully within the Kreis)
ZURICH_KREISE: dict[int, tuple[tuple[str, ...], tuple[str, ...]]] = {
    1: (("Rathaus", "Hochschulen", "Lindenhof", "City"), ("8001",)),
    2: (("Wollishofen", "Leimbach", "Enge"), ("8002", "8038", "8041")),
    3: (("Alt-Wiedikon", "Friesenberg", "Sihlfeld"), ("8003", "8045", "8055")),
    4: (("Werd", "Langstrasse", "Hard"), ("8004",)),
    5: (("Gewerbeschule", "Escher Wyss"), ("8005",)),
    6: (("Unterstrass", "Oberstrass"), ("8006", "8057")),
    7: (("Fluntern", "Hottingen", "Hirslanden", "Witikon"), ("8032", "8044", "8053")),
    8: (("Seefeld", "Mühlebach", "Weinegg"), ("8008",)),
    9: (("Albisrieden", "Altstetten"), ("8047", "8048", "8064")),
    10: (("Höngg", "Wipkingen"), ("8037", "8049")),
    11: (("Affoltern", "Oerlikon", "Seebach"), ("8046", "8050", "8052")),
    12: (("Saatlen", "Schwamendingen-Mitte", "Hirzenbach"), ("8051",)),
}

# Common names for Quartiere that differ from the statistical name
QUARTIER_ALIASES: dict[str, tuple[str, ...]] = {
    "Alt-Wiedikon": ("Wiedikon",),
    "Escher Wyss": ("Zürich West",),
    "Rathaus": ("Niederdorf", "Altstadt"),
    "City": ("Bahnhofstrasse",),
    "Schwamendingen-Mitte": ("Schwamendingen",),
}


def _slug(text: str) -> str:
    return (
        text.upper()
        .replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE")
        .replace(" ", "-")
    )


def seed_locations() -> tuple[Location, ...]:
    country = Location(
        id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None,
        lindas_uri="https://ld.admin.ch/country/CHE",
        names={"de": "Schweiz", "fr": "Suisse", "it": "Svizzera", "en": "Switzerland"},
        aliases=("CH", "Swiss", "Confederation", "Eidgenossenschaft", "Confédération"),
    )
    cantons = tuple(
        Location(
            id=f"CH-{abbr}", parent_id="CH", level=Level.CANTON, bfs_id=bfs,
            lindas_uri=f"https://ld.admin.ch/canton/{bfs}",
            names={"de": de, "fr": fr, "it": it, "en": en},
            aliases=(abbr, f"CH-{abbr}") + extra,
        )
        for bfs, abbr, de, fr, it, en, extra in CANTONS
    )
    city = Location(
        id="CH-ZH-261", parent_id="CH-ZH", level=Level.MUNICIPALITY, bfs_id=261,
        lindas_uri="https://ld.admin.ch/municipality/261",
        names={"de": "Zürich", "fr": "Zurich", "it": "Zurigo", "en": "Zurich"},
        aliases=("Stadt Zürich", "City of Zurich", "Zuerich", "Zurich city"),
    )
    kreise: list[Location] = []
    quartiere: list[Location] = []
    for number, (names, plzs) in ZURICH_KREISE.items():
        kreis_id = f"CH-ZH-261-K{number}"
        kreise.append(Location(
            id=kreis_id, parent_id="CH-ZH-261", level=Level.NEIGHBORHOOD, bfs_id=None,
            lindas_uri=None,
            names={"de": f"Kreis {number}", "en": f"District {number}"},
            aliases=(f"Zürich Kreis {number}", f"Kreis{number}") + plzs,
        ))
        for name in names:
            quartiere.append(Location(
                id=f"{kreis_id}-{_slug(name)}", parent_id=kreis_id, level=Level.NEIGHBORHOOD,
                bfs_id=None, lindas_uri=None,
                names={"de": name},
                aliases=QUARTIER_ALIASES.get(name, ()),
            ))
    return (country,) + cantons + (city,) + tuple(kreise) + tuple(quartiere)
