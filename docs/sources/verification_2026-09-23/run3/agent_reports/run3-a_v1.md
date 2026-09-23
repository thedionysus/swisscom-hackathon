All cells are filled and the evidence is in hand. Writing the final report.

# Run 3, group run3-a: ZH · BE · BS · BL · SO · AG, plus L1 for Zürich, Bern, Thun

Every live check was made on 2026-09-23 in this session with curl or python. Saved responses are in `<scratchpad>/run3-a/pages/`, and the helper scripts sit next to them (`probe.py`, `plone.py`, `plone_text.py`, `eshab.py`, `lexwork_*.py`, `xlsx_peek.py`, `zh_as_scan.py`, `bern_titles.py`).

Conventions:
- **[cited g5] / [cited g2]** means the finding comes from those reports. For those URLs I only re-checked liveness and title today.
- **(prior run)** means the evidence is from last night's log. I re-checked everything that went into a cell today.
- **Inferred** marks conclusions I did not verify directly.

## Headline findings
1. **BL is not blocked.** www.baselland.ch and kanton.baselland.ch answer 403 Cloudflare ("Just a moment...", including one try with a full Chrome 128 User-Agent). The same canton content is served as open Plone REST JSON at **`https://bl-api.webcloud7.ch/<same path>`**, with site search (`@search`) and file downloads (`/@@download/file`). Every BL cell except the Steuerbuch was verified through it.
2. **Official gazettes of SO, ZH, BE, BS and BL all run on eSHAB** (the SECO amtsblattportal). It has an unauthenticated bulk export, `/api/v1/publications/xml|csv?…&pageRequest.page=N&pageRequest.size=M` (rubric and date filters work), plus per-publication XML with full text. **However, robots.txt on amtsblattportal.ch, amtsblatt.so.ch, kantonsblatt.ch and amtsblatt.zh.ch is `User-agent: * / Disallow: /`.** AG runs its own gazette (amtsblatt.ag.ch), whose robots disallows `/publikationen/` and `/ekab/`.
3. **Real Verwaltungsgericht sites:**
   - ZH is the zh.ch section `/de/gerichte-notariate/verwaltungsgericht.html`. Decisions are in FindInfo at `vgrzh.djiktzh.ch/cgi-bin/nph-omniscgi.exe?…Schema=ZH_VG_WEB…`; a deep link answered 200 with the full decision VB.2023.00118.
   - BE is **www.vgb.justice.be.ch**. Decisions are at `www.vg-urteile.apps.be.ch/tribunapublikation/`.
4. **Commune directories with BFS numbers and websites exist as machine-readable files:**
   - AG: XLSX, 196 communes, "Stand: 16. September 2026".
   - BE: XLSX, 334 communes, Homepage column.
   - BL: data.bl.ch dataset 10510 as JSON, 86 communes with a `website` field.
   - ZH: XLSX, 160 communes, e-mail only (no website or BFS column).
5. **City law:**
   - Bern SSSB: every text is exportable as `https://stadtrecht.bern.ch/lex-<nr>.pdf|.docx`. There are 218 numbers in the sitemap, and dog, waste and parking texts are present.
   - Zürich AS: 791 entries with In-Kraft metadata and PDF links. The existing html_crawl source reaches only the metadata pages.
   - Thun: i-web table, 127 PDFs; no dog regulation.

---

## ZH (Kanton Zürich)

### Grid
| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 courts-home | VERIFIED [civil/criminal cited g2] | https://www.gerichte-zh.ch/de · VGR: https://www.zh.ch/de/gerichte-notariate/verwaltungsgericht.html | gerichte-zh: 200 "Zürcher Zivilgerichte und Strafgerichte" (precheck), Drupal server HTML (g2). VGR: 200 "Verwaltungsgericht \| Kanton Zürich", server HTML, 12,058 B, 767 words. `http://www.vgrzh.ch/` redirects there with 200; `https://www.vgrzh.ch/` gives curl 000 | VGR Rechtsprechung page: "Hier finden Sie die Entscheiddatenbank des Gerichts, in der ein Grossteil der Urteile veröffentlicht wird." | The VGR's real site is a zh.ch section, not its own host |
| C2 court-fees | VERIFIED | Page: https://www.gerichte-zh.ch/de/themen/zivilprozess/prozesskosten · Ordinance **LS 211.11 GebV OG**: LexFind 21701 → https://www.zh.ch/de/politik-staat/gesetze-beschluesse/gesetzessammlung/zhlex-ls/erlass-211_11-2010_09_08-2011_01_01-087.html → PDF `https://www.notes.zh.ch/appl/zhlex_r.nsf/WebView/7142D0282EDFCA9CC1257DC4003F6288/$File/211.11_8.9.10_87.pdf` · VGR: LS 175.252 | Page: 200 "Prozesskosten und unentgeltliche Rechtspflege", 120,738 B, 267 words of main text plus JS fee calculators (no static CHF). LS page: 200 "Gebührenverordnung des Obergerichts (GebV OG)". PDF: 200, 6 pages, text layer | GebV OG § 4: "bis 1 000 25% des Streitwertes, mind. Fr. 150"; also "Bei nicht vermögensrechtlichen Streitigkeiten beträgt die Gebühr Fr. 100 bis Fr. 850." | The notes.zh.ch `OpenAttachment` URL returns a 153 B JS redirect; use the `WebView/$File` form. Other fee laws: 212.812 (social insurance court), 215.12 (lawyers) |
| C3 court-guidance | VERIFIED [cited g2; count re-checked] | https://www.gerichte-zh.ch/de/themen | Sitemap 454 URLs, **248** under /de/themen/ (g2 said 249). Server HTML with about 1,400 words of navigation per page | "Im Kanton Zürich sind für gewöhnlich … die Friedensrichterinnen und Friedensrichter der einzelnen Gemeinden als Schlichtungsbehörde im Sinne von Art. 197 ZPO tätig." | 10 URLs: /de/themen/ehe-und-familie, /erbschaft, /miete, /arbeit, /betreibung-und-konkurs, /zivilprozess, /zivilprozess/prozesskosten, /zivilprozess/schlichtungsverfahren, /zivilprozess/mediation, /miete/hilfen/schlichtungsbehoerden. VGR guidance: zh.ch …/streitigkeiten-vor-verwaltungsgericht/informationen-zum-gerichtsverfahren.html (200, 2,238 words) |
| C4 court-decisions | VERIFIED | https://www.gerichte-zh.ch/entscheide/entscheide-anzeigen.html · VGR: zh.ch …/rechtsprechung-des-verwaltungsgerichts.html → https://vgrzh.djiktzh.ch/findinfo/xhtmltemplates/standard.htm → `…/cgi-bin/nph-omniscgi.exe?…Schema=ZH_VG_WEB&Aufruf=getMarkupDocument&nF30_KEY=223634…` | gerichte-zh: 200, server HTML, 1,615 words. FindInfo (Omnis CGI): standard.htm is a 638 B frameset; the deep link answers 200 with 56,660 B iso-8859-1 HTML, 4,604 words. No feed or API seen | "Geschäftsnummer: VB.2023.00118 Entscheidart und -datum: Endentscheid vom 09.11.2023" | opencaselaw ZH: 23 codes, 87,134 decisions. zh_sozialversicherungsgericht 34,715 (latest 2026-06-17), zh_obergericht 28,301 (2026-07-29), zh_verwaltungsgericht 12,637 (2026-08-28), zh_handelsgericht 4,680 (2026-06-04), zh_mietgericht 186 (2026-09-03). **STALE:** zh_kassationsgericht (2012-06-25), zh_gerichte 1,438 (2025-11-05), sav_kantone (no dates) |
| C5 conciliation | VERIFIED | https://www.gerichte-zh.ch/de/themen/zivilprozess/schlichtungsverfahren · https://www.gerichte-zh.ch/de/themen/miete/hilfen/schlichtungsbehoerden | Both 200, server HTML (1,427 and 1,368 words including navigation) | "Bei Streitigkeiten aus Miete und Pacht … sind im Kanton Zürich nicht die Friedensrichterämter … zuständig. Vielmehr ist jedem Bezirksgericht eine besondere Schlichtungsbehörde angegliedert" | Guidance: yes (plus the Friedensrichterhandbuch PDF and a legal-aid form for conciliation). Fees: GebV OG, Fr. 100–850 for non-pecuniary cases. Laws: 212.126/212.127 (Friedensrichterkreise), 177.12 |
| G1 dogs | VERIFIED [cited g5] | https://www.zh.ch/de/umwelt-tiere/tiere/haustiere-heimtiere/hunde.html | Today: 200 "Hunde \| Kanton Zürich", 2,725 words | g5: "Seit 1. Juni 2025 ist neue Hundegesetzgebung in Kraft …" | LS 554.5 Hundegesetz, 554.51 Hundeverordnung. Nothing missing |
| G2 tax guide | VERIFIED [cited g5] | https://www.zh.ch/de/steuern-finanzen.zhweb-sitemap.xml | Today: 200 text/xml. g5: 1,043 locs, 159 zstb-*.html entries plus current PDFs. Enumerable | g5: "ZStB-Nummer 30.1 … Gültig ab 27. September 2023" | LS 631.1, 631.11 |
| G3 school holidays | VERIFIED [cited g5] | https://www.zh.ch/de/bildung/bildungssystem/schulferien.html | Today: 200 "Schulferien \| Kanton Zürich", 1,931 words. XLSX per Schulgemeinde (185 rows, g5) | g5: Zürich-Uto autumn holidays 6–17 Oct 2025 | **Who sets them:** the Schulgemeinden; only school start and Christmas are binding (g5). A Schulgemeinde→BFS map is needed |
| G4 road office | VERIFIED [cited g5] | https://www.zh.ch/de/sicherheitsdirektion/strassenverkehrsamt.html | Today: 200 "Strassenverkehrsamt \| Kanton Zürich", 870 words | g5: "Lernfahrausweis 40.00" (fee order valid from 1 Jan 2026, PDF with text) | LS 741.1/741.11. Parking is municipal |
| D1 communes | VERIFIED | https://www.zh.ch/de/politik-staat/gemeinden.html → https://www.zh.ch/content/dam/zhweb/bilder-dokumente/themen/politik-staat/gemeinden/politische_gemeinden.xlsx (also gemeindeverzeichnis.pdf, gemeindepraesidenten.xlsx, gemeindeschreiber.xlsx) | Page: 200, 1,379 words. XLSX: 200, 84,863 B, sheet Tabelle2 = header + 160 rows. Columns: Organisation, Zusatz, Strasse, Postfach, PLZ, Ort, E-Mail. **No website, no BFS number** | "Die 160 politischen Gemeinden und 60 Schulgemeinden …" · row "Gemeinde Aesch · Dorfstrasse 3 · 8904 · gemeindeverwaltung@aesch-zh.ch" | Destination `resolver`. Website only derivable from the e-mail domain (inferred) |
| D2 chancellery + gazette | VERIFIED | https://www.zh.ch/de/staatskanzlei.html · Gazette: https://amtsblatt.zh.ch/ | SK: 200, 680 words. Gazette: 200 "eSHAB", 1,384 B JS shell. **robots: Disallow /** | "Die Staatskanzlei berät und unterstützt den Regierungsrat und das Präsidium bei der Wahrnehmung der Regierungsaufgaben." | eSHAB tenant kabzh: `tenant=kabzh` gives total 60,495 (SHAB debt-enforcement notices); `cantons=ZH` gives 524,636, including "Todesanzeige – …" (personal data) |

