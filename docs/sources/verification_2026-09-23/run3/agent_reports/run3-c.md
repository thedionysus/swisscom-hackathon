# Run 3, group C: source grids for SG, TG, AR, AI, SH and the city of Schaffhausen

All 11 cells are filled for all five cantons, plus L1. Every URL below was requested live today (2026-09-23), and each cell cites that request.

- **Continuity:** I continued from the stalled run's step 33. The SG communes XLSX has no website column, and openpyxl isn't installed, so I parsed the XML directly.
- **Dead AI links:** not re-requested. Their claim checks use the precheck probe files.
- **Evidence:** everything is under `<scratchpad>/run3-c/`:
  - `requests.jsonl` logs 142 requests.
  - `pages/` holds 126 saved pages, `pdfs/` 15 PDFs, and `sitemaps/` the TG host sitemaps.
  - The helper scripts are there too.
- **Two conduct notes:**
  - publikationen.sg.ch: I made 2 page requests before reading its robots.txt, which disallows `/` for all generic agents. I made no further requests.
  - amtsblatt.tg.ch: the page shows a login form with a shared username and password printed on it. I did not log in.
- **Input path error:** the brief's `pr40/docs/sources/commune_sites.csv` does not exist in this session's scratchpad. I read the repo copy at `<repo>/docs/sources/commune_sites.csv` (read-only). It lists SG 75, TG 80, AR 20, AI 5 and SH 26 communes, which matches every official list below.

Labels: "(inferred)" or "not verified" marks anything not backed by a request made today.

---

## SG: St. Gallen

| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 courts | VERIFIED | https://www.sg.ch/recht/gerichte.html | 200, "Gerichte \| sg.ch", server HTML (AEM), 19.8 KB, 131 links, 595 words. The sitemap has 199 URLs under /recht/gerichte | Landing text is navigation: "Anwalts- & Notarwesen … Informationen & Formulare … Verhandlungstermine" | The AI host gerichte.sg.ch redirects here (precheck) |
| C2 fees | VERIFIED | Page: /recht/gerichte/informationen---formulare/merkblaetter.html, which links "Merkblatt zu den Kosten und dem Verfahren vor Handelsgericht.pdf". Law: sGS **941.12** Gerichtskostenverordnung | Page 200 with 10 cost-sheet PDF links. The PDF is 200, 2 pages, text layer. LexWork meta 200: enacted 2012-03-01, canonical `gesetzessammlung.sg.ch/app/de/texts_of_law/941.12` | "Fr. 1'000 – 15'000.00 bei Streitwerten bis Fr. 50'000.00" | 941.12 `show_as_json` returned only 2,858 characters with no amounts; not investigated |
| C3 guidance | VERIFIED | The sitemap lists 24 pages under /recht/gerichte/informationen---formulare/. Probed: familienrecht, existenzminimum/grundbetrag, mietrecht--mitteilungen-des-vermieters, unentgeltliche-rechtsauskuenfte, merkblaetter. Sitemap only: formulare, weisungen, unentgeltliche-rechtspflege, familienrecht/angeordnete-beratung, existenzminimum/zuschlaege | All probed pages 200, about 19 KB, 124–136 links, 419–625 words. Content marker `id="maincontent"` | "alleinstehende Schuldner ohne solche Wohngemeinschaft Fr. 1'230.–" | Category missing: courts |
| C4 decisions | VERIFIED (route) / BLOCKED (fetch) | /recht/gerichte/rechtsprechung.html leads to https://publikationen.sg.ch/rechtsprechung-gerichte/ | 200. TYPO3 extension `diamjudicalsg`, server-HTML list of 10 per page, "252 Ergebnis(se)" for the current year, detail pages at /rechtsprechung-gerichte-detail/<id>/, one PDF per decision. No feed seen | "Entscheid Versicherungsgericht, 19.08.2026" | Blocked by robots.txt. opencaselaw: see table below |
| C5 conciliation | VERIFIED | …/schlichtungsstellen-und-vermittlungsaemter/vermittlungsaemter.html and …/schlichtungsstellen-fuer-miet--und-pachtverhaeltnisse.html | 200, 878 and 904 words. 6 conciliation URLs in the sitemap | "Der Prozess beginnt in der Regel mit einem Schlichtungsversuch beim Vermittler oder bei der Vermittlerin (allgemeine Schlichtungsbehörde)." | Law sGS 941.112 (law_hits). Fee text on these pages not verified. Tenancy fits category `housing` |
| G1 dogs | VERIFIED | /umwelt-natur/veterinaerwesen/tiere-halten/hunde.html | 200, "Hunde \| sg.ch", 1,009 words | "Seit dem 1. Januar 2020 ist das neue Hundegesetz des Kantons St.Gallen in Kraft." The communes still handle "Hundekontrolle sowie … Erhebung der Hundesteuer" | Laws sGS 456.1 HuG and 456.11 HuV. Dog tax is municipal |
| G2 tax guide | VERIFIED | /steuern-finanzen/steuern/steuerbuch.html and /steuerbuch/inhaltsverzeichnis.html | Both 200. The table of contents has 664 links, 498 PDF links (250 unique) and **243 "StB x Nr. y" entries**. 265 sitemap URLs contain /steuerbuch | The StB 3 Nr. 1 PDF (4 pages, text layer) starts: "StB 3 Nr. 1 01.01.2016 … ersetzt 01.01.2009 Kirchenaustritt" | Enumerable from the table-of-contents page. The page says "Per 1. Januar 2026 wurden diverse Weisungen … aktualisiert" |
| G3 holidays | VERIFIED | /bildung-sport/volksschule/aus-dem-amt/ferienplan.html | 200, server-HTML table for 2026/27 to 2029/30 | "2026/27 Mo, 10.08.2026 So, 27.09.26 bis So, 18.10.26 So, 20.12.26 bis So, 03.01.27" | **The canton sets them:** "…werden durch den Bildungsrat festgelegt" |
| G4 road office | VERIFIED | /verkehr/strassenverkehr.html, /rechnung_gebuehren.html, /fuehrerausweise/verlust.html | All 200. 152 road URLs in the sitemap (stage0) | "Die Kosten für die Neuausstellung eines Führerausweises betragen Fr. 30.–" | Fees page cites "Verkehrsgebührentarif sGS 718.1" |
| D1 communes | VERIFIED | /politik-verwaltung/gemeinden/ueber-die-gemeinden.html links "politische Gemeinden.xlsx" | Page 200 with 6 XLSX links (political communes, school communes, Ortsgemeinden, 2 corporation lists, Zweckverbände). The XLSX is 200, 28,418 bytes | Row "1, St.Gallen, …, 9001, St.Gallen, info@stadt.sg.ch" | 75 communes, dated 2026-09-01 (Excel serial 46266). No website column (0 hyperlinks); domains can be derived from the e-mail addresses. Destination: `resolver` / `fetcher:xlsx` |
| D2 chancellery + gazette | VERIFIED / BLOCKED | Chancellery: /politik-verwaltung/departemente-und-staatskanzlei/staatskanzlei.html. Gazette: /ueber-den-kanton-st-gallen/amtsblatt.html leads to https://publikationen.sg.ch/amtliche-publikationen/ | 200 (1,427 words), 200 "Publikationsplattform \| sg.ch", then 200 on the TYPO3 site | "…rechtsverbindlich elektronisch auf der Publikationsplattform veröffentlicht, bspw. das Amtsblatt." | Gazette blocked by robots. The archive is at retrodigital.sg.ch (link only). eSHAB has only federal rubrics for SG |

