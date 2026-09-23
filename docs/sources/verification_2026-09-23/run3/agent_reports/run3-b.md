Group run3-b is done: all 77 cells for LU, UR, SZ, OW, NW, GL and ZG have an answer (74 VERIFIED, 2 partial, 1 NONE with its ladder). Every URL below was requested live today unless marked otherwise. Scripts and saved pages are in `<scratchpad>/run3-b/` (probe.py, batch.py, iweb.py, iwc.py, offline.py, eshab_*.py, plone.py, ods.py; pages/). All loops ran as Python scripts; no shell loops were used. SZ and GL were throttled to 5 s per request and answered 429 zero times.

## Headline finds
1. **Amtsblattportal serves 4 of my cantons' gazettes as JSON.** The tenants endpoint `https://amtsblattportal.ch/api/v1/tenants` lists 29 tenants. NW, OW, SZ and ZG have their own domains; LU, UR and GL are marked `external` (they publish elsewhere). Live counts of published notices in each canton's own rubrics: ZG 2,213, SZ 1,352, OW 753, NW 504. List call: `https://amtsblatt.<xx>.ch/api/v1/publications?publicationStates=PUBLISHED&tenant=kab<xx>&rubrics=<canton rubric codes>&pageRequest.page=N&pageRequest.size=N`; full text per notice at `/api/v1/publications/{id}/xml`. **robots.txt on every tenant domain is `Disallow: /`**, so this needs a terms-of-use decision first.
2. **The Zuger Steuerbuch has a Plone REST backend** at `https://wissen-backend.webcloud7.ch/steuerbuch` (@type Book, `@search` items_total 1,343). It is the same vendor as Kanton BL.
3. **SZ school holidays are an Opendatasoft dataset:** `data.sz.ch` `ferienplan-kanton-schwyz`, 90 records, CC BY 4.0. It works as a `yaml-now:api` source today.
4. **laburk.ch (Laboratorium der Urkantone) is one dog-guidance source for UR, SZ, OW and NW.**
5. **NW's dog tax is cantonal:** "Die Hundesteuer im Kanton NIdwalden beträgt CHF 120.00 pro Kalenderjahr" (the "NIdwalden" typo is on the page).

---

## LU (79 communes)
| Cell | Status | URL | Evidence | Sample | Notes / destination |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://gerichte.lu.ch/ | 200, 'Gerichte des Kantons Luzern - Kanton Luzern', server HTML 52,161 B, 44 links | "…und der Generalsekretär des Kantonsgerichts Luzern" | html_crawl; category missing: courts |
| C2 | VERIFIED | https://gerichte.lu.ch/rechtsgebiete/prozesskosten/zivilprozess/gerichtskosten + ordinance SRL 265 JusKV (srl.lu.ch API 200 JSON) | 200 'Gerichtskosten', HTML 41,961 B | "Bezirksgericht Streitwert Gebühr … bis 50'000.-- 1'500.-- bis 5'000.--" | yaml-now:html_crawl |
| C3 | VERIFIED | /rechtsgebiete/ehe_und_familie/scheidung/gerichtskosten, /rechtsgebiete/arbeit, /rechtsgebiete/schuldbetreibung_und_konkurs, /rechtsgebiete/unentgeltliche_rechtsauskunft, /rechtsgebiete/prozesskosten, /organisation/schlichtungsbehoerden/miete_pacht/Wichtige_Informationen_zum_Schlichtungsverfahren | all 200 HTML, 142–333 words | "Gemeinsames Scheidungsbegehren und vollständige Einigung Fr. 1'600.-- bis 2'500.--" | Sitemap has 103 /rechtsgebiete URLs (family 39, debt enforcement 41, costs 10, labour 7, 6 singles) plus 16 conciliation URLs. No inheritance page in the court sitemap. |
| C4 | VERIFIED | https://gerichte.lu.ch/recht_sprechung/lgve; per decision `/recht_sprechung/lgve/Ajax?EnId=11116` | 200, 86,976 B; the Ajax call returns 200, 20,966 B HTML | "Entscheiddatum: 23.12.2025 … LGVE: 2026 IV Nr. 5" | opencaselaw lu_gerichte 5,185, latest 2026-03-10: not stale. No feed seen. |
| C5 | VERIFIED | /organisation/schlichtungsbehoerden + the tenancy info page | 200 | "Das Schlichtungsverfahren ist grundsätzlich nicht kostenpflichtig (Art. 113 Abs. 2 ZPO)" | Justice of the peace per court district, plus boards for tenancy, labour and equality; law SRL 261. Guidance and fees both present. |
| G1 | VERIFIED | https://veterinaerdienst.lu.ch/hunde, /hunde/gesetzgebung | 200 HTML 35,970 B, 293 words | "Hundehalter müssen ihren Hund bei der Gemeinde anmelden und Hundesteuer bezahlen" | Law SRL 848 HuG and 849 HuV. The host's sitemap lists only 1 URL, so crawl the 7 /hunde links. |
| G2 | VERIFIED | https://steuerbuch.lu.ch/ + /xmlsitemap | sitemap 391 URLs with `<lastmod>` (band1 104, band2 72, band2a 78, band3 125, band4 11). Säule-3a entry 200, 107 KB, 2,726 words | "Voraussetzungen für einen Abzug von Beiträgen an die Säule 3a sind: Ordentliches Rentenalter…" | Enumerable through the sitemap. The entry's meta `article:modified_time` 2026-02-10 comes from last night's log, not re-checked. |
| G3 | VERIFIED | https://volksschulbildung.lu.ch/syst_schulen/ss_schulsystem/ss_syst_ferien + ferienplan_gemeinden_sj26_27.pdf (6 pages, text) + feriendaten_volksschulen_kt_luzern.pdf (2 pages, text) | 200 each | "Adligenswil 17.08.2026 03.07.2027 26.09.2026 – 18.10.2026 …" | **Communes set them inside a cantonal frame** ("insgesamt 14 Wochen Ferien … Herbst: zwei oder drei Wochen"); the per-commune PDF has one row per commune. |
| G4 | VERIFIED | https://strassenverkehrsamt.lu.ch/ + /Strassenverkehr/steuern_gebuehren/gebuehren_und_abgaben | 200, 282-URL sitemap | "Lernfahrausweis aller Kategorien … 50.00 CHF" | Law SRL 778 |
| D1 | VERIFIED | https://www.lu.ch/gemeinden | 200 'Die 79 Gemeinden des Kantons Luzern', 183 links | 79 commune links /gemeinden/wahlkreise/<kreis>/<commune>, with phone and e-mail (79 e-mail domains) | No website column; detail pages are 58-word stubs. Destination: resolver. Not in the www.lu.ch sitemap. |
| D2 | VERIFIED | https://www.lu.ch/verwaltung/staatskanzlei; gazette …/Publikationen_und_Gesetze/Kantonsblatt | 200 each | "Jahresabonnement Kantonsblatt Fr. 102.–" | **Print only (Galledia).** www.kantonsblatt.lu.ch had no connection (000); kantonsblatt.lu.ch redirects to the print page. LU is an `external` tenant (kablu). "Digital from 2028" comes only from news headlines, not an official page. |