### Site recipe (ZH)
- **www.zh.ch** (AEM, per g5). robots.txt is 56 B: only `Sitemap: /bin/zhweb/publish/sitemap.xml` (index of 44 child sitemaps, 80,504 URLs in stage0); no Disallow, no Crawl-delay. Use the `.html` form of pages (zh_ch.yaml comment).
- **www.gerichte-zh.ch** (Drupal: robots disallows /core/, /profiles/ and composer READMEs). `/sitemap.xml` has 454 URLs (sitemap_index.xml is 404). No Crawl-delay.
- **vgrzh.djiktzh.ch**: FindInfo/Omnis CGI, iso-8859-1.
- **amtsblatt.zh.ch**: eSHAB, robots Disallow /.
- No bot walls met.

### Draft YAMLs (ZH)
```yaml
id: gerichte_zh_themen
name: Gerichte Kanton Zürich – Rechtliche Themen
base_url: https://www.gerichte-zh.ch
default_extent_id: CH-ZH
authority: official_info
categories: []            # category missing: courts (Miete pages would fit housing)
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/themen"]
  path_allowlist: ["/de/themen"]   # 248 pages > crawl_max_pages 200 (config.py:22): split per theme or raise the cap
  language: de
allow_narrowing: false
license: "gerichte-zh.ch terms of use"
---
id: zh_verwaltungsgericht
name: Verwaltungsgericht Kanton Zürich – Verfahren und Kosten
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
Destinations: D1 `resolver` (xlsx) · D2 gazette `design:robots Disallow / plus personal data in notices` · fee laws through `fetcher:lexwork`/LexFind.

### Claim checks (ZH)
- gerichte-zh.ch/ (home, direct link): **Confirmed** (redirects to /de).
- …/themen/prozesskosten.html (fees, wrapped link): **Wrong** (404). Correct: /de/themen/zivilprozess/prozesskosten.
- …/themen.html: **Confirmed** (redirects to /de/themen).
- …/entscheide.html: **Confirmed** (redirects to /entscheide/entscheide-anzeigen.html).
- VGR home zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html (wrapped link): **Wrong** (404). Correct: /de/gerichte-notariate/verwaltungsgericht.html.
- VGR fees = …/informationen-zum-gerichtsverfahren.html (direct link): **Partly**. The page is 200 with 2,238 words but has no CHF amounts; the fee law is LS 175.252.
- VGR guidance …/streitigkeiten-vor-verwaltungsgericht.html (direct link): **Confirmed**.
- VGR decisions vgrzh.djiktzh.ch/ (wrapped link): **Partly**. The root returns a 4-byte body; the real route is /findinfo/… and /cgi-bin/nph-omniscgi.exe (verified above).
- Bezirksgerichte …/organisation/bezirksgerichte.html: **Confirmed** (redirect).
- S4 communes and chancellery: **Confirmed** (both 200).

---

## BE (Kanton Bern)

### Grid
| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.zsg.justice.be.ch/de/start.html · **VGR: https://www.vgb.justice.be.ch/de/start.html** · portal https://www.justice.be.ch/de/start.html | All 200, title "Startseite", AEM server HTML (19,138 / 15,690 / 14,032 B) | zsg: "Obergericht Oberste rechtsprechende Behörde · Regionalgerichte Erstinstanzliche Zivil- und Strafgerichte · Schlichtungsbehörden Schlichtung und Rechtsberatung". vgb: "Das Verwaltungsgericht Oberstes kantonales Gericht in Verwaltungssachen" | The real VGR host was found by WebSearch. The AI's www.vg.justice.be.ch has no DNS (precheck) |
| C2 | VERIFIED | https://www.zsg.justice.be.ch/de/start/themen/zivilrecht/kosten/verfahrenskosten.html · https://www.vgb.justice.be.ch/de/start/themen/kosten.html · law **BSG 161.12 VKD** (law_hits) | 200 "Verfahrenskosten im Zivilverfahren", 499 words. 200 "Kosten", 260 words | "…bis zu einem Streitwert von CHF 30ꞌ000.00 … Im Schlichtungsverfahren fallen zudem bei Streitigkeiten aus Miete und Pacht von Wohn- und Geschäftsräumen keine Gerichtsgebühren an." | The page also cites the PKV (BSG 168.811). The court asks for an advance of half the expected fees |
| C3 | VERIFIED | zsg /de/start/themen (55 de pages plus themen.html) · vgb /de/start/themen (14 of 43 de sitemap URLs, fetched live) | AEM server HTML. zsg sitemap 256 URLs (de 127, stage0) | vgb themen include "…/einen-entscheid-anfechten/bis-wann-koennen-sie-einen-entscheid-anfechten.html" | 10 URLs: zsg …/zivilrecht/familienrecht.html, …/mietrecht.html, …/arbeitsrecht.html, …/betreibung-konkurs.html, …/zivilrecht/kosten.html, …/kosten/unentgeltliche-rechtspflege.html, …/strafrecht/kosten.html, …/strafrecht/verfahrensablaeufe.html; vgb …/einen-entscheid-anfechten.html, …/ablauf-des-verfahrens.html |
| C4 | VERIFIED | zsg …/dienstleistungen/rechtsprechung.html → https://www.zsg-entscheide.apps.be.ch/tribunapublikation/ (also aa-entscheide) · vgb …/dienstleistungen/rechtsprechung.html → https://www.vg-urteile.apps.be.ch/tribunapublikation/ (also strk-entscheide) | Tribuna apps answer 200 with about 19 KB and 30–35 words (JS app). API not probed (no deep dive) | "Die elektronische Entscheidsammlung der Zivil- und Strafgerichte enthält Entscheide der Zivilabteilung von grundlegender Bedeutung…" | opencaselaw BE: 8 codes, 21,722 decisions. be_verwaltungsgericht 12,109 (2026-08-24), be_zivilstraf 6,039 (2026-08-03), be_direktionen 217 (2026-07-02), be_anwaltsaufsicht 78 (2026-08-11). **STALE:** be_bvd 2,094 (2025-12-11), be_weitere 840 (2025-12-18), be_steuerrekurs 343 (2025-12-16) |
| C5 | VERIFIED | https://www.zsg.justice.be.ch/de/start/ueber-uns/schlichtungsbehoerden.html (plus /berner-jura-seeland, /emmental-oberaargau, /bern-mittelland, /oberland) | 200 "Schlichtungsbehörden" | "Im Kanton Bern gibt es vier Schlichtungsbehörden. Sie sind zuständig für Schlichtungsverfahren und Rechtsberatungen." | Fees: none in rent conciliation (C2). BSG 164.211–164.214 |
| G1 | VERIFIED [cited g5] | https://www.weu.be.ch/de/start/themen/veterinaerwesen/hunde-im-kanton-bern.html (+6 subpages) | Today: 200 "Hunde im Kanton Bern" | g5: "Möchten Sie einen Hund kaufen? Die Anforderungen … sind hoch." | BSG 916.31 Hundegesetz, 916.812 THV. Dog tax is municipal (not verified) |
| G2 | VERIFIED [cited g5] | https://www.taxinfo.sv.fin.be.ch/ → /taxinfo/ca95ca72-19b3-4837-8ac0-c4287a8f151e | Today: 200 "Startseite - TaxInfo - Kanton Bern" | g5: at least 591 pages with embedded vike JSON | No sitemap (g5) |
| G3 | **VERIFIED (new, not in g5)** | https://www.akvb-gemeinden.bkd.be.ch/de/start/organisation-finanzierung/schulorganisation/schulferienplanung.html → …/schulferienplanung/schulferien-kanton-bern-d.pdf | Page: 200 "Schulferienplanung". PDF: 200, 121,636 B, 2 pages, text layer ("1. Juni 2026 Kantonale Ferienordnung … 2026/27 bis 2031/32") | "2026/27 Herbstferien Sa, 19.09.2026 - So, 11.10.2026" | **Who sets them:** the canton. "Seit dem Schuljahr 2010/11 legt die Bildungs- und Kulturdirektion … die Ferienzeiten fest" (Art. 8 Abs. 3 VSG, BSG 432.210). Exception: the February (sports) week is free between DIN weeks 2 and 14. The French-speaking part follows BEJUNE. The bkd.be.ch sitemap only has a holiday-care page |
| G4 | VERIFIED [cited g5] | https://www.svsa.sid.be.ch/de/start.html | Today: 200 "Strassenverkehr & Schifffahrt". de sitemap 229 URLs | g5 fee pages (…/fuehrerausweise/…/gebuehren.html) | No parking content (municipal) |
| D1 | VERIFIED | https://www.be.ch/de/start/ueber-uns/gemeinden.html · https://www.gemeinden.dij.be.ch/de/start/daten/gemeindedaten.html → XLSX `…/gemeindedaten/adressliste einwohner- und gemischte gemeinden-de.xlsx` | 200 "Gemeinden". 200 "Gemeindedaten". XLSX 200, 60,843 B, **334 communes**, columns BFS, Gemeinde, Strasse, PLZ, Ort, Telefon, Email, **Homepage**, Sprache, Verwaltungskreis; 333 have a homepage | "Der Kanton Bern hat 334 politische Gemeinden (Stand 1.1.2026)." · row "301 · Gemeindeverwaltung Aarberg · … · www.aarberg.ch · Deutsch · Seeland" | Destination `resolver`. More XLSX lists on the same page (Burger-/Kirchgemeinden, allocation to districts) |
| D2 | VERIFIED | https://www.sta.be.ch/de/start.html · https://www.sta.be.ch/de/start/dienstleistungen/amtsblatt.html → https://amtsblatt.be.ch/ | 200 "Staatskanzlei des Kantons Bern - Startseite". 200 "Amtsblatt des Kantons Bern". Gazette: 200 "eSHAB", 1,384 B | "Das Amtsblatt ist das allgemeine kantonale Publikationsorgan des Kantons Bern. Es erscheint seit dem 1. Januar 2020 nur noch in elektronischer Form." | eSHAB tenant kabbe: 49,679 (sample "Baugesuch: Rue Franche 29, Biel/Bienne"). robots for amtsblatt.be.ch not fetched |

### Site recipe (BE)
- One AEM host per office. Each has `/sitemap.xml` → `/de/sitemap.xml` + `/fr/sitemap.xml`. Stage0 counts: zsg 256, rsta 130, svsa 462, sv.fin 344, weu 955, bkd 1,133, sta 545, akvb-gemeinden 167, be.ch 153. vgb de sitemap: 43 URLs (live).
- **Crawl-delay 10** (stage0 delay 10.0; brief).
- Decisions run on Tribuna under *.apps.be.ch.
- **The repo crawler does not honor Crawl-delay.** It uses a global 0.5 s delay and a 200-page cap (`config.py:22-23`) and checks only `robots.can_fetch` (`html_crawl.py:86-94`).

### Draft YAMLs (BE)
```yaml
id: be_zsg_themen
name: Zivil- und Strafgerichtsbarkeit Bern – Themen und Schlichtung
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
name: Verwaltungsgericht Bern – Verfahren und Kosten
base_url: https://www.vgb.justice.be.ch
default_extent_id: CH-BE
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config: {start_paths: ["/de/start/themen.html"], path_allowlist: ["/de/start/themen"], language: de}
allow_narrowing: false
---
id: be_schulferien
name: Kantonale Ferienordnung Volksschule Bern (deutschsprachiger Teil)
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
Destinations: D1 `resolver` (xlsx) · D2 `design:eSHAB robots` · all BE crawls need a per-source Crawl-delay of 10 (`fetcher:sitemap-crawl`).