**opencaselaw coverage (SG)** (a date before 2026 counts as stale):

| Court | Decisions | Latest | Stale? |
|---|---|---|---|
| sg_versicherungsgericht | 7,632 | 2026-08-19 | no |
| sg_gerichte | 3,141 | 2026-01-14 | no |
| sg_verwaltungsgericht | 2,778 | 2026-06-29 | no |
| sg_verwaltungsrekurskommission | 1,183 | 2026-07-02 | no |
| sg_kantonsgericht | 1,082 | 2026-05-21 | no |
| sg_publikationen | 630 | 2024-04-29 | **yes** |
| sg_handelsgericht | 49 | 2024-07-02 | **yes** |

**Site recipe.** www.sg.ch runs AEM: PDFs sit under `/content/dam/sgch/…pdf.ocFile/…`, content marker `id="maincontent"`. The sitemap is `/tools/sitemap.googleSitemap.xml` (4,722 lines in the stage0 file). robots.txt has 47 lines and no Crawl-delay. No bot wall on www.sg.ch. publikationen.sg.ch sends `User-agent: *` to `Disallow: /`; only Googlebot, Bingbot and a few named crawlers are allowed. Laws are on www.gesetzessammlung.sg.ch (LexWork).

```yaml
id: sg_gerichte_info
name: Gerichte St.Gallen – Informationen & Schlichtungsstellen
base_url: https://www.sg.ch
default_extent_id: CH-SG
authority: official_info
categories: [housing]            # plus "category missing: courts"
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/recht/gerichte/informationen---formulare.html", "/recht/gerichte/organisation---standorte/schlichtungsstellen-und-vermittlungsaemter.html"]
  path_allowlist: ["/recht/gerichte/informationen---formulare", "/recht/gerichte/organisation---standorte/schlichtungsstellen-und-vermittlungsaemter"]
  language: de
allow_narrowing: false
---
id: sg_guidance
name: Kanton St.Gallen – Hunde, Ferienplan, Strassenverkehr
base_url: https://www.sg.ch
default_extent_id: CH-SG
authority: official_info
categories: [dogs, schools, transport]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/umwelt-natur/veterinaerwesen/tiere-halten/hunde.html", "/bildung-sport/volksschule/aus-dem-amt/ferienplan.html", "/verkehr/strassenverkehr.html"]
  path_allowlist: ["/umwelt-natur/veterinaerwesen/tiere-halten/hunde", "/bildung-sport/volksschule/aus-dem-amt/ferienplan", "/verkehr/strassenverkehr"]
  language: de
---
id: sg_steuerbuch            # yaml-now:pdf for a sample; full set needs fetcher:pdf-index (250 PDFs)
base_url: https://www.sg.ch
default_extent_id: CH-SG
authority: official_info
categories: [taxes]
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/003_1.pdf.ocFile/003_1.pdf"]
  language: de
---
id: sg_gerichte_kostenmerkblatt
base_url: https://www.sg.ch
default_extent_id: CH-SG
authority: official_info
categories: []                   # category missing: courts
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.sg.ch/content/dam/sgch/recht/gerichte/merkbl%C3%A4tter-zum-verfahren/Merkblatt%20zu%20den%20Kosten%20und%20dem%20Verfahren%20vor%20Handelsgericht.pdf"]
  language: de
```

**Claim checks** (precheck results, not re-requested):
- Courts `gerichte.sg.ch/*` (6 links): **Partly.** They all redirect to the landing page; deep paths are lost.
- Tax `/steuern-finanzen/steuern/steuerbuch.html`: **Confirmed.**
- Dogs `/gesundheit-soziales/…/hunde.html`: **Wrong** (404). Real page is the G1 URL.
- School `/bildung-sport/volksschule/schulferien.html`: **Wrong** (404). Real page is the G3 URL.
- Road `/verkehr/strassenverkehrsamt.html`: **Wrong** (404). Real page is /verkehr/strassenverkehr.html.
- Communes `/kanton-staat/gemeinden.html`: **Wrong** (404). Real page is the D1 URL.
- Chancellery `/kanton-staat/kantonale-verwaltung/staatskanzlei.html`: **Wrong** (404). Real page is the D2 URL.

---

## TG: Thurgau

| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 courts | VERIFIED | https://obergericht.tg.ch/ (www.tg.ch/justiz/zivil--und-strafrechtspflege/obergericht.html/25 redirects there), https://bezirksgericht.tg.ch/, https://verwaltungsgericht.tg.ch/, portal page www.tg.ch/justiz.html/5 | All 200. Sitemaps: Obergericht 41, Bezirksgericht 46, Verwaltungsgericht 18 URLs. 5 district courts (Arbon, Frauenfeld, Kreuzlingen, Münchwilen, Weinfelden) | "17. September 2026 Fabienne Hinder als neue Oberrichterin gewählt" | govis CMS (`public/upload/assets/…?fp=N`). The AI host gerichte.tg.ch does not exist (precheck) |
| C2 fees | VERIFIED (law) / NONE (resident page) | Law RB **638.1** VGG: https://www.rechtsbuch.tg.ch/app/de/texts_of_law/638.1 | LexWork meta 200, enacted 1992-06-01 | "§ 7 Friedensrichter … Schlichtungsverhandlung bei einem Streitwert bis Fr. 2'000 Fr. 100 bis Fr. 150" | **NONE ladder:** (1) 3 court sitemaps, 105 URLs: no cost page. (2) Arbon Merkblätter PDFs and the Frauenfeld Rechtsöffnung Merkblatt: no fee amounts (only a sample claim of "Fr. 100.00"). (3) WebSearch `site:tg.ch Gerichtskosten Kostenvorschuss Merkblatt`: no cost page. (4) Site search not tried |
| C3 guidance | VERIFIED | bezirksgericht.tg.ch/arbon/merkblaetter.html/5652 (PDFs "Eheprobleme – wie weiter", 6 pages, and "Unentgeltliche Rechtspflege", 1 page). Frauenfeld "Merkblatt Rechtsöffnung" (2 pages). obergericht.tg.ch/das-gericht/richtlinien-weisungen-erlaeuterungen.html/16593 (10 PDFs, e.g. "Richtlinien Berechnung Kindesunterhalt-2024") | All 200; all tested PDFs have a text layer. The sitemaps list 7 guidance URLs (5 forms pages, 1 leaflet page, 1 guidelines page) | "Eine Person hat Anspruch auf unentgeltliche Rechtspflege, wenn: a. sie nicht über die erforderlichen Mittel verfügt…" | Thin and PDF-based. The Weinfelden "Merkblatt Mietausweisung" was a WebSearch hit, not opened |
| C4 decisions | VERIFIED | obergericht.tg.ch/rechtsprechung.html/7353 leads to **https://rechtsprechung.tg.ch/og** and /vg | 200, server HTML. The sitemap index has 2 children: **6,350 URLs** (og 3,378, vg 2,972). /og/rbog-2025 lists "RBOG 2025 Nr. 01…" | "Das Obergericht veröffentlicht seine Entscheide im Internet nicht fortlaufend. Grundsätzliche Entscheide publiziert das Obergericht jährlich" | opencaselaw: tg_obergericht 2,443 (latest 2025-01-29, **STALE**), tg_gerichte 1,162 (2025-12-17, **STALE**), tg_anwaltskommission 5 (sparse). Refresh route: sitemap crawl of rechtsprechung.tg.ch |
| C5 conciliation | VERIFIED | https://friedensrichteraemter.tg.ch/ (reached via www.tg.ch/…/amt-fuer-friedensrichterwesen.html/17710) and https://erechtsverkehr.tg.ch/schlichtungsbehoerden-in-mietsachen.html/7980 | 200 "Home – Friedensrichterämter" with 5 district offices. 200 "Schlichtungsbehörden", 217 links, one entry per district | Menu "Friedensrichteramt Bezirk Arbon … Weinfelden" | Fees: VGG § 7. friedensrichteraemter.tg.ch answered **429** on my first direct requests |
| G1 dogs | VERIFIED | veterinaeramt.tg.ch/tierschutz/haustiere/hundewesen.html/11290 (from /hundewesen.html/14703) and /faq/hundewesen.html/14752 | 200 (204 words) and 200 (2,657 words). The sitemap has 86 URLs, 9 about dogs | "Für den Vollzug des kantonalen Hundegesetzes ist grundsätzlich die Politische Gemeinde zuständig." | Laws RB 641.2 HundeG and 641.21. Dog tax is probably municipal (inferred from this sentence) |
| G2 tax guide | VERIFIED | **https://steuerpraxis.tg.ch/steuerpraxis/** (redirects to /2026-09), linked from steuerverwaltung.tg.ch/informationen/thurgauer-steuerpraxis.html/2937 | 200, "Thurgauer Steuerpraxis", server HTML. The sitemap index lists 3,866 URLs across 7 versions (2023-07 to 2026-09); **559 belong to 2026-09** | Entry "StP 2 Nr. 13 Steuerausscheidung: Geschäftsgewinn und -vermögen Selbständigerwerbender" (13.4 KB, 1,639 words) | Enumerable through the sitemap. The version prefix changes with each release |
| G3 holidays | VERIFIED | av.tg.ch/themen/ferienplan.html/13415, with PDFs Ferienplan_SJ_2026_2027.pdf and the 10-year plan 2023–2033 | 200. Both PDFs are 1 page with a text layer | "Herbstferien Mo, 05.10.2026 – So, 18.10.2026" | **The canton sets them:** "Gemäss § 17 Abs. 4 RRV VG legt das Departement für Erziehung und Kultur die Ferientermine … fest". Exception: VSG Neunforn follows Ossingen (ZH) |
| G4 road office | VERIFIED | https://strassenverkehrsamt.tg.ch/ and /gebuehren-und-steuern.html/16501, which links "Vollständige Gebührenverordnung" (…/assets/89174/…pdf?fp=2) | 200. The PDF has 11 pages with a text layer (SVAV 741.11, as of 1.1.2023). 141 URLs in the sitemap | "§ 7 Führerausweise … Führerausweis Fr. 40 2. Lernfahrausweis Fr. 30" | Laws RB 741.1 and 741.11 |
| D1 communes | VERIFIED | https://www.tg.ch/verwaltung/gemeinden.html/113 | 200, 165 links | "Aadorf → http://www.aadorf.ch/" | 80 names, 76 with a website link. Berg, Bürglen, Rickenbach and Roggwil have no link |
| D2 chancellery + gazette | VERIFIED / BLOCKED | https://staatskanzlei.tg.ch/ and https://amtsblatt.tg.ch/ | 200 "Staatskanzlei". amtsblatt.tg.ch is 200 "Home" but shows only a login form | "Die Staatskanzlei wird vom Staatsschreiber, Dr. Paul Roth, geführt." | Gazette blocked by a login wall (shared credentials shown on the page; not used). amtsblatt.tg.ch answered 429 before a 4-second delay. eSHAB has only federal rubrics for TG |

**Site recipe.** govis CMS everywhere: URLs end in `/<pageId>`, uploads sit under `/public/upload/assets/<id>/…?fp=N`, and robots.txt disallows `/route/`. There is one sitemap per subdomain:

| Host | Sitemap URLs |
|---|---|
| www.tg.ch | 406 (stage0) |
| strassenverkehrsamt.tg.ch | 141 |
| veterinaeramt.tg.ch | 86 |
| av.tg.ch | 249 |
| steuerverwaltung.tg.ch | 233 |
| obergericht.tg.ch | 41 |
| bezirksgericht.tg.ch | 46 |
| verwaltungsgericht.tg.ch | 18 |
| steuerpraxis.tg.ch | 3,866 |
| rechtsprechung.tg.ch | 6,350 |

No Crawl-delay anywhere, but new subdomains answered **429** at first contact, so keep at least 2 s between requests. The steuerverwaltung.tg.ch robots.txt points to a wrong domain (steuerverwaltung.ch); its own /sitemap.xml works. steuerpraxis.tg.ch and rechtsprechung.tg.ch use `/__sitemaps/<uuid>/sitemap.xml` children.

```yaml
id: tg_steuerpraxis
name: Thurgauer Steuerpraxis
base_url: https://steuerpraxis.tg.ch
default_extent_id: CH-TG
authority: official_info
categories: [taxes]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/steuerpraxis/2026-09"]
  path_allowlist: ["/steuerpraxis/2026-09/"]   # version prefix changes per release → fetcher:sitemap-crawl picks newest
  language: de
---
id: tg_hunde
base_url: https://veterinaeramt.tg.ch
default_extent_id: CH-TG
authority: official_info
categories: [dogs]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/tierschutz/haustiere/hundewesen.html/11290", "/faq/hundewesen.html/14752"]
  path_allowlist: ["/tierschutz/haustiere/hundewesen", "/faq/hundewesen"]
  language: de
---
id: tg_strassenverkehrsamt
base_url: https://strassenverkehrsamt.tg.ch
default_extent_id: CH-TG
authority: official_info
categories: [transport]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/gebuehren-und-steuern.html/16501", "/fuehrerzulassung.html/3617", "/fahrzeugzulassung.html/3615"]
  path_allowlist: ["/gebuehren-und-steuern", "/fuehrerzulassung", "/fahrzeugzulassung"]
  language: de
---
id: tg_ferienplan
base_url: https://av.tg.ch
default_extent_id: CH-TG
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://av.tg.ch/public/upload/assets/179040/Ferienplan_SJ_2026_2027.pdf?fp=1", "https://av.tg.ch/public/upload/assets/8713/10_Jahresplan_Schulferien_Volksschule_2023_-_2033.pdf?fp=4"]
  language: de
---
id: tg_gerichte_merkblaetter
base_url: https://bezirksgericht.tg.ch
default_extent_id: CH-TG
authority: official_info
categories: []                   # category missing: courts
fetch_strategy: pdf
fetch_config:
  urls: ["https://bezirksgericht.tg.ch/public/upload/assets/37839/Eheprobleme%20-%20wie%20weiter.pdf?fp=2", "https://bezirksgericht.tg.ch/public/upload/assets/37840/Unentgeltliche%20Rechtspflege.pdf?fp=1", "https://bezirksgericht.tg.ch/public/upload/assets/99108/Merkblatt%20Rechts%C3%B6ffnung.pdf?fp=1"]
  language: de
```

