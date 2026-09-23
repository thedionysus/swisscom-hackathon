# Coverage ledger: were all the links you gave me tested? (2026-09-23)

**Answer: no.** The AI Mode list was covered. Most of the open-data list was never opened individually. Half of the handoff's leads are open.
Link-level data: `ledger_ai_mode.csv` (56 rows), `ledger_awesome.csv` (385 rows, with triage), `ledger_handoff.csv` (16 rows).

How "checked" was decided: a link counts as checked only when a request to that exact page or its API is recorded. The records are the
2026-09-23 group reports, the main session's own spot-checks, or `docs/sources/ogd_lists_assessment.md` (2026-09-22), with the line cited.
A host that is merely *named* in a document does not count. Five such false matches were removed by hand
(e.g. `ag.ch` inside "suigeneris-verl**ag.ch**"; the assessment line for ortsnamen.ch reads "*Not tried*").

## 1. AI Mode answers (56 entries)
| Status | Count | Entries |
|---|---|---|
| Checked 2026-09-23 | 49 | U1–U13, D1, D3–D17, D19–D27, C1–C3, C6–C9, C11–C14 |
| Checked 2026-09-22 | 1 | U14 (opendata.swiss) |
| Partly | 1 | D2 swisstopo: postcode directory only, boundaries not fetched |
| Not fetched | 1 | D18 GE vehicle office: G5 inferred the format without fetching |
| Closed without a request | 4 | C4 Wikipedia, C5 CRW Flags, C10 Splash-DB, D28 Bio Suisse (not sources) |

Smaller leftovers: Bezirk March (JS, unresolved), the BS dog PDFs (text layer not checked).

## 2. Open-data list, awesome-ogd-switzerland (385 links, 299 hosts)
| Status | Links |
|---|---|
| Checked 2026-09-23 | 25 |
| Checked 2026-09-22 | 21 |
| Named 2026-09-22 but never tested (entscheidsuche, onlinekommentar, ortsnamen, LINDAS, OpenPLZ) | 9 |
| **Set aside by category on 2026-09-22, never opened** (§7: statistics, geodata, health, energy, transport, research, heritage, international, tools, organisations, media…) | **254** |
| **Never checked, no category verdict either** | **64** |
| Not a data link (badges, licence pages) | 12 |

**Triage of the 327 unopened links (my inference, per link in the CSV):**
| Next step | Links | What |
|---|---|---|
| **R-GEO: test** | 36 | the 26 cantonal geoportals + the KGK directory of all geoportals, geoportal.ch, geocat, geo.admin, swisstopo, Stadt Zürich geodata. Look for rule layers and legal-document links (the ÖREB/geodienste lesson). Also covers D2 |
| **R-FED: test** | 12 | SLF avalanche, MeteoSwiss warnings, hydrodaten flood levels (safety); BAG, swissmedic (health); BWO (housing: tenancy, reference rate); tourismdata, MySwitzerland, Zürich Tourismus (hiking) |
| **R-PORTALS: test** | 6 | AG data portal, ZH open-data catalogue, Glarus organisation, TI and VS pages, Stadt Zürich LOD |
| **R-COURTS: test** | 5 | entscheidsuche (+ its scraper repo, which lists the court portals), onlinekommentar (+ API), the CLDS UZH database list |
| **R-RESOLVE: check** | 7 | ortsnamen (3), OpenPLZ, LINDAS (2), the GWR building register |
| Not relevant | 261 | statistics (numbers, not rules), international, media, events, tools, heritage, research, energy |

Important: the 2026-09-22 category verdict already failed once. "Geodata / ÖREB: not useful" turned out wrong for ÖREB and geodienste
legal-document links. That is why the geoportals are back in R-GEO.