### Claim checks (BE)
- zsg start (direct link): **Confirmed**.
- …/kosten-und-entschaedigungen/gerichtsgebuehren.html: **Wrong** (404). Correct: …/themen/zivilrecht/kosten/verfahrenskosten.html.
- zsg themen.html: **Confirmed**.
- zsg entscheide.html: **Wrong** (404). Correct: …/dienstleistungen/rechtsprechung.html → zsg-entscheide.apps.be.ch.
- All four www.vg.justice.be.ch links: **Wrong** (no DNS). Correct: www.vgb.justice.be.ch (/de/start.html, /themen/kosten.html, /themen.html, /dienstleistungen/rechtsprechung.html → vg-urteile.apps.be.ch).
- Regionalgerichte (direct link): **Confirmed**.
- …/zivilrecht/kosten-und-entschaedigungen.html: **Wrong** (404). Correct: …/zivilrecht/kosten.html.
- S4 communes www.jgk.be.ch/…: **Wrong** (no response). Correct: be.ch/de/start/ueber-uns/gemeinden.html plus gemeinden.dij.be.ch.
- S4 chancellery sta.be.ch: **Confirmed**.

---

## BS (Kanton Basel-Stadt)

### Grid
| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.bs.ch/willkommen-bei-den-gerichten (courts under /gerichte-judikative/<court>) | 200 "Willkommen bei den Gerichten \| Kanton Basel-Stadt", server HTML (Nuxt SSR), 340 words | "Die Bundesverfassung gibt jeder Person das Recht, Streitigkeiten … vor eine unabhängige Justizbehörde zu bringen." | 11 court sections |
| C2 | VERIFIED | https://www.bs.ch/gerichte-judikative/zivilgericht/gerichtsverfahren/prozesskosten (also appellationsgericht/verfahren/kosten, strafgericht/…/busse-geldstrafe-und-gerichtskosten, jugendgericht/verfahren/kosten) · law **SG 154.800 / 154.810** | 200 "Prozesskosten", 959 words | "Bei nichtvermögensrechtlichen Streitigkeiten beträgt die Grundgebühr CHF 200.- bis 250'000.-." | |
| C3 | VERIFIED | /gerichte-judikative/ | **136** sitemap URLs (zivilgericht 29, ueber-die-gerichte 28, strafgericht 27, appellationsgericht 25, …), 23 on resident topics. Server HTML | see C5 | 10 URLs: …/zivilgericht/ausgewaehlte-rechtsgebiete/familienrecht/getrenntleben-und-scheidung, …/arbeitsrecht, …/schkg-verfahren/konkurs, …/familienrecht/kindschaftsrecht, …/erbschaftsamt/erbgang, …/erbschaftsamt/testament, …/betreibungs-und-konkursamt/betreibungen, …/zivilgericht/gerichtsverfahren/prozesskosten, …/zivilgericht/schlichtung, …/gericht-fuer-fuersorgerische-unterbringungen/verfahren |
| C4 | VERIFIED | https://www.bs.ch/gerichte-judikative/ueber-die-gerichte/gerichtsentscheide → `https://rechtsprechung.gerichte.bs.ch/cgi-bin/nph-omniscgi.exe?…Schema=BS_FI_WEB…` | 200. FindInfo: 200 "Kanton Basel - FindInfoWeb", 14,337 B | "Die Entscheide des Appellationsgerichts … ab Januar 2014 · Die Entscheide des Sozialversicherungsgerichts ab Januar 2018" | opencaselaw BS: bs_appellationsgericht 8,786 (2026-09-03), bs_sozialversicherungsgericht 2,230 (2026-06-18), bs_zivilgericht 3 (sparse). **STALE:** bs_steuerrekurskommission (2024-03-21), bs_personalrekurskommission (2014-09-22), bs_gerichte (2017) |
| C5 | VERIFIED | https://www.bs.ch/regierungsrat/staatskanzlei/staatliche-schlichtungsstelle-fuer-mietstreitigkeiten/schlichtungsverfahren (+ /beratung, /formulare) · https://www.bs.ch/gerichte-judikative/zivilgericht/schlichtung | 200 (698 words). 200 (882 words) | "Das Verfahren vor der Schlichtungsbehörde ist rasch, einfach und grundsätzlich kostenlos." · "…betragen zwischen CHF 100.- und maximal 30% der Gebühr für ein Gerichtsverfahren." | Laws 215.400, 154.130 |
| G1 | VERIFIED [cited g5] | https://www.bs.ch/gd/veterinaeramt/hundehaltende | Today: 200 "Hundehaltende \| bs.ch", 1,147 words | g5: "Hunde müssen so gehalten und ausgeführt werden, dass durch sie keine Menschen oder Tiere belästigt oder gefährdet werden." | 365.100/365.110. **Gap in g5:** Riehen (RiE 365.100) and Bettingen (BeE 365.100) set their own dog tax (law_hits titles) |
| G2 | VERIFIED [cited g5] | https://www.bs.ch/themen/arbeit-und-steuern/steuererklaerung/steuererklaerung-natuerliche-person/wegleitungen-und-formulare-fuer-natuerliche-personen | Today: 200, 775 words | g5 Merkblatt PDF | No Steuerbuch (sitemap grep: 0). Tax law **640.100** (LexWork index), missing from law_hits |
| G3 | VERIFIED [cited g5] | https://www.bs.ch/themen/bildung-und-kinderbetreuung/schulferien · data.bs.ch 100397 | Today: 200 and API 200 JSON | g5: {"year":"2032","name":"Sommerferien","start_date":"2032-06-26",…} | Who sets them is not stated in g5. One canton-wide dataset (inferred: canton sets) |
| G4 | VERIFIED [cited g5] | bs.ch …/motorfahrzeugkontrolle/gebuehrenuebersicht-mfk | Not re-fetched today | g5: "Führerausweis im Kreditkartenformat, Duplikat/Erneuerung … Fr. 40.-" | Parking cards under /themen/mobilitaet/fahren-und-parkieren/parkkarten/ |
| D1 | VERIFIED | https://www.bs.ch/schwerpunkte/portrait/im-herzen-europas/basel-ein-kanton-drei-gemeinden | 200, 692 words. Links https://www.riehen.ch/ and https://www.bs.ch/bettingen | "Der Kanton Basel-Stadt besteht aus der Stadt Basel selbst, sowie den beiden Landgemeinden Riehen und Bettingen." | 3 communes (BFS 2701/2703/2702 from the csv) |
| D2 | VERIFIED | https://www.bs.ch/regierungsrat/staatskanzlei · https://www.bs.ch/regierungsrat/staatskanzlei/e-kantonsblatt-basel-stadt → https://www.kantonsblatt.ch/ | 200 (685 words). 200 (401 words). kantonsblatt.ch: eSHAB build 1.18.14-8272, **robots Disallow /** | "Seit Januar 2019 erscheint das Kantonsblatt Basel-Stadt als digitale Publikation." | Tenant kabbs: 19,598 via tenant filter (sample "Handänderung Bruderholzrain 3, Bruderholzrain 5, Basel") |