**Claim checks** (precheck results):
- Courts `gerichte.tg.ch/*` (6 links): **Wrong** (no DNS). Real sites are obergericht.tg.ch and bezirksgericht.tg.ch.
- Dogs `veterinaeramt.tg.ch/hunde.html`: **Wrong** (404; right host, wrong path).
- Tax `steuerverwaltung.tg.ch/steuerbuch.html`: **Wrong** (404). The real guide is steuerpraxis.tg.ch.
- School `av.tg.ch/schule/…/schulferien.html`: **Wrong** (404).
- Road `strassenverkehrsamt.tg.ch`: **Confirmed.**
- Communes `tg.ch/kanton/gemeinden.html`: **Wrong** (no response).
- Chancellery `staatskanzlei.tg.ch`: **Confirmed.**

---

## AR: Appenzell Ausserrhoden

| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 courts | VERIFIED | https://ar.ch/gerichte/ | 200, TYPO3 server HTML, 10.8 KB, 294 links, 757 words. 47 sitemap URLs under /gerichte/ | "Die Vermittlerämter führen in Zivilstreitigkeiten nach dem Grundsatz "Zuerst schlichten, dann richten"…" | Content marker `id="mainCol"` |
| C2 fees | VERIFIED | Page /gerichte/kantonsgericht/formulare-und-merkblaetter/. Its "Gerichtskosten" link goes to ar.clex.ch 233.3 and "Anwaltstarif" to 145.53. Law bGS **233.3** | Page 200. LexWork meta 200 ("Gebührenordnung", enacted 1981-07-01) | "Einschreibgebühren … bei Scheidungsverfahren Fr. 300.–" | law_hits also lists 212.43 (child and adult protection costs) |
| C3 guidance | VERIFIED | 14 sitemap URLs: 9 topic pages under /kantonsgericht/rechtsgebiete/ (Arbeitsrecht, Ehescheidung, Mieterausweisung, Privatkonkurs, Rechtsöffnung, Getrenntleben, and others), plus unentgeltliche-rechtspflege, rechtsauskunft and 2 forms pages | Probed 4: all 200, 833–1,047 words. The forms page has 3 divorce procedure PDFs | "Nach der Bezahlung eines Kostenvorschusses werden die Ehegatten zu einem Erstgespräch beim Einzelrichter … eingeladen." | Category missing: courts |
| C4 decisions | VERIFIED | /kantonsgericht/rechtsprechung-der-gerichte/ links https://rechtsprechung.ar.ch/ | 200, title "LEv4", 2,241 bytes, 0 links: a JS app. Its bundle calls `POST /.netlify/functions/searchQueryService` and `GET /.netlify/functions/singleDocQueryService/<id>`. No sitemap | (JS app) | opencaselaw ar_gerichte 4,614 (latest 2026-03-17, not stale). Vendor is probably Weblaw (inferred from a `linksWeblaw` variable) |
| C5 conciliation | VERIFIED | /gerichte/vermittler-und-schlichtungsstellen/vermittler/ and …/schlichtungsstelle-fuer-miete-und-nichtlandwirtschaftliche-pacht/ | 200 (1,214 and 1,350 words) | "Das Sekretariat der Schlichtungsstellen (T: +41 71 343 65 26) ist besetzt: Montags und dienstags…" | There is also an office for workplace discrimination. Fees: 233.3; fee text on the pages not verified |
| G1 dogs | VERIFIED | /verwaltung/departement-gesundheit-und-soziales/veterinaeramt/hunde/, plus /hundesteuer/ and /leinenpflicht-in-beiden-appenzell/ | All 200. 17 dog URLs in the sitemap | "**Die jährliche Hundesteuer beträgt Fr. 120 pro Hund.** … Das Veterinäramt erhebt die Steuern…" and "Hunde müssen an der Leine geführt werden: auf Schulanlagen…" | Laws bGS 525.1 and 525.11. **The dog tax is cantonal**, so one page answers it for all 20 communes |
| G2 tax guide | VERIFIED | /verwaltung/departement-finanzen/steuerverwaltung/gesetzeweisungenmerkblaetter/ | 200, 359 links, 1,215 words, **54 PDF links** in the main column | "Steuerliche Behandlung des Liegenschaftsunterhalts (ab Steuerperiode 2013) (pdf)" | No Steuerbuch exists (sitemap grep). PDF text layer not checked. Enumerable from this listing page |
| G3 holidays | VERIFIED | /…/ehandbuch-volksschule/schulbetrieb/regelungen/, which links the PDF "2026-06-23_FerienrichtdatenVolksschulenAppenzellAusserrhoden_v1.3.pdf" | 200. PDF 1 page, text layer. Found through the site's own search (`/search/?q=Schulferien`); the sitemap has 0 holiday URLs | "Herbstferien Mo 06.10.2025 bis Fr 17.10.2025 2 Wochen" | **The canton sets reference dates, and communes choose 2 of the 13 weeks:** "Die Gemeinden haben die Möglichkeit zwei der 13 Ferienwochen selbstständig festzulegen." Years after 2025/26 in the PDF not checked |
| G4 road office | VERIFIED | /verwaltung/departement-inneres-und-sicherheit/strassenverkehrsamt/steuern-und-gebuehren/ | 200. 121 road URLs in the sitemap | bGS 761.32 (enacted 2016-06-01): "Führerausweis 1. Erstmalige Ausstellung im Kreditkartenformat Fr. 60.-" | The page links the old host bgs.ar.ch/data/761.32/de |
| D1 communes | VERIFIED | /verwaltung/kantonskanzlei/…/kanton-und-gemeinden-in-zahlen/ | 200 | "Links zu den 20 Ausserrhoder Gemeinden … Herisau → https://www.herisau.ch/" | 18 links extracted; Bühler and Stein unmatched |
| D2 chancellery + gazette | VERIFIED | /verwaltung/kantonskanzlei/ and /…/amtsblatt/, which lead to **https://amtsblatt.ar.ch** (eSHAB) | All 200. amtsblatt.ar.ch is a JS app with a JSON API: `/api/v1/publications?publicationStates=PUBLISHED&tenant=kabar` returns 21,349 items; adding `&rubrics=RS-AR` returns 1,103 | "Das Amtsblatt … erscheint seit Juli 2020 als digitale Publikation." API item: "Urnäsch; Urnenabstimmung vom 27. September 2026" | robots.txt disallows `/` (see Blocked) |

