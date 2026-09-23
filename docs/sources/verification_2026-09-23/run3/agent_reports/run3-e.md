I have all the evidence. Here is the full report.

# Run 3, group E: TI, GR, VS (plus Lugano), and Part 2 (court and legal links)

**How this run went:** I restarted from the prior agent's log (55 steps) and used its finds as leads only. Every URL in a grid cell below was re-requested today (2026-09-23) with curl, unless the cell says otherwise. I finished the step where the last run stalled: the GR Rechtsprechung page links to **https://entscheidsuche.gr.ch/**. Scratch files are in `…/scratchpad/run3-e/` (helpers `h.py`, `show.py`, `pdfcheck.py`, `lexgrep.py`, `es_spiders.py`, `part2.py`).

One process slip: one early command used a zsh `for` loop over saved local files (not URLs). It ran without stalling. Every other loop is in a Python file.

**Corrections to the inputs (all verified today):**
1. **TI root does not answer 403.** The brief says it does; today `https://www4.ti.ch/` returned 200 and redirected to `/tich/stato-e-organizzazione`.
2. **The GR court site is real.** The pre-check lists `justiz-gr.ch` as "no DNS", but **`https://www.justiz-gr.ch/` is the real GR justice portal** (200, "Justiz Graubünden", sitemap of 305 URLs). The AI had the host right apart from the missing `www.`; only its paths were invented (all 404).
3. **Amtsblattportal filter.** `docs/sources/ogd_lists_assessment.md` lists `tenants` as a filter on `/publications`. With `tenants=kabti`, `kabgr` or `kabvs` the API returned the same total (32,718) every time, so the filter was ignored. **`cantons=TI|GR|VS` does filter.**
4. **Lugano is a source.** `subnational_sources.md:310` says "Lugano … no rule-bearing data, not-a-source". That is wrong: Lugano's collection has **122 texts, including dog, waste and parking rules** (see L1).
5. **GR reorganised its courts (was unverified, now verified).** `justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/` (200): *"Das Obergericht des Kantons Graubünden ist per Anfang 2025 aus der Zusammenführung von Kantonsgericht und Verwaltungsgericht entstanden."* The entscheidsuche GR spider backs this up independently: it now filters on court `OG`, and the older `KG|VG` query templates are commented out.

---

## TI (Ticino), city: Lugano

### Grid

