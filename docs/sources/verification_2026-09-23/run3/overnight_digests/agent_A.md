# Run 3 agent A: progress before the stall (log a73ff78b018803645, 03:30–03:39 UTC 2026-09-23)

Extracted verbatim from the agent transcript. Results are truncated to 2,500 characters. The files it wrote under /tmp are gone.

> I'll start by reading the brief in full.

## Step 1: Bash: Count brief lines and list scratchpad
```
wc -l <scratchpad-overnight>/agent_brief_v5.md; ls -la <scratchpad-overnight>/
```
Result:
```
     295 <scratchpad-overnight>/agent_brief_v5.md
total 904
drwx------  27 <user>  wheel    864 Sep 23 05:29 .
drwx------   4 <user>  wheel    128 Sep 23 01:18 ..
-rw-r--r--   1 <user>  wheel   8011 Sep 23 01:57 agent_brief_v2.md
-rw-r--r--   1 <user>  wheel  10220 Sep 23 02:39 agent_brief_v3.md
-rw-r--r--   1 <user>  wheel  17140 Sep 23 03:38 agent_brief_v4.md
-rw-r--r--   1 <user>  wheel  25330 Sep 23 05:29 agent_brief_v5.md
-rw-r--r--   1 <user>  wheel  34141 Sep 23 01:38 ai_mode_conversation_raw_2026-09-23.md
-rw-r--r--   1 <user>  wheel  48055 Sep 23 02:06 awesome_ogd_switzerland_2026-09-23.md
-rw-r--r--   1 <user>  wheel  11513 Sep 23 01:38 candidate_links_2026-09-23.md
-rw-r--r--   1 <user>  wheel    922 Sep 23 05:07 cities_s2_links.txt
-rw-r--r--   1 <user>  wheel  41810 Sep 23 05:04 courts_s1_probe.json
-rw-r--r--   1 <user>  wheel   9536 Sep 23 05:02 courts_s1_rows.py
-rw-r--r--   1 <user>  wheel   7548 Sep 23 04:31 coverage_ledger_2026-09-23.md
-rw-r--r--   1 <user>  wheel  22077 Sep 23 05:09 guidance_s3a_probe.json
-rw-r--r--   1 <user>  wheel   5520 Sep 23 05:09 guidance_s3a_rows.py
-rw-r--r--   1 <user>  wheel   1549 Sep 23 04:27 ledger_ai_mode.csv
-rw-r--r--   1 <user>  wheel  80756 Sep 23 04:31 ledger_awesome.csv
-rw-r--r--   1 <user>  wheel   1780 Sep 23 04:31 ledger_handoff.csv
-rw-r--r--   1 <user>  wheel  18526 Sep 23 05:06 opencaselaw_courts_2026-09-23.json
-rw-r--r--   1 <user>  wheel   8564 Sep 23 05:16 precheck_entry_points_2026-09-23.md
drwxr-xr-x   8 <user>  wheel    256 Sep 23 03:26 reports
-rw-r--r--   1 <user>  wheel  23845 Sep 23 05:15 s3b_s4_probe.json
-rw-r--r--   1 <user>  wheel   5880 Sep 23 05:15 s3b_s4_rows.py
-rw-r--r--   1 <user>  wheel  12205 Sep 23 03:48 source_registry_2026-09-23.csv
-rw-r--r--   1 <user>  wheel   9805 Sep 23 03:40 source_registry_2026-09-23.md
drwxr-xr-x  32 <user>  wheel   1024 Sep 23 05:28 stage0
-rw-r--r--   1 <user>  wheel   8411 Sep 23 03:48 verification_results_2026-09-23.md
```

## Step 2: Read: <scratchpad-overnight>/agent_brief_v5.md
```
{"file_path": "<scratchpad-overnight>/agent_brief_v5.md"}
```
Result:
```
1	# Brief v5: source verification agents (read fully before starting)
2	
3	_v4 = v3 plus the learnings of the 2026-09-23 runs (pilot + 5 groups). The new sections are marked **NEW v4**._
4	
5	## Why you are doing this
6	We build **Swiss Grounding**, an MCP server that gives a chat model *cited evidence* from Swiss
7	public sources, scoped to the jurisdiction a question applies to (CH → canton → district → commune).
8	Typical questions: "When is cardboard collected in 8003?", "Can my dog run off leash in my commune?",
9	"What does a dog cost in tax here?", "When are school holidays in Bern?", "What is the waste bag fee?"
10	
11	You get a small set of **candidate links** that came from a Google AI answer. **That AI is
12	unreliable.** It invents URLs, shortens links to bare domains and mislabels pages. Each link comes
13	with the AI's *claim*. Your job:
14	
15	1. **Find the real data** behind each lead. Start from the link (or the bare domain) and dig.
16	2. **Decide: can we get it?** If so, **in what exact format**, and **how would a fetcher get it**.
17	3. **Test the AI's claim**: confirmed, wrong or partly right.
18	
19	## THE MOST IMPORTANT RULE: find the real source, and explore freely to do it
20	**What matters most to us is that you find where the actual data lives.** The given link is a
21	starting point, not the answer. In the pilot run, **3 of 4 leads only became useful after a web
22	search or after following a hop to another site.** An agent that had stopped at the given link
23	would have missed all three. In the five group runs that followed, the best finds were all one hop
24	away from the given lead (intlex.ch, tlex.ch, ÖREB LegalProvisions, the zh.ch child sitemap, REAL Luzern's ICS). So:
25	
26	- **You are free to explore.** If the lead points somewhere better (another official host, the
27	  cantonal law collection, an open-data portal, a commune's own site, a vendor platform that hosts
28	  many communes), go there. Up to **2 hops** from the given link is in scope when each hop lands
29	  on an official or data-bearing host. If a find is outside your leads but clearly valuable
30	  (e.g. a platform covering many communes), report it under "Related finds".
31	- **Do not stop at a landing or guidance page.** Keep going until you reach the layer that holds
32	  the actual content (the individual regulation, the calendar entry, the record), or you have
33	  proven it is not reachable.
34	- **Before you are allowed to write "Blocked", "No data
```

> Now the prepared inputs: precheck entry points, law hits, sitemap candidates and prior reports.

## Step 3: Bash: Read precheck entry points and list stage0 files
```
SP=<scratchpad-overnight>; cat $SP/precheck_entry_points_2026-09-23.md; echo ----; ls -la $SP/stage0 $SP/stage0/sitemaps $SP/reports
```
Result:
```
# Pre-check 2026-09-23: verified entry points per canton (input for the agents)

Built from one live request per link. S1 courts: 141 links. S2 cities: 10 links, all 404; real pages came from G1 saved homepages. S3a guidance: 64 links.
Only pages that answered 200 with real content are listed. Gemini-wrapped links that failed are not listed: agents must not retry them.

## AG  (2 verified entry points; 4 dead AI court links)
- [courts] https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/obergericht — Obergericht - Kanton Aargau
- [courts] https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/bezirksgerichte — Bezirksgerichte - Kanton Aargau

## AI  (1 verified entry points; 3 dead AI court links)
- [courts] https://www.ai.ch/gerichte — Gerichte — Appenzell Innerrhoden

## BE  (3 verified entry points; 7 dead AI court links)
- [courts] https://www.zsg.justice.be.ch/de/start.html — Startseite
- [courts] https://www.zsg.justice.be.ch/de/start/themen.html — Themen
- [courts] https://www.zsg.justice.be.ch/de/start/ueber-uns/regionalgerichte.html — Regionalgerichte
- [chancellery (S4)] https://www.sta.be.ch/de/start.html — Staatskanzlei des Kantons Bern - Startseite

## BS  (1 verified entry points; 0 dead AI court links)
- [courts] https://www.bs.ch/willkommen-bei-den-gerichten — Willkommen bei den Gerichten | Kanton Basel-S
- [chancellery (S4)] https://www.bs.ch/regierungsrat/staatskanzlei — Staatskanzlei | Kanton Basel-Stadt

## GL  (4 verified entry points; 1 dead AI court links)
- [courts (id-routed: same page for any path)] https://www.gl.ch/verwaltung/gerichte.html/720 — Merkblätter, Richtlinien – Kanton Glarus
- [courts (id-routed: same page for any path)] https://www.gl.ch/verwaltung/gerichte/gebuehren.html/720 — Merkblätter, Richtlinien – Kanton Glarus
- [courts (id-routed: same page for any path)] https://www.gl.ch/verwaltung/gerichte/merkblaetter.html/720 — Merkblätter, Richtlinien – Kanton Glarus
- [courts (id-routed: same page for any path)] https://www.gl.ch/verwaltung/gerichte/entscheide.html/720 — Merkblätter, Richtlinien – Kanton Glarus

## LU  (4 verified entry points; 4 dead AI court links)
- [courts] https://gerichte.lu.ch/organisation/kantonsgericht — Kantonsgericht - Kanton Luzern
- [dogs] https://veterinaerdienst.lu.ch/hunde — Hunde - Kanton Luzern
- [tax] https://steuerbuch.lu.ch/ — Willkommen im Luzerner Steuerbuch - Kanton Lu
- [road] https://strassenverkehrsamt.lu.ch/ — Strassenverkehrsamt - Kanton Luzern
-
```

## Step 4: Bash: Read the g5 guidance report
```
SP=<scratchpad-overnight>; cat $SP/reports/g5-guidance.md
```
Result:
```
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
| ZH | yes (AEM; e.g. hunde.html 128 KB, 2,556 words) | robots names the index `/bin/zhweb/publish/sitemap.xml` → 44 per-directorate/topic c
```

## Step 5: Bash: Read g2 districts and g1 commune law reports
```
SP=<scratchpad-overnight>; cat $SP/reports/g2-districts.md; echo; echo -----; cat $SP/reports/g1-commune-law.md
```
Result:
```
# G2 report: districts, courts, regional planning, geodata (Opus 5.5 agent, 2026-09-23)
Run: 116 tool calls, ~202k tokens, ~34 min. Evidence: /tmp/sg-verify-g2-districts/. The harness blocked the
agent's own backup file, so this is the main session's transcription of its hand-back.

**Spot-checked by the main session (live curl, 2026-09-23). All matched:**
- einsiedeln.ch/verwaltung/rechtssammlung: 200, 156 KB, **215 unique sre_*.pdf**
- kuessnacht.ch/politik/rechtssammlung.html/436: 200, 76 KB, **72 unique /public/upload/assets/*.pdf**
- api.geobasisdaten.ch/api/v1/corp/: **79 corps** (first = Bund)
- agvchapp.bfs.admin.ch/api/communes/snapshot?date=01-01-2026: CSV header HistoricalCode,BfsCode,…,Level,Parent,Name
- repo src/swiss_grounding/locations/data/communes.csv header: `bfs_id,name,canton,district,postal_codes`
Not re-checked: ÖREB extracts, geodienste OGC features and `dokument` links, gerichte-zh sitemap counts, RSTA sitemap, WP media APIs, Gersau.

## Summary
| id | can we get it | format | strategy / new fetcher | value |
|---|---|---|---|---|
| D4 Bezirk Küssnacht (CH-SZ-1331) | Yes | HTML index + 72 PDFs (text) | pdf / PDF index discoverer | high |
| D4b Einsiedeln (CH-SZ-1301) | Yes | HTML + 215 PDFs (text) | PDF index discoverer | high |
| D4b Gersau (CH-SZ-1311) | Yes | OneGov HTML + 22 PDFs | pdf / PDF index discoverer | med |
| D5 Bezirk Höfe (3 communes) | Yes (new) | WordPress media JSON + PDF | WP media API | low |
| D4b Bezirk Schwyz (15 communes) | Yes (new) | WordPress media JSON | WP media API | low |
| D4b March | Partly | JS (i-web CMS) | unresolved | low |
| D6 BE Regierungsstatthalterämter | Yes | server HTML (AEM), 66 sitemap URLs | html_crawl (Crawl-delay 10) | med |
| D7 gerichte-zh.ch | Yes | server HTML (Drupal), 249 /de/themen/ pages | html_crawl | med-high |
| R1 Planungsgruppe Pfannenstil (zpp.ch) + all 11 ZH regional Richtpläne | Yes | PDF text | pdf | low |
| R2 Region Oberaargau (oberaargau.ch) | Yes | Wix + PDF | pdf | low |
| geobasisdaten.ch | Yes (new) | JSON API + XLSX | list+detail fetcher | med |
| geodienste.ch | Yes (new) | OGC API Features JSON | legal-document harvester | **high** |
| ÖREB-Kataster | Yes (new) | JSON/XML extract | legal-provision harvester | **high** |
| C6/C7 resolvers | Yes | CSV | resolver data | med |

## Key findings
- **Schwyz districts are autonomous** (GOG SZ §1 Abs. 2 applies the commune rules to districts). District law is **not** in the
  cantonal SRSZ. Küssnacht, Einsiedeln an
```

> Now the law hits and sitemap topic candidates for my six cantons.

## Step 6: Bash: Print law_hits.json entries for six cantons
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/law_hits.json'))
print(type(d), list(d.keys())[:40] if isinstance(d,dict) else len(d))
for c in ['ZH','BE','BS','BL','SO','AG']:
    v=d.get(c)
    print('=====',c, type(v))
    if isinstance(v,dict):
        for t,hits in v.items():
            print('  --',t, len(hits) if isinstance(hits,list) else hits)
            if isinstance(hits,list):
                for h in hits[:12]:
                    print('     ',json.dumps(h,ensure_ascii=False)[:260])
    else:
        print(json.dumps(v,ensure_ascii=False)[:2000])
"