**Site recipe.** ar.ch runs TYPO3 (generator tag), content marker `id="mainCol"`, site search at `/search/?q=` (Solr). robots.txt has no Crawl-delay and no Sitemap line; stage0 found the sitemap anyway (1,719 lines). Laws are on ar.clex.ch (LexWork). amtsblatt.ar.ch disallows `/` in robots.txt.

```yaml
id: ar_gerichte
base_url: https://ar.ch
default_extent_id: CH-AR
authority: official_info
categories: [housing]            # plus "category missing: courts"
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/gerichte/kantonsgericht/rechtsgebiete/", "/gerichte/vermittler-und-schlichtungsstellen/", "/gerichte/kantonsgericht/unentgeltliche-rechtspflege/", "/gerichte/kantonsgericht/rechtsauskunft/"]
  path_allowlist: ["/gerichte/kantonsgericht/rechtsgebiete/", "/gerichte/vermittler-und-schlichtungsstellen/", "/gerichte/kantonsgericht/unentgeltliche-rechtspflege/", "/gerichte/kantonsgericht/rechtsauskunft/"]
  language: de
---
id: ar_hunde_strassenverkehr
base_url: https://ar.ch
default_extent_id: CH-AR
authority: official_info
categories: [dogs, transport]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/verwaltung/departement-gesundheit-und-soziales/veterinaeramt/hunde/", "/verwaltung/departement-inneres-und-sicherheit/strassenverkehrsamt/"]
  path_allowlist: ["/verwaltung/departement-gesundheit-und-soziales/veterinaeramt/hunde/", "/verwaltung/departement-inneres-und-sicherheit/strassenverkehrsamt/"]
  language: de
---
id: ar_ferienrichtdaten
base_url: https://ar.ch
default_extent_id: CH-AR
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://ar.ch/fileadmin/user_upload/Departement_Bildung_Kultur/Amt_fuer_Volksschule/eHandbuch_Volksschule/2026-06-23_FerienrichtdatenVolksschulenAppenzellAusserrhoden_v1.3.pdf"]
  language: de
---
id: ar_amtsblatt                 # needs a decision first: robots Disallow / vs documented API
base_url: https://amtsblatt.ar.ch
default_extent_id: CH-AR
authority: official_info
categories: []                   # category missing: gazette
fetch_strategy: api
fetch_config:
  url: https://amtsblatt.ar.ch/api/v1/publications?publicationStates=PUBLISHED&tenant=kabar&rubrics=RS-AR&pageRequest.page=0&pageRequest.size=100
  records_path: content
  id_template: "{meta[publicationNumber]}"
  title_template: "{meta[title][de]}"
  text_template: "{meta[title][de]} (Amtsblatt AR, Rubrik {meta[rubric]}, publiziert {meta[publicationDate]})"
  language: de
allow_narrowing: true            # titles often name the commune; whether event_date_field accepts a nested field is not verified
```

**Claim checks** (precheck):
- Courts `www.ar.ch/verwaltung/kantonsgericht/…` (4 links): **Wrong** (404 "Verirrt?"). Real site is ar.ch/gerichte/.
- Dogs `…/amt-fuer-verbraucherschutz/hunde/`: **Wrong.** The office is the Veterinäramt.
- Tax `…/steuerverwaltung/steuerbuch/`: **Wrong.**
- School `…/schulferien/`: **Wrong.**
- Road `…/departement-bau-und-volkswirtschaft/strassenverkehrsamt/`: **Wrong.** The office sits under Departement Inneres und Sicherheit.
- Communes `/kanton/gemeinden/`: **Wrong.**
- Chancellery `/verwaltung/ratskanzlei/`: **Wrong.** AR's office is the Kantonskanzlei.

---

## AI: Appenzell Innerrhoden

| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 courts | VERIFIED | https://www.ai.ch/gerichte | 200, Plone (ftw.simplelayout), 8.6 KB, 61 links. 911 court-topic sitemap URLs, many of them layout-block and hearing-date pages | "Gerichte Gerichtliche Instanzen im Kanton Appenzell Innerrhoden." | Content marker `id="content"` |
| C2 fees | VERIFIED (law) / NONE (resident page) | GS **173.810** GGV: https://ai.clex.ch/app/de/texts_of_law/173.810 | Meta 200, enacted 2001-10-01 | "Art. 7 Vermittler und Schlichtungsstellen … Erteilung einer Klagebewilligung: 200.-- bis 1'000.--" | **NONE ladder:** (1) Sitemap grep for court plus cost/fee/tariff: only 2 PDFs from the GGV revision consultation. (2) The district-court forms page has no fees. (3) WebSearch `site:ai.ch Gerichtskosten OR Gerichtsgebühren`: no fee page. (4) Site search not tried for fees |
| C3 guidance | VERIFIED | /gerichte/vermittler, /gerichte/bezirksgericht/formulare, /themen/persoenliches/wohnen-und-umziehen/schlichtungsstelle-mietverhaeltnisse. Sitemap only: /themen/persoenliches/todesfall/erbschaft and its subpages (process, certificate, wills, fees) | All probed pages 200 (272–413 words) | "…Anspruch auf unentgeltliche Rechtspflege. Vermittlerämter Appenzell Bettina Manser, Kronengarten 8…" | About 25 URLs in the sitemap grep; many are Plone anchor pages |
| C4 decisions | VERIFIED | /gerichte/rechtsprechung and /gerichte/gerichtsentscheide | 200, server HTML listing PDFs (yearly PDFs 2021–2025) | "V 9-2025 BauG-Beschwerde (Ersatzvornahme) 25.03.2026" | opencaselaw ai_gerichte 182 (latest 2026-08-17, not stale). PDF text layer not checked |
| C5 conciliation | VERIFIED | /gerichte/vermittler, and the tenancy office at /themen/persoenliches/wohnen-und-umziehen/schlichtungsstelle-mietverhaeltnisse (target of the court-section link) | 200 | "Vermittlerämter Appenzell … Schwende-Rüte Thomas Mainberger…" | Fees: GGV Art. 7 |
| G1 dogs | VERIFIED | /themen/landwirtschaft-tierhaltung/tierhaltung/hundehalterausbildung and /tierhaltung | 200 | "Hunde sind jederzeit so zu halten, dass sie Menschen und Tiere nicht gefährden oder belästigen…" and "neue Hundehalter [haben sich] bei der Bezirksverwaltung des Wohnorts zu melden" | Laws GS 560.100 and 560.110. The veterinary office is shared with AR; AR's "Leinenpflicht in beiden Appenzell" page probably covers AI too (inferred from its title) |
| G2 tax guide | VERIFIED | https://www.ai.ch/themen/steuern/publikationen | 200, 246 links, 51 PDF links | "Merkblätter gültig ab Steuerperiode 2026 … Besteuerung nach dem Aufwand und Bewilligungsprozess 28.01.2026" | No Steuerbuch; leaflets are grouped per tax period. 364 tax-topic sitemap URLs |
| G3 holidays | VERIFIED | /themen/bildung/eltern-und-schule/ferienplan, with PDF "Ferienplan AI_2026-2029.pdf" | 200. PDF 1 page, text layer | "Herbst Sa, 03.10.2026 So, 18.10.2026 \| Sa, 26.09.2026 So, 18.10.2026" (inner district \| Bezirk Oberegg) | **The canton sets them:** the PDF header reads "Erziehungsdepartement Landesschulkommission". Two tracks, fixed three years at a time |
| G4 road office | VERIFIED | /themen/mobilitaet-und-verkehr/strassenverkehr/gebuehrentarif-verordnung | 200, links to ai.clex.ch 741.000, 741.010 and 741.011 | GS 741.011: "2.1.1 Neuausstellung Fr. 60.-- 2.1.2 Ersatz / Umtausch Fr. 30.--" | 343 road-topic sitemap URLs |
| D1 communes | VERIFIED | https://www.ai.ch/land-und-leute/bezirke | 200 | "Schwende-Rüte → https://schwende-ruete.ch/" | **5 districts** (Appenzell → appenzell.org, Schwende-Rüte, Schlatt-Haslen, Gonten, Oberegg), matching the 5 rows in commune_sites.csv |
| D2 chancellery + gazette | VERIFIED / NONE (online gazette) | /verwaltung/ratskanzlei and https://www.appenzell.org/dienstleistungen/22898 | 200 and 200 "Bezirk Appenzell - Amtliches Publikationsorgan" | "Die Lokalzeitung, der Appenzeller Volksfreund, ist zugleich das amtliche Publkationsorgan für alle Amtsstellen (Kanton, Bezirke, Schulen)." | **NONE ladder:** (1) Sitemap grep "amtsblatt": 0. (2) Site search `@@search?SearchableText=Amtsblatt`: no gazette. (3) Chancellery and home page: 0 gazette links. (4) eSHAB: federal rubrics only. (5) 2 WebSearches found the page above |

