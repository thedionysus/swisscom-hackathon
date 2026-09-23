# Run 3 agent D: progress before the stall (log a72833521bc1b1a64, 03:30–03:39 UTC 2026-09-23)

Extracted verbatim from the agent transcript. Results are truncated to 2,500 characters. The files it wrote under /tmp are gone.

> I'll start by reading the brief in full.

## Step 1: Bash: Count brief lines and create scratch dir
```
wc -l <scratchpad-overnight>/agent_brief_v5.md; mkdir -p /tmp/sg-verify-run3-d/
```
Result:
```
     295 <scratchpad-overnight>/agent_brief_v5.md
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

> Now let me read the input files listed in the addendum.

## Step 3: Bash: List scratchpad inputs and sitemaps
```
cd <scratchpad-overnight>/ && ls -la && ls -la stage0/ reports/ 2>/dev/null | head -80 && ls stage0/sitemaps/ | head -100
```
Result:
```
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
reports/:
total 144
drwxr-xr-x   8 <user>  wheel    256 Sep 23 03:26 .
drwx------  27 <user>  wheel    864 Sep 23 05:29 ..
-rw-r--r--   1 <user>  wheel   5855 Sep 23 03:24 g1-commune-law.md
-rw-r--r--   1 <user>  wheel   5179 Sep 23 03:15 g2-districts.md
-rw-r--r--   1 <user>  wheel   5667 Sep 23 03:26 g3-associations.md
-rw-r--r--   1 <user>  wheel   7205 Sep 23 03:10 g4-inte
```

## Step 4: Bash: Read precheck entry points file
```
cd <scratchpad-overnight>/ && cat precheck_entry_points_2026-09-23.md
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

## Step 5: Bash: Read law_hits.json for my five cantons
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('stage0/law_hits.json'))
print(type(d), list(d.keys())[:40] if isinstance(d,dict) else len(d))
for k in ['FR','VD','NE','GE','JU']:
    if k in d:
        print('=====',k)
        print(json.dumps(d[k], ensure_ascii=False, indent=1)[:6000])