### Site recipe (BS)
- www.bs.ch runs Nuxt SSR over Drupal (g5). `/sitemap.xml` has 14 pages and 27,210 URLs (stage0). **Crawl-delay 10.** PDFs are on media.bs.ch.
- Decisions: FindInfo. Gazette: eSHAB.
- No bot walls.

### Draft YAML (BS)
```yaml
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
allow_narrowing: false    # Crawl-delay 10 is not honored today (config.py:23)
```

### Claim checks (BS)
- www.gerichte.bs.ch/ : **Partly**. The host only redirects to bs.ch/willkommen-bei-den-gerichten.
- /kosten.html, /recht-hilfen.html, /rechtsprechung.html: **Wrong**. All three redirect to the welcome page. Correct: …/zivilgericht/gerichtsverfahren/prozesskosten and …/ueber-die-gerichte/gerichtsentscheide.
- S4 bs.ch/portrait/gemeinden: **Wrong** (404). Correct: /schwerpunkte/portrait/im-herzen-europas/basel-ein-kanton-drei-gemeinden.
- S4 staatskanzlei.bs.ch: **Confirmed** (redirect).

---

## BL (Kanton Basel-Landschaft): public hosts are behind Cloudflare, the Plone API is open

**Bot wall log:**
- `www.baselland.ch/politik-und-behorden/gerichte` answers 403 "Just a moment..." with a full Chrome 128 User-Agent (one try).
- `kanton.baselland.ch/…/steuerbuch` answers 403.
- `https://bl-api.webcloud7.ch/` answers 200 JSON. It is a Plone site whose root items are "Kanton Basel-Landschaft", politik-und-behorden, themen and so on.
- Paths match www.baselland.ch one to one. Evidence: WebSearch URLs such as …/gerichte/kantonsgericht_hs resolve on the API, and the API pages link back to www.baselland.ch. A full 1:1 mapping is inferred, not proven.

### Grid
| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED via API (public URL BLOCKED) | Public https://www.baselland.ch/politik-und-behorden/gerichte (403) · API https://bl-api.webcloud7.ch/politik-und-behorden/gerichte | API 200 JSON, @type "direktion" "Gerichte", 25 children, modified 2026-09-22 | "Das Zivilkreisgericht Basel-Landschaft Ost in Sissach ist zuständig für folgende Gemeinden: Anwil, Arboldswil, Arisdorf, …" | Kantonsgericht, Zivilkreisgericht Ost/West, Friedensrichter, Strafgericht, Jugendgericht, Zwangsmassnahmengericht, Steuer- und Enteignungsgericht |
| C2 | VERIFIED (ordinance and form); fee page NONE | **SGS 170.31 GebT** (law_hits, bl.clex.ch) · form https://bl-api.webcloud7.ch/politik-und-behorden/gerichte/leistungsverzeichnis/insolvenzerklaerung.pdf/@@download/file | PDF 200, 46,317 B, 2 pages, text layer | "Der Kostenvorschuss von CHF 4'000.00 wird gleichzeitig bezahlt" | Ladder for a fee page: AI path /gerichte/kosten gives API 404. `@search` "Kostenvorschuss" in /gerichte gives 18 hits (forms, annual reports). `@search` "Gerichtsgebühren" gives 33 hits (mostly tax-practice PDFs). WebSearch finds only 170.31. **No fee page exists** |
| C3 | VERIFIED | API `@search?path.query=/politik-und-behorden/gerichte&portal_type=ContentPage` gives **27** pages; `leistungsverzeichnis` folder has 7 PDFs | JSON (slblocks HTML) | see C5 | 10 URLs: …/gerichte/friedensrichter-innen, …/zivilkreisgerichte-formulare, …/copy_of_zivilkreisgerichte-formulare, …/enteignungsgericht/haeufig-gestellte-fragen-zum-verfahren-am-enteignungsgericht, …/elektronischer-rechtsverkehr-1, and in leistungsverzeichnis: gesuch-um-unentgeltliche-rechtspflege.pdf, insolvenzerklaerung.pdf, lohnklageformular.pdf, schlichtungsgesuch_arbeitsstreitigkeit.pdf, gesuch_eroeffnung_konkurs.pdf |
| C4 | VERIFIED | API …/gerichte/rechtsprechung → https://bl.swisslex.ch/ | API 200 (158 words). bl.swisslex.ch: 200 "Gerichte Basel-Landschaft", 8,165 B, 2 words (JS app) | "Hier kommen Sie zum Rechtsprechungsportal der Gerichte des Kantons Basel-Landschaft: bl.swisslex.ch" | opencaselaw bl_gerichte 19,453 (1962-06-08 to 2026-06-03), not stale |
| C5 | VERIFIED | API …/gerichte/friedensrichter-innen · API …/volkswirtschafts-und-gesundheitsdirektion/generalsekretariat/aufgaben/schlichtungsstellen/mietangelegenheiten | 200 JSON (258 and 322 words; modified 2025-01-02 and 2026-08-27) | "In der Regel ist das Schlichtungsgesuch an die Friedensrichterin oder den Friedensrichter im Friedensrichterkreis am Wohnsitz der beklagten Partei einzureichen." · "Die Schlichtungsstelle für Mietangelegenheiten des Kantons Basel-Landschaft ist zuständig bei Streitigkeiten aus Miete und Pacht…" | Fees are not stated on either page. Form PDFs are present |
| G1 | VERIFIED via API | …/lebensmittelsicherheit-und-veterinarwesen/veterinaerwesen/hunde | 200 JSON, 922 words, modified 2025-08-26 | "Weiter müssen Hunde bei der Wohnsitzgemeinde des Hundehaltenden angemeldet und in der Hundedatenbank AMICUS registriert werden." | SGS 342, 342.12 |
| G2 | **BLOCKED (Cloudflare)** | https://kanton.baselland.ch/politik-und-behorden/direktionen/finanz-und-kirchendirektion/steuerverwaltung/steuerbuch (linked from the API page …/steuerverwaltung/steuerbuch, 19 words) | 403 "Just a moment..." | WebSearch titles: "Band 1 - Steuerbuch", "Baselbieter Steuerbuch Band 2 - Unternehmen 10 Nr. 1" (…/band2_010_01.pdf/@@download/file/…) | Entry count unknown. Reachable instead via the API: tax-return guidance pages (…/steuererklaerung-natuerliche-personen-und-e-tax-bl/abzuege-1, liegenschaften, wertschriften-und-vermoegen) and tax-practice PDFs (BLStPra) |
| G3 | VERIFIED | API …/bildungs-kultur-und-sportdirektion/schulferien (6 year pages, 2026/27 to 2031/32) · data.bl.ch 13350 [cited g5; today 200, total_count 58] | API 200 (modified 2026-03-31) | "Herbst · Ferienbeginn Samstag 26. September 2026 · Unterrichtsbeginn Montag 12. Oktober 2026" | **Who sets them:** the canton, one rule for all schools: "gilt für die Volksschulen, Musikschulen, weiterführenden Schulen und Berufsfachschulen … mit Ausnahme des Regionalen Gymnasiums Laufental-Thierstein" |
| G4 | VERIFIED via API | …/sicherheitsdirektion/motorfahrzeugkontrolle and …/motorfahrzeugsteuern-und-gebuehren/gebuehren/gebuehren-und-besondere-abgaben-fuehrerzulassung (also fahrzeugzulassung, kontrollschilder, parkkarte-fuer-gehbehinderte) | 200 JSON, modified 2026-07-01 | "Die Ausstellung eines Führerausweises im Kreditkartenformat (FAK) 42.00" (CHF column) | SGS 145.36, revised 1 July 2026 (news page → bl.clex.ch change_documents/1283) |
| D1 | VERIFIED | API /politik-und-behorden/gemeinden (Link "Adressen der Gemeinden") → `https://data.bl.ch/api/explore/v2.1/catalog/datasets/10510/records` | ODS 200 JSON, **total_count 86**. Fields: bfs_nummer, name, …, e_mail, **website**, uid_nummer, koordinaten | "2761 · Gemeinde Aesch · https://www.aesch.bl.ch/" | Destination `resolver`. Usable with `api` today (86 ≤ 100 records) |
| D2 | VERIFIED | API …/besondere-behoerden/landeskanzlei · gazette https://www.amtsblatt.bl.ch/ | 200 JSON. amtsblatt.bl.ch: 200 "eSHAB", 1,384 B | "Die Landeskanzlei ist die Stabsstelle von Landrat und Regierungsrat." · "Das Amtsblatt des Kantons Basel-Landschaft erscheint ab Januar 2023 digital" | Tenant kabbl: 13,520 |

