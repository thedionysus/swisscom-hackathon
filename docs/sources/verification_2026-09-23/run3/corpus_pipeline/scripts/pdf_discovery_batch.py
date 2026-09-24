"""Batch offline PDF-link discovery with the NEW connector's page_meta (no network)."""
import json
from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.ingest.html_sections import extract_links
S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
CASES = [
    ("https://www.ai.ch/themen/bildung/eltern-und-schule/ferienplan", [r"\.pdf/download$"]),
    ("https://www.ai.ch/themen/steuern/publikationen/merkblaetter-ab-steuerperiode-2026", [r"\.pdf/download$"]),
    ("https://ar.ch/verwaltung/departement-bildung-und-kultur/amt-fuer-volksschule-und-sport/ehandbuch-volksschule/schulbetrieb/regelungen/", []),
    ("https://ar.ch/verwaltung/departement-finanzen/steuerverwaltung/gesetzeweisungenmerkblaetter/", []),
    ("https://www.fr.ch/impots/personnes-physiques/impot-des-personnes-physiques-themes-particuliers", [r"^https://www\.fr\.ch/document/\d+$"]),
    ("https://www.glarus-nord.ch/online-schalter/bildung/ferienplan-wichtige-termine.html/2648", []),
    ("https://www.lugano.ch/la-mia-citta/amministrazione/legislazione.html", [r"^https://www\.lugano\.ch/law/\d+/"]),
    ("https://www.ne.ch/themes/impots/documents-et-liens-utiles", []),
    ("https://www.nw.ch/biddirektionssekrdienste/520", [r"^https://www\.nw\.ch/_docn?/\d+"]),
    ("https://www.nw.ch/obgrechtsprechung", [r"^https://www\.nw\.ch/_docn?/\d+"]),
    ("https://www.ow.ch/dienstleistungen/5276", [r"^https://www\.ow\.ch/_docn?/\d+"]),
    ("https://www.ow.ch/_rte/dienst/5276", [r"^https://www\.ow\.ch/_docn?/\d+"]),
    ("https://www.ow.ch/steuern/3517", [r"^https://www\.ow\.ch/_docn?/\d+"]),
    ("https://www.ur.ch/_rte/dienst/3869", [r"^https://www\.ur\.ch/_docn?/\d+"]),
    ("https://www.ur.ch/_rte/dienst/3125", [r"^https://www\.ur\.ch/_docn?/\d+"]),
    ("https://www.ur.ch/_rtr/publikation_4903", [r"^https://www\.ur\.ch/_docn?/\d+"]),
    ("https://www.ur.ch/_rte/publikation/42868", [r"^https://www\.ur\.ch/_docn?/\d+"]),
    ("https://www.ur.ch/rechtsprechung", [r"^https://www\.ur\.ch/_docn?/\d+"]),
    ("https://www.ur.ch/amtsblatt", [r"^https://www\.ur\.ch/_docn?/\d+"]),
    ("https://www.thun.ch/reglementeverordnungen", [r"^https://www\.thun\.ch/_docn?/\d+"]),
    ("https://www.stadt-schaffhausen.ch/rechtssammlung", [r"^https://www\.stadt-schaffhausen\.ch/_docn?/\d+"]),
    ("https://www.sg.ch/recht/gerichte/informationen---formulare/merkblaetter.html", []),
    ("https://www.sg.ch/steuern-finanzen/steuern/steuerbuch/inhaltsverzeichnis.html", []),
    ("https://so.ch/verwaltung/departement-fuer-bildung-kultur-und-sport/volksschulamt/aktuell/ferienplan/", []),
    ("https://stadtrecht.bern.ch/", []),
    ("https://stadtrecht.bern.ch/lex-151_21", []),
    ("https://stadtrecht.bern.ch/dgn-lex_901_1", []),
    ("https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung.html", []),
    ("https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung/7/712/110.html", []),
    ("https://bezirksgericht.tg.ch/arbon/merkblaetter.html/5652", []),
    ("https://www4.ti.ch/decs/cosa-facciamo/calendario-scolastico/2026-2027", []),
    ("https://www4.ti.ch/dfe/dc/dichiarazione/istruzioni-pf/istr-pf-attuale", []),
    ("https://zg.ch/de/bildung/bildungssystem/schulferien", []),
    ("https://zg.ch/de/natur-umwelt-tiere/veterinaerwesen/hunde", []),
    ("https://www.jura.ch/fr/Autorites/JUST/Instances-judiciaires/Tribunal-cantonal/Circulaires/Circulaires-du-Tribunal-cantonal-et-de-ses-sections.html", []),
    ("https://www.jura.ch/fr/Autorites/Administration/DFI/CTR/Formulaires/Formulaires-personnes-physiques/Annee-fiscale-2025/Annee-fiscale-2025.html", []),
    ("https://www.neuchatelville.ch/votre-commune/reglementation", []),
    ("https://www.neuchatelville.ch/votre-commune/reglementation/anciennes-communes/reglementation-neuchatel", []),
    ("https://www.vernier.ch/administration-et-autorites/reglements-communaux", []),
    ("https://www.vernier.ch/administration-et-autorites/publications?category=38&profile=_all", []),
    ("https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux", []),
    ("http://www.lausanne.ch/apps/actualites/index_recueil.php", [r"serve\.php\?id=\d+&kind=recueil"]),
    ("https://rsju.jura.ch/fr/Sommaire/Journal-officiel.html", []),
    ("https://www.chaux-de-fonds.ch/rapports-et-reglements/reglementation", []),
    ("https://www.faovd.ch/rubrique/communes/", []),
    ("https://www.schulen-aargau.ch/regelschule/schulorganisation/planung-ressourcen/stunden-ferienplanung", []),
]
for url, pats in CASES:
    if url not in idx:
        print(f"### NOT SAVED {url}"); continue
    html = open(idx[url], "rb").read().decode("utf-8", errors="replace")
    meta = page_meta(html, url, pdf_link_patterns=pats)
    links = extract_links(html, url)
    print(f"### {url}\n    pdf_links={len(meta.pdf_links)} links={len(links)} bytes={len(html)} patterns={pats}")
    for href, text in meta.pdf_links[:6]:
        print("      ", href[:150], "|", text[:50])
    if len(meta.pdf_links) > 6:
        print("       ...")