| Cell | Status | URL | Evidence (HTTP · title · format · size) | Sample / notes |
|---|---|---|---|---|
| C1 courts-home | VERIFIED | https://www4.ti.ch/poteri/giudiziario/pg | 200 · "PG - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino" · server HTML (TYPO3) · 71 links, 439 words | Links "Divorzio" → `/poteri/giudiziario/io-e-il-diritto/io-e-il-divorzio`, "Sentenze online" → `http://www.sentenze.ti.ch/` |
| C2 court-fees | Ordinance VERIFIED; resident fee page NONE | Ordinance: https://m3.ti.ch/CAN/RLeggi/public/index.php/raccolta-leggi/legge/num/137 (**178.200 LTG**); also 178.310 and 178.320 (law_hits). Closest resident page: https://www4.ti.ch/di/dg/cosa-facciamo/assistenza-giudiziaria | LTG: 200 · "CAN - Raccolta delle leggi…" · HTML · 2,130 words. Legal aid: 200 · "Assistenza giudiziaria - DG (DI)" · 328 words, no amounts | LTG Art. 5: *"Nelle procedure di conciliazione, è fissata una tassa… fino a 2'000 → 50 - 150; 2'000 - 5'000 → 100 - 300; 5'000 - 30'000 → 200 - 1'500"* (franchi). **Ladder for the resident page:** AI link `/potere-giudiziario/tasse-giudiziarie` 404 (pre-check) → no XML sitemap (only the culture agenda) → PG navigation (sportello/temi, pubblicazioni, giudici-di-pace, locazione): no fee table; giudici-di-pace only cites *"Legge sulla tariffa giudiziaria del 30 novembre 2010"* → site search is a JS shell (prior-run evidence, not re-checked) → WebSearch `site:ti.ch` and `site:www4.ti.ch` returned only law texts, the legal-aid page and forms → law_hits. The labour brochure `…/IoDiritto/opuscolo_lavoro.pdf` (200) says *"La procedura è gratuita… fino al valore di fr. 30'000.-"*, but it is **dated 2006 and cites old cantonal CPC art. 417: stale, do not ingest** |
| C3 court-guidance | VERIFIED | `/poteri/giudiziario/io-e-il-diritto/{io-e-il-divorzio, io-e-la-locazione, io-e-il-lavoro, io-e-lautorita-di-protezione}`, `/sportello/temi`, `/locazione/la-locazione`, `/locazione/competenze`, `/di/dg/cosa-facciamo/assistenza-giudiziaria` | all 200, server HTML, 247–821 words each | Divorce page: *"…sono trattate dal Pretore del luogo di domicilio dell'uno o dell'altro coniuge secondo una procedura particolare."* No sitemap for this section. From 4 hub pages: **58 distinct `/poteri/giudiziario/` pages, 20 of them resident guidance**. Pages are short |
| C4 court-decisions | VERIFIED | https://www.sentenze.ti.ch/ → `/findinfo/ti/home.htm` → `/cgi-bin/nph-omniscgi` | root 200 · "FindinfoWeb TI" · 747 B meta-refresh. Omnis FindinfoWeb: the entscheidsuche `TI_Gerichte.py` sends a POST form to `/cgi-bin/nph-omniscgi` | opencaselaw `ti_gerichte`: **66,944 decisions, 1922-05-07 → 2026-07-08**. Not stale by the "before 2026" rule, but the newest decision is about 11 weeks old (the Atom feed agrees). No court API or feed |
| C5 conciliation | VERIFIED | https://www4.ti.ch/poteri/giudiziario/giustizia-civile/giudici-di-pace, tenancy: `/poteri/giudiziario/locazione/la-locazione` and `/competenze` | 200 · "Giudici di pace - GIUDIZIARIO (POTERI)" · 1,067 words | *"Il Giudice di pace: funge da autorità di conciliazione nelle controversie patrimoniali fino a un valore litigioso di fr. 5'000…"*. Tenancy: *"L'Ufficio deve tentare una conciliazione in tutte le controversie…"*. 11 local tenancy offices listed (Chiasso … Biasca). Forms include "Istanza di conciliazione art. 202 CPC" (PDF). Fees are in LTG Art. 5. Laws 177.110, 842.100/842.110 (labour office page not fetched) |
| G1 dogs | VERIFIED | https://www4.ti.ch/dss/dsp/uvc/temi/tenuta-di-animali/cani/razze-soggette-a-restrizioni (plus 8 sibling pages under `/cani/`) | 200 · "Razze soggette a restrizioni - UVC (DSS)" · 1,545 words | *"In base all'articolo 14 della Legge sui cani (LCani)… obbligo di autorizzazione prima di entrare in possesso del cane"*. Laws **482.300 LCani (19.02.2008), 482.310 RCani "del 30 dicembre 2025" (new)**, 482.315 |
| G2 tax guide | VERIFIED | https://www4.ti.ch/dfe/dc/dichiarazione/istruzioni-pf/istr-pf-attuale, PDF `/fileadmin/DFE/DC/DOC-IPF/2025/Istruzioni/Istruzioni_PF_2025.pdf` | page 200 · "2025 - DC (DFE)" · 317 words. PDF 200 · **43.7 MB, 56 pages, text layer** | *"…per la compilazione della dichiarazione d'imposta 2025 delle persone fisiche… www.ti.ch/etax"*. Enumerable: year pages `/istruzioni-pf/2016…2025` (10), about 5 PDFs per year (instructions, out-of-canton, part-year, deductions table, flyer). No entry-by-entry manual like ZH's Steuerbuch |
| G3 school holidays | VERIFIED | https://www4.ti.ch/decs/cosa-facciamo/calendario-scolastico/2026-2027 (the parent path redirects here), PDFs 2026/27 to 2029/30 | 200 · "2026/2027 - DECS (DECS)" · 483 words. PDF 2026_2027: 200 · 1 page · text layer | *"vacanze autunnali: dal 31 ottobre all'8 novembre 2026; vacanze di Natale: dal 24 dicembre 2026 al 6 gennaio 2027"*. **Set by the canton (DECS) for "tutte le scuole"** (vocational schools excepted). The `/2025-2026` page is now 404 |
| G4 road office | VERIFIED | https://www4.ti.ch/di/sc/home/, `/di/sc/veicoli/imposta-di-circolazione`, `/di/sc/conducenti/licenza-allievo-conducente` | home 200 · "Home - SC (DI)" · 1,013 words. Imposta 200 · 1,202 words | *"Diffida di pagamento, tassa di richiamo fr. 20.00. Decisione di sequestro tassa fr. 100.00."* Laws 760.100, 760.500, 760.510. Online calculator `/calcolo-imposta` not checked |
| D1 communes | VERIFIED (no links) | https://www4.ti.ch/di/sel/comuni/elenco-comuni, XLSX `/fileadmin/DI/DI_DI/SEL/Comuni/Elenco_comuni/2025-04-comuni_attuali.xlsx` | page 200 · "Elenco comuni - SEL (DI)". XLSX 200 · 8.9 KB · columns COMUNE, Distretto | *"Il Ticino conta attualmente 100 comuni"*; a row reads `AGNO / Lugano`. **No BFS numbers and no website links (0 hyperlinks)**. Use `commune_sites.csv` (100 TI rows) for websites |
| D2 chancellery and gazette | VERIFIED | https://www4.ti.ch/can/cancelleria and Foglio ufficiale https://foglioufficiale.ti.ch/ (eSHAB front end of Amtsblattportal) | Cancelleria 200 · "Cancelleria - CAN (CAN)" · 407 words. foglioufficiale 200 · "eSHAB" · 1.4 KB JS shell. API `amtsblattportal.ch/api/v1/publications?…&cantons=TI&publicationDate.start=2026-09-01` → **2,014 notices** (157,248 since 2020) | Sample (2026-09-23, rubric KA-TI60): *"Notifica di sentenza nella forma degli assenti (art. 141 CPC) – SO.2026.3313"*. The law gazette (Bollettino ufficiale) is at `/can/bu/bu` (200) |
| **L1 Lugano** | VERIFIED | https://www.lugano.ch/la-mia-citta/amministrazione/legislazione.html | 200 · "Legislazione \| lugano.ch" · server HTML · 20.7 KB, 415 links, 2,607 words. Texts at `/law/<id>/<slug>` → application/pdf with a text layer | **122 texts.** Dogs: 2.6.1 *"i cani di qualsiasi razza ed indole devono quindi essere tenuti costantemente al guinzaglio"*. Waste: 4.1, 4.1.1 (13 pp, *"CHF 40.-- cadauna in caso di perdita"*), 4.1.2 bag tax 2026. Parking: 2.2.1 (tariffs), 2.2.3, 2.2.6. Platform: own CMS listing plus a PDF endpoint (Magnolia inferred from `/dam/jcr:` paths, not verified). `/law/` URLs are not in the sitemap; robots.txt allows them |

### TI site recipe
- **Hosts:** www4.ti.ch (portal, TYPO3: `typo3conf`/`typo3temp` appear in the HTML); m4.ti.ch (the same `/fileadmin/` PDFs); m3.ti.ch and www3.ti.ch (RLeggi law texts as HTML at `/raccolta-leggi/legge/num/{n}`); www.sentenze.ti.ch (Omnis); foglioufficiale.ti.ch (eSHAB); www.lugano.ch.
- **Sitemaps:** www4.ti.ch's robots.txt names only the culture-agenda sitemap (618 URLs per the brief). lugano.ch/sitemap.xml has 5,684 URLs, 1,421 of them Italian.
- **robots.txt:** www4.ti.ch has `Allow: /` with a few disallows and no crawl-delay. lugano.ch disallows only specific `/dam/jcr` ids and `downloadAlbo`.
- **Bot walls:** none met. `rlws.ti.ch/rl/ws/getActPDF/137` (linked from RLeggi) gave no connection (HTTP 000).