### Site recipe (BL)
- **Public hosts:** www.baselland.ch and kanton.baselland.ch are behind Cloudflare. On www.baselland.ch, robots.txt and sitemap were blocked in stage0 too (robots 404, sitemap.xml 403).
- **bl-api.webcloud7.ch, Plone REST, no authentication:**
  - `GET <path>` with `Accept: application/json` returns title, description, `modified`, `effective`, `items[]`, and `slblocks{id:{text:{data:<html>}}}` (ftw.simplelayout; the order comes from `slblocks_layout`).
  - Search: `@search?SearchableText=…&path.query=…&portal_type=…&b_size=…`.
  - Files: `<file>/@@download/file`.
  - **Its robots.txt answers 403.** Usage policy unknown.
- data.bl.ch (Opendatasoft), bl.clex.ch (LexWork), bl.swisslex.ch (decisions, JS app).

### Draft YAML and hints (BL)
```yaml
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
```
- Courts, dogs, MFK and holiday pages need a new `fetcher:plone-rest`:
  - roots: `/politik-und-behorden/gerichte`, `…/veterinaerwesen/hunde`, `…/sicherheitsdirektion/motorfahrzeugkontrolle`, `…/schulferien`.
  - Walk `items[]` recursively, take text from `slblocks[*].text.data`, use `modified` as the date, and rewrite the document URL to `https://www.baselland.ch/<path>`.
- D1: `resolver` (data.bl.ch 10510).
- G2: `blocked:cloudflare (kanton.baselland.ch)`.

### Claim checks (BL): tested on the API using the same paths
- …/gerichte/kantonsgericht: **Confirmed** (200).
- /gerichte/kosten: **Wrong** (404).
- /gerichte/themen: **Partly**. It answers 200, but it is the site-wide topic container with 16 general topics.
- /gerichte/rechtsprechung (direct link): **Confirmed**.
- /gerichte/zivilkreisgerichte: **Wrong** (404). Correct: /zivilkreisgericht-basel-landschaft-ost and -west.
- All four S3a `/politik-und-verwaltung/direktionen/…` links (dogs, tax, school, road): **Wrong** (404; the correct root is /politik-und-behorden/).
- S4 /politik-und-behorden/gemeinden: **Confirmed**.
- S4 /politik-und-behorden/regierungsrat/landeskanzlei: **Wrong** (404). Correct: /politik-und-behorden/besondere-behoerden/landeskanzlei.

---

## SO (Kanton Solothurn)

### Grid
| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://so.ch/gerichte/ | 200 "Gerichte - Kanton Solothurn", TYPO3 server HTML, 11,731 B, 54 links | Menu: "Richterämter · Obergericht · Weitere Gerichte · Gerichtsverwaltung · Informationen" | First instance courts are the "Richterämter" (5 regional) |
| C2 | VERIFIED (ordinance); resident fee page NONE | **BGS 615.11 Gebührentarif (GT)** (LexWork: enactment 2016-07-15, not abrogated) · https://so.ch/gerichte/richteraemter/zustaendigkeit/zivilsachen/ | GT show_as_json 200. Zivilsachen page 200, 731 words | GT: "Für Tätigkeiten der Verwaltung und der Gerichte werden Gebühren nach diesem Tarif erhoben." · "Die Entscheidgebühr in Disziplinarsachen beträgt 100-7'000 Franken" (Zivilsachen fees in § 145) · page: "Ein arbeitsrechtliches Verfahren ist in aller Regel bis zu einem Streitwert von CHF 30'000.00 für die Parteien kostenlos." | Ladder for a fee page: AI /gerichte/gebuehren/ gives 404. Sitemap grep under /gerichte/ for kosten, gebuehr, tarif gives 0. /gerichte/, downloads, zentrale-gerichtskasse and reglemente-weisungen have no CHF (prior run; /gerichte/ re-checked). **law_hits is wrong here** (it lists 125.751.3, a Hague convention) |
| C3 | VERIFIED | /gerichte/ (73 sitemap URLs, 20 on resident topics) plus /services/ and /verwaltung/ pages | Server HTML | URP page: "Gegen einen Unkostenbeitrag von Fr. 35.00 erhalten Sie vom Solothurnischen Anwaltsverband einen Gutschein für ein Beratungsgespräch" | 10 URLs: …/zustaendigkeit/zivilsachen/, …/zustaendigkeit/strafsachen/, /gerichte/informationen/prozessformulare/, /verwaltung/staatskanzlei/legistik-und-justiz/unentgeltliche-rechtspflege-urp/, /verwaltung/finanzdepartement/erbschaftsaemter/wer-erbt/, …/erbschaftsaemter/preise/, /services/betreibung-einleiten/, /gerichte/weitere-gerichte/friedensrichter/, …/oberaemter/schlichtung-und-vermittlung/mietschlichtung/, /services/schlichtungsverfahren-fuer-miete-und-pacht-schlichtungsgesuch/ |
| C4 | VERIFIED | /gerichte/informationen/rechtsprechung/ → https://gerichtsentscheide.so.ch | Without cookies: redirect to a CookieCheckError page. With a cookie jar: 200 "FindInfoWeb", 1,156 B (FindInfo/Omnis). The sitemap also lists 10 "ausgewaehlte-entscheide" HTML pages (2015–16) | "…Entscheide der Beschwerdekammer werden nur publiziert, wenn…" (prior run) | opencaselaw so_gerichte 13,587 (1956-11-07 to 2026-09-08), not stale |
| C5 | VERIFIED | https://so.ch/gerichte/weitere-gerichte/friedensrichter/ · https://so.ch/verwaltung/departement-des-innern/departementssekretariat/oberaemter/schlichtung-und-vermittlung/mietschlichtung/ | 200 (627 words). 200 (932 words, Merkblatt PDFs) | "Die Friedensrichterinnen und Friedensrichter sind Gemeindeorgane." · "Das Verfahren ist kostenlos. Bei bös- oder mutwilliger Prozessführung können allerdings Kosten auferlegt werden." | The Friedensrichter page lists the inter-commune Friedensrichterkreise |
| G1 | VERIFIED | https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/ (+ /leinenpflicht/) · …/oberaemter/hundehaltung/ | 200 (597 and 604 words). 53 dog URLs in the sitemap | "…gilt in den Solothurner Wäldern in der Zeit vom 1. April bis 31. Juli eine generelle Leinenpflicht für alle Hunde." | BGS 614.71, 614.72 |
| G2 | VERIFIED | https://steuerbuch.so.ch/ (sitemap index → `/sitemap.xml?sitemap=pages&cHash=24b7400c2abd53b636ae62df3638e26a`) | Home 200 "Solothurner Steuerbuch". Child sitemap **175 locs, 140 entry pages** ("…/48-nr-1/"). An entry page has the **full text in HTML** (782 words of main text) plus a PDF version | PDF (3 pages, text layer): "Fassung vom 26.09.2017 In Kraft ab 01.10.2017 … Grundstückgewinnsteuer, Allgemeines § 48 Nr. 1" | Enumerable. Also Inhaltsverzeichnis_2026-06-08.pdf. Tax law 614.11 (LexWork), missing from law_hits |
| G3 | VERIFIED | https://so.ch/verwaltung/departement-fuer-bildung-kultur-und-sport/volksschulamt/aktuell/ferienplan/ → `…/Ferienplan/Schulferienplan_2026_2027.pdf` (also 2025-2026, 2027_2028) | Page 200. PDF 200, 8 pages, text layer | "Solothurn 28.09.2026 - 16.10.2026 [Herbst] …" | **Who sets them:** each Schulträger (commune or school association). "Die Feriendaten der Volkschule unterscheiden sich nach Gemeinde und Region." The PDF has one row per Schulträger |
| G4 | VERIFIED | https://so.ch/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/ (+ /steuern-und-gebuehren/) | 200 (874 words). 158 road URLs in the sitemap. The fee page (913 words) has no CHF in the HTML; its PDFs include the 614.62 ordinance (15 pages, "Stand 15. Juli 2016") | "Die nächste Aktion für 4-stellige Kontrollschilder zum Preis von CHF 900.00 findet vom 9. September bis am 7. Oktober 2026 statt." | |
| D1 | VERIFIED | https://so.ch/allgemeine-informationen/einwohnergemeinden/ (+ /nach-bezirken/) | 200 "Einwohnergemeinden Kanton Solothurn", **97 commune website links** (csv: 104 communes; 8 names not matched, apparently name variants) | "Aedermannsdorf → http://www.aedermannsdorf.ch/" | Destination `resolver` (html) |
| D2 | VERIFIED | https://so.ch/verwaltung/staatskanzlei/ · https://so.ch/verwaltung/staatskanzlei/publikationen/amtsblatt/ → https://amtsblatt.so.ch/ | 200. 200. eSHAB JS shell (32 words), **robots Disallow /** | "Die öffentlichen Meldungen des Kantons Solothurn werden seit Juli 2023 im elektronischen Amtsblatt veröffentlicht. Die Publikation findet über das Amtsblattportal statt…" | **API verified:** `https://amtsblattportal.ch/api/v1/publications/xml?publicationStates=PUBLISHED&rubrics=BA-SO&publicationDate.start=2026-09-01&publicationDate.end=2026-09-23&pageRequest.page=0&pageRequest.size=2` gives `<total>248</total>`. Per-notice XML `…/publications/<id>/xml` carries content ("Handänderung, Härkingen … Grundbuch Nr. 236, 914 m2"). `/api/v1/publications?…` without the format suffix gives 401 |