"
```
Result:
```
<class 'dict'> ['AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH']
===== FR
{
 "conciliation": [
  {
   "nr": "862.2",
   "title": "Loi instituant un Office de conciliation en matière de conflits collectifs de travail",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/862.2"
  },
  {
   "nr": "862.21",
   "title": "Règlement d'exécution de la loi instituant un Office de conciliation en matière de conflits collectifs de travail",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/862.21"
  },
  {
   "nr": "122.70.19",
   "title": "Ordonnance sur l'organe de conciliation et d'arbitrage en matière de conflits collectifs de travail impliquant le personnel de l'Etat",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/122.70.19"
  }
 ],
 "dogs": [
  {
   "nr": "551.34",
   "title": "Ordonnance concernant les indemnités pour l'achat et l'entretien de chiens de police",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/551.34"
  },
  {
   "nr": "725.3",
   "title": "Loi sur la détention des chiens",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/725.3"
  },
  {
   "nr": "725.31",
   "title": "Règlement sur la détention des chiens",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/725.31"
  }
 ],
 "court_fees": [
  {
   "nr": "76.16",
   "title": "Tarif des frais de procédure en matière d'expropriation",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/76.16"
  },
  {
   "nr": "710.16",
   "title": "Ordonnance fixant le tarif des émoluments et des frais de procédure dans le domaine de l'aménagement du territoire et des constructions",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/710.16"
  },
  {
   "nr": "150.12",
   "title": "Tarif des frais de procédure et des indemnités en matière de juridiction administrative",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/150.12"
  }
 ],
 "holidays": [
  {
   "nr": "750.21",
   "title": "Arrêté concernant l'utilisation du domaine public ou privé de l'Etat en vue de la construction de maisons de vacances",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/750.21"
  },
  {
   "nr": "753.31",
   "title": "Arrêté instaurant des mesures concernant les maisons de vacances sur le domaine public et privé de l'Etat au bord du lac de Neuchâtel",
   "api": "https://bdlf.fr.ch/api/fr/texts_of_law/753.31"
  }
 ],
 "road": [
  {
   "nr": "781.1",
   "title": "Loi d'application de la législation fédérale sur la circulation routièr
```

## Step 6: Bash: Read the g5-guidance report for GE
```
cd <scratchpad-overnight>/ && cat reports/g5-guidance.md | head -400
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

## Step 7: Bash: Read sitemap summary for my hosts
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('stage0/sitemaps_summary.json'))
print(type(d))
if isinstance(d,dict):
    for k,v in d.items():
        if any(h in k for h in ['fr.ch','vd.ch','ne.ch','ge.ch','jura','geneve','lausanne','neuchatel','chaux','vernier','ocn','scan','justice']):
            print(k, json.dumps(v)[:600])
else:
    for x in d:
        s=json.dumps(x)
        if any(h in s for h in ['fr.ch','vd.ch','ne.ch','ge.ch','jura','geneve','lausanne','neuchatel','chaux','vernier','ocn','scan','justice']):
            print(s[:600])
"
```
Result:
```
<class 'dict'>
```

## Step 8: Bash: Inspect sitemap summary structure
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('stage0/sitemaps_summary.json'))
print(list(d.keys())[:50])
print(json.dumps(d, ensure_ascii=False)[:3000])
"
```
Result:
```
['hosts', 'result']
{"hosts": {"ZH": ["www.zh.ch", "www.gerichte-zh.ch", "www.stadt-zuerich.ch"], "BE": ["www.zsg.justice.be.ch", "www.rsta.dij.be.ch", "www.svsa.sid.be.ch", "www.sv.fin.be.ch", "www.weu.be.ch", "www.bkd.be.ch", "www.sta.be.ch", "www.akvb-gemeinden.bkd.be.ch", "www.be.ch", "www.bern.ch", "www.thun.ch"], "LU": ["www.lu.ch", "gerichte.lu.ch", "veterinaerdienst.lu.ch", "steuerbuch.lu.ch", "strassenverkehrsamt.lu.ch", "volksschulbildung.lu.ch"], "UR": ["www.ur.ch"], "SZ": ["www.sz.ch"], "OW": ["www.ow.ch"], "NW": ["www.nw.ch"], "GL": ["www.gl.ch"], "ZG": ["zg.ch"], "FR": ["www.fr.ch", "www.ocn.ch"], "SO": ["so.ch"], "BS": ["www.bs.ch"], "BL": ["www.baselland.ch"], "SH": ["sh.ch", "www.stadt-schaffhausen.ch"], "AR": ["ar.ch"], "AI": ["www.ai.ch"], "SG": ["www.sg.ch"], "GR": ["www.gr.ch"], "AG": ["www.ag.ch"], "TG": ["www.tg.ch", "strassenverkehrsamt.tg.ch", "staatskanzlei.tg.ch"], "TI": ["www4.ti.ch", "www.lugano.ch"], "VD": ["www.vd.ch", "www.lausanne.ch"], "VS": ["www.vs.ch"], "NE": ["www.ne.ch", "www.scan-ne.ch", "www.chaux-de-fonds.ch", "www.neuchatelville.ch"], "GE": ["www.ge.ch", "justice.ge.ch", "www.geneve.ch", "www.vernier.ch"], "JU": ["www.jura.ch"]}, "result": {"www.zh.ch": {"urls": 80504, "sitemaps_fetched": 45, "delay": 0.3, "log": ["robots 200", "https://www.zh.ch/bin/zhweb/publish/sitemap.xml 200 44", "https://www.zh.ch/de-ls.zhweb-sitemap.xml 200 1"]}, "www.gerichte-zh.ch": {"urls": 454, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.gerichte-zh.ch/sitemap.xml 200 454", "https://www.gerichte-zh.ch/sitemap_index.xml 404 0"]}, "www.stadt-zuerich.ch": {"urls": 0, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.stadt-zuerich.ch/sitemap.xml 404 0", "https://www.stadt-zuerich.ch/sitemap_index.xml 404 0"]}, "www.zsg.justice.be.ch": {"urls": 256, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.zsg.justice.be.ch/sitemap.xml 200 6", "https://www.zsg.justice.be.ch/de/sitemap.xml 200 127"]}, "www.rsta.dij.be.ch": {"urls": 130, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.rsta.dij.be.ch/sitemap.xml 200 6", "https://www.rsta.dij.be.ch/de/sitemap.xml 200 66"]}, "www.svsa.sid.be.ch": {"urls": 462, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.svsa.sid.be.ch/sitemap.xml 200 6", "https://www.svsa.sid.be.ch/de/sitemap.xml 200 229"]}, "www.sv.fin.be.ch": {"urls": 344, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 2
```

## Step 9: Bash: Show sitemap fetch results for my hosts
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('stage0/sitemaps_summary.json'))
for h in ['www.fr.ch','www.ocn.ch','www.vd.ch','www.lausanne.ch','www.ne.ch','www.scan-ne.ch','www.chaux-de-fonds.ch','www.neuchatelville.ch','www.ge.ch','justice.ge.ch','www.geneve.ch','www.vernier.ch','www.jura.ch']:
    print(h, json.dumps(d['result'].get(h), ensure_ascii=False))
"; wc -l stage0/sitemaps/www.fr.ch.txt stage0/sitemaps/www.ocn.ch.txt stage0/sitemaps/www.vd.ch.txt stage0/sitemaps/www.lausanne.ch.txt stage0/sitemaps/www.ne.ch.txt stage0/sitemaps/www.scan-ne.ch.txt stage0/sitemaps/www.chaux-de-fonds.ch.txt stage0/sitemaps/www.neuchatelville.ch.txt stage0/sitemaps/www.ge.ch.txt stage0/sitemaps/justice.ge.ch.txt stage0/sitemaps/www.geneve.ch.txt stage0/sitemaps/www.vernier.ch.txt stage0/sitemaps/www.jura.ch.txt
```
Result:
```
www.fr.ch {"urls": 67964, "sitemaps_fetched": 32, "delay": 0.3, "log": ["robots 200", "https://www.fr.ch/sitemap.xml 200 2", "https://www.fr.ch/sitemap_index.xml 404 0"]}
www.ocn.ch {"urls": 856, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.ocn.ch/sitemap.xml 200 856", "https://www.ocn.ch/sitemap_index.xml 404 0"]}
www.vd.ch {"urls": 27472, "sitemaps_fetched": 52, "delay": 0.3, "log": ["robots 200", "https://www.vd.ch/sitemap?type=1533906435 200 51", "https://www.vd.ch/sitemap/sitemap.xml?sitemap=pages&cHash=d42db98fb3b10972c3c0210f38ad09e4 200 1000"]}
www.lausanne.ch {"urls": 8201, "sitemaps_fetched": 3, "delay": 0.3, "log": ["robots 200", "https://www.lausanne.ch/sitemap.xml 200 2", "https://www.lausanne.ch/sitemaps/lausanne.xml 200 8002"]}
www.ne.ch {"urls": 0, "sitemaps_fetched": 4, "delay": 0.3, "log": ["robots 200", "https://www.ne.ch/sitemap.xml 200 2", "https://www.ne.ch/sitemap_index.xml 404 0"]}
www.scan-ne.ch {"urls": 0, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.scan-ne.ch/sitemap.xml 404 0", "https://www.scan-ne.ch/sitemap_index.xml 404 0"]}
www.chaux-de-fonds.ch {"urls": 0, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 404", "https://www.chaux-de-fonds.ch/sitemap.xml 500 0", "https://www.chaux-de-fonds.ch/sitemap_index.xml 500 0"]}
www.neuchatelville.ch {"urls": 867, "sitemaps_fetched": 4, "delay": 0.3, "log": ["robots 200", "https://www.neuchatelville.ch/sitemap.xml 200 2", "https://www.neuchatelville.ch/sitemap_index.xml 404 0"]}
www.ge.ch {"urls": 27978, "sitemaps_fetched": 15, "delay": 0.3, "log": ["robots 200", "https://www.ge.ch/sitemap.xml 200 14", "https://www.ge.ch/sitemap.xml?page=1 200 2000"]}
justice.ge.ch {"urls": 953, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://justice.ge.ch/sitemap.xml 200 953", "https://justice.ge.ch/sitemap_index.xml 404 0"]}
www.geneve.ch {"urls": 31218, "sitemaps_fetched": 18, "delay": 0.3, "log": ["robots 200", "https://www.geneve.ch/sitemap.xml 200 16", "https://www.geneve.ch/sitemap_index.xml 404 0"]}
www.vernier.ch {"urls": 2263, "sitemaps_fetched": 4, "delay": 0.3, "log": ["robots 200", "https://www.vernier.ch/sitemap.xml 200 2", "https://www.vernier.ch/sitemap_index.xml 404 0"]}
www.jura.ch {"urls": 7803, "sitemaps_fetched": 1, "delay": 0.3, "log": ["robots 200", "https://www.jura.ch/sitemap/Francais_fr_fr_z1_sitemap.xml 200 7803"]}
   67963 stage0/sitemaps/www.fr.ch.txt
     855 stage0/sitemaps/www.ocn.ch.txt
   27
```

## Step 10: Bash: Inspect opencaselaw courts JSON structure
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('opencaselaw_courts_2026-09-23.json'))
print(type(d), (list(d.keys()) if isinstance(d,dict) else len(d)))
rows = d if isinstance(d,list) else d.get('courts', d)
if isinstance(rows, dict):
    rows = list(rows.values()) if not isinstance(list(rows.values())[0], (int,str)) else rows
print(json.dumps(rows[:2] if isinstance(rows,list) else rows, ensure_ascii=False)[:800])
"
```
Result:
```
<class 'list'> 136
[{"court": "bger", "canton": "CH", "decision_count": 193393, "earliest": "1986-10-06", "latest": "2026-09-10", "languages": 3, "sparse": false}, {"court": "ge_gerichte", "canton": "GE", "decision_count": 170523, "earliest": "1908-11-08", "latest": "2026-09-14", "languages": 3, "sparse": false}]
```

## Step 11: Bash: List opencaselaw courts for my cantons
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('opencaselaw_courts_2026-09-23.json'))
for c in ['FR','VD','NE','GE','JU']:
    rows=[r for r in d if r['canton']==c]
    print('==',c, 'courts',len(rows),'total',sum(r['decision_count'] for r in rows))
    for r in sorted(rows,key=lambda r:-r['decision_count']):
        print('  ',r['court'],r['decision_count'],r['earliest'],r['latest'],'sparse' if r.get('sparse') else '', 'STALE' if r['latest']<'2026' else '')
"
```
Result:
```
Exit code 1
Traceback (most recent call last):
  File "<string>", line 8, in <module>
TypeError: '<' not supported between instances of 'NoneType' and 'str'
== FR courts 2 total 14771
   fr_gerichte 14768 2002-07-31 2027-07-27
```

## Step 12: Bash: List opencaselaw courts for my cantons
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('opencaselaw_courts_2026-09-23.json'))
for c in ['FR','VD','NE','GE','JU']:
    rows=[r for r in d if r['canton']==c]
    print('==',c, 'courts',len(rows),'total',sum(r['decision_count'] or 0 for r in rows))
    for r in sorted(rows,key=lambda r:-(r['decision_count'] or 0)):
        lt=r['latest'] or ''
        print('  ',r['court'],r['decision_count'],r['earliest'],r['latest'],'sparse' if r.get('sparse') else '', 'STALE' if lt<'2026' else '')
"
```
Result:
```
== FR courts 2 total 14771
   fr_gerichte 14768 2002-07-31 2027-07-27  
   fr_anwaltsaufsicht 3 None None sparse STALE
== VD courts 3 total 171392
   vd_findinfo 74714 1969-02-16 2025-12-20  STALE
   vd_gerichte 68645 1969-02-16 2026-09-03  
   vd_omni 28033 1958-10-27 2026-02-09  
== NE courts 2 total 12465
   ne_gerichte 10817 1913-04-02 2026-08-20  
   ne_jurisprudence_adm 1648 2003-10-27 2026-02-05  
== GE courts 2 total 170525
   ge_gerichte 170523 1908-11-08 2026-09-14  
   sav_kantone 2 None None sparse STALE
== JU courts 1 total 1201
   ju_gerichte 1201 2011-01-17 2026-09-03
```

## Step 13: Bash: Read courts_s1_rows.py header and my canton rows
```
cd <scratchpad-overnight>/ && head -60 courts_s1_rows.py && grep -n -i -E "'(FR|VD|NE|GE|JU)'|\"(FR|VD|NE|GE|JU)\"" courts_s1_rows.py | head -80
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

## Step 14: Bash: Inspect courts_s1_probe.json structure
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('courts_s1_probe.json'))
print(type(d), (list(d.keys())[:10] if isinstance(d,dict) else len(d)))
rows = d if isinstance(d,list) else d.get('results', d)
print(json.dumps(rows[0] if isinstance(rows,list) else list(rows.items())[0], ensure_ascii=False)[:600])
"
```
Result:
```
<class 'dict'> ['https://www.gerichte-zh.ch/', 'https://www.gerichte-zh.ch/themen/prozesskosten.html', 'https://www.gerichte-zh.ch/themen.html', 'https://www.gerichte-zh.ch/entscheide.html', 'https://www.zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html', 'https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht/informationen-zum-gerichtsverfahren.html', 'https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht.html', 'https://vgrzh.djiktzh.ch/', 'https://www.gerichte-zh.ch/organisation/bezirksgerichte.html', 'https://www.zsg.justice.be.ch/de/start.html']
["https://www.gerichte-zh.ch/", {"code": "200", "ct": "text/html", "size": 623161, "final": "https://www.gerichte-zh.ch/de", "title": "Z&uuml;rcher Zivilgerichte und Strafgerichte | www.gerichte-zh.ch", "links": 640, "words": 1302, "grounded": true, "class": "redirect-to-home"}]
```

## Step 15: Bash: Show probe results for my cantons' AI links
```
cd <scratchpad-overnight>/ && python3 -c "
import json
for fn in ['courts_s1_probe.json','guidance_s3a_probe.json','s3b_s4_probe.json']:
    d=json.load(open(fn))
    print('#####',fn)
    for u,v in d.items():
        if any(h in u for h in ['fr.ch','vd.ch','ne.ch','ge.ch','jura','geneve','lausanne','neuchatel','chaux','vernier','ocn','scan-ne','justice.ge','getax','fribourg','vaud','neuch','genev']):
            print(u, '|', v.get('code'), v.get('size'), v.get('final'), '|', (v.get('title') or '')[:70], '|', v.get('class'), v.get('grounded'))
"
```
Result:
```
Exit code 1
Traceback (most recent call last):
  File "<string>", line 6, in <module>
AttributeError: 'list' object has no attribute 'items'
##### courts_s1_probe.json
https://www.fr.ch/pouvoir-judiciaire/tribunal-cantonal | 404 72533 https://www.fr.ch/pouvoir-judiciaire/tribunal-cantonal | Page introuvable | Etat de Fribourg | http-404 False
https://www.fr.ch/pouvoir-judiciaire/frais-et-emoluments | 404 72533 https://www.fr.ch/pouvoir-judiciaire/frais-et-emoluments | Page introuvable | Etat de Fribourg | http-404 False
https://www.fr.ch/pouvoir-judiciaire/themes | 404 72533 https://www.fr.ch/pouvoir-judiciaire/themes | Page introuvable | Etat de Fribourg | http-404 False
https://www.fr.ch/pouvoir-judiciaire/jurisprudence | 404 72533 https://www.fr.ch/pouvoir-judiciaire/jurisprudence | Page introuvable | Etat de Fribourg | http-404 False
https://www.fr.ch/pouvoir-judiciaire/tribunaux-darrondissement | 404 72533 https://www.fr.ch/pouvoir-judiciaire/tribunaux-darrondissement | Page introuvable | Etat de Fribourg | http-404 False
https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/tribunal-cantonal | 200 33012 https://www.vd.ch/ojv/tribunal-cantonal | Tribunal cantonal | État de Vaud | redirect-elsewhere True
https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/frais-et-emoluments | 404 705564 https://www.vd.ch/ojv/frais-et-emoluments | Page non trouvée | État de Vaud | http-404 False
https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/themes | 404 705564 https://www.vd.ch/ojv/themes | Page non trouvée | État de Vaud | http-404 False
https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/jurisprudence | 404 705564 https://www.vd.ch/ojv/jurisprudence | Page non trouvée | État de Vaud | http-404 False
https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/cour-de-droit-administratif-et-public | 404 705564 https://www.vd.ch/ojv/cour-de-droit-administratif-et-public | Page non trouvée | État de Vaud | http-404 False
https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/tribunaux-darrondissement | 200 33895 https://www.vd.ch/ojv/tribunaux-darrondissement | Tribunaux d'arrondissement | État de Vaud | redirect-elsewhere True
https://www.ne.ch/autorites/PJ/TC | 404 484776 https://www.ne.ch/autorites/PJ/TC | 404 | ne.ch | http-404 False
https://www.ne.ch/autorites/PJ/frais | 404 484776 https://www.ne.ch/autorites/PJ/frais | 404 | ne.ch | http-404 False
https://www.ne.ch/autorites/PJ
```

## Step 16: Bash: Show S3a and S3b/S4 probe results for my cantons
```
cd <scratchpad-overnight>/ && python3 -c "
import json
for fn in ['guidance_s3a_probe.json','s3b_s4_probe.json']:
    d=json.load(open(fn))
    print('#####',fn, type(d), len(d))
    print(json.dumps(d[0], ensure_ascii=False)[:500])
    for v in d:
        s=json.dumps(v, ensure_ascii=False)
        if any(h in s for h in ['fr.ch','vd.ch','ne.ch','ge.ch','jura','geneve','lausanne','neuchatel','chaux','vernier','ocn','scan-ne','justice.ge','getax','\"FR\"','\"VD\"','\"NE\"','\"GE\"','\"JU\"']):
            print(s[:400])
"
```
Result:
```
##### guidance_s3a_probe.json <class 'list'> 69
{"canton": "AG", "topic": "dogs", "kind": "G", "url": "https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde", "code": "404", "cls": "http-404", "final": "https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde", "title": "404-Seite - Kanton Aargau", "size": 61442}
{"canton": "city-real", "topic": "Genève (homepage link)", "kind": "R", "url": "https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux", "code": "200", "cls": "ok", "final": "https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux", "title": "Règlements de la Ville de Genève Page 1 | Ville de Genève - ", "size": 105735}
{"canton": "city-real", "topic": "La Chaux-de-Fonds (homepage link)", "kind": "R", "url": "http://www.chaux-de-fonds.ch/rapports-et-reglements", "code": "200", "cls": "redirect", "final": "https://www.chaux-de-fonds.ch:443/rapports-et-reglements", "title": "Ville de La Chaux-de-Fonds", "size": 83414}
##### s3b_s4_probe.json <class 'list'> 76
{"src": "S3b", "canton": "VD", "topic": "dogs", "url": "https://www.vd.ch/themes/environnement/animaux/chiens", "code": "404", "cls": "http-404", "final": "https://www.vd.ch/environnement/animaux/chiens", "title": "Page non trouvée | État de Vaud", "size": 705564, "links": 5, "words": 78}
{"src": "S3b", "canton": "VD", "topic": "dogs", "url": "https://www.vd.ch/themes/environnement/animaux/chiens", "code": "404", "cls": "http-404", "final": "https://www.vd.ch/environnement/animaux/chiens", "title": "Page non trouvée | État de Vaud", "size": 705564, "links": 5, "words": 78}
{"src": "S3b", "canton": "VD", "topic": "tax", "url": "https://www.vd.ch/themes/etat-droit-finances/impots/pour-les-individus/remplir-ma-declaration-dimpot/instructions-g-et-annexes", "code": "404", "cls": "http-404", "final": "https://www.vd.ch/etat-droit-finances/impots/pour-les-individus/remplir-ma-declaration-dimpot/instructions-g-et-annexes", "title": "Page non trouvée | État de Vaud", "size"
{"src": "S3b", "canton": "VD", "topic": "school", "url": "https://www.vd.ch/themes/formation/scolarite-obligatoire/vacances-et-jours-feries", "code": "404", "cls": "http-404", "final": "https://www.vd.ch/formation/enseignement-obligatoire-et-pedagogie-specialisee/vacances-et-jours-feries", "title": "Page non trouvée | État de Vaud", "size": 705564, "links": 5, "words": 78}
{"src": "S3b", "canton": "VD", "topic": "road", "url": "https://www.vd.ch/
```

## Step 17: Bash: Read city links and AI rows for my cantons
```
cd <scratchpad-overnight>/ && cat cities_s2_links.txt; echo ----; grep -n -E "FR|VD|NE|GE|JU|Gen|Laus|Neuch|Chaux|Vernier" guidance_s3a_rows.py | head -40; echo ----; head -20 s3b_s4_rows.py; grep -n -E "'(FR|VD|NE|GE|JU)'" s3b_s4_rows.py
```
Result:
```
Zürich|https://www.stadt-zuerich.ch/portal/de/index/politik_u_recht/stadtrecht/systematische_rechtssammlung.html
Genève|https://www.geneve.ch/fr/autorites-administration/conseil-municipal/reglementation-municipale
Lausanne|https://www.lausanne.ch/officiel/statut-et-reglements/reglements-municipaux.html
Bern|https://www.bern.ch/politik-und-verwaltung/stadtrecht/systematische-rechtssammlung-bsr
Lugano|https://www.lugano.ch/amministrazione-servizi/regolamenti.html
Thun|https://www.thun.ch/politik-verwaltung/rechtssammlung/systematische-rechtssammlung-srt.html
La Chaux-de-Fonds|https://www.chaux-de-fonds.ch/autorites/conseil-general/reglements-communaux
Schaffhausen|https://www.stadt-schaffhausen.ch/politik/rechtssammlung.html
Vernier|https://www.vernier.ch/politique-et-administration/reglements-et-arretes
Neuchâtel|https://www.neuchatelville.ch/autorites-et-administration/conseil-general/reglements-communaux
----
----
# S3b (FR/IT guidance) and S4 (cantonal directories) as pasted by the user, 2026-09-23. Plain URLs, no Gemini wrapper signal.
ROWS=[
('S3b','VD','dogs','https://www.vd.ch/themes/environnement/animaux/chiens'),('S3b','VD','tax','https://www.vd.ch/themes/etat-droit-finances/impots/pour-les-individus/remplir-ma-declaration-dimpot/instructions-g-et-annexes'),('S3b','VD','school','https://www.vd.ch/themes/formation/scolarite-obligatoire/vacances-et-jours-feries'),('S3b','VD','road','https://www.vd.ch/themes/mobilite/automobile'),
('S3b','VS','dogs','https://www.vs.ch/web/scav/chiens'),('S3b','VS','tax','https://www.vs.ch/web/scc/personnes-physiques'),('S3b','VS','school','https://www.vs.ch/web/se/vacances-scolaires'),('S3b','VS','road','https://www.vs.ch/web/scn'),
('S3b','FR','dogs','https://www.fr.ch/sanu/animaux/chiens/detention-de-chiens'),('S3b','FR','tax','https://www.fr.ch/scc/impots/personnes-physiques/guide-pour-la-declaration-dimpot'),('S3b','FR','school','https://www.fr.ch/formation-et-ecoles/scolarite-obligatoire/vacances-scolaires'),('S3b','FR','road','https://www.ocn.ch/'),
('S3b','NE','dogs','https://www.ne.ch/autorites/DDTE/SCAV/sante-animale/Pages/Chiens.aspx'),('S3b','NE','tax','https://www.ne.ch/autorites/DFS/SCCO/personnes-physiques/Pages/accueil.aspx'),('S3b','NE','school','https://www.ne.ch/autorites/DEF/SECO/Pages/vacances-scolaires.aspx'),('S3b','NE','road','https://www.scan-ne.ch/'),
('S3b','JU','dogs','https://www.jura.ch/DEN/SCAV/Sante-animale/Chiens.html'),('S3b','JU','tax','https://www.jura.ch/DFN/IMP/Personnes-physiques/
```

## Step 18: Bash: Inspect sitemap topic candidates structure
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('stage0/sitemap_topic_candidates.json'))
print(type(d), list(d.keys())[:30])
k=list(d.keys())[0]
print(json.dumps(d[k], ensure_ascii=False)[:1500])
"
```
Result:
```
<class 'dict'> ['ZH', 'BE', 'LU', 'UR', 'SZ', 'OW', 'NW', 'GL', 'ZG', 'FR', 'SO', 'BS', 'BL', 'SH', 'AR', 'AI', 'SG', 'GR', 'AG', 'TG', 'TI', 'VD', 'VS', 'NE', 'GE', 'JU']
{"courts": {"count": 2101, "shortest": ["https://www.gerichte-zh.ch/de", "https://www.gerichte-zh.ch/de/themen", "https://www.gerichte-zh.ch/de/karriere", "https://www.gerichte-zh.ch/de/impressum", "https://www.gerichte-zh.ch/de/startseite", "https://www.gerichte-zh.ch/de/datenschutz", "https://www.gerichte-zh.ch/de/karriere-old", "https://www.gerichte-zh.ch/de/organisation", "https://www.gerichte-zh.ch/de/themen/miete", "https://www.gerichte-zh.ch/de/themen/arbeit", "https://www.gerichte-zh.ch/de/themen/person", "https://www.gerichte-zh.ch/de/themen/verbot", "https://www.zh.ch/de/sicherheit-justiz.html", "https://www.gerichte-zh.ch/de/kreisschreiben", "https://www.zh.ch/de/gerichte-notariate.html", "https://www.zh.ch/en/gerichte-notariate.html", "https://www.gerichte-zh.ch/de/themen/erbschaft", "https://www.gerichte-zh.ch/de/karriere/benefits", "https://www.gerichte-zh.ch/de/themen/wertpapier", "https://www.gerichte-zh.ch/de/karriere/ueber-uns", "https://www.gerichte-zh.ch/de/themen/zinsrechner", "https://www.gerichte-zh.ch/de/medien/medienportal", "https://www.gerichte-zh.ch/de/themen/strafprozess", "https://www.gerichte-zh.ch/de/themen/zivilprozess", "https://www.gerichte-zh.ch/de/medien/medienanfrage", "https://www.gerichte-zh.ch/de/themen/arbeit/hilfen", "https://www.gerichte-zh.ch/de/themen/partnerschaft", "https://www.gerichte-zh.ch/de/themen/person/hilfen", "https://www.gerichte-zh.ch/de/medien/akkreditierung", "https://www.zh.ch/de/sicherheit-justiz/epolice.html", "h
```

## Step 19: Bash: Show FR sitemap topic candidates
```
cd <scratchpad-overnight>/ && python3 -c "
import json
d=json.load(open('stage0/sitemap_topic_candidates.json'))
for c in ['FR']:
    for t,v in d[c].items():
        print('==',c,t,v['count'])
        for u in v['shortest'][:40]: print('   ',u)
"
```
Result:
```
== FR courts 585
    https://www.fr.ch/etat-et-droit/justice
    https://www.fr.ch/de/gb/gerichtsbehoerden
    https://www.fr.ch/de/gb/jr/news/justizrat
    https://www.fr.ch/de/gb/jr/news/justizrat-0
    https://www.fr.ch/de/gb/jr/news/justizrat-1
    https://www.fr.ch/de/gb/jr/news/justizrat-2
    https://www.fr.ch/de/gb/jr/news/justizrat-3
    https://www.fr.ch/de/gb/jr/news/justizrat-4
    https://www.fr.ch/de/gb/jr/news/justizrat-5
    https://www.fr.ch/de/gb/jr/news/justizrat-6
    https://www.fr.ch/de/gb/jr/news/justizrat-7
    https://www.fr.ch/de/gb/jr/news/justizrat-8
    https://www.fr.ch/de/staat-und-recht/justiz
    https://www.fr.ch/etat-et-droit/justice/faq-mp
    https://www.fr.ch/etat-et-droit/justice/tarifs
    https://www.fr.ch/etat-et-droit/justice/avocats
    https://www.fr.ch/etat-et-droit/justice/justice
    https://www.fr.ch/etat-et-droit/justice/formules
    https://www.fr.ch/de/gb/jr/news/kantonsgericht-kg
    https://www.fr.ch/etat-et-droit/justice/mediation
    https://www.fr.ch/de/gb/jr/aufgabe-des-justizrates
    https://www.fr.ch/de/gb/jr/news/bezirksgericht-see
    https://www.fr.ch/de/staat-und-recht/justiz/justiz
    https://www.fr.ch/de/staat-und-recht/justiz/tarife
    https://www.fr.ch/etat-et-droit/justice/directives
    https://www.fr.ch/etat-et-droit/justice/formules-0
    https://www.fr.ch/de/staat-und-recht/justiz/faq-sas
    https://www.fr.ch/etat-et-droit/justice/formulaires
    https://www.fr.ch/etat-et-droit/justice/prefectures
    https://www.fr.ch/de/gb/jr/news/bezirksgericht-broye
    https://www.fr.ch/de/gb/jr/news/bezirksgericht-glane
    https://www.fr.ch/de/gb/jr/news/bezirksgericht-saane
    https://www.fr.ch/de/gb/jr/news/bezirksgericht-sense
    https://www.fr.ch/de/staat-und-recht/justiz/eservice
    https://www.fr.ch/etat-et-droit/justice/presentation
    https://www.fr.ch/pj/autorites-du-pouvoir-judiciaire
    https://www.fr.ch/pj/tc/mission-du-tribunal-cantonal
    https://www.fr.ch/de/gb/jr/leistungen-des-justizrates
    https://www.fr.ch/de/staat-und-recht/justiz/formulare
    https://www.fr.ch/de/staat-und-recht/justiz/mediation
== FR dogs 114
    https://www.fr.ch/de/alltag/heimtiere/hunde
    https://www.fr.ch/dsjs/sscm/dangers-naturels/canicule
    https://www.fr.ch/de/alltag/heimtiere/hunde/hundegebuehr
    https://www.fr.ch/deef/spe/actualites/canicule-et-travail
    https://www.fr.ch/de/alltag/heimtiere/hunde/verbotene-hunde
    https://www.fr.ch/de/ilfd/lsvw/news/augen-auf-beim-hundekauf
```

> Let me check the prior verified work in the repo and scratchpad for my cantons so I cite rather than redo.

## Step 20: Bash: Grep OGD assessment for my cantons
```
grep -n -i -E "vaud|\bVD\b|fribourg|\bFR\b|neuch|\bNE\b|gen[eè]v|\bGE\b|jura|\bJU\b|lausanne|vernier|chaux|blv|rsn|rsju|silgeneve|bdlf" docs/sources/ogd_lists_assessment.md | head -60
```
Result:
```
131:| Geneva **Espaces interdits aux chiens** | `https://vector.sitg.ge.ch/arcgis/rest/services/FFP_CHIENS_INTERDITS/FeatureServer/0/query?where=1=1&outFields=*&f=geojson` | >2 (paged) | NOM (e.g. Parc Louis Cottier), LOCALISATION | SITG conditions, *unverified* |
132:| Geneva Espaces pour chiens en liberté | `…/FFP_CHIENS/FeatureServer` | paged | GESTION only, **no names** | |
133:| Geneva Points de collecte des déchets | `…/GOL_DECHETTERIE/FeatureServer` | paged | COMMUNE, ADRESSE, TYPE_CENTRE, BENNE, HORAIRES (a URL) | |
134:| Geneva Stationnement sur la voie publique | `…/OTC_STATIONNEMENT_V_PUBLIQUE/FeatureServer` | paged | NOM_RUES, TYPE_STATIONNEMENT ("Gratuit 60 min"), NOMBRE_PLACES | |
154:HTTP client. `html_crawl` cannot ingest them. (`zh.ch` and `ge.ch` landing pages are real HTML, but
179:| GE | M 3 45 Loi sur les chiens | 45/45 | silgeneve.ch (Geneva legislative system; *official status inferred*) |
181:| BE | 916.31 Hundegesetz | 28/28 | www.belex.sites.be.ch (de + fr) |
183:| VD | 133.75 Loi police des chiens | 40/40 | prestations.vd.ch |
197:`url = original_url`, `identifier = <canton> <systematic_number>`. Documents are DE/FR/IT and go
216:### 3.4 Zurich and Geneva, tested directly
229:- **Geneva (rsGE):** the index `silgeneve.ch/legis/index.aspx` is an application; each act is a
240:- 29 tenants: every cantonal gazette (ZH, BE, LU, …, GE, VD, TI) plus SHAB and `kabda`,
268:  v0.1 2026-04-28): 30 questions in DE/FR/IT with reference answers and gold SR-article citations;
280:  no key; `search?SearchTerm=&InLanguageCode=`): official DE/FR/IT/EN equivalents for
295:- **Geneva SITG**: the catalogue is a JavaScript app with no search API found; use the national
296:  catalogue instead — organisation `canton-geneve` lists 65 waste, 6 dog, 32 noise and 36 parking
322:- Licences of the Bern and Geneva geodata layers (not stated on opendata.swiss); ArcGIS
331:   REST), Geneva dog-ban spaces and street parking — all under the 100-row cap or filterable.
388:### B.2 Opendatasoft Explore API v2.1 — JSON (data.bs.ch, data.bl.ch, daten.stadt.sg.ch, data.tg.ch, daten.sg.ch, data.sz.ch, opendata.fr.ch)
416:  &fq=organization:<slug>&rows=N` → `{success, result: {count, results: [{name, title: {de, fr,
419:  `organization_list?all_fields=true` lists publishers (`canton-geneve`, `kanton-basel-stadt`,
450:### B.5 ArcGIS REST — GeoJSON (Bern MapServer, Geneva SITG FeatureServer)
461:- Geneva `https://vector.sitg.ge.ch/arcgis/rest/services/<SERVICE>/FeatureServ
```

## Step 21: Bash: Grep prior verification results for my cantons
```
cd <scratchpad-overnight>/ && grep -n -i -E "vaud|\bVD\b|fribourg|\bFR\b|neuch|\bNE\b|gen[eè]v|\bGE\b|jura|\bJU\b|lausanne|vernier|chaux|blv|rsn|rsju|silgeneve|bdlf" verification_results_2026-09-23.md source_registry_2026-09-23.md coverage_ledger_2026-09-23.md reports/g1-commune-law.md reports/g4-intercantonal.md | head -60
```
Result:
```
coverage_ledger_2026-09-23.md:17:| Not fetched | 1 | D18 GE vehicle office: G5 inferred the format without fetching |
coverage_ledger_2026-09-23.md:48:| Done | 1 (7 LexWork + 4 other cantonal platforms), 2 (Winterthur, Luzern, St. Gallen, Biel via tlex), 4 (ZH GE BE BS guidance + federal soft law), 5 (commune_sites.csv), 6 (city data portals) |
coverage_ledger_2026-09-23.md:51:| **Open, and links are needed** | 2: city law of Zürich, Bern, Lausanne, Lugano · 3: courts per canton · 4: guidance in the other 22 cantons · 5: the 26 chancellery link pages · 8: Wikidata idea |
coverage_ledger_2026-09-23.md:62:  Amtliche Sammlung / recueil systématique / raccolta delle leggi) of each of these Swiss cities: Zürich, Genève, Lausanne, Bern, Lugano,
coverage_ledger_2026-09-23.md:63:  Thun, La Chaux-de-Fonds, Schaffhausen, Vernier, Neuchâtel. I need the page that lists their municipal regulations (dogs, waste, parking,
coverage_ledger_2026-09-23.md:70:- **S3b Guidance, French- and Italian-speaking cantons:** "Pour les cantons de Vaud, Valais, Fribourg, Neuchâtel, Jura et Tessin, donnez
coverage_ledger_2026-09-23.md:83:  R-COURTS 5, open-ius ×3, D18 GE vehicle office, Bezirk March, BS dog PDFs. That is 5 agents with brief v4, each given the exact links.
reports/g1-commune-law.md:12:Not re-checked: FR per-commune counts, terrara 1,484, Weblication 113, BL Plone 12/682, Romandie counts, Köniz 91.
reports/g1-commune-law.md:22:| G1-a Fribourg | Yes, new fetcher | HTML index + PDF text | PDF-index discoverer (+ i-web) | high: ~100/119 FR |
reports/g1-commune-law.md:29:| Cantonal central index of commune bylaws | **None found** (FR, SO, VD, BE only publish templates) | – | – | – |
reports/g1-commune-law.md:40:- By canton: ZG 11 (all), BL 8, AG 6, SG 5, GR 4, TG 3, GL 3, ZH 3, BE 2, LU 2, JU 1, SO 1. Includes Winterthur (270 texts), Luzern,
reports/g1-commune-law.md:41:  Biel/Bienne (de+fr), Aarau, Frauenfeld, Wil, Rapperswil-Jona, Delémont (fr).
reports/g1-commune-law.md:42:- API: `/api/{de|fr}/texts_of_law/lightweight_index`, `/api/de/systematic_categories`, `/api/de/settings` (entity_description),
reports/g1-commune-law.md:50:- 496 of 2,060 homepages (ZH 91, AG 54, BE 50, SG 45, SO 44, VD 30, LU 27, FR 23).
reports/g1-commune-law.md:58:- FR CMS mix: TYPO3 30, WordPress 33, i-web 23, other 33. There is no common path. In a sample of 10, none had article HTML; all had PDF lists.
reports/g1-commune-law.md:59:- Romandie CMS: WordPress 142, i-web 56, Quicksite 38 (VD), TYPO3 35
```

> Now I'll build a curl-based probe helper for efficient batch checks.

## Step 22: Write: /tmp/sg-verify-run3-d/probe.py
```
#!/usr/bin/env python3
"""curl-based probe: prints code, content-type, bytes, final url, title, #links, words, optional sample.
Usage: probe.py URL [regex] ...  (pairs via 'URL::regex')
Saves body to /tmp/sg-verify-run3-d/pages/<slug>.
"""
import html
import os
import re
import subprocess
import sys
import hashlib

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 swiss-grounding-check"
OUT = "/tmp/sg-verify-run3-d/pages"
os.makedirs(OUT, exist_ok=True)


def slug(u):
    s = re.sub(r"[^A-Za-z0-9]+", "_", u)[:120]
    return s + "_" + hashlib.md5(u.encode()).hexdigest()[:6]


def probe(url, rx=None, ctx=160, maxhits=2):
    fn = os.path.join(OUT, slug(url))
    r = subprocess.run(
        ["curl", "-g", "-sL", "--max-time", "40", "-A", UA, "-o", fn, "-w",
         "%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}", url],
        capture_output=True, text=True)
    meta = r.stdout.strip().split("\t")
    while len(meta) < 4:
        meta.append("")
    code, ct, size, final = meta
    title = ""
    links = words = 0
    text = ""
    try:
        raw = open(fn, "rb").read()
    except FileNotFoundError:
        raw = b""
    if "html" in ct or raw[:200].lower().find(b"<html") >= 0 or raw[:100].lstrip().startswith(b"<!"):
        t = raw.decode("utf-8", "replace")
        m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
        title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""
        links = len(re.findall(r"<a\s[^>]*href", t, re.I))
        body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
        text = html.unescape(re.sub(r"<[^>]+>", " ", body))
        text = re.sub(r"\s+", " ", text)
        words = len(text.split())
    elif "pdf" in ct:
        try:
            from pypdf import PdfReader
            rd = PdfReader(fn)
            pages = len(rd.pages)
            text = " ".join((rd.pages[i].extract_text() or "") for i in range(min(pages, 3)))
            text = re.sub(r"\s+", " ", text)
            title = f"[PDF {pages} pages, text chars p1-3: {len(text)}]"
            words = len(text.split())
        except Exception as e:  # noqa
            title = f"[PDF read error {e}]"
    else:
        text = raw[:4000].decode("utf-8", "replace")
    print(f"{code} | {ct} | {size}B | {final}\n   title: {title[:110]}\n   links={links} words={words}  file={fn}")
    if rx:
        hits = 0
        for m in re.finditer(rx, text, re.I):
            s = max(0, m.start() - ctx // 2)
            print("   SAMPLE:", text[s:m.end() + ctx].strip()[:ctx * 2])
            hits += 1
            if hits >= maxhits:
                break
        if hits == 0:
            print("   SAMPLE: <no match for", rx, ">")
    sys.stdout.flush()


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if "::" in arg:
            u, rx = arg.split("::", 1)
        else:
            u, rx = arg, None
      
```
Result:
```
File created successfully at: /tmp/sg-verify-run3-d/probe.py (file state is current in your context — no need to Read it back)
```

> Starting FR breadth: grep the fr.ch sitemap for court, fee, conciliation and other cell candidates.

## Step 23: Bash: Grep FR sitemap for judiciary pages
```
cd <scratchpad-overnight>/stage0/sitemaps && F=www.fr.ch.txt; echo "pj pages:"; grep -c "fr.ch/pj/" $F; grep "fr.ch/pj/" $F | grep -v actualites | awk '{print length, $0}' | sort -n | cut -d' ' -f2 | head -60
```
Result:
```
pj pages:
147
https://www.fr.ch/pj/cm
https://www.fr.ch/pj/tc
https://www.fr.ch/pj/cm/contact
https://www.fr.ch/pj/tc/contact
https://www.fr.ch/pj/autorites-du-pouvoir-judiciaire
https://www.fr.ch/pj/tc/mission-du-tribunal-cantonal
https://www.fr.ch/pj/cm/fonctions-judiciaires-vacantes
https://www.fr.ch/pj/organigramme-du-pouvoir-judiciaire
https://www.fr.ch/pj/tc/prestations-du-tribunal-cantonal
https://www.fr.ch/pj/tc/jurisprudence-du-tribunal-cantonal
https://www.fr.ch/pj/tc/debats-publics-du-tribunal-cantonal
https://www.fr.ch/pj/cm/mission-du-conseil-de-la-magistrature
https://www.fr.ch/pj/cm/prestations-du-conseil-de-la-magistrature
https://www.fr.ch/pj/cm/organisation-du-conseil-de-la-magistrature
https://www.fr.ch/pj/jurisprudence-du-tribunal-cantonal-jusquen-2011
```

## Step 24: Bash: List FR justice theme pages from sitemap
```
cd <scratchpad-overnight>/stage0/sitemaps && F=www.fr.ch.txt; echo "etat-et-droit/justice pages:"; grep -c "fr.ch/etat-et-droit/justice" $F; grep "fr.ch/etat-et-droit/justice" $F | awk '{print length, $0}' | sort -n | cut -d' ' -f2 | head -120
```
Result:
```
etat-et-droit/justice pages:
138
https://www.fr.ch/etat-et-droit/justice
https://www.fr.ch/etat-et-droit/justice/faq-mp
https://www.fr.ch/etat-et-droit/justice/tarifs
https://www.fr.ch/etat-et-droit/justice/avocats
https://www.fr.ch/etat-et-droit/justice/justice
https://www.fr.ch/etat-et-droit/justice/formules
https://www.fr.ch/etat-et-droit/justice/mediation
https://www.fr.ch/etat-et-droit/justice/directives
https://www.fr.ch/etat-et-droit/justice/formules-0
https://www.fr.ch/etat-et-droit/justice/formulaires
https://www.fr.ch/etat-et-droit/justice/prefectures
https://www.fr.ch/etat-et-droit/justice/presentation
https://www.fr.ch/etat-et-droit/justice/ministere-public
https://www.fr.ch/etat-et-droit/justice/liens-interessants
https://www.fr.ch/etat-et-droit/justice/mission-prestations
https://www.fr.ch/etat-et-droit/justice/mediation-judiciaire
https://www.fr.ch/etat-et-droit/justice/politique-criminelle
https://www.fr.ch/etat-et-droit/justice/commission-du-barreau
https://www.fr.ch/etat-et-droit/justice/fonctions-judiciaires
https://www.fr.ch/etat-et-droit/justice/offices-des-poursuites
https://www.fr.ch/etat-et-droit/justice/journalistes-accredites
https://www.fr.ch/etat-et-droit/justice/principales-legislations
https://www.fr.ch/etat-et-droit/justice/competences-territoriales
https://www.fr.ch/etat-et-droit/justice/quest-ce-quun-ou-une-juge
https://www.fr.ch/etat-et-droit/justice/indications-complementaires
https://www.fr.ch/etat-et-droit/justice/office-cantonal-des-faillites
https://www.fr.ch/etat-et-droit/justice/organes-du-pouvoir-judiciaire
https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-reglements
https://www.fr.ch/etat-et-droit/justice/surveillance-et-administration
https://www.fr.ch/etat-et-droit/justice/directives-du-tribunal-cantonal
https://www.fr.ch/etat-et-droit/justice/reglements-du-tribunal-cantonal
https://www.fr.ch/etat-et-droit/justice/mission-de-loffice-des-faillites
https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-jurisprudence
https://www.fr.ch/etat-et-droit/justice/procedure-de-poursuite/sequestre
https://www.fr.ch/etat-et-droit/justice/recherche-dautorites-judiciaires
https://www.fr.ch/etat-et-droit/justice/bibliotheque-du-tribunal-cantonal
https://www.fr.ch/etat-et-droit/justice/presentation-du-tribunal-cantonal
https://www.fr.ch/etat-et-droit/justice/collaborateurs-du-tribunal-cantonal
https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-justices-de-paix
https://www.fr.ch/etat-et-droit/justice/pouvoir-
```

## Step 25: Bash: Grep FR sitemap for conciliation and guidance topics
```
cd <scratchpad-overnight>/stage0/sitemaps && F=www.fr.ch.txt; for t in conciliation "commission-de-conciliation" "baux|bail" divorce "assistance-judiciaire" succession "separation" "prud" "justice-de-paix|justices-de-paix"; do echo "== $t: $(grep -E -c "$t" $F)"; grep -E "$t" $F | grep -v -E "/de/|actualites|/news/" | awk '{print length, $0}' | sort -n | cut -d' ' -f2 | head -12; done
```
Result:
```
== conciliation: 9
https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-commissions-de-conciliation-en-matiere-de-bail-et-tribunal-des-baux
https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-commission-de-conciliation-en-matiere-degalite-entre-les-sexes-dans-les-rapports-de-travail
https://www.fr.ch/travail-et-entreprises/employes/la-lutte-contre-le-harcelement-sexuel/commission-cantonale-de-conciliation-en-matiere-degalite-entre-les-sexes-dans-les-rapports-de-travail
https://www.fr.ch/etat-et-droit/gouvernement-et-administration/legalite-dans-la-vie-professionnelle/egalite-dans-la-vie-professionnelle-informations-aux-entreprises/conciliation-vie-privee-vie-professionnelle-facilitee
https://www.fr.ch/etat-et-droit/gouvernement-et-administration/legalite-dans-la-vie-professionnelle/egalite-dans-la-vie-professionnelle-informations-aux-entreprises/conciliation-vie-privee-vie-professionnelle-facilitee/mesures-pour-faciliter-la
https://www.fr.ch/etat-et-droit/gouvernement-et-administration/legalite-dans-la-vie-professionnelle/egalite-dans-la-vie-professionnelle-informations-aux-entreprises/conciliation-vie-privee-vie-professionnelle-facilitee/egalite-et-modeles-de-temps-de
https://www.fr.ch/etat-et-droit/gouvernement-et-administration/legalite-dans-la-vie-professionnelle/egalite-dans-la-vie-professionnelle-informations-aux-entreprises/conciliation-vie-privee-vie-professionnelle-facilitee/vous-voulez-introduire-une-plus
== commission-de-conciliation: 1
https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-commission-de-conciliation-en-matiere-degalite-entre-les-sexes-dans-les-rapports-de-travail
== baux|bail: 19
https://www.fr.ch/territoire-amenagement-et-constructions/registre-foncier/bail-a-ferme-agricole
https://www.fr.ch/territoire-amenagement-et-constructions/registre-foncier/requetes-en-matiere-de-bail-a-ferme
https://www.fr.ch/dime/sbat/chateau-de-chatel-saint-denis-une-premiere-etape-de-mise-en-valeur-des-chateaux-baillivaux
https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-commissions-de-conciliation-en-matiere-de-bail-et-tribunal-des-baux
https://www.fr.ch/territoire-amenagement-et-constructions/registre-foncier/foire-aux-questions-en-matiere-de-bail-a-ferme-agricole
https://www.fr.ch/territoire-amenagement-et-constructions/registre-foncier/notions-principales-en-matiere-de-bail-a-ferme-agricole
https://www.fr.ch/territoire-amenagement-et-constructions/registre-foncier/foire-aux-questions-sur-le-droit-foncier-rural-et-sur-le
```

## Step 26: Bash: Probe FR court pages: home, fees, conciliation, decisions
```
cd /tmp/sg-verify-run3-d && python3 probe.py \
 "https://www.fr.ch/pj/tc::tribunal cantonal" \
 "https://www.fr.ch/etat-et-droit/justice::pouvoir judiciaire" \
 "https://www.fr.ch/etat-et-droit/justice/tarifs::(CHF|Fr\.|frais|émolument)" \
 "https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-commissions-de-conciliation-en-matiere-de-bail-et-tribunal-des-baux::(conciliation|gratuit|frais)" \
 "https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-justices-de-paix::(conciliation|justice de paix)" \
 "https://www.fr.ch/etat-et-droit/justice/moteur-de-recherche-tribuna-publication::(publication|recherche|http)" \
 "https://www.fr.ch/pj/tc/jurisprudence-du-tribunal-cantonal::(publication|arr[eê]t|http)" 2>&1
```
Result:
```
==> https://www.fr.ch/pj/tc
200 | text/html; charset=UTF-8 | 91310B | https://www.fr.ch/pj/tc
   title: Tribunal cantonal (TC) | Etat de Fribourg
   links=76 words=695  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_pj_tc_82dc62
   SAMPLE: Tribunal cantonal (TC) | Etat de Fribourg Page d'accueil Navigation Contenu Contact Recherche Entête fr.ch Menu Fermer Sprache ändern Ihr Browser verwendet eine andere Sprache.
   SAMPLE: Consultations cantonales et fédérales Consultations en cours.. Jurisprudence Du Tribunal cantonal Feuille officielle Consultation de la FO en ligne Votations et élections Décisions du Conseil d’Etat Compte rendu des séances du Conseil d’Etat Sessions du Gra
==> https://www.fr.ch/etat-et-droit/justice
200 | text/html; charset=UTF-8 | 98565B | https://www.fr.ch/etat-et-droit/justice
   title: Justice | Etat de Fribourg
   links=78 words=773  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_etat_et_droit_justice_fc07fc
   SAMPLE: oix du thème Défaut Clair Sombre Accueil Etat et droit Justice Justice Justice, pouvoir judiciaire, instances, tribunal, tribunaux, juge d'instruction, juge de paix, justice de paix, commissions, préfectures, indépendance, législatif, exécutif, injonction, p
   SAMPLE: , injonction, présentation, informations Prestations et informations Organes du Pouvoir judiciaire Chapeau Il existe trois types de juridictions ou d'organes du Pouvoir judiciaire : les juridictions civiles (s'occupent de conflits entre particuliers), pénale
==> https://www.fr.ch/etat-et-droit/justice/tarifs
200 | text/html; charset=UTF-8 | 81824B | https://www.fr.ch/etat-et-droit/justice/tarifs
   title: Tarifs | Etat de Fribourg
   links=65 words=442  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_etat_et_droit_justice_tarifs_33859d
   SAMPLE: s | Etat de Fribourg Page d'accueil Navigation Contenu Contact Recherche Entête fr.ch Menu Fermer Sprache ändern Ihr Browser verwendet eine andere Sprache. Sie können die Sprache ändern, indem Sie auf den Link "Français" klicken. Okay, ich hab
   SAMPLE: ombre Accueil Etat et droit Justice Tarifs Tarifs Chapeau Tarifs de l'avance de frais Tarifs Voici le montant de l'avance de frais à effectuer pour l'enregistrement d'une réquisition de poursuite, l'établissement et la notification du commandeme
==> https://www.fr.ch/etat-et-droit/justice/pouvoir-judiciaire-commissions-de-conciliation-en-matiere-de-bail-et-tribunal-des-baux
200 | text/html; charset=UTF-8 | 92054B | https://www.fr.ch/etat-et-droit/justice
```

## Step 27: Bash: Extract FR tarifs text and Tribuna links
```
cd /tmp/sg-verify-run3-d/pages && python3 - <<'EOF'
import re,html,glob
def text(fn):
    t=open(fn,encoding='utf-8',errors='replace').read()
    b=re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>"," ",t,flags=re.S|re.I)
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",b)))
def links(fn,pat=None):
    t=open(fn,encoding='utf-8',errors='replace').read()
    out=[]
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S|re.I):
        h=m.group(1); lab=re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",m.group(2))).strip()
        if pat is None or re.search(pat,h+' '+lab,re.I): out.append((h,lab[:80]))
    return out
f=glob.glob('https_www_fr_ch_etat_et_droit_justice_tarifs_*')[0]
tx=text(f); i=tx.find('Tarifs de l')
print(tx[i:i+1500])
print('----')
f=glob.glob('https_www_fr_ch_etat_et_droit_justice_moteur_de_recherche_tribuna*')[0]
for l in links(f,r'tribuna|publication|http'): print(l)
EOF
```
Result:
```
Tarifs de l'avance de frais Tarifs Voici le montant de l'avance de frais à effectuer pour l'enregistrement d'une réquisition de poursuite, l'établissement et la notification du commandement de payer ou de la commination de faillite : Créance en CHF Montant de l'avance de frais en CHF jusqu'à 100.00 21.00 supérieure à 100.00 et ne dépassant pas 500.00 34.00 supérieure à 500.00 et ne dépassant pas 1'000.00 54.00 supérieure à 1'000.00 et ne dépassant pas 10'000.00 74.00 supérieure à 10'000.00 et ne dépassant pas 100'000.00 104.00 supérieure à 100'000.00 et ne dépassant pas 1'000'000.00 204.00 supérieure à 1'000'000.00 414.00 Valable dès le 1er janvier 2024. Retour au sujet principal Justice Direction / Service propriétaire Offices des poursuites et Office des faillites Information de contact Publié par Offices des poursuites et Office des faillites Dernière modification : 19.12.2023 Partager sur : Pied de page Impressum Politique de confidentialité Accessibilité Contact Abonnement à des contenus et accréditation Suivez-nous sur : Fermer Recherche 
----
('/etat-et-droit/justice/moteur-de-recherche-tribuna-publication#nav', 'Navigation')
('/etat-et-droit/justice/moteur-de-recherche-tribuna-publication#main', 'Contenu')
('https://www.fr.ch/', 'fr.ch')
('https://www.fr.ch/travail-et-entreprises', 'Travail et entreprises')
('https://www.fr.ch/formation-et-ecoles', 'Formation et écoles')
('https://www.fr.ch/impots', 'Impôts')
('https://www.fr.ch/territoire-amenagement-et-constructions', 'Territoire, aménagement et constructions')
('https://www.fr.ch/police-et-securite', 'Police et sécurité')
('https://www.fr.ch/vie-quotidienne', 'Vie quotidienne')
('https://www.fr.ch/energie-agriculture-et-environnement', 'Energie, agriculture et environnement')
('https://www.fr.ch/etat-et-droit', 'Etat et droit')
('https://www.fr.ch/sante', 'Santé')
('https://www.fr.ch/mobilite-et-transport', 'Mobilité et transport')
('https://www.fr.ch/sport-et-loisirs', 'Sport et loisirs')
('https://www.fr.ch/culture-et-tourisme', 'Culture et tourisme')
('https://www.fr.ch/vie-quotidienne/etat-civil/commande-dun-acte-detat-civil', 'Acte d&#039;état civil')
('https://www.fr.ch/etat-et-droit/poursuites-et-faillites/procedure-de-poursuite/obtenir-un-extrait-de-loffice-des-poursuites', 'Extrait de poursuite')
('https://www.fr.ch/etat-et-droit/poursuites-et-faillites/ventes-aux-encheres', 'Ventes aux enchères')
('https://www.fr.ch/diaf/pref/prestations-de-la-prefecture', 'Autorisations de la Préfectu
```

## Step 28: Bash: Inspect laws_FR.json structure
```
cd <scratchpad-overnight>/stage0 && python3 -c "
import json,re
d=json.load(open('laws_FR.json'))
print(type(d), (list(d.keys())[:5] if isinstance(d,dict) else len(d)))
rows = d if isinstance(d,list) else (d.get('items') or d.get('texts') or d.get('data') or list(d.values())[0])
print(json.dumps(rows[0],ensure_ascii=False)[:400])
"
```
Result:
```
<class 'dict'> ['host', 'lang', 'items']
{"id": 1, "systematic_number": "10.1", "systematic_category_id": 10, "title": "Constitution du canton de Fribourg", "abrogated": false, "structured_document_id": 32224}
```

## Step 29: Bash: Search FR law list for fee/dog/tax/court laws
```
cd <scratchpad-overnight>/stage0 && python3 - <<'EOF'
import json,re
def search(fn, pats, excl=None):
    d=json.load(open(fn))
    rows=d['items'] if isinstance(d,dict) and 'items' in d else d
    for r in rows:
        t=r.get('title') or ''
        nr=r.get('systematic_number') or r.get('nr') or ''
        if any(re.search(p,t,re.I) for p in pats) and not (excl and re.search(excl,t,re.I)):
            print('  ',nr,'|',t[:140],'| abrogated' if r.get('abrogated') else '', '| id',r.get('id'))
for fn in ['laws_FR.json']:
    d=json.load(open(fn)); print(fn, d.get('host'), d.get('lang'), len(d['items']))
    search(fn,[r'justice\b', r'frais (judiciaires|de proc)', r'tarif', r'émolument', r'chiens?', r'conciliation', r'bail', r'vacances', r'impôt', r'Feuille officielle', r'communes\b'], excl=r'forêt|chasse|pêche')
EOF
```
Result:
```
laws_FR.json bdlf.fr.ch fr 814
   111.13 | Ordonnance indiquant les effectifs au 31 décembre 2025 de la population dite légale des communes du canton de Fribourg  | id 5
   261.16 | Tarif des émoluments des notaires  | id 38
   261.162 | Tarif de l'Association des notaires relatif aux honoraires dus pour les opérations annexes  | id 17
   122.93.16 | Tarif des frais et honoraires perçus par la Commission d'acquisition des immeubles  | id 286
   222.4.3 | Loi d'application de la loi fédérale sur le bail à ferme agricole  | id 40
   222.3.1 | Loi d'application relative au bail à loyer et au bail à ferme non agricole  | id 41
   222.3.11 | Ordonnance relative au bail à loyer et au bail à ferme non agricole  | id 22
   222.3.12 | Ordonnance concernant l'usage de la formule officielle pour la conclusion d'un nouveau bail à loyer  | id 21
   214.5.16 | Tarif des émoluments fixes du registre foncier  | id 27
   214.2.13 | Ordonnance fixant les émoluments de l'Autorité foncière cantonale  | id 1256
   862.2 | Loi instituant un Office de conciliation en matière de conflits collectifs de travail  | id 304
   862.21 | Règlement d'exécution de la loi instituant un Office de conciliation en matière de conflits collectifs de travail  | id 364
   112.51 | Ordonnance indiquant les noms des communes et leur rattachement aux districts administratifs  | id 967
   810.16 | Ordonnance fixant les émoluments du Service de l'environnement  | id 310
   721.3.14 | Ordonnance concernant la réserve forestière En Biffé, sur le territoire des communes de Botterens, Châtel-sur-Montsalvens et Villarbeney  | id 560
   721.3.18 | Ordonnance concernant la réserve forestière Galm Sud, sur le territoire des communes de Gurmels et de Jeuss et sur celui du Staatswald Galm  | id 552
   721.3.24 | Ordonnance concernant la réserve forestière Petite-Sarine, sur le territoire des communes d'Arconciel, de Rossens et de Treyvaux  | id 963
   721.3.26 | Ordonnance concernant la réserve forestière Seiseflüe, sur le territoire des communes d'Ueberstorf, Heitenried et St. Antoni  | id 1021
   721.3.27 | Ordonnance concernant la réserve forestière Naturwaud Seiseflüe 2, sur le territoire des communes d'Alterswil et St. Antoni  | id 1056
   31.16 | Tarif relatif à la participation financière des personnes astreintes à un programme de prévention de la violence  | id 1067
   634.2.11 | Ordonnance d'exécution de la loi fédérale sur l'impôt anticipé  | id 828
   821.0.61 | Ordonnance fixant le tarif des émolume
```

## Step 30: Bash: Fetch FR LexWork court fee laws and sample fees
```
cd /tmp/sg-verify-run3-d && for nr in 130.11 130.16; do curl -s -A "Mozilla/5.0 swiss-grounding-check" -o bdlf_$nr.json -w "%{http_code} %{content_type} %{size_download}B\n" "https://bdlf.fr.ch/api/fr/texts_of_law/$nr"; python3 - "$nr" <<'EOF'
import json,sys,re,html
nr=sys.argv[1]
d=json.load(open(f'bdlf_{nr}.json'))
print('top keys:', list(d.keys())[:12])
tol=d.get('text_of_law') or d
print('title:', tol.get('title'), '| canonical_link:', tol.get('canonical_link') or d.get('canonical_link'))
s=json.dumps(d,ensure_ascii=False)
x=html.unescape(re.sub(r'<[^>]+>',' ',s))
x=re.sub(r'\s+',' ',x)
for m in list(re.finditer(r'(frais judiciaires|émolument)[^.]{0,200}?(\d[\d\' ]*(\.\d+)? ?francs|Fr\.? ?\d|CHF ?\d|\d+ à \d+ francs)',x))[:3]:
    print('  SAMPLE:', x[m.start():m.end()+80][:300])
print('  version dates:', re.findall(r'"(?:version_active_since|enactment|valid_from|inforce_from_date|version_date|date_of_version)":\s*"([^"]+)"',s)[:5])
EOF
done
```
Result:
```
200 application/json; charset=utf-8 1433906B
top keys: ['text_of_law']
title: Règlement sur la justice | canonical_link: https://bdlf.fr.ch/app/fr/texts_of_law/130.11
  SAMPLE: émolument de conciliation de 50 à 10'000 francs. \n \n \n \n \n \n Art. 19 \n \n \n Emolument forfaitaire de décision – Tribuna
  SAMPLE: émolument de 100 à 200'000 francs. \n \n \n \n \n 2 \n \n Le maximum peut être porté à 1'000'000 de francs lorsqu
  SAMPLE: émolument de 100 à 500'000 francs. \n \n \n \n \n 2 \n \n En cas de difficultés spéciales, ou si la valeur litigi
  version dates: ['2011-01-01']
200 application/json; charset=utf-8 124923B
top keys: ['text_of_law']
title: Tarif du Tribunal cantonal des émoluments pour les contestations portant sur des affaires pécuniaires | canonical_link: https://bdlf.fr.ch/app/fr/texts_of_law/130.16
  SAMPLE: émolument de conciliation selon le barème suivant, en fonction de la valeur litigieuse: \n \n \n \n \n \n a)\n \n \n jusqu'à 1000 francs:\n \n \n Fr. 50 à 250\n \n \n \n \n \n \n b)\n \n \n de 1000 à 5000 francs:\n \
  SAMPLE: émolument selon le barème suivant, en fonction de la valeur litigieuse: \n \n \n \n \n \n a)\n \n \n jusqu'à 1000 francs:\n \n \n Fr. 100 à 500\n \n \n \n \n \n \n b)\n \n \n de 1000 à 5000 francs:\n 
  SAMPLE: émolument selon le barème suivant, en fonction de la valeur litigieuse: \n \n \n \n \n \n a)\n \n \n jusqu'à 10'000 francs:\n \n \n Fr. 100 à 2000\n \n \n \n \n \n \n b)\n \n \n de 10'000 à 30'000 franc
  version dates: ['2016-02-01']
```

## Step 31: Bash: Grep FR sitemap for court fee pages
```
cd <scratchpad-overnight>/stage0/sitemaps && F=www.fr.ch.txt; for t in "frais" "cout|coût" "emolument" "assistance-judiciaire|assistance judiciaire" "avance"; do echo "== $t: $(grep -E -c "$t" $F)"; grep -E "$t" $F | grep -v -E "/de/|actualites|/news/" | grep -E "justice|pj/|etat-et-droit|judiciaire" | head -12; done
```
Result:
```
== frais: 13
https://www.fr.ch/etat-et-droit/poursuites-et-faillites/procedure-de-faillite/avance-de-frais-effectuee
https://www.fr.ch/etat-et-droit/poursuites-et-faillites/procedure-de-faillite/pas-davance-de-frais
== cout|coût: 34
https://www.fr.ch/etat-et-droit/publications-officielles/ou-obtenir-des-publications-et-a-quel-cout
== emolument: 6
== assistance-judiciaire|assistance judiciaire: 1
https://www.fr.ch/etat-et-droit/gouvernement-et-administration/paiement-relatif-a-la-premiere-heure-et-a-lassistance-judiciaire
== avance: 18
https://www.fr.ch/etat-et-droit/poursuites-et-faillites/procedure-de-faillite/avance-de-frais-effectuee
https://www.fr.ch/etat-et-droit/poursuites-et-faillites/procedure-de-faillite/pas-davance-de-frais
```

## Step 32: Bash: Probe FR legal aid, dogs and school holiday pages
```
cd /tmp/sg-verify-run3-d && python3 probe.py \
 "https://www.fr.ch/etat-et-droit/gouvernement-et-administration/paiement-relatif-a-la-premiere-heure-et-a-lassistance-judiciaire::(assistance judiciaire|CHF|francs)" \
 "https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens::(laisse|chien)" \
 "https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens/impot-sur-les-chiens::(CHF|francs|Fr\.)" \
 "https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens/chiens-interdits::(interdit)" \
 "https://www.fr.ch/dfac/vacances-scolaires::(20[2-3][0-9])" \
 "https://www.fr.ch/dfac/vacances-scolaires/comment-se-fabriquent-les-calendriers-scolaires::(commune|cercle|direction|fix)" 2>&1; grep -o -i -E "gratuit[^.]{0,200}" pages/*commissions_de_conciliation* | head -3
```
Result:
```
==> https://www.fr.ch/etat-et-droit/gouvernement-et-administration/paiement-relatif-a-la-premiere-heure-et-a-lassistance-judiciaire
200 | text/html; charset=UTF-8 | 92329B | https://www.fr.ch/etat-et-droit/gouvernement-et-administration/paiement-relatif-a-la-premiere-heure-et-a-lassistance-judiciaire
   title: Paiement relatif à la première heure et à l'assistance judiciaire | Etat de Fribourg
   links=69 words=1342  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_etat_et_droit_gouvernement_et_administration_paiement_relatif_a_la_premiere_heure_et_a_lassistance_judic_8fce6a
   SAMPLE: Paiement relatif à la première heure et à l'assistance judiciaire | Etat de Fribourg Page d'accueil Navigation Contenu Contact Recherche Entête fr.ch Menu Fermer Sprache ändern Ihr Browser verwendet eine andere Sprache. Sie k
   SAMPLE: roit Gouvernement et administration Paiement relatif à la première heure et à l'assistance judiciaire Paiement relatif à la première heure et à l'assistance judiciaire Chapeau Pratique du Service de la justice en matière de paiement des factures de la première
==> https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens
200 | text/html; charset=UTF-8 | 156573B | https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens
   title: Chiens | Etat de Fribourg
   links=84 words=701  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_vie_quotidienne_animaux_de_compagnie_chiens_a2bf88
   SAMPLE: Chiens | Etat de Fribourg Page d'accueil Navigation Contenu Contact Recherche Entête fr.ch Menu Fermer Sprache ändern Ihr Browser verwendet eine andere Sprache. Sie
   SAMPLE: ères de l'office des faillites Autorisations de la Préfecture Patentes, chasse, chiens, lotos, ... ECAS AVS, APG, allocations familiales, subsides d’assurance-maladie, ... FRIAC Application de gestion des demandes de permis de construire Passepo
==> https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens/impot-sur-les-chiens
200 | text/html; charset=UTF-8 | 85386B | https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens/impot-sur-les-chiens
   title: Impôt sur les chiens | Etat de Fribourg
   links=71 words=510  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_vie_quotidienne_animaux_de_compagnie_chiens_impot_sur_les_chiens_ce840f
   SAMPLE: s | Etat de Fribourg Page d'accueil Navigation Contenu Contact Recherche Entête fr.ch Menu Fermer Sprache ändern Ihr Browser verwendet eine andere Sprache. Sie können die Sprache ändern, indem Sie auf den Link "Français" klicken.
```

## Step 33: Bash: Extract FR holiday dates, PDFs and dog page text
```
cd /tmp/sg-verify-run3-d/pages && python3 - <<'EOF'
import re,html,glob
def text(fn):
    t=open(fn,encoding='utf-8',errors='replace').read()
    b=re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>"," ",t,flags=re.S|re.I)
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",b)))
def links(fn,pat=None):
    t=open(fn,encoding='utf-8',errors='replace').read()
    out=[]
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S|re.I):
        h=m.group(1); lab=re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",m.group(2))).strip()
        if pat is None or re.search(pat,h+' '+lab,re.I): out.append((h,lab[:80]))
    return out
f=glob.glob('https_www_fr_ch_dfac_vacances_scolaires_7c42ca')[0]
tx=text(f); i=tx.find('Calendrier majoritaire 2026')
print(tx[i:i+900]); print('...')
for l in links(f,r'\.pdf|\.ics|\.xlsx|download|files|calend'): print(l)
f=glob.glob('*comment_se_fabriquent*')[0]
tx=text(f); i=tx.find("L'élaboration du cal")
print(tx[i:i+1200])
f=glob.glob('*animaux_de_compagnie_chiens_a2bf88')[0]
tx=text(f); i=tx.find('Accueil Vie quotidienne')
print('DOGS:',tx[i:i+900])
EOF
```
Result:
```
Calendrier majoritaire 2026 / 2027 Calendrier scolaire majoritaire valable pour toutes les communes du canton, sauf celles de la région de Morat/Murten et de Kerzers. Jours fériés scolaires 2026/2027 - Calendrier majoritaire Jour férié Date Jour de la semaine Toussaint 1 novembre 2026 Dimanche Immaculée Conception 8 décembre 2026 Mardi Ascension 6 mai 2027 Jeudi Pont de l’Ascension 7 mai 2027 Vendredi Lundi de Pentecôte 17 mai 2027 Lundi Fête-Dieu 27 mai 2027 Jeudi Vacances scolaires 2026/2027 - Calendrier majoritaire Période Début Fin Niveau / Région Début de l’année scolaire 27 août 2026 27 août 2026 École obligatoire – calendrier majoritaire Vacances d’automne 12 octobre 2026 23 octobre 2026 (inclus) École obligatoire – calendrier majoritaire Vacances de Noël 21 décembre 2026 1 janvier 2027 (inclus) École obligatoire – calendrier majoritaire Vacances de carnaval 8 février 2027 12 févr
...
('/document/574836', 'calendrier majoritaire 20262027 (PDF, 53.4k)')
('/document/508696', 'ics - Calendrier majoritaire 2026/27 (ICS, 426.76k)')
('/document/574846', 'calendrier morat 20262027 (PDF, 255.08k)')
('/document/508646', 'ics - Calendrier Morat/Murten 2026/27 (ICS, 349.24k)')
('/document/574841', 'calendrier kerzers (PDF, 256.94k)')
('/document/513541', 'ics - Calendrier Kerzers 2026/27 (ICS, 349.05k)')
('#295418277-335625158', 'Calendrier 2027 / 2028')
('/document/508606', 'Calendrier majoritaire 2027/28 (PDF, 53.43k)')
('/document/508701', 'ics - Calendrier majoritaire 2027/28 (ICS, 426.76k)')
('/document/508651', 'Calendrier Morat/Murten 2027/28 (PDF, 255.35k)')
('/document/508656', 'ics - Calendrier Morat/Murten 2027/28 (ICS, 349.24k)')
('/document/513521', 'Calendrier Kerzers 2027/28 (PDF, 260.53k)')
('/document/513546', 'ics - Calendrier Kerzers 2027/28 (ICS, 349.05k)')
('#295418277-123581184', 'Calendrier 2028 / 2029')
('/document/508616', 'Calendrier majoritaire 2028/29 (PDF, 53.44k)')
('/document/508611', 'ics - Calendrier majoritaire 2028/29 (ICS, 426.76k)')
('/document/508661', 'Calendrier Morat/Murten 2028/29 (PDF, 255.87k)')
('/document/508666', 'ics - Calendrier Morat/Murten 2028/29 (ICS, 349.24k)')
('/document/513526', 'Calendrier Kerzers 2028/29 (PDF, 257.74k)')
('/document/513551', 'ics - Calendrier Kerzers 2028/29 (ICS, 349.05k)')
('#295418277-2712232600', 'Calendrier 2029 / 2030')
('/document/508626', 'Calendrier majoritaire 2029/30 (PDF, 53.44k)')
('/document/508621', 'ics - Calendrier majoritaire 2029/30 (ICS, 426.76k)')
('/document/50867
```

## Step 34: Bash: Verify FR school holiday ICS and PDF
```
cd /tmp/sg-verify-run3-d && curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o fr_ics_508696 -w "%{http_code} %{content_type} %{size_download}B %{url_effective}\n" "https://www.fr.ch/document/508696"; head -c 300 fr_ics_508696; echo; grep -c "BEGIN:VEVENT" fr_ics_508696; grep -a -E "^(SUMMARY|DTSTART|DTEND)" fr_ics_508696 | head -12; curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o fr_pdf_574836 -w "%{http_code} %{content_type} %{size_download}B %{url_effective}\n" "https://www.fr.ch/document/574836"; python3 -c "
from pypdf import PdfReader; r=PdfReader('fr_pdf_574836'); print(len(r.pages)); print(r.pages[0].extract_text()[:400])"
```
Result:
```
200 text/calendar 437002B https://www.fr.ch/sites/default/files/2023-08/ics--calendrier-majoritaire-202627.ics?v=1724316240
BEGIN:VCALENDAR
PRODID:-//Microsoft Corporation//Outlook 16.0 MIMEDIR//EN
VERSION:2.0
METHOD:PUBLISH
X-CALSTART:20260713T000000
X-CALEND:20270826T000000
X-WR-RELCALID:{0000002E-24FB-F552-A38C-30DF2D6F3E68}
X-WR-CALNAME:Vacances scolaires majoritaire 2026/27
BEGIN:VEVENT
CLASS:PUBLIC
CREATE
11
DTEND;VALUE=DATE:20260827
DTSTART;VALUE=DATE:20260713
SUMMARY;LANGUAGE=fr-ch:Vacances d'été
DTEND;VALUE=DATE:20261024
DTSTART;VALUE=DATE:20261012
SUMMARY;LANGUAGE=fr-ch:Vacances d'automne
DTEND;VALUE=DATE:20261209
DTSTART;VALUE=DATE:20261208
SUMMARY;LANGUAGE=fr-ch:Immaculée Conception
DTEND;VALUE=DATE:20270102
DTSTART;VALUE=DATE:20261221
SUMMARY;LANGUAGE=fr-ch:Vacances de Noël
200 application/pdf 54686B https://www.fr.ch/sites/default/files/2025-10/calendrier-majoritaire-20262027.pdf?v=1761656109
1
        	 
     
      
 
  
 
  	    	 	 
   
  

    



 	   

  

 	    	 	 



 	 



  
 
 

  ! " # $% & ' ( ) * ++" ' , - . ( * / 0 ' 1 + 2 * + 3 4 - 5 $ ( 6 * 50
7 7 8 9 7  : * - * + - ' , & ) * $% . ; +' < ' 0 # , % 2 ' 0 / ' +
 7 77
=
. $ , , * / + % 1 ( ( ' 0 5' / ( / 3 ' +
  7
> ; ; * -
```

## Step 35: Bash: Grep FR sitemap for tax guide pages
```
cd <scratchpad-overnight>/stage0/sitemaps && F=www.fr.ch.txt; echo "impots pages: $(grep -c 'fr.ch/impots' $F)"; grep -E "fr.ch/impots" $F | grep -i -E "instruction|guide|declaration|directive|commentaire|notice|fritax|brochure|aide" | head -30
```
Result:
```
impots pages: 79
https://www.fr.ch/impots/personnes-physiques/fritax
https://www.fr.ch/impots/personnes-physiques/fritax/fritax-faq
https://www.fr.ch/impots/personnes-physiques/fritax/telecharger-fritax
https://www.fr.ch/impots/personnes-physiques/mise-en-consultation-de-lavant-projet-de-loi-modifiant-la-loi-sur-les-impots-cantonaux-directs-et-la-loi-sur-laide-sociale
https://www.fr.ch/impots/personnes-physiques/obtenir-un-delai-pour-le-depot-de-sa-declaration
https://www.fr.ch/impots/personnes-physiques/prolongation-du-delai-pour-le-depot-de-la-declaration-pour-les-representants-personnes-physiques
```

## Step 36: Bash: List all FR tax pages from sitemap
```
cd <scratchpad-overnight>/stage0/sitemaps && F=www.fr.ch.txt; grep -E "fr.ch/impots" $F | awk '{print length, $0}' | sort -n | cut -d' ' -f2 | head -80
```
Result:
```
https://www.fr.ch/impots/impot-a-la-source
https://www.fr.ch/impots/personnes-morales
https://www.fr.ch/impots/paiement-des-impots
https://www.fr.ch/impots/personnes-physiques
https://www.fr.ch/impots/personnes-morales/e-tax-pm
https://www.fr.ch/impots/personnes-physiques/fritax
https://www.fr.ch/impots/personnes-morales/e-tax-pm-faq
https://www.fr.ch/impots/personnes-morales/taxe-sociale
https://www.fr.ch/impots/impot-sur-les-gains-immobiliers
https://www.fr.ch/impots/paiement-des-impots/remise-dimpot
https://www.fr.ch/impots/personnes-physiques/taxe-militaire
https://www.fr.ch/impots/paiement-des-impots/acomptes-impots
https://www.fr.ch/impots/personnes-physiques/limpot-anticipe
https://www.fr.ch/impots/personnes-physiques/fritax/fritax-faq
https://www.fr.ch/impots/rappel-dimpot-et-soustraction-fiscale
https://www.fr.ch/impots/personnes-physiques/calculer-ses-impots
https://www.fr.ch/impots/paiement-des-impots/payer-les-impots-faq
https://www.fr.ch/impots/personnes-physiques/impots-bases-legales
https://www.fr.ch/impots/personnes-physiques/activite-independante
https://www.fr.ch/impots/personnes-physiques/certificat-de-salaire
https://www.fr.ch/impots/personnes-physiques/vehicules-dentreprise
https://www.fr.ch/impots/impot-sur-les-successions-et-les-donations
https://www.fr.ch/impots/personnes-physiques/imposition-individuelle
https://www.fr.ch/impots/personnes-physiques/estimation-des-immeubles
https://www.fr.ch/impots/personnes-physiques/famille-et-impots-directs
https://www.fr.ch/impots/personnes-physiques/fritax/telecharger-fritax
https://www.fr.ch/impots/personnes-morales/e-tax-pm-assistance-en-ligne
https://www.fr.ch/impots/personnes-physiques/famille-et-impots-indirects
https://www.fr.ch/impots/personnes-physiques/formulaires-personnes-physiques
https://www.fr.ch/impots/personnes-physiques/prestations-en-ligne-des-impots
https://www.fr.ch/impots/impot-a-la-source/personnes-imposees-a-la-source-pis
https://www.fr.ch/impots/personnes-physiques/statistiques-fiscales-officielles
https://www.fr.ch/impots/personnes-morales/impots-sur-le-benefice-et-le-capital
https://www.fr.ch/impots/personnes-physiques/impots-des-personnes-physiques-faq
https://www.fr.ch/impots/personnes-physiques/coefficients-communaux-et-paroisses
https://www.fr.ch/impots/impot-a-la-source/debiteurs-dune-prestation-imposable-dpi
https://www.fr.ch/impots/personnes-morales/demande-de-delai-pour-personnes-morales
https://www.fr.ch/impots/personnes-morales/devenir-utilisateurmandataire-d
```

## Step 37: Bash: Probe FR tax forms and legal-basis pages
```
cd /tmp/sg-verify-run3-d && python3 probe.py "https://www.fr.ch/impots/personnes-physiques/formulaires-personnes-physiques::(instruction|guide|directive)" "https://www.fr.ch/impots/personnes-physiques/impots-bases-legales::(directive|commentaire|instruction|pratique)" "https://www.fr.ch/impots/personnes-physiques/impots-des-personnes-physiques-faq::(déduction|frais)" >/tmp/sg-verify-run3-d/fr_tax.txt 2>&1; cat fr_tax.txt; cd pages && python3 - <<'EOF'
import re,glob
for pat in ['*formulaires_personnes_physiques*','*impots_bases_legales*']:
    f=glob.glob(pat)[0]
    t=open(f,encoding='utf-8',errors='replace').read()
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S|re.I):
        h=m.group(1); lab=re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",m.group(2))).strip()
        if re.search(r'document|\.pdf|instruction|guide|directive|commentaire|bdlf|pratique',h+lab,re.I): print(pat[:25],h,'|',lab[:90])
EOF
```
Result:
```
==> https://www.fr.ch/impots/personnes-physiques/formulaires-personnes-physiques
200 | text/html; charset=UTF-8 | 82060B | https://www.fr.ch/impots/personnes-physiques/formulaires-personnes-physiques
   title: Formulaires - personnes physiques | Etat de Fribourg
   links=67 words=364  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_impots_personnes_physiques_formulaires_personnes_physiques_14a80b
   SAMPLE: <no match for (instruction|guide|directive) >
==> https://www.fr.ch/impots/personnes-physiques/impots-bases-legales
200 | text/html; charset=UTF-8 | 96394B | https://www.fr.ch/impots/personnes-physiques/impots-bases-legales
   title: Impôts : bases légales | Etat de Fribourg
   links=99 words=718  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_impots_personnes_physiques_impots_bases_legales_77a282
   SAMPLE: <no match for (directive|commentaire|instruction|pratique) >
==> https://www.fr.ch/impots/personnes-physiques/impots-des-personnes-physiques-faq
200 | text/html; charset=UTF-8 | 95320B | https://www.fr.ch/impots/personnes-physiques/impots-des-personnes-physiques-faq
   title: Impôts des personnes physiques : FAQ | Etat de Fribourg
   links=69 words=1882  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_impots_personnes_physiques_impots_des_personnes_physiques_faq_038dc5
   SAMPLE: ution d'entretien pour mon fils majeur qui est en étude. Puis-je revendiquer la déduction de ces montants ? Les contributions d’entretien sont déductibles jusqu'à la fin du mois où l'enfant atteint l'âge de 18 ans révolus. Au-delà, elles ne sont plu
   SAMPLE: les. Par contre, suivant l’importance de vos contributions, vous avez droit aux déductions sociales pour enfants. J'ai reçu un capital de ma caisse de retraite. Comment ce dernier est-il imposable ? Les prestations en capital ayant un caractère de p
*formulaires_personnes_ph https://www.fr.ch/vie-quotidienne/documents-didentite/passeports-et-cartes-didentite | Passeport et carte d&#039;identité
*formulaires_personnes_ph https://bdlf.fr.ch/app/fr/systematic/texts_of_law | Législation fribourgeoise
*formulaires_personnes_ph /document/58176 | Annexe relative aux frais médicaux PDF, 572.5k
*formulaires_personnes_ph /document/58181 | Annexe relative aux versements bénévoles PDF, 256.64k
*impots_bases_legales* https://www.fr.ch/vie-quotidienne/documents-didentite/passeports-et-cartes-didentite | Passeport et carte d&#039;identité
*impots_bases_legales* https://bdlf.fr.ch/app/fr/systematic/texts_of_law | Législation frib
```

## Step 38: Bash: Look for FR tax guide PDFs on tax pages
```
cd /tmp/sg-verify-run3-d && python3 probe.py "https://www.fr.ch/impots/personnes-physiques/tout-sur-les-impots-dans-le-canton-de-fribourg::(instruction|guide|brochure)" "https://www.fr.ch/impots/personnes-physiques/impot-des-personnes-physiques-themes-particuliers::(instruction|guide|directive|pratique)" "https://www.fr.ch/impots/personnes-physiques::(instruction|guide)" 2>&1 | grep -v "^   SAMPLE: <no"; cd pages && python3 - <<'EOF'
import re,glob
for pat in ['*tout_sur_les_impots*','*themes_particuliers*','https_www_fr_ch_impots_personnes_physiques_[0-9a-f]*']:
    for f in glob.glob(pat):
        t=open(f,encoding='utf-8',errors='replace').read()
        for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S|re.I):
            h=m.group(1); lab=re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",m.group(2))).strip()
            if re.search(r'/document/|\.pdf|instruction|guide|directive|brochure',h+lab,re.I): print(pat[:25],h,'|',lab[:100])
EOF
```
Result:
```
==> https://www.fr.ch/impots/personnes-physiques/tout-sur-les-impots-dans-le-canton-de-fribourg
200 | text/html; charset=UTF-8 | 89859B | https://www.fr.ch/impots/personnes-physiques/tout-sur-les-impots-dans-le-canton-de-fribourg
   title: Tout sur les impôts dans le canton de Fribourg | Etat de Fribourg
   links=85 words=489  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_impots_personnes_physiques_tout_sur_les_impots_dans_le_canton_de_fribourg_826f67
==> https://www.fr.ch/impots/personnes-physiques/impot-des-personnes-physiques-themes-particuliers
200 | text/html; charset=UTF-8 | 90724B | https://www.fr.ch/impots/personnes-physiques/impot-des-personnes-physiques-themes-particuliers
   title: Impôt des personnes physiques: thèmes particuliers | Etat de Fribourg
   links=83 words=509  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_impots_personnes_physiques_impot_des_personnes_physiques_themes_particuliers_357fea
   SAMPLE: thèmes particuliers Impôt des personnes physiques: thèmes particuliers Chapeau Instructions générales concernant la déclaration d'impôts, activité indépendante, fortune à l'étranger, impôt anticipé, etc. Activité indépendante Fortune à l'étranger Fra
   SAMPLE: tiers Impôt anticipé Estimation des immeubles Annexes de la déclaration fiscale Instructions générales concernant la déclaration d'impôt PDF, 316.68k Procuration pour personnes physiques PDF, 459.05k Assujettissement inférieur à une année en cas de dé
==> https://www.fr.ch/impots/personnes-physiques
200 | text/html; charset=UTF-8 | 82976B | https://www.fr.ch/impots/personnes-physiques
   title: Personnes physiques | Etat de Fribourg
   links=65 words=579  file=/tmp/sg-verify-run3-d/pages/https_www_fr_ch_impots_personnes_physiques_69b5c9
   SAMPLE: e à une ... Démarrer Impôt des personnes physiques: thèmes particuliers Chapeau Instructions générales concernant la déclaration d'impôts, activité indépendante, fortune à l'étranger, impôt anticipé, etc. Démarrer Obtenir un délai pour le dépôt de sa
*themes_particuliers* /document/57721 | Instructions générales concernant la déclaration d'impôt PDF, 316.68k
*themes_particuliers* /document/492491 | Procuration pour personnes physiques PDF, 459.05k
*themes_particuliers* /document/57736 | Assujettissement inférieur à une année en cas de départs et arrivées de l'étranger ainsi que lors du
*themes_particuliers* /document/401471 | Gains de loterie PDF, 143.23k
*themes_particuliers* /document/375771 | Traitement fiscal de la location d'im
```

## Step 39: Bash: Verify FR tax instructions PDF text layer
```
cd /tmp/sg-verify-run3-d && curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o fr_tax_57721.pdf -w "%{http_code} %{content_type} %{size_download}B %{url_effective}\n" "https://www.fr.ch/document/57721"; python3 -c "
from pypdf import PdfReader; import re
r=PdfReader('fr_tax_57721.pdf'); print('pages',len(r.pages))
t=' '.join((r.pages[i].extract_text() or '') for i in range(len(r.pages)))
t=re.sub(r'\s+',' ',t); print('chars',len(t)); print(t[:400])
m=re.search(r'.{0,120}(Fr\.|CHF) ?\d[\d\'.]*.{0,80}',t); print('SAMPLE:',m.group(0) if m else None)
"
```
Result:
```
200 application/pdf 324278B https://www.fr.ch/sites/default/files/2026-05/instructions-generales-concernant-la-declaration-d-impot_0.pdf?v=1778497822
pages 50
chars 122632
La présente formule, dûment remplie et signée, doit être retournée dans l’enveloppe prévue à cet effet au Service cantonal des contributions au plus tard jusqu’au Situation personnelle, professionnelle et familiale le 31 décembre 2025 PERSONNE 1* PERSONNE 2* N o AVS N o AVS Date de naissance Date de naissance État civil et date Religion Religion Nom de naissance Profession Profession Employeurs 20
SAMPLE: es des impôts en raison de leur but de service public ou d’utilité publique sont déductibles. Le montant minimal est de Fr. 100.- par année fiscale et le montant maximal est li- mité à 20% du revenu net (code
```

## Step 40: Bash: Grep OCN sitemap for fees, registration, licences
```
cd <scratchpad-overnight>/stage0/sitemaps && F=www.ocn.ch.txt; echo "fr: $(grep -c '/fr/' $F) de: $(grep -c '/de/' $F)"; grep -E "/fr/" $F | grep -i -E "emolument|tarif|prix|frais|immatricul|permis-de-conduire$|plaques" | head -20
```
**No result: this is the command that was waiting for approval when the run stalled.**