### TI draft YAMLs
```yaml
id: ti_giudiziario_guidance
base_url: https://www4.ti.ch
default_extent_id: CH-TI
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  language: it
  start_paths: ["/poteri/giudiziario/sportello/temi", "/poteri/giudiziario/io-e-il-diritto/io-e-il-divorzio",
                "/poteri/giudiziario/locazione/la-locazione", "/poteri/giudiziario/giustizia-civile/giudici-di-pace",
                "/di/dg/cosa-facciamo/assistenza-giudiziaria"]
  path_allowlist: ["/poteri/giudiziario/io-e-il-diritto/", "/poteri/giudiziario/sportello/", "/poteri/giudiziario/locazione/",
                   "/poteri/giudiziario/giustizia-civile/giudici-di-pace", "/di/dg/cosa-facciamo/assistenza-giudiziaria"]
allow_narrowing: false
---
id: ti_uvc_cani
base_url: https://www4.ti.ch
default_extent_id: CH-TI
authority: official_info
categories: [dogs]
fetch_strategy: html_crawl
fetch_config: {language: it, start_paths: ["/dss/dsp/uvc/temi/tenuta-di-animali/cani/razze-soggette-a-restrizioni"],
               path_allowlist: ["/dss/dsp/uvc/temi/tenuta-di-animali/cani/"]}
---
id: ti_calendario_scolastico      # canton-wide, so CH-TI is correct
default_extent_id: CH-TI
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  language: it
  urls:
    - https://m4.ti.ch/fileadmin/DECS/calendario_scolastico/Calendario_scolastico_2026_2027.pdf   # fetched, text layer
    - https://www4.ti.ch/fileadmin/DECS/calendario_scolastico/Calendario_scolastico_2027-2028.pdf # from the page link, not fetched
---
id: ti_sezione_circolazione
base_url: https://www4.ti.ch
default_extent_id: CH-TI
authority: official_info
categories: [transport]
fetch_strategy: html_crawl
fetch_config: {language: it, start_paths: ["/di/sc/home/"], path_allowlist: ["/di/sc/veicoli/", "/di/sc/conducenti/"]}
---
id: ti_dc_istruzioni_pf
default_extent_id: CH-TI
authority: official_info
categories: [taxes]
fetch_strategy: pdf
fetch_config: {language: it, urls: ["https://www4.ti.ch/fileadmin/DFE/DC/DOC-IPF/2025/Istruzioni/Istruzioni_PF_2025.pdf"]}  # 43.7 MB
---
id: lugano_legislazione
base_url: https://www.lugano.ch
default_extent_id: CH-TI-5192
authority: official_info          # until lugano.ch is registered as a law platform
categories: [dogs, waste, parking]
fetch_strategy: pdf
fetch_config:
  language: it
  urls:
    - https://www.lugano.ch/law/16176713/2-6-1-Ordinanza-sulla-custodia-dei-cani-e-sulle-aree-di-svago-del-13-gennaio-2010
    - https://www.lugano.ch/law/16176717/4-1-Regolamento-sulla-raccolta-dei-rifiuti-del-13-maggio-2019
    - https://www.lugano.ch/law/16371927/4-1-1-Ordinanza-municipale-sulla-gestione-dei-rifiuti-del-17-ottobre-2019
    - https://www.lugano.ch/law/16597411/4-1-2-Ordinanza-municipale-sulla-tassa-sul-sacco-per-l-anno-2026-del-23-ottobre-2025
    - https://www.lugano.ch/law/17057218/2-2-1-Ordinanza-municipale-concernente-le-agevolazioni-e-le-tariffe-di-parcheggio-del-25-agosto-2022
    - https://www.lugano.ch/law/16595053/2-2-3-Ordinanza-municipale-sull-utilizzo-delle-aree-di-parcheggio-pubblico-di-Cornaredo-del-9-febbraio-2017
# all 122 texts: fetcher:pdf-index over legislazione.html (the "1.1.2 …" link text gives the identifier and title; the date is in the title)
```

### TI claim checks
All AI links below were 404 in the pre-check, so each claim is **Wrong**. The real URL is on the right.

| AI link | Real location |
|---|---|
| `/potere-giudiziario/{tribunale-di-appello, tasse-giudiziarie, temi, giurisprudenza, tribunale-amministrativo, preture}` | `/poteri/giudiziario/…`; decisions at sentenze.ti.ch |
| `/dss/dsp/uvc/settori/sanita-animale/cani` | `/dss/dsp/uvc/temi/tenuta-di-animali/cani/…` |
| `/dfe/dc/dichiarazione/istruzioni-e-moduli` | `/dfe/dc/dichiarazione/istruzioni-pf/istr-pf-attuale` |
| `/decs/ds/scuola/calendario-scolastico` | `/decs/cosa-facciamo/calendario-scolastico/2026-2027` |
| `/di/sezione-della-circolazione/…` | `/di/sc/home/` |
| `/di/sel/comuni/elenco-dei-comuni-ticinesi` | `/di/sel/comuni/elenco-comuni` |
| `/can/oltre-confine/cancelleria-dello-stato` | `/can/cancelleria` |
| Lugano `/amministrazione-servizi/regolamenti.html` | `/la-mia-citta/amministrazione/legislazione.html` |

---

## GR (Graubünden)

### Grid