## 3. Handoff leads (section 5)
| Status | Items |
|---|---|
| Done | 1 (7 LexWork + 4 other cantonal platforms), 2 (Winterthur, Luzern, St. Gallen, Biel via tlex), 4 (ZH GE BE BS guidance + federal soft law), 5 (commune_sites.csv), 6 (city data portals) |
| Partly | 5: opendata.swiss organisations (search used; the full organisation list not walked) |
| **Open, and I have links** | 5: open-ius.ch `/gesetzgebung` `/rechtsprechung` `/literatur` · 7: OpenPLZ, ortsnamen, I14Y, SITG licence · 5: ch.ch outbound links (ch.ch is already a source, so they can be extracted mechanically) |
| **Open, and links are needed** | 2: city law of Zürich, Bern, Lausanne, Lugano · 3: courts per canton · 4: guidance in the other 22 cantons · 5: the 26 chancellery link pages · 8: Wikidata idea |
| Not re-audited here | the awesome-open-legal-switzerland list (114 links, assessed 2026-09-22) |

## 4. Search sentences for the areas without links
Each sentence asks for **full URLs**, because the AI Mode answers last time shortened most links to bare domains.

- **S1 Courts (in scope as `official_info`):** "For each of the 26 Swiss cantons, list the official websites of the cantonal courts: the
  Obergericht or Kantonsgericht, the Verwaltungsgericht, and the district courts (Bezirksgerichte / tribunaux d'arrondissement).
  For each court give the full URL (https://…) of its page on court fees (Gerichtsgebühren / émoluments), its guidance pages for residents
  (family, tenancy, employment, debt collection) and its page of published decisions. One row per court; full URLs only, no bare domains."
- **S2 City law collections:** "Give the full URL (https://…) of the official systematic law collection (Systematische Rechtssammlung /
  Amtliche Sammlung / recueil systématique / raccolta delle leggi) of each of these Swiss cities: Zürich, Genève, Lausanne, Bern, Lugano,
  Thun, La Chaux-de-Fonds, Schaffhausen, Vernier, Neuchâtel. I need the page that lists their municipal regulations (dogs, waste, parking,
  police). One line per city with the direct URL, not only the domain."
- **S3a Guidance, German-speaking cantons:** "For the cantons Aargau, Luzern, St. Gallen, Thurgau, Solothurn, Basel-Landschaft, Schwyz,
  Zug, Graubünden, Schaffhausen, Appenzell Ausserrhoden, Appenzell Innerrhoden, Glarus, Uri, Obwalden and Nidwalden, give the full URLs of
  the official cantonal pages on: (1) rules for keeping dogs (Veterinärdienst / Hundegesetz), (2) the tax return guide for private persons
  (Wegleitung / Steuerbuch), (3) school holiday dates (Schulferien), (4) the road traffic office (Strassenverkehrsamt). One row per
  canton and topic; direct URLs only."
- **S3b Guidance, French- and Italian-speaking cantons:** "Pour les cantons de Vaud, Valais, Fribourg, Neuchâtel, Jura et Tessin, donnez
  les URL complètes (https://…) des pages cantonales officielles sur : (1) la détention de chiens, (2) le guide de la déclaration d'impôt
  des personnes physiques, (3) les dates des vacances scolaires, (4) le service des automobiles / la circolazione. Une ligne par canton
  et par sujet, uniquement des URL directes."
- **S4 Cantonal directories:** "For each Swiss canton, give the full URL of (1) the official cantonal page that lists all its communes with
  links to their websites, and (2) the state chancellery (Staatskanzlei / chancellerie d'État) page that links to the canton's law
  collection, official gazette and official publications. One row per canton; direct URLs only."
- **S5 Waste-calendar platforms (optional):** "Which platforms or apps publish waste collection calendars for Swiss communes (for example
  entsorglos.swiss, Sammelkalender, anthrazit, Abfall-App, Züri-Abfall-App)? For each, list the communes that use it and the full URL of each
  commune's calendar page or ICS/iCal export."

## 5. Proposed second run: links only, no open searching
- **Run 2a (can start now, 66 of your links + 3 handoff URLs + 3 leftovers):** R-GEO 36, R-FED 12, R-RESOLVE 7, R-PORTALS 6,
  R-COURTS 5, open-ius ×3, D18 GE vehicle office, Bezirk March, BS dog PDFs. That is 5 agents with brief v4, each given the exact links.
- **Run 2b (after your filtered links from S1–S5):** the same method.
- Or combine both into one run once your links are in.