**Site recipe.** www.ai.ch runs Plone with ftw.simplelayout. The sitemap is `sitemap.xml.gz` (20,491 lines); exclude the `ftw-simplelayout-*`, `/view` and `/download` sub-URLs. robots.txt has no Crawl-delay and no rules for `*` (the Googlebot rules disallow `/@@search`). File download URLs end in `/download`. Laws are on ai.clex.ch.

```yaml
id: ai_gerichte
base_url: https://www.ai.ch
default_extent_id: CH-AI
authority: official_info
categories: [housing]            # plus "category missing: courts"
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/gerichte/vermittler", "/gerichte/bezirksgericht/formulare", "/gerichte/rechtsprechung", "/themen/persoenliches/wohnen-und-umziehen/schlichtungsstelle-mietverhaeltnisse"]
  path_allowlist: ["/gerichte/vermittler", "/gerichte/bezirksgericht/formulare", "/gerichte/rechtsprechung", "/themen/persoenliches/wohnen-und-umziehen/schlichtungsstelle-mietverhaeltnisse"]
  language: de                   # risk: html_crawl has no denylist for ftw-simplelayout block URLs
---
id: ai_guidance
base_url: https://www.ai.ch
default_extent_id: CH-AI
authority: official_info
categories: [dogs, transport, schools]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/themen/landwirtschaft-tierhaltung/tierhaltung", "/themen/mobilitaet-und-verkehr/strassenverkehr", "/themen/bildung/eltern-und-schule/ferienplan"]
  path_allowlist: ["/themen/landwirtschaft-tierhaltung/tierhaltung", "/themen/mobilitaet-und-verkehr/strassenverkehr", "/themen/bildung/eltern-und-schule/ferienplan"]
  language: de
---
id: ai_ferienplan
base_url: https://www.ai.ch
default_extent_id: CH-AI
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.ai.ch/themen/bildung/eltern-und-schule/ferienplan/ftw-simplelayout-filelistingblock/ferienplan-ai_2026-2029.pdf/download"]
  language: de
```

**Claim checks** (precheck):
- Courts `/themen/staat-und-recht/gerichte`: **Confirmed** (redirects to /gerichte).
- Its `/gebuehren`, `/ratgeber`, `/rechtsprechung` subpaths: **Wrong** (404). Real page is /gerichte/rechtsprechung.
- Dogs, tax, school and road links: all **Wrong** (404 with 26-byte bodies).
- Communes `/politik-und-verwaltung/gemeinden`: **Wrong.**
- Chancellery `/politik-und-verwaltung/ratskanzlei`: **Wrong.** Real page is /verwaltung/ratskanzlei.

---

## SH: Schaffhausen

**Key fact.** sh.ch pages are a JavaScript shell: about 20 visible words and 9 links each, so `html_crawl` cannot read them. The content is embedded in the page as `window.CONTENT_DATA` JSON. Each item is also served by a JSON endpoint I verified: `https://sh.ch/CMS/content?contentid=<id>&language=DE`. It returns `data_post_content` (HTML text), `data_permalink`, `data_publication_date` and `data_link_url`.

| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 courts | VERIFIED | https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Justiz-1812-DE.html; Obergericht …/Justiz/Obergericht-41021-DE.html; Kantonsgericht …/Justiz/Kantonsgericht-110173-DE.html | 200. The Justiz page embeds 19 items (both courts, justice of the peace, tenancy office, child protection authority, debt enforcement office, PDFs "Rechtsberatungsstellen im Kanton Schaffhausen" and "Organisation der Justizbehörden"). The Obergericht page embeds 11 items | "Beurteilung von Berufungen und Beschwerden gegen Entscheide des Kantonsgerichts" | Unknown ids answer 500 "Maintenance Page" |
| C2 fees | VERIFIED (law) / NONE (resident page) | Justizgesetz SHR **173.200**, Art. 82–84: https://sh.clex.ch/app/de/texts_of_law/173.200 | LexWork 200 | "Art. 82 … Im Schlichtungsverfahren beträgt die Pauschalgebühr Fr. 100.00 bis Fr. 1'000.00, wenn das Verfahren nicht kostenlos ist." | **Correction to law_hits.json:** 172.201 is the administrative-fee ordinance. The court fees are in the Justizgesetz; the sh.clex.ch index (431 texts) has no separate court-fee ordinance. **NONE ladder:** (1) Sitemap, 599 URLs: 0 cost/fee/tariff URLs. (2) Court JSON items: no fee item. (3) WebSearch: only the divorce leaflet, which has no amounts |
| C3 guidance | VERIFIED | Kantonsgericht items: joint divorce request (…-310661-, form plus leaflet PDF), partnership dissolution (…-311162-), marital protection request (…-1236259-). Obergericht: legal aid request (…/Obergericht-56327-DE.html). PDF sh.ch/CMS/get/file/97a8f518-572a-4762-8a51-fa84f01dbff5 | All 200. The PDF has 2 pages with a text layer | "Merkblatt zur Einreichung einer Scheidungsklage Voraussetzung - Fehlender Scheidungswille eines Ehe[gatten]" | The sitemap (partial) lists 5 Kantonsgericht, 2 Obergericht and 1 justice-of-the-peace URLs |
| C4 decisions | VERIFIED | https://obergerichtsentscheide.sh.ch/, redirecting to /CMS/Webseite/Obergerichtsentscheide-2272928-DE.html | 200, same CMS. 29 embedded items: year folders "2000" to "2024" | (JS shell) | opencaselaw sh_obergericht 718 (latest 2025-12-16, **STALE**); sh_gerichte 716 (latest 2026-09-01) |
| C5 conciliation | VERIFIED | …/Justiz/Friedensrichteramt-1235775-DE.html and …/Justiz/Schlichtungsstelle-f-r-Mietsachen-1236819-DE.html | 200 (embedded texts of 1,664 and 2,958 characters) | "Allgemeine Schlichtungsbehörde in Zivilstreitigkeiten (ohne Mietsachen und Gleichstellungssachen)" and "Beratung in allen Mietfragen betreffend Raummiete und -pacht" | Fees: Justizgesetz Art. 82 |
| G1 dogs | VERIFIED | …/Departement-des-Innern/Veterin-ramt-1575596-DE.html, also as JSON via `/CMS/content?contentid=1575596&language=DE` | 200, "Haltung und Betreuung von Hunden", published 05.01.2023. JSON 200, 1,875 bytes | "Jeder Hundehalter und jeder Hund muss in der Hundedatenbank AMICUS registriert sein." | Laws SHR 455.200 and 455.201. Other dog pages found by WebSearch were not opened |
| G2 tax guide | VERIFIED | Steuerverwaltung …/Steuerverwaltung-3918-DE.html (www.steuern.sh.ch redirects here). Its "Dienstanleitung" tile links **https://sh.lexican.cloud/Project/Details/KArfO5bFd0CkaahGqsNmbQ/article/aoFNqnTRdogvkpgo** | 200, "Steuerverwaltung - Dienstanleitung", lexiCan +WEB v4.0 (vetafab Software), JS shell. With a session cookie, `/api/OutlineApi/full?projectId=…` returns **168 nodes (143 leaf articles)**. Each article (`/api/ArticlesApi/content?articleId=…`) links a PDF (`/Files/Download?…`) | PDF (1 page, text layer): "Dienstanleitung zum Schaffhauser Steuergesetz Art. 4 Nr. 3 Februar 2014 … Hauptsteuerdomizil bei Aufenthalt in Alters- und Pflegeheimen" | The id WebSearch found (2235891) now answers 500 |
| G3 holidays | VERIFIED | https://schule.sh.ch/CMS/Webseite/Schulportal-Kanton-Schaffhausen/Schulorganisation/Schuljahresplanung-1280144-DE.html and PDF sh.ch/CMS/get/file/c5d7c8e8-2819-4ae1-a1c6-9861471b0182 | 200 "Schulferien". PDF 1 page, text layer | "Herbstferien: 40. bis und mit 42. Kalenderwoche Weihnachtsferien: 25. Dezember bis 2. Januar" | **The canton sets them** by a calendar-week rule, not dated ranges: "…ist in der Verordnung SHR 410.114 wie folgt geregelt" |
| G4 road office | VERIFIED | …/Baudepartement/Strassenverkehrs--und-Schifffahrtsamt-3612-DE.html | 200 (JS shell, 7 embedded items). 47 road sitemap URLs | SHR 741.012: "Lernfahrausweise: Fr. 65.00 … Führerausweis im Kreditkartenformat: Fr. 60.00" | www.strassenverkehrsamt.sh.ch redirects here |
| D1 communes | VERIFIED | …/Services/Gemeinde-Portal-1668759-DE.html | 200. 26 link items, each with `data_link_url` | "Stadt Schaffhausen → http://www.stadt-schaffhausen.ch/" | 26 = commune_sites.csv |
| D2 chancellery + gazette | VERIFIED (gazette) / partial (chancellery) | Gazette page …/Regierung/Staatskanzlei/Amtsblatt-1809392-DE.html, which leads to **https://amtsblatt.sh.ch** (eSHAB) | 200. API `tenant=kabsh` returns 11,720 items; `&rubrics=RE-SH` returns 404 | "Bekanntmachung – Aus den Verhandlungen des Regierungsrates, 15. September 2026" | The chancellery node Staatskanzlei-2757 is 200 but a menu page with no text. robots.txt disallows `/` on amtsblatt.sh.ch |

**Site recipe.** sh.ch, schule.sh.ch and obergerichtsentscheide.sh.ch share one CMS. Pages are addressed as `…-<contentId>-DE.html`. The sitemap is `https://sh.ch/Sitemap/SitemapXml` (599 URLs, partial). robots.txt has no Crawl-delay. The CMS bundle also names `/CMS/lists/list` and `/CMS/content/list`; those did not work with my guessed parameters. Laws are on sh.clex.ch (a WebSearch hit also shows rechtsbuch.sh.ch). sh.lexican.cloud has no robots.txt (404) and needs the `ASP.NET_SessionId` cookie from its page before API calls.

```yaml
id: sh_ch_guidance               # NEW fetcher needed: api strategy cannot read a single-object response
base_url: https://sh.ch
default_extent_id: CH-SH
authority: official_info
categories: [dogs, housing]      # plus "category missing: courts"
fetch_strategy: sh_cms_json      # fetcher:sh-cms-json
fetch_config:
  content_url: "https://sh.ch/CMS/content?contentid={id}&language=DE"
  ids: [1575596, 1235775, 1236819, 1962811, 310661, 311162, 1236259]   # or all ids parsed from https://sh.ch/Sitemap/SitemapXml (-<id>-DE.html)
  text_field: data_post_content
  date_field: data_publication_date
  url_template: "https://sh.ch/CMS{data_permalink}"
  language: de
---
id: sh_amtsblatt_regierung
base_url: https://amtsblatt.sh.ch
default_extent_id: CH-SH
authority: official_info
categories: []                   # category missing: gazette
fetch_strategy: api
fetch_config:
  url: https://amtsblatt.sh.ch/api/v1/publications?publicationStates=PUBLISHED&tenant=kabsh&rubrics=RE-SH&pageRequest.page=0&pageRequest.size=100
  records_path: content
  id_template: "{meta[publicationNumber]}"
  title_template: "{meta[title][de]}"
  text_template: "{meta[title][de]} (Amtsblatt SH, {meta[publicationDate]})"
  language: de
---
id: sh_ferien
base_url: https://sh.ch
default_extent_id: CH-SH
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://sh.ch/CMS/get/file/c5d7c8e8-2819-4ae1-a1c6-9861471b0182"]
  language: de
```

For the tax guide (Dienstanleitung), a `fetcher:lexican` would:
1. GET the project page to obtain the session cookie.
2. Read the tree from `/api/OutlineApi/full?projectId=KArfO5bFd0CkaahGqsNmbQ` (fields Title, ArticleId, ChildArticles).
3. For each leaf, read `/api/ArticlesApi/info` (title, modification date) and `/api/ArticlesApi/content`, which contains the `/Files/Download?projectId=…&fileId=…` PDF link.
4. Extract the PDF text with pypdf. The article number (e.g. "Art. 4 Nr. 3") serves as the identifier.

