# G5 report: cantonal resident guidance ZH/GE/BE/BS (Opus 5.5 agent, 2026-09-23)
Evidence: /tmp/sg-verify-g5-guidance/. Below: the agent's own report file (backup copy).

**Spot-checked by the main session (live curl, 2026-09-23). All matched:**
- zh.ch/de/steuern-finanzen.zhweb-sitemap.xml: 200, 1043 URLs, **159 unique zstb-*.html**. This corrects the pilot, which said no index existed
- ge.ch/document/39777/telecharger: 200 text/calendar, 391,179 B, 10 VEVENTs ("Rentrée scolaire", "Pont du Jeûne genevois")
- data.bs.ch dataset 100397: total_count 88, fields year, name, start_date, end_date, name_short
- taxinfo.sv.fin.be.ch → /taxinfo/<uuid>, 200, contains vike_pageContext
Not re-checked: ZH holiday XLSX, getax.ch 98 pages, BE office sitemaps, BS PDF lists, GE OCV pages.

---
# g5-guidance report (ZH, GE, BE, BS cantonal guidance): taxes, dogs, road traffic, school holidays
All claims below come from curl/python runs on 2026-09-23. Scratch files are in /tmp/sg-verify-g5-guidance/.

## Headline: the pilot's ZH Steuerbuch conclusion was wrong. The entries ARE enumerable from the sitemap.
The zh.ch sitemap `/bin/zhweb/publish/sitemap.xml` is a **sitemap index** with 44 child sitemaps. The child
`https://www.zh.ch/de/steuern-finanzen.zhweb-sitemap.xml` (400 KB, 1,043 locs, all with `<lastmod>`) holds
**404 distinct zstb URLs: 159 HTML entries** (`.../steuerbuch-definition/zstb-<nr>.html`) and 245 PDFs, of which
148 have no "gueltig-bis" in the name, meaning they are current PDF-only or attachment entries. There are also
`ESchG-ZH.html` and `ESchGV-ZH.html`. Sample `zstb-30-1.html`: 65 KB server HTML, 685 words, structured header
"Thema Natürliche Personen · Unterthema Einkommenssteuer (§§ 16 - 37b) · Titel Weisung ... Wertschriften ...
Erlassdatum 27. September 2023 · Gültig ab 27. September 2023 · ZStB-Nummer 30.1 · Nummer alt 18/701", and
sections A–E. → **Yes today (html_crawl), if it is seeded from the sitemap**. A small "sitemap-seeded crawl" helper
is better (see the new fetcher classes). The zh.ch search JSON `/de/suche/_jcr_content/searchoverview.zhweb-search.json`
exists but returned 400 for `q=`/`query=`, and the suggestion endpoint returned 204. It is not needed.

## Cross-cutting: can one "cantonal portal crawler" cover all four cantons?
| Canton | Server HTML? | Sitemap | Site-search API |
|---|---|---|---|
| ZH | yes (AEM; e.g. hunde.html 128 KB, 2,556 words) | robots names the index `/bin/zhweb/publish/sitemap.xml` → 44 per-directorate/topic child sitemaps (`/de/<topic>.zhweb-sitemap.xml`), with lastmod. umwelt-tiere has 7,826 locs, mobilitaet 2,314, bildung 2,311, steuern-finanzen 1,043, sicherheitsdirektion 197. PDFs are listed too. | `searchoverview.zhweb-search.json` answers 400; parameters not found |
| GE | yes (Drupal; detenir-chien 366 words) | `/sitemap.xml` → 14 pages × ≤2,000 = **27,978 URLs** with lastmod. 17,519 `/document/`, 3,643 `/actualite/`, about 4,345 topic pages (top-level slugs such as `/detenir-chien/...`) | `/search/` is disallowed in robots; not probed |
| BE | yes (AEM), but **decentralised**: every directorate/office has its own host (`www.weu.be.ch`, `www.sv.fin.be.ch`, `www.svsa.sid.be.ch`, `www.bkd.be.ch`) | `be.ch/sitemap.xml` covers only be.ch (de 39 URLs, fr 40). Each office host has the same template `/<host>/sitemap.xml` → `/de/sitemap.xml` + `/fr/sitemap.xml`: svsa 229, sv.fin 172, weu 489, bkd 697 (de). robots: `Disallow: /content/`, `Allow: /content/dam/` (be.ch), `Crawl-delay: 10` | not checked |
| BS | yes (Nuxt SSR over Drupal; the text is in the HTML, e.g. anwohnerparkkarte 745 words) | `/sitemap.xml` → 14 pages, **27,209 URLs** with lastmod. 19,856 are medienmitteilungen, 676 `/themen/`. `Crawl-delay: 10` | `/jsonapi` 404, `/graphql` 403, `/api/search` 404 |