| Cell | Status | URL | Evidence | Sample / notes |
|---|---|---|---|---|
| C1 courts-home | VERIFIED | https://www.justiz-gr.ch/ | 200 · "Justiz Graubünden" · server HTML · 328 links, 484 words. `robots.txt` allows everything; `sitemap.xml` has **305 URLs** | The Obergericht "Aufgaben" page (200) states the 2025 merger (quote above). Sections: Obergericht, Justizgericht (13 sitemap URLs, role not checked), 11 Regionalgerichte, Schlichtungsbehörden, SchKG. DE/RM/IT |
| C2 court-fees | VERIFIED | https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/prozess-und-verfahrenskosten/ and `/schlichtungsbehoerden-und-mediation/dienstleistungenthemen/kosten/` | 200 · "Prozess- und Verfahrenskosten" · 1,739 words. 200 · "Kosten" · 726 words | *"Im Schlichtungsverfahren beträgt diese Pauschalgebühr CHF 100.00 bis CHF 500.00"*; *"…im Umfang von 200 bis 1000 Franken festgelegt"* (IV disputes). Ordinances: **320.210 VGZ**, 350.210 VGS, 370.110 VGÖ, 370.140 (Justizgericht), 370.120 VKV |
| C3 court-guidance | VERIFIED | `/gerichte/obergericht/dienstleistungenthemen/unentgeltliche-rechtspflege/` (200, 2,031 words), `/schuldbetreibung-und-konkurs/dienstleistungenthemen/betreibungsverfahren/` (200, 1,803 words), the Schlichtung pages below, the cost page | server HTML | *"Eine Person hat dann Anspruch auf unentgeltliche Rechtspflege (URP), wenn sie nicht über die erforderlichen Mittel verfügt… Die Kosten gehen dann zu Lasten des Kantons."* **Sitemap: 94 guidance-like URLs of 305 (43 outside the regional-court pages)**, e.g. allgemeine-rechtsauskuenfte, wen-betreibt-man-wo, auskunft-ueber-betreibungen, rechtsberatung. Only the pages named here were fetched |
| C4 court-decisions | VERIFIED | https://entscheidsuche.gr.ch/ (linked from `/gerichte/obergericht/dokumentation/rechtsprechung/`, 200) | 200 · 19 KB · 0 links · **Tribuna VTPlus GWT app** (`tribunavtplus/tribunavtplus.nocache.js`); robots 404. Per the spider code: GWT-RPC POST to `/tribunavtplus/loadTable`, downloads from `/tribunavtplus/ServletDownload/` | opencaselaw `gr_gerichte`: **15,821 decisions, 1992-09-02 → 2026-09-14** (not stale). 8 regional courts have "Publikation von Entscheiden" pages. No usable API |
| C5 conciliation | VERIFIED | `/schlichtungsbehoerden-und-mediation/ueber-uns/mietsachen/` and `/vermittleraemter/` | both 200, about 1,050 words | *"In jeder Region gibt es eine Schlichtungsbehörde für Mietsachen."* Fees on the Kosten page (CHF 100–500). Laws 173.190, 370.300/370.310 |
| G1 dogs | VERIFIED | https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/tiere/hundewesen/Seiten/default.aspx | 200 · "Hundewesen - Hundewesen" · SharePoint HTML · 829 words | *"Hundehalterinnen und Hundehalter sind verpflichtet, der kantonalen Fachstelle zu melden, wenn sie einen Hund mit coupierten Ohren oder verkürzter Rute besitzen."* **Jurisdiction trap:** *"Die Fachstelle Hundewesen ist für den Gesetzesvollzug… im Kanton Graubünden und Glarus verantwortlich"*, and the page carries GL permit rules. **Law (not in law_hits): BR 914.000 Veterinärgesetz (enactment 2008-12-01), chapter "9. Hundehaltung und Findeltiere"**, plus 914.100 VetV. VetG: *"Die Gemeinden vollziehen… die Hundehaltung…"* |
| G2 tax guide | VERIFIED | `…/dfg/stv/dokumentation/praxis/Seiten/default.aspx` plus 6 sub-pages; `…/steuererklaerung/einkommens_und_vermoegenssteuer/Seiten/wegleitungen_merkblaetter.aspx` | all 200. **88 distinct practice-rule PDFs** (Praxisfestlegungen). Wegleitungen page: 102 PDF link occurrences (links appear twice, so about 51, inferred). Wegleitung 2025 PDF: 3.4 MB, 69 pp, text layer | *"Praxisfestlegung Steuerverwaltung Graubünden 1.5.2024 … 010-01 … Familien-/Ehegattenbesteuerung"*. Enumerable through the 7 listing pages. There is no "Steuerbuch" |
| G3 school holidays | VERIFIED | https://www.gr.ch/DE/institutionen/verwaltung/ekud/avs/Volksschule/SB_Ferienplaene_2026_2027_de.pdf | 200 · 77 KB · 8 pp · text layer · about 172 rows | *"132 Chur 17.08.26 … 10.10.26 25.10.26 … 23.12.26 05.01.27"*. **Who sets them: BR 421.000 Art. 24 Abs. 3: "Das Departement legt die Herbst- und Weihnachtsferien fest. Die übrigen Ferien bestimmen die Schulträgerschaften."** Row numbers are school-body ids, not BFS numbers |
| G4 road office | VERIFIED | `…/djsg/stva/Seiten/Start.aspx`, fees `…/djsg/stva/ueberuns/steuern-gebuehren/Seiten/Geb%C3%BChrenverordnung.aspx` | 200 · "Willkommen beim Strassenverkehrsamt". 200 · "Gebühren - Steuern und Gebühren" · 485 words | *"Fahrzeugausweis für alle Kategorien (ausgenommen Motorfahrräder / E-Bike) Fr. 40.–"*. Law 870.130 StrGebV |
| D1 communes | VERIFIED | `…/dfg/afg/gemeinden/UnsereGemeinden/Seiten/InfoSeiteNeu.aspx`; BFS list PDF `…/dvs/alg/Dokumente%20Geoinformation/AV_HS_02_DE_Die_Gemeinden_des_Kantons_Graub%C3%BCnden.pdf` | 200 · "Informationen - Unsere Gemeinden" · **99 external commune domains**. PDF 200 · 2 pp · text layer | Link: `http://www.albula-alvra.ch`. PDF: *"Albula/Alvra 3542 Andeer 3701 Arosa 3921…"* The CSV has 100 GR communes |
| D2 chancellery and gazette | VERIFIED; gazette BLOCKED for crawling | https://www.gr.ch/DE/institutionen/verwaltung/staka/Seiten/home.aspx; https://www.kantonsamtsblatt.gr.ch/publikationen/ | 200 · "Standeskanzlei Graubünden". 200 · "Kantonsamtsblatt Graubünden Publikationen" · TYPO3 + DIAM, run by Somedia | *"Das elektronische Kantonsamtsblatt ersetzt seit 1. Januar 2016 die gedruckte Ausgabe…"* **robots.txt disallows `/publikationen/` and `/ekab/`.** Amtsblattportal `cantons=GR`: 611 notices since 1 Sept; the 3 sampled were all commercial-register (HR) notices; whether cantonal GR rubrics exist there is not verified |