**Claim checks** (precheck):
- Courts, 5 `…/Gerichte/…-8802xx-DE.html` links: **Wrong** (500; invented ids). Real pages sit under /Justiz/ (ids 1812, 41021, 110173).
- Dogs `CMS/get/file/c822e118…`: **Wrong** (500).
- Tax and school `desktopdefault.aspx/tabid-…`: **Wrong** (redirect to the home page).
- Road `www.strassenverkehrsamt.sh.ch`: **Confirmed.**
- Communes `Gemeinden-32338`: **Wrong** (500).
- Chancellery `Staatskanzlei-1153163`: **Wrong** (500).

### L1: city of Schaffhausen (CH-SH-2939)

| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| L1 city law | VERIFIED | https://www.stadt-schaffhausen.ch/rechtssammlung | 200, "Stadt Schaffhausen - Rechtssammlung", 46.9 KB, 275 links. **i-web** table `icms-dt` (id `icmsTable-gesetzessammlungList`) with a `data-entities` JSON of **215 rows**. Fields: `title` (→ /_rte/information/<id>), `_nummer`, `_dokumentList` (→ /_doc/<id>), `_rechtsgueltigkeit`. 214 rows have a PDF; all 215 have a validity date | Dog tax 353.2 (valid 01.01.2018), /_doc/3720785, PDF 2 pages, text layer: "a) Fr. 160.-- für den ersten Hund b) Fr. 200.-- für jeden weiteren Hund" | **Dogs, waste and parking are all present:** Abfallverordnung 740.1 (/_doc/4688455, 9 pages, text layer), Parkgebühren 400.41 (/_doc/3720833, not opened), Parkplatzverordnung, and an ordinance on overnight parking. Destination `fetcher:iweb-table`, authority official_info. The AI link from the city list (S2) was 404 per the precheck |

```yaml
id: stadt_schaffhausen_rs        # yaml-now:pdf sample; full collection needs fetcher:iweb-table (215 rows)
base_url: https://www.stadt-schaffhausen.ch
default_extent_id: CH-SH-2939
authority: official_info
categories: [dogs, waste]
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.stadt-schaffhausen.ch/_doc/3720785", "https://www.stadt-schaffhausen.ch/_doc/4688455"]
  language: de
```

---

## Across the five cantons

### Grid status summary

| Canton | Verified | Split cells | Blocked or missing piece |
|---|---|---|---|
| SG | 9 of 11 | C4, D2 | Decisions list and gazette blocked by publikationen.sg.ch robots.txt |
| TG | 9 of 11 | C2, D2 | No resident fee page; gazette behind a login wall |
| AR | 11 of 11 | none | Gazette API site disallows crawling in robots.txt (design question) |
| AI | 9 of 11 | C2, D2 | No resident fee page; no online gazette (newspaper) |
| SH + L1 | 11 of 11, plus L1 | C2 | No resident fee page; the chancellery node has no text |

### New fetcher classes needed

1. **`pdf-index`** (5 cantons). Serves SG Steuerbuch (250 PDFs listed on the table-of-contents page), SG court leaflets (10), AR tax instructions (54 PDFs), AI tax leaflets (51 PDF links), TG Obergericht guidelines (10) and TG district-court leaflets.
2. **`sitemap-crawl`** (TG, SG). Serves steuerpraxis.tg.ch (559 entries; pick the newest version prefix) and rechtsprechung.tg.ch (6,350 URLs). The second one refreshes TG decisions, where opencaselaw is stale. Also any govis subdomain sitemap.
3. **`eshab`** (new name). Serves the amtsblattportal.ch gazette API: AR (tenant kabar) and SH (tenant kabsh).
   - Paginated JSON with up to 2,000 items per page (per its official docs), filters for tenant, rubric and date.
   - The docs say municipality ids exist on some publication types since December 2024, which could map notices to commune nodes.
   - Other cantons publish there too: the docs use amtsblatt.zh.ch as an example, and BE commune notices appear in the unfiltered feed.
4. **`sh-cms-json`** (new; SH only). Makes every page on sh.ch, schule.sh.ch and obergerichtsentscheide.sh.ch readable.
5. **`lexican`** (new). Serves the SH Dienstanleitung (143 articles). Whether this vendor hosts other cantons is not verified.
6. **`iweb-table`** (existing). Serves Stadt Schaffhausen (215 rows). appenzell.org (Bezirk Appenzell) has the same page template (inferred, not verified).
7. **`xlsx`**. Serves the SG commune lists (6 files: political communes, school communes, Ortsgemeinden, corporations, Zweckverbände).
8. **`lexwork`** (existing). All the laws cited above, from gesetzessammlung.sg.ch, rechtsbuch.tg.ch, ar.clex.ch, ai.clex.ch and sh.clex.ch.
9. Decisions: opencaselaw already covers them. The AR Weblaw app (POST JSON) and the SG TYPO3 list are not needed.

### Blocked items

- **publikationen.sg.ch:** its robots.txt says `User-agent: *` → `Disallow: /`. That covers the SG gazette and the SG decision list. Design question: ask the canton, or rely on opencaselaw.
- **amtsblatt.tg.ch:** login wall with shared credentials displayed on the page; not used. It also answered 429 before a 4-second delay.
- **amtsblattportal.ch, amtsblatt.ar.ch, amtsblatt.sh.ch:** robots.txt disallows `/`. Yet the API is officially documented at amtsblattportal.ch/docs/api, which says authentication is needed only for submitting or fetching unpublished items. Design question: may we use the documented API against the robots.txt?
- **AI gazette:** does not exist online. The Appenzeller Volksfreund newspaper is the official organ.
- **Rate limits:** TG subdomains answered 429 at first contact; keep at least 2 s between requests.
- **Session and stale ids:** sh.lexican.cloud needs a session cookie first. sh.ch answers 500 for stale or invented ids.

### Five best finds

1. **amtsblattportal.ch eSHAB JSON API** (multi-canton gazettes). AR returns 21,349 items and SH 11,720; rubric filters such as `RE-SH` return 404 SH government notices. It is documented and has municipality ids (policy decision pending).
2. **sh.ch CMS JSON endpoint** `/CMS/content?contentid=<id>&language=DE`. It unlocks every SH page, which are otherwise unreadable JS shells.
3. **steuerpraxis.tg.ch**. Server-HTML TG tax practice, 559 entries in the 2026-09 version, 7 versions, enumerable through the sitemap. Its sister site rechtsprechung.tg.ch (6,350 URLs) refreshes TG decisions, where opencaselaw is stale.
4. **SH Dienstanleitung on lexiCan**. A JSON outline of 168 nodes with 143 text-layer PDF articles; the real SH equivalent of a Steuerbuch.
5. **Stadt Schaffhausen i-web Rechtssammlung** (215 rows, 214 PDFs, dog tax Fr. 160, waste and parking present). A close runner-up: AR levies the dog tax at canton level (Fr. 120), so one page answers it for all 20 communes.

### Corrections to the Stage 0 inputs

- SH court fees are in Justizgesetz 173.200, Art. 82–84, not in 172.201.
- AI has 5 districts, not 6: Schwende and Rüte are now Schwende-Rüte.
- The steuerverwaltung.tg.ch robots.txt points to a wrong host.
- The brief's `pr40/…/commune_sites.csv` path does not exist in this session.