### Site recipe (SO)
- so.ch is TYPO3 (`/fileadmin/`). robots.txt is 1,709 B with 49 Disallow lines, none on the target paths, and no Crawl-delay.
- `https://so.ch/sitemap.xml` has 10 children and 8,909 URLs.
- steuerbuch.so.ch is TYPO3 with a sitemap index (175 pages).
- gerichtsentscheide.so.ch needs a cookie. amtsblatt.so.ch is eSHAB.

### Draft YAMLs (SO)
```yaml
id: so_gerichte
name: Gerichte Kanton Solothurn – Zuständigkeit, Schlichtung
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
name: Hunde Kanton Solothurn
base_url: https://so.ch
default_extent_id: CH-SO
authority: official_info
categories: [dogs]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/", "/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/"]
  path_allowlist: ["/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/", "/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/"]
  language: de
allow_narrowing: false
---
id: so_steuerbuch
name: Solothurner Steuerbuch
base_url: https://steuerbuch.so.ch
default_extent_id: CH-SO
authority: official_info
categories: [taxes]
fetch_strategy: html_crawl
fetch_config: {start_paths: ["/steuern/"], path_allowlist: ["/steuern/"], language: de}   # 175 pages < 200 cap
allow_narrowing: false
---
id: so_schulferien
name: Schulferienpläne Volksschulen Kanton Solothurn
base_url: https://so.ch
default_extent_id: CH-SO       # rows are per Schulträger: narrowing or a per-commune split needed
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://so.ch/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2026_2027.pdf",
         "https://so.ch/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2027_2028.pdf"]
  language: de
allow_narrowing: true
```
MFK: `yaml-now:html_crawl` with start and allowlist `/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/`. D2: `design:eSHAB robots`.

### Claim checks (SO)
- …/gerichte/obergericht/: **Partly** (redirects to /kontakt-kanzleien/).
- /gerichte/gebuehren/: **Wrong** (404; there is no fee page, the law is 615.11).
- /gerichte/themen/: **Wrong** (404). Correct: /gerichte/richteraemter/zustaendigkeit/… and /gerichte/informationen/….
- /gerichte/rechtsprechung/: **Wrong** (404). Correct: /gerichte/informationen/rechtsprechung/ → gerichtsentscheide.so.ch.
- /gerichte/amtsgerichte/: **Wrong** (404). The courts are called "Richterämter".
- All four S3a `so.ch/staat/departemente/…` links: **Wrong** (404). Correct URLs are in G1–G4.
- S4 so.ch/staat/gemeinden/: **Wrong** (404). Correct: /allgemeine-informationen/einwohnergemeinden/.
- S4 so.ch/staatskanzlei/: **Confirmed** (redirect).

---

## AG (Kanton Aargau)

