I've checked all six cantons and the three cities live, and every grid cell is filled with a verified, blocked or "no such page" answer. The main surprises: the Basel-Landschaft (BL) site behind Cloudflare is fully readable through an open Plone REST API; five cantons' gazettes run on one platform with an open export API that robots.txt forbids; and law_hits.json missed or got wrong the court-fee ordinances for Aargau (AG) and Solothurn (SO).

Every claim below comes from a curl/python request I made today, except cells marked **[cited g5]** / **[cited g2]** (earlier verified reports, cited as the brief asked) and a few marked **[prior-run log]**. Inference is labelled "inferred" or "not verified". Scratch evidence and scripts are in `<scratchpad>/run3-a/` (`pages/` holds every fetched body). I picked up exactly where the prior run stalled, at the SO eSHAB API probe.

**Status legend:** VERIFIED = URL + HTTP status + title + format + quoted sample. NONE = no such page, with the search log. BLOCKED = found but not fetchable or not allowed.

## Headline findings

1. **BL is reachable despite Cloudflare.** www.baselland.ch and kanton.baselland.ch return 403 "Just a moment..." even with a full Chrome 128 User-Agent. But the same site content is served as open JSON at `https://bl-api.webcloud7.ch/<same path>`. Content sits in `slblocks[*].text.data` (HTML), `@search` works, and files download via `<file>/@@download/file`. Every BL cell was filled this way.
2. **Gazettes (D2): one platform, open API, robots ban.** The eSHAB / amtsblattportal platform (SECO) hosts the SO, ZH, BE, BS and BL gazettes.
   - The public bulk export works without login: `https://amtsblattportal.ch/api/v1/publications/xml|csv?publicationStates=PUBLISHED&tenant=<t>&rubrics=<code>&publicationDate.start=…&pageRequest.page=N&pageRequest.size=M`. Each notice's full text is at `/api/v1/publications/<id>/xml`.
   - robots.txt is `User-agent: * / Disallow: /` on amtsblattportal.ch, amtsblatt.so.ch, amtsblatt.zh.ch, amtsblatt.be.ch, www.kantonsblatt.ch and www.amtsblatt.bl.ch. So these are **not clear to ingest**.
   - AG runs its own gazette, amtsblatt.ag.ch, whose robots.txt disallows `/publikationen/` and `/ekab/`.
3. **Own-gazette counts vs the `cantons=` filter.** Own notices = published, `tenant=kab<xx>` plus the canton's own rubric codes, taken from `/api/v1/rubrics` by `tenantId`. Repeated `rubrics=` parameters act as OR: the combined total equals the sum of single-rubric totals in all five tenants.

   | Canton | Own rubrics | Own notices | `cantons=XX` (includes federal SHAB) |
   |---|---|---|---|
   | SO | 7 | 1,580 | 68,445 |
   | ZH | 12 | 19,659 | 524,636 |
   | BE | 12 | 20,165 | 243,402 |
   | BS | 18 | 9,462 | 93,656 |
   | BL | 11 | 5,619 | 76,292 |
   | AG | 0 | none on eSHAB | 161,591 |

   Whether expired notices stay in the PUBLISHED state is not verified.
4. **law_hits.json is wrong on court fees in two cantons.**
   - AG has no court_fees hit. The ordinance is **SAR 662.110 Gebührendekret**, section "2. Gerichtsgebühren", §§ 5–20. The old Verfahrenskostendekret 221.150 is `abrogated: true`.
   - SO's court_fees hit (125.751.3, a Hague convention) is wrong. The ordinance is **BGS 615.11 Gebührentarif (GT)**.
   - Also missing: the SO income tax law **BGS 614.11** and the BS tax law **SG 640.100**. law_hits only has SO's motor-vehicle tax law 614.61 and no BS tax topic at all.
5. **Official commune directories exist as XLSX or JSON with BFS numbers and websites:** AG (196), BE (334), BL (86, data.bl.ch API). ZH's XLSX (160) has e-mail but no website column. These are good resolver data.
6. **City law (L1): all three cities have their full collections enumerable.**
   - Zürich: 791 entries, 622 in force; each detail page embeds JSON metadata plus a text-layer PDF.
   - Bern: 218 texts in the sitemap, each exportable as `lex-<nr>.pdf` or `.docx`.
   - Thun: i-web table with 127 rows and 127 PDFs.
   - Dog, waste and parking rules are present in Zürich and Bern. Thun has waste and parking; none of its 127 rows mentions dogs ("Hund").

---

## ZH (Zürich)

### Grid

| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | Supreme and district courts: https://www.gerichte-zh.ch/de [cited g2]. Administrative court (VGR): https://www.zh.ch/de/gerichte-notariate/verwaltungsgericht.html | gerichte-zh.ch 200 "Zürcher Zivilgerichte und Strafgerichte" (pre-check). VGR page 200 "Verwaltungsgericht \| Kanton Zürich", server HTML, 767 words. `http://www.vgrzh.ch/` redirects to that page; `https://www.vgrzh.ch` gives no connection (curl 000) | "Hier finden Sie die Entscheiddatenbank des Gerichts, in der ein Grossteil der Urteile veröffentlicht wird." | The VGR has no separate site; it lives inside zh.ch |
| C2 | VERIFIED | Page: https://www.gerichte-zh.ch/de/themen/zivilprozess/prozesskosten. Ordinance LS 211.11 GebV OG, law page `…/zhlex-ls/erlass-211_11-2010_09_08-2011_01_01-087.html`, PDF `https://www.notes.zh.ch/appl/zhlex_r.nsf/WebView/7142D0282EDFCA9CC1257DC4003F6288/$File/211.11_8.9.10_87.pdf`. VGR fees: LS 175.252 | Page 200 "Prozesskosten und unentgeltliche Rechtspflege"; amounts only via JS fee calculators. Law page 200 "Gebührenverordnung des Obergerichts (GebV OG)". PDF 200, 6 pages, text layer | § 4: "bis 1 000 25% des Streitwertes, mind. Fr. 150"; conciliation: "Bei nicht vermögensrechtlichen Streitigkeiten beträgt die Gebühr Fr. 100 bis Fr. 850." | The notes.zh.ch `OpenAttachment` link returns a 153-B JS redirect; use the `WebView/$File` URL. law_hits also lists 212.812 and 215.12 |
| C3 | VERIFIED [cited g2; count re-checked] | https://www.gerichte-zh.ch/de/themen and /miete, /arbeit, /erbschaft, /ehe-und-familie, /betreibung-und-konkurs, /zivilprozess, /zivilprozess/prozesskosten, /zivilprozess/schlichtungsverfahren, /miete/hilfen/schlichtungsbehoerden, /zivilprozess/mediation. VGR: `…/streitigkeiten-vor-verwaltungsgericht/informationen-zum-gerichtsverfahren.html` | Sitemap 454 URLs, **248 under /de/themen/** (g2: 249). Server HTML (Drupal), pages about 120 KB with a large navigation menu. VGR info page 200, 2,238 words | "…fällt im Prozess eine Gerichtsgebühr an, welche den Parteien nach dem Ausgang des Verfahrens auferlegt wird." | 248 pages exceed the crawler's 200-page cap (`config.py:22`) |
| C4 | VERIFIED | https://www.gerichte-zh.ch/entscheide/entscheide-anzeigen.html. VGR: zh.ch "Rechtsprechung des Verwaltungsgerichts" → `https://vgrzh.djiktzh.ch/findinfo/xhtmltemplates/standard.htm` (FindInfo/Omnis CGI) | entscheide page 200, 1,615 words. FindInfo frameset 200 (638 B). Deep link `…/cgi-bin/nph-omniscgi.exe?…Schema=ZH_VG_WEB&Aufruf=getMarkupDocument…` 200, 56,660 B, 4,604 words. No feed or API seen | "Geschäftsnummer: VB.2023.00118 Entscheidart und -datum: Endentscheid vom 09.11.2023" | opencaselaw ZH: 23 codes, 87,134 decisions. VGR 12,637 (latest 2026-08-28); Obergericht 28,301 (2026-07-29); social insurance court 34,715 (2026-06-17); Mietgericht 186 (2026-09-03). **STALE:** zh_gerichte 1,438 (2025-11-05), zh_kassationsgericht 1,454 (2012-06-25), sav_kantone (no dates) |
| C5 | VERIFIED | https://www.gerichte-zh.ch/de/themen/zivilprozess/schlichtungsverfahren; https://www.gerichte-zh.ch/de/themen/miete/hilfen/schlichtungsbehoerden | Both 200, server HTML | "…die Friedensrichterinnen und Friedensrichter der einzelnen Gemeinden als Schlichtungsbehörde im Sinne von Art. 197 ZPO tätig." / "…jedem Bezirksgericht eine besondere Schlichtungsbehörde angegliedert" | Fees in GebV OG (Fr. 100–850). Downloads: Friedensrichterhandbuch PDF, legal-aid form for conciliation. Laws 212.126, 212.127, 177.12 |
| G1 dogs | VERIFIED [cited g5] | https://www.zh.ch/de/umwelt-tiere/tiere/haustiere-heimtiere/hunde.html (+15 subpages) | 200 today "Hunde \| Kanton Zürich", server HTML, 2,725 words | "Seit 1. Juni 2025 ist neue Hundegesetzgebung in Kraft …" (g5) | Law LS 554.5 / 554.51. Nothing missing found |
| G2 tax | VERIFIED [cited g5] | Steuerbuch via https://www.zh.ch/de/steuern-finanzen.zhweb-sitemap.xml | 200 today. g5: 1,043 locs, 159 Steuerbuch HTML entries plus about 148 current PDFs; enumerable | "ZStB-Nummer 30.1 … Gültig ab 27. September 2023" (g5) | — |
| G3 holidays | VERIFIED [cited g5] | https://www.zh.ch/de/bildung/bildungssystem/schulferien.html → XLSX per school community | 200 today "Schulferien \| Kanton Zürich", 1,931 words. XLSX has 185 school communities (g5) | Autumn holidays 6–17 Oct 2025, Zürich-Uto (g5) | **Who sets them:** school communities; only school start and Christmas are binding (g5) |
| G4 road | VERIFIED [cited g5] | https://www.zh.ch/de/sicherheitsdirektion/strassenverkehrsamt.html + /de/mobilitaet/… | 200 today "Strassenverkehrsamt \| Kanton Zürich", 870 words. Fee order PDF, 16 pages, text layer (g5) | "Lernfahrausweis 40.00" (g5) | Parking is municipal |
| D1 | VERIFIED | https://www.zh.ch/de/politik-staat/gemeinden.html → `…/gemeinden/politische_gemeinden.xlsx` (+ gemeindeverzeichnis.pdf, gemeindepraesidenten.xlsx, gemeindeschreiber.xlsx) | Page 200, 1,379 words. XLSX 200, 84,863 B; sheet "Tabelle2" has a header plus **160 rows** (Organisation, Zusatz, Strasse, Postfach, PLZ, Ort, E-Mail). No website column, no BFS number | "Die 160 politischen Gemeinden und 60 Schulgemeinden …"; row "Gemeinde Aesch \| Dorfstrasse 3 \| 8904 \| gemeindeverwaltung@aesch-zh.ch" | Resolver data. Websites could only be derived from e-mail domains (inferred) |
| D2 | VERIFIED; gazette BLOCKED by robots | https://www.zh.ch/de/staatskanzlei.html; gazette https://amtsblatt.zh.ch/ (eSHAB, tenant kabzh) | Chancellery page 200 "Staatskanzlei \| Kanton Zürich". Gazette host 200 "eSHAB", 1,384-B JS shell. robots.txt `User-agent: * / Disallow: /` | "Die Staatskanzlei berät und unterstützt den Regierungsrat und das Präsidium …" | 12 own rubrics (AI-, BP-, BV-, FZ-, GB-, KA-, KO-, RP-, RS-, SW-, TE-, VE-ZH). Own notices 19,659; cantons=ZH 524,636 |