**Site recipe:** hosts gerichte / steuerbuch / strassenverkehrsamt / volksschulbildung / veterinaerdienst / www .lu.ch, each with `/xmlsitemap` (201 / 391 / 282 / 497 / 1 / 129 URLs; gemeinden.lu.ch 91). robots 200 (stage 0). CMS uses `/-/media/` paths and a `notfound?item=…&site=` 404 pattern; that it is Sitecore is inferred, not checked. No rate limit seen.

```yaml
- id: lu-gerichte-guidance          # official_info, CH-LU, category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://gerichte.lu.ch/rechtsgebiete, https://gerichte.lu.ch/organisation/schlichtungsbehoerden], path_allowlist: [/rechtsgebiete/, /organisation/schlichtungsbehoerden/], language: de}
- id: lu-steuerbuch                  # official_info, CH-LU, taxes
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://steuerbuch.lu.ch/band1, https://steuerbuch.lu.ch/band2, https://steuerbuch.lu.ch/band2a, https://steuerbuch.lu.ch/band3, https://steuerbuch.lu.ch/band4], path_allowlist: [/band], language: de}
- id: lu-hunde                       # dogs
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://veterinaerdienst.lu.ch/hunde], path_allowlist: [/hunde], language: de}
- id: lu-schulferien                 # schools; per-commune rows need narrowing or one source per commune
  fetch_strategy: pdf
  fetch_config: {urls: [https://volksschulbildung.lu.ch/-/media/Volksschulbildung/Dokumente/syst_schulen/ss_schulsystem/schulferien/ferienplan_gemeinden_sj26_27.pdf, https://volksschulbildung.lu.ch/-/media/Volksschulbildung/Dokumente/syst_schulen/ss_schulsystem/schulferien/feriendaten_volksschulen_kt_luzern.pdf]}
- id: lu-strassenverkehrsamt         # transport
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://strassenverkehrsamt.lu.ch/Strassenverkehr/steuern_gebuehren], path_allowlist: [/Strassenverkehr/], language: de}
```
**Claim checks:** /organisation/kantonsgericht confirmed (200). /themen/gerichtsgebuehren, /themen, /entscheide and /organisation/bezirksgerichte are all wrong (404); the real pages are /rechtsgebiete/prozesskosten/…, /rechtsgebiete and /recht_sprechung/lgve. The first-instance court page /organisation/erstinstanzliche_gerichte is in the sitemap but was not probed. S3a: dogs, tax and road confirmed; holidays wrong (404), real page /syst_schulen/ss_schulsystem/ss_syst_ferien. S4: gem.lu.ch wrong (no DNS), real www.lu.ch/gemeinden. staatskanzlei.lu.ch partly right: it redirects to www.lu.ch/verwaltung/staatskanzlei.

---