```
Result:
```
<class 'dict'> ['AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH']
===== ZH <class 'dict'>
  -- court_fees 4
      {"nr": "175.252", "title": "Gebührenverordnung des Verwaltungsgerichts", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/22304"}
      {"nr": "211.11", "title": "Gebührenverordnung des Obergerichts", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/21701"}
      {"nr": "212.812", "title": "Verordnung über die Gebühren, Kosten und Entschädigungen vor dem Sozialversicherungsgericht", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/22327"}
      {"nr": "215.12", "title": "Verordnung des Obergerichts über die Gebühren, Kosten und Entschädigungen gemäss Anwaltsgesetz", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/23375"}
  -- conciliation 5
      {"nr": "177.12", "title": "Gesetz über das Schlichtungsverfahren für Streitigkeiten nach Gleichstellungsgesetz in öffentlich-rechtlichen Arbeitsverhältnissen", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/23785"}
      {"nr": "212.126", "title": "Beschluss des Regierungsrates über die Neuaufteilung der Friedensrichterkreise 3, 4, 5, 6, 9, 10, 11 und 12 (der Stadt Zürich)", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/22245"}
      {"nr": "212.127", "title": "Beschluss des Regierungsrates über die Vereinigung der Friedensrichterkreise 1 und 2 (der Stadt Zürich)", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/22947"}
      {"nr": "212.23", "title": "Beschluss des Kantonsrates über die Zahl der Beisitzenden der Arbeitsgerichte für die Amtsdauer 2026–2032", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/23814"}
      {"nr": "212.24", "title": "Beschluss des Kantonsrates über die Zahl der Beisitzenden der Mietgerichte für die Amtsdauer 2026–2032", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/23975"}
  -- dogs 2
      {"nr": "554.5", "title": "Hundegesetz", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/22871"}
      {"nr": "554.51", "title": "Hundeverordnung", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/22888"}
  -- tax 4
      {"nr": "631.1", "title": "Steuergesetz", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/23108"}
      {"nr": "631.11", "title": "Verordnung zum Steuergesetz", "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/22362"}
      {"nr": "632.1", "title": "Erbschafts- und Schenkungssteuergesetz", "api": 
```

> Law hits have gaps (AG has no court_fees; SO's only "court_fees" hit is a Hague convention). Let me inspect the full law lists to fill them.

## Step 7: Bash: Inspect structure of laws_XX.json files
```
SP=<scratchpad-overnight>; python3 -c "
import json
for c in ['AG','SO','ZH','BL','BE','BS']:
    d=json.load(open('$SP/stage0/laws_%s.json'%c))
    print(c, type(d), (list(d.keys())[:10] if isinstance(d,dict) else len(d)))
    if isinstance(d,dict):
        for k,v in list(d.items())[:3]:
            print('  ',k, json.dumps(v,ensure_ascii=False)[:300])
    else:
        print('  ', json.dumps(d[0],ensure_ascii=False)[:300])
"

```
Result:
```
AG <class 'dict'> ['host', 'lang', 'items']
   host "gesetzessammlungen.ag.ch"
   lang "de"
   items [{"id": 775, "systematic_number": "953.311", "systematic_category_id": 208, "title": "Vollziehungsverordnung zum Bundesgesetz über den Konsumkredit", "abrogated": false, "structured_document_id": 37073}, {"id": 521, "systematic_number": "301.100", "systematic_category_id": 168, "title": "Gesundheits
SO <class 'dict'> ['host', 'lang', 'items']
   host "bgs.so.ch"
   lang "de"
   items [{"id": 513, "systematic_number": "614.81", "systematic_category_id": 203, "title": "Gesetz über die Schiffssteuer", "abrogated": false, "structured_document_id": 4659}, {"id": 514, "systematic_number": "615.11", "systematic_category_id": 205, "title": "Gebührentarif", "abrogated": false, "structure
ZH <class 'dict'> ['lexfind_entity', 'items']
   lexfind_entity 26
   items [{"id": 21736, "title": "Verfassung des Kantons Zürich", "keywords": null, "systematic_number": "101", "is_active": true, "category_id": 3}, {"id": 22107, "title": "Vertrag zwischen den Ständen Zürich und St. Gallen betreffend die Festsetzung der Staatsgrenze auf dem Zürichsee bei Rapperswil", "keyw
BL <class 'dict'> ['host', 'lang', 'items']
   host "bl.clex.ch"
   lang "de"
   items [{"id": 257, "systematic_number": "341", "systematic_category_id": 42, "title": "Gesetz über die Motorfahrzeugsteuer", "abrogated": false, "structured_document_id": 11422}, {"id": 183, "systematic_number": "341.11", "systematic_category_id": 42, "title": "Verordnung zum Gesetz über die Motorfahrzeug
BE <class 'dict'> ['host', 'lang', 'items']
   host "www.belex.sites.be.ch"
   lang "de"
   items [{"id": 256, "systematic_number": "324.1", "systematic_category_id": 105, "title": "Gesetz betreffend die Einführung des Bundesgesetzes vom 24. Juni 1970 über Ordnungsbussen im Strassenverkehr und die Erhebung von anderen Ordnungsbussen", "abrogated": false, "structured_document_id": 413}, {"id": 27
BS <class 'dict'> ['host', 'lang', 'items']
   host "gesetzessammlung.bs.ch"
   lang "de"
   items [{"id": 1, "systematic_number": "111.100", "systematic_category_id": 5, "title": "Verfassung des Kantons Basel-Stadt", "abrogated": false, "structured_document_id": 29086}, {"id": 258, "systematic_number": "258.100", "systematic_category_id": 53, "title": "Gesetz über die Begnadigung", "abrogated":
```

## Step 8: Bash: Search law lists for fee, conciliation, gazette laws
```
SP=<scratchpad-overnight>; python3 -c "
import json,re
pat=re.compile(r'(Verfahrenskost|Gebühr|Gerichtskost|Kostendekret|Schlicht|Friedensricht|Ferien|Schulferien|Hund|Gemeinde(verzeichnis|n des)|Amtsblatt|Staatskanzlei|Anwalt.*Tarif|Tarif)',re.I)
for c in ['AG','SO','ZH','BL','BE','BS']:
    d=json.load(open('$SP/stage0/laws_%s.json'%c))
    items=d['items']
    print('=====',c,len(items))
    for it in items:
        t=it.get('title','')
        if re.search(r'(Verfahrenskost|Gerichtsgeb|Gebühren der Gerichte|Gebührentarif|Kostendekret|Gerichtskost|Schlicht|Friedensricht|Schulferien|Ferienordnung|Amtsblatt|Publikationsgesetz|Gebühren.*Gericht|Gericht.*Gebühr)',t,re.I):
            print('  ',it.get('systematic_number'),'|',t[:150],'|abrogated' if it.get('abrogated') or it.get('is_active') is False else '', '| id',it.get('id'))
"

```
Result:
```
===== AG 463
   155.612 | Reglement der Justizleitung über die Anzahl der übrigen Richterinnen und Richter (nebenamtliche Richterinnen und Richter an den Bezirksgerichten; Fach  | id 926
   155.614 | Reglement für die Schlichtungsbehörden für Miete und Pacht  | id 1136
===== SO 539
   615.11 | Gebührentarif  | id 514
   129.12 | Notariats-Gebührentarif  | id 124
   212.473.91 | Gebührentarif für die Nachführung der Vermessungswerke  | id 163
===== ZH 944
   170.5 | Publikationsgesetz  | id 22636
   175.252 | Gebührenverordnung des Verwaltungsgerichts  | id 22304
   177.12 | Gesetz über das Schlichtungsverfahren für Streitigkeiten nach Gleichstellungsgesetz in öffentlich-rechtlichen Arbeitsverhältnissen  | id 23785
   211.11 | Gebührenverordnung des Obergerichts  | id 21701
   212.126 | Beschluss des Regierungsrates über die Neuaufteilung der Friedensrichterkreise 3, 4, 5, 6, 9, 10, 11 und 12 (der Stadt Zürich)  | id 22245
   212.127 | Beschluss des Regierungsrates über die Vereinigung der Friedensrichterkreise 1 und 2 (der Stadt Zürich)  | id 22947
   212.812 | Verordnung über die Gebühren, Kosten und Entschädigungen vor dem Sozialversicherungsgericht  | id 22327
   215.12 | Verordnung des Obergerichts über die Gebühren, Kosten und Entschädigungen gemäss Anwaltsgesetz  | id 23375
===== BL 860
   250.13 | Verordnung über die Verfahrenskosten der Staatsanwaltschaft  | id 780
   421.17 | Gebührentarif der Schweizerischen Rheinhäfen  | id 905
   170.31 | Verordnung über die Gebühren der Gerichte (Gebührentarif, GebT)  | id 424
   106 | Publikationsgesetz (PublG)  | id 1192
   106.11 | Verordnung zum Publikationsgesetz (Vo PublG)  | id 433
===== BE 711
   103.1 | Publikationsgesetz (PuG)  | id 23
   161.12 | Dekret betreffend die Verfahrenskosten und die Verwaltungsgebühren der Gerichtsbehörden und der Staatsanwaltschaft (Verfahrenskostendekret, VKD)  | id 104
   164.211 | Geschäftsreglement der regionalen Schlichtungsbehörde Berner Jura-Seeland (GeschR SB BJS)  | id 868
   164.212 | Geschäftsreglement der regionalen Schlichtungsbehörde Emmental-Oberaargau (GeschR SB EO)  | id 869
   164.213 | Geschäftsreglement der regionalen Schlichtungsbehörde Bern-Mittelland (GeschR SB BM)  | id 870
   164.214 | Geschäftsreglement der regionalen Schlichtungsbehörde Oberland (GeschR SB OL)  | id 871
===== BS 944
   955.470 | Gebührentarif der Schweizerischen Rheinhäfen  | id 815
   154.800 | Gesetz über die Gerichtsgebühren  | id 119
   154.810 | Reglement über die Gerichtsg
```

> AG shows no fee decree. Let me look at AG's 221.x and 155.x ranges and SO's 615.11 to confirm.

## Step 9: Bash: List AG laws in court and admin ranges
```
SP=<scratchpad-overnight>; python3 -c "
import json,re
d=json.load(open('$SP/stage0/laws_AG.json'))
for it in sorted(d['items'],key=lambda x:x['systematic_number']):
    n=it['systematic_number']
    if n.startswith(('221','155','291','15','41','1')) and n[:3] in ('221','155','291','150','151','152','153','154','156','411','401','421','131','171','172','120','110','140','161'):
        print(n,'|',it['title'][:120],'| abr' if it.get('abrogated') else '')
" | head -80
```
Result:
```
110.000 | Verfassung des Kantons Aargau 
110.300 | Beschluss über Standesfarbe, Wappen und Siegel des Kantons 
131.100 | Gesetz über die politischen Rechte 
131.111 | Verordnung zum Gesetz über die politischen Rechte 
131.131 | Verordnung über die Wahl des Nationalrates 
131.731 | Verordnung über die Wahl des Einwohnerrates 
150.200 | Haftungsgesetz 
150.211 | Haftungsverordnung 
150.300 | Unvereinbarkeitsgesetz 
150.400 | Gesetz über die öffentliche Statistik 
150.411 | Statistikverordnung 
150.600 | Gesetz über die amtlichen Publikationsorgane 
150.700 | Gesetz über die Information der Öffentlichkeit, den Datenschutz und das Archivwesen 
150.711 | Verordnung zum Gesetz über die Information der Öffentlichkeit, den Datenschutz und das Archivwesen 
150.717 | Interkantonale bzw. interbehördliche Vereinbarung über den Datenaustausch zum Betrieb von Lage- und Analysesystemen im B 
150.721 | Verwaltungsvereinbarung über die Zusammenarbeit von Schweizer Kantonen bezüglich Errichtung und Betrieb eines Verbundes  
150.731 | Verordnung zur Aktenführung in der kantonalen Verwaltung 
150.920 | Dekret über das öffentliche Beschaffungswesen 
150.950 | Interkantonale Vereinbarung über das öffentliche Beschaffungswesen 
150.960 | Interkantonale Vereinbarung über das öffentliche Beschaffungswesen 
152.020 | Vereinbarung über die Interparlamentarische Konferenz der Nordwestschweiz 
152.100 | Gesetz über die Wahl des Grossen Rates 
152.111 | Verordnung zum Grossratswahlgesetz 
152.200 | Gesetz über die Organisation des Grossen Rates und über den Verkehr zwischen dem Grossen Rat, dem Regierungsrat und der  
152.210 | Dekret über die Geschäftsführung des Grossen Rates 
152.212 | Richtlinien des Büros des Grossen Rats zur Vorbereitung und Durchführung der durch den Grossen Rat vorzunehmenden Wahlen 
153.010 | Vereinbarung über die Nordwestschweizer Regierungskonferenz 
153.100 | Gesetz über die Organisation des Regierungsrates und der kantonalen Verwaltung 
153.113 | Verordnung über die Delegation von Kompetenzen des Regierungsrats 
153.313 | Verordnung über den Rechtsdienst des Regierungsrats 
153.520 | Dekret über die Besoldung der Mitglieder des Regierungsrats 
153.560 | Dekret über die berufliche Vorsorge für die Mitglieder des Regierungsrats und die Übergangsleistungen beim Ausscheiden a 
155.200 | Gerichtsorganisationsgesetz 
155.520 | Dekret über die Besoldung der Mitglieder des Obergerichts 
155.560 | Dekret über die Entschädigung der nebenamtlichen Richterinnen und Ri
```

> AG's list (463 items) lacks the Verfahrenskostendekret; I'll query the LexWork API directly later. Now the sitemap topic candidates and summary.

## Step 10: Bash: Show sitemap summary for my cantons' hosts
```
SP=<scratchpad-overnight>; mkdir -p /tmp/sg-verify-run3-a; python3 -c "
import json
s=json.load(open('$SP/stage0/sitemaps_summary.json'))
print(type(s))
if isinstance(s,dict):
    for k,v in s.items():
        if any(x in k for x in ['zh','be.ch','bs.ch','basel','so.ch','ag.ch','bern','thun','zuerich']):
            print(k, json.dumps(v,ensure_ascii=False)[:400])
else:
    for v in s:
        if any(x in json.dumps(v) for x in ['zh.ch','be.ch','bs.ch','basel','so.ch','ag.ch','bern.ch','thun','zuerich']):
            print(json.dumps(v,ensure_ascii=False)[:400])
"
```
Result:
```
<class 'dict'>
```

## Step 11: Bash: Inspect sitemap summary and topic candidates structure
```
SP=<scratchpad-overnight>; python3 -c "
import json
s=json.load(open('$SP/stage0/sitemaps_summary.json'))
print(list(s.keys())[:20])
k0=list(s.keys())[0]
print(json.dumps(s[k0],ensure_ascii=False)[:1500])
"; head -c 1500 $SP/stage0/sitemap_topic_candidates.json
```
Result:
```
['hosts', 'result']
{"ZH": ["www.zh.ch", "www.gerichte-zh.ch", "www.stadt-zuerich.ch"], "BE": ["www.zsg.justice.be.ch", "www.rsta.dij.be.ch", "www.svsa.sid.be.ch", "www.sv.fin.be.ch", "www.weu.be.ch", "www.bkd.be.ch", "www.sta.be.ch", "www.akvb-gemeinden.bkd.be.ch", "www.be.ch", "www.bern.ch", "www.thun.ch"], "LU": ["www.lu.ch", "gerichte.lu.ch", "veterinaerdienst.lu.ch", "steuerbuch.lu.ch", "strassenverkehrsamt.lu.ch", "volksschulbildung.lu.ch"], "UR": ["www.ur.ch"], "SZ": ["www.sz.ch"], "OW": ["www.ow.ch"], "NW": ["www.nw.ch"], "GL": ["www.gl.ch"], "ZG": ["zg.ch"], "FR": ["www.fr.ch", "www.ocn.ch"], "SO": ["so.ch"], "BS": ["www.bs.ch"], "BL": ["www.baselland.ch"], "SH": ["sh.ch", "www.stadt-schaffhausen.ch"], "AR": ["ar.ch"], "AI": ["www.ai.ch"], "SG": ["www.sg.ch"], "GR": ["www.gr.ch"], "AG": ["www.ag.ch"], "TG": ["www.tg.ch", "strassenverkehrsamt.tg.ch", "staatskanzlei.tg.ch"], "TI": ["www4.ti.ch", "www.lugano.ch"], "VD": ["www.vd.ch", "www.lausanne.ch"], "VS": ["www.vs.ch"], "NE": ["www.ne.ch", "www.scan-ne.ch", "www.chaux-de-fonds.ch", "www.neuchatelville.ch"], "GE": ["www.ge.ch", "justice.ge.ch", "www.geneve.ch", "www.vernier.ch"], "JU": ["www.jura.ch"]}
{
 "ZH": {
  "courts": {
   "count": 2101,
   "shortest": [
    "https://www.gerichte-zh.ch/de",
    "https://www.gerichte-zh.ch/de/themen",
    "https://www.gerichte-zh.ch/de/karriere",
    "https://www.gerichte-zh.ch/de/impressum",
    "https://www.gerichte-zh.ch/de/startseite",
    "https://www.gerichte-zh.ch/de/datenschutz",
    "https://www.gerichte-zh.ch/de/karriere-old",
    "https://www.gerichte-zh.ch/de/organisation",
    "https://www.gerichte-zh.ch/de/themen/miete",
    "https://www.gerichte-zh.ch/de/themen/arbeit",
    "https://www.gerichte-zh.ch/de/themen/person",
    "https://www.gerichte-zh.ch/de/themen/verbot",
    "https://www.zh.ch/de/sicherheit-justiz.html",
    "https://www.gerichte-zh.ch/de/kreisschreiben",
    "https://www.zh.ch/de/gerichte-notariate.html",
    "https://www.zh.ch/en/gerichte-notariate.html",
    "https://www.gerichte-zh.ch/de/themen/erbschaft",
    "https://www.gerichte-zh.ch/de/karriere/benefits",
    "https://www.gerichte-zh.ch/de/themen/wertpapier",
    "https://www.gerichte-zh.ch/de/karriere/ueber-uns",
    "https://www.gerichte-zh.ch/de/themen/zinsrechner",
    "https://www.gerichte-zh.ch/de/medien/medienportal",
    "https://www.gerichte-zh.ch/de/themen/strafprozess",
    "https://www.gerichte-zh.ch/de/themen/zivilprozess",
    "https://www.gerichte-zh.ch/
```

## Step 12: Bash: Show sitemap summary result per host
```
SP=<scratchpad-overnight>; python3 -c "
import json
s=json.load(open('$SP/stage0/sitemaps_summary.json'))
r=s['result']
print(type(r))
if isinstance(r,dict):
  for k,v in r.items():
    if any(x in k for x in ['zh.ch','be.ch','bs.ch','baselland','so.ch','ag.ch','bern.ch','thun','zuerich']):
        print(k, json.dumps(v,ensure_ascii=False)[:600])
"
```
Result:
```
<class 'dict'>
www.zh.ch {"urls": 80504, "sitemaps_fetched": 45, "delay": 0.3, "log": ["robots 200", "https://www.zh.ch/bin/zhweb/publish/sitemap.xml 200 44", "https://www.zh.ch/de-ls.zhweb-sitemap.xml 200 1"]}
www.gerichte-zh.ch {"urls": 454, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.gerichte-zh.ch/sitemap.xml 200 454", "https://www.gerichte-zh.ch/sitemap_index.xml 404 0"]}
www.stadt-zuerich.ch {"urls": 0, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.stadt-zuerich.ch/sitemap.xml 404 0", "https://www.stadt-zuerich.ch/sitemap_index.xml 404 0"]}
www.zsg.justice.be.ch {"urls": 256, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.zsg.justice.be.ch/sitemap.xml 200 6", "https://www.zsg.justice.be.ch/de/sitemap.xml 200 127"]}
www.rsta.dij.be.ch {"urls": 130, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.rsta.dij.be.ch/sitemap.xml 200 6", "https://www.rsta.dij.be.ch/de/sitemap.xml 200 66"]}
www.svsa.sid.be.ch {"urls": 462, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.svsa.sid.be.ch/sitemap.xml 200 6", "https://www.svsa.sid.be.ch/de/sitemap.xml 200 229"]}
www.sv.fin.be.ch {"urls": 344, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.sv.fin.be.ch/sitemap.xml 200 6", "https://www.sv.fin.be.ch/de/sitemap.xml 200 172"]}
www.weu.be.ch {"urls": 955, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.weu.be.ch/sitemap.xml 200 6", "https://www.weu.be.ch/de/sitemap.xml 200 489"]}
www.bkd.be.ch {"urls": 1133, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.bkd.be.ch/sitemap.xml 200 6", "https://www.bkd.be.ch/de/sitemap.xml 200 697"]}
www.sta.be.ch {"urls": 545, "sitemaps_fetched": 10, "delay": 10.0, "log": ["robots 200", "https://www.sta.be.ch/sitemap.xml 200 9", "https://www.sta.be.ch/de/sitemap.xml 200 273"]}
www.akvb-gemeinden.bkd.be.ch {"urls": 167, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.akvb-gemeinden.bkd.be.ch/sitemap.xml 200 6", "https://www.akvb-gemeinden.bkd.be.ch/de/sitemap.xml 200 65"]}
www.be.ch {"urls": 155, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.be.ch/sitemap.xml 200 6", "https://www.be.ch/de/sitemap.xml 200 39"]}
www.bern.ch {"urls": 64203, "sitemaps_fetched": 1, "delay": 0.3, "log": ["robots 200", "https://www.bern.ch/sitemap.xml.gz 200 64203"]}
www.thun.ch {"urls": 189, "sitemaps_fetche
```

> Now topic candidates per canton (counts and a few shortest URLs).

## Step 13: Bash: Print topic candidates for SO, AG, BS
```
SP=<scratchpad-overnight>; python3 -c "
import json
s=json.load(open('$SP/stage0/sitemap_topic_candidates.json'))
for c in ['SO','AG','BS']:
    print('=======',c)
    for t,v in s.get(c,{}).items():
        print('--',t,v.get('count'))
        for u in v.get('shortest',[])[:25]:
            print('    ',u)
"
```
Result:
```
<persisted-output>
Output too large (39.3KB). Full output saved to: <claude-project-dir>/020cdda0-8dd0-4108-896f-cca0e5f386a1/tool-results/b0f5r8zaz.txt

Preview (first 2KB):
======= SO
-- courts 1258
     https://so.ch/gerichte/
     https://so.ch/gerichte/informationen/aktuell/
     https://so.ch/gerichte/informationen/downloads/
     https://so.ch/gerichte/informationen/linkseite/
     https://so.ch/gerichte/gerichtsverwaltung/leitung/
     https://so.ch/verwaltung/bau-und-justizdepartement/
     https://so.ch/gerichte/informationen/rechtsprechung/
     https://so.ch/gerichte/richteraemter/zustaendigkeit/
     https://so.ch/gerichte/weitere-gerichte/haftgericht/
     https://so.ch/gerichte/gerichtsverwaltung/informatik/
     https://so.ch/gerichte/informationen/aktuell/aktuell/
     https://so.ch/gerichte/obergericht/kontakt-kanzleien/
     https://so.ch/gerichte/informationen/prozessformulare/
     https://so.ch/gerichte/weitere-gerichte/steuergericht/
     https://so.ch/gerichte/obergericht/verhandlungskalender/
     https://so.ch/gerichte/weitere-gerichte/friedensrichter/
     https://so.ch/gerichte/informationen/verhandlungskalender/
     https://so.ch/gerichte/richteraemter/richteramt-thal-gaeu/
     https://so.ch/gerichte/informationen/nebenbeschaeftigungen/
     https://so.ch/verwaltung/bau-und-justizdepartement/aktuell/
     https://so.ch/verwaltung/staatskanzlei/legistik-und-justiz/
     https://so.ch/gerichte/weitere-gerichte/miete-gleichstellung/
     https://so.ch/gerichte/richteraemter/richteramt-olten-goesgen/
     https://so.ch/gerichte/weitere-gerichte/schaetzungskommission/
     https://so.ch/services/justizvollzug-opferauskunft-beantragen/
-- dogs 53
     https://so.ch/services/hundebiss-oder-gefaehrdung-durch-hund-melden/
     https://so.ch/verwaltung/staatskanzlei/eumzug/eumzug/familie-kinder-und-hunde/
     https://so.ch/services/haltung-eines-bewilligungspflichtigen-hundes-bewilligung-beantragen/
     https://so.ch/verwaltung/departement-des-innern/polizei/ueber-uns/sondergruppen/diensthunde/
     https://so.ch/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/
...
</persisted-output>
```

> Let me pull the AI claims for my cantons from the pre-check probe files (needed for claim checks).

## Step 14: Bash: Inspect courts S1 rows and probe structure
```
SP=<scratchpad-overnight>; head -c 3000 $SP/courts_s1_rows.py; echo; echo ----; python3 -c "
import json
d=json.load(open('$SP/courts_s1_probe.json'))
print(type(d), len(d))
print(json.dumps(d[0] if isinstance(d,list) else list(d.items())[0],ensure_ascii=False)[:800])
"
```
Result:
```
# S1 courts table as pasted by the user (Gemini answer, 2026-09-23). D: = shown as a direct link; G: = wrapped in google.com/search?q= (Gemini did not ground it).
# Columns: canton, court, homepage, fees, guidance, decisions. utm_source parameters stripped.
ZHG='https://www.gerichte-zh.ch'; BEZ='https://www.zsg.justice.be.ch/de/start'; BEV='https://www.vg.justice.be.ch/de/start'
LU='https://gerichte.lu.ch'; SZ='https://www.sz.ch/behoerden/rechtspflege-gerichte'; GL='https://www.gl.ch/verwaltung/gerichte'
ZG='https://gerichte-zg.ch'; FR='https://www.fr.ch/pouvoir-judiciaire'; SO='https://so.ch/gerichte'; BS='https://www.gerichte.bs.ch'
BL='https://www.baselland.ch/politik-und-behorden/gerichte'; SH='https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte'
AR='https://www.ar.ch/verwaltung/kantonsgericht'; AI='https://www.ai.ch/themen/staat-und-recht/gerichte'; SG='https://www.gerichte.sg.ch'
GR='https://www.justiz-gr.ch'; AG='https://www.ag.ch/de/gerichte'; TG='https://gerichte.tg.ch'; TI='https://www4.ti.ch/potere-giudiziario'
VD='https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv'; VS='https://tribunaux.vs.ch/fr'; NE='https://www.ne.ch/autorites/PJ'
GE='https://justice.ge.ch/fr'; JU='https://www.jura.ch/pju'
ROWS=[
('ZH','Obergericht',f'D:{ZHG}/',f'G:{ZHG}/themen/prozesskosten.html',f'D:{ZHG}/themen.html',f'D:{ZHG}/entscheide.html'),
('ZH','Verwaltungsgericht','G:https://www.zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html','D:https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht/informationen-zum-gerichtsverfahren.html','D:https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht.html','G:https://vgrzh.djiktzh.ch/'),
('ZH','Bezirksgerichte',f'D:{ZHG}/organisation/bezirksgerichte.html',f'G:{ZHG}/themen/prozesskosten.html',f'D:{ZHG}/themen.html',f'D:{ZHG}/entscheide.html'),
('BE','Obergericht',f'D:{BEZ}.html',f'G:{BEZ}/themen/zivilrecht/kosten-und-entschaedigungen/gerichtsgebuehren.html',f'G:{BEZ}/themen.html',f'G:{BEZ}/entscheide.html'),
('BE','Verwaltungsgericht',f'G:{BEV}.html',f'G:{BEV}/themen/kosten.html',f'G:{BEV}/themen.html',f'G:{BEV}/entscheide.html'),
('BE','Regionalgerichte',f'D:{BEZ}/ueber-uns/regionalgerichte.html',f'G:{BEZ}/themen/zivilrecht/kosten-und-entschaedigungen.html',f'G:{BEZ}/themen.html',f'G:{BEZ}/entscheide.html'),
('LU','Kantonsgericht',f'D:{LU}/organisation/kantonsgericht',f'G:{LU}/themen/gerichtsgebuehren',f'G:{LU}/themen',f'G:{LU}/entscheide'),
('LU',
```

## Step 15: Bash: List AI court claims and probe results for my cantons
```
SP=<scratchpad-overnight>; grep -nE "^\('(ZH|BE|BS|BL|SO|AG)'" $SP/courts_s1_rows.py; echo; python3 -c "
import json
d=json.load(open('$SP/courts_s1_probe.json'))
for u,v in d.items():
    if any(x in u for x in ['gerichte-zh','zh.ch','djiktzh','justice.be.ch','gerichte.bs.ch','bs.ch','baselland','so.ch','ag.ch']):
        print(v.get('code'), v.get('class'), v.get('size'), u, '->', v.get('final'), '|', (v.get('title') or '')[:60])
"
```
Result:
```
12:('ZH','Obergericht',f'D:{ZHG}/',f'G:{ZHG}/themen/prozesskosten.html',f'D:{ZHG}/themen.html',f'D:{ZHG}/entscheide.html'),
13:('ZH','Verwaltungsgericht','G:https://www.zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html','D:https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht/informationen-zum-gerichtsverfahren.html','D:https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht.html','G:https://vgrzh.djiktzh.ch/'),
14:('ZH','Bezirksgerichte',f'D:{ZHG}/organisation/bezirksgerichte.html',f'G:{ZHG}/themen/prozesskosten.html',f'D:{ZHG}/themen.html',f'D:{ZHG}/entscheide.html'),
15:('BE','Obergericht',f'D:{BEZ}.html',f'G:{BEZ}/themen/zivilrecht/kosten-und-entschaedigungen/gerichtsgebuehren.html',f'G:{BEZ}/themen.html',f'G:{BEZ}/entscheide.html'),
16:('BE','Verwaltungsgericht',f'G:{BEV}.html',f'G:{BEV}/themen/kosten.html',f'G:{BEV}/themen.html',f'G:{BEV}/entscheide.html'),
17:('BE','Regionalgerichte',f'D:{BEZ}/ueber-uns/regionalgerichte.html',f'G:{BEZ}/themen/zivilrecht/kosten-und-entschaedigungen.html',f'G:{BEZ}/themen.html',f'G:{BEZ}/entscheide.html'),
32:('SO','Obergericht & Verwaltungsgericht',f'G:{SO}/obergericht/',f'G:{SO}/gebuehren/',f'G:{SO}/themen/',f'G:{SO}/rechtsprechung/'),
33:('SO','Amtsgerichte',f'G:{SO}/amtsgerichte/',f'G:{SO}/gebuehren/',f'G:{SO}/themen/',f'G:{SO}/rechtsprechung/'),
34:('BS','Appellationsgericht',f'G:{BS}/',f'G:{BS}/kosten.html',f'G:{BS}/recht-hilfen.html',f'G:{BS}/rechtsprechung.html'),
35:('BS','Zivil- und Strafgericht',f'G:{BS}/',f'G:{BS}/kosten.html',f'G:{BS}/recht-hilfen.html',f'G:{BS}/rechtsprechung.html'),
36:('BL','Kantonsgericht',f'G:{BL}/kantonsgericht',f'G:{BL}/kosten',f'G:{BL}/themen',f'D:{BL}/rechtsprechung'),
37:('BL','Zivilkreisgerichte',f'G:{BL}/zivilkreisgerichte',f'G:{BL}/kosten',f'G:{BL}/themen',f'D:{BL}/rechtsprechung'),
48:('AG','Obergericht',f'D:{AG}/obergericht',f'G:{AG}/themen/kosten-gebuehren',f'G:{AG}/themen',f'G:{AG}/rechtsprechung'),
49:('AG','Verwaltungsgericht',f'G:{AG}/verwaltungsgericht',f'G:{AG}/themen/kosten-gebuehren',f'G:{AG}/themen',f'G:{AG}/rechtsprechung'),
50:('AG','Bezirksgerichte',f'G:{AG}/bezirksgerichte',f'G:{AG}/themen/kosten-gebuehren',f'G:{AG}/themen',f'G:{AG}/rechtsprechung'),

200 redirect-to-home 623161 https://www.gerichte-zh.ch/ -> https://www.gerichte-zh.ch/de | Z&uuml;rcher Zivilgerichte und Strafgerichte | www.gerichte-
404 http-404 599404 https://www.gerichte-zh.ch/themen/prozesskosten.html -> https://www.gerichte-zh.ch/them
```

> Now the S3a guidance and S3b/S4 AI claims for my cantons.

## Step 16: Bash: List AI guidance claims and probe results for my cantons
```
SP=<scratchpad-overnight>; head -c 1200 $SP/guidance_s3a_rows.py; echo; grep -nE "'(ZH|BE|BS|BL|SO|AG)'" $SP/guidance_s3a_rows.py | head -40; echo ----; python3 -c "
import json
d=json.load(open('$SP/guidance_s3a_probe.json'))
for u,v in d.items():
    if any(x in u for x in ['zh.ch','be.ch','bs.ch','baselland','so.ch','ag.ch','bl.ch']):
        print(v.get('code'), v.get('class'), v.get('size'), u, '->', v.get('final'), '|', (v.get('title') or '')[:60])
"
```
Result:
```
Exit code 1
# S3a guidance table as pasted by the user (Gemini, 2026-09-23). D: direct link, G: wrapped in google.com/search?q= (ungrounded). utm stripped.
BL='https://www.baselland.ch/politik-und-verwaltung/direktionen'
ROWS=[
('AG','dogs','G:https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde'),('AG','tax','G:https://www.ag.ch/de/verwaltung/dfr/steuern/steuern-natuerliche-personen/steuererklaerung'),('AG','school','G:https://www.ag.ch/de/verwaltung/bks/volksschule/schulbetrieb/schulferien'),('AG','road','G:https://www.ag.ch/de/verwaltung/dvs/strassenverkehrsamt'),
('LU','dogs','D:https://veterinaerdienst.lu.ch/hunde'),('LU','tax','D:https://steuerbuch.lu.ch'),('LU','school','G:https://volksschulbildung.lu.ch/schulbetrieb_organisation/so_schulferien'),('LU','road','D:https://strassenverkehrsamt.lu.ch'),
('SG','dogs','G:https://www.sg.ch/gesundheit-soziales/verbraucherschutz-veterinaerwesen/veterinaerwesen/hunde.html'),('SG','tax','D:https://www.sg.ch/steuern-finanzen/steuern/steuerbuch.html'),('SG','school','G:https://www.sg.ch/bildung-sport/volksschule/schulferien.html'),('SG','road','G:https://www.sg.ch/verkehr/strassenverkehrsamt.html'),
('TG','dogs','G:https://veterinaeramt.tg.ch/
4:('AG','dogs','G:https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde'),('AG','tax','G:https://www.ag.ch/de/verwaltung/dfr/steuern/steuern-natuerliche-personen/steuererklaerung'),('AG','school','G:https://www.ag.ch/de/verwaltung/bks/volksschule/schulbetrieb/schulferien'),('AG','road','G:https://www.ag.ch/de/verwaltung/dvs/strassenverkehrsamt'),
8:('SO','dogs','G:https://so.ch/staat/departemente/volkswirtschaftsdepartement/veterinaeramt/hunde/'),('SO','tax','G:https://so.ch/staat/departemente/finanzdepartement/steueramt/steuerbuch/'),('SO','school','G:https://so.ch/staat/departemente/departement-fuer-bildung-und-kultur/amt-fuer-volksschule/schulferien/'),('SO','road','G:https://so.ch/staat/departemente/bau-und-justizdepartement/motorfahrzeugkontrolle/'),
9:('BL','dogs',f'G:{BL}/volkswirtschafts-und-gesundheitsdirektion/amt-fuer-lebensmittelsicherheit-und-veterinaerwesen/veterinaerwesen/hunde'),('BL','tax',f'G:{BL}/finanz-und-kirchendirektion/steuerverwaltung/steuerbuch'),('BL','school',f'G:{BL}/bildungs-kultur-und-sportdirektion/pats/schulferien'),('BL','road',f'G:{BL}/sicherheitsdirektion/mfk'),
----
Traceback (most recent call last):
  File "<string>", line 4, in <module>
AttributeError: 'list' object has no attribute 'items'
```

## Step 17: Bash: Show S3a and S3b/S4 probe rows for my cantons
```
SP=<scratchpad-overnight>; python3 -c "
import json
for f in ['guidance_s3a_probe.json','s3b_s4_probe.json']:
    d=json.load(open('$SP/'+f))
    print('=====',f,type(d),len(d))
    print(json.dumps(d[0],ensure_ascii=False)[:500])
    for v in d:
        s=json.dumps(v)
        if any(x in s for x in ['\"ZH\"','\"BE\"','\"BS\"','\"BL\"','\"SO\"','\"AG\"']):
            print(v.get('canton'),v.get('topic') or v.get('kind'), v.get('code'), v.get('class'), v.get('url'), '->', v.get('final'), '|', (v.get('title') or '')[:60])
"; grep -nE "'(ZH|BE|BS|BL|SO|AG)'" $SP/s3b_s4_rows.py | head -40
```
Result:
```
===== guidance_s3a_probe.json <class 'list'> 69
{"canton": "AG", "topic": "dogs", "kind": "G", "url": "https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde", "code": "404", "cls": "http-404", "final": "https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde", "title": "404-Seite - Kanton Aargau", "size": 61442}
AG dogs 404 None https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde -> https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde | 404-Seite - Kanton Aargau
AG tax 404 None https://www.ag.ch/de/verwaltung/dfr/steuern/steuern-natuerliche-personen/steuererklaerung -> https://www.ag.ch/de/verwaltung/dfr/steuern/steuern-natuerliche-personen/steuererklaerung | 404-Seite - Kanton Aargau
AG school 404 None https://www.ag.ch/de/verwaltung/bks/volksschule/schulbetrieb/schulferien -> https://www.ag.ch/de/verwaltung/bks/volksschule/schulbetrieb/schulferien | 404-Seite - Kanton Aargau
AG road 404 None https://www.ag.ch/de/verwaltung/dvs/strassenverkehrsamt -> https://www.ag.ch/de/verwaltung/dvs/strassenverkehrsamt | 404-Seite - Kanton Aargau
SO dogs 404 None https://so.ch/staat/departemente/volkswirtschaftsdepartement/veterinaeramt/hunde/ -> https://so.ch/staat/departemente/volkswirtschaftsdepartement/veterinaeramt/hunde/ | 404 - Seite wurde nicht gefunden - Kanton Solothurn
SO tax 404 None https://so.ch/staat/departemente/finanzdepartement/steueramt/steuerbuch/ -> https://so.ch/staat/departemente/finanzdepartement/steueramt/steuerbuch/ | 404 - Seite wurde nicht gefunden - Kanton Solothurn
SO school 404 None https://so.ch/staat/departemente/departement-fuer-bildung-und-kultur/amt-fuer-volksschule/schulferien/ -> https://so.ch/staat/departemente/departement-fuer-bildung-und-kultur/amt-fuer-volksschule/schulferien/ | 404 - Seite wurde nicht gefunden - Kanton Solothurn
SO road 404 None https://so.ch/staat/departemente/bau-und-justizdepartement/motorfahrzeugkontrolle/ -> https://so.ch/staat/departemente/bau-und-justizdepartement/motorfahrzeugkontrolle/ | 404 - Seite wurde nicht gefunden - Kanton Solothurn
BL dogs 403 None https://www.baselland.ch/politik-und-verwaltung/direktionen/volkswirtschafts-und-gesundheitsdirektion/amt-fuer-lebensmittelsicherheit-und-veterinaerwesen/veterinaerwesen/hunde -> https://www.baselland.ch/politik-und-verwaltung/direktionen/volkswirtschafts-und-gesundheitsdirektion/amt-fuer-lebensmittelsicherheit-und-veterinaerwesen/veterinaerwesen/hunde | Just a moment...
BL tax 403 None https://www.baselland.ch/politik-und-ve
```

> Now opencaselaw coverage for my six cantons.

## Step 18: Bash: List opencaselaw court coverage for my cantons
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/opencaselaw_courts_2026-09-23.json'))
print(type(d), (list(d.keys()) if isinstance(d,dict) else len(d)))
rows=d if isinstance(d,list) else d.get('courts') or d.get('result') or d
if isinstance(rows,dict): 
    print(json.dumps(rows,ensure_ascii=False)[:600])
else:
    print(json.dumps(rows[0],ensure_ascii=False))
    for r in rows:
        if r.get('canton') in ('ZH','BE','BS','BL','SO','AG'):
            print(r.get('canton'), r.get('code') or r.get('court'), r.get('decision_count'), r.get('earliest'), r.get('latest'), '|', (r.get('name') or r.get('name_de') or '')[:70])
"
```
Result:
```
<class 'list'> 136
{"court": "bger", "canton": "CH", "decision_count": 193393, "earliest": "1986-10-06", "latest": "2026-09-10", "languages": 3, "sparse": false}
ZH zh_sozialversicherungsgericht 34715 1981-01-21 2026-06-17 | 
ZH zh_obergericht 28301 1980-04-15 2026-07-29 | 
BL bl_gerichte 19453 1962-06-08 2026-06-03 | 
SO so_gerichte 13587 1956-11-07 2026-09-08 | 
ZH zh_verwaltungsgericht 12637 1960-06-21 2026-08-28 | 
BE be_verwaltungsgericht 12109 1962-01-12 2026-08-24 | 
BS bs_appellationsgericht 8786 1996-07-17 2026-09-03 | 
BE be_zivilstraf 6039 1979-07-04 2026-08-03 | 
ZH zh_handelsgericht 4680 2001-05-21 2026-06-04 | 
AG ag_gerichte 2834 1931-03-26 2025-12-12 | 
BS bs_sozialversicherungsgericht 2230 2013-06-03 2026-06-18 | 
AG ag_strafgericht 2160 1999-08-24 2026-09-08 | 
BE be_bvd 2094 1998-09-18 2025-12-11 | 
AG ag_versicherungsgericht 2088 1995-12-11 2026-07-31 | 
AG ag_zivilgericht 1942 1992-11-18 2026-08-28 | 
AG ag_verwaltungsgericht 1909 1923-09-07 2026-09-03 | 
ZH zh_kassationsgericht 1454 1995-12-13 2012-06-25 | 
ZH zh_gerichte 1438 1998-08-10 2025-11-05 | 
AG ag_spezialverwaltungsgericht 1213 1940-12-09 2026-06-17 | 
ZH zh_baurekursgericht 1162 1935-09-17 2026-06-26 | 
ZH zh_steuerrekursgericht 903 1982-04-06 2026-05-28 | 
BE be_weitere 840 2002-05-31 2025-12-18 | 
ZH zh_arbeitsgericht 653 2002-02-27 2026-06-23 | 
ZH zh_bezirksgericht_zuerich 417 2000-02-08 2026-07-29 | 
BE be_steuerrekurs 343 2013-03-09 2025-12-16 | 
AG ag_handelsgericht 336 2003-12-31 2026-08-27 | 
AG ag_regierungsrat 248 2000-09-06 2026-05-27 | 
BE be_direktionen 217 2018-06-01 2026-07-02 | 
AG ag_baugesetzgebung 198 1968-07-09 2021-08-20 | 
ZH zh_mietgericht 186 2006-02-23 2026-09-03 | 
ZH zh_bezirksgericht_horgen 102 2011-10-27 2026-04-02 | 
AG ag_departement_bvu 97 2007-01-10 2026-01-28 | 
BE be_anwaltsaufsicht 78 2014-02-19 2026-08-11 | 
ZH zh_bezirksgericht_winterthur 76 2014-06-26 2026-05-26 | 
ZH zh_bezirksgericht_dielsdorf 73 2009-08-10 2026-08-03 | 
ZH zh_bezirksgericht_meilen 68 2010-12-21 2026-06-22 | 
ZH zh_bezirksgericht_dietikon 67 2012-06-18 2026-04-14 | 
ZH zh_bezirksgericht_buelach 57 2007-06-04 2026-07-14 | 
ZH zh_bezirksgericht_hinwil 49 2019-07-11 2026-03-27 | 
ZH zh_bezirksgericht_uster 41 2006-12-12 2026-02-13 | 
AG ag_departement_vi 38 1999-06-11 2021-11-08 | 
BS bs_steuerrekurskommission 37 2022-01-20 2024-03-21 | 
AG ag_anwaltskommission 32 1999-04-28 2020-06-30 | 
ZH zh_bezirksgericht_pfaeffikon 30 2020-08-19 2026-03-16 | 
AG ag_weitere 24 2001
```

> Inputs are read. Now I'll build a small probe helper (status, title, links, words, sample grep) that keeps a per-host delay, so BE/BS get their 10 s crawl delay.

## Step 19: Write: /tmp/sg-verify-run3-a/probe.py
```
#!/usr/bin/env python3
"""Probe helper: fetch URL(s) with curl, report status/ctype/size/final/title/links/words and optional regex samples.
Keeps a per-host minimum delay (state in /tmp/sg-verify-run3-a/.lastreq.json) so crawl-delay hosts are respected.
Usage: probe.py [-g REGEX] [-s] [-o OUTFILE] URL [URL...]
  -g REGEX  print up to 5 matching text snippets (after tag stripping)
  -s        save body to /tmp/sg-verify-run3-a/pages/<slug>
  -H        print hrefs matching -f FILTER
"""
import hashlib, html, json, os, re, subprocess, sys, time
from urllib.parse import urlparse

BASE = "/tmp/sg-verify-run3-a"
STATE = os.path.join(BASE, ".lastreq.json")
PAGES = os.path.join(BASE, "pages")
os.makedirs(PAGES, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 swiss-grounding-check"
SLOW = {"be.ch": 10.5, "bs.ch": 10.5, "sz.ch": 3.5, "gl.ch": 3.5}


def delay_for(host):
    for suf, d in SLOW.items():
        if host == suf or host.endswith("." + suf):
            return d, suf
    return 0.4, host


def wait(host):
    d, key = delay_for(host)
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    last = st.get(key, 0)
    now = time.time()
    if now - last < d:
        time.sleep(d - (now - last))
    st[key] = time.time()
    json.dump(st, open(STATE, "w"))


def fetch(url, accept=None):
    host = urlparse(url).hostname or ""
    wait(host)
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    slug = re.sub(r"[^A-Za-z0-9]+", "_", url.split("//", 1)[-1])[:80] + "_" + h
    out = os.path.join(PAGES, slug)
    cmd = ["curl", "-g", "-sL", "--compressed", "-m", "40", "-A", UA, "-o", out, "-w",
           "%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}"]
    if accept:
        cmd += ["-H", "Accept: " + accept]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    parts = (r.stdout or "000\t\t0\t" + url).split("\t")
    return parts, out


def analyse(path, ctype):
    try:
        raw = open(path, "rb").read()
    except FileNotFoundError:
        return {}, "", b""
    txt = raw.decode("utf-8", "replace")
    info = {}
    if "html" in (ctype or "") or txt.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        m = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
        info["title"] = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip())[:90] if m else ""
        info["links"] = len(re.findall(r"<a\s[^>]*href", txt, re.I))
        body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", txt)
        body = re.sub(r"(?s)<[^>]+>", " ", body)
        body = html.unescape(re.sub(r"\s+", " ", body))
        info["words"] = len(body.split())
        return info, body, raw
    return info, txt, raw


def main():
    args = sys.argv[1:]
    grep = None; save = False; hrefs = None; accept = None
    urls = []
    i = 0
    while i < len(args):
        a = args[i]
  
```
Result:
```
File created successfully at: /tmp/sg-verify-run3-a/probe.py (file state is current in your context — no need to Read it back)
```

> Breadth pass first. I'll start with local sitemap greps (no network) for SO and AG, which have no prior coverage.

## Step 20: Bash: Count SO/AG sitemap URLs and SO court sections
```
SM=<scratchpad-overnight>/stage0/sitemaps; wc -l $SM/so.ch.txt $SM/www.ag.ch.txt; echo "--- SO gerichte top-level sections"; grep -oE "^https://so.ch/gerichte/[^/]+/[^/]+/" $SM/so.ch.txt | sort | uniq -c | sort -rn | head -40
```
Result:
```
    8908 <scratchpad-overnight>/stage0/sitemaps/so.ch.txt
   39510 <scratchpad-overnight>/stage0/sitemaps/www.ag.ch.txt
   48418 total
--- SO gerichte top-level sections
  10 https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/
   5 https://so.ch/gerichte/weitere-gerichte/schaetzungskommission/
   4 https://so.ch/gerichte/weitere-gerichte/steuergericht/
   4 https://so.ch/gerichte/richteraemter/richteramt-thal-gaeu/
   4 https://so.ch/gerichte/richteraemter/richteramt-solothurn-lebern/
   4 https://so.ch/gerichte/richteraemter/richteramt-olten-goesgen/
   4 https://so.ch/gerichte/richteraemter/richteramt-dorneck-thierstein/
   4 https://so.ch/gerichte/richteraemter/richteramt-bucheggberg-wasseramt/
   4 https://so.ch/gerichte/obergericht/weisungen-kreisschreiben/
   3 https://so.ch/gerichte/richteraemter/zustaendigkeit/
   3 https://so.ch/gerichte/obergericht/leitung-kammern/
   2 https://so.ch/gerichte/weitere-gerichte/jugendgericht/
   2 https://so.ch/gerichte/informationen/aktuell/
   1 https://so.ch/gerichte/weitere-gerichte/versicherungs-und-verwaltungsgericht/
   1 https://so.ch/gerichte/weitere-gerichte/miete-gleichstellung/
   1 https://so.ch/gerichte/weitere-gerichte/haftgericht/
   1 https://so.ch/gerichte/weitere-gerichte/friedensrichter/
   1 https://so.ch/gerichte/richteraemter/organisation-der-richteraemter/
   1 https://so.ch/gerichte/obergericht/weisungen-und-kreisschreiben/
   1 https://so.ch/gerichte/obergericht/verhandlungskalender/
   1 https://so.ch/gerichte/obergericht/kontakt-kanzleien/
   1 https://so.ch/gerichte/informationen/verhandlungskalender/
   1 https://so.ch/gerichte/informationen/rechtsprechung/
   1 https://so.ch/gerichte/informationen/prozessformulare/
   1 https://so.ch/gerichte/informationen/nebenbeschaeftigungen/
   1 https://so.ch/gerichte/informationen/linkseite/
   1 https://so.ch/gerichte/informationen/elektronischer-rechtsverkehr/
   1 https://so.ch/gerichte/informationen/downloads/
   1 https://so.ch/gerichte/gerichtsverwaltung/zentrale-gerichtskasse/
   1 https://so.ch/gerichte/gerichtsverwaltung/reglemente-weisungen/
   1 https://so.ch/gerichte/gerichtsverwaltung/leitung/
   1 https://so.ch/gerichte/gerichtsverwaltung/informatik/
```

## Step 21: Bash: List SO court URLs and count topic matches
```
SM=<scratchpad-overnight>/stage0/sitemaps; echo "so.ch/gerichte/ URLs: $(grep -c '^https://so.ch/gerichte/' $SM/so.ch.txt)"; grep '^https://so.ch/gerichte/' $SM/so.ch.txt | head -90; echo "--- SO topic greps"; for p in hund steuerbuch steuer ferien schulferien motorfahrzeug strassenverkehr gemeinden amtsblatt staatskanzlei friedensricht schlicht kosten gebuehr; do echo "$p: $(grep -ic "$p" $SM/so.ch.txt)"; done
```
Result:
```
so.ch/gerichte/ URLs: 73
https://so.ch/gerichte/
https://so.ch/gerichte/gerichtsverwaltung/informatik/
https://so.ch/gerichte/gerichtsverwaltung/leitung/
https://so.ch/gerichte/gerichtsverwaltung/reglemente-weisungen/
https://so.ch/gerichte/gerichtsverwaltung/zentrale-gerichtskasse/
https://so.ch/gerichte/informationen/aktuell/
https://so.ch/gerichte/informationen/aktuell/aktuell/
https://so.ch/gerichte/informationen/downloads/
https://so.ch/gerichte/informationen/elektronischer-rechtsverkehr/
https://so.ch/gerichte/informationen/linkseite/
https://so.ch/gerichte/informationen/nebenbeschaeftigungen/
https://so.ch/gerichte/informationen/prozessformulare/
https://so.ch/gerichte/informationen/rechtsprechung/
https://so.ch/gerichte/informationen/verhandlungskalender/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/01062016-verwaltungsgericht/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/09052016-zivilkammer/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/13012016-strafkammer/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/13042016-verwaltungsgericht/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/14062016-verwaltungsgericht/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/17092015-zivilkammer/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/19042016-strafkammer/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/21062016-zivilkammer/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/23122015-strafkammer/
https://so.ch/gerichte/obergericht/ausgewaehlte-entscheide/urteile/25022016-verwaltungsgericht/
https://so.ch/gerichte/obergericht/kontakt-kanzleien/
https://so.ch/gerichte/obergericht/leitung-kammern/gerichtsschreiber/
https://so.ch/gerichte/obergericht/leitung-kammern/kammern-und-gerichte/
https://so.ch/gerichte/obergericht/leitung-kammern/richter-leitung/
https://so.ch/gerichte/obergericht/verhandlungskalender/
https://so.ch/gerichte/obergericht/weisungen-kreisschreiben/amtschreibereien/
https://so.ch/gerichte/obergericht/weisungen-kreisschreiben/obergericht-allgemein/
https://so.ch/gerichte/obergericht/weisungen-kreisschreiben/schuldbetreibung-konkurs/
https://so.ch/gerichte/obergericht/weisungen-kreisschreiben/strafrecht/
https://so.ch/gerichte/obergericht/weisungen-und-kreisschreiben/zivilrecht/
https://so.ch/gerichte/richteraemter/organisation-der-richteraemter/
https://so.ch/gerichte
```

## Step 22: Bash: Grep SO sitemap for guidance topics
```
SM=<scratchpad-overnight>/stage0/sitemaps; for p in hund steuerbuch ferien strassenverkehr amtsblatt schlicht gebuehr; do echo "=== $p"; grep -i "$p" $SM/so.ch.txt | grep -v '\.pdf$' | awk '{print length, $0}' | sort -n | cut -d' ' -f2- | head -14; done; echo "=== motorfahrzeugkontrolle (short)"; grep -i "motorfahrzeugkontrolle" $SM/so.ch.txt | awk '{print length, $0}' | sort -n | cut -d' ' -f2- | head -15; echo "=== gemeinden (short)"; grep -i "gemeinden" $SM/so.ch.txt | awk '{print length, $0}' | sort -n | cut -d' ' -f2- | head -20
```
Result:
```
=== hund
https://so.ch/services/hundebiss-oder-gefaehrdung-durch-hund-melden/
https://so.ch/verwaltung/staatskanzlei/eumzug/eumzug/familie-kinder-und-hunde/
https://so.ch/services/haltung-eines-bewilligungspflichtigen-hundes-bewilligung-beantragen/
https://so.ch/verwaltung/departement-des-innern/polizei/ueber-uns/sondergruppen/diensthunde/
https://so.ch/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/spezialseiten/mein-hund-und-ich/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-wald-jagd-und-fischerei/wildtiere/neozoen/marderhund/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-wald-jagd-und-fischerei/wildtiere/mit-hund-im-wald-leinenpflicht/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-wald-jagd-und-fischerei/wald/freizeit-und-erholung/mit-hund-im-wald/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/leinenpflicht/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/coupierte-hunde/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/auffaellige-hunde/
https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/spezialseiten/mein-hund-und-ich-kennzeichnung-und-registrierung/
=== steuerbuch
https://so.ch/verwaltung/finanzdepartement/steueramt/solothurner-steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/informationen/newsletter/newsletter-01-2024/steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/informationen/newsletter/newsletter-01-2025/steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/informationen/newsletter/newsletter-01-2026/steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/informationen/newsletter/newsletter-02-2024/steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/informationen/newsletter/newsletter-02-2025/steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/informationen/newsletter/newsletter-02-2026/steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/informationen/newsletter/newsletter-03-2025/steuerbuch/
https://so.ch/verwaltung/finanzdepartement/steueramt/inform
```

> SO candidates are clear. I'll probe them in the background while grepping the AG sitemap.

## Step 23: Bash: Probe SO court pages for fees and conciliation
```
cd /tmp/sg-verify-run3-a && python3 probe.py -g "(CHF|Fr\.)\s?[0-9]|Gebühr|Kostenvorschuss" https://so.ch/gerichte/ https://so.ch/gerichte/informationen/downloads/ https://so.ch/gerichte/informationen/rechtsprechung/ https://so.ch/gerichte/gerichtsverwaltung/zentrale-gerichtskasse/ https://so.ch/gerichte/gerichtsverwaltung/reglemente-weisungen/ https://so.ch/gerichte/richteraemter/zustaendigkeit/zivilsachen/ https://so.ch/gerichte/weitere-gerichte/friedensrichter/ https://so.ch/gerichte/weitere-gerichte/miete-gleichstellung/ https://so.ch/verwaltung/departement-des-innern/departementssekretariat/oberaemter/schlichtung-und-vermittlung/mietschlichtung/ https://so.ch/services/schlichtungsverfahren-fuer-miete-und-pacht-schlichtungsgesuch/ > so_batch1.txt 2>&1; cat so_batch1.txt
```
Result:
```
Command running in background with ID: b198ort53. Output is being written to: <claude-tmp>/020cdda0-8dd0-4108-896f-cca0e5f386a1/tasks/b198ort53.output. You will be notified when it completes. To check interim output, use Read on that file path.
Session cwd remains <repo>; directory changes made by the backgrounded command do not apply to subsequent commands.
```

## Step 24: Bash: Summarise AG court URL sections in sitemap
```
SM=<scratchpad-overnight>/stage0/sitemaps; echo "ag gerichte URLs: $(grep -c 'gerichte-kanton-aargau' $SM/www.ag.ch.txt)"; grep -oE "^https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/[^/]+/?[^/]*" $SM/www.ag.ch.txt | sort | uniq -c | sort -rn | head -50
```
Result:
```
ag gerichte URLs: 140
  27 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/bezirksgerichte
  21 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/obergericht
  15 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/leitung-und-aufsicht
  14 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/schlichtungsbehoerden
  14 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/die-familiengerichte-als-kesb
  10 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/betreibungs-und-konkurswesen
   7 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/spezialverwaltungsgericht
   5 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/rechtliche-grundlagen/reglemente-und-kreisschreiben
   3 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/anwaltskommission
   2 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/justizgericht
   1 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/zahlen-fakten
   1 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/rechtliche-grundlagen
   1 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/zwangsmassnahmengericht
   1 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/organisation/startseite-gerichte
   1 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/leitbild
   1 https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/interessenbindungen
```

## Step 25: Bash: List AG court URLs outside Bezirks/Obergericht
```
SM=<scratchpad-overnight>/stage0/sitemaps; grep 'gerichte-kanton-aargau' $SM/www.ag.ch.txt | grep -vE '/organisation/(bezirksgerichte|obergericht)/' | head -80; echo; for p in rechtsprechung entscheid gerichtskost prozesskost unentgeltlich kostenvorschuss friedensricht schlichtung; do echo "$p: $(grep -ic "$p" $SM/www.ag.ch.txt)"; done
```
Result:
```
https://www.ag.ch/de/medien/medienmitteilungen?mm=der-geschaeftsbericht-der-gerichte-kanton-aargau-2019-ist-publiziert-0a676ffc-8b57-4b5f-9c12-f6d517c0829f_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=der-geschaeftsbericht-der-gerichte-kanton-aargau-2020-ist-publiziert-ec1c0d6d-415f-484c-a041-7fda85925709_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=der-geschaeftsbericht-der-gerichte-kanton-aargau-2021-ist-publiziert-301070ae-3fc3-44e3-8996-dbe0d65ab5b6_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=der-geschaeftsbericht-der-gerichte-kanton-aargau-2022-ist-publiziert-0d92beb7-55c8-4fe9-8676-3412d26f63c5_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=der-geschaeftsbericht-der-gerichte-kanton-aargau-2023-ist-publiziert-742d9d21-2adf-45a6-a668-c270b8cb4a78_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=der-geschaeftsbericht-der-gerichte-kanton-aargau-2024-ist-publiziert-1fecb5e1-8016-4aac-a2ab-7a63474db074_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=der-geschaeftsbericht-der-gerichte-kanton-aargau-2025-ist-publiziert-7feed101-6f2d-40f8-9551-2ad45579b3f7_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=die-gerichte-kanton-aargau-trafen-sich-unter-einem-dach-05a6b24e-f29a-4148-8acf-509720a394b3_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=geschaeftsbericht-der-gerichte-kanton-aargau-2014-407eee7e-d693-4ca9-b0ba-ff1719875d7c_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=geschaeftsbericht-der-gerichte-kanton-aargau-2015-37545aef-4ead-4440-9294-34cf30623708_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=geschaeftsbericht-der-gerichte-kanton-aargau-2016-22a111ed-383b-4cd2-8c95-86ec72ac7836_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=geschaeftsbericht-der-gerichte-kanton-aargau-2017-db614e8a-cb87-4984-8b07-e0967352182f_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=geschaeftsbericht-der-gerichte-kanton-aargau-2018-221e7701-1801-4168-9f3a-c97bf911e7f9_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=kommission-fuer-justiz-veroeffentlicht-bericht-der-finanzkontrolle-zur-sonderpruefung-der-gerichte-kanton-aargau-561dec9b-70dc-405b-b49c-8736bc24b894_de
https://www.ag.ch/de/medien/medienmitteilungen?mm=wahl-der-neuen-generalsekretaerin-der-gerichte-kanton-aargau-53e4d4ab-2c79-4d48-b951-97690310942a_de
https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau
https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/interessenbindungen
https://www.ag.ch/de/ueber-uns/gerichte-kanton-aargau/leitb
```

## Step 26: Bash: Show SO court probe results
```
cat /tmp/sg-verify-run3-a/so_batch1.txt
```
Result:
```
200 | text/html | 11731B | https://so.ch/gerichte/ | title='Gerichte - Kanton Solothurn' | links=54 | words=265 | file=/tmp/sg-verify-run3-a/pages/so_ch_gerichte__194e059326
   ~ (no match for (CHF|Fr\.)\s?[0-9]|Gebühr|Kostenvorschuss )
200 | text/html | 10717B | https://so.ch/gerichte/informationen/downloads/ | title='Downloads - Kanton Solothurn' | links=68 | words=160 | file=/tmp/sg-verify-run3-a/pages/so_ch_gerichte_informationen_downloads__be6cd3b8fc
   ~ (no match for (CHF|Fr\.)\s?[0-9]|Gebühr|Kostenvorschuss )
200 | text/html | 11258B | https://so.ch/gerichte/informationen/rechtsprechung/ | title='Rechtsprechung - Kanton Solothurn' | links=64 | words=325 | file=/tmp/sg-verify-run3-a/pages/so_ch_gerichte_informationen_rechtsprechung__c22dddf69a
   ~ e von Urteilen, die von geringem Interesse sind, wie z.B. Abschreibungsbeschlüsse infolge Nichtleistung eines Kostenvorschusses, routinemässige Rechtsöffnungsentscheide, u.a.). Die Entscheide der Beschwerdekammer werden nur publiziert, wenn die den Beschwerdeverfahren zugrun
200 | text/html | 11141B | https://so.ch/gerichte/gerichtsverwaltung/zentrale-gerichtskasse/ | title='Zentrale Gerichtskasse - Kanton Solothurn' | links=57 | words=202 | file=/tmp/sg-verify-run3-a/pages/so_ch_gerichte_gerichtsverwaltung_zentrale_gerichtskasse__cc83b74af1
   ~ (no match for (CHF|Fr\.)\s?[0-9]|Gebühr|Kostenvorschuss )
200 | text/html | 10439B | https://so.ch/gerichte/gerichtsverwaltung/reglemente-weisungen/ | title='Reglemente/Weisungen - Kanton Solothurn' | links=58 | words=149 | file=/tmp/sg-verify-run3-a/pages/so_ch_gerichte_gerichtsverwaltung_reglemente_weisungen__4c2bdadbf1
   ~ (no match for (CHF|Fr\.)\s?[0-9]|Gebühr|Kostenvorschuss )
200 | text/html | 12948B | https://so.ch/gerichte/richteraemter/zustaendigkeit/zivilsachen/ | title='Kompetenzen in Zivilsachen - Kanton Solothurn' | links=84 | words=731 | file=/tmp/sg-verify-run3-a/pages/so_ch_gerichte_richteraemter_zustaendigkeit_zivilsachen__adf0fda35d
   ~ tscheide im ordentlichen Verfahren nach Art. 236 bis 240 ZPO, also insbesondere bei einem Streitwert von über CHF 30'000.00. Arbeitsrechtliche Streitigkeiten Für arbeitsrechtliche Klagen ist das Gericht am Wohnsitz oder Sitz der beklagten Partei oder an dem Ort, an
   ~ htsorganisation, BGS 125.12). Ein arbeitsrechtliches Verfahren ist in aller Regel bis zu einem Streitwert von CHF 30'000.00 für die Parteien kostenlos. Hingegen besteht die Möglichkeit, dass die unterliegende Partei der obsiegenden eine Parteie
```

## Step 27: Bash: Inspect SO rechtsprechung/downloads links and fee mentions
```
cd /tmp/sg-verify-run3-a && python3 - <<'EOF'
import re,html,glob
def text(p):
    t=open(p,encoding='utf-8',errors='replace').read()
    b=re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>',' ',t); b=re.sub(r'(?s)<[^>]+>',' ',b); return html.unescape(re.sub(r'\s+',' ',b)), t
for slug,pat in [('so_ch_gerichte_informationen_rechtsprechung__','href'),('so_ch_gerichte_informationen_downloads__','href'),('so_ch_gerichte_weitere_gerichte_friedensrichter__','kost|gebühr|Fr\.|CHF'),('so_ch_verwaltung_departement_des_innern_departementssekretariat_oberaemter_schli','kost|gebühr|unentgelt')]:
    p=glob.glob('pages/'+slug+'*')[0]
    body,raw=text(p)
    print('=====',slug)
    if pat=='href':
        hs=[html.unescape(h) for h in re.findall(r'href="([^"]+)"',raw)]
        hs=[h for h in hs if not h.startswith('#') and ('/gerichte/' in h or 'http' in h or '.pdf' in h.lower() or 'fileadmin' in h)]
        seen=[]
        for h in hs:
            if h not in seen: seen.append(h)
        for h in seen[-45:]: print('  ',h)
    else:
        for m in re.finditer(pat,body,re.I):
            print('  ~',body[max(0,m.start()-150):m.end()+150])
EOF
```
Result:
```
===== so_ch_gerichte_informationen_rechtsprechung__
   https://so.ch/gerichte/informationen/rechtsprechung/
   /gerichte/
   /gerichte/informationen/aktuell/
   /gerichte/informationen/rechtsprechung/
   /gerichte/informationen/prozessformulare/
   /gerichte/informationen/downloads/
   /gerichte/informationen/verhandlungskalender/
   /gerichte/informationen/elektronischer-rechtsverkehr/
   /gerichte/informationen/nebenbeschaeftigungen/
   /gerichte/informationen/linkseite/
   https://karriere.so.ch
   https://my.so.ch
   /gerichte/richteraemter/zustaendigkeit/
   /gerichte/obergericht/kontakt-kanzleien/
   /gerichte/weitere-gerichte/versicherungs-und-verwaltungsgericht/
   /gerichte/gerichtsverwaltung/leitung/
   https://gerichtsentscheide.so.ch
   http://geo.so.ch/standortkarte/index.html?egid=2124260
   https://www.facebook.com/kantonsolothurn
   https://twitter.com/kantonsolothurn
   https://www.instagram.com/kantonsolothurn/
   https://ch.linkedin.com/company/kanton-solothurn
   https://karriere.so.ch/stellenmarkt/offene-stellen/
   https://amtsblatt.so.ch/
   http://bgs.so.ch/
   https://steuerbuch.so.ch/
===== so_ch_gerichte_informationen_downloads__
   https://so.ch/gerichte/informationen/downloads/
   /gerichte/
   /gerichte/informationen/aktuell/
   /gerichte/informationen/rechtsprechung/
   /gerichte/informationen/prozessformulare/
   /gerichte/informationen/downloads/
   /gerichte/informationen/verhandlungskalender/
   /gerichte/informationen/elektronischer-rechtsverkehr/
   /gerichte/informationen/nebenbeschaeftigungen/
   /gerichte/informationen/linkseite/
   https://karriere.so.ch
   https://my.so.ch
   /gerichte/richteraemter/zustaendigkeit/
   /gerichte/obergericht/kontakt-kanzleien/
   /gerichte/weitere-gerichte/versicherungs-und-verwaltungsgericht/
   /gerichte/gerichtsverwaltung/leitung/
   /fileadmin/internet/gerichte/gerichtsverwaltung/pdf/Gerichtsverwaltung/Rechenschaftsbericht_2025_01.pdf
   /fileadmin/internet/gerichte/gerichtsverwaltung/doc/1_Personalblatt_elektr.dotx
   /gerichte/obergericht/weisungen-kreisschreiben/obergericht-allgemein/
   /gerichte/gerichtsverwaltung/reglemente-weisungen/
   /gerichte/weitere-gerichte/friedensrichter/
   http://geo.so.ch/standortkarte/index.html?egid=2124260
   https://www.facebook.com/kantonsolothurn
   https://twitter.com/kantonsolothurn
   https://www.instagram.com/kantonsolothurn/
   https://ch.linkedin.com/company/kanton-solothurn
   https://karriere.so.ch/stellenmarkt/offene-stellen/
   h
```

> SO links point to gerichtsentscheide.so.ch, amtsblatt.so.ch and steuerbuch.so.ch. Probing the SO guidance, directory and gazette candidates next.

## Step 28: Bash: Probe SO guidance, directory, gazette, decisions pages
```
cd /tmp/sg-verify-run3-a && python3 probe.py -g "Leine|Leinenpflicht|Hundesteuer|Ferien|Sommerferien|Herbstferien|Fr\.\s?[0-9]|CHF\s?[0-9]|Gemeinde" https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/ https://so.ch/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/ https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/leinenpflicht/ https://steuerbuch.so.ch/ https://so.ch/verwaltung/finanzdepartement/steueramt/solothurner-steuerbuch/ https://so.ch/verwaltung/departement-fuer-bildung-kultur-und-sport/volksschulamt/aktuell/ferienplan/ https://so.ch/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/ https://so.ch/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/steuern-und-gebuehren/ https://so.ch/allgemeine-informationen/einwohnergemeinden/ https://so.ch/allgemeine-informationen/einwohnergemeinden/nach-bezirken/ https://so.ch/verwaltung/staatskanzlei/ https://amtsblatt.so.ch/ https://so.ch/verwaltung/staatskanzlei/publikationen/amtsblatt/ https://gerichtsentscheide.so.ch/ > so_batch2.txt 2>&1; cat so_batch2.txt
```
Result:
```
200 | text/html | 15448B | https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-landwirtschaft/tiere-und-lebensmittel/tierschutz/hunde/ | title='Hunde - Kanton Solothurn' | links=180 | words=596 | file=/tmp/sg-verify-run3-a/pages/so_ch_verwaltung_volkswirtschaftsdepartement_amt_fuer_landwirtschaft_tiere_und_l_85ba125efe
   ~ ldungen Hunde Akkordeon Button Akkordeon Button Auffällige Hunde Bewilligungspflichtige Hunde Coupierte Hunde Leinenpflicht Schutzdienst mit Hunden Gefundene und vermisste Tiere Gewerbsmässiger Umgang mit Tieren Akkordeon Button Akkordeon Button Gewerbsmässige Klau
   ~ Kontrollen Tierschutz Tierschutzmeldungen Hunde Auffällige Hunde Bewilligungspflichtige Hunde Coupierte Hunde Leinenpflicht Schutzdienst mit Hunden Gefundene und vermisste Tiere Gewerbsmässiger Umgang mit Tieren Enthornen und kastrieren Wildtierhaltung CITES Landsc
   ~ nderassen, zu den Pflichten der Hundehaltenden bezüglich Sicherheit und Haftpflicht, sowie die Regelungen zur Leinenpflicht, zur Kennzeichnung und Registrierung und zu den Abgaben. Gesetzliche Grundlagen Gesetz über das Halten von Hunden (Hundegesetz) Verordnung zu
   ~ S) Bereinigte Gesetzessammlung (BGS) Direktlinks Geoportal Medien Polizei Statistikportal Steuerbuch Einwohnergemeinden Gesetzliche Feiertage Staatskalender SO! Personalzeitschrift © 2026, Kanton Solothurn Rechtliches Impressum Offene Stellen Newsletter
200 | text/html | 16239B | https://so.ch/verwaltung/departement-des-innern/departementssekretariat/oberaemter/hundehaltung/ | title='Hundehaltung - Kanton Solothurn' | links=188 | words=824 | file=/tmp/sg-verify-run3-a/pages/so_ch_verwaltung_departement_des_innern_departementssekretariat_oberaemter_hunde_037894e81e
   ~ fängnis Der Schuldenfalle vorbeugen Ein Blick hinter die Kulissen der Pandemiebewältigung Teilzeitlehre für Alleinerziehende Mit Vereinbarungen zu besserer Integration Förderung gemeinnütziger Projekte Akkordeon Button Akkordeon Button Swisslos-Fonds Akkordeon Butt
   ~ nnen sie zum Beispiel Anordnungen über Erziehung, Pflege oder Unterbringung des Hundes veranlassen oder einen Leinen- und Maulkorbzwang erlassen. Links Hundehaltung Kanton Solothurn     Oberamt Region Solothurn Rötistrasse 4 4502 Solothurn Öffnungszeiten: Montag -
   ~ S) Bereinigte Gesetzessammlung (BGS) Direktlinks Geoportal Medien Polizei Statistikportal Steuerbuch Einwohnergemeinden Gesetzliche Feiertage Staatskalender SO! Personalzeitschrift © 2026, Kanton Solothurn Rechtliches Impressum Offene
```

> SO pages are server HTML. Let me extract real content lines (dog rule, Steuerbuch structure, Ferienplan PDF, MFK fees, commune links, gazette) from the saved files.

## Step 29: Bash: Extract SO dog rule and Steuerbuch links
```
cd /tmp/sg-verify-run3-a && python3 - <<'EOF'
import re,html,glob
def load(slug):
    p=glob.glob('pages/'+slug+'*')[0]; raw=open(p,encoding='utf-8',errors='replace').read()
    b=re.sub(r'(?is)<(script|style|noscript|nav|header|footer)[^>]*>.*?</\1>',' ',raw); b=re.sub(r'(?s)<[^>]+>',' ',b)
    return html.unescape(re.sub(r'\s+',' ',b)), raw
def hrefs(raw,pat):
    out=[]
    for h in re.findall(r'href="([^"]+)"',raw):
        h=html.unescape(h)
        if re.search(pat,h,re.I) and h not in out: out.append(h)
    return out
b,r=load('so_ch_verwaltung_volkswirtschaftsdepartement_amt_fuer_landwirtschaft_tiere_und_l_49184b1bac')
i=b.find('Leinenpflicht Leinenpflicht Seitennavigation'); 
m=re.search(r'(Hunde sind|Im Wald|Hunde müssen|an der Leine)[^.]*\.',b); print('LEINE:', m.group(0) if m else None)
for m in re.finditer(r'[^.]{0,200}(an der Leine|Leinenpflicht gilt|1\. April)[^.]{0,200}\.',b): print('  *',m.group(0).strip()[:400])
b,r=load('steuerbuch_so_ch__4f64bfd0c8'); hs=hrefs(r,r'.'); print('STEUERBUCH hrefs',len(hs)); print('  ',hs[:60])
EOF
```
Result:
```
LEINE: None
  * amit weder die Mutter- noch ihre Jungtiere in dieser sensiblen Zeit durch nicht unter der Kontrolle des Hundeführenden stehende Hunde gefährdet werden, gilt in den Solothurner Wäldern in der Zeit vom 1. April bis 31.
STEUERBUCH hrefs 115
   ['/Resources/libs.css?1787740380', '/Resources/Solr.css?1787740380', '/Resources/Main.css?1787740380', '/typo3temp/assets/compressed/merged-c6abf998b9eefc2fa3f3863351975baf.css?1788758456', '/_assets/00835a7ba7820699b5ef0d807a3bb069/Images/Favicon.ico', '//fonts.googleapis.com/css?family=Open+Sans:300italic,400italic,600italic,700italic,800italic,400,300,600,700,800', 'https://steuerbuch.so.ch/', '/typo3temp/assets/vhs/vhs-assets-922e445ccc6eb6c12c6b4a963c384ad3.css', '/', '#MainNavigation', '#Content', '/spezialseiten/suche/', 'https://steuerbuch.so.ch/steuern/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerpflicht/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerbare-einkuenfte-generalklausel/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerbare-einkuenfte-aus-unselbstaendiger-erwerbstaetigkeit-und-berufsauslagen/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerbare-einkuenfte-aus-selbstaendiger-erwerbstaetigkeit/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/ertraege-aus-beweglichem-vermoegen-und-vermoegensverwaltungskosten/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/ertraege-aus-unbeweglichem-vermoegen-und-liegenschaftskosten/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/renten-und-uebrige-einkommen/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/allgemeine-abzuege-und-sozialabzuege/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/tarif-und-steuerberechnung/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/zeitliche-bemessung/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/48-nr-1/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/48-nr-2/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/48-nr-3/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/49-nr-1/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/49-nr-2/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/50-nr-1/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/51-nr-1/', 'https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/52-nr-1/', 'https://steuerbuch.so.ch/steuern/
```

> steuerbuch.so.ch is a TYPO3 site with one page per entry. Checking its sitemap and one entry, plus the Ferienplan, MFK, commune and gazette details.

## Step 30: Bash: Probe steuerbuch.so.ch robots, sitemap and entries
```
cd /tmp/sg-verify-run3-a && python3 probe.py https://steuerbuch.so.ch/robots.txt https://steuerbuch.so.ch/sitemap.xml > so_b3.txt; cat so_b3.txt; head -c 600 $(awk -F'file=' 'NR==2{print $2}' so_b3.txt); echo; python3 probe.py -g "Steuerbuch|gültig|Stand|Nr\. 1" -f "\.pdf|fileadmin" https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/48-nr-1/ https://steuerbuch.so.ch/steuern/einkommenssteuer/allgemeine-abzuege-und-sozialabzuege/
```
Result:
```
200 | text/plain | 272B | https://steuerbuch.so.ch/robots.txt | title='-' | links=- | words=- | file=/tmp/sg-verify-run3-a/pages/steuerbuch_so_ch_robots_txt_a1c271b4e3
200 | application/xml | 316B | https://steuerbuch.so.ch/sitemap.xml | title='-' | links=- | words=- | file=/tmp/sg-verify-run3-a/pages/steuerbuch_so_ch_sitemap_xml_2a12443036
<?xml version="1.0" encoding="UTF-8"?><?xml-stylesheet type="text/xsl" href="/_assets/984e6ee9829f85eb447bb6a36455204a/CSS/Sitemap.xsl"?>

<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    
        <sitemap>
            <loc>https://steuerbuch.so.ch/sitemap.xml?sitemap=pages&amp;cHash=24b7400c2abd53b636ae62df3638e26a</loc>
            <lastmod>2026-09-11T16:01:11+02:00</lastmod>
        </sitemap>
    
</sitemapindex>

200 | text/html | 11680B | https://steuerbuch.so.ch/steuern/grundstueckgewinnsteuer/48-nr-1/ | title='Allgemeines - Steuern - Kanton Solothurn' | links=131 | words=1181 | file=/tmp/sg-verify-run3-a/pages/steuerbuch_so_ch_steuern_grundstueckgewinnsteuer_48_nr_1__ca11b78c41
   ~ llgemeine Abzüge und Sozialabzüge Tarif und Steuerberechnung Zeitliche Bemessung Grundstück-gewinnsteuer § 48 Nr. 1 § 48 Nr. 2 § 48 Nr. 3 § 49 Nr. 1 § 49 Nr. 2 § 50 Nr. 1 § 51 Nr. 1 § 52 Nr. 1 § 53 Nr. 1 § 54 Nr. 1 § 55 Nr. 1 § 56 Nr. 1 § 57 Nr. 1 § 58 Nr. 1 § 59 N
   ~ Tarif und Steuerberechnung Zeitliche Bemessung Grundstück-gewinnsteuer § 48 Nr. 1 § 48 Nr. 2 § 48 Nr. 3 § 49 Nr. 1 § 49 Nr. 2 § 50 Nr. 1 § 51 Nr. 1 § 52 Nr. 1 § 53 Nr. 1 § 54 Nr. 1 § 55 Nr. 1 § 56 Nr. 1 § 57 Nr. 1 § 58 Nr. 1 § 59 Nr. 1 § 59bis Nr. 1 Vermögenssteue
   ~ hnung Zeitliche Bemessung Grundstück-gewinnsteuer § 48 Nr. 1 § 48 Nr. 2 § 48 Nr. 3 § 49 Nr. 1 § 49 Nr. 2 § 50 Nr. 1 § 51 Nr. 1 § 52 Nr. 1 § 53 Nr. 1 § 54 Nr. 1 § 55 Nr. 1 § 56 Nr. 1 § 57 Nr. 1 § 58 Nr. 1 § 59 Nr. 1 § 59bis Nr. 1 Vermögenssteuer § 60 Nr. 1 § 62 Nr.
   ~ iche Bemessung Grundstück-gewinnsteuer § 48 Nr. 1 § 48 Nr. 2 § 48 Nr. 3 § 49 Nr. 1 § 49 Nr. 2 § 50 Nr. 1 § 51 Nr. 1 § 52 Nr. 1 § 53 Nr. 1 § 54 Nr. 1 § 55 Nr. 1 § 56 Nr. 1 § 57 Nr. 1 § 58 Nr. 1 § 59 Nr. 1 § 59bis Nr. 1 Vermögenssteuer § 60 Nr. 1 § 62 Nr. 1 § 62 Nr.
   ~ ung Grundstück-gewinnsteuer § 48 Nr. 1 § 48 Nr. 2 § 48 Nr. 3 § 49 Nr. 1 § 49 Nr. 2 § 50 Nr. 1 § 51 Nr. 1 § 52 Nr. 1 § 53 Nr. 1 § 54 Nr. 1 § 55 Nr. 1 § 56 Nr. 1 § 57 Nr. 1 § 58 Nr. 1 § 59 Nr. 1 § 59bis Nr. 1 Vermögenssteuer § 60 Nr. 1 § 62 Nr. 1 § 62 Nr. 2 § 66 Nr.
   hrefs matching '\\.pdf|fileadmin': 2
      /fileadmin/steuerbuch/aktuell/048-01_2017-0
```

## Step 31: Bash: Count SO Steuerbuch sitemap entries and test entry PDF
```
cd /tmp/sg-verify-run3-a && curl -sL -A "Mozilla/5.0 swiss-grounding-check" "https://steuerbuch.so.ch/sitemap.xml?sitemap=pages&cHash=24b7400c2abd53b636ae62df3638e26a" -o so_stb_pages.xml -w "%{http_code} %{size_download}\n"; python3 -c "
import re
t=open('/tmp/sg-verify-run3-a/so_stb_pages.xml').read()
locs=re.findall(r'<loc>([^<]+)</loc>',t)
print('locs',len(locs))
import collections
c=collections.Counter(l.split('/')[4] if len(l.split('/'))>5 else '(top)' for l in locs)
print(c.most_common(20))
ent=[l for l in locs if re.search(r'/\d+[a-z]*-nr-\d+/?$|nr-\d+/?$',l)]
print('entry-like (…-nr-N):',len(ent)); print(ent[:5])
"; curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o so_stb_048.pdf -w "%{http_code} %{content_type} %{size_download}\n" https://steuerbuch.so.ch/fileadmin/steuerbuch/aktuell/048-01_2017-09-26.pdf; python3 -c "
from pypdf import PdfReader
r=PdfReader('/tmp/sg-verify-run3-a/so_stb_048.pdf'); print('pages',len(r.pages)); print(r.pages[0].extract_text()[:500])"
```
Result:
```
200 69815
locs 175
[('einkommenssteuer', 98), ('grundstueckgewinnsteuer', 17), ('allgemeine-verfahrensgrundsaetze', 12), ('vermoegenssteuer', 10), ('veranlagung-im-ordentlichen-verfahren', 9), ('(top)', 5), ('rechtsmittel', 5), ('einzelfragen', 4), ('meta', 3), ('personalsteuer', 2), ('gewinn-und-kapitalsteuer-juristische-personen', 2), ('bezug', 2), ('suche', 1), ('404-seite-wurde-nicht-gefunden', 1), ('quellensteuer', 1), ('nebensteuern', 1), ('gemeindesteuern', 1), ('steuerstrafrecht', 1)]
entry-like (…-nr-N): 140
['https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerpflicht/8-nr-1/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerpflicht/10-nr-1/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerpflicht/13-nr-1/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerpflicht/14-nr-1/', 'https://steuerbuch.so.ch/steuern/einkommenssteuer/steuerpflicht/14-nr-2/']
200 application/pdf 98778
pages 3
  
Fassung vom 26.09.2017 In Kraft ab 01.10.2017 Ersetzt Fassung vom - 
 
Solothurner Steuerbuch   
 
Grundstückgewinnsteuer, Allgemeines  § 48 Nr. 1 
 
 
1 Gründe für die Besteuerung von Grundstückgewinnen  
Grundstücke werden oft mit Gewinn veräussert. Der Erlös aus dem Verkauf kann deu t-
lich höher sein als der Betrag, den man zu ihrer  Anschaffung auslegen musste. Die wic h-
tigsten Gründe für diese Wertsteigerung liegen einerseits im dauernden Nachfrageübe r-
hang nach Grundstücken, der ni
```

> SO Steuerbuch: 140 entry pages, each with a text-layer PDF. Now the Ferienplan, MFK fees, commune list and gazette details.

## Step 32: Bash: Extract SO holidays, MFK fees, communes, gazette details
```
cd /tmp/sg-verify-run3-a && python3 - <<'EOF'
import re,html,glob
def load(slug):
    p=glob.glob('pages/'+slug+'*')[0]; raw=open(p,encoding='utf-8',errors='replace').read()
    b=re.sub(r'(?is)<(script|style|noscript|nav|header|footer)[^>]*>.*?</\1>',' ',raw); b=re.sub(r'(?s)<[^>]+>',' ',b)
    return html.unescape(re.sub(r'\s+',' ',b)), raw
def hrefs(raw,pat):
    out=[]
    for h in re.findall(r'href="([^"]+)"',raw):
        h=html.unescape(h)
        if re.search(pat,h,re.I) and h not in out: out.append(h)
    return out
b,r=load('so_ch_verwaltung_departement_fuer_bildung_kultur_und_sport_volksschulamt_aktuell_2f8927727a')
i=b.find('Ferienplan Ferienplan Seitennavigation'); j=b.find('Seitennavigation',i+40)
m=re.search(r'Ferienplan Ferienplan Seitennavigation.*?(Der Ferienplan|Die Ferien|Ferienplan der|Schulferien)(.{0,900})',b)
print('FERIEN text:', m.group(1)+m.group(2) if m else b[i:i+1200])
print('FERIEN hrefs:', hrefs(r,r'\.pdf|\.xlsx|\.ics|fileadmin'))
b,r=load('so_ch_verwaltung_bau_und_justizdepartement_motorfahrzeugkontrolle_steuern_und_ge_8936de06c6')
for m in re.finditer(r'.{0,160}(CHF|Fr\.)\s?\d.{0,160}',b): print('MFK fee:',m.group(0))
print('MFK hrefs:', hrefs(r,r'\.pdf|rechner|tarif|gebuehr')[:15])
b,r=load('so_ch_allgemeine_informationen_einwohnergemeinden__0e116dd259')
ext=[h for h in hrefs(r,r'^https?://') if 'so.ch' not in h and 'facebook' not in h and 'twitter' not in h and 'instagram' not in h and 'linkedin' not in h]
print('GEMEINDEN external links:',len(ext), ext[:8])
print('GEMEINDEN internal:', [h for h in hrefs(r,r'einwohnergemeinden/') ][:12])
b,r=load('so_ch_verwaltung_staatskanzlei_publikationen_amtsblatt__642f747b69')
m=re.search(r'Amtsblatt Amtsblatt Seitennavigation(.{0,900})',b); print('AMTSBLATT page:', m.group(1)[:900] if m else '')
print('AMTSBLATT hrefs:', [h for h in hrefs(r,r'amtsblatt|shab') ])
print(open(glob.glob('pages/amtsblatt_so_ch__*')[0]).read()[:1400])
EOF
```
Result:
```
FERIEN text: 
FERIEN hrefs: ['/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2025-2026.pdf', '/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2026_2027.pdf', '/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2027_2028.pdf', '/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Schulfuehrung/schulleitungsliste.xlsx', '/fileadmin/internet/dbk/dbk-vsa/VSA/Ansprechpersonen_und_Zustaendigkeiten_Volksschulamt_August_2025_01.pdf', '/fileadmin/internet/dbk/dbk-vsa/Beratung/SPD/gebietszuteilung_spd.pdf', '/fileadmin/internet/dbk/dbk-vsa/VSA/Bildungsbericht_Nordwestschweiz_2017.pdf']
MFK hrefs: ['https://so.ch/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/steuern-und-gebuehren/', '/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/fuehrerinnen-und-fuehrer/administrativmassnahmen/verfahren-und-gebuehren/', '/verwaltung/bau-und-justizdepartement/motorfahrzeugkontrolle/steuern-und-gebuehren/', '/fileadmin/internet/bjd/bjd-mfk/Steuern-und-Gebuehren/PDF/614-61-1-2-de.pdf', '/fileadmin/internet/bjd/bjd-mfk/Steuern-und-Gebuehren/PDF/steuern_gebuehren_614.62.pdf', '/fileadmin/internet/bjd/bjd-mfk/Schifffahrt/PDF/Gesetz_ueber_die_Schiffssteuer.pdf', '/fileadmin/internet/bjd/bjd-mfk/Steuern-und-Gebuehren/PDF/revision_gebuehrentarif_1119.pdf']
GEMEINDEN external links: 98 ['http://www.aedermannsdorf.ch/', 'http://www.balm-balmberg.ch/', 'http://www.balsthal.ch/', 'http://www.baerschwil.ch/', 'http://www.baettwil.ch/', 'http://www.bellach.ch/', 'http://www.bettlach.ch/', 'http://www.biberist.ch/']
GEMEINDEN internal: ['https://so.ch/allgemeine-informationen/einwohnergemeinden/', '/allgemeine-informationen/einwohnergemeinden/', '/allgemeine-informationen/einwohnergemeinden/nach-bezirken/']
AMTSBLATT page: 
AMTSBLATT hrefs: ['https://so.ch/verwaltung/staatskanzlei/publikationen/amtsblatt/', '/verwaltung/staatskanzlei/publikationen/amtsblatt/', '/services/amtsblatt-abrufen-fuer-die-leserschaft/', '/services/amtsblattmeldungen-veroeffentlichen-fuer-publizierende-stellen/', 'https://amtsblattportal.ch/#!/publish/info/contact', 'https://amtsblattportal.ch/static/agb_de.pdf', 'https://amtsblattportal.ch/#!/publish/info/faq', 'https://amtsblatt.so.ch/']



<!DOCTYPE html>
<html lang="en" translate="no">
	<head>
		<!-- build version: 1.18.14-8272 -->
		<meta charset="utf-8"/>
		<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
		<meta name="google" content="notranslate">
		<meta htt
```

> SO gazette is the eSHAB/amtsblattportal app (JS). Checking the Ferienplan text and PDF, then the eSHAB API.

## Step 33: Bash: Read SO Ferienplan page text and PDF
```
cd /tmp/sg-verify-run3-a && python3 - <<'EOF'
import re,html,glob
p=glob.glob('pages/so_ch_verwaltung_departement_fuer_bildung_kultur_und_sport_volksschulamt_aktuell_2f8927727a*')[0]
raw=open(p,encoding='utf-8',errors='replace').read()
m=re.search(r'(?is)<main.*?</main>',raw) or re.search(r'(?is)id="Content".*',raw)
b=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',m.group(0)); b=re.sub(r'(?s)<[^>]+>',' ',b); b=html.unescape(re.sub(r'\s+',' ',b))
i=b.find('Ferienplan'); print(b[:1500])
EOF
curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o so_ferien_2627.pdf -w "%{http_code} %{content_type} %{size_download}\n" "https://so.ch/fileadmin/internet/dbk/dbk-vsa/Schulsystem/Ferienplan/Schulferienplan_2026_2027.pdf"; python3 -c "
from pypdf import PdfReader
r=PdfReader('/tmp/sg-verify-run3-a/so_ferien_2627.pdf'); print('pages',len(r.pages)); print(r.pages[0].extract_text()[:900])"
```
Result:
```
 Ferienplan Die Feriendaten der Volkschule unterscheiden sich nach Gemeinde und Region. Ferien im Schuljahr 2025/2026 (pdf, 122 KB) Ferien im Schuljahr 2025/2026 (pdf, 122 KB) Ferien im Schuljahr 2026/2027 (pdf, 124 KB) Ferien im Schuljahr 2026/2027 (pdf, 124 KB) Ferien im Schuljahr 2027/2028 (pdf, 120 KB) Ferien im Schuljahr 2027/2028 (pdf, 120 KB) Hier finden Sie die Feriendaten der Mittel- und Berufsfachschulen. Direktlinks Ferienplan Ferienplan Weitere Links Heilpädagogisches Schulzentrum Bildungsraum NW-CH Lehrerin/Lehrer werden Interkantonale Lehrmittelzentrale ILZ Download Adressen Schulleitungen (xlsx, 26 KB) Adressen Schulleitungen (xlsx, 26 KB) Ansprechpersonen und Zuständigkeiten Volksschulamt (pdf, 115 KB) Ansprechpersonen und Zuständigkeiten Volksschulamt (pdf, 115 KB) Ansprechpersonen und Gebietszuständigkeiten Schulpsychologischer Dienst (pdf, 64 KB) Ansprechpersonen und Gebietszuständigkeiten Schulpsychologischer Dienst (pdf, 64 KB) Bildungsbericht Nordwestschweiz 2017 (pdf, 2.74 MB) Bildungsbericht Nordwestschweiz 2017 (pdf, 2.74 MB) Volksschulamt Kreuzackerstrasse 1 Postfach 4502 Solothurn Öffnungszeiten: Montag, Mittwoch und Donnerstag: 08:00 – 11:30 Telefon 032 627 29 37 Telefon 032 627 29 37 vsa@dbk.so.ch vsa@dbk.so.ch Standort Standort 
200 application/pdf 126480
pages 8
Schulferienpläne der Volksschulen im Kanton Solothurn
Schuljahr 2026/2027
Beginn des Schuljahres: 10.08.2026
Schulträger Herbstferien Weihnachtsferien Winterferien Frühlingsferien Sommerferien Beginn Schuljahr 
2027/2028
Solothurn
Solothurn 28.09.2026 - 16.10.2026 21.12.2026 - 01.01.2027 08.02.2027 - 19.02.2027 12.04.2027 - 23.04.2027 12.07.2027 - 13.08.2027 16.08.2027
.
Lebern
BeLoSe                         
Bellach, Lommiswil, Selzach  28.09.2026 - 16.10.2026 21.12.2026 - 01.01.2027 08.02.2027 - 19.02.2027 12.04.2027 - 23.04.2027 12.07.2027 - 13.08.2027 16.08.2027
 
Bettlach 28.09.2026 - 16.10.2026 21.12.2026 - 01.01.2027 08.02.2027 - 19.02.2027 12.04.2027 - 23.04.2027 12.07.2027 - 13.08.2027 16.08.2027
Feldbrunnen-St. Niklaus 28.09.2026 - 16.10.2026 21.12.2026 - 01.01.2027 08.02.2027 - 19.02.2027 12.04.2027 - 23.04.2027 12.07.2027 - 13.08.2027 16.08.2027
Geslor
```

> SO holidays: one PDF per school year listing each Schulträger. Now testing the eSHAB (amtsblattportal) API behind amtsblatt.so.ch.

## Step 34: Bash: Probe eSHAB amtsblatt API endpoints
```
cd /tmp/sg-verify-run3-a && for u in "https://amtsblatt.so.ch/api/v1/current-tenant" "https://amtsblatt.so.ch/api/v1/publications?pageRequest.page=0&pageRequest.size=3" "https://amtsblattportal.ch/api/v1/publications?pageRequest.page=0&pageRequest.size=2&cantons=SO"; do echo "== $u"; curl -sL -A "Mozilla/5.0 swiss-grounding-check" -H "Accept: application/json" -o /tmp/sg-verify-run3-a/eshab.json -w "%{http_code} %{content_type} %{size_download}\n" "$u"; head -c 900 /tmp/sg-verify-run3-a/eshab.json; echo; done
```
**No result: this is the command that was waiting for approval when the run stalled.**