### Site recipe (ZH)
- **www.zh.ch:** AEM. robots.txt is 56 B with no Disallow and no Crawl-delay, and names the sitemap index `/bin/zhweb/publish/sitemap.xml` (44 child sitemaps, 80,504 URLs at stage 0). Bare section paths redirect to a 403; use the `.html` form (per the repo's `zh_ch.yaml`).
- **www.gerichte-zh.ch:** Drupal (robots disallows /core/ and /profiles/). `/sitemap.xml` has 454 URLs. No crawl-delay.
- **vgrzh.djiktzh.ch:** FindInfo Omnis CGI, iso-8859-1.
- **amtsblatt.zh.ch:** eSHAB; robots disallows everything.

### Draft YAMLs (ZH)
```yaml
# yaml-now:html_crawl — 248 theme pages > crawl_max_pages 200 (config.py:22): split by theme or raise the cap
id: gerichte_zh_themen
name: Gerichte Kanton Zürich – Rechtliche Themen
base_url: https://www.gerichte-zh.ch
default_extent_id: CH-ZH
authority: official_info
categories: []            # category missing: courts (Miete pages would also fit housing)
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/themen"]
  path_allowlist: ["/de/themen"]
  language: de
allow_narrowing: false
license: "gerichte-zh.ch terms of use"   # placeholder, not checked
---
# yaml-now:html_crawl
id: zh_verwaltungsgericht
name: Verwaltungsgericht des Kantons Zürich – Verfahren
base_url: https://www.zh.ch
default_extent_id: CH-ZH
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/politik-staat/streitigkeiten-vor-verwaltungsgericht.html", "/de/gerichte-notariate/verwaltungsgericht.html"]
  path_allowlist: ["/de/politik-staat/streitigkeiten-vor-verwaltungsgericht", "/de/gerichte-notariate/verwaltungsgericht"]
  language: de
allow_narrowing: false
license: "zh.ch terms of use"
```
- D1 → `resolver` (needs a `fetcher:xlsx`).
- D2 → `blocked:robots` plus a design question: gazettes contain personal data (e.g. ZH death notices).
- G1–G4 → use the g5 fetch hints.

### Claim checks (ZH)
- **Supreme court (Obergericht):**
  - Homepage gerichte-zh.ch/ → Confirmed (redirects to /de).
  - Fees `/themen/prozesskosten.html` → Wrong (404). Correct: /de/themen/zivilprozess/prozesskosten.
  - Guidance `/themen.html` → Confirmed (redirects to /de/themen).
  - Decisions `/entscheide.html` → Confirmed (redirects to /entscheide/entscheide-anzeigen.html).
- **Administrative court (VGR):**
  - Homepage `zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html` → Wrong (404). Correct: zh.ch/de/gerichte-notariate/verwaltungsgericht.html.
  - Fees `…/informationen-zum-gerichtsverfahren.html` → Partly: 200, procedure information but no CHF amounts; the ordinance is LS 175.252.
  - Guidance `…/streitigkeiten-vor-verwaltungsgericht.html` → Confirmed.
  - Decisions `vgrzh.djiktzh.ch/` → Partly: right host, but the root returns 4 bytes. The real entry is /findinfo/xhtmltemplates/standard.htm (deep links 200).
- **District courts:** /organisation/bezirksgerichte.html → Confirmed (redirects).
- **Communes and chancellery (S4):** both Confirmed.

---

## BE (Bern)

### Grid

| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | Civil and criminal courts: https://www.zsg.justice.be.ch/de/start.html. **Real administrative court host:** https://www.vgb.justice.be.ch/de/start.html (found via WebSearch). Justice portal: https://www.justice.be.ch/de/start.html | zsg 200 "Startseite", server HTML (AEM). vgb 200 "Startseite". justice.be.ch 200 | vgb: "Das Verwaltungsgericht Oberstes kantonales Gericht in Verwaltungssachen"; zsg: "Obergericht Oberste rechtsprechende Behörde Regionalgerichte Erstinstanzliche Zivil- und Strafgerichte Schlichtungsbehörden" | The AI's www.vg.justice.be.ch does not exist (pre-check) |
| C2 | VERIFIED | https://www.zsg.justice.be.ch/de/start/themen/zivilrecht/kosten/verfahrenskosten.html; https://www.vgb.justice.be.ch/de/start/themen/kosten.html; decree BSG 161.12 (VKD, per law_hits) | zsg page 200 "Verfahrenskosten im Zivilverfahren", 499 words. vgb 200 "Kosten" | "Im Schlichtungsverfahren fallen zudem bei Streitigkeiten aus Miete und Pacht von Wohn- und Geschäftsräumen keine Gerichtsgebühren an."; "…bis zu einem Streitwert von CHF 30ꞌ000.00…" | The page also cites the party-costs ordinance PKV, BSG 168.811 |
| C3 | VERIFIED | zsg: …/themen/zivilrecht/familienrecht.html, /mietrecht.html, /arbeitsrecht.html, /betreibung-konkurs.html, /zivilrecht/kosten.html, /kosten/unentgeltliche-rechtspflege.html, /strafrecht/kosten.html. vgb: …/themen/einen-entscheid-anfechten.html, /ablauf-des-verfahrens.html, /kosten/stundung-und-erlass.html | zsg sitemap: 55 German theme pages plus themen.html. vgb `/de/sitemap.xml` 200: 43 URLs, 14 of them theme pages. Server HTML | see C2 | — |
| C4 | VERIFIED | zsg `/de/start/dienstleistungen/rechtsprechung.html` → https://www.zsg-entscheide.apps.be.ch/tribunapublikation/ (+ aa-entscheide.apps.be.ch). vgb `/de/start/dienstleistungen/rechtsprechung.html` → https://www.vg-urteile.apps.be.ch/tribunapublikation/ (+ strk-entscheide.apps.be.ch) | Both route pages 200. Both Tribuna apps answer 200 with about 19 KB and 30–35 words: JS apps | "Die elektronische Entscheidsammlung der Zivil- und Strafgerichte enthält Entscheide … von grundlegender Bedeutung" | opencaselaw BE: 8 codes, 21,722 decisions. be_verwaltungsgericht 12,109 (2026-08-24); be_zivilstraf 6,039 (2026-08-03); be_direktionen (2026-07-02); be_anwaltsaufsicht (2026-08-11). **STALE:** be_bvd (2025-12-11), be_weitere (2025-12-18), be_steuerrekurs (2025-12-16), sav_kantone |
| C5 | VERIFIED | https://www.zsg.justice.be.ch/de/start/ueber-uns/schlichtungsbehoerden.html (+ berner-jura-seeland, emmental-oberaargau, bern-mittelland, oberland) | 200 "Schlichtungsbehörden" | "Im Kanton Bern gibt es vier Schlichtungsbehörden. Sie sind zuständig für Schlichtungsverfahren und Rechtsberatungen." | Tenancy conciliation costs no court fee (C2 page). Laws 164.211–164.214 |
| G1 dogs | VERIFIED [cited g5] | https://www.weu.be.ch/de/start/themen/veterinaerwesen/hunde-im-kanton-bern.html (+6) | 200 today "Hunde im Kanton Bern" | "Möchten Sie einen Hund kaufen? Die Anforderungen an Sie als Hundehalterin oder Hundehalter sind hoch." (g5) | Laws 916.31 and 916.812. Dog tax is municipal (not verified) |
| G2 tax | VERIFIED [cited g5] | https://www.taxinfo.sv.fin.be.ch/ → `/taxinfo/ca95ca72-…` | 200 today "Startseite - TaxInfo - Kanton Bern". At least 591 pages; each embeds JSON (`vike_pageContext`) (g5) | "Fahrkosten für den Arbeitsweg" (g5) | g5 flagged "für den internen Gebrauch" wording |
| G3 holidays | VERIFIED (not in g5) | https://www.akvb-gemeinden.bkd.be.ch/de/start/organisation-finanzierung/schulorganisation/schulferienplanung.html → PDF `…/schulferienplanung/schulferien-kanton-bern-d.pdf` | Page 200 "Schulferienplanung". PDF 200, 2 pages, text layer, "1. Juni 2026 … 2026/27 bis 2031/32" | "2026/27 Herbstferien Sa, 19.09.2026 - So, 11.10.2026" | **Who sets them:** the canton's education directorate (BKD), per Art. 8 para. 3 VSG. Exception: the February sports week is freely chosen (weeks 2–14). The French-speaking part follows the BEJUNE calendar. The bkd.be.ch sitemap has no holiday page |
| G4 road | VERIFIED [cited g5] | https://www.svsa.sid.be.ch/de/start.html | 200 today "Strassenverkehr & Schifffahrt"; 229 German sitemap URLs (g5) | fee pages …/gebuehren.html (g5) | No parking content (municipal) |
| D1 | VERIFIED | https://www.be.ch/de/start/ueber-uns/gemeinden.html → https://www.gemeinden.dij.be.ch/de/start/daten/gemeindedaten.html → `…/adressliste einwohner- und gemischte gemeinden-de.xlsx` | Pages 200. XLSX 200, 60,843 B, sheet "Adressliste Gemeinden", 336 rows = **334 communes**, columns BFS, Gemeinde, …, Homepage, Sprache, Verwaltungskreis; 333 have a homepage | "Der Kanton Bern hat 334 politische Gemeinden (Stand 1.1.2026)."; row "301 \| Gemeindeverwaltung Aarberg \| … \| www.aarberg.ch \| Deutsch \| Seeland" | Resolver data with BFS and websites |
| D2 | VERIFIED; gazette BLOCKED by robots | https://www.sta.be.ch/de/start.html; https://www.sta.be.ch/de/start/dienstleistungen/amtsblatt.html → https://amtsblatt.be.ch/ (eSHAB, tenant kabbe) | Chancellery 200 "Staatskanzlei des Kantons Bern - Startseite". Gazette page 200 "Amtsblatt des Kantons Bern". amtsblatt.be.ch 200 "eSHAB". robots.txt `Disallow: /` | "Das Amtsblatt ist das allgemeine kantonale Publikationsorgan … erscheint seit dem 1. Januar 2020 nur noch in elektronischer Form." | 12 own rubrics (BP-BE Baugesuche 8,430 … VE-BE 5,792). Own notices 20,165; cantons=BE 243,402 |

### Site recipe (BE)
- Each office has its own AEM host with `/sitemap.xml` → `/de/sitemap.xml` + `/fr/sitemap.xml`. Stage-0 counts (total / German): zsg 256/127, rsta 130/66, svsa 462/229, sv.fin 344/172, weu 955/489, bkd 1,133/697, sta 545/273, akvb-gemeinden 167/65, be.ch 153/39. vgb: 43 German URLs (fetched live).
- Crawl-delay 10 on BE hosts (stage 0 and brief). The repo crawler uses a global 0.5 s delay (`config.py:23`) and does not honour per-host Crawl-delay; only `robots.can_fetch` is checked (`html_crawl.py:86-94`).
- Decisions run on Tribuna JS apps at `*.apps.be.ch`. The gazette is eSHAB.

### Draft YAMLs (BE)
```yaml
# yaml-now:html_crawl (Crawl-delay 10 not honoured by the crawler; needs a per-source delay)
id: be_zsg_themen
name: Zivil- und Strafgerichtsbarkeit Kanton Bern – Themen und Schlichtungsbehörden
base_url: https://www.zsg.justice.be.ch
default_extent_id: CH-BE
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/start/themen.html", "/de/start/ueber-uns/schlichtungsbehoerden.html"]
  path_allowlist: ["/de/start/themen", "/de/start/ueber-uns/schlichtungsbehoerden"]
  language: de
allow_narrowing: false
---
id: be_vgb_themen
name: Verwaltungsgericht des Kantons Bern – Verfahren und Kosten
base_url: https://www.vgb.justice.be.ch
default_extent_id: CH-BE
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/start/themen.html"]
  path_allowlist: ["/de/start/themen"]
  language: de
allow_narrowing: false
---
# yaml-now:pdf
id: be_schulferien_volksschule
name: Kantonale Ferienordnung Volksschule Bern (deutschsprachiger Teil) 2026/27–2031/32
base_url: https://www.akvb-gemeinden.bkd.be.ch
default_extent_id: CH-BE
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.akvb-gemeinden.bkd.be.ch/content/dam/akvb-gemeinden_bkd/dokumente/de/startseite/organisation-finanzierung/schulorganisation/schulferienplanung/schulferien-kanton-bern-d.pdf"]
  language: de
allow_narrowing: false
```
- D1 → `resolver` (XLSX with BFS, needs `fetcher:xlsx`).
- D2 → `blocked:robots`.

### Claim checks (BE)
- **Supreme court:** homepage Confirmed. Fees `…/kosten-und-entschaedigungen/gerichtsgebuehren.html` → Wrong (404); correct …/themen/zivilrecht/kosten/verfahrenskosten.html. Guidance themen.html → Confirmed. Decisions `/entscheide.html` → Wrong (404); correct /de/start/dienstleistungen/rechtsprechung.html → zsg-entscheide.apps.be.ch.
- **Administrative court:** all four links on www.vg.justice.be.ch → Wrong (no response). Correct host www.vgb.justice.be.ch: /de/start.html, /de/start/themen/kosten.html, /de/start/themen.html, /de/start/dienstleistungen/rechtsprechung.html.
- **Regional courts:** homepage Confirmed. Fees `…/kosten-und-entschaedigungen.html` → Wrong (404); correct /themen/zivilrecht/kosten.html.
- **Communes (S4):** www.jgk.be.ch → Wrong (no response); correct be.ch/de/start/ueber-uns/gemeinden.html and gemeinden.dij.be.ch. **Chancellery:** Confirmed.

---

## BS (Basel-Stadt)

### Grid

| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.bs.ch/willkommen-bei-den-gerichten; section root `/gerichte-judikative/` (11 court sub-sections) | 200 "Willkommen bei den Gerichten \| Kanton Basel-Stadt", server HTML, 340 words | "Die Bundesverfassung gibt jeder Person das Recht, Streitigkeiten … vor eine unabhängige Justizbehörde zu bringen." | — |
| C2 | VERIFIED | https://www.bs.ch/gerichte-judikative/zivilgericht/gerichtsverfahren/prozesskosten (+ appellationsgericht/verfahren/kosten, strafgericht/…/busse-geldstrafe-und-gerichtskosten, jugendgericht/verfahren/kosten); law SG 154.800 and 154.810 | 200 "Prozesskosten \| Kanton Basel-Stadt", 959 words | "Bei nichtvermögensrechtlichen Streitigkeiten beträgt die Grundgebühr CHF 200.- bis 250'000.-." | — |
| C3 | VERIFIED | …/zivilgericht/ausgewaehlte-rechtsgebiete/familienrecht/getrenntleben-und-scheidung, …/arbeitsrecht, …/schkg-verfahren/konkurs, /erbschaftsamt/erbgang, /erbschaftsamt/testament, /betreibungs-und-konkursamt/betreibungen, /zivilgericht/schlichtung, /appellationsgericht/verfahren/kosten, /gericht-fuer-fuersorgerische-unterbringungen/verfahren | Sitemap: **136** `/gerichte-judikative/` URLs, 23 on resident topics. Server HTML (Nuxt SSR) | see C2/C5 | — |
| C4 | VERIFIED | https://www.bs.ch/gerichte-judikative/ueber-die-gerichte/gerichtsentscheide → `https://rechtsprechung.gerichte.bs.ch/cgi-bin/nph-omniscgi.exe?…Schema=BS_FI_WEB…` | Route page 200. FindInfo search 200 "Kanton Basel - FindInfoWeb", 14,337 B | "Die Entscheide des Appellationsgerichts … ab Januar 2014; Die Entscheide des Sozialversicherungsgerichts ab Januar 2018" | opencaselaw BS: 6 codes, 11,072 decisions. Court of appeal 8,786 (2026-09-03); social insurance 2,230 (2026-06-18); civil court 3 (sparse). **STALE:** tax appeals commission (2024-03-21), staff appeals commission (2014), bs_gerichte (2017) |
| C5 | VERIFIED | https://www.bs.ch/regierungsrat/staatskanzlei/staatliche-schlichtungsstelle-fuer-mietstreitigkeiten/schlichtungsverfahren; https://www.bs.ch/gerichte-judikative/zivilgericht/schlichtung | Both 200 (698 / 882 words) | "Das Verfahren vor der Schlichtungsbehörde ist rasch, einfach und grundsätzlich kostenlos." / "…betragen zwischen CHF 100.- und maximal 30% der Gebühr für ein Gerichtsverfahren." | Laws 215.400 and 154.130 |
| G1 dogs | VERIFIED [cited g5] | https://www.bs.ch/gd/veterinaeramt/hundehaltende (+ themen/…/hunde) | 200 today "Hundehaltende \| bs.ch", 1,147 words | "Hunde müssen so gehalten und ausgeführt werden, dass durch sie keine Menschen oder Tiere belästigt oder gefährdet werden." (g5) | law_hits shows the dog tax is set by commune decisions: RiE 365.100 (Riehen), BeE 365.100 (Bettingen) |
| G2 tax | VERIFIED [cited g5] | https://www.bs.ch/themen/arbeit-und-steuern/steuererklaerung/steuererklaerung-natuerliche-person/wegleitungen-und-formulare-fuer-natuerliche-personen | 200 today, 775 words; 38 PDFs (g5) | Merkblatt "Besondere Berufskosten … Expatriates" (g5) | No Steuerbuch: sitemap grep for "steuerbuch" gives 0. Tax law SG 640.100 (missing from law_hits) |
| G3 holidays | VERIFIED [cited g5] | https://www.bs.ch/themen/bildung-und-kinderbetreuung/schulferien → data.bs.ch 100397 | Page 200 today; ODS API 200 JSON | `{"year":"2032","name":"Sommerferien","start_date":"2032-06-26",…}` (g5) | **Who sets them:** one canton-wide dataset, so inferred to be the canton; Riehen/Bettingen not verified |
| G4 road | VERIFIED [cited g5] | motor vehicle office `…/motorfahrzeugkontrolle/gebuehrenuebersicht-mfk`; residents' parking cards under /themen/mobilitaet/… | server HTML (g5) | "Führerausweis im Kreditkartenformat, Duplikat/Erneuerung … Fr. 40.-" (g5) | — |
| D1 | VERIFIED | https://www.bs.ch/schwerpunkte/portrait/im-herzen-europas/basel-ein-kanton-drei-gemeinden | 200, 692 words; links riehen.ch and bs.ch/bettingen | "Der Kanton Basel-Stadt besteht aus der Stadt Basel selbst, sowie den beiden Landgemeinden Riehen und Bettingen." | 3 communes (BFS 2701, 2703, 2702 per csv) |
| D2 | VERIFIED; gazette BLOCKED by robots | https://www.bs.ch/regierungsrat/staatskanzlei; https://www.bs.ch/regierungsrat/staatskanzlei/e-kantonsblatt-basel-stadt → https://www.kantonsblatt.ch/ (eSHAB, tenant kabbs) | Chancellery 200 (685 words). Gazette page 200. kantonsblatt.ch 200 "eSHAB" (build 1.18.14-8272). robots.txt `Disallow: /` | "Seit Januar 2019 erscheint das Kantonsblatt Basel-Stadt als digitale Publikation." | 18 own rubrics. Own notices 9,462 (RS-BS 3,482, OB-BS 2,901 …); cantons=BS 93,656 |

### Site recipe (BS)
- www.bs.ch is Nuxt SSR over Drupal (g5). `/sitemap.xml` has 14 pages and 27,210 URLs. Crawl-delay 10, not honoured by the crawler. PDFs are on media.bs.ch.
- Decisions: FindInfo (Omnis). Gazette: eSHAB.

### Draft YAML (BS)
```yaml
# yaml-now:html_crawl (136 court URLs < 200 cap; Crawl-delay 10 not honoured).
# Whether the landing links reach all of /gerichte-judikative/ is not tested; seeding from the sitemap is safer.
id: bs_gerichte
name: Gerichte Basel-Stadt – Verfahren, Kosten, Schlichtung
base_url: https://www.bs.ch
default_extent_id: CH-BS
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/willkommen-bei-den-gerichten", "/regierungsrat/staatskanzlei/staatliche-schlichtungsstelle-fuer-mietstreitigkeiten/schlichtungsverfahren"]
  path_allowlist: ["/willkommen-bei-den-gerichten", "/gerichte-judikative/", "/regierungsrat/staatskanzlei/staatliche-schlichtungsstelle-fuer-mietstreitigkeiten"]
  language: de
allow_narrowing: false
```
G3 holidays → `yaml-now:api` as given in g5 (data.bs.ch 100397).

### Claim checks (BS)
- **Courts (S1):** www.gerichte.bs.ch/ → Partly (redirects to the courts welcome page). /kosten.html, /recht-hilfen.html and /rechtsprechung.html → Partly: all three redirect to the same welcome page, not the claimed content. Correct: …/prozesskosten, …/appellationsgericht/verfahren/kosten, …/ueber-die-gerichte/gerichtsentscheide.
- **Communes (S4):** bs.ch/portrait/gemeinden → Wrong (404); correct /schwerpunkte/portrait/im-herzen-europas/basel-ein-kanton-drei-gemeinden.
- **Chancellery:** www.staatskanzlei.bs.ch → Confirmed (redirects).

---

## BL (Basel-Landschaft). Public host blocked; content read through the open Plone API

The bot wall was tested once as the brief asked: `https://www.baselland.ch/politik-und-behorden/gerichte` with a full Chrome 128 User-Agent returned 403 "Just a moment...". kanton.baselland.ch also returned 403. Every BL cell below was filled via `https://bl-api.webcloud7.ch` (JSON, 200). Its paths equal the www.baselland.ch paths shown in WebSearch results (e.g. `/politik-und-behorden/gerichte/kantonsgericht_hs`), so the mapping is inferred to be 1:1.

### Grid

| Cell | Status | URL(s) (public / API) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED via API (public page BLOCKED: Cloudflare) | www.baselland.ch/politik-und-behorden/gerichte = API `/politik-und-behorden/gerichte` | API 200, type "direktion" 'Gerichte', 25 children (courts, rulings, forms, service list), modified 2026-09-22 | "Das Zivilkreisgericht Basel-Landschaft Ost in Sissach ist zuständig für folgende Gemeinden: Anwil, Arboldswil, Arisdorf, …" | — |
| C2 | VERIFIED (ordinance + fee in a form); fee page NONE | Ordinance SGS 170.31 GebT (bl.clex.ch); form `/politik-und-behorden/gerichte/leistungsverzeichnis/insolvenzerklaerung.pdf/@@download/file` | PDF 200, 2 pages, text layer. Ladder: AI path `/gerichte/kosten` → API 404; `@search` "Gerichtsgebühren" gave 33 hits, mostly tax-practice PDFs; `@search` "Kostenvorschuss" in /gerichte gave 18, no fee page; WebSearch found the ordinance only | "Der Kostenvorschuss von CHF 4'000.00 wird gleichzeitig bezahlt" | — |
| C3 | VERIFIED | API `@search?path.query=/politik-und-behorden/gerichte&portal_type=ContentPage` → **27 pages**; service list `/gerichte/leistungsverzeichnis` (7 PDFs: legal-aid request, bankruptcy, insolvency, wage claim, labour conciliation, conciliation authorities, builders' lien); `/gerichte/zivilkreisgerichte-formulare`; the expropriation court FAQ | JSON; page HTML in `slblocks` | "In der Regel ist das Schlichtungsgesuch an die Friedensrichterin oder den Friedensrichter im Friedensrichterkreis am Wohnsitz der beklagten Partei einzureichen." | — |
| C4 | VERIFIED | API `/gerichte/rechtsprechung` → https://bl.swisslex.ch/ | API 200 (158 words). bl.swisslex.ch 200 "Gerichte Basel-Landschaft", 8,165 B, 2 words: JS app | "Hier kommen Sie zum Rechtsprechungsportal der Gerichte des Kantons Basel-Landschaft: bl.swisslex.ch" | opencaselaw bl_gerichte 19,453 decisions, 1962-06-08 → 2026-06-03, **not stale** |
| C5 | VERIFIED | API `/gerichte/friedensrichter-innen`; `/politik-und-behorden/direktionen/volkswirtschafts-und-gesundheitsdirektion/generalsekretariat/aufgaben/schlichtungsstellen/mietangelegenheiten` | Both 200 (258 / 322 words; tenancy page modified 2026-08-27) | "Die Schlichtungsstelle für Mietangelegenheiten des Kantons Basel-Landschaft ist zuständig bei Streitigkeiten aus Miete und Pacht von unbeweglichen Sachen…" | Fees not stated on either page |
| G1 dogs | VERIFIED via API | `/politik-und-behorden/direktionen/volkswirtschafts-und-gesundheitsdirektion/lebensmittelsicherheit-und-veterinarwesen/veterinaerwesen/hunde` | 200, 922 words, modified 2025-08-26 | "Weiter müssen Hunde bei der Wohnsitzgemeinde des Hundehaltenden angemeldet und in der Hundedatenbank AMICUS registriert werden." | Laws SGS 342 and 342.12 |
| G2 tax | **BLOCKED: Cloudflare** | API `/…/steuerverwaltung/steuerbuch` (200, 19 words) links only to https://kanton.baselland.ch/politik-und-behorden/direktionen/finanz-und-kirchendirektion/steuerverwaltung/steuerbuch → 403 | Structure seen only in WebSearch: volumes 1–3, per-entry PDFs such as `…/band2_010_01.pdf/@@download/file/…`. Entry count unknown | — | Reachable instead via the API: filing pages …/steuererklaerung-natuerliche-personen-und-e-tax-bl/(abzuege-1, liegenschaften, …) and tax-practice PDFs (BLStPra). Tax law SGS 331 |
| G3 holidays | VERIFIED | API `/…/bildungs-kultur-und-sportdirektion/schulferien` (6 school-year pages, 2026/27–2031/32); data.bl.ch 13350 [cited g5] | Page 200; ODS API 200, total_count 58 (fields schuljahr, startdatum, enddatum, name) | "Herbst: Ferienbeginn Samstag 26. September 2026 … Unterrichtsbeginn Montag 12. Oktober 2026" | **Who sets them:** the canton. "Die Regelung der Schulferien gilt für die Volksschulen, … weiterführenden Schulen und Berufsfachschulen im Kanton Basel-Landschaft, mit Ausnahme des Regionalen Gymnasiums Laufental-Thierstein" |
| G4 road | VERIFIED via API | `/…/sicherheitsdirektion/motorfahrzeugkontrolle`; fee page `…/motorfahrzeugsteuern-und-gebuehren/gebuehren/gebuehren-und-besondere-abgaben-fuehrerzulassung` | Fee page 200, modified 2026-07-01 | "Die Ausstellung eines Führerausweises im Kreditkartenformat (FAK) 42.00" (CHF column) | Fee ordinance SGS 145.36 was revised 1 July 2026 (news page links bl.clex.ch change document 1283) |
| D1 | VERIFIED | API `/politik-und-behorden/gemeinden` (19 items, including 12 commune subsites) → link "Adressen der Gemeinden" → data.bl.ch dataset **10510** | ODS API 200, total_count **86**, fields bfs_nummer, name, …, website, uid_nummer, koordinaten | `{"bfs_nummer":"2761","name":"Gemeinde Aesch",…,"website":"https://www.aesch.bl.ch/"}` | `resolver`; one GET with limit=100 covers all 86 |
| D2 | VERIFIED; gazette BLOCKED by robots | API `/politik-und-behorden/besondere-behoerden/landeskanzlei`; gazette https://www.amtsblatt.bl.ch/ (eSHAB, tenant kabbl) | Chancellery page 200. amtsblatt.bl.ch 200 "eSHAB". robots.txt `Disallow: /` | "Die Landeskanzlei ist die Stabsstelle von Landrat und Regierungsrat." / "Das Amtsblatt des Kantons Basel-Landschaft erscheint ab Januar 2023 digital" | 11 own rubrics. Own notices 5,619 (GR-BL Grundbuch 3,245 …); cantons=BL 76,292 |

### Site recipe (BL)
- **www.baselland.ch and kanton.baselland.ch:** Cloudflare challenge (403). robots.txt 404 and sitemap 403 at stage 0.
- **bl-api.webcloud7.ch:** Plone REST with ftw.simplelayout.
  - Request any page path with `Accept: application/json`. Text is in `slblocks[*].text.data` (HTML), children in `items`, dates in `modified` / `effective`.
  - Search: `@search?SearchableText=…&path.query=<path>&portal_type=ContentPage&b_size=N` (returns `items_total`).
  - Files: `<file-url>/@@download/file` (PDF with text layer).
  - The API's own robots.txt answers **403** (a crawler that treats 403 as disallow-all would skip the host). Links in page HTML sometimes point to bl-backend.webcloud7.ch (not probed).
- Also: data.bl.ch (ODS), bl.clex.ch (LexWork laws), bl.swisslex.ch (decisions JS app).

### Draft YAMLs (BL)
```yaml
# yaml-now:api — cited g5, re-checked today (200, total_count 58)
id: bl_schulferien
name: Schulferien Basel-Landschaft (data.bl.ch 13350)
base_url: https://data.bl.ch
default_extent_id: CH-BL
authority: official_info
categories: [schools]
fetch_strategy: api
fetch_config:
  url: https://data.bl.ch/api/explore/v2.1/catalog/datasets/13350/records?limit=100&order_by=startdatum
  records_path: results
  id_template: "{schuljahr}-{name}-{startdatum}"
  event_date_field: startdatum
  title_template: "Schulferien Basel-Landschaft: {name} ({startdatum} bis {enddatum})"
  text_template: "{name} im Schuljahr {schuljahr}: vom {startdatum} bis {enddatum}."
  language: de
allow_narrowing: false
llm_tagging: false
---
# fetcher:plone-rest (NEW). Draft config; not supported by today's strategies
id: bl_gerichte
name: Gerichte Basel-Landschaft
base_url: https://bl-api.webcloud7.ch          # public URL: https://www.baselland.ch (Cloudflare 403)
default_extent_id: CH-BL
authority: official_info
categories: []                                 # category missing: courts
fetch_strategy: plone_rest                     # NEW
fetch_config:
  public_base_url: https://www.baselland.ch    # rewrite document URLs to the public host
  roots: ["/politik-und-behorden/gerichte",
          "/politik-und-behorden/direktionen/volkswirtschafts-und-gesundheitsdirektion/generalsekretariat/aufgaben/schlichtungsstellen/mietangelegenheiten"]
  include_types: [ContentPage, amt, File]
  language: de
# Same fetcher with other roots: bl_hunde (…/veterinaerwesen/hunde, [dogs]),
# bl_mfk (…/sicherheitsdirektion/motorfahrzeugkontrolle, [transport, parking]),
# bl_schulferien_seiten (…/bildungs-kultur-und-sportdirektion/schulferien, [schools])
```
- D1 → `resolver`: `https://data.bl.ch/api/explore/v2.1/catalog/datasets/10510/records?limit=100`.
- G2 → `blocked:cloudflare` (kanton.baselland.ch).
- D2 → `blocked:robots`.

### Claim checks (BL; the AI links were only ever tested behind Cloudflare, now tested through the API)
- **Cantonal court:**
  - `/gerichte/kantonsgericht` → Confirmed (API 200).
  - `/gerichte/kosten` → Wrong (API 404).
  - `/gerichte/themen` → Partly: 200, but it is the site-wide topic list (Arbeit, Bauen, …), not court guidance.
  - `/gerichte/rechtsprechung` → Confirmed (→ bl.swisslex.ch).
- **Civil district courts:** `/gerichte/zivilkreisgerichte` → Wrong (API 404). Correct: /gerichte/zivilkreisgericht-basel-landschaft-ost and -west.
- **Guidance (dogs, tax, school, road) under `/politik-und-verwaltung/…`:** all Wrong (API 404, that root does not exist). Correct paths are under `/politik-und-behorden/direktionen/…` (see grid).
- **Communes (S4):** `/politik-und-behorden/gemeinden` → Confirmed.
- **Chancellery:** `/politik-und-behorden/regierungsrat/landeskanzlei` → Wrong (API 404). Correct: `/politik-und-behorden/besondere-behoerden/landeskanzlei`.

---

## SO (Solothurn)

### Grid

| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://so.ch/gerichte/ | 200 "Gerichte - Kanton Solothurn", server HTML (TYPO3, fileadmin), 265 words, 54 links | Menu: "Richterämter · Obergericht · Weitere Gerichte · Gerichtsverwaltung · Informationen" | — |
| C2 | VERIFIED (ordinance); resident fee page NONE | Ordinance **BGS 615.11 Gebührentarif (GT)** → https://bgs.so.ch/app/de/texts_of_law/615.11 (LexWork: enactment 2016-07-15, not abrogated) | Ladder: AI `/gerichte/gebuehren/` → 404 (pre-check). Sitemap grep for fees under /gerichte/ → 0. /gerichte/, downloads, central court cashier and regulations pages had no CHF (prior-run log; /gerichte/ re-fetched today). The law text was fetched live (`show_as_json`, 792 KB) | "Für Tätigkeiten der Verwaltung und der Gerichte werden Gebühren nach diesem Tarif erhoben."; "Die Entscheidgebühr in Disziplinarsachen beträgt 100-7'000 Franken"; section "3.2. Zivilsachen § 145 Entscheidgebühr" | Resident info: "Ein arbeitsrechtliches Verfahren ist in aller Regel bis zu einem Streitwert von CHF 30'000.00 für die Parteien kostenlos." (/gerichte/richteraemter/zustaendigkeit/zivilsachen/). law_hits' SO court_fees entry is wrong |
| C3 | VERIFIED | /gerichte/richteraemter/zustaendigkeit/zivilsachen/ (731 words), …/strafsachen/, /gerichte/informationen/prozessformulare/, /verwaltung/staatskanzlei/legistik-und-justiz/unentgeltliche-rechtspflege-urp/ (292 words), /verwaltung/finanzdepartement/erbschaftsaemter/wer-erbt/, …/erbschaftsaemter/preise/, /services/betreibung-einleiten/, /gerichte/weitere-gerichte/friedensrichter/, …/mietschlichtung/, /services/schlichtungsverfahren-fuer-miete-und-pacht-schlichtungsgesuch/ | Sitemap: **73** so.ch/gerichte/ URLs, 20 on resident topics. Server HTML | "Gegen einen Unkostenbeitrag von Fr. 35.00 erhalten Sie vom Solothurnischen Anwaltsverband einen Gutschein für ein Beratungsgespräch" | — |
| C4 | VERIFIED | /gerichte/informationen/rechtsprechung/ → https://gerichtsentscheide.so.ch (FindInfo/Omnis). Also /gerichte/obergericht/ausgewaehlte-entscheide/urteile/* (10 pages, 2015–2016) | Route page links the host [prior-run log]. Host without cookies → "Cookie Not accepted" page; with a cookie jar → 200 "FindInfoWeb", 1,156 B | — | opencaselaw so_gerichte 13,587 decisions, 1956-11-07 → 2026-09-08, **not stale** |
| C5 | VERIFIED | https://so.ch/gerichte/weitere-gerichte/friedensrichter/; https://so.ch/verwaltung/departement-des-innern/departementssekretariat/oberaemter/schlichtung-und-vermittlung/mietschlichtung/ | 200 (627 words); 200 (932 words, fact sheet PDFs) | "Die Friedensrichterinnen und Friedensrichter sind Gemeindeorgane…"; "Das Verfahren ist kostenlos. Bei bös- oder mutwilliger Prozessführung können allerdings Kosten auferlegt werden." | Justice-of-the-peace circles listed (e.g. Gäu: Egerkingen, Härkingen, …) |
| G1 dogs | VERIFIED | https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/ (+ /leinenpflicht/, district offices' …/oberaemter/hundehaltung/) | 200 "Hunde - Kanton Solothurn", 597 words; leash page 200, 604 words; 53 dog URLs in sitemap (stage 0) | "…gilt in den Solothurner Wäldern in der Zeit vom 1. April bis 31. Juli eine generelle Leinenpflicht für alle Hunde." | Laws BGS 614.71 / 614.72 |
| G2 tax | VERIFIED | https://steuerbuch.so.ch/ | Home 200 "Solothurner Steuerbuch - Kanton Solothurn". Sitemap index → `?sitemap=pages&cHash=24b7400c2abd53b636ae62df3638e26a`: **175 locs today (140 entry pages `…/<§>-nr-<n>/`)**. Entry `/steuern/grundstueckgewinnsteuer/48-nr-1/` 200, full text in HTML (782 words in main). Entry PDF 200, 3 pages, text layer | "Fassung vom 26.09.2017 In Kraft ab 01.10.2017 … Grundstückgewinnsteuer, Allgemeines § 48 Nr. 1" | Enumerable; `yaml-now:html_crawl`. Tax law BGS 614.11 (missing from law_hits) |
| G3 holidays | VERIFIED | https://so.ch/verwaltung/departement-fuer-bildung-kultur-und-sport/volksschulamt/aktuell/ferienplan/ → 3 PDFs (2025/26, 2026/27, 2027/28) | Page 200; 2026/27 PDF 200, 8 pages, text layer | "Solothurn 28.09.2026 - 16.10.2026 21.12.2026 - 01.01.2027 …" | **Who sets them:** communes and school bodies. "Die Feriendaten der Volkschule unterscheiden sich nach Gemeinde und Region." The PDF lists each school body |
| G4 road | VERIFIED | https://so.ch/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/ (+ steuern-und-gebuehren/, fahrzeuge/, fuehrerinnen-und-fuehrer/) | 200 "Motorfahrzeugkontrolle - Kanton Solothurn", 874 words; fee page 200, 913 words (amounts only in linked PDFs); 158 road URLs (stage 0) | "Aktion für 4-stellige Kontrollschilder zum Preis von CHF 900.00 findet vom 9. September bis am 7. Oktober 2026 statt." | The linked 614.62 PDF is an old law copy ("Stand 15. Juli 2016", 15 pages); take the law from LexWork instead |
| D1 | VERIFIED | https://so.ch/allgemeine-informationen/einwohnergemeinden/ (+ /nach-bezirken/) | 200 "Einwohnergemeinden Kanton Solothurn - Kanton Solothurn"; **97** commune website links, A–Z | "Aedermannsdorf" → http://www.aedermannsdorf.ch/ | csv has 104 SO communes; 8 csv names not matched on the page (likely name variants such as "Oberdorf" or "Büren"; inferred) |
| D2 | VERIFIED; gazette BLOCKED by robots | https://so.ch/verwaltung/staatskanzlei/; https://so.ch/verwaltung/staatskanzlei/publikationen/amtsblatt/ → https://amtsblatt.so.ch/ (eSHAB, tenant kabso) | Chancellery 200; gazette page 200; amtsblatt.so.ch 200 "eSHAB" JS shell; robots.txt `Disallow: /` | "Die öffentlichen Meldungen des Kantons Solothurn werden seit Juli 2023 im elektronischen Amtsblatt veröffentlicht … über das Amtsblattportal … (SECO)" | 7 own rubrics: BA-SO 649, RE-SO 504, GE-SO 215, VA-SO 195, AL-SO 9, AR-SO 7, BU-SO 1. Own notices **1,580**; cantons=SO 68,445. One notice's XML: "Handänderung, Härkingen … Grundbuch Nr. 236, 914 m2" |

### Site recipe (SO)
- **so.ch:** TYPO3. robots.txt 1,709 B, no Crawl-delay, 49 Disallow lines, none covering /gerichte/, the dog, road or holiday pages, or /fileadmin/internet/dbk. `/sitemap.xml` has 10 child sitemaps and 8,909 URLs (stage 0).
- **steuerbuch.so.ch:** TYPO3. `/sitemap.xml` (index) → pages child with 175 locs. Note: curl `--compressed` reports only the 2,341-B transfer size; the body is 69,815 B.
- **gerichtsentscheide.so.ch:** FindInfo; needs a cookie jar.
- **amtsblatt.so.ch:** eSHAB; robots disallows everything.

### Draft YAMLs (SO)
```yaml
id: so_gerichte
name: Gerichte Kanton Solothurn – Zuständigkeit, Friedensrichter, Mietschlichtung
base_url: https://so.ch
default_extent_id: CH-SO
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/gerichte/", "/verwaltung/departement-des-innern/departementssekretariat/oberaemter/schlichtung-und-vermittlung/"]
  path_allowlist: ["/gerichte/", "/verwaltung/departement-des-innern/departementssekretariat/oberaemter/schlichtung-und-vermittlung/"]
  language: de
allow_narrowing: false
---
id: so_hunde
name: Hunde im Kanton Solothurn
base_url: https://so.ch
default_extent_id: CH-SO
authority: official_info
categories: [dogs]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/",
                "/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/"]
  path_allowlist: ["/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/",
                   "/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/",
                   "/verwaltung/volkswirtschaftsdepartement/amt-fuer-wald-jagd-und-fischerei/wildtiere/mit-hund-im-wald-leinenpflicht/"]
  language: de
allow_narrowing: false
---
# 175 sitemap locs < 200 cap; the entry HTML holds the full text
id: so_steuerbuch
name: Solothurner Steuerbuch
base_url: https://steuerbuch.so.ch
default_extent_id: CH-SO
authority: official_info
categories: [taxes]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/steuern/"]
  path_allowlist: ["/steuern/"]
  language: de
allow_narrowing: false
---
id: so_schulferien
name: Schulferienpläne der Volksschulen im Kanton Solothurn
base_url: https://so.ch
default_extent_id: CH-SO   # the PDF lists school bodies; commune-level answers need a school-body→BFS map
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://so.ch/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2025-2026.pdf",
         "https://so.ch/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2026_2027.pdf",
         "https://so.ch/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2027_2028.pdf"]
  language: de
allow_narrowing: false
---
id: so_mfk
name: Motorfahrzeugkontrolle Kanton Solothurn
base_url: https://so.ch
default_extent_id: CH-SO
authority: official_info
categories: [transport]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/"]
  path_allowlist: ["/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/"]
  language: de
allow_narrowing: false
```
- D1 → `resolver` (commune links in HTML, no BFS).
- D2 → `blocked:robots`.

### Claim checks (SO)
- **Supreme and administrative court:** `/gerichte/obergericht/` → Partly (redirects to the contact page). `/gebuehren/` → Wrong (404; no fee page exists; the law is 615.11). `/themen/` → Wrong (404). `/rechtsprechung/` → Wrong (404; real: /gerichte/informationen/rechtsprechung/).
- **District courts:** `/amtsgerichte/` → Wrong (404; SO calls them Richterämter, under /gerichte/richteraemter/).
- **Guidance (dogs, tax, school, road) under `so.ch/staat/departemente/…`:** all Wrong (404). Correct URLs are in the grid.
- **Communes (S4):** `so.ch/staat/gemeinden/` → Wrong (404); correct /allgemeine-informationen/einwohnergemeinden/.
- **Chancellery:** `so.ch/staatskanzlei/` → Confirmed (redirects).

---

## AG (Aargau)

### Grid

| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau | 200 "Gerichte Kanton Aargau", server HTML, 338 words | "Die Aargauer Gerichte stehen für eine unabhängige, sach- und zeitgemässe Rechtsprechung." | — |
| C2 | VERIFIED (ordinance + fact sheet); fee page NONE | Ordinance **SAR 662.110 Gebührendekret** (LexWork `show_as_json` 200: title "2. Gerichtsgebühren"). Fact sheet https://www.ag.ch/media/kanton-aargau/jb/dokumente/bezirksgerichte/formulare-und-merkblaetter/gka-155-200-1-215-merkblatt-stand-17-02-2025.pdf | Ladder: AI `/de/gerichte/themen/kosten-gebuehren` → 404 (pre-check). Sitemap grep for fees under the courts section → 0 (only the legal-aid page). PDF 200, 3 pages, text layer. VKD 221.150 is `abrogated: true` | "…gemäss § 12 Abs. 1 des Gebührendekrets eine Gerichtsgebühr zwischen Fr. 300.00 bis Fr. 2'500.00"; law: "Die Gerichtsgebühren richten sich im Übrigen nach den §§ 5–20." | law_hits has no AG court_fees entry |
| C3 | VERIFIED | …/organisation/bezirksgerichte/formulare-und-merkblaetter (5 PDFs: inheritance certificate, mediation, …), …/bezirksgerichte/aufgaben, …/schlichtungsbehoerden/friedensrichterinnen-und-friedensrichter/aufgaben, …/formulare-und-merkblaetter, …/schlichtungsbehoerden-fuer-miete-und-pacht, …/schlichtungsstelle-fuer-gleichstellungsfragen/aufgaben, …/die-familiengerichte-als-kesb/…, …/betreibungs-und-konkurswesen/…, /de/themen/recht-justiz/informationen-zur-unentgeltlichen-rechtspflege-(urp) | Sitemap: **125** court-section URLs (no query), 44 on resident topics. Server HTML | see C5 | — |
| C4 | VERIFIED (route); database host down during run | https://www.ag.ch/de/themen/recht-justiz/gesetze-entscheide/agve (www.ag.ch/agve redirects here) → agve.weblaw.ch (found via WebSearch) | Route page 200. **agve.weblaw.ch → 503 "Weblaw - Service Unavailable" on 3 tries** (12:2x–13:xx). decwork.ag.ch (named in the LexWork settings) → login redirect `/auth/main/factor_1` | "Diese sogenannten Leitentscheide sind ab dem Jahr 2000 online einsehbar." | opencaselaw AG: 18 codes, 13,165 decisions. Criminal court 2,160 (2026-09-08); administrative 1,909 (2026-09-03); civil 1,942 (2026-08-28); insurance 2,088 (2026-07-31); special administrative 1,213 (2026-06-17); commercial 336 (2026-08-27). **STALE:** ag_gerichte 2,834 (2025-12-12) and 8 small bodies (2008–2025) |
| C5 | VERIFIED | …/organisation/schlichtungsbehoerden/schlichtungsbehoerden-fuer-miete-und-pacht; …/friedensrichterinnen-und-friedensrichter/aufgaben | 200 (296 words); 200 (403 words) | "Das Schlichtungsverfahren ist grundsätzlich kostenlos."; justice of the peace decides "bis zu einem Streitwert von 2'000 Franken" and proposes a decision "bis zu einem Streitwert von 10'000 Franken" | Law 155.614 |
| G1 dogs | VERIFIED | https://www.ag.ch/de/themen/landwirtschaft-tiere/heim-und-nutztiere/hunde (+ /listenhunde, /tipps-beim-welpenkauf) | 200 "Hunde im Kanton Aargau", 740 words | "Im Kanton Aargau gilt die Leinenpflicht im Wald und am Waldrand vom 1. April bis 31. Juli." | Laws SAR 393.400 / 393.411 |
| G2 tax | VERIFIED | https://www.ag.ch/de/themen/steuern-finanzen/steuern-startseite/steuererklaerung-einreichen/wegleitung-zur-steuererklaerung (filing guide) | 200 "Wegleitung NP - Kanton Aargau", 640 words, 129 links; **97** guide URLs in the sitemap (enumerable) | "Die Wegleitung zur Steuererklärung 2025 hilft Ihnen dabei, Ihre Steuererklärung korrekt und vollständig auszufüllen." | No "Steuerbuch" URL among 39,511 sitemap URLs; a practice handbook elsewhere was not searched |
| G3 holidays | VERIFIED | https://www.schulen-aargau.ch/regelschule/schulorganisation/planung-ressourcen/stunden-ferienplanung → PDF `…/bksvs-kantonal-einheitlicher-ferienplan.pdf` | Page 200, 1,231 words. PDF 200, 3 pages, text layer | "Herbstferien 40. / 41. Woche 29.09. – 10.10. 2025" | **Who sets them:** mixed. "Je zwei Wochen Frühlings-, Herbst- und Weihnachtsferien sowie drei Wochen Sommerferien werden einheitlich durch den Erziehungsrat festgelegt. Die restlichen vier Ferienwochen legen die Gemeinden selber fest." The www.ag.ch sitemap has 0 holiday URLs |
| G4 road | VERIFIED | https://www.ag.ch/de/themen/mobilitaet-verkehr/strassenverkehr; office page …/dvi/organisation/strassenverkehrsamt; fees …/strassenverkehr/steuern-gebuehren/gebuehren/fahrzeug | 200 (708 words); 200; fee page 200 (314 words); 202 road URLs in sitemap | "Fahrzeugausweis für alle Kategorien (ausgenommen MOFA) Fr. 20.–" | — |
| D1 | VERIFIED | https://www.ag.ch/de/themen/staat-politik/gemeinden (no list) → XLSX `…/statistik/statistische-daten/eckdaten-kt-aargau/gemeinden/gemeindeverzeichnis-ag-adressen-telefon.xlsx` (found via WebSearch) | Page 200. XLSX 200, 40,147 B, sheet "Gemeinden AG", "Stand: 16. September 2026", **196** rows with Bezirk, BFSNR, …, Internet | "Mit 196 Gemeinden ist der Kanton Aargau einer der gemeindereichsten Kantone."; row "Aarau \| 4001 \| Aarau \| … \| http://www.aarau.ch" | The staff directory (Behördenverzeichnis) JSON `/io/staatskalender_frontend/search.json?query=` has no communes (0 results) and `/io/*` is robots-disallowed |
| D2 | VERIFIED; gazette BLOCKED by robots | https://www.ag.ch/de/ueber-uns/kantonale-verwaltung/sk; https://www.ag.ch/de/themen/staat-politik/amtsblatt → https://amtsblatt.ag.ch/publikationen/ | Chancellery 200 "Staatskanzlei - Kanton Aargau". Gazette page 200. amtsblatt.ag.ch 200 "Amtsblatt AG Publikationen", server HTML (TYPO3 "ekab"), 5,370 words; per-notice URLs /ekab/00.103.623/publikation/. **robots.txt disallows /publikationen/, /ekab/, /fileadmin/ekab/** (sitemap https://amtsblatt.ag.ch/sitemap.xml) | "Im Amtsblatt werden Bekanntmachungen der gesetzgebenden, vollziehenden und richterlichen Behörden publiziert…" | Not on eSHAB: 0 AG rubrics. Tenant kabag holds only secondary SHAB notices (17,844) |

### Site recipe (AG)
- **www.ag.ch:** custom CMS (bundles from static.cdn.ag.ch v24.1.1), server HTML.
  - robots.txt: all agents may crawl except `/app/*`, `/io/*` and `/media/system|special|dynAssets/`. No Crawl-delay.
  - `/sitemap.xml` has 8 children and 39,511 URLs.
- **www.schulen-aargau.ch:** robots.txt 404 (no rules).
- **gesetzessammlungen.ag.ch:** LexWork. Its settings expose `decwork_hostname: decwork.ag.ch`, a login-only backend.
- **amtsblatt.ag.ch:** TYPO3; robots-restricted.

### Draft YAMLs (AG)
```yaml
id: ag_gerichte
name: Gerichte Kanton Aargau – Organisation, Schlichtung, Merkblätter
base_url: https://www.ag.ch
default_extent_id: CH-AG
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/ueber-uns/gerichte-kanton-aargau"]
  path_allowlist: ["/de/ueber-uns/gerichte-kanton-aargau"]   # 125 URLs < 200 cap
  language: de
allow_narrowing: false
---
id: ag_hunde
name: Hunde im Kanton Aargau
base_url: https://www.ag.ch
default_extent_id: CH-AG
authority: official_info
categories: [dogs]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/themen/landwirtschaft-tiere/heim-und-nutztiere/hunde"]
  path_allowlist: ["/de/themen/landwirtschaft-tiere/heim-und-nutztiere/hunde"]
  language: de
allow_narrowing: false
---
id: ag_steuern_wegleitung
name: Wegleitung zur Steuererklärung (natürliche Personen) Kanton Aargau
base_url: https://www.ag.ch
default_extent_id: CH-AG
authority: official_info
categories: [taxes]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/themen/steuern-finanzen/steuern-startseite/steuererklaerung-einreichen/wegleitung-zur-steuererklaerung"]
  path_allowlist: ["/de/themen/steuern-finanzen/steuern-startseite/steuererklaerung-einreichen/wegleitung-zur-steuererklaerung",
                   "/de/themen/steuern-finanzen/steuern/steuererklaerung-einreichen/wegleitung"]   # 97 URLs
  language: de
allow_narrowing: false
---
# the whole road section has 202 URLs > cap, so restrict to three sub-sections
id: ag_strassenverkehr
name: Strassenverkehrsamt Aargau – Gebühren, Fahrzeuge, Führerausweise
base_url: https://www.ag.ch
default_extent_id: CH-AG
authority: official_info
categories: [transport]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/themen/mobilitaet-verkehr/strassenverkehr/steuern-gebuehren", "/de/themen/mobilitaet-verkehr/strassenverkehr/fahrzeuge", "/de/themen/mobilitaet-verkehr/strassenverkehr/fuehrerausweise"]
  path_allowlist: ["/de/themen/mobilitaet-verkehr/strassenverkehr/steuern-gebuehren", "/de/themen/mobilitaet-verkehr/strassenverkehr/fahrzeuge", "/de/themen/mobilitaet-verkehr/strassenverkehr/fuehrerausweise"]
  language: de
allow_narrowing: false
---
id: ag_schulferien
name: Kantonal einheitliche Feriendaten Volksschule Aargau
base_url: https://www.schulen-aargau.ch
default_extent_id: CH-AG   # covers 9 canton-wide weeks; the other 4 weeks are set by each commune
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.schulen-aargau.ch/media/schulen-aargau/schulorganisation/ressourcen-planung/stunden-ferienplanung/bksvs-kantonal-einheitlicher-ferienplan.pdf"]
  language: de
allow_narrowing: false
```
- D1 → `resolver` (XLSX with BFS and websites).
- D2 → `blocked:robots`.

### Claim checks (AG)
- **Supreme court:** `/de/gerichte/obergericht` → Confirmed (redirects to …/organisation/obergericht). Fees, themes and case-law links under /de/gerichte/… → Wrong (404). Correct: fact sheet + SAR 662.110; AGVE page.
- **Administrative court:** `/de/gerichte/verwaltungsgericht` → Wrong (404); correct …/organisation/obergericht/verwaltungsgericht (sitemap).
- **District courts:** `/de/gerichte/bezirksgerichte` → Confirmed (redirects).
- **Guidance (dogs, tax, school, road) under `/de/verwaltung/…`:** all Wrong (404). Correct URLs are in the grid.
- **Communes (S4):** `/de/verwaltung/dvi/gemeinde-fachbereich` → Wrong (404). **Chancellery:** `/de/verwaltung/staatskanzlei` → Wrong (404); correct /de/ueber-uns/kantonale-verwaltung/sk.

---

## L1: city law (Zürich, Bern, Thun)

| City | Status | URL | Platform and format | Number of texts | Dog / waste / parking | Destination |
|---|---|---|---|---|---|---|
| **Zürich** (CH-ZH-261) | VERIFIED | https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung.html (200 "Amtliche Sammlung \| Stadt Zürich", 153 words: "Seit 1893 werden die Erlasse der Stadt Zürich in der sogenannten amtlichen Sammlung geführt.") | stadt-zuerich.ch web components. 80 group pages `/amtliche-sammlung/<n>/<nnn>.html` list entries as `<stzh-card-superteaser heading="712.110 …" meta='["In Kraft: 01.01.2023"]'>`. Each detail page's `<stzh-datatable rows="…">` JSON holds AS-Nummer, Beschlussdatum, Inkrafttreten, Ausserkrafttreten and the Rechtstexte PDF link `/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/<grp>/<nr>/….pdf`. PDFs have a text layer (VAZ: 13 pages) | **791 entries: 622 in force, 169 repealed.** No sitemap (stage 0) | **Dogs:** 554.510 Vollzugsvorschriften zum Hundegesetz (in force 01.09.2017). **Waste:** 712.110 VAZ (01.01.2023). **Parking:** 551.310 Parkkartenverordnung (01.01.2026), 551.311 blue-zone parking card fees ("Die Jahresgebühren betragen: a. Fr. 300.– für Anwohnerparkkarten"), 551.330, 741.500 Parkplatzverordnung | Existing `stadt_zuerich.yaml` (html_crawl) reaches group and detail pages, because `extract_links` reads `href` on any element (`html_sections.py:144-158`). But detail pages are metadata only (76–181 words); the PDF link sits inside the JSON attribute and `.pdf` is skipped anyway (`html_crawl.py:14`). About 871 AS pages exceed the 200-page cap shared with 3 other start paths. So: `yaml-now:pdf` for the selection below plus `fetcher:stzh-as` for all 622 |
| **Bern** (CH-BE-351) | VERIFIED | https://www.bern.ch/themen/stadt-recht-und-politik/stadtrecht (200 "Stadtrecht — Stadt Bern": "Die Stadt Bern führt zwei Rechtssammlungen: Die Systematische Sammlung des Stadtrechts von Bern (SSSB) und die Amtliche Sammlung…") → https://stadtrecht.bern.ch/lexoverview-home | **iDPARC/openlaws ExtJS app** (tenant `sssb`): every URL returns the same 1,333-B JS shell; data flows over a custom request channel (not reverse-engineered). robots allows all and names `https://stadtrecht.bern.ch/sitemap.xml` (200, 491,803 B, 2,593 locs). **Per-text export works:** `https://stadtrecht.bern.ch/lex-<nr>.pdf` (lex-151_21.pdf 200, 40 pages, text layer) and `lex-<nr>.docx` (200). `.json` / `.xml` → 404 | **218 SSSB numbers** (`dgn-lex_*` in the sitemap; 95 also have `lex-*` URLs; numbers listed only as `dgn-lex_` still export, e.g. lex-761_232.docx 200) | **Dogs:** 559.61 Hundeverordnung (HV), 15.02.2023, "Stand: 1. September 2026". **Waste:** 822.1 Abfallreglement (AFR), 822.111 Abfallverordnung (AFV). **Parking:** 761.232 Parkkartenverordnung (PKV), 761.212 PVUA, 761.211 VZB | `yaml-now:pdf` (selection) + `fetcher:idparc-export` (sitemap → lex-<nr>.pdf) |
| **Thun** (CH-BE-942) | VERIFIED | https://www.thun.ch/reglementeverordnungen (200 "Stadt Thun - Reglemente und Verordnungen", 830 words, 285 links) | **i-web** (`icms-dt` table, `data-entities` JSON with fields title, _nummer, _dokumentList, _rechtsgueltigkeit). `/_doc/<id>` → `/_docn/<id>/<name>.pdf`; text layer (AFR: 7 pages, "Abfallreglement der Stadt Thun (AFR) (Stadtratsbeschluss Nr. 76 vom 24. November 2011)") | **127 rows, 127 distinct `/_doc/` PDFs** | **Waste:** 822.1 AFR (valid 01.01.2024), 822.11 AFV (01.01.2025). **Parking:** 552.04 PBR, 552.05 PKV, 154.261.12 PGV, 72.07 PPO. **Dogs:** none (0 of 127 rows mention "Hund") | `fetcher:iweb-table` (existing class) + `yaml-now:pdf` selection |

The Bern PDF URLs below follow the export pattern verified on lex-151_21.pdf; for these five numbers I fetched the DOCX (200), not the PDF. The repo's pdf fetcher follows redirects (`pdf.py:37,47`), so Thun's `/_doc/` links work.

```yaml
id: stadt_zuerich_as_hunde_abfall_parkieren
name: Stadt Zürich – Amtliche Sammlung (Hunde, Abfall, Parkieren)
base_url: https://www.stadt-zuerich.ch
default_extent_id: CH-ZH-261
authority: official_info        # municipal_law once the AS is registered as a law platform
categories: [dogs, waste, parking]
fetch_strategy: pdf
fetch_config:
  urls:
    - https://www.stadt-zuerich.ch/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/554/510/554.510%20Vollzugsvorschriften%20zum%20Hundegesetz_17_V4.pdf
    - https://www.stadt-zuerich.ch/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/712/110/712.110%20Verordnung%20Abfallbewirtschaftung%20%28VAZ%29%202022_V8.pdf
    - https://www.stadt-zuerich.ch/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/551/310/551.310-pkv-2011-inkl-anhang-pkv-2025-v3.pdf
    - https://www.stadt-zuerich.ch/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/551/311/551.311_Geb%C3%BChrenordnung%20Parkkarten%20Blaue%20Zonen%20V1.pdf
    - https://www.stadt-zuerich.ch/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/551/330/551.330_Parkierungs-%20und%20Parkuhrkontrollgeb%C3%BChren17_V3.pdf
    - https://www.stadt-zuerich.ch/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/741/500/741.500_Parkplatzverordnung_16_V4.pdf
  language: de
allow_narrowing: false
---
id: stadt_bern_sssb_hunde_abfall_parkieren
name: Stadt Bern – SSSB (Hunde, Abfall, Parkieren)
base_url: https://stadtrecht.bern.ch
default_extent_id: CH-BE-351
authority: official_info
categories: [dogs, waste, parking]
fetch_strategy: pdf
fetch_config:
  urls: ["https://stadtrecht.bern.ch/lex-559_61.pdf", "https://stadtrecht.bern.ch/lex-822_1.pdf", "https://stadtrecht.bern.ch/lex-822_111.pdf",
         "https://stadtrecht.bern.ch/lex-761_232.pdf", "https://stadtrecht.bern.ch/lex-761_212.pdf"]
  language: de
allow_narrowing: false
---
id: stadt_thun_abfall_parkieren
name: Stadt Thun – Reglemente Abfall und Parkieren
base_url: https://www.thun.ch
default_extent_id: CH-BE-942
authority: official_info
categories: [waste, parking]
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.thun.ch/_doc/4917697", "https://www.thun.ch/_doc/5450779", "https://www.thun.ch/_doc/4355560",
         "https://www.thun.ch/_doc/4355563", "https://www.thun.ch/_doc/4351168", "https://www.thun.ch/_doc/4355737"]
  language: de
allow_narrowing: false
```

**City claim checks** (all three AI links were 404 at pre-check; I did not re-request them):
- Zürich `…/portal/de/index/politik_u_recht/stadtrecht/systematische_rechtssammlung.html` → Wrong; correct: the Amtliche Sammlung URL above.
- Bern `www.bern.ch/politik-und-verwaltung/stadtrecht/systematische-rechtssammlung-bsr` → Wrong; the collection is called SSSB and lives on stadtrecht.bern.ch.
- Thun `…/politik-verwaltung/rechtssammlung/systematische-rechtssammlung-srt.html` → Wrong; correct: /reglementeverordnungen.

---

## Cross-canton section

### New fetcher classes needed
1. **`plone-rest`** (Plone REST with ftw.simplelayout):
   - Reads page JSON, takes text from `slblocks[*].text.data`, walks children via `items` or `@search?path.query=`, downloads files via `@@download/file`, and rewrites URLs to the public host.
   - Serves all BL cantonal pages (courts, dogs, road office, holidays, conciliation) and **12 BL commune subsites** seen under `/politik-und-behorden/gemeinden/` (Arisdorf, Augst, Burg im Leimental, Diepflingen, Eptingen, Giebenach, Hersberg, Lampenberg, Maisprach, Nenzlingen, Nusshof, Ramlinsburg).
   - bern.ch is probably Plone too (the sitemap has an `ftw-simplelayout-textblock` slug; inferred, not tested).
2. **`eshab-export`** (paginated XML/CSV bulk export plus per-notice XML): gazettes of SO, ZH, BE, BS, BL. The rubric list shows 16 tenants: kabar, kabbe, kabbl, kabbs, kabda, kabgr, kabnw, kabow, kabsh, kabso, kabsz, kabti, kabvs, kabzg, kabzh and shab, i.e. **14 cantonal gazettes**. Destination today: `blocked:robots` plus a design question (robots `Disallow: /`, personal data in notices).
3. **`idparc-export`** (sitemap → `lex-<nr>.pdf|.docx`): Bern city, 218 texts. Other tenants of this platform are not verified; the app's theme list names uri, weblaw, walderwyss, openlaws and others (inferred).
4. **`stzh-as`** (Zürich AS: group pages → detail `stzh-datatable` JSON → PDF plus in-force dates): Zürich city, 791 entries.
5. **`iweb-table`** (existing): Thun, 127 rows.
6. **`xlsx`**: commune directories AG (196), BE (334), ZH (160), all resolver data, plus the ZH holiday XLSX (g5).
7. **`pdf-index`**: SO holiday PDFs (one per school year, year in the file name), AG and BE holiday PDFs, AG court fact sheets, BL court service list (via the Plone API).
8. **`sitemap-crawl`**, plus two html_crawl gaps:
   - Many sections exceed the 200-page cap (`config.py:22`): gerichte-zh.ch themes 248, Zürich AS about 871, AG road 202.
   - There is no per-source Crawl-delay; BE and BS ask for 10 s, the crawler uses 0.5 s (`config.py:23`).
9. **Decision systems** (only if opencaselaw were insufficient; it is current for all main courts here): FindInfo/Omnis CGI (SO, BS, ZH VGR), Tribuna JS apps (BE), Swisslex (BL), Weblaw AGVE (AG).

### Blocked items
- **Cloudflare 403:** www.baselland.ch and kanton.baselland.ch. The API workaround covers all BL cells except **BL G2 (Steuerbuch on kanton.baselland.ch)**.
- **robots.txt `Disallow: /`:** amtsblattportal.ch, amtsblatt.so.ch, amtsblatt.zh.ch, amtsblatt.be.ch, www.kantonsblatt.ch, www.amtsblatt.bl.ch.
- **amtsblatt.ag.ch:** robots disallows /publikationen/, /ekab/ and /fileadmin/ekab/.
- **agve.weblaw.ch:** 503 on three tries. decwork.ag.ch requires login.
- **www.ag.ch:** `/app/*` and `/io/*` disallowed (staff-directory JSON).
- **bl-api.webcloud7.ch/robots.txt:** answers 403; policy unclear.
- **Minor:** gerichtsentscheide.so.ch needs cookies (works with a cookie jar); `https://www.vgrzh.ch` gives no connection (the http:// variant redirects to zh.ch).

### 5 best finds
1. **BL's whole cantonal website is open JSON** at `bl-api.webcloud7.ch` (Plone REST, same paths, `@search`, file downloads) despite the Cloudflare wall. data.bl.ch 10510 adds a commune directory: 86 communes with BFS number and website.
2. **eSHAB bulk export** (`/api/v1/publications/xml?tenant=…&rubrics=…&publicationDate.start=…&pageRequest.page=N`, plus `/api/v1/rubrics` for each tenant's rubric codes) exposes 14 cantonal gazettes with full-text XML. Own notices: ZH 19,659, BE 20,165, BS 9,462, BL 5,619, SO 1,580. Robots forbids crawling.
3. **Bern city SSSB:** 218 texts enumerable from the sitemap, each exportable as a text-layer PDF or DOCX (`lex-<nr>.pdf|.docx`), including the Hundeverordnung, Abfallreglement and Parkkartenverordnung.
4. **Official commune directories with BFS numbers and websites:** AG XLSX (196, "Stand 16. September 2026"), BE XLSX (334), BL JSON (86). Ready resolver data.
5. **Solothurn Steuerbuch** (175 sitemap locs, 140 entries, full text in HTML plus PDF with "In Kraft ab" date; `yaml-now:html_crawl`) and **Zürich AS** structured metadata (791 entries with in-force dates and PDF links).

### law_hits.json corrections
| Canton | Topic | law_hits says | Correct |
|---|---|---|---|
| AG | court_fees | (missing) | SAR 662.110 Gebührendekret; 221.150 VKD is abrogated |
| SO | court_fees | 125.751.3 (Hague convention) — wrong | BGS 615.11 Gebührentarif (GT) |
| SO | tax | 614.61 (motor-vehicle tax only) | add BGS 614.11 Gesetz über die Staats- und Gemeindesteuern |
| BS | tax | (no tax topic) | add SG 640.100 Gesetz über die direkten Steuern |

### Not verified / open
- BS holiday authority (inferred canton-wide) and Riehen/Bettingen coverage.
- The BL Steuerbuch entry count (blocked).
- AGVE database content (host down).
- eSHAB terms of use: a search summary says the data is "freely usable"; I did not open the terms.
- Whether www.baselland.ch paths map 1:1 onto the API (inferred from matching WebSearch URLs).
- Whether the BS courts landing page links reach all 136 court pages.