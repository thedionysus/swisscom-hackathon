# Run 3 agent C: progress before the stall (log a9363af37f7465c1d, 03:30–03:39 UTC 2026-09-23)

Extracted verbatim from the agent transcript. Results are truncated to 2,500 characters. The files it wrote under /tmp are gone.

> I'll start by reading the brief in full.

## Step 1: Bash: Count brief lines and list scratchpad files
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

## Step 3: Bash: Read precheck entry points and list stage0 files
```
SP=<scratchpad-overnight>; cat $SP/precheck_entry_points_2026-09-23.md; echo ----; ls -la $SP/stage0 $SP/stage0/sitemaps 2>/dev/null | head -80; ls -la $SP/reports
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

## Step 4: Bash: Show sitemap summary entries for my cantons
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/sitemaps_summary.json'))
print(type(d), len(d))
if isinstance(d,dict):
    for k,v in d.items():
        s=json.dumps(v)
        if any(x in k.lower() or x in s.lower() for x in ['sg.ch','tg.ch','ar.ch','ai.ch','sh.ch','schaffhausen']):
            print(k, s[:1500])
else:
    for v in d:
        s=json.dumps(v)
        if any(x in s.lower() for x in ['sg.ch','tg.ch','ar.ch','ai.ch','sh.ch','schaffhausen']):
            print(s[:1500])
"; cat $SP/stage0/sitemap_fetch.py
```
Result:
```
<class 'dict'> 2
hosts {"ZH": ["www.zh.ch", "www.gerichte-zh.ch", "www.stadt-zuerich.ch"], "BE": ["www.zsg.justice.be.ch", "www.rsta.dij.be.ch", "www.svsa.sid.be.ch", "www.sv.fin.be.ch", "www.weu.be.ch", "www.bkd.be.ch", "www.sta.be.ch", "www.akvb-gemeinden.bkd.be.ch", "www.be.ch", "www.bern.ch", "www.thun.ch"], "LU": ["www.lu.ch", "gerichte.lu.ch", "veterinaerdienst.lu.ch", "steuerbuch.lu.ch", "strassenverkehrsamt.lu.ch", "volksschulbildung.lu.ch"], "UR": ["www.ur.ch"], "SZ": ["www.sz.ch"], "OW": ["www.ow.ch"], "NW": ["www.nw.ch"], "GL": ["www.gl.ch"], "ZG": ["zg.ch"], "FR": ["www.fr.ch", "www.ocn.ch"], "SO": ["so.ch"], "BS": ["www.bs.ch"], "BL": ["www.baselland.ch"], "SH": ["sh.ch", "www.stadt-schaffhausen.ch"], "AR": ["ar.ch"], "AI": ["www.ai.ch"], "SG": ["www.sg.ch"], "GR": ["www.gr.ch"], "AG": ["www.ag.ch"], "TG": ["www.tg.ch", "strassenverkehrsamt.tg.ch", "staatskanzlei.tg.ch"], "TI": ["www4.ti.ch", "www.lugano.ch"], "VD": ["www.vd.ch", "www.lausanne.ch"], "VS": ["www.vs.ch"], "NE": ["www.ne.ch", "www.scan-ne.ch", "www.chaux-de-fonds.ch", "www.neuchatelville.ch"], "GE": ["www.ge.ch", "justice.ge.ch", "www.geneve.ch", "www.vernier.ch"], "JU": ["www.jura.ch"]}
result {"www.zh.ch": {"urls": 80504, "sitemaps_fetched": 45, "delay": 0.3, "log": ["robots 200", "https://www.zh.ch/bin/zhweb/publish/sitemap.xml 200 44", "https://www.zh.ch/de-ls.zhweb-sitemap.xml 200 1"]}, "www.gerichte-zh.ch": {"urls": 454, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.gerichte-zh.ch/sitemap.xml 200 454", "https://www.gerichte-zh.ch/sitemap_index.xml 404 0"]}, "www.stadt-zuerich.ch": {"urls": 0, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.stadt-zuerich.ch/sitemap.xml 404 0", "https://www.stadt-zuerich.ch/sitemap_index.xml 404 0"]}, "www.zsg.justice.be.ch": {"urls": 256, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.zsg.justice.be.ch/sitemap.xml 200 6", "https://www.zsg.justice.be.ch/de/sitemap.xml 200 127"]}, "www.rsta.dij.be.ch": {"urls": 130, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.rsta.dij.be.ch/sitemap.xml 200 6", "https://www.rsta.dij.be.ch/de/sitemap.xml 200 66"]}, "www.svsa.sid.be.ch": {"urls": 462, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https://www.svsa.sid.be.ch/sitemap.xml 200 6", "https://www.svsa.sid.be.ch/de/sitemap.xml 200 229"]}, "www.sv.fin.be.ch": {"urls": 344, "sitemaps_fetched": 7, "delay": 10.0, "log": ["robots 200", "https
```

## Step 5: Bash: Show sitemap results for my cantons' hosts
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/sitemaps_summary.json'))
for h in ['www.sg.ch','www.tg.ch','strassenverkehrsamt.tg.ch','staatskanzlei.tg.ch','ar.ch','www.ai.ch','sh.ch','www.stadt-schaffhausen.ch']:
    print(h, json.dumps(d['result'].get(h)))
"; ls $SP/stage0/sitemaps | grep -i tg; wc -l $SP/stage0/sitemaps/{www.sg.ch,strassenverkehrsamt.tg.ch,staatskanzlei.tg.ch,ar.ch,www.ai.ch,sh.ch,www.stadt-schaffhausen.ch}.txt
```
Result:
```
www.sg.ch {"urls": 4716, "sitemaps_fetched": 1, "delay": 0.3, "log": ["robots 200", "https://www.sg.ch/tools/sitemap.googleSitemap.xml 200 4785"]}
www.tg.ch {"urls": 406, "sitemaps_fetched": 1, "delay": 0.3, "log": ["robots 200", "https://www.tg.ch/sitemap.xml 200 406"]}
strassenverkehrsamt.tg.ch {"urls": 141, "sitemaps_fetched": 1, "delay": 0.3, "log": ["robots 200", "https://strassenverkehrsamt.tg.ch/sitemap.xml 200 141"]}
staatskanzlei.tg.ch {"urls": 6, "sitemaps_fetched": 1, "delay": 0.3, "log": ["robots 200", "https://staatskanzlei.tg.ch/sitemap.xml 200 6"]}
ar.ch {"urls": 1719, "sitemaps_fetched": 4, "delay": 0.3, "log": ["robots 200", "https://ar.ch/sitemap.xml 200 2", "https://ar.ch/sitemap_index.xml 404 0"]}
www.ai.ch {"urls": 20492, "sitemaps_fetched": 1, "delay": 0.3, "log": ["robots 200", "https://www.ai.ch/sitemap.xml.gz 200 20492"]}
sh.ch {"urls": 600, "sitemaps_fetched": 8, "delay": 0.3, "log": ["robots 200", "https://sh.ch/Sitemap/SitemapXml 200 7", "https://sh.ch/Sitemap/SitemapXml/sitemapxml?contentType=HOME&language=DE&domainId=1753&priority=1.0&changefreq=daily 200 1"]}
www.stadt-schaffhausen.ch {"urls": 219, "sitemaps_fetched": 2, "delay": 0.3, "log": ["robots 200", "https://www.stadt-schaffhausen.ch/sitemap.xml 200 220", "https://www.stadt-schaffhausen.ch/sitemap_index.xml 404 0"]}
staatskanzlei.tg.ch.txt
strassenverkehrsamt.tg.ch.txt
www.tg.ch.txt
    4715 <scratchpad-overnight>/stage0/sitemaps/www.sg.ch.txt
     140 <scratchpad-overnight>/stage0/sitemaps/strassenverkehrsamt.tg.ch.txt
       5 <scratchpad-overnight>/stage0/sitemaps/staatskanzlei.tg.ch.txt
    1718 <scratchpad-overnight>/stage0/sitemaps/ar.ch.txt
   20491 <scratchpad-overnight>/stage0/sitemaps/www.ai.ch.txt
     599 <scratchpad-overnight>/stage0/sitemaps/sh.ch.txt
     218 <scratchpad-overnight>/stage0/sitemaps/www.stadt-schaffhausen.ch.txt
   27886 total
```

## Step 6: Bash: Show law hits for SG, TG, AR, AI, SH
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/law_hits.json'))
print(type(d), list(d.keys())[:40] if isinstance(d,dict) else len(d))
for c in ['SG','TG','AR','AI','SH']:
    v=d.get(c)
    print('=====',c)
    print(json.dumps(v,ensure_ascii=False,indent=1)[:6000])
"
```
Result:
```
<class 'dict'> ['AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH']
===== SG
{
 "court_fees": [
  {
   "nr": "821.1",
   "title": "Verordnung über Kosten und Entschädigungen im Verwaltungsverfahren (Verwaltungsgebührenverordnung) (VGV)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/821.1"
  },
  {
   "nr": "941.12",
   "title": "Gerichtskostenverordnung",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/941.12"
  }
 ],
 "court_org": [
  {
   "nr": "961.2",
   "title": "Einführungsgesetz zur Schweizerischen Zivilprozessordnung (EG-ZPO)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/961.2"
  },
  {
   "nr": "941.1",
   "title": "Gerichtsgesetz (GerG)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/941.1"
  }
 ],
 "road": [
  {
   "nr": "711.1",
   "title": "Einführungsverordnung zum eidgenössischen Strassenverkehrsgesetz",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/711.1"
  },
  {
   "nr": "711.70",
   "title": "Gesetz über die Strassenverkehrsabgaben (SVAG)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/711.70"
  },
  {
   "nr": "711.73",
   "title": "Verordnung über die Strassenverkehrsabgaben (SVAV)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/711.73"
  },
  {
   "nr": "711.74",
   "title": "Regierungsratsbeschluss über den Vollzug der eidgenössischen Vorschriften über die Schwerverkehrsabgabe und die Nationalstrassenabgabe",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/711.74"
  }
 ],
 "tax": [
  {
   "nr": "811.1",
   "title": "Steuergesetz (StG)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/811.1"
  }
 ],
 "dogs": [
  {
   "nr": "671.513",
   "title": "Regierungsratsbeschluss über das Pflanzenschutzgebiet Hoher Kasten-Kamor-Schwämme-Chienberg",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/671.513"
  },
  {
   "nr": "456.1",
   "title": "Hundegesetz (HuG)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/456.1"
  },
  {
   "nr": "456.11",
   "title": "Hundeverordnung (HuV)",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/456.11"
  }
 ],
 "conciliation": [
  {
   "nr": "941.112",
   "title": "Verordnung über die Schlichtungsbehörden",
   "api": "https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/941.112"
  },
  
```

## Step 7: Bash: Show sitemap topic candidates for SG
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/sitemap_topic_candidates.json'))
print(type(d), list(d.keys())[:40] if isinstance(d,dict) else len(d))
for c in ['SG']:
    v=d.get(c)
    print('=====',c)
    if isinstance(v,dict):
        for t,x in v.items():
            print('--',t, json.dumps(x,ensure_ascii=False)[:3000])