**Verdict:** yes. One **sitemap-driven cantonal crawler** works for ZH, GE and BS as they are, and for BE if it is given
a list of office hosts. Config: sitemap URL(s) + URL path allowlist regexes per topic + language + an optional
PDF include. The same crawler also discovers the PDFs (ZH /content/dam, BS media.bs.ch are linked from pages). It must respect Crawl-delay 10 (BE, BS).

**School holidays as .ics / open data:** GE publishes **.ics** (below). BS (data.bs.ch 100397, 88 rows, up to 2032)
and BL (data.bl.ch 13350, 58 rows) are confirmed again live (`total_count` 88 / 58; fields `year,name,start_date,end_date,name_short`
/ `schuljahr,startdatum,enddatum,name`). Both are already in ogd_lists_assessment.md. opendata.swiss `package_search`
for "schulferien OR vacances scolaires" (76 hits) has **no ZH-canton, GE or BE holiday dataset**; the only matches are BS, BL, Stadt SG and Stadt Zürich.
ZH publishes an **XLSX** (below). No ZH .ics was found on the schulferien page (no `.ics` href).

---

### U9 — ZH veterinary PDF "dog rules"
- **AI claim:** ZH dog rules  →  **Claim check:** Wrong. It is a 2-page English PDF (metadata Subject: "Cats and dogs from Ukraine not meeting Swiss import requirements: Guidance for owners and veterinarians", 24 Mar 2022) plus a list of cantonal veterinary office addresses.
- **Real location:** ZH's dog guidance: `https://www.zh.ch/de/umwelt-tiere/tiere/haustiere-heimtiere/hunde.html` and 15 subpages (verbotene-hunderassen, fuer-theoriepruefung-anmelden, cug_hundegesetz-vollzugshilfen-fuer-gemeinden, vorfaelle-mit-hunden-melden …). Found through the umwelt-tiere child sitemap (step 2).
- **What data is there:** Dog-keeping duties, the revised Hundegesetz in force since 1 June 2025 (mandatory theory course for first-time owners, practical course for all dogs), banned breeds, incident reporting, guidance for communes. German.
- **Format:** server HTML. hunde.html 127,766 B, 45 links, 2,556 words. U9 is a PDF with a text layer (337 KB, 2 pages).
- **Sample:** "Seit 1. Juni 2025 ist neue Hundegesetzgebung in Kraft … Wer noch nie einen Hund oder seit mehr als zehn Jahren keinen Hund mehr gehalten hat, muss einen theoretischen Ausbildungskurs besuchen"
- **Dates & jurisdiction:** sitemap lastmod per page; CH-ZH.
- **Authority:** official_info (the law text itself, LS 554.51 Hundeverordnung, is already covered in ogd_lists_assessment.md)   **Categories:** dogs
- **Can we get it?** Yes today (html_crawl)
- **Fetcher hint:** `html_crawl`, `start_paths: [/de/umwelt-tiere/tiere/haustiere-heimtiere/hunde.html]`, `path_allowlist: [/de/umwelt-tiere/tiere/haustiere-heimtiere/hunde]`, language de. Drop U9: it is out of date and off-topic.
- **Related finds:** none beyond the above.
- **Unknowns:** whether the subpages link to one another well enough for html_crawl without sitemap seeding (not tested).

