# Scope

This file declares what the Swiss Grounding MCP answers and what it does not. It is meant for anyone
writing evaluation questions against the server: a question inside this scope should come back with
`results` and citations; a question outside it should come back with `outside_scope`, `needs_location`
or `no_evidence`, and that refusal is the correct answer.

It describes the corpus in release
[`corpus-full-sources-described-2026-09-25`](https://github.com/thedionysus/swisscom-hackathon/releases/tag/corpus-full-sources-described-2026-09-25)
(every searchable passage has a description and an embedding). Older dumps (`corpus-latest`,
`corpus-run3-cleaned-2026-09-25`) hold less; see [Which database](#which-database) below.

## In one paragraph

Swiss public-administration information, in German, French, Italian, English and Romansh: federal law
and what federal offices publish, for all of Switzerland; cantonal procedures and rules, deepest for
Zurich, Bern, Vaud, Geneva, Ticino and Graubünden; municipal services for Zürich, Bern, Lausanne,
Genève, Lugano, Chur, Scuol and the communes of canton Fribourg; three live lookups (health insurance
premiums 2026, public transport connections, the mortgage reference interest rate); and, with the
zbern.ch tools, the federal Parliament and federal popular votes. Every answer cites official pages.
The server tells you what the rules are and where to find them. It does not compute personal amounts,
look up individual companies or give live weather or statistics.

## Size of the corpus

| | Count |
|---|---|
| Sources | 252 (250 with content) |
| Current documents | 44,897 |
| Searchable passages | 270,835, all described and embedded |
| Federal passages | 99,605 (Fedlex alone: 52,618) |

## Coverage by level

Coverage is declared in three tiers. Write most questions against Tier 1.

### Tier 1: deep coverage (target these)

**Federal, for all of Switzerland.** No place needs to be named.

| Area | Main sources |
|---|---|
| Federal law text (about 37 acts: ZGB, OR, SVG, AHVG, AVIG, KVG, ArG, AIG, MWSTG, …) in de/fr/it/en | Fedlex |
| Citizen guidance on everyday procedures | ch.ch |
| Old-age and disability insurance, family allowances, EO | AHV/IV, BSV |
| Unemployment, job search, labour law, working hours | SECO, arbeit.swiss |
| Health insurance (obligations, premium reduction, deductibles) | BAG |
| Residence permits, visas, naturalisation, asylum | SEM |
| Renting, notice periods, reference interest rate | BWO |
| VAT, company founding, commercial register (how it works) | ESTV, KMU admin, EHRA |
| Customs and imports | BAZG |
| Road traffic, driving licences, vehicles | ASTRA |
| Popular votes and political rights (explanations, how to vote) | Federal Chancellery |
| Natural hazards guidance | MeteoSwiss |
| Accident insurance, Swiss abroad, cybersecurity, energy, ID documents | Suva, FDFA, NCSC, SFOE, fedpol |

**Cantons Zurich, Bern, Vaud, Geneva, Ticino, Graubünden.** Cantonal administration portals: taxes and
tax returns, driving licence and vehicle office, residence and registration, schools and school
holidays, social assistance, building permits, dogs, courts and cantonal law.
Deepest: Zurich (14,211 passages), Vaud (7,735), Geneva (4,286), Ticino (3,848). Bern (1,079) and
Graubünden (1,958) are thinner, so keep Bern and Graubünden questions to common procedures.

**Municipalities Zürich, Bern, Lausanne, Genève, Lugano, Chur, Scuol.** Municipal services:
waste collection and recycling, registration with the residents' office, dog registration and tax,
school holidays and schools, parking, local fees, municipal regulations (Lugano).

### Tier 2: covered, less deep

These have content and the server names them in its scope text at start, but coverage is narrower.
Questions here are fair, but expect fewer and more specific citations.

- **The other 20 cantons**, mostly through tax handbooks, road-traffic offices, courts, dog rules and
  school holidays: Thurgau (22,537 passages, mostly court rulings), Lucerne, St. Gallen, Jura, Neuchâtel,
  Fribourg, Solothurn, Zug, Aargau, Basel-Stadt, Appenzell Ausserrhoden, Appenzell Innerrhoden, Valais,
  Obwalden, Schwyz.
- **About 110 communes of canton Fribourg** (Fribourg, Bulle, Villars-sur-Glâne, Marly, Morat/Murten,
  Estavayer, Val-de-Charmey, Riaz, …): municipal services, in French or German.
- **St. Gallen and Basel city**: waste collection dates and areas only.
- **Other institutions**: diploma recognition (EDK, swissuniversities ENIC, SBFI), IV Bern, Swiss Red
  Cross health professions, Swiss hiking trails, Tox Info Suisse, UZH and ETH calendars, Pronovo (solar
  subsidies).

### Tier 3: present but too thin to evaluate on

Glarus, Nidwalden, Uri, Basel-Landschaft (under 200 passages each); Winterthur (statistics pages
only); Vernier. School holidays for Jura, Neuchâtel, Bern canton, Thurgau and Lucerne are single
pages. Aargau school holidays and the City of Neuchâtel regulations are empty.

## Lookup tools

| Tool | Answers | Limits |
|---|---|---|
| `swiss_premium` | Cheapest compulsory health insurance premiums for a **municipality**, age and deductible | Year 2026 only; a municipality, not a canton; the deductible must exist for the age class |
| `swiss_connections` | Public transport connections between two Swiss stops | Up to 6 connections; live from transport.opendata.ch |
| `swiss_reference_rate` | The current mortgage reference interest rate for rents | Current value only |
| `swiss_get_document` | The text of a cited document or a law article ("Art. 336c OR", "SR 741.51 Art. 44") | Documents in the corpus |
| `zbern_*` | Federal Parliament members, business items, transcripts, roll-call votes, federal vote results down to municipality, upcoming votes | Only when the server runs with `ZBERN_MCP_TOKEN` |

## Languages

Questions may be asked in German, French, Italian, English or Romansh. The server searches all
language versions of a source and cites passages in the language of the question where one exists.
Results are strongest when the question is asked in the place's own language (French for Lausanne or
Geneva, Italian for Lugano). Romansh questions are answered by embedding search only, so ranking is
weaker.

## Not covered

A question on one of these is expected to be refused. The server answers `outside_scope`, `needs_location`
or `no_evidence`; the table says which.

| Not covered | Example | Expected status |
|---|---|---|
| Places outside Switzerland | "Rundfunkbeitrag nach meinem Umzug nach Konstanz?" with `locations=["Konstanz"]` | `outside_scope` |
| Place-dependent question with no place given | "Wann wird bei mir das Altpapier abgeholt?" | `needs_location` |
| Computed personal amounts: a tax bill, a pension amount, a benefit total | "Wie viel Steuern zahle ich bei 90'000 Fr. in Schaffhausen?" | `no_evidence` (the rules and the official calculator may be cited instead) |
| Looking up a specific company | "Ist die Muster Bau GmbH im Handelsregister eingetragen?" | `no_evidence` |
| Live weather forecasts, statistics, geodata | "Wie wird das Wetter morgen in Zürich?" | `no_evidence` |
| Private-sector information: prices, opening hours of shops, product advice | "Welcher Handyanbieter ist am günstigsten?" | `no_evidence` |
| Legal advice on an individual case | "Gewinne ich meinen Prozess gegen den Vermieter?" | The applicable rules are cited, not a verdict |

Excluded topics are refused because nothing relevant is retrieved, not by a dedicated filter. When a
general official page on the topic exists (for example how the commercial register works, or MeteoSwiss
hazard levels), the server cites it and answers `results`.

## Writing questions against this scope

1. **Name the place** for anything cantonal or municipal (waste, dogs, school holidays, registration,
   cantonal taxes, driving licence office). Without a place the correct answer is `needs_location`.
   Say which level is meant: "Stadt Zürich" or "Kanton Zürich".
2. **Use a Swiss place the server knows** and spell it as it is spelled officially. An unknown or
   misspelled place is treated as outside Switzerland and answered `outside_scope`. Disambiguate
   duplicate names ("Wil SG", "Buchs AG").
3. **Ask for the rule, the procedure, the deadline or the office**, not for a personal calculation.
   "Welche Abzüge für Kinder gibt es im Kanton Bern?" is in scope; "Wie viel Steuern spare ich?" is not.
4. **Federal questions need no place.** "Kündigungsfrist einer Mietwohnung" is answered from the OR
   for anywhere in Switzerland, including communes not listed here.
5. **Weight the question set toward Tier 1**, keep Tier 2 to common procedures, and do not write
   questions whose answer depends on Tier 3 content.
6. **For lookups, give the tool's inputs**: municipality, age and deductible for premiums; two stops
   for connections.

### Examples in scope

| Question | Level |
|---|---|
| Ab welchem Alter erhalte ich eine AHV-Altersrente? | Federal |
| À partir de quel chiffre d'affaires une entreprise doit-elle s'inscrire à la TVA? | Federal |
| What is the notice period for an employment contract after three years of service? | Federal |
| Qual è il termine di disdetta per un appartamento in affitto? | Federal |
| Wie viel Stammkapital braucht man für die Gründung einer GmbH? | Federal |
| Wie oft finden eidgenössische Volksabstimmungen statt? | Federal |
| Brauche ich eine Kontrollfahrt, um meinen ausländischen Führerausweis im Kanton Zürich umzutauschen? | Canton ZH |
| Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps? | Canton VD |
| Wie beantrage ich im Kanton Graubünden eine Fristerstreckung für die Steuererklärung? | Canton GR |
| Quelles sont les dates des vacances scolaires 2026 à Genève? | Geneva |
| Innerhalb welcher Frist muss ich meinen Hund in der Stadt Zürich anmelden? | City of Zürich |
| Dans quel délai dois-je m'annoncer au contrôle des habitants après mon arrivée à Lausanne? | Lausanne |
| Quando sono le vacanze autunnali 2026 per le scuole di Lugano? | Lugano |
| Cura èn las vacanzas d'atun 2026 per la scola da Scuol? | Scuol |
| Günstigste Prämie in Chur, 30 Jahre, Franchise 2500? | `swiss_premium` |
| Wie hoch ist der aktuelle Referenzzinssatz? | `swiss_reference_rate` |

## Which database

At start the server reads which cantons and municipalities its database holds passages for and adds
them to the scope text that `swiss_scope` returns. The six cantons and seven municipalities of Tier 1
are always named. A canton with more than ten added municipalities (Fribourg) is named with a count.
Against the release above, `swiss_scope` therefore names all 26 cantons and the Fribourg communes.
Against an older dump it names less, and questions about the missing places are answered
`outside_scope`. Evaluate against the release named at the top of this file; the restore steps are in
the README.

The full list of sources, with URLs and languages, is in
[`manifests/declared-scope.yaml`](manifests/declared-scope.yaml). Per-source counts are in the release
file `counts-per-source-full-described-2026-09-25.tsv`.