"
```
Result:
```
<class 'dict'> ['ZH', 'BE', 'LU', 'UR', 'SZ', 'OW', 'NW', 'GL', 'ZG', 'FR', 'SO', 'BS', 'BL', 'SH', 'AR', 'AI', 'SG', 'GR', 'AG', 'TG', 'TI', 'VD', 'VS', 'NE', 'GE', 'JU']
===== SG
-- courts {"count": 339, "shortest": ["https://www.sg.ch/recht/gerichte.html", "https://www.sg.ch/recht/gerichte/links.html", "https://www.sg.ch/recht/gerichte/aktuelles.html", "https://www.sg.ch/sicherheit/justizvollzug.html", "https://www.sg.ch/recht/gerichte/rechtsprechung.html", "https://www.sg.ch/sicherheit/justizvollzug/rgal.html", "https://www.sg.ch/recht/gerichte/verhandlungstermine.html", "https://www.sg.ch/sicherheit/justizvollzug/saxerriet.html", "https://www.sg.ch/recht/gerichte/aktuelles/lehrstellen.html", "https://www.sg.ch/recht/gerichte/anwalts----notarwesen.html", "https://www.sg.ch/sicherheit/justizvollzug/platanenhof.html", "https://www.sg.ch/recht/gerichte/aktuelles/mitteilungen.html", "https://www.sg.ch/sicherheit/justizvollzug/rgal/kontakt.html", "https://www.sg.ch/sicherheit/justizvollzug/rgal/portrait.html", "https://www.sg.ch/recht/gerichte/organisation---standorte.html", "https://www.sg.ch/sicherheit/justizvollzug/saxerriet/shop.html", "https://www.sg.ch/recht/gerichte/informationen---formulare.html", "https://www.sg.ch/sicherheit/justizvollzug/rgal/ihr-besuch.html", "https://www.sg.ch/sicherheit/justizvollzug/bewaehrungshilfe.html", "https://www.sg.ch/sicherheit/justizvollzug/platanenhof/shop.html", "https://www.sg.ch/sicherheit/justizvollzug/saxerriet/kontakt.html", "https://www.sg.ch/sicherheit/justizvollzug/saxerriet/portrait.html", "https://www.sg.ch/recht/gerichte/anwalts----notarwesen/honorar.html", "https://www.sg.ch/recht/gerichte/offenlegung-interessenbindung.html", "https://www.sg.ch/sicherheit/justizvollzug/platanenhof/kontakt.html", "https://www.sg.ch/sicherheit/justizvollzug/platanenhof/portrait.html", "https://www.sg.ch/sicherheit/justizvollzug/saxerriet/ihr-besuch.html", "https://www.sg.ch/recht/gerichte/anwalts----notarwesen/formulare.html", "https://www.sg.ch/recht/gerichte/anwalts----notarwesen/praktikum.html", "https://www.sg.ch/recht/gerichte/anwalts----notarwesen/pruefungen.html", "https://www.sg.ch/sicherheit/justizvollzug/platanenhof/ihr-besuch.html", "https://www.sg.ch/sicherheit/justizvollzug/massnahmenzentrum-bitzi.html", "https://www.sg.ch/sicherheit/justizvollzug/rgal/aufgaben-und-werte.html", "https://www.sg.ch/sicherheit/justizvollzug/straf-massnahmenvollzug.html", "https://www.sg.ch/sicherheit/justizvollzug/bewaehrungshil
```

## Step 8: Bash: Show sitemap topic candidates for TG and AR
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/sitemap_topic_candidates.json'))
for c in ['TG','AR']:
    v=d.get(c)
    print('=====',c)
    for t,x in v.items():
        print('--',t, x.get('count'))
        for u in x.get('shortest',[])[:40]: print('   ',u)
"
```
Result:
```
===== TG
-- courts 30
    https://www.tg.ch/justiz.html/5
    https://www.tg.ch/justiz/anwaltswesen.html/37
    https://www.tg.ch/justiz/verwaltungsrechtspflege.html/33
    https://www.tg.ch/verwaltung/justiz-und-sicherheit.html/110
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege.html/23
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/djs.html/148
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/eichamt.html/156
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege/obergericht.html/25
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/migrationsamt.html/157
    https://wahlen.tg.ch/2019/201019/friedensrichterin-bezirk-arbon.html/10181
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/feuerschutzamt.html/161
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/kantonspolizei.html/159
    https://www.tg.ch/justiz/verwaltungsrechtspflege/verwaltungsgericht.html/34
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege/organisation.html/179
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege/bezirksgericht.html/29
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/schiffsregisteramt.html/151
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/staatsanwaltschaft.html/153
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/strassenverkehrsamt.html/155
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege/staatsanwaltschaft.html/31
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege/zwangsmassnahmengericht.html/32
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/massnahmenzentrum-kalchrain.html/154
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/grundbuchaemter-und-notariate.html/150
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/jagd--und-fischereiverwaltung.html/158
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege/amt-fuer-friedensrichterwesen.html/17710
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/amt-fuer-betreibungs-und-konkurswesen.html/152
    https://www.tg.ch/regierung/kommissionen/schlichtungsstelle-gemaess-gleichstellungsgesetz-.html/78
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/amt-fuer-bevoelkerungsschutz-und-armee.html/160
    https://www.tg.ch/justiz/zivil--und-strafrechtspflege/kindes--und-erwachsenenschutzbehoerde.html/30
    https://www.tg.ch/justiz/verwaltungsrechtspflege/rekurskommissionen-und-enteignungskommission.html/35
    https://www.tg.ch/verwaltung/justiz-und-sicherheit/amt-fuer-handelsregister-und-zivilstandswesen.html
```

## Step 9: Bash: Show sitemap topic candidates for AI and SH
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/sitemap_topic_candidates.json'))
for c in ['AI','SH']:
    v=d.get(c)
    print('=====',c)
    for t,x in v.items():
        print('--',t, x.get('count'))
        for u in x.get('shortest',[])[:40]: print('   ',u)
"
```
Result:
```
<persisted-output>
Output too large (35.1KB). Full output saved to: <claude-project-dir>/020cdda0-8dd0-4108-896f-cca0e5f386a1/tool-results/bj7pliyvk.txt

Preview (first 2KB):
===== AI
-- courts 911
    https://www.ai.ch/gerichte
    https://www.ai.ch/gerichte/test
    https://www.ai.ch/personen-gerichte
    https://www.ai.ch/gerichte/aktuelles
    https://www.ai.ch/gerichte/vermittler
    https://www.ai.ch/gerichte/anwaltskammer
    https://www.ai.ch/gerichte/aktuelles/news
    https://www.ai.ch/gerichte/bezirksgericht
    https://www.ai.ch/gerichte/kantonsgericht
    https://www.ai.ch/gerichte/rechtsprechung
    https://www.ai.ch/gerichte/termine-gerichte
    https://www.ai.ch/gerichte/gerichtsentscheide
    https://www.ai.ch/gerichte/geschaeftsberichte
    https://www.ai.ch/themen/staat-und-recht/gerichte
    https://www.ai.ch/gerichte/bezirksgericht/formulare
    https://www.ai.ch/gerichte/kantonsgericht/aktuelles
    https://www.ai.ch/gerichte/anwaltskammer/direktlinks
    https://www.ai.ch/gerichte/ftw-news-newslistingblock
    https://www.ai.ch/gerichte/geschaeftsberichte/bisher
    https://www.ai.ch/gerichte/vermittler/vermittleraemter
    https://www.ai.ch/gerichte/bezirksgericht/gesamtgericht
    https://www.ai.ch/gerichte/aktuelles/news-auf-startseite
    https://www.ai.ch/gerichte/anwaltskammer/zusammensetzung
    https://www.ai.ch/gerichte/kantonsgericht/aktuelles/news
    https://www.ai.ch/gerichte/bezirksgericht/zusammensetzung
    https://www.ai.ch/gerichte/kantonsgericht/zusammensetzung
    https://www.ai.ch/gerichte/elektronischer-geschaeftsverkehr
    https://www.ai.ch/gerichte/rechtsprechung/aktuelle-entscheide
    https://www.ai.ch/gerichte/rechtsprechung/aktuelle-entscheide-1
    https://www.ai.ch/gerichte/bezirksgericht/termine-bezirksgericht
    https://www.ai.ch/gerichte/gerichtsentscheide/gerichtsentscheide
    https://www.ai.ch/gerichte/kantonsgericht/termine-kantonsgericht
    https://www.ai.ch/gerichte/vermittler/ftw-simplelayout-textblock
    https://www.ai.ch/gerichte/bezirksgericht/zwangsmassnahmengericht
    https://www.ai.ch/gerichte/kantonsgericht/aufsichtsbehoerde-schkg
...
</persisted-output>
```

## Step 10: Bash: Show AI and SH topic candidates, trimmed
```
SP=<scratchpad-overnight>; python3 -c "
import json
d=json.load(open('$SP/stage0/sitemap_topic_candidates.json'))
for c in ['AI','SH']:
    v=d.get(c)
    print('=====',c)
    for t,x in v.items():
        print('--',t, x.get('count'))
        for u in x.get('shortest',[])[:25]: print('   ',u[:170])
" | cut -c1-180 | sed -n '1,400p' | grep -v 'ftw-' 
```
Result:
```
===== AI
-- courts 911
    https://www.ai.ch/gerichte
    https://www.ai.ch/gerichte/test
    https://www.ai.ch/personen-gerichte
    https://www.ai.ch/gerichte/aktuelles
    https://www.ai.ch/gerichte/vermittler
    https://www.ai.ch/gerichte/anwaltskammer
    https://www.ai.ch/gerichte/aktuelles/news
    https://www.ai.ch/gerichte/bezirksgericht
    https://www.ai.ch/gerichte/kantonsgericht
    https://www.ai.ch/gerichte/rechtsprechung
    https://www.ai.ch/gerichte/termine-gerichte
    https://www.ai.ch/gerichte/gerichtsentscheide
    https://www.ai.ch/gerichte/geschaeftsberichte
    https://www.ai.ch/themen/staat-und-recht/gerichte
    https://www.ai.ch/gerichte/bezirksgericht/formulare
    https://www.ai.ch/gerichte/kantonsgericht/aktuelles
    https://www.ai.ch/gerichte/anwaltskammer/direktlinks
    https://www.ai.ch/gerichte/geschaeftsberichte/bisher
    https://www.ai.ch/gerichte/vermittler/vermittleraemter
    https://www.ai.ch/gerichte/bezirksgericht/gesamtgericht
    https://www.ai.ch/gerichte/aktuelles/news-auf-startseite
    https://www.ai.ch/gerichte/anwaltskammer/zusammensetzung
    https://www.ai.ch/gerichte/kantonsgericht/aktuelles/news
    https://www.ai.ch/gerichte/bezirksgericht/zusammensetzung
-- dogs 47
    https://www.ai.ch/themen/natur-und-umwelt/jagd/ausbildung-von-jagdhunden
    https://www.ai.ch/land-und-leute/veranstaltungen/18-appenzeller-hunderallye-2017
    https://www.ai.ch/themen/landwirtschaft-tierhaltung/tierhaltung/hundehalterausbildung
    https://www.ai.ch/land-und-leute/geschichte/18-19-jahrhundert-sennen-heubauern-und-grempler
    https://www.ai.ch/land-und-leute/veranstaltungen/18-appenzeller-hunderallye-2017/beschreibung
    https://www.ai.ch/land-und-leute/veranstaltungen/18-appenzeller-hunderallye-2017/angaben-anlass
    https://www.ai.ch/themen/landwirtschaft-tierhaltung/tierhaltung/hundehalterausbildung/direktlinks
    https://www.ai.ch/verwaltung/erziehungsdepartement/aktuelles/gemeinsames-appenzeller-liederbuch-erschienen
    https://www.ai.ch/themen/kultur-und-geschichte/kulturfoerderung/aktuelles/cd-zum-appenzeller-liederbuch-ist-erschienen
    https://www.ai.ch/themen/natur-und-umwelt/jagd/aktuelles-zur-jagd/wildernde-hunde-dringender-aufruf-der-jagdverwaltung
    https://www.ai.ch/politik/standeskommission/kantonale-vernehmlassungen/vernehmlassung-revision-der-verordnung-zum-hundegesetz-huv
    https://www.ai.ch/themen/kultur-und-geschichte/kulturfoerderung/aktuelles/cd-zum-appenzeller-liederbuch-ist-ersc
```

## Step 11: Bash: Inspect courts S1 rows file for my cantons
```
SP=<scratchpad-overnight>; head -c 1500 $SP/courts_s1_rows.py; echo; echo ======; grep -n -E "'(SG|TG|AR|AI|SH)'|\"(SG|TG|AR|AI|SH)\"|St\. ?Gallen|Thurgau|Appenzell|Schaffhausen" $SP/courts_s1_rows.py | head -80
```
Result:
```
Exit code 1
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
('ZH','Verwaltungsgericht','G:https://www.zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html','D:http
(eval):1: ===== not found
```

## Step 12: Bash: Show S1 court rows and probe results for my cantons
```
SP=<scratchpad-overnight>; grep -n -E "^\('(SG|TG|AR|AI|SH)'" $SP/courts_s1_rows.py; echo ======; python3 - <<'EOF'
import json
SP='<scratchpad-overnight>'
d=json.load(open(SP+'/courts_s1_probe.json'))
print(type(d), len(d))
items = d if isinstance(d,list) else d.get('results', d)
if isinstance(items, dict):
    print(list(items.keys())[:10])
    items=list(items.values())
print(json.dumps(items[0])[:500])
for it in items:
    s=json.dumps(it,ensure_ascii=False)
    if any(k in s for k in ['sg.ch','tg.ch','ar.ch','ai.ch','sh.ch','"SG"','"TG"','"AR"','"AI"','"SH"']):
        print(s[:400])
EOF
```
Result:
```
Exit code 1
38:('SH','Obergericht',f'G:{SH}/Obergericht-880221-DE.html',f'G:{SH}/Gebuehren-880230-DE.html',f'G:{SH}/Themen-880240-DE.html',f'G:{SH}/Entscheide-880250-DE.html'),
39:('SH','Kantonsgericht',f'G:{SH}/Kantonsgericht-880222-DE.html',f'G:{SH}/Gebuehren-880230-DE.html',f'G:{SH}/Themen-880240-DE.html',f'G:{SH}/Entscheide-880250-DE.html'),
40:('AR','Obergericht & Kantonsgericht',f'G:{AR}/',f'G:{AR}/gebuehren/',f'G:{AR}/themen/',f'G:{AR}/rechtsprechung/'),
41:('AI','Kantonsgericht',f'G:{AI}',f'G:{AI}/gebuehren',f'G:{AI}/ratgeber',f'G:{AI}/rechtsprechung'),
42:('SG','Kantonsgericht',f'G:{SG}/kantonsgericht.html',f'G:{SG}/themen/kosten-und-gebuehren.html',f'G:{SG}/themen.html',f'G:{SG}/rechtsprechung.html'),
43:('SG','Verwaltungsgericht',f'G:{SG}/verwaltungsgericht.html',f'G:{SG}/themen/kosten-und-gebuehren.html',f'G:{SG}/themen.html',f'G:{SG}/rechtsprechung.html'),
44:('SG','Kreisgerichte',f'G:{SG}/kreisgerichte.html',f'G:{SG}/themen/kosten-und-gebuehren.html',f'G:{SG}/themen.html',f'G:{SG}/rechtsprechung.html'),
51:('TG','Obergericht',f'G:{TG}/obergericht.html/10452',f'G:{TG}/themen/kosten.html/10460',f'G:{TG}/themen.html/10461',f'G:{TG}/entscheide.html/10462'),
52:('TG','Verwaltungsgericht',f'G:{TG}/verwaltungsgericht.html/10453',f'G:{TG}/themen/kosten.html/10460',f'G:{TG}/themen.html/10461',f'G:{TG}/entscheide.html/10462'),
53:('TG','Bezirksgerichte',f'G:{TG}/bezirksgerichte.html/10454',f'G:{TG}/themen/kosten.html/10460',f'G:{TG}/themen.html/10461',f'G:{TG}/entscheide.html/10462'),
(eval):1: ===== not found
```

## Step 13: Bash: Show probe results for my cantons in all three probe files
```
SP=<scratchpad-overnight>; python3 - <<'EOF'
import json
SP='<scratchpad-overnight>'
for fn in ['courts_s1_probe.json','guidance_s3a_probe.json','s3b_s4_probe.json']:
    d=json.load(open(SP+'/'+fn))
    print('#####',fn,type(d).__name__, len(d))
    items = d
    if isinstance(d, dict):
        print('keys', list(d.keys())[:10])
        for k in d:
            if isinstance(d[k], list): items=d[k]; break
    if isinstance(items, list) and items:
        print('sample', json.dumps(items[0],ensure_ascii=False)[:400])
        for it in items:
            s=json.dumps(it,ensure_ascii=False)
            if any(k in s for k in ['sg.ch','tg.ch','ar.ch','ai.ch','sh.ch','schaffhausen','"SG"','"TG"','"AR"','"AI"','"SH"']):
                print(s[:330])
EOF
```
Result:
```
##### courts_s1_probe.json dict 141
keys ['https://www.gerichte-zh.ch/', 'https://www.gerichte-zh.ch/themen/prozesskosten.html', 'https://www.gerichte-zh.ch/themen.html', 'https://www.gerichte-zh.ch/entscheide.html', 'https://www.zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html', 'https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht/informationen-zum-gerichtsverfahren.html', 'https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht.html', 'https://vgrzh.djiktzh.ch/', 'https://www.gerichte-zh.ch/organisation/bezirksgerichte.html', 'https://www.zsg.justice.be.ch/de/start.html']
##### guidance_s3a_probe.json list 69
sample {"canton": "AG", "topic": "dogs", "kind": "G", "url": "https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde", "code": "404", "cls": "http-404", "final": "https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde", "title": "404-Seite - Kanton Aargau", "size": 61442}
{"canton": "SG", "topic": "dogs", "kind": "G", "url": "https://www.sg.ch/gesundheit-soziales/verbraucherschutz-veterinaerwesen/veterinaerwesen/hunde.html", "code": "404", "cls": "http-404", "final": "https://www.sg.ch/gesundheit-soziales/verbraucherschutz-veterinaerwesen/veterinaerwesen/hunde.html", "title": "404 Not Found", "si
{"canton": "SG", "topic": "tax", "kind": "D", "url": "https://www.sg.ch/steuern-finanzen/steuern/steuerbuch.html", "code": "200", "cls": "ok", "final": "https://www.sg.ch/steuern-finanzen/steuern/steuerbuch.html", "title": "Steuerbuch und rechtliche Grundlagen | sg.ch", "size": 126734}
{"canton": "SG", "topic": "school", "kind": "G", "url": "https://www.sg.ch/bildung-sport/volksschule/schulferien.html", "code": "404", "cls": "http-404", "final": "https://www.sg.ch/bildung-sport/volksschule/schulferien.html", "title": "404 Not Found", "size": 598}
{"canton": "SG", "topic": "road", "kind": "G", "url": "https://www.sg.ch/verkehr/strassenverkehrsamt.html", "code": "404", "cls": "http-404", "final": "https://www.sg.ch/verkehr/strassenverkehrsamt.html", "title": "404 Not Found", "size": 588}
{"canton": "TG", "topic": "dogs", "kind": "G", "url": "https://veterinaeramt.tg.ch/hunde.html", "code": "404", "cls": "http-404", "final": "https://veterinaeramt.tg.ch/hunde.html", "title": "Seite nicht gefunden", "size": 22381}
{"canton": "TG", "topic": "tax", "kind": "G", "url": "https://steuerverwaltung.tg.ch/steuerbuch.html", "code": "404", "cls": "http-404", "final": "https://steuerverwaltung.tg.ch/steue
```

## Step 14: Bash: Show court probe results and other AI rows for my cantons
```
SP=<scratchpad-overnight>; python3 - <<'EOF'
import json
SP='<scratchpad-overnight>'
d=json.load(open(SP+'/courts_s1_probe.json'))
for k,v in d.items():
    if any(x in k for x in ['sg.ch','tg.ch','ar.ch','ai.ch','sh.ch']):
        print(k, '=>', json.dumps(v,ensure_ascii=False)[:300])
EOF
grep -n -i -E "sg|tg|ar\b|ai\b|sh|schaffhausen" $SP/cities_s2_links.txt; grep -n -E "'(SG|TG|AR|AI|SH)'" $SP/guidance_s3a_rows.py $SP/s3b_s4_rows.py | cut -c1-400
```
Result:
```
https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Obergericht-880221-DE.html => {"code": "500", "ct": "text/html", "size": 2213, "final": "https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Obergericht-880221-DE.html", "title": "Maintenance Page", "links": 0, "words": 18, "grounded": false, "class": "http-500"}
https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Gebuehren-880230-DE.html => {"code": "500", "ct": "text/html", "size": 2213, "final": "https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Gebuehren-880230-DE.html", "title": "Maintenance Page", "links": 0, "words": 18, "grounded": false, "class": "http-500"}
https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Themen-880240-DE.html => {"code": "500", "ct": "text/html", "size": 2213, "final": "https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Themen-880240-DE.html", "title": "Maintenance Page", "links": 0, "words": 18, "grounded": false, "class": "http-500"}
https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Entscheide-880250-DE.html => {"code": "500", "ct": "text/html", "size": 2213, "final": "https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Entscheide-880250-DE.html", "title": "Maintenance Page", "links": 0, "words": 18, "grounded": false, "class": "http-500"}
https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Kantonsgericht-880222-DE.html => {"code": "500", "ct": "text/html", "size": 2213, "final": "https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gerichte/Kantonsgericht-880222-DE.html", "title": "Maintenance Page", "links": 0, "words": 18, "grounded": false, "class": "http-500"}
https://www.ar.ch/verwaltung/kantonsgericht/ => {"code": "404", "ct": "text/html", "size": 100272, "final": "https://ar.ch/verwaltung/kantonsgericht/", "title": "Verirrt? - Appenzell Ausserrhoden", "links": 284, "words": 666, "grounded": false, "class": "http-404"}
https://www.ar.ch/verwaltung/kantonsgericht/gebuehren/ => {"code": "404", "ct": "text/html", "size": 100272, "final": "https://ar.ch/verwaltung/kantonsgericht/gebuehren/", "title": "Verirrt? - Appenzell Ausserrhoden", "links": 284, "words": 666, "grounded": false, "class": "http-404"}
https://www.ar.ch/verwaltung/kantonsgericht/themen/ => {"code": "404", "ct": "text/html", "size": 100272, "final": "https://ar.ch/verwaltung/kantonsgericht/themen/", "title": "Verirrt? - Appenzell Ausserrhoden", "links": 284, "words": 666, "grounded": false,
```

## Step 15: Bash: Show opencaselaw coverage for my cantons
```
SP=<scratchpad-overnight>; python3 - <<'EOF'
import json
SP='<scratchpad-overnight>'
d=json.load(open(SP+'/opencaselaw_courts_2026-09-23.json'))
print(type(d).__name__, (list(d.keys())[:10] if isinstance(d,dict) else len(d)))
items = d if isinstance(d,list) else (d.get('courts') or list(d.values())[0])
print(json.dumps(items[0])[:300] if isinstance(items,list) else str(items)[:300])
if isinstance(items,list):
    for it in items:
        if it.get('canton') in ('SG','TG','AR','AI','SH'):
            print(json.dumps(it,ensure_ascii=False))
EOF
```
Result:
```
list 136
{"court": "bger", "canton": "CH", "decision_count": 193393, "earliest": "1986-10-06", "latest": "2026-09-10", "languages": 3, "sparse": false}
{"court": "sg_versicherungsgericht", "canton": "SG", "decision_count": 7632, "earliest": "1979-02-16", "latest": "2026-08-19", "languages": 1, "sparse": false}
{"court": "ar_gerichte", "canton": "AR", "decision_count": 4614, "earliest": "1901-07-29", "latest": "2026-03-17", "languages": 1, "sparse": false}
{"court": "sg_gerichte", "canton": "SG", "decision_count": 3141, "earliest": "1969-07-04", "latest": "2026-01-14", "languages": 1, "sparse": false}
{"court": "sg_verwaltungsgericht", "canton": "SG", "decision_count": 2778, "earliest": "1968-07-27", "latest": "2026-06-29", "languages": 1, "sparse": false}
{"court": "tg_obergericht", "canton": "TG", "decision_count": 2443, "earliest": "1957-01-01", "latest": "2025-01-29", "languages": 1, "sparse": false}
{"court": "sg_verwaltungsrekurskommission", "canton": "SG", "decision_count": 1183, "earliest": "1931-04-02", "latest": "2026-07-02", "languages": 1, "sparse": false}
{"court": "tg_gerichte", "canton": "TG", "decision_count": 1162, "earliest": "1907-12-10", "latest": "2025-12-17", "languages": 1, "sparse": false}
{"court": "sg_kantonsgericht", "canton": "SG", "decision_count": 1082, "earliest": "1970-03-20", "latest": "2026-05-21", "languages": 1, "sparse": false}
{"court": "sh_obergericht", "canton": "SH", "decision_count": 718, "earliest": "2000-02-24", "latest": "2025-12-16", "languages": 1, "sparse": false}
{"court": "sh_gerichte", "canton": "SH", "decision_count": 716, "earliest": "2000-02-24", "latest": "2026-09-01", "languages": 1, "sparse": false}
{"court": "sg_publikationen", "canton": "SG", "decision_count": 630, "earliest": "1996-04-01", "latest": "2024-04-29", "languages": 1, "sparse": false}
{"court": "ai_gerichte", "canton": "AI", "decision_count": 182, "earliest": "1995-01-01", "latest": "2026-08-17", "languages": 1, "sparse": false}
{"court": "sg_handelsgericht", "canton": "SG", "decision_count": 49, "earliest": "1992-11-06", "latest": "2024-07-02", "languages": 1, "sparse": false}
{"court": "tg_anwaltskommission", "canton": "TG", "decision_count": 5, "earliest": null, "latest": null, "languages": 1, "sparse": true}
{"court": "sav_kantone", "canton": "SG", "decision_count": 1, "earliest": null, "latest": null, "languages": 1, "sparse": true}
```

## Step 16: Bash: Grep earlier reports for my cantons and i-web
```
SP=<scratchpad-overnight>; grep -n -i -E "schaffhausen|st\.? ?gallen|thurgau|appenzell|\bSG\b|\bTG\b|\bAR\b|\bAI\b|\bSH\b|i-web|iweb" $SP/reports/*.md $SP/verification_results_2026-09-23.md $SP/source_registry_2026-09-23.md 2>/dev/null | cut -c1-300 | head -60
```
Result:
```
<scratchpad-overnight>/reports/g2-districts.md:2:Run: 116 tool calls, ~202k tokens, ~34 min. Evidence: /tmp/sg-verify-g2-districts/. The harness blocked the
<scratchpad-overnight>/reports/g2-districts.md:21:| D4b March | Partly | JS (i-web CMS) | unresolved | low |
<scratchpad-overnight>/reports/g2-districts.md:38:- **The AI got both regional-planning domains wrong** (zpp.ch, oberaargau.ch). Regional plans are low value for resident questions.
<scratchpad-overnight>/reports/g3-associations.md:2:Run: 138 tool calls, ~238k tokens, ~43 min. Evidence: /tmp/sg-verify-g3-associations/. The harness blocked the backup,
<scratchpad-overnight>/reports/g3-associations.md:22:| D10 Schule Zollikon / D11 Schule Dietikon | Yes today (pdf) + new for lists | i-CMS `data-entities` + PDF text | i-web/i-CMS table | med. **Single-commune sc
<scratchpad-overnight>/reports/g3-associations.md:42:- **govis/backslash CMS:** 264 commune homepages contain `public/upload/assets` (AG 69, ZH 46, TG 44…). G1 counted
<scratchpad-overnight>/reports/g3-associations.md:44:- **i-CMS/i-web:** G3 counts the same 496 signature as G1.
<scratchpad-overnight>/reports/g3-associations.md:73:2. **i-CMS/i-web publication table** (same as G1 #2).
<scratchpad-overnight>/reports/g1-commune-law.md:2:Run: 108 tool calls, ~185k tokens, ~40 min. Evidence: /tmp/sg-verify-g1-commune-law/ (scan.json, iweb_all.json,
<scratchpad-overnight>/reports/g1-commune-law.md:8:- st.gallen.tlex.ch `/api/de/texts_of_law/412.9/show_as_json`: "Hundereglement", enactment 2020-11-01
<claude-tmp>/020cdda0-8dd0-4108-896
```

## Step 17: Bash: Read g1 commune-law report and size of CONTEXT.md
```
SP=<scratchpad-overnight>; sed -n 1,80p $SP/reports/g1-commune-law.md; wc -l <repo>/CONTEXT.md
```
Result:
```
# G1 report: commune bylaws and shared platforms (Opus 5.5 agent, 2026-09-23)
Run: 108 tool calls, ~185k tokens, ~40 min. Evidence: /tmp/sg-verify-g1-commune-law/ (scan.json, iweb_all.json,
tlex_hosts.txt, tlex_counts.txt). The harness blocked the agent's backup file, so this is the main session's transcription.
Method: fetched the homepages of all 2,103 communes in commune_sites.csv that list a website (2,060 returned 200) and detected CMS/vendor signatures.

**Spot-checked by the main session (live curl or the agent's data files, 2026-09-23). All matched:**
- baar.tlex.ch lightweight_index: 153 texts, 48 structured
- st.gallen.tlex.ch `/api/de/texts_of_law/412.9/show_as_json`: "Hundereglement", enactment 2020-11-01
- tlex_hosts.txt: 50 hosts
- wetzikon.ch/de/verwaltung/rechtssammlung/: 200, **191 unique Rechtssammlung PDFs**
- iweb_all.json: 496 i-web communes; 355 publikation + 83 rechtssammlung = **438**; rows 11,513 + 6,905 = **18,418**
Not re-checked: FR per-commune counts, terrara 1,484, Weblication 113, BL Plone 12/682, Romandie counts, Köniz 91.

**Conflict with G4:** G1 says LexFind `entities/{id}/systematics` returns nodes with empty `tols`. G4 says the texts
are filled in when you pass `tols_for_systematics[]=<node ids>` (batches of ≤100). **Resolved by the main session (curl, entity 28): without the param, 0 tols; with `tols_for_systematics[]` over 55 node ids, 317 tols. G4 is right, and G1 omitted the parameter.**

## Summary
| id | can we get it | format | fetcher | value |
|---|---|---|---|---|
| **tlex.ch (Sitrox LexWork for communes)** | Yes, new fetcher | JSON, article tree | LexWork commune | **high**: ≥49 communes, 4,002 texts, ~846k inhabitants |
| **i-web regulations module** | Yes, new fetcher | inline `data-entities` JSON → `/_doc/<id>` PDF | i-web regulations | **high**: 438 communes, 18,418 rows |
| G1-a Fribourg | Yes, new fetcher | HTML index + PDF text | PDF-index discoverer (+ i-web) | high: ~100/119 FR |
| Wetzikon (191 PDFs), Köniz (91 PDFs) | Yes, new fetcher | HTML + PDF text | PDF-index discoverer | med |
| Talus / Weblication | Yes, new fetcher | AJAX HTML list (wList.php) + PDF | Weblication list | med: ~113 communes, mostly BE |
| Webcloud7 → Kanton BL Plone | Yes, new fetcher | Plone REST JSON + PDF | Plone REST | low-med: 12 BL communes |
| Romandie | Yes, new fetcher | HTML + PDF | PDF-index discoverer + i-web | med-high: 401/542 homepages link to règlements |
| D1 LexFind | Communal: **No** (28 entities: CH + Intl
```

## Step 18: Bash: Read CONTEXT.md, create scratch dir, count communes per canton
```
cat <repo>/CONTEXT.md; mkdir -p /tmp/sg-verify-run3-c && ls -la /tmp/sg-verify-run3-c; grep -c . <repo>/docs/sources/commune_sites.csv; awk -F, 'NR>1{print $3}' <repo>/docs/sources/commune_sites.csv | sort | uniq -c | grep -E "CH-(SG|TG|AR|AI|SH)"
```
Result:
```
# Swiss Grounding

An MCP server that hands a language model cited evidence from Swiss public sources, scoped to the jurisdiction a question applies to. This glossary fixes the terms used when talking about the server, its sources, and its failure modes.

## Language

### Jurisdiction

**Extent**:
The jurisdiction node a document or chunk applies to: Switzerland, a canton, a municipality, a Kreis, or a Quartier.
_Avoid_: Scope, region, area

**Extent path**:
The chain of extents from Switzerland down to a resolved location, inclusive. A search returns only chunks whose extent lies on this path.
_Avoid_: Ancestor list, hierarchy

**Ambiguous location**:
An input naming more than one place that does not sit on a single path, such as Wil in Zurich and Wil in St. Gallen, or a Quartier and a commune sharing a name. The server asks which one is meant instead of guessing.
_Avoid_: Fallback, best guess

**Coverage signal**:
The part of a search result that states, per extent on the path, whether any indexed document exists there. A result stays `results` when only parent extents have data; the signal is what makes the gap visible.
_Avoid_: Fallback notice, warning

**Calendar evidence**:
A chunk that describes one dated event, such as a waste collection on a given day. Ranked by nearness to today among future events; past events stay visible but sink to the bottom.
_Avoid_: Schedule entry, event record

**Commune register**:
The Federal Statistical Office list of every Swiss commune with its BFS number and canton. The location tree is meant to hold all of them, whether or not any source covers them, so a place always resolves to its own node.
_Avoid_: Municipality list, gazetteer

**Narrowing**:
The ingestion step that moves a document from its source's default extent to a more specific one found in its text. Only a level marker, or a bare name in the title or a heading, may narrow. A name shared with an ancestor of the default extent never narrows on its own.
_Avoid_: Localisation, scoping

**Level marker**:
A word that fixes which level a place name means: Kanton, Stadt, Gemeinde, Kreis, Quartier, or a postal code. "Stadt Zürich" is marked; "Zürich" is bare.
_Avoid_: Qualifier, prefix

### Evaluation

**Probe**:
A hand-written question with a location, and the behaviour the raw tool response must show: status, resolved extent, required and forbidden sources or documents, coverage signal, event date rule. Graded deterministically without a model.
_Avoid_: Test ca
```

## Step 19: Write: /tmp/sg-verify-run3-c/probe.py
```
#!/usr/bin/env python3
"""Probe URLs: status, content type, size, final URL, <title>, #links, #words; optional regex samples.
usage: probe.py [-g REGEX] [-n N] [-s] URL [URL ...]
  -g REGEX  print up to N text snippets matching REGEX (tags stripped)
  -s        save body to /tmp/sg-verify-run3-c/pages/<slug>
"""
import sys, subprocess, re, os, html, hashlib, time

UA = 'Mozilla/5.0 swiss-grounding-check'
OUT = '/tmp/sg-verify-run3-c/pages'
os.makedirs(OUT, exist_ok=True)


def slug(u):
    s = re.sub(r'[^A-Za-z0-9]+', '_', u.split('://', 1)[-1])[:90]
    return s + '_' + hashlib.md5(u.encode()).hexdigest()[:6]


def fetch(url):
    fn = os.path.join(OUT, slug(url))
    r = subprocess.run(['curl', '-sL', '-g', '--compressed', '--max-time', '40', '-A', UA, '-o', fn,
                        '-w', '%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}', url],
                       capture_output=True, text=True)
    parts = (r.stdout or '000\t\t0\t' + url).split('\t')
    code, ct, size, final = (parts + ['', '', '', ''])[:4]
    body = b''
    if os.path.exists(fn):
        body = open(fn, 'rb').read()
    return code, ct, size, final, body, fn


def text_of(b):
    t = b.decode('utf-8', errors='ignore')
    t = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', t)
    t = re.sub(r'(?s)<[^>]+>', ' ', t)
    t = html.unescape(t)
    return re.sub(r'\s+', ' ', t).strip()


def main():
    args = sys.argv[1:]
    pat = None
    n = 3
    while args and args[0].startswith('-'):
        a = args.pop(0)
        if a == '-g':
            pat = re.compile(args.pop(0), re.I)
        elif a == '-n':
            n = int(args.pop(0))
    for u in args:
        code, ct, size, final, body, fn = fetch(u)
        s = body.decode('utf-8', errors='ignore')
        m = re.search(r'(?is)<title[^>]*>(.*?)</title>', s)
        title = html.unescape(re.sub(r'\s+', ' ', m.group(1))).strip()[:90] if m else ''
        links = len(re.findall(r'(?i)<a\s[^>]*href', s))
        txt = text_of(body) if 'html' in ct or s.lstrip().startswith('<') else ''
        words = len(txt.split())
        print(f'{code} | {ct[:28]} | {size}B | links {links} | words {words} | title: {title}')
        print(f'   url: {u}')
        if final != u:
            print(f'   final: {final}')
        print(f'   file: {fn}')
        if pat is not None and txt:
            k = 0
            for mm in pat.finditer(txt):
                a, b = max(0, mm.start() - 110), min(len(txt), mm.end() + 150)
                print('   >> ' + txt[a:b])
                k += 1
                if k >= n:
                    break
            if k == 0:
                print('   >> (no match)')
        sys.stdout.flush()


if __name__ == '__main__':
    main()

```
Result:
```
File created successfully at: /tmp/sg-verify-run3-c/probe.py (file state is current in your context — no need to Read it back)
```

## Step 20: Bash: List SG court pages from the sitemap
```
SM=<scratchpad-overnight>/stage0/sitemaps; echo "SG court-related (recht/gerichte):"; grep -c "sg.ch/recht/gerichte" $SM/www.sg.ch.txt; grep "sg.ch/recht/gerichte" $SM/www.sg.ch.txt | grep -v -E "/aktuelles/|/organisation---standorte/[^/]+/[^/]+/" | head -150
```
Result:
```
SG court-related (recht/gerichte):
199
https://www.sg.ch/recht/gerichte.html
https://www.sg.ch/recht/gerichte/aktuelles.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/anwaltskammer.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/anwaltskammer/aufgaben.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/anwaltskammer/personelles.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/anwaltsregister---register-der-notare.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/anwaltsregister---register-der-notare/anwaltsregister---register-der-notare-a-z.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/anwaltsregister---register-der-notare/eu--efta-anwaltsliste---register-der-notare.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/berufspflichten-des-anwalts.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/formulare.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/honorar.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/praktikum.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/pruefungen.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/pruefungen/pruefungskommission-fuer-rechtsagenten.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/pruefungen/pruefungskommission-fuer-rechtsanwaelte.html
https://www.sg.ch/recht/gerichte/anwalts----notarwesen/vertretung-vor-gericht.html
https://www.sg.ch/recht/gerichte/informationen---formulare.html
https://www.sg.ch/recht/gerichte/informationen---formulare/elektronischer-rechtsverkehr-im-zivil--und-strafprozess.html
https://www.sg.ch/recht/gerichte/informationen---formulare/elektronischer-rechtsverkehr-im-zivil--und-strafprozess/gerichte.html
https://www.sg.ch/recht/gerichte/informationen---formulare/elektronischer-rechtsverkehr-im-zivil--und-strafprozess/schlichtungsstellen.html
https://www.sg.ch/recht/gerichte/informationen---formulare/elektronischer-rechtsverkehr-im-zivil--und-strafprozess/vermittlungsaemter.html
https://www.sg.ch/recht/gerichte/informationen---formulare/existenzminimum.html
https://www.sg.ch/recht/gerichte/informationen---formulare/existenzminimum/grundbetrag.html
https://www.sg.ch/recht/gerichte/informationen---formulare/existenzminimum/zuschlaege.html
https://www.sg.ch/recht/gerichte/informationen---formulare/familienrecht.html
https://www.sg.ch/recht/gerichte/informationen---formulare/familienrecht/angeordnete-ber
```

## Step 21: Bash: Probe SG courts home, decisions, legal aid and info pages
```
cd /tmp/sg-verify-run3-c && python3 probe.py -g "Gericht|Kantonsgericht|Rechtsprechung" -n 2 https://www.sg.ch/recht/gerichte.html https://www.sg.ch/recht/gerichte/rechtsprechung.html; python3 probe.py -g "CHF|Fr\. ?[0-9]|Kosten|Gebühr|Kostenvorschuss" -n 4 https://www.sg.ch/recht/gerichte/informationen---formulare/unentgeltliche-rechtspflege.html https://www.sg.ch/recht/gerichte/informationen---formulare/merkblaetter.html https://www.sg.ch/recht/gerichte/informationen---formulare.html
```
Result:
```
200 | text/html | 19787B | links 131 | words 595 | title: Gerichte | sg.ch
   url: https://www.sg.ch/recht/gerichte.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_recht_gerichte_html_2484a7
   >> Gerichte | sg.ch Direkt zur Startseite Direkt zur Navigation Direkt zum Inhalt Direkt zur Suche Zur Suche Mobiles Menü öffnen logo for mobile-menu Menü Ebene
   >> Direkt zum Inhalt Direkt zur Suche Zur Suche Mobiles Menü öffnen logo for mobile-menu Menü Ebene zurück Recht Gerichte Anwalts- & Notarwesen Untermenü aufklappen Informationen & Formulare Untermenü aufklappen Verhandlungstermine Untermenü aufklappen Offenlegung Inter
200 | text/html | 19225B | links 116 | words 517 | title: Rechtsprechung | sg.ch
   url: https://www.sg.ch/recht/gerichte/rechtsprechung.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_recht_gerichte_rechtsprechung_html_851384
   >> Rechtsprechung | sg.ch Direkt zur Startseite Direkt zur Navigation Direkt zum Inhalt Direkt zur Suche Frage alles in deiner Sprache Suchen Suchbereich Ganzer Kanton
   >>  Navigation Direkt zum Inhalt Direkt zur Suche Frage alles in deiner Sprache Suchen Suchbereich Ganzer Kanton Gerichte Inhaltstyp Gerichte Organisation und Standorte Gerichte Rechtsprechung Gerichte Anwaltsregister und Register der Notare Gerichte Existenzminimum, No
200 | text/html | 19085B | links 127 | words 449 | title: Unentgeltliche Rechtspflege | sg.ch
   url: https://www.sg.ch/recht/gerichte/informationen---formulare/unentgeltliche-rechtspflege.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_recht_gerichte_informationen_formulare_unentgeltliche_rechtspflege_html_00248a
   >> (no match)
200 | text/html | 19389B | links 133 | words 485 | title: Merkblätter | sg.ch
   url: https://www.sg.ch/recht/gerichte/informationen---formulare/merkblaetter.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_recht_gerichte_informationen_formulare_merkblaetter_html_d9832a
   >> erstellt. Zum Lesen der PDF-Dateien ist der Acrobat-Reader erforderlich. Vorlesen Beschwerdeverfahren und die Kostenfolgen betreffend Kindes- und Erwachsenenschutz (112 kB, PDF, 25.03.2019) Merkblatt über das Opferhilfegesetz (25 kB, PDF, 25.03.2019) Merkblatt zu de
   >> chutz (112 kB, PDF, 25.03.2019) Merkblatt über das Opferhilfegesetz (25 kB, PDF, 25.03.2019) Merkblatt zu den Kosten und dem Verfahren vor Handelsgericht.pdf (87 kB, PDF, 05.01.2021) Rechtsmittelverfahren (Rekurs bzw. Beschwerde) und die Kostenfolgen betreffend Gebü
   >> fahren vor Handelsgericht.pd
```

## Step 22: Bash: Extract main-content links and text from SG court pages
```
cd /tmp/sg-verify-run3-c/pages && python3 - <<'EOF'
import re,html
for fn in ['www_sg_ch_recht_gerichte_rechtsprechung_html_851384','www_sg_ch_recht_gerichte_informationen_formulare_merkblaetter_html_d9832a','www_sg_ch_recht_gerichte_html_2484a7']:
    s=open(fn,encoding='utf-8',errors='ignore').read()
    i=s.find('<main'); j=s.find('</main>')
    print('#',fn,'main at',i,j)
    body=s[i:j] if i>=0 else s
    t=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',body)
    links=re.findall(r'(?is)<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t)
    for h,a in links[:60]:
        a=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(a))).strip()
        print('  ',h[:120],'|',a[:90])
    txt=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t))).strip()
    print('  TEXT:',txt[:900])
EOF
```
Result:
```
# www_sg_ch_recht_gerichte_rechtsprechung_html_851384 main at -1 -1
   https://www.sg.ch | Direkt zur Startseite
   #content-navigation | Direkt zur Navigation
   #content | Direkt zum Inhalt
   #aiInputField-overlay | Direkt zur Suche
   https://www.sg.ch | 
   /recht/gerichte/organisation---standorte.html | Gerichte Organisation und Standorte
   /recht/gerichte/rechtsprechung.html | Gerichte Rechtsprechung
   /recht/gerichte/anwalts----notarwesen/anwaltsregister---register-der-notare.html | Gerichte Anwaltsregister und Register der Notare
   /recht/gerichte/informationen---formulare/existenzminimum.html | Gerichte Existenzminimum, Notbedarf und Grundbetrag
   /recht/gerichte/informationen---formulare/elektronischer-rechtsverkehr-im-zivil--und-strafprozess.html | Gerichte Elektronischer Rechtsverkehr
   /recht/gerichte/anwalts----notarwesen/pruefungen.html | Gerichte Prüfungen (Rechts-anwälte, Notare und Rechtsagenten)
   #contact-row | 
   #site-menu | Mobiles Menü öffnen
   # | logo for mobile-menu
   /recht/gerichte/rechtsprechung.html | Rechtsprechung
   #site-menu | Menü aufklappen
   javascript:window.print() | Drucken
   # | Teilen
   #site-menu | Mobiles Menü schliessen
   # | logo for mobile-menu
   https://www.sg.ch | Alle Themen
   /ueber-den-kanton-st-gallen.html | Über den Kanton
   /politik-verwaltung.html | Politik & Verwaltung
   /bauen.html | Bauen
   /bildung-sport.html | Bildung & Sport
   /gesundheit-soziales.html | Gesundheit & Soziales
   /kultur.html | Kultur
   /recht.html | Recht
   /sicherheit.html | Sicherheit
   /steuern-finanzen.html | Steuern & Finanzen
   /umwelt-natur.html | Umwelt & Natur
   /verkehr.html | Verkehr
   /wirtschaft-arbeit.html | Wirtschaft & Arbeit
   /recht.html | Recht
   /recht/gerichte.html | Gerichte
   https://www.gesetzessammlung.sg.ch/ | Gesetze neues Fenster
   /recht/staatsanwaltschaft-jugendanwaltschaft.html | Staatsanwaltschaft
   /recht/handelsregister-notariate.html | Handelsregister & Notariate
   /recht/buergerrecht-zivilstand.html | Bürgerrecht & Zivilstand
   /recht/unentgeltliche-rechtspflege.html | Unentgeltliche Rechtspflege
   /recht/opferhilfe.html | Opferhilfe
   /recht/beglaubigungen.html | Apostillen und Legalisationen
   /recht/planungs-bau-umweltrecht.html | Planungs-, Bau- und Umweltrecht
   /recht/beschaffungswesen.html | Beschaffungswesen
   /recht/geldspiele.html | Geldspiele
   /recht/gerichte.html | Gerichte
   /recht/gerichte/anwalts----notarwesen.html | Anwalts- & Notarwes
```

## Step 23: Bash: Find the main-content marker in sg.ch HTML
```
cd /tmp/sg-verify-run3-c/pages && grep -o -E 'id="[^"]*(main|content|inhalt)[^"]*"' www_sg_ch_recht_gerichte_informationen_formulare_merkblaetter_html_d9832a | sort | uniq -c; grep -o -E 'class="[^"]*(main|content)[^"]*"' www_sg_ch_recht_gerichte_informationen_formulare_merkblaetter_html_d9832a | sort | uniq -c | head
```
Result:
```
   1 id="content"
   1 id="content-navigation"
   1 id="main"
   1 id="maincontent"
   1 class="dropdown desktop-visible main-nav-top quickmenutoggler"
   1 class="dropdown main-nav-top kontakt-link"
   1 class="dropdown main-nav-top searchtoggler"
   6 class="ktsg-tile main-tile width-25 txt-tile desktop-square-tile tilestyle-color-green "
   2 class="nav-list-block nav-level-current ajax-content"
   1 class="navbar phantom-desktop-menu desktop-hidden main-navigation"
   1 class="navbar withincontentandmobile main-navigation"
   1 class="navbar-content pull-right"
   1 class="sgch contentpage"
   6 class="tile-content"
```

> Let me add a content-marker option to the probe helper so samples come from the page body rather than navigation.

## Step 24: Bash: Add marker option; probe SG legal aid pages for fee amounts
```
cd /tmp/sg-verify-run3-c && python3 - <<'EOF'
p='/tmp/sg-verify-run3-c/probe.py'
s=open(p).read()
s=s.replace("""        elif a == '-n':
            n = int(args.pop(0))""","""        elif a == '-n':
            n = int(args.pop(0))
        elif a == '-m':
            marker = args.pop(0)""")
s=s.replace("""    pat = None
    n = 3""","""    pat = None
    n = 3
    marker = None""")
s=s.replace("""        txt = text_of(body) if 'html' in ct or s.lstrip().startswith('<') else ''
        words = len(txt.split())""","""        txt = text_of(body) if 'html' in ct or s.lstrip().startswith('<') else ''
        words = len(txt.split())
        if marker:
            k2 = s.find(marker)
            if k2 >= 0:
                txt = text_of(s[k2:].encode())""")
open(p,'w').write(s)
EOF
python3 probe.py -m 'id="maincontent"' -g "CHF|Fr\. ?[0-9]|Franken|Kosten|Gebühr|Vorschuss" -n 5 https://www.sg.ch/recht/gerichte/informationen---formulare/unentgeltliche-rechtspflege.html https://www.sg.ch/recht/unentgeltliche-rechtspflege.html https://www.sg.ch/recht/gerichte/informationen---formulare/unentgeltliche-rechtsauskuenfte.html
```
Result:
```
200 | text/html | 19085B | links 127 | words 449 | title: Unentgeltliche Rechtspflege | sg.ch
   url: https://www.sg.ch/recht/gerichte/informationen---formulare/unentgeltliche-rechtspflege.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_recht_gerichte_informationen_formulare_unentgeltliche_rechtspflege_html_00248a
   >> (no match)
200 | text/html | 18506B | links 104 | words 423 | title: Unentgeltliche Rechtspflege | sg.ch
   url: https://www.sg.ch/recht/unentgeltliche-rechtspflege.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_recht_unentgeltliche_rechtspflege_html_0eaeb7
   >> (no match)
200 | text/html | 18992B | links 125 | words 419 | title: Unentgeltliche Rechtsauskünfte | sg.ch
   url: https://www.sg.ch/recht/gerichte/informationen---formulare/unentgeltliche-rechtsauskuenfte.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_recht_gerichte_informationen_formulare_unentgeltliche_rechtsauskuenfte_html_d20bed
   >> band; Gewerkschaften, Arbeitgeberorganisationen; Verkehrsverbände). Diese sind aber häufig nur für Mitglieder kostenlos. Noch offene Fragen? Kantonsgericht Kantonsgericht Klosterhof 1 9001 St.Gallen +41 58 229 32 41 Handelsgericht Handelsgericht Klosterhof 1 9001 St
```

## Step 25: Bash: Read SG legal-aid page text; grep sitemap for court cost pages
```
cd /tmp/sg-verify-run3-c/pages && python3 - <<'EOF'
import re,html
def main_text(fn, marker='id="maincontent"', n=1500):
    s=open(fn,encoding='utf-8',errors='ignore').read()
    k=s.find(marker); s=s[k:] if k>=0 else s
    s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s)
    t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
    return t[:n]
for fn in ['www_sg_ch_recht_gerichte_informationen_formulare_unentgeltliche_rechtspflege_html_00248a','www_sg_ch_recht_gerichte_html_2484a7']:
    print('#',fn); print(main_text(fn))
EOF
SM=<scratchpad-overnight>/stage0/sitemaps; grep -i -E "kosten|gebuehr|tarif" $SM/www.sg.ch.txt | grep -i -E "recht|gericht|schlicht|vermitt" | head
```
Result:
```
# www_sg_ch_recht_gerichte_informationen_formulare_unentgeltliche_rechtspflege_html_00248a
id="maincontent" data-swiftype-name="body" data-swiftype-type="text"> Eine Prozesspartei darf nicht wegen ihrer Bedürftigkeit vom Recht ausgeschlossen werden, einen Anspruch gerichtlich beurteilen zu lassen. Vorlesen Dafür gibt es die Möglichkeit der unentgeltlichen Rechtspflege. Sie wird im Zivilprozess und im Verwaltungsprozess je nach Bedarf in unterschiedlichem Umfang gewährt. Das Gesuch ist beim angerufenen Gericht einzureichen. Dazu besteht ein detailliertes Formular " Gesuch um unentgeltliche Rechtspflege ". Dieses ist vollständig und wahrheitsgetreu auszufüllen, und es sind sämtliche im Formular erwähnten Unterlagen einzureichen. Unvollständige Angaben oder fehlende Belege können zur Abweisung des Gesuchs führen. Die wesentlichen Grundsätze sind in den Richtlinien des Kantonsgerichts zur unentgeltlichen Rechtspflege und Honorarbemessung zusammengefasst. Noch offene Fragen? Kantonsgericht Kantonsgericht Klosterhof 1 9001 St.Gallen +41 58 229 32 41 Handelsgericht Handelsgericht Klosterhof 1 9001 St.Gallen +41 58 229 32 45 Anklagekammer Anklagekammer Klosterhof 1 9001 St.Gallen +41 58 229 22 95 Versicherungsgericht Versicherungsgericht Wassergasse 44 9001 St.Gallen +41 58 229 25 25 Verwaltungsgericht Verwaltungsgericht Webergasse 8 9001 St.Gallen +41 58 229 39 02 Weitere Informationen Für Sie da Zuständig für den Inhalt dieser Seite: Gerichte St.Gallen Letzte Aktualisierung: 24.03.2021 Bleiben Sie in Kontakt mit uns: Medienstelle Unsere Themen Anwalts- & Notarwesen Infor
# www_sg_ch_recht_gerichte_html_2484a7
Gerichte | sg.ch Direkt zur Startseite Direkt zur Navigation Direkt zum Inhalt Direkt zur Suche Zur Suche Mobiles Menü öffnen logo for mobile-menu Menü Ebene zurück Recht Gerichte Anwalts- & Notarwesen Untermenü aufklappen Informationen & Formulare Untermenü aufklappen Verhandlungstermine Untermenü aufklappen Offenlegung Interessenbindung Aktuelles Untermenü aufklappen Menü aufklappen Gerichte Frage alles in deiner Sprache Suchen Suchbereich Gerichte Ganzer Kanton Mobiles Menü schliessen logo for mobile-menu Alle Themen Untermenü aufklappen Über den Kanton Politik & Verwaltung Bauen Bildung & Sport Gesundheit & Soziales Kultur Recht Sicherheit Steuern & Finanzen Umwelt & Natur Verkehr Wirtschaft & Arbeit Recht Untermenü aufklappen Gerichte Gesetze neues Fenster Staatsanwaltschaft Handelsregister & Notariate Bürgerrecht & Zivilstand Unentgeltliche Rechtspfle
```

## Step 26: Bash: Grep SG sitemap for tax guide, gazette, inheritance, holidays, dogs, communes
```
SM=<scratchpad-overnight>/stage0/sitemaps; F=$SM/www.sg.ch.txt; echo "steuerbuch: $(grep -c '/steuerbuch' $F)"; grep '/steuerbuch' $F | head -8; echo "amtsblatt:"; grep -i amtsblatt $F | head; echo "erb:"; grep -i -E "erbschaft|erbrecht|nachlass|testament" $F | head -5; echo "ferien:"; grep -i ferien $F | head -5; echo "hunde:"; grep -i hund $F | head; echo "gemeinden list:"; grep -i -E "gemeinden/(ueber|verzeichnis|liste|alle)|gemeindeverzeichnis|gemeindeportraet" $F | head; echo "betreibung:"; grep -i -E "betreibung|konkurs" $F | head -5
```
Result:
```
steuerbuch: 265
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/003_1.pdf.ocFile/003_1.pdf
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/006_1.pdf.ocFile/006_1.pdf
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/006_2.pdf.ocFile/006_2.pdf
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/012bis_1.pdf.ocFile/012bis_1.pdf
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/A%2520Organigramm%2520KStA.pdf.ocFile/A%2520Organigramm%2520KStA.pdf
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/B%2520Mitarbeiter%2520des%2520KStA.pdf.ocFile/B%2520Mitarbeiter%2520des%2520KStA.pdf
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/C%2520Karten%2520NP%2520u%2520%2520JP.pdf.ocFile/C%2520Karten%2520NP%2520u%2520%2520JP.pdf
https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/D%20Hotline-%C3%9Cbersicht.pdf.html
amtsblatt:
https://www.sg.ch/ueber-den-kanton-st-gallen/amtsblatt.html
erb:
https://www.sg.ch/recht/handelsregister-notariate/amtsnotariate/beurkundungen/testament.html
https://www.sg.ch/recht/handelsregister-notariate/amtsnotariate/erben/erbschaftsausschlagung.html
https://www.sg.ch/recht/handelsregister-notariate/amtsnotariate/erben/testamentseroeffnung.html
https://www.sg.ch/recht/handelsregister-notariate/amtsnotariate/nachlassplanung.html
https://www.sg.ch/steuern-finanzen/steuern/steuerarten/erbschafts-schenkungssteuer.html
ferien:
https://www.sg.ch/bildung-sport/mittelschule/information-fuer-lehrpersonen-und-kommissionen/handbuch-mittelschulen/5-3-ferien.html
https://www.sg.ch/bildung-sport/mittelschule/kantonsschulen/ferienplan.html
https://www.sg.ch/bildung-sport/volksschule/aus-dem-amt/ferienplan.html
https://www.sg.ch/politik-verwaltung/gemeinden/grundstueckerwerb-durch-personen-im-ausland/ferienwohnung--haus.html
https://www.sg.ch/ueber-den-kanton-st-gallen/arbeitgeber-kanton-stgallen/mein-neues-arbeitsverhaeltnis/personalhandbuch/4-arbeitszeit--ruhetage--ferien-und-urlaub.html
hunde:
https://www.sg.ch/umwelt-natur/landwirtschaft/lzsg/Beratung/tierhaltung/Herdenschutz/herdenschutzhunde-.html
https://www.sg.ch/umwelt-natur/veterinaerwesen/tiere-halten/hunde.html
https://www.sg.ch/verkehr/oeffentlicher-verkehr/planung-oev-angebote/abgeschlossene-planungen/busplanung-st-gallen-stein-hu
```

## Step 27: Bash: Probe SG dogs, school holidays, tax book pages
```
cd /tmp/sg-verify-run3-c && M='id="maincontent"'; python3 probe.py -m "$M" -g "Leine|Hundehalte|Hundesteuer|muss|Hundegesetz" -n 3 https://www.sg.ch/umwelt-natur/veterinaerwesen/tiere-halten/hunde.html; python3 probe.py -m "$M" -g "Ferien|[0-9]{1,2}\.[0-9]{1,2}\.20[0-9]{2}|Schulträger|Gemeinde" -n 4 https://www.sg.ch/bildung-sport/volksschule/aus-dem-amt/ferienplan.html; python3 probe.py -m "$M" -g "Steuerbuch|Artikel|Praxis|Änderung" -n 3 https://www.sg.ch/steuern-finanzen/steuern/steuerbuch.html https://www.sg.ch/steuern-finanzen/steuern/steuerbuch/inhaltsverzeichnis.html
```
Result:
```
200 | text/html | 22857B | links 127 | words 1009 | title: Hunde | sg.ch
   url: https://www.sg.ch/umwelt-natur/veterinaerwesen/tiere-halten/hunde.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_umwelt_natur_veterinaerwesen_tiere_halten_hunde_html_c911ef
   >> id="maincontent" data-swiftype-name="body" data-swiftype-type="text"> Seit dem 1. Januar 2020 ist das neue Hundegesetz des Kantons St.Gallen in Kraft. Damit übernimmt der Kanton von den Gemeinden diverse Aufgaben im Vollzug, insbesondere bei auffälligen und aggressive
   >> e kommunale Aufgaben zuständig, namentlich für die Durchführung der Hundekontrolle sowie für die Erhebung der Hundesteuer. Vorlesen Vorfälle mit Hunden Sie können uns Hunde melden, die einen Menschen oder einen anderen Hund gebissen haben oder die Ihnen sonst übermässig 
   >> orbtragepflicht. Dennoch können es bestimmte Situationen erfordern, dass ein Hund mit Maulkorb geführt werden muss. Sei dies aufgrund eines Aufenthalts in einem Kanton / Land mit Maulkorbtragepflicht für Hunde, bei einem Tierarztbesuch, oder zur Gewährleistung der
200 | text/html | 20205B | links 125 | words 532 | title: Ferienplan | sg.ch
   url: https://www.sg.ch/bildung-sport/volksschule/aus-dem-amt/ferienplan.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_bildung_sport_volksschule_aus_dem_amt_ferienplan_html_f488d6
   >> id="maincontent" data-swiftype-name="body" data-swiftype-type="text"> Die Schulferien der öffentlichen Volksschulen und der kantonalen Mittelschulen werden durch den Bildungsrat festgelegt. Vorlesen Ferienplan Schuljahre 2026/27 bis 20
   >>  öffentlichen Volksschulen und der kantonalen Mittelschulen werden durch den Bildungsrat festgelegt. Vorlesen Ferienplan Schuljahre 2026/27 bis 2029/30 Schuljahr Schulbeginn Herbstferien (KW 40 bis 42) Weihnachtsferien 1 Frühlingsferien (KW 15 und 16) Sommerferien (
   >> ch den Bildungsrat festgelegt. Vorlesen Ferienplan Schuljahre 2026/27 bis 2029/30 Schuljahr Schulbeginn Herbstferien (KW 40 bis 42) Weihnachtsferien 1 Frühlingsferien (KW 15 und 16) Sommerferien (KW 28 bis 32) 2026/27 Mo, 10.08.2026 So, 27.09.26 bis So, 18.10.26 So,
   >> orlesen Ferienplan Schuljahre 2026/27 bis 2029/30 Schuljahr Schulbeginn Herbstferien (KW 40 bis 42) Weihnachtsferien 1 Frühlingsferien (KW 15 und 16) Sommerferien (KW 28 bis 32) 2026/27 Mo, 10.08.2026 So, 27.09.26 bis So, 18.10.26 So, 20.12.26 bis So, 03.01.27 So, 1
200 | text/html | 21744B | links 148 | words 679 | title: Steuerbuch und rechtliche Grundla
```

## Step 28: Bash: Count SG Steuerbuch entries and PDF links
```
cd /tmp/sg-verify-run3-c/pages && python3 - <<'EOF'
import re,html
s=open('www_sg_ch_steuern_finanzen_steuern_steuerbuch_inhaltsverzeichnis_html_d24bfa',encoding='utf-8',errors='ignore').read()
hrefs=re.findall(r'href="([^"]+)"',s)
pdf=[h for h in hrefs if '.pdf' in h.lower()]
stb=[h for h in pdf if '/steuerbuch/' in h]
print('hrefs',len(hrefs),'pdf',len(pdf),'steuerbuch pdf',len(stb),'unique',len(set(stb)))
print(stb[:3])
t=html.unescape(re.sub(r'<[^>]+>',' ',s))
e=re.findall(r'StB (\d+[a-z]*) Nr\. ?(\d+)',t)
print('StB entries',len(e),'unique',len(set(e)))
EOF
```
Result:
```
hrefs 650 pdf 498 steuerbuch pdf 498 unique 250
['/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/Inhaltsverzeichnis.pdf.ocFile/Inhaltsverzeichnis.pdf', '/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/Stichwortverzeichnis.pdf.ocFile/Stichwortverzeichnis.pdf', '/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/A%20Organigramm%20KStA.pdf.ocFile/A%20Organigramm%20KStA.pdf']
StB entries 243 unique 243
```

## Step 29: Bash: Download one SG Steuerbuch PDF and test text layer
```
cd /tmp/sg-verify-run3-c && python3 - <<'EOF'
import re
s=open('pages/www_sg_ch_steuern_finanzen_steuern_steuerbuch_inhaltsverzeichnis_html_d24bfa',encoding='utf-8',errors='ignore').read()
hrefs=[h for h in re.findall(r'href="([^"]+)"',s) if '/steuerbuch/' in h and '.pdf' in h.lower()]
# pick a StB entry pdf
cand=[h for h in hrefs if re.search(r'/\d{3}[a-z]*_\d+\.pdf',h)]
print(len(cand), cand[:2])
open('sg_stb_sample.txt','w').write('https://www.sg.ch'+cand[5]+'\n')
EOF
U=$(cat /tmp/sg-verify-run3-c/sg_stb_sample.txt); curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o /tmp/sg-verify-run3-c/sg_stb.pdf -w "%{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$U"; python3 -c "
from pypdf import PdfReader; r=PdfReader('/tmp/sg-verify-run3-c/sg_stb.pdf'); print('pages',len(r.pages)); print(r.pages[0].extract_text()[:400])"
```
Result:
```
486 ['/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/003_1.pdf.ocFile/003_1.pdf', '/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/003_1.pdf.ocFile/003_1.pdf']
200 application/pdf 18777B https://www.sg.ch/content/dam/sgch/steuern-finanzen/steuern/steuerbuch/art-1-12-stg/006_2.pdf
pages 1
 StB 6 Nr. 2 
 
 
                                                                                
 
01.01.2022 - 1 - ersetzt 01.07.2017 
 
Steuerfüsse der Gemeinden 
 
 
 
Die laufend aktualisierten Steuerfüsse der st. gallischen Gemeinden ab dem Jahr 2001 finden 
Sie auf unserer Internetseite https://www.steuern.sg.ch/ (<Steuern berechnen > < Steuerfuss-
Übersicht aller SG -Gemeinden>) bzw. unte
```

## Step 30: Bash: Probe SG road office, communes, gazette, chancellery pages
```
cd /tmp/sg-verify-run3-c && M='id="maincontent"'; python3 probe.py -m "$M" -g "CHF|Fr\. ?[0-9]|Franken|Gebühr" -n 3 https://www.sg.ch/verkehr/strassenverkehr.html https://www.sg.ch/verkehr/strassenverkehr/rechnung_gebuehren.html; python3 probe.py -m "$M" -g "Gemeinde[n]? |Altstätten|Wil|Rapperswil|75|Gemeinden" -n 3 https://www.sg.ch/politik-verwaltung/gemeinden.html https://www.sg.ch/politik-verwaltung/gemeinden/ueber-die-gemeinden.html; python3 probe.py -m "$M" -g "Amtsblatt|amtsblatt|publikationen" -n 3 https://www.sg.ch/ueber-den-kanton-st-gallen/amtsblatt.html https://www.sg.ch/politik-verwaltung/departemente-und-staatskanzlei/staatskanzlei.html
```
Result:
```
200 | text/html | 20592B | links 135 | words 519 | title: Strassenverkehr | sg.ch
   url: https://www.sg.ch/verkehr/strassenverkehr.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_verkehr_strassenverkehr_html_712275
   >> schilder Untermenü aufklappen Prüfstellen Prüfungstermine und Informationen Untermenü aufklappen Rechnung und Gebühren Untermenü aufklappen Sonderbewilligungen Untermenü aufklappen Theorieprüfungen / Lernfahrausweise Untermenü aufklappen Menü aufklappen Strassenverk
   >> schilder Untermenü aufklappen Prüfstellen Prüfungstermine und Informationen Untermenü aufklappen Rechnung und Gebühren Untermenü aufklappen Sonderbewilligungen Untermenü aufklappen Theorieprüfungen / Lernfahrausweise Untermenü aufklappen Inhaltstyp Haben Sie Fragen?
   >> hrerprüfungen und Kontrollfahrten Kontrollschilder Prüfstellen Prüfungstermine und Informationen Rechnung und Gebühren Sonderbewilligungen Theorieprüfungen / Lernfahrausweise Bestens informiert Den Kanton etwas besser kennen lernen? Erhalten Sie täglich die Neuigkei
200 | text/html | 21310B | links 131 | words 658 | title: Rechnung und Gebühren | sg.ch
   url: https://www.sg.ch/verkehr/strassenverkehr/rechnung_gebuehren.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_verkehr_strassenverkehr_rechnung_gebuehren_html_8e50ee
   >> enznummern! Eine eRechnung gelangt direkt in Ihr eBanking-Postfach. Anmeldung eRechnung (eBill) neues Fenster Gebühren Gebühren bezahlen Sie für die Dienstleistungen des Strassenverkehrs- und Schifffahrtsamtes, wie zum Beispiel für einen Schilder- oder Fahrzeugwechs
   >> n! Eine eRechnung gelangt direkt in Ihr eBanking-Postfach. Anmeldung eRechnung (eBill) neues Fenster Gebühren Gebühren bezahlen Sie für die Dienstleistungen des Strassenverkehrs- und Schifffahrtsamtes, wie zum Beispiel für einen Schilder- oder Fahrzeugwechsel. Geset
   >>  Schifffahrtsamtes, wie zum Beispiel für einen Schilder- oder Fahrzeugwechsel. Gesetzliche Grundlage: Verkehrsgebührentarif sGS 718.1 neues Fenster Strassenverkehrsabgaben Die Informationen zu den Strassenverkehrsabgaben finden Sie hier neues Fenster . Gesetzliche G
200 | text/html | 19134B | links 114 | words 425 | title: Gemeinden | sg.ch
   url: https://www.sg.ch/politik-verwaltung/gemeinden.html
   file: /tmp/sg-verify-run3-c/pages/www_sg_ch_politik_verwaltung_gemeinden_html_b05dee
   >> Gemeinden | sg.ch Direkt zur Startseite Direkt zur Navigation Direkt zum Inhalt Direkt zur Suche Zur Suche Mobiles Menü öffnen logo for mobile-menu 
```

## Step 31: Bash: Extract communes portal, gazette and publication links for SG
```
cd /tmp/sg-verify-run3-c/pages && grep -o -E 'href="[^"]*(gemeinden\.sg\.ch|amtsblatt|publikationen\.sg\.ch)[^"]*"' www_sg_ch_politik_verwaltung_gemeinden_html_b05dee www_sg_ch_politik_verwaltung_departemente_und_staatskanzlei_staatskanzlei_html_670336 www_sg_ch_ueber_den_kanton_st_gallen_amtsblatt_html_00c774 www_sg_ch_politik_verwaltung_gemeinden_ueber_die_gemeinden_html_d6b8b7 | sort | uniq | cut -c1-250; python3 - <<'EOF'
import re,html
s=open('/tmp/sg-verify-run3-c/pages/www_sg_ch_politik_verwaltung_gemeinden_ueber_die_gemeinden_html_d6b8b7',encoding='utf-8',errors='ignore').read()
k=s.find('id="maincontent"'); s=s[k:k+20000]
for h,a in re.findall(r'(?is)<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',s)[:30]:
    print(h[:120],'|',re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',html.unescape(a))).strip()[:60])
EOF
```
Result:
```
www_sg_ch_politik_verwaltung_departemente_und_staatskanzlei_staatskanzlei_html_670336:href="http://amtsblatt.sg.ch"
www_sg_ch_politik_verwaltung_departemente_und_staatskanzlei_staatskanzlei_html_670336:href="http://publikationen.sg.ch"
www_sg_ch_ueber_den_kanton_st_gallen_amtsblatt_html_00c774:href="//app-eu.readspeaker.com/cgi-bin/rsent?customerid=11974&amp;lang=de_de&amp;readid=maincontent&amp;url=https%3A%2F%2Fwww.sg.ch%2Fueber-den-kanton-st-gallen%2Famtsblatt.html"
www_sg_ch_ueber_den_kanton_st_gallen_amtsblatt_html_00c774:href="/ueber-den-kanton-st-gallen/amtsblatt.html"
www_sg_ch_ueber_den_kanton_st_gallen_amtsblatt_html_00c774:href="http://www.publikationen.sg.ch"
www_sg_ch_ueber_den_kanton_st_gallen_amtsblatt_html_00c774:href="https://publikationen.sg.ch"
www_sg_ch_ueber_den_kanton_st_gallen_amtsblatt_html_00c774:href="https://publikationen.sg.ch/weitere-publikationen/?filter[category][]=2"
www_sg_ch_ueber_den_kanton_st_gallen_amtsblatt_html_00c774:href="https://www.sg.ch/ueber-den-kanton-st-gallen/amtsblatt.html"
//app-eu.readspeaker.com/cgi-bin/rsent?customerid=11974&amp;lang=de_de&amp;readid=maincontent&amp;url=https%3A%2F%2Fwww. | Vorlesen
/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/politische%20Gemeinden.xlsx | politische Gemeinden
/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/Schulgemeinden.xlsx | Schulgemeinden
/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/Ortsgemeinden.xlsx | Ortsgemeinden
/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/%C3%B6rtliche%20Korporationen.xlsx | örtliche Korporationen
/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/ortsb%C3%BCrgerliche%20Korporationen.xlsx | ortsbürgerliche Korporationen
/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/Zweckverb%C3%A4nde.xlsx | Zweckverbände
/politik-verwaltung/gemeinden/gemeindeaufsicht.html | Team der Gemeindeaufsicht
tel:+41582292241 | +41 58 229 22 41
mailto:[redacted] | [name]@sg.ch
# | Amt für Gemeinden und Bürgerrecht
https://www.facebook.com/KantonSG | 
https://www.youtube.com/channel/UCyMR58kgg4FtEVjvJSInJSQ | 
https://www.instagram.com/kantonsg/ | 
https://www.linkedin.com/company/kanton-st-gallen | 
https://bit.ly/4aERKhD | 
/content/sgch/ueber-den-kanton-st-gallen/messenger-kanaele-des-kantons-st-gallen | 
/content/sgch/ueb
```

## Step 32: Bash: Download SG political communes XLSX and inspect rows and links
```
cd /tmp/sg-verify-run3-c && curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o sg_polgem.xlsx -w "%{http_code} %{content_type} %{size_download}B %{url_effective}\n" "https://www.sg.ch/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/politische%20Gemeinden.xlsx"; python3 - <<'EOF'
import zipfile,re
z=zipfile.ZipFile('/tmp/sg-verify-run3-c/sg_polgem.xlsx')
names=z.namelist(); print([n for n in names if 'sheet' in n or 'shared' in n][:8])
ss=z.read('xl/sharedStrings.xml').decode('utf-8') if 'xl/sharedStrings.xml' in names else ''
strs=re.findall(r'<t[^>]*>([^<]*)</t>',ss)
print('shared strings',len(strs)); print(strs[:40])
sh=z.read('xl/worksheets/sheet1.xml').decode('utf-8')
rows=re.findall(r'<row ',sh); print('rows',len(rows))
print('hyperlinks', len(re.findall(r'<hyperlink ',sh)))
urls=[s for s in strs if 'http' in s or 'www.' in s]; print('url-like strings',len(urls), urls[:5])
EOF
```
Result:
```
200 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet 28418B https://www.sg.ch/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/politische%20Gemeinden.xlsx
['xl/worksheets/sheet1.xml', 'xl/sharedStrings.xml', 'xl/worksheets/_rels/sheet1.xml.rels']
shared strings 458
['politische Gemeinden im Kanton St.Gallen', 'Stand:', 'Nr.', 'Gemeinde', 'Präsidium-Anrede', 'Präsidium-Vorname', 'Präsidium-Name', 'Präsidium-E-Mail', 'Adresse', 'PLZ', 'Ort', 'E-Mail allgemein', 'St.Gallen', 'Frau', 'Maria', 'Pappa', '[name]@stadt.sg.ch', 'Rathaus', 'info@stadt.sg.ch', 'Wittenbach', 'Herr', 'Peter', 'Bruhin', '[name]@wittenbach.ch', 'Dottenwilerstrasse 2', 'info@wittenbach.ch', 'Häggenschwil', 'Raffael', 'Gemperle', '[name]@haeggenschwil.ch', 'Dorfstrasse 18', 'info@haeggenschwil.ch', 'Muolen', 'Florian', 'Hafner', '[name]@muolen.ch', 'Dorfstrasse 9', 'info@muolen.ch', 'Mörschwil', 'Martina']
rows 81
hyperlinks 0
url-like strings 0 []
```

## Step 33: Bash: Parse SG communes XLSX with openpyxl
```
cd /tmp/sg-verify-run3-c && python3 -c "
import openpyxl
wb=openpyxl.load_workbook('sg_polgem.xlsx',read_only=True)
ws=wb.active
rows=list(ws.iter_rows(values_only=True))
print(len(rows)); 
for r in rows[:5]: print(r)
data=[r for r in rows if r and isinstance(r[0],(int,float))]
print('numbered rows',len(data)); print(data[-1])
" 2>&1 | head -20
```
**No result: this is the command that was waiting for approval when the run stalled.**