### D15 — ZH Strassenverkehrsamt guidance
- **AI claim:** road traffic office guidance  →  **Claim check:** Partly. It exists, but under /de/mobilitaet/ (topics) and /de/sicherheitsdirektion/strassenverkehrsamt (the office itself), not as one site.
- **Real location:** mobilitaet child sitemap: `fahrzeuge-kontrollschilder` (47 pages), `fuehrerausweis-fahren-lernen` (55), `verkehrsabgaben` (28), plus `.../parkierungserleichterung-beantragen.html`. Fee schedule PDF: `.../strassenverkehrsamt/organisation/ueber-uns-grundlagen/Gebührenverfügung, gültig ab 1. Januar 2026.pdf` (from the sicherheitsdirektion child sitemap).
- **What data is there:** vehicle registration and plates, licences, vehicle tax (Verkehrsabgaben), fees. **Parking rules are municipal.** The canton only handles disabled-parking relief.
- **Format:** server HTML. Fee PDF: 4.3 MB, 16 pages, has a text layer.
- **Sample:** "Verfügung vom 26. November 2025 … Lernfahrausweis 40.00 · Lernfahrausweis — Duplikat 20.00"
- **Dates & jurisdiction:** the fee order is dated 26 Nov 2025, valid from 1 Jan 2026; CH-ZH.
- **Authority:** official_info   **Categories:** vehicles, driving licences, fees
- **Can we get it?** Yes today (html_crawl + pdf)
- **Fetcher hint:** html_crawl with `path_allowlist: [/de/mobilitaet/fahrzeuge-kontrollschilder, /de/mobilitaet/fuehrerausweis-fahren-lernen, /de/mobilitaet/verkehrsabgaben]`. pdf `urls:` [the Gebührenverfügung URL]; the filename changes each year, so discovery comes from the sitemap.
- **Unknowns:** did not sample a verkehrsabgaben page.

### D16 — ZH school holidays
- **AI claim:** .ics files exist  →  **Claim check:** Wrong about .ics (no `.ics` href on the page). There is something better: an **XLSX covering every school community in the canton**.
- **Real location:** `https://www.zh.ch/de/bildung/bildungssystem/schulferien.html` (server HTML, 36 links, 1,764 words) →
  `.../schulferien/volksschulen/schulferien_ganzer_kanton_zuerich_2025_2026.xlsx` (92 KB); `feriendaten_empfehlung_bis_2033.pdf` (4 pages, text layer); Mittelschulen and Berufsfachschulen PDFs, one per school year from 2026/27 to 2032/33 (for example `Ferien_Mittelschulen_SJ_2026_2027.pdf`, 3 pages, text layer).
- **What data is there:** The page says Volksschulen set their own holidays. Only the school start and Christmas are binding. The XLSX lists, per **Schulgemeinde** (sheet "Kanton" 194 rows, 185 data rows, plus one sheet per district: Zürich, Dietikon, Affoltern …), columns `GdeNr` (internal code such as A01), `Bezirk`, `Typ`, `Sgde` (name), and from/to pairs for Herbst, Weihnachten, Sport, Frühling, Heuen, Sommer. Dates are Excel serials (45936 = 2025-10-06).
- **Format:** XLSX (one per school year) + PDF text
- **Sample:** row `('A01','Zürich','KSB','Zürich-Uto', 45936, 45947, 46013, 46024 …)`, i.e. autumn holidays 6–17 Oct 2025.
- **Dates & jurisdiction:** event dates per school community. **Schulgemeinden are not BFS communes.** Some cover several communes, and Stadt Zürich has 7 Schulkreise. A mapping Sgde→BFS is needed; this was not verified. PDFs → CH-ZH.
- **Authority:** official_info   **Categories:** schools/holidays
- **Can we get it?** Yes with a new fetcher (XLSX). The PDFs work today (pdf).
- **Fetcher hint:** "XLSX table" fetcher: discover the `.xlsx` href on schulferien.html (the name carries the year), read the sheet "Kanton", header row 3, one event per (Sgde, holiday) pair, id `{GdeNr}-{holiday}-{von}`, title "Schulferien {holiday} {Sgde}". Needs a Schulgemeinde→BFS map (for PSP/KSB types the name usually equals the commune; *inferred, not verified*). Only the current year is published (2025/26). Stadt Zürich is already covered by CKAN (assessment).

### ZH Steuerbuch enumeration (pilot extension): see the headline. **Solved via the steuern-finanzen child sitemap.**