### GR site recipe
- **www.gr.ch:** SharePoint (`/Seiten/*.aspx`; robots.txt lists `_layouts`, `_vti_bin`). `/sitemap.xml` 404. The chancellery's `SitemapSTAKA.aspx` returns 500 "Parser Error". robots.txt disallows `*/Suche.aspx?*`, `/DE/publikationen/kantonsamtsblatt/` and `…/Verwaltungsverordnungen/*`; no crawl-delay. Department code is **djsg**, not djs.
- **www.justiz-gr.ch:** 305-URL sitemap (use it as the seed); allows everything.
- **www.gr-lex.gr.ch:** LexWork; `lightweight_index` returned 419 entries.
- **entscheidsuche.gr.ch:** Tribuna GWT. **www.kantonsamtsblatt.gr.ch:** DIAM, crawling of publications blocked by robots.txt.

### GR draft YAMLs
```yaml
id: gr_justiz_guidance
base_url: https://www.justiz-gr.ch
default_extent_id: CH-GR
authority: official_info
categories: []          # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  language: de
  start_paths: ["/gerichte/obergericht/dienstleistungenthemen/", "/schlichtungsbehoerden-und-mediation/dienstleistungenthemen/",
                "/schlichtungsbehoerden-und-mediation/ueber-uns/", "/schuldbetreibung-und-konkurs/dienstleistungenthemen/"]
  path_allowlist: ["/gerichte/obergericht/dienstleistungenthemen/", "/schlichtungsbehoerden-und-mediation/", "/schuldbetreibung-und-konkurs/dienstleistungenthemen/"]
allow_narrowing: false   # regional pages name regions, not communes
---
id: gr_alt_hundewesen    # design: the page mixes GR and GL rules; strip the GL sections or GL facts land on CH-GR
base_url: https://www.gr.ch
default_extent_id: CH-GR
authority: official_info
categories: [dogs]
fetch_strategy: html_crawl
fetch_config: {language: de, start_paths: ["/DE/institutionen/verwaltung/dvs/alt/tiere/hundewesen/Seiten/default.aspx"],
               path_allowlist: ["/DE/institutionen/verwaltung/dvs/alt/tiere/hundewesen/"]}
---
id: gr_stv_wegleitung    # all 88 practice PDFs: fetcher:pdf-index over the 6 practice pages
default_extent_id: CH-GR
authority: official_info
categories: [taxes]
fetch_strategy: pdf
fetch_config:
  language: de
  urls:
    - https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/steuererklaerung/einkommens_und_vermoegenssteuer/WegleitungenMerkbltter/Wegleitung%202025%20Prim%c3%a4rsteuerpflichtige.pdf
    - https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/PraxisEinkommenVermgen/010-01.pdf
---
id: gr_schulferien       # lands on CH-GR only; rows need fetcher:pdf-table to reach communes
default_extent_id: CH-GR
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config: {language: de, urls: ["https://www.gr.ch/DE/institutionen/verwaltung/ekud/avs/Volksschule/SB_Ferienplaene_2026_2027_de.pdf"]}
---
id: gr_stva
base_url: https://www.gr.ch
default_extent_id: CH-GR
authority: official_info
categories: [transport]
fetch_strategy: html_crawl
fetch_config: {language: de, start_paths: ["/DE/institutionen/verwaltung/djsg/stva/Seiten/Start.aspx"], path_allowlist: ["/DE/institutionen/verwaltung/djsg/stva/"]}
```

### GR claim checks
- **Courts, Partly:** `www.justiz-gr.ch/{kantonsgericht, verwaltungsgericht, regionalgerichte, themen, themen/gebuehren, rechtsprechung}` were all 404. The host is right, the paths are invented, and the Kantonsgericht and Verwaltungsgericht no longer exist (merged into the Obergericht in 2025).
- **Wrong** (all 404), with the real location:
  - Dogs `…/dvs/alt/hunde/` → `…/dvs/alt/tiere/hundewesen/Seiten/default.aspx`
  - Tax `…/stv/steuerbuch/` → there is no Steuerbuch; use Praxisfestlegungen and Wegleitungen
  - School `…/avs/schulferien/` → the Ferienplan PDF
  - Road `…/djs/stva/` → `…/djsg/stva/Seiten/Start.aspx`
  - Communes `/DE/kanton/gemeinden/` → the AFG page
- **Confirmed:** chancellery `…/staka/` (200).

---

## VS (Valais)

### Grid