## UR (19 communes); i-web
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.ur.ch/gerichtefs | 200 'Kanton Uri - Gerichte Kanton Uri', 16 KB, 949 words | "Obergericht des Kantons Uri +41 41 875 2267 … Landgericht Uri" | |
| C2 | VERIFIED (ordinance only) / NONE (resident page) | Law: rechtsbuch.ur.ch 2.3232 GGebR (in force 2022-10-01) and 2.3231 GGebV | LexWork JSON 200 | "In kostenpflichtigen Verfahren vor der Schlichtungsbehörde beträgt die Gebühr 200 Franken bis 2'000 Franken" | **Ladder for the missing page:** entry points (/gerichtefs only) → sitemap (287 URLs, no fee page) → site search `/suchen?query=` (results rendered by JS; same 16.7 KB page for every query) → services A-Z (794 services; "Gebühren" 3379 is an unrelated eazw.admin.ch link) → court publications (23 items, no tariff) → WebSearch site:ur.ch (only the GGebR PDF, decisions, Amtsblatt) → law_hits 2.3231/2.3232. |
| C3 | VERIFIED | /rechtsgebiete (i-web table, 6 services): /rechtsgebiete/3909 family, 3912 debt enforcement, 3914 legal aid, 3915 labour, 3917 other civil, 3918 conciliation | all 200 HTML, about 17 KB | "Das Familienrecht ist im zweiten Teil des Zivilgesetzbuches (ZGB) geregelt…" | Content is 1–2 paragraphs per page; 10 court paths in the sitemap. |
| C4 | VERIFIED | /rechtsprechung | 200, i-web `data-entities` table with **444** decision PDFs, newest 2026-08-30 | "2018_OG BI 18 6. Strafprozessordnung…" | fetcher:iweb-table. opencaselaw ur_gerichte 1,240, latest 2026-08-30: not stale. |
| C5 | VERIFIED | /rechtsgebiete/3918 'Schlichtung' | 200 | "Hier finden Sie Vorlagen und Informationen zum allgemeinen Verfahren vor Schlichtungsbehörde sowie zum Mietrecht" | Fees in GGebR Art. 4 (Fr. 200–2,000). A service "Paritätische Vertretung der Schlichtungsbehörde Uri" (dienst/6773) is listed but was not probed. |
| G1 | VERIFIED (law + shared guidance) | laburk.ch/kantonstierarzt/tierschutz/; laws 60.2111 Veterinärverordnung, 60.2113 Veterinärreglement | 200 HTML 2,216 words; LexWork 200 | "Die Datenbank für die Registrierung von im Kanton Uri gehaltenen Hunden ist AMICUS" | No dog page on ur.ch (no "Hund" in the sitemap or in the 794 services). Who levies dog tax in UR: not verified. |
| G2 | VERIFIED | /_rte/dienst/3869 → /_doc/437558 (np_wegltgsteuern2025.pdf) | PDF with text, 24 pages, 661 KB | Contents list: "Merkblatt über den privaten Gebäudeunterhalt…" | No Steuerbuch. Services "Natürliche Personen - Veranlagungspraxis" (3192) and "…Weisungen und Merkblätter" (3871) are listed but were not probed. Enumerable through i-web service pages. |
| G3 | VERIFIED | /_rte/dienst/3125 + /_doc/449362 (per commune, 2 pages, text) + /_doc/408844 (framework plan) | 200 | "Herbstferien SA, 03.10.2026 – SO, 18.10.2026" | **The Erziehungsrat sets a framework plan; the schools set their holidays** ("…auf dessen Grundlage die Schulen ihre Ferien bestimmen"). |
| G4 | VERIFIED | /verkehr/4372 (Amt für Strassen- und Schiffsverkehr), /verkehr/4378; fees /_rtr/publikation_4903 → Tarifordnung_2026.pdf | 21 pages, text | "Führerausweis im Kreditkartenformat (FAK) erstmalig Ausweis 60.--" | Tax law 50.1413 |
| D1 | VERIFIED (names only) | https://www.ur.ch/gemeinden | 200; all 19 commune names in content blocks | "Die Gemeinde Altdorf ist der Hauptort des Kantons Uri." | No commune website links in the HTML. Destination: resolver. |
| D2 | VERIFIED | Standeskanzlei /aemter/825; Amtsblatt /amtsblatt | i-web table 1,479 issues (1999-01-08 to 2026-09-18); issue /amtsblatt/42868 → /_doc/457969, PDF 24 pages with text | "AMTSBLATT DES KANTONS URI Inhaltsverzeichnis…" | fetcher:iweb-table + PDF; category missing: official_notices |

**Site recipe:** www.ur.ch; sitemap /sitemap.xml has 287 URLs, topic hubs only. Services come from `/dienstleistungen` (794 rows) and publications from the `data-entities` tables. robots.txt is 200 and empty. i-web signature confirmed (stats.i-web.ch, pcdn1.i-web.ch, /_rte/, /_doc/). Site search is JS-only. Laws: rechtsbuch.ur.ch (LexWork).
```yaml
- id: ur-gerichte-rechtsgebiete   # official_info, CH-UR, category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.ur.ch/rechtsgebiete/3909, https://www.ur.ch/rechtsgebiete/3912, https://www.ur.ch/rechtsgebiete/3914, https://www.ur.ch/rechtsgebiete/3915, https://www.ur.ch/rechtsgebiete/3917, https://www.ur.ch/rechtsgebiete/3918], path_allowlist: [/rechtsgebiete/], language: de}
- id: ur-pdfs   # taxes / schools / transport
  fetch_strategy: pdf
  fetch_config: {urls: [https://www.ur.ch/_doc/437558, https://www.ur.ch/_doc/449362, https://www.ur.ch/_doc/408844, https://www.ur.ch/_docn/437621/Tarifordnung_2026.pdf]}
```
**Claim checks:** /gerichte confirmed (redirects to /gerichtefs). /gerichte/gebuehren, /dienstleistungen and /rechtsprechung all wrong (404); real pages are /rechtsgebiete and /rechtsprechung, and no fee page exists. S3a: /dienstleistungen/3807 (dogs) wrong, real source laburk.ch plus 60.2111. /steuerbuch wrong, real Wegleitung is dienst 3869. /dienstleistungen/3328 wrong, real dienst 3125. /organisations/530 wrong, real /verkehr/4372. S4: /gemeinden confirmed; /staatskanzlei wrong, real /aemter/825 "Standeskanzlei".

---