### U10 — GE Guide fiscal 2025 particuliers
- **AI claim:** tax guide with web and PDF editions  →  **Claim check:** Confirmed.
- **Real location:** landing `https://www.ge.ch/document/guide-fiscal-2025-particuliers` (server HTML, 92 words, "Date de publication 27 janvier 2026", author AFC). PDF `https://www.ge.ch/document/41995/annexe/file/573038` (4.0 MB, 62 pages, 33 outline bookmarks, text layer). **Web edition** `https://www.getax.ch/support/guide/declaration2025/` (one hop): server HTML, 260 links, 98 relative chapter pages (`Deductionsdesfraismedicaux.html` …).
- **What data is there:** complete French filling guide for the 2025 personal tax return: deductions with worked examples, per-page instructions.
- **Format:** server HTML (getax.ch; the chapter page has 356 words) + PDF text
- **Sample:** "ICC Revenu seule la part qui dépasse le 0.5% du revenu net … IFD seule la part qui dépasse le 5% … Frais médicaux déductibles 7'000.– moins 300.– 6'700.–"
- **Dates & jurisdiction:** tax year 2025, published 27 Jan 2026; CH-GE.
- **Authority:** official_info (the getax.ch page title says "Administration fiscale cantonale de Genève"; that getax.ch is operated by the AFC is inferred from that title)   **Categories:** taxes
- **Can we get it?** Yes today
- **Fetcher hint:** `html_crawl` start `https://www.getax.ch/support/guide/declaration2025/`, `path_allowlist: [/support/guide/declaration2025/]`, language fr. One chapter per page gives clean sections. The year sits in the path, so re-point it each year. Alternative: `pdf` with the attachment URL.
- **Unknowns:** whether earlier-year guides stay online.

### D17 — GE dog rules (SCAV, "détenir un chien")
- **AI claim:** SCAV dog rules  →  **Claim check:** Confirmed.
- **Real location:** GE sitemap (step 2): `/detenir-chien` + 7 subpages (`declarer-mon-chien`, `obtenir-marque-controle`, `regles-promener-son-chien`, `races-canines-interdites-geneve`, `espaces-liberte-parcs-publics-interdits-aux-chiens`, `cours-education-canine-tmc`, `etapes-vie-mon-chien`), `/impot-chiens` + 3, `/agressions-canines/*`, `/cohabiter-avec-faune-sauvage/se-promener-avec-chien-dans-nature`. In total about 30 dog URLs among the topic pages.
- **What data is there:** AMICUS registration, the control tag (from 1 April), leash rules by place and season, banned breeds, dog tax.
- **Format:** server HTML (detenir-chien 366 words; regles-promener 373 words)
- **Sample:** "Toujours en laisse : Dans les localités et sur les voies de circulation … En forêt du 1er avril au 15 juillet … Dans les campings"
- **Dates & jurisdiction:** sitemap lastmod; CH-GE.
- **Authority:** official_info (the law is M 3 45 on silgeneve, already in the assessment)   **Categories:** dogs, dog tax
- **Can we get it?** Yes today (html_crawl)
- **Fetcher hint:** html_crawl `start_paths: [/detenir-chien, /impot-chiens, /agressions-canines]`, `path_allowlist` the same prefixes, language fr.

### D18 — GE Office cantonal des véhicules (OCV)
- **AI claim:** OCV guidance  →  **Claim check:** Partly. The OCV has no site of its own in the sitemap. Its services are ge.ch topic pages.
- **Real location:** `/plaques` (+6), `/immatriculer-vehicule-obtenir-carte-grise`, `/passer-son-permis-conduire` (+2), `/echanger-son-permis-conduire-etranger`, `/impot-vehicules`, `/impot-vehicules/baremes-impot`, `/stationner-geneve/*` (3: reserving public spaces, health professionals, disabled). All come from the GE sitemap grep (step 2).
- **What data is there:** plates, registration, licences, vehicle tax rates, some parking permits.
- **Format:** server HTML (same Drupal template as D17; the OCV pages themselves were not sampled)
- **Dates & jurisdiction:** CH-GE
- **Authority:** official_info   **Categories:** vehicles, parking, vehicle tax
- **Can we get it?** Yes today (html_crawl)
- **Fetcher hint:** html_crawl with allowlist `[/plaques, /immatriculer-vehicule, /passer-son-permis-conduire, /impot-vehicules, /stationner-geneve]`.
- **Unknowns:** no OCV page was fetched. The format is inferred from the shared template. Residents' parking cards (macaron) are not found in the sitemap under "macaron".