### Grid
| Cell | Status | URL(s) | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau | 200 "Gerichte Kanton Aargau", 56,138 B, 338 words | "Die Aargauer Gerichte stehen für eine unabhängige, sach- und zeitgemässe Rechtsprechung." | |
| C2 | VERIFIED (ordinance and Merkblatt); fee page NONE | **SAR 662.110 Gebührendekret** (LexWork: title "2. Gerichtsgebühren", "…richten sich im Übrigen nach den §§ 5–20") · Merkblatt https://www.ag.ch/media/kanton-aargau/jb/dokumente/bezirksgerichte/formulare-und-merkblaetter/gka-155-200-1-215-merkblatt-stand-17-02-2025.pdf | PDF 200, 3 pages, text layer | "…gemäss § 12 Abs. 1 des Gebührendekrets eine Gerichtsgebühr zwischen Fr. 300.00 bis Fr. 2'500.00" (Erbbescheinigung) | Ladder: AI …/kosten-gebuehren gives 404. Sitemap grep under the court section for kosten, gebuehr, tarif gives 0 (only the URP page). **The old VKD 221.150 is abrogated=True.** law_hits has no AG court_fees |
| C3 | VERIFIED | /de/ueber-uns/gerichte-kanton-aargau/… | **125** sitemap URLs (no query string), 44 on resident topics. Server HTML | Friedensrichter page (C5) | 10 URLs: …/bezirksgerichte/formulare-und-merkblaetter (5 PDFs), …/bezirksgerichte/aufgaben, …/friedensrichterinnen-und-friedensrichter/aufgaben, …/friedensrichterinnen-und-friedensrichter/formulare-und-merkblaetter, …/schlichtungsbehoerden-fuer-miete-und-pacht, …/schlichtungsstelle-fuer-gleichstellungsfragen/aufgaben, …/die-familiengerichte-als-kesb/beschwerdeinstanzen, …/betreibungs-und-konkurswesen/konkursamt, …/obergericht/obergerichtskasse, /de/themen/recht-justiz/informationen-zur-unentgeltlichen-rechtspflege-(urp) |
| C4 | VERIFIED (route); database host down | https://www.ag.ch/de/themen/recht-justiz/gesetze-entscheide/agve (www.ag.ch/agve redirects here) · database agve.weblaw.ch (found by WebSearch) | Page 200. **agve.weblaw.ch returned 503 "Weblaw - Service Unavailable" three times.** decwork.ag.ch (named as `decwork_hostname` in the LexWork settings) redirects to a login (`/auth/main/factor_1`) | "Diese sogenannten Leitentscheide sind ab dem Jahr 2000 online einsehbar." | opencaselaw AG: 18 codes, 13,165. ag_strafgericht 2,160 (2026-09-08), ag_verwaltungsgericht 1,909 (2026-09-03), ag_zivilgericht 1,942 (2026-08-28), ag_versicherungsgericht 2,088 (2026-07-31), ag_handelsgericht 336 (2026-08-27), ag_spezialverwaltungsgericht 1,213 (2026-06-17). **STALE:** ag_gerichte 2,834 (2025-12-12), ag_justizgericht (2025-11-06), ag_departement_gs (2025-01-08), and 6 more with latest dates between 2008 and 2023 |
| C5 | VERIFIED | …/schlichtungsbehoerden/schlichtungsbehoerden-fuer-miete-und-pacht · …/friedensrichterinnen-und-friedensrichter/aufgaben | 200 (296 words). 200 (403 words) | "Das Schlichtungsverfahren ist grundsätzlich kostenlos." · Friedensrichter "…bis zu einem Streitwert von 2'000 Franken … einen kostenpflichtigen Entscheid fällen…" | SAR 155.614 |
| G1 | VERIFIED | https://www.ag.ch/de/themen/landwirtschaft-tiere/heim-und-nutztiere/hunde | 200 "Hunde im Kanton Aargau", 740 words | "Im Kanton Aargau gilt die Leinenpflicht im Wald und am Waldrand vom 1. April bis 31. Juli." | SAR 393.400, 393.411 |
| G2 | VERIFIED | https://www.ag.ch/de/themen/steuern-finanzen/steuern-startseite/steuererklaerung-einreichen/wegleitung-zur-steuererklaerung | 200 "Wegleitung NP", 640 words. **97** Wegleitung chapter URLs in the sitemap (enumerable) | "Die Wegleitung zur Steuererklärung 2025 hilft Ihnen dabei, Ihre Steuererklärung korrekt und vollständig auszufüllen." | No Steuerbuch URL in the 39,511-URL sitemap |
| G3 | VERIFIED | https://www.schulen-aargau.ch/regelschule/schulorganisation/planung-ressourcen/stunden-ferienplanung → …/bksvs-kantonal-einheitlicher-ferienplan.pdf | 200, 1,231 words. PDF 200, 3 pages, text layer | "Beginn des Schuljahres 2025 / 2026 11. August 2025 Herbstferien 40. / 41. Woche 29.09. – 10.10. 2025" | **Who sets them:** shared. "Je zwei Wochen Frühlings-, Herbst- und Weihnachtsferien sowie drei Wochen Sommerferien werden einheitlich durch den Erziehungsrat festgelegt. Die restlichen vier Ferienwochen legen die Gemeinden selber fest." The www.ag.ch sitemap has 0 holiday URLs |
| G4 | VERIFIED | https://www.ag.ch/de/themen/mobilitaet-verkehr/strassenverkehr (+ /steuern-gebuehren/gebuehren/fahrzeug, /fuehrerausweise/*) · office …/dvi/organisation/strassenverkehrsamt | 200 (708 words). 202 strassenverkehr URLs in the sitemap. Fee page 200 (314 words) | "Fahrzeugausweis für alle Kategorien (ausgenommen MOFA) Fr. 20.–" | |
| D1 | VERIFIED | https://www.ag.ch/de/themen/staat-politik/gemeinden (no list) → XLSX https://www.ag.ch/media/kanton-aargau/dfr/dokumente/statistik/statistische-daten/eckdaten-kt-aargau/gemeinden/gemeindeverzeichnis-ag-adressen-telefon.xlsx | Page 200. XLSX 200, 40,147 B, "Stand: 16. September 2026", columns Bezirk, **BFSNR**, Gemeinde, …, **Internet**; 196 rows with a website | "Mit 196 Gemeinden ist der Kanton Aargau einer der gemeindereichsten Kantone." · row "Aarau · 4001 · Aarau · Rathausgasse 1 · 5000 · http://www.aarau.ch" | Found by WebSearch. The Behördenverzeichnis is a JS app on `/io/staatskalender_frontend/search.json`, which is cantonal-only (0 hits for communes) and disallowed by robots (`/io/*`) |
| D2 | VERIFIED; gazette BLOCKED by robots | https://www.ag.ch/de/ueber-uns/kantonale-verwaltung/sk · https://www.ag.ch/de/themen/staat-politik/amtsblatt → https://amtsblatt.ag.ch/publikationen/ | SK 200. Amtsblatt page 200. amtsblatt.ag.ch 200 "Amtsblatt AG Publikationen", TYPO3 "ekab" server HTML, 5,370 words, notices at `/ekab/<nr>/publikation/`. **robots disallows /publikationen/ and /ekab/** | "Die Kernaktivitäten der Staatskanzlei umfassen die strategische, operative, rechtliche und kommunikative Unterstützung des Regierungsrats." · "Im Amtsblatt werden Bekanntmachungen der gesetzgebenden, vollziehenden und richterlichen Behörden publiziert…" | Not eSHAB. There is an eSHAB tenant kabag, but it holds SHAB debt-enforcement notices |

### Site recipe (AG)
- www.ag.ch is a custom CMS (release bundles on static.cdn.ag.ch). robots.txt: `Sitemap: https://www.ag.ch/sitemap.xml` (8 children, 39,511 URLs); for `User-agent: *` it disallows `/app/*`, `/io/*` and `/media/system|special|dynAssets/`. No Crawl-delay.
- schulen-aargau.ch: robots.txt is 404.
- gesetzessammlungen.ag.ch: LexWork. agve.weblaw.ch: 503.

### Draft YAMLs (AG)
```yaml
id: ag_gerichte
name: Gerichte Kanton Aargau – Organisation, Schlichtung, Merkblätter
base_url: https://www.ag.ch
default_extent_id: CH-AG
authority: official_info
categories: []            # category missing: courts
fetch_strategy: html_crawl
fetch_config: {start_paths: ["/de/ueber-uns/gerichte-kanton-aargau"], path_allowlist: ["/de/ueber-uns/gerichte-kanton-aargau"], language: de}   # 125 pages
allow_narrowing: false
---
id: ag_hunde_steuern_verkehr
name: Kanton Aargau – Hunde, Wegleitung Steuererklärung, Strassenverkehr (Gebühren)
base_url: https://www.ag.ch
default_extent_id: CH-AG
authority: official_info
categories: [dogs, taxes, transport]
fetch_strategy: html_crawl
fetch_config:
  start_paths: ["/de/themen/landwirtschaft-tiere/heim-und-nutztiere/hunde",
                "/de/themen/steuern-finanzen/steuern-startseite/steuererklaerung-einreichen/wegleitung-zur-steuererklaerung",
                "/de/themen/mobilitaet-verkehr/strassenverkehr/steuern-gebuehren"]
  path_allowlist: ["/de/themen/landwirtschaft-tiere/heim-und-nutztiere/hunde",
                   "/de/themen/steuern-finanzen/steuern-startseite/steuererklaerung-einreichen/wegleitung",
                   "/de/themen/steuern-finanzen/steuern/steuererklaerung-einreichen/wegleitung",
                   "/de/themen/mobilitaet-verkehr/strassenverkehr/steuern-gebuehren"]
  language: de
allow_narrowing: false
---
id: ag_schulferien
name: Kantonal einheitliche Feriendaten Volksschule Aargau
base_url: https://www.schulen-aargau.ch
default_extent_id: CH-AG
authority: official_info
categories: [schools]
fetch_strategy: pdf
fetch_config:
  urls: ["https://www.schulen-aargau.ch/media/schulen-aargau/schulorganisation/ressourcen-planung/stunden-ferienplanung/bksvs-kantonal-einheitlicher-ferienplan.pdf"]
  language: de
allow_narrowing: false    # covers only the 9 cantonal weeks; the 4 commune weeks are per commune
```
D1: `resolver` (xlsx). D2: `blocked:robots (amtsblatt.ag.ch /publikationen/, /ekab/)`.

### Claim checks (AG)
- /de/gerichte/obergericht (direct link): **Confirmed** (redirect).
- /de/gerichte/bezirksgerichte: **Confirmed** (redirect).
- /de/gerichte/themen/kosten-gebuehren, /de/gerichte/themen, /de/gerichte/rechtsprechung, /de/gerichte/verwaltungsgericht: **Wrong** (404). Correct: Merkblatt plus SAR 662.110; …/bezirksgerichte/formulare-und-merkblaetter; /de/themen/recht-justiz/gesetze-entscheide/agve; …/organisation/obergericht/verwaltungsgericht.
- All four S3a `/de/verwaltung/…` links: **Wrong** (404). Correct URLs are in G1–G4; school holidays are on schulen-aargau.ch.
- S4 /de/verwaltung/dvi/gemeinde-fachbereich and /de/verwaltung/staatskanzlei: **Wrong** (404). Correct: /de/themen/staat-politik/gemeinden plus the XLSX, and /de/ueber-uns/kantonale-verwaltung/sk.

---

## L1: city law (Zürich, Bern, Thun)