## SZ (30 communes, 6 districts); govis, rate-limited
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.sz.ch/behoerden/justiz.html/8756-8758-8801 | 200 'Justiz – Kanton Schwyz', 19 KB | "Vermittlerämter streben bei Zivilstreitigkeiten gütliche Einigungen … an" | |
| C2 | VERIFIED | …/verwaltungsgericht/kosten-und-entschaedigungen.html/8756-8758-8801-11738-11855; Kantonsgericht PDFs /public/upload/assets/69458/… (Bezirksgerichte) and 69457 (Kantonsgericht); SRSZ 173.111 GebO | 200 | "pauschalierte Gerichtsgebühren von CHF 500.– (einfache Fälle) bis rund CHF 6'000.– (komplexe Fälle)" | SZ has no law_hits entry. I found the laws through **LexFind entity 19 (430 active texts)**; they are PDFs on sz.ch (e.g. `/public/upload/assets/32452/173_111.pdf`). The two fee PDFs were not opened. |
| C3 | VERIFIED | …/verwaltungsgericht/themen.html/…-11756 (1,141 words), …/kantonsgericht/eingaben.html/…-12233, …/kantonsgericht/gesetze-und-richtlinien.html/…-12234 | 200 | Links a maintenance calculator (Unterhaltsrechner XLSX), subsistence-minimum guidelines and a legal-aid form | 31 /behoerden/justiz URLs in the sitemap |
| C4 | VERIFIED | Kantonsgericht: https://gerichte.sz.ch/ (Tribuna VTPlus GWT app, 19.6 KB shell, 0 links); yearly EGV-SZ PDFs 2012–2024 on …/entscheidsammlungen.html/…-11700 | 200 | "publiziert … sämtliche Entscheide in anonymisierter Form online … seit circa März 2017" | opencaselaw sz_gerichte 3,413 (latest 2026-07-22) and sz_verwaltungsgericht 2,242 (latest 2026-08-20): not stale |
| C5 | VERIFIED | …/vermittleraemter.html/8756-8758-8801-12287 | 200, 506 words | "Arbeitsrechtliche Verfahren bis zu einem Streitwert von CHF 30 000.– sind für die klagende Partei kostenlos." | One Vermittler per commune (30); § 69 JG (SRSZ 231.110) |
| G1 | VERIFIED | laburk.ch (linked from sz.ch …/laboratorium-der-urkantone.html/…-9322); law SRSZ 546.100 (PDF 4 pages, text, as of 1.2.2024) | 200 | "§ 5 … hat der Halter seiner Wohngemeinde die Hundesteuer zu entrichten … Fr. 50.-- im Jahr" | Leash rule on public paths and roads in § 1. No SZ dog page in the 1,086-URL sitemap. |
| G2 | VERIFIED | Schwyzer Steuerbuch: 11 section pages in the sitemap; Weisungen page …/steuerrechtliche-weisungen-der-steuerverwaltung.html/…-10368 | 200; 19 PDF links on the Weisungen page | "70.20 Weisung über Liegenschaftskosten und Photovoltaik (LKPV) vom 18.11.2025" | Enumerable: sitemap sections, then PDF links → fetcher:pdf-index. PDF text layers not checked. |
| G3 | VERIFIED | data.sz.ch ODS `ferienplan-kanton-schwyz`; PDF …/85734/Kanton_Schwyz_Ferienplan_Schuljahr_2026-2027.pdf | API 200: 90 records, CC BY 4.0, modified 2026-05-28 | "Verbindlich sind die von den Schulräten erlassenen Ferienpläne." | **School councils (Schulräte) of communes and districts set them; the canton compiles.** yaml-now:api |
| G4 | VERIFIED | Verkehrsamt …/verkehrsamt.html/8756-8758-8802-9276-9293; fees …/fahrzeugsteuern-gebuehren.html/…-12382 | 200 | "Fahrzeugausweis … Gebühr in CHF … 50.–" | SRSZ 782.311, 782.300 |
| D1 | VERIFIED | …/gemeindesteueraemter.html/…-10498 (the sitemap's gemeinden-bezirke URL redirects there); ODS `raumgliederungen` | 200; 29 commune website links; ODS 30 records (BFS number, commune, district) | "Alpthal … Wollerau" | Wangen is not on the page. Districts: cite reports/g2-districts.md. Destination: resolver. |
| D2 | VERIFIED | …/staatskanzlei.html/8756-8758-8802-9944; …/staatskanzlei/amtsblatt.html/…-11248 | 200 | "Seit dem 1. Januar 2026 wird das Amtsblatt de[…]" → amtsblatt.sz.ch | Amtsblattportal tenant kabsz, 1,352 notices. Yearly compilations 2024/2025 as PDF. robots Disallow on the tenant domain. |

**Site recipe:** www.sz.ch (govis: `/public/upload/assets/<id>/<file>.pdf?fp=N`, `/route/…`); sitemap has 1,086 URLs; page URLs carry id suffixes (`.html/8756-…`). 5 s spacing gave 0 × 429 over about 25 requests. Open data at data.sz.ch (ODS). Laws are sz.ch PDFs, not LexWork.
```yaml
- id: sz-schulferien        # official_info, schools, default_extent CH-SZ (records per district/school, no per-record jurisdiction)
  fetch_strategy: api
  fetch_config:
    url: https://data.sz.ch/api/explore/v2.1/catalog/datasets/ferienplan-kanton-schwyz/records?limit=100
    records_path: results
    id_template: "{schuljahr}-{name_schule}"
    title_template: "Schulferien {schuljahr}: {name_schule} (Bezirk {bezirk})"
    text_template: "Schuljahr {schuljahr}, {name_schule}, Bezirk {bezirk}: Schulbeginn {start_schuljahr}; Herbstferien {herbstferien_start} bis {herbstferien_ende}; Weihnachtsferien {weihnachtsferien_start} bis {weihnachtsferien_ende}; Sportferien {sportferien_start} bis {sportferien_ende}; Frühlingsferien {fruehlingsferien_start} bis {fruehlingsferien_ende}; Schuljahresende {ende_schuljahr}."
    language: de
- id: sz-justiz             # category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.sz.ch/behoerden/justiz.html/8756-8758-8801], path_allowlist: [/behoerden/justiz/], language: de}   # needs crawl delay ≥5 s (new config)
```
**Claim checks:** all four AI court links under /behoerden/rechtspflege-gerichte… are wrong (404); the real pages are /behoerden/justiz…. The Bezirksgerichte link (429 in the pre-check) was not retested; the sitemap's real URL is /behoerden/justiz/bezirksgerichte.html/8756-8758-8801-9217. S3a dogs, tax, holidays and road all wrong (404); real sources are laburk.ch, the Schwyzer Steuerbuch pages, data.sz.ch plus the Schulorganisation page, and the Verkehrsamt page. S4 /kanton/gemeinden-bezirke.html and /kanton/staatskanzlei.html wrong (404); real pages are the Gemeindesteuerämter page and /behoerden/verwaltung/staatskanzlei.html/….

---

## OW (7 communes); i-web
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.ow.ch/gerichte | 200 'Obwalden - Gerichte'; table: Kantonsgericht (/gerichte/32), Obergericht (33), Ober- und Verwaltungsgerichtskanzlei (34) | | |
| C2 | VERIFIED (ordinance only) / NONE (resident page) | gdb.ow.ch 134.15 GebOR | LexWork 200 | "Ist mit dem Verfahren ein Augenschein verbunden, wird ein Zuschlag von Fr. 100.– bis Fr. 1 000.– berechnet." | **Ladder:** entry /gerichte → sitemap (295 URLs; 8 court paths, no fees) → services A-Z (632, no court fee) → court publications (newest 2024-03-19, no tariff) → WebSearch site:ow.ch (Kantonsgericht page, creditor leaflet, Amtsblatt PDF) → law_hits 134.15. |
| C3 | VERIFIED | /gerichte/32 (1,421 words); /dienstleistungen/7966 and 15 debt-enforcement and bankruptcy services (7957–8437); /dienstleistungen/998 | 200 | "…im Falle von Ehetrennungen und Ehescheidungen, soweit Einigkeit besteht; … Streitigkeiten aus Miete und Pacht" | |
| C4 | VERIFIED (JS) | http://rechtsprechung.ow.ch → /le/ (Weblaw LEv3, Vaadin 7.1.15, 834 B shell) | 200 | /rechtsprechunglinks: "Seit dem Jahr 2014 werden alle Grundsatzentscheide … (OGVE) publiziert" | **opencaselaw ow_gerichte 3,470, latest 2022-12-19: STALE** |
| C5 | VERIFIED | /dienstleistungen/998 'Sekretariat Schlichtungsbehörde' | 200 | "Das Sekretariat der Schlichtungsbehörde wird vom Amt für Justiz geführt." | No fees on the page; law 134.118 |
| G1 | VERIFIED | laburk.ch (OW links it as /aemter/243); law 818.3 (as of 01.08.2007) | LexWork 200 | "Die Einwohnergemeinden können durch Verordnung eine Hundesteuer einführen." | Dog tax is communal. No OW dog page. |
| G2 | VERIFIED | /publikationen/40733 → /_doc/447067 (Wegleitung 2025, 47 pages, text); practice manual list /publikationen/147 (~16 PDFs, e.g. "DA 01 2025 Krankheitskosten…"); Weisungen `_rtr/publikation_279`, Merkblätter `_rtr/publikation_3972` (not opened) | 200 | "Hier finden sie sämtliche aktuell gültigen Dienstanleitungen der Steuerverwaltung Obwalden" | steuerportal.ow.ch is a 371 B JS shell. Enumerable through i-web publication pages → fetcher:pdf-index. |
| G3 | VERIFIED | /dienstleistungen/5276 + /_doc/454867 (1 page, text) | 200 | "Herbstferien FR, 25. September 2026* SO, 11. Oktober 2026" | Canton sets them for "Volksschule (ohne Engelberg), Kantonsschule, BWZ"; that Engelberg sets its own is inferred from that wording. |
| G4 | VERIFIED | www.vsz.ch (Verkehrssicherheitszentrum OW/NW; /mobilitaet/276 redirects there); Gebuehren.pdf (4 pages, text) | 200; sitemap index with 2 children, 121 URLs | "Auszug aus dem Gebührenkatalog 01.01.2026 … FAK Ausstellung 50.00" | Laws OW 771.411 and NW 651.21. **Covers 2 cantons** (design:multi-canton). |
| D1 | VERIFIED | /gemeindenmain | 200 | "Alpnach Engelberg Giswil Kerns Lungern Sachseln Sarnen" | Each /gemeindenmain/<id> redirects to the commune site (4439 → sachseln.ch). resolver |
| D2 | VERIFIED | Staatskanzlei /departemente/16; amtsblatt.ow.ch (tenant kabow, 753 notices); ow.ch year archives up to 2025 (/dienstleistungen/9466, 107 issue PDF links) | 200 | "01-02_9.Januar_Seite1-51" | robots Disallow on the tenant domain |

**Site recipe:** www.ow.ch; 295-URL sitemap; robots 200 and empty; i-web. Laws on gdb.ow.ch (LexWork).
```yaml
- id: ow-pdfs   # taxes, schools
  fetch_strategy: pdf
  fetch_config: {urls: [https://www.ow.ch/_doc/447067, https://www.ow.ch/_doc/454867, https://www.ow.ch/_doc/447907]}
- id: vsz-ownw  # transport; jurisdiction OW+NW → one source per canton or design:multi-canton
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.vsz.ch/strassenverkehr], path_allowlist: [/strassenverkehr/], language: de}
```
**Claim checks:** /gerichte confirmed. /gerichte/kosten, /themen and /entscheide wrong (404). S3a /dienstleistungen/6216, /steuerbuch, /dienstleistungen/14299 and /organisations/1039 all wrong (404); real sources are laburk.ch, publications 40733/147, dienst 5276 and vsz.ch. S4 /kanton/gemeinden and /staatskanzlei wrong; real /gemeindenmain and /departemente/16.

---

## NW (11 communes); i-web
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.nw.ch/gerichte | 200 'Gerichte \| Kanton Nidwalden Online' | | |
| C2 | VERIFIED | /kantonsgerichtrechtspflege (legal aid) + PKoG 261.2 (gesetze.nw.ch, in force 2012-01-01) | 200 | "…Augenschein … Zuschlag von Fr. 50.– bis Fr. 1'000.–" | No tariff table on the web pages |
| C3 | VERIFIED | /kantonsgerichtrechtsauskunft, /kantonsgerichtzustaendigkeit, /kantonsgerichtrechtspflege, /kantonsgerichtpub (12 leaflets incl. "Mieterausweisung"), /schlichtungsbehpub (17 forms) | 200 | "Die Gerichte erteilen deshalb nur Auskünfte zum Verfahrensablauf…" | 30 court slugs in the sitemap |
| C4 | VERIFIED | /obgrechtsprechung | i-web table, **558** PDFs, 2016-10-24 to 2026-08-05 | "Konkurseröffnung (BAZ 26 9)" | opencaselaw nw_gerichte 1,052, same range: not stale |
| C5 | VERIFIED | /schlichtungsbehoerde → /schlichtungsbehoerde/326 | 200, 1,514 words | "…mit Ausnahme von Streitigkeiten aus dem Arbeitsrecht (bis zu einem Streitwert von CHF 30'000.--) und dem Miet- und Pachtrecht kostenpflichtig" | |
| G1 | VERIFIED | /amtjustizdienste/581; /kantonstierarzt/1124 (links laburk); service "Gefährliche Hunde" dienst/2275 (listed, not probed) | 200 | "Die Hundesteuer im Kanton NIdwalden beträgt CHF 120.00 pro Kalenderjahr." | **Cantonal dog register and dog tax (Amt für Justiz).** Laws 826.3 HuG, 826.31 HuV |
| G2 | VERIFIED | www.steuern-nw.ch (WordPress/Yoast; 121-URL sitemap): Wegleitung_2025_natuerliche-Personen.pdf (40 pages, text); "Weisungen & Richtlinien NP" (16 PDFs, StP-NW numbered) | 200 | "Wegleitung 2025 Natürliche Personen … Wer hat eine Steuererklärung 2025 einzureichen?" | WP media API returned HTTP 500 → crawl the pages or sitemap instead |
| G3 | VERIFIED | /biddirektionssekrdienste/520 + /_doc/456520 (plan 2026/27 to 2031/32, 1 page, text) | 200 | "Gemäss Bildungsgesetz (NG 311.1) Art. 8 Abs. 2 legt die Bildungsdirektion den Beginn und die Dauer des Schuljahres und der Ferien fest" | **Canton sets them.** The PDF was found through the publications A-Z (1,748 rows). |
| G4 | VERIFIED | www.vsz.ch (shared with OW) | see OW | | NW law 651.21 |
| D1 | VERIFIED | /gemeindenmain | 11 image-map links (Beckenried … Wolfenschiessen) | "Der Kanton Nidwalden besteht aus elf Gemeinden" | resolver |
| D2 | VERIFIED | /staatskanzlei/12; /amtsblatt/9163 → amtsblatt.nw.ch (tenant kabnw, 504 notices) | 200 | "Seit 2025 in digitaler Form" | robots Disallow on the tenant domain |

**Site recipe:** www.nw.ch; 668-URL sitemap with named slugs; robots 200 and empty; i-web. Service list `/dienstleistungen` (570 rows) and publications `/publikationen` (1,748 rows) are enumerable i-web tables.
```yaml
- id: nw-gerichte   # category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.nw.ch/kantonsgerichtrechtspflege, https://www.nw.ch/kantonsgerichtrechtsauskunft, https://www.nw.ch/kantonsgerichtzustaendigkeit, https://www.nw.ch/schlichtungsbehoerde/326], path_allowlist: [/kantonsgericht, /schlichtungsbeh], language: de}
- id: nw-hunde      # dogs
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.nw.ch/amtjustizdienste/581], path_allowlist: [/amtjustizdienste/581], language: de}
- id: nw-pdfs       # schools, taxes
  fetch_strategy: pdf
  fetch_config: {urls: [https://www.nw.ch/_doc/456520, https://www.steuern-nw.ch/app/uploads/2024/01/Wegleitung_2025_natuerliche-Personen.pdf]}
```
**Claim checks:** /gerichte confirmed. /gerichte/kosten, /informationen and /entscheide wrong. S3a /veterinaerdienst/417, /steueramt/402, /amtamtsstelle/352 and /verkehrsamt/365 all wrong (404); real sources are dienst 581, steuern-nw.ch, dienst 520 and vsz.ch. S4 /gemeinden wrong (real /gemeindenmain); /staatskanzlei confirmed (redirects to /12).

---

## GL (3 communes); govis, id-routed, rate-limited
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://www.gl.ch/rechtspflege/gerichte.html/285 | 200 'Gerichte – Kanton Glarus' | Navigation: "Obergericht Verwaltungsgericht Kantonsgericht Gerichtskasse" | |
| C2 | VERIFIED | …/kantonale-schlichtungsbehoerde/das-schlichtungsverfahren.html/4794; ordinances III A/5, III G/2 | 200, 960 words | "Die Pauschalgebühr für das Schlichtungsverfahren beträgt CHF 100.— bis CHF 800.— (Art. 2 …; GS III A/5)" | The Gerichtskasse page (/284) has no amounts |
| C3 | VERIFIED | FAQ /4916, /4794, Kantonsgericht /280; leaflets /4885 (not probed) | 200 | "…aus Miete und Pacht … bis zu einem Streitwert von CHF 30'000.—" | 62 /rechtspflege/ URLs in the sitemap |
| C4 | VERIFIED (JS) | https://findinfo.gl.ch (1,120 B JS shell 'Glarus - FindInfoWeb'); gl.ch page /272 | 200 | "Die Entscheide sind unter folgendem Link abrufbar: FindInfo" | opencaselaw gl_gerichte 1,418, latest 2026-08-13: not stale |
| C5 | VERIFIED | /rechtspflege/kantonale-schlichtungsbehoerde.html/316 + /4794 | 200 | fees CHF 100–800 | |
| G1 | VERIFIED (communal) | https://www.glarus-sued.ch/ansprechpartner/gesellschaft-und-sicherheit/hundewesen.html/3700; laws IV G/3/2, IX D/633/2 | 200 | "Die jährliche Hundetaxe beträgt ab dem Jahr 2025 pro Hund CHF 220.-. Davon entfallen 55 Franken zu Gunsten des Kantons Glarus und 165 Franken zu Gunsten der Gemeinde Glarus Süd." | No cantonal dog page (not in the 1,377-URL sitemap). Its Hundetaxen regulation PDF is **scanned** (1 text char in 3 pages). The Glarus Nord and Glarus pages came from WebSearch and were not probed. The legal basis for the 55-franc cantonal share was not found. |
| G2 | VERIFIED | https://www.gl.ch/public/upload/assets/59619/01%20Wegleitung%202025.pdf?fp=1 | PDF 36 pages, text | | Found only by WebSearch: not linked from /steuern.html/507 and no Steuerbuch in the sitemap. No index. |
| G3 | VERIFIED | Glarus Nord PDF …/35598/Ferienpl%C3%A4ne_2025-2028.pdf (1 page, text); BiG IV B/1/3 Art. 91 | 200 | "Das Departement setzt die Ferientermine und die Brückentage fest." / "Herbstferien Sa 03.10.26 So 18.10.26" | **Canton sets them.** The PDF sits on a commune host; no holiday page in the gl.ch sitemap. |
| G4 | VERIFIED | …/justiz/strassenverkehrsamt.html/466; fees /steuern-gebuehren/gebuehren.html/441 → StrGebV VII D/12/3 | 200 | "Führerausweis im Kreditkartenformat (FAK): 55 Fr." | id trap: /strassenverkehrsamt.html/1678 is a "News-Detailseite" |
| D1 | **NONE** (official list with links); 3 archive pages exist | /gl2011/die-gemeinden.html/351 → /349 | 200 | "Homepage: www.gl-nord.ch" (text only; commune_sites.csv has glarus-nord.ch) | **Ladder:** entry points (none) → sitemap (only /gl2011/… pages 348/349/350) → home page (no commune links) → /gemeindefragen/902 (no list) → AI link /kanton-und-gemeinden/gemeinden.html 404 → WebSearch surfaced the commune sites only. Use the BFS register (resolver). |
| D2 | VERIFIED | /verwaltung/staatskanzlei.html/1358; Amtsblatt /…/amtsblatt.html/5270 → https://amtsblatt.gl.ch/ | 200 | "Elektronisches Amtsblatt des Kantons Glarus … https://amtsblatt.gl.ch/ipub" | amtsblatt.gl.ch/ipub not probed; GL is an `external` tenant |

**Site recipe:** www.gl.ch (govis); 1,377-URL sitemap; robots `Disallow: /route/`; the trailing id decides the page, so always check `<title>`. 5 s spacing gave 0 × 429 over about 20 requests.
```yaml
- id: gl-schlichtung   # category missing: courts; crawl delay ≥5 s
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.gl.ch/rechtspflege/kantonale-schlichtungsbehoerde.html/316], path_allowlist: [/rechtspflege/kantonale-schlichtungsbehoerde/], language: de}
- id: gl-pdfs          # taxes, schools (jurisdiction CH-GL although hosted on glarus-nord.ch)
  fetch_strategy: pdf
  fetch_config: {urls: ["https://www.gl.ch/public/upload/assets/59619/01%20Wegleitung%202025.pdf?fp=1", "https://www.glarus-nord.ch/public/upload/assets/35598/Ferienpl%C3%A4ne_2025-2028.pdf?fp=5"]}
```
**Claim checks:** all AI court links ending in /720 are **wrong**. Id 720 is the forestry "Merkblätter, Richtlinien" page (…/wald-und-naturgefahren/merkblaetter-richtlinien-links.html/720 in the sitemap); the real court page is /rechtspflege/…/285. S3a dogs, Steuerbuch, holidays and road links all wrong (404). S4 /kanton-und-gemeinden/gemeinden.html is wrong (404, retested today because the pre-check only got 429). /verwaltung/staatskanzlei.html is partly right: correct path but missing the routing id; not retested; the real URL is …/1358.

---

## ZG (11 communes)
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | https://zg.ch/de/gerichte | 200 'Gerichte', 44 KB server HTML | "Urteil des Obergerichts Zug … vom 19. Juni 2026" | |
| C2 | VERIFIED | /de/news/2026/April/verwaltungsgericht-passt-gerichtskosten-an; /de/gerichte/zivil-und-strafrechtspflege/gerichtskasse; ordinances 161.7 KoV OG, 162.12 | 200 | "…Bau- und Planungsrechts von Fr. 2'000.– auf Fr. 4'000.– verdoppelt"; KoV OG § 10: "bis und mit 1000: 50 bis 250" | |
| C3 | VERIFIED | /de/recht-justiz/zivilverfahren, /de/recht-justiz/unentgeltliche-rechtspflege, …/zivilverfahren/schlichtung (+ tenancy FAQ pages listed in the sitemap) | 200 | | 99 /de/recht-justiz/ URLs in the sitemap |
| C4 | VERIFIED (JS) | https://obergericht.zg.ch/ (Tribuna VTPlus behind a **cookie check**: without cookies "HSP Error Page - Cookie Not accepted", with a cookie jar a 200 22 KB JS shell); administrative court: …/entscheide-des-verwaltungsgerichtes-zug (PDFs on cdn.zg.ch) | 200 | "Urteil V 2023 95 vom 24. Juni 2026" | opencaselaw: zg_verwaltungsgericht 1,902 (2026-09-10), zg_obergericht 1,718 (2026-08-25), zg_regierungsrat 306, zg_anwaltsaufsicht 26; **stale:** zg_kantonsgericht (2024-12-18), zg_strafgericht (2005-11-23), zg_datenschutzstelle (2016) |
| C5 | VERIFIED | …/schlichtung/friedensrichteraemter; /de/gerichte/zivil-und-strafrechtspflege/schlichtungsbehoerden | 200 | "Die Friedensrichterämter sind administrativ den Einwohnergemeinden angegliedert, unterstehen aber … dem Obergericht" | 11 links to the communes' offices; fees KoV OG § 10; law 161.4 |
| G1 | VERIFIED | https://zg.ch/de/natur-umwelt-tiere/veterinaerwesen/hunde; "Infoblatt Hundereglemente" PDF (January 2026, 1 page, text) | 200 | "…zwischen dem 1. April und dem 31. Juli eine Hundeleinenpflicht im Wald und am Waldrand" | **Dog rules are communal** ("Gesetze und Reglemente der Zuger Gemeinden massgebend"). The Infoblatt links each commune's regulation. Cantonal law only 436.1. |
| G2 | VERIFIED | zg.ch …/steuerrecht-und-steuergesetz/steuerbuch → https://wissen.zg.ch/steuerbuch (Angular SSR 401 KB; ng-state) → **https://wissen-backend.webcloud7.ch/steuerbuch** | backend 200 JSON: @type Book, modified 2026-01-06; `@search` items_total **1,343** chapters | "Erläuterungen zu § 1 - Einkommenssteuern: System der Postnumerandobesteuerung" | Enumerable → fetcher:plone-rest |
| G3 | VERIFIED | /de/bildung/bildungssystem/schulferien + PDF 2026/27–2030/31 (1 page, text) | 200 | "Für alle öffentlichen Schulen im Kanton Zug gelten die gleichen Schulferiendaten" / "Herbstferien Sa 03.10.26 - So 18.10.26" | One set of dates for the whole canton. Which body decides was not verified: the press-release PDF was not opened. |
| G4 | VERIFIED | /de/sicherheitsdirektion/strassenverkehrsamt; VO GS 751.221 (in force 2026-01-01) | 200 | "Bearbeitung eines Ausweisgesuchs generell: Fr. 30.–" | |
| D1 | VERIFIED | https://zg.ch/de/gemeinden | 200 'Gemeinden im Kanton Zug' | "Websites Unserer Gemeinden Baar Cham Hünenberg … Stadt Zug" | 11 names; links such as https://www.baar.ch/. resolver |
| D2 | VERIFIED | /de/staatskanzlei; /de/staat-politik/publikationssammlungen/amtsblatt → https://amtsblatt.zg.ch/tenant-kabzg | 200 | "erscheint primär in digitaler Form (E-Amtsblatt) jeweils donnerstags und ist die massgebende Fassung" | tenant kabzg, 2,213 notices |

**Site recipe:** zg.ch server HTML; 8 sitemaps with 9,109 URLs (3,537 German); files on cdn.zg.ch/dam; no rate limit seen. The old /behoerden/… paths mostly answer 404, but …/steuerbuch-zug still redirects to wissen.zg.ch. Laws on bgs.zg.ch (LexWork).
```yaml
- id: zg-recht-justiz   # category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://zg.ch/de/recht-justiz], path_allowlist: [/de/recht-justiz/], language: de}
- id: zg-hunde-ferien
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://zg.ch/de/natur-umwelt-tiere/veterinaerwesen/hunde, https://zg.ch/de/bildung/bildungssystem/schulferien], path_allowlist: [/de/natur-umwelt-tiere/veterinaerwesen/hunde, /de/bildung/bildungssystem/schulferien], language: de}
- id: zg-pdfs
  fetch_strategy: pdf
  fetch_config: {urls: ["https://cdn.zg.ch/dam/jcr:f4773ecc-3b24-4ed1-86aa-a1a5e891811a/Schulferien%20202627-203031.pdf", "https://cdn.zg.ch/dam/jcr:f9793485-4f58-4f82-9db4-a13b6cb095c1/Infoblatt%20Hundereglemente%20Januar%202026.pdf"]}
```
**Claim checks:** all six gerichte-zg.ch links are wrong (no DNS); the real pages are zg.ch/de/gerichte and /de/recht-justiz/…. S3a: the four www.zg.ch/behoerden/… links are wrong (404); real pages are /de/natur-umwelt-tiere/veterinaerwesen/hunde, the Steuerbuch on wissen.zg.ch, /de/bildung/bildungssystem/schulferien and /de/sicherheitsdirektion/strassenverkehrsamt. S4 /behoerden/gemeinden and /behoerden/staatskanzlei wrong; real /de/gemeinden and /de/staatskanzlei.

---

## Cross-canton

**New fetcher classes needed**
- `fetcher:amtsblattportal` (new): paged JSON list, then XML per notice. Field mapping: `meta.id` → identifier, `title.de` → title, `publicationDate` → published_at/event_date, `registrationOffice.municipalityId` → commune BFS number. Serves the NW, OW, SZ and ZG gazettes; the platform also hosts AR, BE, BL, BS, SH, SO, TI, VS and ZH. **Blocked on robots**; needs a design decision. Category missing: official_notices.
- `fetcher:iweb-table`: decodes `data-entities`, follows `/_rte/publikation/<id>` → `/_doc/<id>`. Serves UR decisions (444) and Amtsblatt (1,479), NW decisions (558) and publications (1,748), OW publications, and the UR/OW/NW service lists.
- `fetcher:pdf-index`: SZ Steuerbuch and EGV-SZ, the OW practice-manual PDFs, NW StP-NW PDFs, UR holiday plans, LU holiday PDFs.
- `fetcher:plone-rest`: the ZG Steuerbuch (1,343 chapters); same vendor as BL.
- `fetcher:lexwork`: laws for UR, OW, NW, GL, ZG, LU. SZ has no LexWork and needs **SRSZ PDFs through LexFind** (entity 19).
- `yaml-now:api` for Opendatasoft: SZ holidays. Paginated ODS would be needed for larger sets.
- `fetcher:wp-media`: laburk.ch (17 dog items). steuern-nw.ch returned 500, so crawl its sitemap instead.
- OCR: the Glarus Süd dog-tax regulation.
- `design:multi-canton`: laburk.ch (UR/SZ/OW/NW) and vsz.ch (OW/NW) cannot sit on one extent.

**Blocked or JavaScript-only**
- Amtsblattportal tenant domains: robots `Disallow: /`.
- Decision portals that are JS apps: gerichte.sz.ch and obergericht.zg.ch (Tribuna GWT; ZG also has a cookie wall), rechtsprechung.ow.ch (Weblaw Vaadin), findinfo.gl.ch. opencaselaw covers all of them, but **OW is stale (2022-12-19)**.
- steuern-nw.ch WP media API: HTTP 500.
- LU Kantonsblatt: no online edition found.
- Glarus Süd dog-tax regulation PDF: scanned.

**5 best finds**
1. Amtsblattportal API: one pattern for 4 of my 7 cantons' gazettes (plus 9 more cantons), with live counts; robots must be settled first.
2. Zuger Steuerbuch on Plone REST (`wissen-backend.webcloud7.ch/steuerbuch`, 1,343 chapters, `@search` enumeration).
3. `data.sz.ch` holiday dataset: 90 records, CC BY 4.0, ingestible with the YAML above today.
4. laburk.ch: one dog-guidance host for UR, SZ, OW and NW (35-URL sitemap, WP media API).
5. LU per-commune holiday PDF covering all 79 communes, plus the LU Steuerbuch sitemap (391 URLs with lastmod) and the LGVE per-decision Ajax HTML.

Also worth knowing: NW's dog tax is cantonal (CHF 120), SZ's is set in cantonal law (Fr. 50, with communal increases allowed), and in OW, GL and ZG dog rules are communal. ZG's dog Infoblatt links every commune's dog regulation.