### D19 — GE school holidays
- **AI claim:** "vacances scolaires"  →  **Claim check:** Confirmed, and there is **.ics**.
- **Real location:** `https://www.ge.ch/vacances-scolaires-jours-feries` (dates "fixées jusqu'à 2030") → per-year HTML pages `/vacances-scolaires-jours-feries/vacances-scolaires-2026-2027` … `2029-2030`. ICS document pages in the sitemap: `/document/ics-calendrier-vacances-scolaires-2024-2025-0`, `/document/ics-calendrier-vacances-2025-2026`, `…-2026-2027`, `/document/ics-calendrier-vacances-scolaires-2027-2028` … `2030-2031`. Each document page links `/document/<n>/telecharger` (e.g. 39777 for 2027-28).
- **What data is there:** 10 VEVENTs per school year (rentrée, Pont du Jeûne genevois, autumn, Christmas …), primary and secondary schools, French.
- **Format:** ICS (`text/calendar`, 391 KB, Outlook-generated, `DTSTART;VALUE=DATE`) + server HTML + PDF
- **Sample:** `DTSTART;VALUE=DATE:20271025 / DTEND;VALUE=DATE:20271030 / SUMMARY;LANGUAGE=fr-ch:Vacances d'automne`
- **Dates & jurisdiction:** event dates; document "Date de publication 25 juin 2025"; CH-GE.
- **Authority:** official_info (DIP)   **Categories:** schools/holidays
- **Can we get it?** Yes with a new fetcher (ICS). The HTML year pages work today via html_crawl.
- **Fetcher hint:** "ICS calendar" fetcher: enumerate `/document/ics-calendrier-vacances*` from the sitemap, take the `/document/<n>/telecharger` href, parse VEVENTs → one event each (id = UID or `{DTSTART}-{SUMMARY}`, `event_date` = DTSTART). Note: DTEND is exclusive.

### D20 — BE tax guide (Steuerbuch / TaxInfo)
- **AI claim:** Steuerbuch / TaxInfo  →  **Claim check:** Confirmed. The real system is **TaxInfo**.
- **Real location:** `https://www.taxinfo.sv.fin.be.ch/` → redirects to `/taxinfo/ca95ca72-…` (a "phonemos" wiki). Topic roots: "1. Allgemeines" … "11. Erbschafts- und Schenkungssteuern", "Inhalte nach Formularen" (Formular 1–10), "Gesetzgebung", "Aktuell". Also `www.sv.fin.be.ch/de/start/publikationen/wegleitungen*.html` (Wegleitungen 2020–aktuell, from its sitemap).
- **What data is there:** the BE tax practice handbook: articles such as "Fahrkosten für den Arbeitsweg", "Kinderabzug – Ermittlung der anwendbaren Tarifkolonne", "Abzüge auf einen Blick" (with a Steuerjahr 2002–2026 selector), "Steuergesetzrevision 2027". A BFS crawl by link over 330 s fetched **407 pages with 184 still queued (so ≥591 pages)**. 240 of the 407 have more than 20 text nodes. de + fr.
- **Format:** SSR HTML (vike/React). Each page (130–460 KB) embeds `<script id="vike_pageContext" type="application/json">` with `pageProps.wikipage {lang,title,content}`, where content is a ProseMirror JSON tree (headings/paragraphs). Links are `/taxinfo/<uuid>`.
- **Sample:** titles: "2. Einkommens- und Vermögenssteuern", "Fahrkosten für den Arbeitsweg", "Wichtigste Neuerungen im Steuerjahr 2026"
- **Dates & jurisdiction:** no date field in the `wikipage` object. Tax years appear in the content. CH-BE.
- **Authority:** official_info   **Categories:** taxes
- **Can we get it?** Yes with a new fetcher (html_crawl would see links and text, but the pages carry a large data:image and navigation noise; a JSON extractor is cleaner)
- **Fetcher hint:** "phonemos wiki" fetcher: BFS from the start UUID over `href="/taxinfo/<uuid>"`, parse `vike_pageContext.pageProps.wikipage`, split sections by ProseMirror `heading` nodes, id = UUID, title = `wikipage.title`, languages via `name[]` (de/fr). About 600 or more pages; use 0.15 s or more between requests.
- **Ladder log:** 1 curl → redirect to the wiki; 2 robots/sitemap on the taxinfo host → `/sitemap.xml` returns HTML (the app shell), no sitemap; 4 embedded JSON found (vike_pageContext) → used.
- **Unknowns:** the start page says "TaxInfo intern und Gemeinden … für den internen Gebrauch", although it is served publicly without login. **Check whether a separate public view is the intended one** (the link on the page points back to www.taxinfo.sv.fin.be.ch). Full page count not reached.