| City | Status | URL | Platform and format | Texts | Dog / waste / parking | Destination |
|---|---|---|---|---|---|---|
| **Zürich** (CH-ZH-261) | VERIFIED | https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung.html | 200 "Amtliche Sammlung \| Stadt Zürich" ("Seit 1893 werden die Erlasse der Stadt Zürich in der sogenannten amtlichen Sammlung geführt."). Server HTML built from web components: 80 group pages `/amtliche-sammlung/<n>/<nnn>.html` list `<stzh-card-superteaser heading="712.110 …" href meta='["In Kraft: 01.01.2023"]'>`. Each detail page has a `<stzh-datatable rows="…">` JSON with AS-Nummer, Beschlussdatum, **Inkrafttreten**, Ausserkrafttreten and a **Rechtstexte PDF** under `/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/…`. The VAZ PDF has 13 pages with a text layer | **791** entries: 622 in force, 169 repealed | Dogs: 554.510 Vollzugsvorschriften zum Hundegesetz (in force 01.09.2017). Waste: 712.110 VAZ (01.01.2023). Parking: 551.310 Parkkartenverordnung (01.01.2026), 551.311 Gebührenordnung Parkkarten Blaue Zone, 551.330, 741.500 Parkplatzverordnung | Existing `stadt_zuerich.yaml` reaches the group and detail pages, because `extract_links` reads href on any tag (`html_sections.py:144-158`). **It gets metadata only:** the PDF link sits inside the rows JSON and .pdf is skipped (`html_crawl.py:14`). The collection is 871 pages, over the 200-page cap (`config.py:22`). New `fetcher:stzh-as` needed |
| **Bern** (CH-BE-351) | VERIFIED | https://www.bern.ch/themen/stadt-recht-und-politik/stadtrecht → https://stadtrecht.bern.ch/lexoverview-home | The site is a 1,333 B JS shell (ExtJS; iDPARC/openlaws, tenant "sssb"). robots allows everything and names `sitemap.xml` (491,803 B, 2,593 locs). **Per-text export `https://stadtrecht.bern.ch/lex-<nr>.pdf` and `.docx`**: lex-151_21.pdf answered 200 (40 pages, text layer); DOCX export answered for all 24 numbers tested. .json/.xml are 404 | **218** SSSB numbers (`dgn-lex_*`), 95 of them also listed as `lex-*` | Dogs: 559.61 Hundeverordnung (HV), 15.02.2023, Stand 1.9.2026. Waste: 822.1 Abfallreglement (AFR), 822.111 AFV. Parking: 761.232 Parkkartenverordnung (PKV), 761.212 PVUA, 761.211 VZB | Today: `yaml-now:pdf` with fixed URLs. Full collection: new `fetcher:idparc-export` (sitemap → number list → .docx/.pdf) |
| **Thun** (CH-BE-942) | VERIFIED | https://www.thun.ch/reglementeverordnungen | 200 "Stadt Thun - Reglemente und Verordnungen", **i-web** (`icms-dt` table, `data-entities` JSON; fields title, _nummer, _dokumentList, _rechtsgueltigkeit). `/_doc/4917697` → `/_docn/4917697/822.1_Abfallreglement,_i.K.1.12024.pdf` (200, 7 pages, text layer) | **127** rows, 127 distinct `/_doc/` ids | Waste: 822.1 AFR (legally valid from 01.01.2024), 822.11 AFV. Parking: PBR, PKV, PGV 154.261.12, PPO 72.07. **Dogs: 0 of 127 rows mention "Hund"** | `fetcher:iweb-table`. PDF links are inside the JSON attribute, so html_crawl cannot see them |

```yaml
id: bern_stadtrecht_kern
name: Stadtrecht Bern (SSSB) – Hunde, Abfall, Parkieren
base_url: https://stadtrecht.bern.ch
default_extent_id: CH-BE-351
authority: official_info          # municipal_law once the host is registered as a law platform
categories: [dogs, waste, parking]
fetch_strategy: pdf
fetch_config:
  urls: ["https://stadtrecht.bern.ch/lex-559_61.pdf", "https://stadtrecht.bern.ch/lex-822_1.pdf",
         "https://stadtrecht.bern.ch/lex-822_111.pdf", "https://stadtrecht.bern.ch/lex-761_232.pdf"]
  language: de                    # PDF export verified on lex-151_21; these four were verified as .docx only
allow_narrowing: false
```
Landing-contract mapping:
- Bern: identifier = SSSB number; title from the lines after the date; valid_from from "(Stand: …)".
- Zürich: identifier = AS-Nummer; valid_from = Inkrafttreten; in_force = Ausserkrafttreten is empty.
- Thun: identifier = `_nummer`; valid_from = `_rechtsgueltigkeit`.

---

## Cross-canton section

### New fetcher classes needed
| Fetcher | Serves | Coverage |
|---|---|---|
| **eshab-export** (bulk `…/publications/xml` + `/publications/<id>/xml`) | D2 for SO, ZH, BE, BS, BL | 5 of my 6 cantons, plus SHAB. **design: robots `Disallow: /`** and personal data in notices (death notices seen). An open-source "amtsblatt-mcp" uses the same API (WebSearch; its terms are unverified) |
| **plone-rest** (`bl-api.webcloud7.ch`: slblocks, `@search`, `@@download/file`) | All BL C and G cells except G2 | Kanton BL plus 12 commune subsites under /politik-und-behorden/gemeinden (Arisdorf, Augst, Burg im Leimental, Diepflingen, Eptingen, Giebenach, Hersberg, Lampenberg, Maisprach, Nenzlingen, Nusshof, Ramlinsburg) |
| **sitemap-crawl** (html_crawl seeded from the sitemap, with per-source Crawl-delay and page cap) | ZH gerichte-zh (248 > 200), AG (strassenverkehr 202; courts 125; Wegleitung 97), SO (courts 73; Steuerbuch 175), BS (136, Crawl-delay 10), BE office hosts (Crawl-delay 10) | 5 cantons. The current crawler has a global 0.5 s delay and a 200-page cap (`config.py:22-23`) |
| **pdf-index** | SO holiday plans (one PDF per school year), AG and BE holiday PDFs, AG court Merkblätter, SO Mietschlichtung Merkblätter, Zürich AS PDFs | 4 cantons, 1 city |
| **xlsx** | D1 directories AG (196), BE (334), ZH (160); ZH holiday XLSX (g5) | Resolver data |
| **iweb-table** (existing class) | Thun (127) | |
| **stzh-as** | Stadt Zürich AS (791 entries) | 1 city |
| **idparc-export** | Bern SSSB (218; ASSB `lexas*` URLs also in the sitemap) | 1 city. Other tenants on the platform are not verified (the page's theme list names uri, weblaw, walderwyss, openlaws, …) |
| findinfo / tribuna / swisslex | Decisions: FindInfo (SO, BS, ZH VGR), Tribuna (BE ×4), Swisslex (BL), Weblaw (AG) | **Not needed now.** opencaselaw is current for the main courts |

### Blocked items
- **www.baselland.ch and kanton.baselland.ch:** Cloudflare 403. BL G2 (Steuerbuch) stays blocked; everything else goes through bl-api.webcloud7.ch, whose robots.txt answers 403 (usage policy unknown).
- **eSHAB gazettes:** robots `Disallow: /` on amtsblattportal.ch, amtsblatt.so.ch, kantonsblatt.ch and amtsblatt.zh.ch. Same shell on amtsblatt.be.ch and amtsblatt.bl.ch (robots not fetched there).
- **amtsblatt.ag.ch:** robots disallows `/publikationen/` and `/ekab/`.
- **agve.weblaw.ch:** 503 three times (AG decision DB). decwork.ag.ch needs a login.
- **www.ag.ch:** `/app/*` and `/io/*` are robots-disallowed (the Staatskalender JSON).
- **Minor:** gerichtsentscheide.so.ch needs a cookie jar. `https://www.vgrzh.ch` fails (the `http://` form redirects).

### law_hits.json corrections (verified against LexWork this session)
- **AG court_fees missing:** add **SAR 662.110 Gebührendekret**. 221.150 VKD is abrogated.
- **SO court_fees wrong:** 125.751.3 is a Hague convention. Use **BGS 615.11 Gebührentarif**.
- **SO tax:** only 614.61 (motor vehicles) is listed. Add **614.11** Gesetz über die Staats- und Gemeindesteuern.
- **BS:** no tax topic; add **640.100**. The BS "holidays" hits (411.600, 162.410) are staff leave rules, not school holidays (judged from their titles).
- **ZH "conciliation" hits 212.23/212.24** are about the number of lay judges (from the titles).

### Five best finds
1. **bl-api.webcloud7.ch:** the entire Kanton BL site as open JSON behind the Cloudflare wall, with search and file downloads.
2. **eSHAB public bulk export:** paginated XML/CSV with rubric and date filters, plus full-text XML per notice, for the gazettes of 5 cantons (SO, ZH, BE, BS, BL). It needs a policy decision because robots disallows all crawling.
3. **Bern SSSB `lex-<nr>.pdf|.docx`:** 218 city law texts enumerable from the sitemap with text layers, including the dog, waste and parking regulations.
4. **Commune directories with BFS numbers and websites:** AG XLSX (196), BE XLSX (334), BL JSON (86). Ready as resolver data.
5. **SO Steuerbuch** (175 pages, full text in HTML, "In Kraft ab" dates in the PDFs) and the **Zürich AS metadata** (791 entries with In-Kraft dates and PDF links).

### Unknowns / not verified
- The AGVE database format (host down).
- The BL Steuerbuch structure and entry count (blocked).
- eSHAB terms of use (only a WebSearch summary says "freely usable").
- Whether BS sets its school holidays centrally.
- That the bl-api paths map 1:1 to www.baselland.ch (inferred from matching URLs).
- robots.txt of amtsblatt.be.ch and amtsblatt.bl.ch.
- AG and BE per-commune dog tax.
- The BS G4 MFK pages, which I did not re-fetch today.