| Cell | Status | URL | Evidence | Sample / notes |
|---|---|---|---|---|
| C1 courts-home | VERIFIED | https://www.vs.ch/web/tribunaux | 200 · "Accueil - Tribunaux - vs.ch" · Liferay HTML · 81 links, 580 words | Links to the cantonal court, district courts, jurisprudence, "Calcul des frais de justice", "Juges et vice-juges de commune" |
| C2 court-fees | VERIFIED (page and ordinance; CHF amounts only in the law) | https://www.vs.ch/web/tribunaux/calcul-des-frais-de-justice; **LTar 173.8** (lex.vs.ch, enactment 2011-01-01) | 200 · 255 words. The linked `.xls` (200, 86 KB) is a legacy macro calculator (VBA forms, "Streitwert" input), not data. The `.xlsm` link is 404 | Page: *"La procédure en justice n'est pas gratuite…"* LTar Art. 15: *"de 50 à 100 francs pour la citation en conciliation… de 120 à 250 francs pour la tenue de la séance de conciliation"* |
| C3 court-guidance | VERIFIED (thin) | `/web/tribunaux/{qu%C3%A9stions-r%C3%A9ponses, contributions-d-entretien, liste-de-juges-et-vice-juges-de-commune, calcul-des-frais-de-justice}` | all 200, 255–505 words | Q&A: *"Le Tribunal cantonal est ouvert à tout public selon ses heures d'ouverture."* **The XML sitemap (99 URLs) has 0 `/web/tribunaux` URLs.** The HTML site plan `/web/tribunaux/sitemap` (200) lists 23 pages, about 5 of them resident guidance |
| C4 court-decisions | VERIFIED | `/web/tribunaux/jurisprudence` → https://jurisprudence.vs.ch/ (Nuxt "JustSearch", 1 KB shell) → **JSON API `https://api-justsearche.vs.ch/api/search/?offset=0&limit=2&sort=_score`** | API 200 · `{count: 5006, offset, facets, results[]}`. Fields: id, file_name, language{}, document_type "pdf", tribunal{abbreviation "KGVS"}, date_decision, date_publication, case_number{} | opencaselaw `vs_gerichte`: **7,008, 1959-11-20 → 2026-09-06** (not stale). Why opencaselaw has more decisions than the court API (7,008 vs 5,006): **I don't know** |
| C5 conciliation | VERIFIED | `/web/tribunaux/liste-de-juges-et-vice-juges-de-commune`; tenancy https://www.vs.ch/web/sict/bail-a-loyer | 200 · 505 words. 200 · 1,272 words | *"La conciliation constitue l'aspect essentiel de l'activité du juge de commune… un procès civil débute par une audience de conciliation devant ce dernier."* Tenancy: *"Commission cantonale de conciliation en matière de bail à loyer… Av. du Midi 7 1950 Sion"*. Every commune page names its judge (see D1). Fees in LTar Art. 15 |
| G1 dogs | VERIFIED | `/web/scav/veterinaire/affaires-canines`, `/web/scav/veterinaire/securit%C3%A9-publique` | 200 · 369 words. 200 · 718 words | *"En Valais, le respect de la prescription concernant la tenue en laisse des chiens incombe aux communes selon l'article 30 de la LALPA (RS 455.1)"*; *"Liste des 12 races… interdits en Valais"*. Laws 455.1, **455.100 (in force 01.01.2020)**, 652.100 (dog tax) |
| G2 tax guide | VERIFIED | `/web/scc/personnes-physiques` (200); **`/web/guide-de-taxation`** (200 · "Guide de taxation (VSMODULE)"); `/web/scc/directives` (200) | **87 entries**, each at `/web/guide-de-taxation/detail?groupId=85485&classPK=<id>` | Entry 1410 (114 words): *"Pensions alimentaires versées pour l'ex-conjoint (e) séparé ou divorcé…"* plus a PDF. Entries are thin. The yearly guide PDFs sit under `/documents/`, which robots.txt disallows |
| G3 school holidays | VERIFIED (dates are colour-coded in the PDF) | `/web/se/plans-de-scolarite` | 200 · 291 words. PDF 2026-2027 (200, 1 page): the text layer holds only a calendar grid, the holidays are shown by colour | *"Attention, les plans sont indicatifs. Pour toutes dates de vacances plus précises, s'adresser directement à la Direction d'école (ou Commune)."* **The canton sets an indicative frame** (4 Conseil d'Etat decisions are linked); schools and communes fix the dates. Plans for Valais romand 2025–29 and a German Übersicht for 2025-26 |
| G4 road office | VERIFIED | https://www.vs.ch/web/scn, `/web/scn/taxes-emoluments`, `/web/scn/immatriculation-d-un-vehicule-en-plaques-vs`, `/web/scn/permis-de-conduire` | 200 · "SCN - SCN - vs.ch" · 106 links. Fee page 200: links to laws only | 741.104 (enactment 2022-01-01): *"délivrance d'un permis d'élève conducteur Fr. 40"*. Also 641.5 |
| D1 communes | VERIFIED | https://www.vs.ch/web/communes/commune | 200 · "Communes - Région District Commune" · **122 commune pages** (the CSV also has 122) | `/web/communes/-/blatten`: *"Commune Blatten OFS 6192 … Juge Hans-Anton Ebener … Site Internet http://www.blatten-vs.ch"*. Each page gives BFS number, executive, commune judge, website and e-mail |
| D2 chancellery and gazette | VERIFIED | https://www.vs.ch/web/che; `/web/communication/bo` → https://bulletin-officiel.vs.ch/ (eSHAB) | 200 · 624 words. BO page 200. eSHAB 200, 1.4 KB shell. Amtsblattportal `cantons=VS`: **1,942 notices since 1 Sept** (110,001 since 2020) | *"Depuis le 1er mars 2023, il paraît sous forme électronique… Seule la version électronique publiée sur la plateforme fait foi."* Sampled rubrics RE-VS and BA-VS55 (building permits) carry `municipalityId` 6037. bulletinvalaiswallis.ch is only the PDF archive |

### VS site recipe
- **www.vs.ch:** Liferay DXP (the "liferayee" server-instance string appears in pages; paths `/web/<site>`, `/documents/<group>/…`).
- `sitemap.xml` has 99 URLs (link pages only), so it is useless. Use the per-site HTML site plans (e.g. `/web/tribunaux/sitemap`).
- **robots.txt disallows `/documents/`, `*.pdf`, `*.docx`, `*.xlsx`**, so a PDF ingest from vs.ch goes against robots.txt. No crawl-delay.
- Other hosts: lex.vs.ch (LexWork, `/data/{nr}/fr` links), api-justsearche.vs.ch (JSON), bulletin-officiel.vs.ch (eSHAB).

### VS draft YAMLs
```yaml
id: vs_tribunaux
base_url: https://www.vs.ch
default_extent_id: CH-VS
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config: {language: fr, start_paths: ["/web/tribunaux/sitemap"], path_allowlist: ["/web/tribunaux/"]}
allow_narrowing: false
---
id: vs_scav_chiens
base_url: https://www.vs.ch
default_extent_id: CH-VS
authority: official_info
categories: [dogs]
fetch_strategy: html_crawl
fetch_config: {language: fr, start_paths: ["/web/scav/veterinaire/affaires-canines", "/web/scav/veterinaire/securit%C3%A9-publique"],
               path_allowlist: ["/web/scav/veterinaire/affaires-canines", "/web/scav/veterinaire/securit", "/web/scav/veterinaire/vente-acquisition-chiens"]}
---
id: vs_guide_taxation    # detail ids are in the query string; whether html_crawl keeps query strings is NOT verified
base_url: https://www.vs.ch
default_extent_id: CH-VS
authority: official_info
categories: [taxes]
fetch_strategy: html_crawl
fetch_config: {language: fr, start_paths: ["/web/guide-de-taxation"], path_allowlist: ["/web/guide-de-taxation"]}
---
id: vs_scn
base_url: https://www.vs.ch
default_extent_id: CH-VS
authority: official_info
categories: [transport]
fetch_strategy: html_crawl
fetch_config: {language: fr, start_paths: ["/web/scn"], path_allowlist: ["/web/scn/"]}
```

### VS claim checks
- **Wrong:** `tribunaux.vs.ch/fr/*` has no DNS (pre-check) → `www.vs.ch/web/tribunaux`.
- **Wrong** (404), with the real location: dogs `/web/scav/chiens` → `/web/scav/veterinaire/affaires-canines`; school `/web/se/vacances-scolaires` → `/web/se/plans-de-scolarite`; communes `/web/sifom/communes` → `/web/communes/commune`.
- **Confirmed** (200): tax `/web/scc/personnes-physiques` (the actual guide is at `/web/guide-de-taxation`), road `/web/scn`, chancellery `/web/che`.

---

## Part 2: court and legal links

### entscheidsuche.ch and github.com/entscheidsuche
- **Status:** entscheidsuche.ch is 200 (722 B JS shell). The GitHub API lists 7 repos. Current scrapers are in **`NeueScraper`** (AGPL-3.0, pushed 2026-09-18). The old `scraper` repo was last pushed in 2021 and has no licence. Not opened: `entscheidsuche-mcp` and `headless-scraping-subsystem`.
- **Does it list every court portal? Yes, in the code:** 57 spiders cover **all 26 cantons** plus federal bodies.
- **Two caveats:**
  - `Description/Spiderliste.xlsx` (48 rows) is **stale for 6 hosts**. Examples: VS listed as rechtsprechung.vs.ch/WeblawVaadin but the code uses api-justsearche.vs.ch; AG agve.weblaw.ch vs decwork.ag.ch; BL www.baselland.ch vs bl.swisslex.ch; TG ogbuch.tg.ch vs rechtsprechung.tg.ch.
  - Hosts in the table below come from a regex over the spider sources, and platform types from base classes or code strings. I read only GR, TI and VS line by line, and tested only VS live.

| Canton | Portal host (from spider code) | Platform / endpoint |
|---|---|---|
| AG | decwork.ag.ch; www.ag.ch | JSON API; PDF lists |
| AI | www.ai.ch | simple lists → PDF |
| AR | rechtsprechung.ar.ch | Weblaw Vaadin |
| BE | zsg-entscheide, vg-urteile, strk-entscheide, bvd-entscheide, aa-entscheide `.apps.be.ch`; several `*.be.ch` | Tribuna ×5; PDF lists |
| BL | bl.swisslex.ch | JSON API |
| BS | rechtsprechung.gerichte.bs.ch | Omnis CGI (POST) |
| FR | publicationtc.fr.ch | Tribuna |
| GE | justice.ge.ch | parametrised lists → PDF |
| GL | findinfo.gl.ch | Omnis FindInfo CGI (POST) |
| **GR** | **entscheidsuche.gr.ch** | **Tribuna GWT-RPC POST `/tribunavtplus/loadTable`** |
| JU | jurisprudence.jura.ch | Tribuna |
| LU | gerichte.lu.ch | search page (POST) |
| NE | jurisprudence.ne.ch | Omnis (POST) |
| NW | www.nw.ch | list → PDF |
| OW | rechtsprechung.ow.ch | Weblaw Vaadin |
| SG | publikationen.sg.ch | search page |
| SH | obergerichtsentscheide.sh.ch | search page → PDF |
| SO | gerichtsentscheide.so.ch | Omnis CGI (POST) |
| SZ | gerichte.sz.ch | Tribuna ×2 |
| TG | rechtsprechung.tg.ch | POST form |
| **TI** | **www.sentenze.ti.ch** | **Omnis CGI POST `/cgi-bin/nph-omniscgi`** |
| UR | www.ur.ch | list → PDF |
| VD | prestations.vd.ch; www.jurisprudence.vd.ch | FindInfo JSON API; Omnis |
| **VS** | **api-justsearche.vs.ch** | **JSON GET `/api/search/?offset&limit`, PDFs at `/api/documents/{id}/file/` (tested live: 5,006)** |
| ZG | obergericht.zg.ch; verwaltungsgericht.zg.ch | Tribuna |
| ZH | www.gerichte-zh.ch; vgrzh.djiktzh.ch; findex.webgate.cloud; www.baurekursgericht-zh.ch; www.strgzh.ch | search page → PDF; Omnis CGI; JSON API; POST form; list |
| CH | search.bger.ch; bvger.ch/jurispub.admin.ch; bstger.weblaw.ch; bundespatentgericht.ch; weko, edoeb, oa, bj, amtsdruckschriften (`.admin.ch`); hudoc; servat.unibe.ch; sportstribunal.ch | Eurospider (headless browser); lists; Weblaw API |

This confirms all three of my C4 cells.

### Onlinekommentar
- **Pages:** `onlinekommentar.ch` redirects to `/de` (200). `/en/apis` (200) documents two APIs.
- **JSON API:** `GET /api/commentaries?language=de` (Accept: application/json) → 200 `{data, links, meta}`, 8 pages in DE. Fields: id (uuid), title (e.g. "Art. 1b BankG"), date, language, authors[], editors[], legislative_act{id, title}, html_link, pdf_link.
- **OAI-PMH:** `/oai?verb=ListRecords&metadataPrefix=oai_dc` → 50 records per page, **completeListSize 1,657**, 24 `legal_domain` sets.
- **Licence:** `dc:rights` = CC BY 4.0.
- **Fit:** `institutional`. It is article-by-article commentary on federal acts, which is low value for local citizen questions. The repo already reaches its text through opencaselaw (`ogd_lists_assessment.md:771`).
- **Oddity:** the resumptionToken `expirationDate` is 2026-09-17, six days before my request. Possibly a cached response; not verified.

### CLDS UZH "Useful Databases"
The page (200) lists 5 Swiss datasets.
- **Not covered by the repo:**
  - **SCD**, Swiss Federal Supreme Court Dataset (zenodo 7793043): 116,000+ cases since 2007, 31 variables.
  - **SwissJudgmentPrediction** (zenodo 5529712): 85,000 federal supreme court cases, 2000–2020.
  - **SRF coercive-measures sheet** (2017 counts per canton, Google Sheet).
- **Already covered:** opendata.swiss and OpenCaseLaw.
- **Out of scope:** the rest of the page (EU, ECHR, US and international datasets).
- **Verdict:** none of them holds citizen-facing rules, so `not-a-source`. At most, SCD and SwissJudgmentPrediction could be federal-level evaluation assets.

### opencaselaw Atom feeds
All three answer 200 as `application/atom+xml` with 50 entries each. The feed `<updated>` is 2026-09-23T11:21Z (today).

| Feed | Title | Newest entry | Oldest of the 50 |
|---|---|---|---|
| ti_gerichte | "TI Tribunale d'appello — neue Entscheide" | 2026-07-08 | 2026-02-15 |
| gr_gerichte | "GR Gerichte — neue Entscheide" | 2026-09-14 | 2026-08-10 |
| vs_gerichte | "VS Kantonsgericht — neue Entscheide" | 2026-09-06 | 2026-06-05 (entries not strictly sorted) |

- **Entry format:** id and link `https://mcp.opencaselaw.ch/entscheid/<court>_<docket>`; **the docket contains raw spaces** (e.g. `gr_gerichte_SR2 2026 44`), which makes an invalid IRI. Title is "Gericht <docket> vom <date>" (German template for every court). updated and published both equal the decision date. No `<summary>` in the entries I checked.
- **Use:** good for freshness monitoring, not for content.

---

## Cross-canton

### New fetcher classes needed
- **`fetcher:pdf-index`** (listing page → PDF links): GR practice rules (88 PDFs on 6 pages) and Wegleitungen, Lugano legislazione (122 texts), TI calendars (4). The same pattern likely fits other city collections (inferred).
- **`fetcher:amtsblatt-xml`** (Amtsblattportal API with `cantons=`, `municipalityId`, and the XML body per notice): TI and VS gazettes (about 2,000 notices a month each). It would cover the other Amtsblattportal cantons too, but **not GR** (DIAM, blocked by robots.txt).
- **`fetcher:pdf-table`** (table rows → per-body events): the GR Ferienplan (about 172 school bodies). Design question: how to map a Schulträgerschaft to BFS communes.
- **`resolver` inputs:**
  - VS: 122 commune pages with BFS number, website and commune judge.
  - GR: AFG page (99 domains) and ALG PDF (BFS numbers).
  - TI: SEL XLSX (names and districts only).
- **`fetcher:paginated-json`:** VS JustSearch, Onlinekommentar. Low priority, since decisions come through opencaselaw and Onlinekommentar is institutional.
- **`fetcher:oai-pmh`:** Onlinekommentar only. Low value.
- **html_crawl with query strings:** the VS Guide de taxation. It needs a check that the crawler keeps query strings.
- **`fetcher:lexwork`** (existing): gr-lex and lex.vs.ch, for GR VetG 914.000, GR 421.000 and VS LTar 173.8.

### Blocked items
- **GR Kantonsamtsblatt:** robots.txt disallows `/publikationen/` and `/ekab/`.
- **vs.ch `/documents/` and `*.pdf`:** disallowed by robots.txt (tax guides, school plans).
- **VS school plans:** holidays are colour-coded, so the dates are not in the PDF text.
- **VS court-fee calculator:** macro-driven `.xls`; the `.xlsm` link is 404.
- **GR decisions (GWT-RPC) and TI decisions (Omnis POST):** no clean API; opencaselaw covers both.
- **TI resident court-fee page:** none exists (full ladder in the C2 row).
- **`rlws.ti.ch` web service:** no connection.

### 5 best finds
1. **Lugano legislazione:** 122 municipal texts with text-layer PDFs, including the dog leash ordinance, waste rules and bag tax 2026, and parking tariffs. It reverses the repo's "not-a-source" verdict.
2. **VS commune directory:** 122 pages, each with BFS number, website and the commune judge (the conciliation authority per commune).
3. **Amtsblattportal `cantons=` filter:** it works, `tenants=` is ignored. That gives TI (2,014) and VS (1,942) notices since 1 Sept, with `municipalityId`, so a gazette fetcher for TI and VS is ready to build.
4. **GR school holidays:** one per-school-body PDF for the whole canton, plus the legal split (BR 421.000 Art. 24 Abs. 3: canton sets autumn and Christmas, school bodies the rest).
5. **entscheidsuche `NeueScraper` code:** decision portal and platform for all 26 cantons. Along the way, the VS JustSearch JSON API (5,006 decisions) and the verified 2025 GR court merger.

The claims above are labelled verified or inferred. Per the repo's CLAUDE.md, run `/audit` on the consolidated report before anyone acts on it.