### D21 — BE dogs / pets guidance
- **AI claim:** dogs guidance  →  **Claim check:** Confirmed, on `www.weu.be.ch` (LANAT/veterinary service), not be.ch.
- **Real location:** from the weu.be.ch/de/sitemap.xml grep: `/de/start/themen/veterinaerwesen/hunde-im-kanton-bern.html` + 6 subpages (`einen-hund-kaufen-halten`, `hundegesetz-kanton-bern`, `ausfuehren-von-mehr-als-drei-hunden`, `dogsitting`, `meldung-vorfall-mit-hunden` …).
- **Format:** server HTML (einen-hund-kaufen-halten: 262 KB, 39 links, 328 words)
- **Sample:** "Möchten Sie einen Hund kaufen? Die Anforderungen an Sie als Hundehalterin oder Hundehalter sind hoch."
- **Dates & jurisdiction:** CH-BE. The law (916.31 Hundegesetz) is already in the assessment.
- **Authority:** official_info   **Categories:** dogs
- **Can we get it?** Yes today (html_crawl on host www.weu.be.ch, allowlist `/de/start/themen/veterinaerwesen/hunde-im-kanton-bern`; French via `/fr/sitemap.xml`)
- **Unknowns:** dog tax in BE is municipal (not verified here).

### U11 — BE SVSA (road traffic office)
- **AI claim:** parking and vehicles  →  **Claim check:** Partly. Vehicles and licences: yes. **Parking: no** (no parking URL among the 229 de sitemap URLs; parking is municipal).
- **Real location:** `https://www.svsa.sid.be.ch/` → `/de/start.html` (155 KB). Sitemap `/de/sitemap.xml`, 229 URLs: fahrzeuge/nummernschilder (15), fahrzeug-anmelden (11), fuehrerausweise/* (≈30), schifffahrt (≈40), `fahrzeuge/steuern-gebuehren/fahrzeugsteuer.html`, `lsva`, `psva`, `fuehrerausweise/rund-um-fuehrerausweis/gebuehren.html`, `lernfahrer/gebuehren.html`.
- **Format:** server HTML (sample page 156 KB, 34 links, 654 words)
- **Dates & jurisdiction:** CH-BE
- **Authority:** official_info   **Categories:** vehicles, vehicle tax, fees, boats
- **Can we get it?** Yes today (html_crawl, host www.svsa.sid.be.ch, allowlist `/de/start/fahrzeuge`, `/de/start/fuehrerausweise`, `/de/start/lernfahrer`)

### D22 — BS "Steuerwissen A–Z"
- **AI claim:** Steuerwissen A–Z  →  **Claim check:** Wrong (outdated). `www.steuerverwaltung.bs.ch/steuerwissen/quellensteuer.html` and `/steuerwissen.html` both **redirect to `https://www.bs.ch/fd/steuerverwaltung`**. No "steuerwissen" URL exists among the 27,209 bs.ch sitemap URLs.
- **Real location:** `bs.ch/themen/arbeit-und-steuern/steuererklaerung/steuererklaerung-natuerliche-person/` subpages: `wegleitungen-und-formulare-fuer-natuerliche-personen` (38 media.bs.ch PDFs, including `15500-fw-np-ste-25-05-wegleitung-bf-0.pdf`), `merkblaetter-und-tariftabellen-natuerliche-personen` (23 PDFs, e.g. `17000-steuertarife-2024.pdf`), `fragen-und-antworten`; `bs.ch/fd/steuerverwaltung/steuergesetze` (links to gesetzessammlung.bs.ch + tax treaty PDFs). Found via WebSearch → redirect → page links (steps 3 and 6).
- **What data is there:** the Wegleitung (filing guide), Merkblätter (e.g. expatriate professional costs), tariff tables, FAQ.
- **Format:** server HTML + PDF text (Merkblatt 18024: 6 pages, text layer: "Merkblatt … Besondere Berufskosten von … Expatriates vom 6. Januar 2021")
- **Dates & jurisdiction:** dates inside the PDFs; CH-BS.
- **Authority:** official_info   **Categories:** taxes
- **Can we get it?** Yes today (pdf with listed URLs; html_crawl for the pages). Discovery needs a "PDF index discoverer".
- **Fetcher hint:** PDF index discoverer over the two index pages, collecting `https://media.bs.ch/original_file/<sha>/<name>.pdf`. The names carry a form number and year (`…-25-…`). Filter out the `ansichtsexemplar` forms.
- **Ladder log:** 1 old URL → redirect; 2 sitemap grep "steuerwissen" → 0; 3 WebSearch → the steuerverwaltung.bs.ch result redirects; 6 bs.ch pages → found.
- **Unknowns:** Wegleitung PDF text layer not checked. There is no BS "Steuerbuch" equivalent: a WebSearch returned only BL's Steuerbuch (kanton.baselland.ch), which is out of scope, but it is a lead for BL.

### D23 — BS Veterinäramt dogs
- **AI claim:** Veterinäramt dogs  →  **Claim check:** Confirmed.
- **Real location:** `https://www.bs.ch/gd/veterinaeramt/hundehaltende` (+ `/hundekurse`, `/kind-hund`), `bs.ch/themen/umwelt-und-bauen/tiere-und-pflanzen/hunde` (+ auffaelligehunde, bewilligungspflichtige-hunderassen), `/allgemeines-zu-hunden`, `/hundeareale`. PDFs: `media.bs.ch/…/hundeverbots-und-leinenpflichtzonen.pdf`, `media.bs.ch/…/merkblatt-hundesteuer-2025-26.pdf`.
- **Format:** server HTML (hundehaltende 1,009 words, 22 links); the PDFs were not text-checked
- **Sample:** "Als Grundsatz gilt: Hunde müssen so gehalten und ausgeführt werden, dass durch sie keine Menschen oder Tiere belästigt oder gefährdet werden." / themen page: "Leinenpflicht während der Brut- und Setzzeit vom 1. April bis 31. Juli … Inhalt aktualisiert 26.06.2026"
- **Dates & jurisdiction:** "Inhalt aktualisiert" date on the page; CH-BS (the Hundesteuer merkblatt may differ for Riehen/Bettingen, not checked).
- **Authority:** official_info   **Categories:** dogs, dog tax
- **Can we get it?** Yes today (html_crawl + pdf)

### U13 — BS Motorfahrzeugkontrolle
- **AI claim:** MFK fees and parking permits  →  **Claim check:** Partly. The fees are at MFK. Parking cards are only mentioned there ("Abgabe von 20'000 Parkkarten für die Blaue Zone"); the rules and fees are under `/themen/mobilitaet/fahren-und-parkieren/parkkarten/*`.
- **Real location:** the given URL (102 KB, 284 words) + `…/motorfahrzeugkontrolle/gebuehrenuebersicht-mfk` (416 words); `/jsd/polizei/unsere-hauptabteilungen/verkehr/motorfahrzeugkontrolle/antworten-auf-haeufige-fragen-der-mfk`; parking: `bs.ch/themen/mobilitaet/fahren-und-parkieren/parkkarten/anwohnerparkkarte` (745 words), `…/aerztinnen-und-aerzteparkkarte`.
- **Format:** server HTML (Nuxt SSR)
- **Sample:** "Führerausweis im Kreditkartenformat, Duplikat/Erneuerung … Fr. 40.-"; "Kleine Fahrzeuge (bis 3'899 mm) CHF 47.— [pro Monat] CHF 564.— [pro Jahr] … Bearbeitungsgebühr von Fr. 20.–"
- **Dates & jurisdiction:** CH-BS (Anwohnerparkkarte covers the city of Basel; Riehen/Bettingen coverage not checked)
- **Authority:** official_info   **Categories:** vehicles, fees, parking
- **Can we get it?** Yes today (html_crawl). Related: the data.bs.ch 100329 Parkflächen dataset is already in the assessment.

### D24 — BS school holidays
- **AI claim:** school holidays  →  **Claim check:** Confirmed. `bs.ch/themen/bildung-und-kinderbetreuung/schulferien` (364 words) links to `data.bs.ch/explore/assets/100397`.
- **Format:** JSON (Opendatasoft), `total_count` 88, rows up to 2032 (`{"year":"2032","name":"Sommerferien","start_date":"2032-06-26","end_date":"2032-08-08","name_short":"Sommer"}`)
- **Can we get it?** **Yes today (api)**:
```yaml
fetch_strategy: api
fetch_config:
  url: https://data.bs.ch/api/explore/v2.1/catalog/datasets/100397/records?limit=100&order_by=start_date
  records_path: results
  id_template: "{year}-{name_short}-{start_date}"
  event_date_field: start_date
  title_template: "Schulferien Basel-Stadt: {name} ({start_date} bis {end_date})"
  text_template: "{name} im Kanton Basel-Stadt vom {start_date} bis {end_date}."
  language: de
```
BL is the same: `https://data.bl.ch/api/explore/v2.1/catalog/datasets/13350/records?limit=100`, records_path `results`, fields `schuljahr,name,startdatum,enddatum`, 58 rows. Note that BL includes exception rows such as "Herbstferien Gymnasium Laufental-Thierstein (Ausnahmeregelung)". Jurisdiction CH-BS / CH-BL. Authority official_info.

---

## 1. Summary table
| id | can we get it | format | strategy / new fetcher | value |
|---|---|---|---|---|
| ZH Steuerbuch (pilot ext.) | Yes today | server HTML (159) + PDF (≈148 current) | html_crawl seeded from the steuern-finanzen child sitemap | high |
| U9 ZH "dog" PDF | Yes, but wrong content (Ukraine pets 2022) | PDF text | drop | low |
| U9→ZH Hunde pages | Yes today | server HTML | html_crawl | med |
| D15 ZH StVA | Yes today | server HTML + PDF text | html_crawl + pdf | med |
| D16 ZH school holidays | Yes with new fetcher | XLSX (185 Schulgemeinden) + PDF text | XLSX table + Sgde→BFS map | high |
| U10 GE Guide fiscal | Yes today | server HTML (getax.ch, 98 pages) + PDF text (62 pages) | html_crawl | high |
| D17 GE dogs | Yes today | server HTML | html_crawl | med |
| D18 GE OCV | Yes today | server HTML (inferred) | html_crawl | med |
| D19 GE school holidays | Yes with new fetcher (ICS); HTML today | ICS 2024/25–2030/31 | ICS calendar | high |
| D20 BE TaxInfo | Yes with new fetcher | SSR HTML + embedded ProseMirror JSON, ≥591 pages | phonemos wiki crawler | high |
| D21 BE dogs | Yes today | server HTML | html_crawl (weu.be.ch) | med |
| U11 BE SVSA | Yes today (no parking) | server HTML | html_crawl | med |
| D22 BS tax | Yes today (pdf/html); Steuerwissen A–Z is gone | server HTML + PDF (61 PDFs on 2 index pages) | PDF index discoverer | med |
| D23 BS dogs | Yes today | server HTML + PDF | html_crawl + pdf | med |
| U13 BS MFK / parking | Yes today | server HTML | html_crawl | med |
| D24 BS (+BL) holidays | Yes today | JSON (88 / 58 rows) | api | high |

## 2. New fetcher classes needed
1. **Sitemap-seeded cantonal crawler** (html_crawl extension: sitemap(-index) → URL regex allowlist → fetch; optional PDF include). Serves the ZH Steuerbuch, U9/D15/D16 pages, D17–D19, D21, U11, D22, D23, U13. It covers **4 cantons** (ZH 44 child sitemaps; GE about 28k URLs; BS about 27k; BE through per-office hosts `<office>.be.ch/de|fr/sitemap.xml`), and probably any AEM/Drupal canton site with a sitemap (inferred).
2. **ICS calendar**. D19 GE school holidays (7 school years). Also usable for Stadt/commune ICS elsewhere (not verified here).
3. **XLSX table**. D16 ZH: 185 Schulgemeinden, about 160 communes (the Sgde→BFS mapping is unverified).
4. **PDF index discoverer** (collect PDF hrefs from an index page by pattern). D22 BS (61 PDFs), ZH StVA fee order (the yearly filename changes), ZH Mittelschul holiday PDFs. It overlaps with #1 if the sitemap lists the PDFs (ZH does).
5. **Phonemos wiki (vike_pageContext JSON)**. D20 BE TaxInfo (≥591 pages). Other cantons on phonemos: unknown.

## 3. Best finds
1. **ZH Steuerbuch is enumerable**: `https://www.zh.ch/de/steuern-finanzen.zhweb-sitemap.xml` lists 159 zstb HTML entries (with Erlassdatum/Gültig ab/ZStB-Nummer) + current PDFs. This overturns the pilot's "no index".
2. **GE school holidays as .ics** for 2024/25–2030/31 (`/document/ics-calendrier-vacances*` → `/document/<n>/telecharger`, `text/calendar`, 10 events per year), plus GeTax's 98-page server-HTML tax guide.
3. **ZH canton-wide school holiday XLSX per Schulgemeinde** (185 rows × 6 holiday periods, 2025/26), the only commune-level holiday source for the whole canton. Runner-up: BE TaxInfo (≥591 structured tax-practice pages via embedded JSON).
