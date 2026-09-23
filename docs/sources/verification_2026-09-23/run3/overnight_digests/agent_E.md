# Run 3 agent E: progress before the stall (log a781c7853e8e16247, 03:30–03:39 UTC 2026-09-23)

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

> Now let me read the prepared inputs: the precheck entry points, law_hits, sitemap candidates, and the probe files.

## Step 3: Bash: Read precheck entry points file
```
cat <scratchpad-overnight>/precheck_entry_points_2026-09-23.md
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

## Step 4: Bash: List stage0 and reports directories
```
ls -la <scratchpad-overnight>/stage0/ <scratchpad-overnight>/reports/; ls <scratchpad-overnight>/stage0/sitemaps/ 2>/dev/null | head -80
```
Result:
```
<scratchpad-overnight>/reports/:
total 144
drwxr-xr-x   8 <user>  wheel    256 Sep 23 03:26 .
drwx------  27 <user>  wheel    864 Sep 23 05:29 ..
-rw-r--r--   1 <user>  wheel   5855 Sep 23 03:24 g1-commune-law.md
-rw-r--r--   1 <user>  wheel   5179 Sep 23 03:15 g2-districts.md
-rw-r--r--   1 <user>  wheel   5667 Sep 23 03:26 g3-associations.md
-rw-r--r--   1 <user>  wheel   7205 Sep 23 03:10 g4-intercantonal.md
-rw-r--r--   1 <user>  wheel  29663 Sep 23 03:12 g5-guidance.md
-rw-r--r--   1 <user>  wheel   4135 Sep 23 02:26 pilot.md

<scratchpad-overnight>/stage0/:
total 7832
drwxr-xr-x  32 <user>  wheel    1024 Sep 23 05:28 .
drwx------  27 <user>  wheel     864 Sep 23 05:29 ..
-rw-r--r--   1 <user>  wheel   72586 Sep 23 05:22 law_hits.json
-rw-r--r--   1 <user>  wheel  100081 Sep 23 05:19 laws_AG.json
-rw-r--r--   1 <user>  wheel   91793 Sep 23 05:19 laws_AI.json
-rw-r--r--   1 <user>  wheel   69030 Sep 23 05:19 laws_AR.json
-rw-r--r--   1 <user>  wheel  166668 Sep 23 05:19 laws_BE.json
-rw-r--r--   1 <user>  wheel  190961 Sep 23 05:19 laws_BL.json
-rw-r--r--   1 <user>  wheel  216290 Sep 23 05:19 laws_BS.json
-rw-r--r--   1 <user>  wheel  179564 Sep 23 05:19 laws_FR.json
-rw-r--r--   1 <user>  wheel  176529 Sep 23 05:19 laws_GE.json
-rw-r--r--   1 <user>  wheel  111466 Sep 23 05:19 laws_GL.json
-rw-r--r--   1 <user>  wheel   90962 Sep 23 05:19 laws_GR.json
-rw-r--r--   1 <user>  wheel  188156 Sep 23 05:20 laws_JU.json
-rw-r--r--   1 <user>  wheel  141526 Sep 23 05:19 laws_LU.json
-rw-r--r--   1 <user>  wheel  171257 Sep 23 05:19 laws_NE.json
-rw-r--r--   1 <user>  wheel   93182 Sep 23 05:19 laws_NW.json
-rw-r--r--   1 <user>  wheel  114139 Sep 23 05:19 laws_OW.json
-rw-r--r--   1 <user>  wheel  167759 Sep 23 05:19 laws_SG.json
-rw-r--r--   1 <user>  wheel   99052 Sep 23 05:19 laws_SH.json
-rw-r--r--   1 <user>  wheel  119141 Sep 23 05:19 laws_SO.json
-rw-r--r--   1 <user>  wheel  107168 Sep 23 05:19 laws_TG.json
-rw-r--r--   1 <user>  wheel  122532 Sep 23 05:19 laws_TI.json
-rw-r--r--   1 <user>  wheel   78934 Sep 23 05:19 laws_UR.json
-rw-r--r--   1 <user>  wheel  187897 Sep 23 05:19 law
```

## Step 5: Bash: Show law_hits for TI, GR, VS
```
cd <scratchpad-overnight>/stage0/; python3 -c "
import json
d=json.load(open('law_hits.json'))
print(type(d), list(d.keys())[:40] if isinstance(d,dict) else len(d))
for c in ['TI','GR','VS']:
    print('=====',c)
    print(json.dumps(d.get(c), ensure_ascii=False, indent=1)[:6000])
"
```
Result:
```
<class 'dict'> ['AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH']
===== TI
{
 "road": [
  {
   "nr": "760.100",
   "title": "Legge di applicazione alla legislazione federale sulla circolazione stradale e la tassa sul traffico pesante",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/21053"
  },
  {
   "nr": "760.110",
   "title": "Regolamento della legge cantonale di applicazione della legislazione federale sulla circolazione stradale e la tassa sul traffico pesante",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/21314"
  },
  {
   "nr": "760.120",
   "title": "Regolamento sulle slitte a motore, sui veicoli per la preparazione delle piste e sulla circolazione fuori strada",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/19862"
  },
  {
   "nr": "760.500",
   "title": "Legge sulle imposte e tasse di circolazione dei veicoli a motore",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/19614"
  },
  {
   "nr": "760.510",
   "title": "Regolamento di applicazione della legge sulle imposte e tasse di circolazione dei veicoli a motore",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/21900"
  },
  {
   "nr": "561.350",
   "title": "Regolamento sulle registrazioni audio e video per l’identificazione dei veicoli",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/23173"
  },
  {
   "nr": "741.280",
   "title": "Decreto esecutivo concernente gli incentivi per l'acquisto di veicoli, motoveicoli, quadricicli e tricicli elettrici, lo sviluppo di infrastrutture di",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/23515"
  },
  {
   "nr": "832.200",
   "title": "Legge concernente l’eliminazione degli autoveicoli inservibili",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/21004"
  }
 ],
 "court_org": [
  {
   "nr": "177.100",
   "title": "Legge sull’organizzazione giudiziaria",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/32191"
  }
 ],
 "conciliation": [
  {
   "nr": "177.110",
   "title": "Regolamento delle Giudicature di pace",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/20829"
  },
  {
   "nr": "842.100",
   "title": "Legge sull’Ufficio cantonale di conciliazione e sul conferimento del carattere obbligatorio generale al contratto collettivo di lavoro",
   "api": "https://www.lexfind.ch/api/fe/de/texts-of-law/21414"
  },
  {
   "nr": "842.110",
   "title": "Regolamento sull’
```

## Step 6: Bash: Show sitemap topic candidates for TI, GR, VS
```
cd <scratchpad-overnight>/stage0/; python3 -c "
import json
d=json.load(open('sitemap_topic_candidates.json'))
print(type(d), list(d.keys())[:60] if isinstance(d,dict) else len(d))
for c in ['TI','GR','VS']:
    print('=====',c)
    print(json.dumps(d.get(c), ensure_ascii=False, indent=1)[:5000])
"; python3 -c "
import json
d=json.load(open('<scratchpad-overnight>/stage0/sitemaps_summary.json'))
print(json.dumps(d, indent=1)[:200])
for k in (d if isinstance(d,dict) else []):
    if any(x in k for x in ['ti.ch','gr.ch','vs.ch','lugano']):
        print(k, d[k])
"
```
Result:
```
<class 'dict'> ['ZH', 'BE', 'LU', 'UR', 'SZ', 'OW', 'NW', 'GL', 'ZG', 'FR', 'SO', 'BS', 'BL', 'SH', 'AR', 'AI', 'SG', 'GR', 'AG', 'TG', 'TI', 'VD', 'VS', 'NE', 'GE', 'JU']
===== TI
{
 "courts": {
  "count": 0,
  "shortest": []
 },
 "dogs": {
  "count": 1,
  "shortest": [
   "https://www4.ti.ch/decs/dcsu/osservatorio/agenda-culturale/cerca-evento/dettaglio/109423/liebe_und_sexualitt_in_der_frhen_neuzeit_und_im_19_jahrhundert"
  ]
 },
 "tax": {
  "count": 4,
  "shortest": [
   "https://www.lugano.ch/temi-servizi/lavoro-e-impresa/imposte/dichiarazione.html",
   "https://www.lugano.ch/de/temi-servizi/lavoro-e-impresa/imposte/dichiarazione.html",
   "https://www.lugano.ch/en/temi-servizi/lavoro-e-impresa/imposte/dichiarazione.html",
   "https://www.lugano.ch/fr/temi-servizi/lavoro-e-impresa/imposte/dichiarazione.html"
  ]
 },
 "holidays": {
  "count": 4,
  "shortest": [
   "https://www.lugano.ch/temi-servizi/scuola-formazione/calendario-scolastico.html",
   "https://www.lugano.ch/de/temi-servizi/scuola-formazione/calendario-scolastico.html",
   "https://www.lugano.ch/en/temi-servizi/scuola-formazione/calendario-scolastico.html",
   "https://www.lugano.ch/fr/temi-servizi/scuola-formazione/calendario-scolastico.html"
  ]
 },
 "road": {
  "count": 4,
  "shortest": [
   "https://www.lugano.ch/temi-servizi/salute-sicurezza/educazione-stradale/giardino-circolazione.html",
   "https://www.lugano.ch/de/temi-servizi/salute-sicurezza/educazione-stradale/giardino-circolazione.html",
   "https://www.lugano.ch/en/temi-servizi/salute-sicurezza/educazione-stradale/giardino-circolazione.html",
   "https://www.lugano.ch/fr/temi-servizi/salute-sicurezza/educazione-stradale/giardino-circolazione.html"
  ]
 },
 "communes": {
  "count": 8,
  "shortest": [
   "https://www.lugano.ch/area-stampa/comunicati-stampa.html",
   "https://www.lugano.ch/de/area-stampa/comunicati-stampa.html",
   "https://www.lugano.ch/en/area-stampa/comunicati-stampa.html",
   "https://www.lugano.ch/fr/area-stampa/comunicati-stampa.html",
   "https://www.lugano.ch/vivere-lugano/cultura-e-tempo-libero/associazioni/lista-associazioni/comunita-culturale-afghana-ticino.html",
   "https://www.lugano.ch/de/vivere-lugano/cultura-e-tempo-libero/associazioni/lista-associazioni/comunita-culturale-afghana-ticino.html",
   "https://www.lugano.ch/en/vivere-lugano/cultura-e-tempo-libero/associazioni/lista-associazioni/comunita-culturale-afghana-ticino.html",
   "https://www.lugano.ch/fr/vivere-lugano/cultura-e-tempo-libero
```

## Step 7: Bash: Show sitemap summary for my cantons and line counts
```
cd <scratchpad-overnight>/stage0/; python3 -c "
import json
d=json.load(open('sitemaps_summary.json'))
print(d.keys())
for k,v in d.items():
    if isinstance(v,dict):
        for kk,vv in v.items():
            if kk in ('TI','GR','VS') or any(x in str(kk) for x in ['ti.ch','gr.ch','vs.ch','lugano']):
                print(k,kk,vv)
"; wc -l sitemaps/www4.ti.ch.txt sitemaps/www.gr.ch.txt sitemaps/www.vs.ch.txt sitemaps/www.lugano.ch.txt; cat sitemap_fetch.py | head -80
```
Result:
```
dict_keys(['hosts', 'result'])
hosts GR ['www.gr.ch']
hosts TI ['www4.ti.ch', 'www.lugano.ch']
hosts VS ['www.vs.ch']
result www.gr.ch {'urls': 0, 'sitemaps_fetched': 2, 'delay': 0.3, 'log': ['robots 200', 'https://www.gr.ch/sitemap.xml 404 0', 'https://www.gr.ch/sitemap_index.xml 404 0']}
result www4.ti.ch {'urls': 603, 'sitemaps_fetched': 1, 'delay': 0.3, 'log': ['robots 200', 'https://www4.ti.ch/user_librerie/php/DECS/agendaCulturale/sitemapAgendaCulturale.xml 200 603']}
result www.lugano.ch {'urls': 5684, 'sitemaps_fetched': 1, 'delay': 0.3, 'log': ['robots 200', 'https://www.lugano.ch/sitemap.xml 200 5684']}
result www.vs.ch {'urls': 99, 'sitemaps_fetched': 61, 'delay': 0.3, 'log': ['robots 200', 'https://www.vs.ch/sitemap.xml 200 60', 'https://www.vs.ch/sitemap.xml?p_l_id=6652985&layoutUuid=30252b91-e44f-e2fa-0d87-046e716b74b4&groupId=10181&privateLayout=false 200 0']}
     602 sitemaps/www4.ti.ch.txt
       0 sitemaps/www.gr.ch.txt
      98 sitemaps/www.vs.ch.txt
    5683 sitemaps/www.lugano.ch.txt
    6383 total
import sys,re,json,gzip,time,subprocess,threading,collections,concurrent.futures as cf
S=sys.argv[1];UA='Mozilla/5.0 swiss-grounding-check'
HOSTS={
'ZH':['www.zh.ch','www.gerichte-zh.ch','www.stadt-zuerich.ch'],
'BE':['www.zsg.justice.be.ch','www.rsta.dij.be.ch','www.svsa.sid.be.ch','www.sv.fin.be.ch','www.weu.be.ch','www.bkd.be.ch','www.sta.be.ch','www.akvb-gemeinden.bkd.be.ch','www.be.ch','www.bern.ch','www.thun.ch'],
'LU':['www.lu.ch','gerichte.lu.ch','veterinaerdienst.lu.ch','steuerbuch.lu.ch','strassenverkehrsamt.lu.ch','volksschulbildung.lu.ch'],
'UR':['www.ur.ch'],'SZ':['www.sz.ch'],'OW':['www.ow.ch'],'NW':['www.nw.ch'],'GL':['www.gl.ch'],'ZG':['zg.ch'],
'FR':['www.fr.ch','www.ocn.ch'],'SO':['so.ch'],'BS':['www.bs.ch'],'BL':['www.baselland.ch'],'SH':['sh.ch','www.stadt-schaffhausen.ch'],
'AR':['ar.ch'],'AI':['www.ai.ch'],'SG':['www.sg.ch'],'GR':['www.gr.ch'],'AG':['www.ag.ch'],
'TG':['www.tg.ch','strassenverkehrsamt.tg.ch','staatskanzlei.tg.ch'],'TI':['www4.ti.ch','www.lugano.ch'],
'VD':['www.vd.ch','www.lausanne.ch'],'VS':['www.vs.ch'],'NE':['www.ne.ch','www.scan-ne.ch','www.chaux-de-fonds.ch','www.neuchatelville.ch'],
'GE':['www.ge.ch','justice.ge.ch','www.geneve.ch','www.vernier.ch'],'JU':['www.jura.ch'],
}
THROTTLE={'www.sz.ch':3,'www.gl.ch':3}
def get(url):
    r=subprocess.run(['curl','-sL','-g','--compressed','--max-time','60','-A',UA,'-w','\n%{http_code}',url],capture_output=True)
    body=r.stdout;code=body[-3:].decode(error
```

## Step 8: Bash: Grep AI rows for TI, GR, VS links
```
cd <scratchpad-overnight>/; grep -n -i -E "'(TI|GR|VS)'|\"(TI|GR|VS)\"|ti\.ch|gr\.ch|vs\.ch|lugano|justiz-gr|tribunaux" courts_s1_rows.py guidance_s3a_rows.py s3b_s4_rows.py cities_s2_links.txt | head -100
```
Result:
```
cities_s2_links.txt:5:Lugano|https://www.lugano.ch/amministrazione-servizi/regolamenti.html
s3b_s4_rows.py:4:('S3b','VS','dogs','https://www.vs.ch/web/scav/chiens'),('S3b','VS','tax','https://www.vs.ch/web/scc/personnes-physiques'),('S3b','VS','school','https://www.vs.ch/web/se/vacances-scolaires'),('S3b','VS','road','https://www.vs.ch/web/scn'),
s3b_s4_rows.py:8:('S3b','TI','dogs','https://www4.ti.ch/dss/dsp/uvc/settori/sanita-animale/cani'),('S3b','TI','tax','https://www4.ti.ch/dfe/dc/dichiarazione/istruzioni-e-moduli'),('S3b','TI','school','https://www4.ti.ch/decs/ds/scuola/calendario-scolastico'),('S3b','TI','road','https://www4.ti.ch/di/sezione-della-circolazione/sezione-della-circolazione'),
s3b_s4_rows.py:18:('S4','GR','communes','https://www.gr.ch/DE/kanton/gemeinden/'),('S4','GR','chancellery','https://www.gr.ch/DE/institutionen/verwaltung/staka/'),
s3b_s4_rows.py:29:('S4','TI','communes','https://www4.ti.ch/di/sel/comuni/elenco-dei-comuni-ticinesi'),('S4','TI','chancellery','https://www4.ti.ch/can/oltre-confine/cancelleria-dello-stato'),
s3b_s4_rows.py:31:('S4','VS','communes','https://www.vs.ch/web/sifom/communes'),('S4','VS','chancellery','https://www.vs.ch/web/che'),
guidance_s3a_rows.py:12:('GR','dogs','G:https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/hunde/'),('GR','tax','G:https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/steuerbuch/'),('GR','school','G:https://www.gr.ch/DE/institutionen/verwaltung/ekud/avs/schulferien/'),('GR','road','G:https://www.gr.ch/DE/institutionen/verwaltung/djs/stva/'),
courts_s1_rows.py:8:GR='https://www.justiz-gr.ch'; AG='https://www.ag.ch/de/gerichte'; TG='https://gerichte.tg.ch'; TI='https://www4.ti.ch/potere-giudiziario'
courts_s1_rows.py:9:VD='https://www.vd.ch/toutes-les-autorites/ordre-judiciaire-vaudois-ojv'; VS='https://tribunaux.vs.ch/fr'; NE='https://www.ne.ch/autorites/PJ'
courts_s1_rows.py:31:('FR',"Tribunaux d'arrondissement",f'G:{FR}/tribunaux-darrondissement',f'G:{FR}/frais-et-emoluments',f'G:{FR}/themes',f'G:{FR}/jurisprudence'),
courts_s1_rows.py:45:('GR','Kantonsgericht',f'G:{GR}/kantonsgericht',f'G:{GR}/themen/gebuehren',f'G:{GR}/themen',f'G:{GR}/rechtsprechung'),
courts_s1_rows.py:46:('GR','Verwaltungsgericht',f'G:{GR}/verwaltungsgericht',f'G:{GR}/themen/gebuehren',f'G:{GR}/themen',f'G:{GR}/rechtsprechung'),
courts_s1_rows.py:47:('GR','Regionalgerichte',f'G:{GR}/regionalgerichte',f'G:{GR}/themen/gebuehren',f'G:{GR}/themen',f'G:{GR}/rechtsprechung'),
courts_s1_rows.py:54:('TI','Tribu
```

## Step 9: Bash: Show AI probe results for TI, GR, VS
```
cd <scratchpad-overnight>/; python3 - <<'EOF'
import json
for f in ['courts_s1_probe.json','guidance_s3a_probe.json','s3b_s4_probe.json']:
    d=json.load(open(f))
    print('=====',f,type(d), len(d))
    items = d if isinstance(d,list) else (d.get('results') or d.get('rows') or list(d.values()))
    if isinstance(d,dict): print('keys',list(d.keys())[:10])
    for it in (items if isinstance(items,list) else []):
        s=json.dumps(it,ensure_ascii=False)
        if any(x in s for x in ['"TI"','"GR"','"VS"','ti.ch','gr.ch','vs.ch','lugano']):
            print(s[:400])
EOF
```
Result:
```
===== courts_s1_probe.json <class 'dict'> 141
keys ['https://www.gerichte-zh.ch/', 'https://www.gerichte-zh.ch/themen/prozesskosten.html', 'https://www.gerichte-zh.ch/themen.html', 'https://www.gerichte-zh.ch/entscheide.html', 'https://www.zh.ch/de/direktion-der-justiz-und-des-innern/verwaltungsgericht.html', 'https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht/informationen-zum-gerichtsverfahren.html', 'https://www.zh.ch/de/politik-staat/streitigkeiten-vor-verwaltungsgericht.html', 'https://vgrzh.djiktzh.ch/', 'https://www.gerichte-zh.ch/organisation/bezirksgerichte.html', 'https://www.zsg.justice.be.ch/de/start.html']
{"code": "404", "ct": "text/html", "size": 1451, "final": "https://www.justiz-gr.ch/kantonsgericht/", "title": "Page Not Found", "links": 0, "words": 97, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 1443, "final": "https://www.justiz-gr.ch/themen/gebuehren/", "title": "Page Not Found", "links": 0, "words": 97, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 1443, "final": "https://www.justiz-gr.ch/themen/", "title": "Page Not Found", "links": 0, "words": 97, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 1451, "final": "https://www.justiz-gr.ch/rechtsprechung/", "title": "Page Not Found", "links": 0, "words": 97, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 1455, "final": "https://www.justiz-gr.ch/verwaltungsgericht/", "title": "Page Not Found", "links": 0, "words": 97, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 1453, "final": "https://www.justiz-gr.ch/regionalgerichte/", "title": "Page Not Found", "links": 0, "words": 97, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 7462, "final": "https://www4.ti.ch/potere-giudiziario/tribunale-di-appello", "title": "404 - Cantone Ticino", "links": 15, "words": 57, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 7464, "final": "https://www4.ti.ch/potere-giudiziario/tasse-giudiziarie", "title": "404 - Cantone Ticino", "links": 15, "words": 57, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 7465, "final": "https://www4.ti.ch/potere-giudiziario/temi", "title": "404 - Cantone Ticino", "links": 15, "words": 57, "grounded": false, "class": "http-404"}
{"code": "404", "ct": "text/html", "size": 7463, 
```

## Step 10: Bash: Inspect opencaselaw courts JSON structure
```
cd <scratchpad-overnight>/; python3 - <<'EOF'
import json
d=json.load(open('opencaselaw_courts_2026-09-23.json'))
print(type(d), (list(d.keys())[:10] if isinstance(d,dict) else len(d)))
items = d if isinstance(d,list) else d.get('courts', d)
if isinstance(items, dict):
    items = list(items.values()) if not isinstance(list(items.values())[0], (int,str)) else items
print(json.dumps(items[:2] if isinstance(items,list) else items, ensure_ascii=False)[:800])
EOF
```
Result:
```
<class 'list'> 136
[{"court": "bger", "canton": "CH", "decision_count": 193393, "earliest": "1986-10-06", "latest": "2026-09-10", "languages": 3, "sparse": false}, {"court": "ge_gerichte", "canton": "GE", "decision_count": 170523, "earliest": "1908-11-08", "latest": "2026-09-14", "languages": 3, "sparse": false}]
```

## Step 11: Bash: Show opencaselaw coverage and prior reports for my cantons
```
cd <scratchpad-overnight>/; python3 - <<'EOF'
import json
d=json.load(open('opencaselaw_courts_2026-09-23.json'))
for it in d:
    if it['canton'] in ('TI','GR','VS'):
        print(it)
print(sum(x['decision_count'] for x in d), len(d))
EOF
grep -n -i -E "TI|GR|VS|ticino|graub|valais|wallis|lugano|rleggi" reports/g5-guidance.md | head -30; grep -n -i -E "ticino|RLeggi|www3.ti|graub|valais|wallis|lex.vs|gr-lex|lugano" verification_results_2026-09-23.md reports/*.md | head -40
```
Result:
```
{'court': 'ti_gerichte', 'canton': 'TI', 'decision_count': 66944, 'earliest': '1922-05-07', 'latest': '2026-07-08', 'languages': 3, 'sparse': False}
{'court': 'gr_gerichte', 'canton': 'GR', 'decision_count': 15821, 'earliest': '1992-09-02', 'latest': '2026-09-14', 'languages': 2, 'sparse': False}
{'court': 'vs_gerichte', 'canton': 'VS', 'decision_count': 7008, 'earliest': '1959-11-20', 'latest': '2026-09-06', 'languages': 3, 'sparse': False}
{'court': 'sav_kantone', 'canton': 'VS', 'decision_count': 1, 'earliest': None, 'latest': None, 'languages': 1, 'sparse': True}
1081345 136
18:**404 distinct zstb URLs: 159 HTML entries** (`.../steuerbuch-definition/zstb-<nr>.html`) and 245 PDFs, of which
19:148 have no "gueltig-bis" in the name, meaning they are current PDF-only or attachment entries. There are also
21:"Thema Natürliche Personen · Unterthema Einkommenssteuer (§§ 16 - 37b) · Titel Weisung ... Wertschriften ...
22:Erlassdatum 27. September 2023 · Gültig ab 27. September 2023 · ZStB-Nummer 30.1 · Nummer alt 18/701", and
23:sections A–E. → **Yes today (html_crawl), if it is seeded from the sitemap**. A small "sitemap-seeded crawl" helper
25:exists but returned 400 for `q=`/`query=`, and the suggestion endpoint returned 204. It is not needed.
27:## Cross-cutting: can one "cantonal portal crawler" cover all four cantons?
30:| ZH | yes (AEM; e.g. hunde.html 128 KB, 2,556 words) | robots names the index `/bin/zhweb/publish/sitemap.xml` → 44 per-directorate/topic child sitemaps (`/de/<topic>.zhweb-sitemap.xml`), with lastmod. umwelt-tiere has 7,826 locs, mobilitaet 2,314, bildung 2,311, steuern-finanzen 1,043, sicherheitsdirektion 197. PDFs are listed too. | `searchoverview.zhweb-search.json` answers 400; parameters not found |
32:| BE | yes (AEM), but **decentralised**: every directorate/office has its own host (`www.weu.be.ch`, `www.sv.fin.be.ch`, `www.svsa.sid.be.ch`, `www.bkd.be.ch`) | `be.ch/sitemap.xml` covers only be.ch (de 39 URLs, fr 40). Each office host has the same template `/<host>/sitemap.xml` → `/de/sitemap.xml` + `/fr/sitemap.xml`: svsa 229, sv.fin 172, weu 489, bkd 697 (de). robots: `Disallow: /content/`, `Allow: /content/dam/` (be.ch), `Crawl-delay: 10` | not checked |
33:| BS | yes (Nuxt SSR over Drupal; the text is in the HTML, e.g. anwohnerparkkarte 745 words) | `/sitemap.xml` → 14 pages, **27,209 URLs** with lastmod. 19,856 are medienmitteilungen, 676 `/themen/`. `Crawl-delay: 10` | `/jsonapi` 404, `/graphql` 403, `/api/search` 404 |
36:a
```

## Step 12: Bash: Grep repo assessment for my cantons and count communes
```
cd <repo>; grep -n -i -E "lugano|ticino|www3.ti|RLeggi|graub|gr-lex|valais|wallis|lex.vs|entscheidsuche|onlinekommentar|clds|opencaselaw" docs/sources/ogd_lists_assessment.md | head -40; echo ---; awk -F, 'NR>1{print $3}' docs/sources/commune_sites.csv | sort | uniq -c | grep -E "TI|GR|VS"; grep -i lugano docs/sources/commune_sites.csv
```
Result:
```
10:with a handful of contributors. The maintainer also publishes `opencaselaw-client` (MIT, a Python
11:client for the opencaselaw REST API), `entscheidsuche-client`, `onlinekommentar-client` and
160:### 3.1 opencaselaw.ch — keyless REST API, CC0 corpus
162:Base `https://mcp.opencaselaw.ch/api`, OpenAPI at `/api/openapi.json` (62 endpoints). No API key.
182:| TI | 922.110 Regolamento caccia | 69/69 | www3.ti.ch |
185:Provenance chain for a citation: opencaselaw → LexFind → official portal. Cite `original_url`.
206:is a JavaScript shell. There is no listing endpoint; opencaselaw's scraper enumerates through
207:full-text search sessions and sleeps between requests. Prefer opencaselaw's mirror for bulk work
228:  from opencaselaw/LexFind; the site JSON is only good for spot checks.
231:  ingest acts from a URL list taken from opencaselaw/LexFind; the API route gives article text
260:cantonal collections via LexFind/opencaselaw, municipal collections), `official_info` for official
270:- **opencaselaw MCP** (`https://mcp.opencaselaw.ch`, 42 tools): a second grounding server to
293:- LexFind and opencaselaw `/legislation/search` for law discovery per canton and topic.
321:- opencaselaw refresh is documented, not observed; the failed TI lookup is unexplained.
332:4. Hand the colleague three enhancement issues with the evidence here: an `opencaselaw` fetcher
346:# opencaselaw: search cantonal articles, then full text
347:curl -s "https://mcp.opencaselaw.ch/api/laws/search?q=Hund%20Leine&canton=ZH&limit=5"
348:curl -s "https://mcp.opencaselaw.ch/api/legislation/22888"
477:### B.7 opencaselaw REST — JSON (cantonal and federal legislation)
479:- Base `https://mcp.opencaselaw.ch/api`; OpenAPI 3.0.3 at `/api/openapi.json` (62 paths); no key;
505:  belex.sites.be.ch (de and fr), www3.ti.ch, prestations.vd.ch.
517:  &page_no=&results_per_page=60`, as opencaselaw's scraper does, with a sleep between calls).
598:| E2 | OpenCaseLaw | live API | Usable with a new fetcher | Decision, citation-graph, scholarship and commentary APIs plus a CC0 bulk parquet; authority for court rulings from an aggregator to decide |
762:### C.11 E2 — OpenCaseLaw (decisions, citation graph, scholarship, bulk dataset, MCP)
763:API https://mcp.opencaselaw.ch/api (200 JSON, no auth), OpenAPI /api/openapi.json (62 paths). MCP SSE at /sse live; POST /api/tool/{name} calls any of 42 tools over HTTP.
764:What: third-party aggregator (Jonas Hertner), rebuilt daily; 1,081,345 decisions (live /api/statist
```

## Step 13: Bash: Read assessment intro and opencaselaw section
```
cd <repo>; sed -n 1,30p docs/sources/ogd_lists_assessment.md; echo ....; sed -n 155,240p docs/sources/ogd_lists_assessment.md
```
Result:
```
# What the two rnckp lists give Swiss Grounding

Assessed 2026-09-22 against the pipeline at `ec2d7ed` (fetch strategies: `fedlex_sparql`,
`html_crawl`, `api`, `pdf`; categories: hiking, waste, dogs, taxes, housing, transport, parking,
schools, health, safety). Every claim below was checked with a live request on that date unless
marked *inferred* or *unverified*. Commands are in the appendix so anyone can re-run them.

Repository facts (GitHub API, 2026-09-22): 177 stars, 18 forks, created 2022-11-13, last push
2026-09-16, no open issues; maintained by one person (rnckp / Patrick Arnecke, 190 of ~205 commits)
with a handful of contributors. The maintainer also publishes `opencaselaw-client` (MIT, a Python
client for the opencaselaw REST API), `entscheidsuche-client`, `onlinekommentar-client` and
starter-code generators for opendata.swiss CSVs.

Lists:
- `rnckp/awesome-ogd-switzerland` (CC0, 320 links, last commit 2026-09-16) — open government
  *data*: statistics, geodata, APIs, linked data.
- `rnckp/awesome-open-legal-switzerland` (same author, 114 links, last commit 2026-08-17) — open
  *legal* data: legislation, courts, soft law, MCP servers. **This is the list that maps onto the
  project; the OGD list pointed to it.**

## 1. Verdict

About ninety percent of the OGD list is statistical tables and geodata the pipeline cannot ingest
and a citizen question cannot cite. The remaining ten percent contains the cheapest coverage wins
left before the deadline (calendar feeds, YAML only, no LLM cost) and the only practical route to
cantonal law (an API, because the cantonal law portals are JavaScript apps the crawler cannot read).

## 2. Ingestible now, YAML only, through the `api` strategy

Constraints of the strategy (`ingest/fetchers/api.py`): one request per source, no pagination, so
....
their inner collections were not tested.)

**The schema has a `cantonal_law` authority and no source uses it** (`grep authority: cantonal_law
registry/sources/` is empty).

### 3.1 opencaselaw.ch — keyless REST API, CC0 corpus

Base `https://mcp.opencaselaw.ch/api`, OpenAPI at `/api/openapi.json` (62 endpoints). No API key.
Relevant endpoints:

| endpoint | returns |
|---|---|
| `GET /laws/search?q=&canton=&limit=` | federated hits over federal and cantonal *articles*: level, canton, sr_number, title, article_num, heading, snippet, lexfind_id |
| `GET /laws/{canton}/{sr_number}` | act metadata + article list (num, heading) |
| `GET /legislation/{lexfind_id}` | **full arti
```

## Step 14: Bash: Read Amtsblattportal and OpenCaseLaw sections
```
cd <repo>; sed -n 240,300p docs/sources/ogd_lists_assessment.md; echo ....; sed -n 755,840p docs/sources/ogd_lists_assessment.md
```
Result:
```
- 29 tenants: every cantonal gazette (ZH, BE, LU, …, GE, VD, TI) plus SHAB and `kabda`,
  "ePublikation für Gemeinden und Städte".
- 152 rubrics, including "Allgemeine amtliche Bekanntmachungen", "Bau, Raum, Verkehr, Umwelt und
  Energie", "Bürgerrecht, Steuer- und Zivilstandswesen", "Politische Rechte", "Kommunale
  Bauprojekte", "Beschlüsse und Erlasse".
- Filters on `GET /publications`: `tenants`, `rubrics`, `cantons`, `registrationOffice`,
  **`municipalityId` (FSO commune number, joins `location.bfs_id`)**, `publicationDate.start/.end`,
  `keyword`, `title`. Example counts: tenant ZH 2,849,769 total, 11,348 in the week to 2026-09-22;
  Stadt Bern municipal rubric 1,120.
- Each publication: JSON meta (rubric, office with `municipalityId`, cantons, publicationDate,
  expirationDate, multilingual title) and `GET /publications/{id}/xml` with a `<content>` block
  holding the notice text (e.g. the Solothurn police lifting a forest fire ban, 3 KB).

Most volume is commercial-register and bankruptcy notices; the value is in the general and
municipal rubrics: temporary rules, closures, changed collection days, new ordinances entering
into force. Needs an XML fetcher (new code): filter by rubric and date, map `municipalityId` →
commune node and `cantons` → canton node, `valid_from = publicationDate`, `valid_to =
expirationDate`, cite the portal URL. **Authority: `official_info` for every rubric, including
"Beschlüsse und Erlasse"** — a gazette is a publication organ, not a law collection; the law
authorities are reserved for legal text fetched from the official law platforms (Fedlex, the
cantonal collections via LexFind/opencaselaw, municipal collections), `official_info` for official
entities and the online systems they run, `institutional` for non-government publishers (decision
2026-09-22, recorded in #39). The web UI's robots.txt disallows crawling; the API is the
intended access path.

## 4. Evaluation assets

- **Swiss Legal RAG Bench** (`huggingface.co/datasets/voilaj/swiss-legal-rag-bench`, CC0,
  v0.1 2026-04-28): 30 questions in DE/FR/IT with reference answers and gold SR-article citations;
  federal law only so far. Usable as extra judge cases once the acts are ingested.
- **opencaselaw MCP** (`https://mcp.opencaselaw.ch`, 42 tools): a second grounding server to
  compare answers against in the judge harness. *Not tried.*

## 5. Location resolution assets

- Swiss official commune register (BFS) — already the basis of `locations/data/communes.csv`.

```

> Inputs read. Setting up a scratch dir and a probe helper that reports status, type, size, title, link and word counts for each URL.

## Step 15: Bash: Create scratch dir and URL probe helper
```
mkdir -p /tmp/sg-verify-run3-e && cd /tmp/sg-verify-run3-e && cat > probe.py <<'EOF'
import sys, subprocess, re, html, hashlib, os
UA = os.environ.get('UA', 'Mozilla/5.0 swiss-grounding-check')
def probe(url, save=None, extra=None):
    fn = save or '/tmp/sg-verify-run3-e/p_' + hashlib.md5(url.encode()).hexdigest()[:10]
    cmd = ['curl', '-sL', '-g', '--compressed', '--max-time', '40', '-A', UA, '-o', fn,
           '-w', '%{http_code}|%{content_type}|%{size_download}|%{url_effective}']
    if extra: cmd += extra
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    code, ct, size, final = (r.stdout.split('|') + ['', '', '', ''])[:4]
    title = ''; links = words = 0
    try:
        b = open(fn, 'rb').read()
        t = b.decode('utf-8', errors='ignore')
        if 'html' in ct or t.lstrip()[:15].lower().startswith(('<!doctype', '<html')):
            m = re.search(r'<title[^>]*>(.*?)</title>', t, re.S | re.I)
            title = html.unescape(re.sub(r'\s+', ' ', m.group(1))).strip()[:80] if m else ''
            links = len(re.findall(r'<a\s[^>]*href', t, re.I))
            body = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', t, flags=re.S | re.I)
            words = len(re.sub(r'<[^>]+>', ' ', body).split())
    except Exception as e:
        pass
    print(f'{code} | {ct[:30]} | {size}B | links {links} | words {words} | {title} | {final} | file {fn}')
    return fn
if __name__ == '__main__':
    for u in sys.argv[1:]:
        probe(u)
EOF
echo ok
```
Result:
```
ok
```

## Step 16: Bash: Probe TI portal root, robots and judiciary paths
```
cd /tmp/sg-verify-run3-e && python3 probe.py https://www4.ti.ch/ https://www.ti.ch/ https://www4.ti.ch/robots.txt https://www4.ti.ch/poteri/giudiziario/ https://www4.ti.ch/poteri/giudiziario/home/ https://www.ti.ch/giustizia https://www4.ti.ch/tribunali/ ; cat $(ls -t p_* | head -5 | tail -1) | head -30
```
Result:
```
200 | text/html; charset=utf-8 | 19723B | links 110 | words 1268 | Stato e organizzazione - Repubblica e Cantone Ticino | https://www4.ti.ch/tich/stato-e-organizzazione | file /tmp/sg-verify-run3-e/p_d914a63fb3
200 | text/html; charset=utf-8 | 19722B | links 110 | words 1268 | Stato e organizzazione - Repubblica e Cantone Ticino | https://www4.ti.ch/tich/stato-e-organizzazione | file /tmp/sg-verify-run3-e/p_dddc45e881
200 | text/plain; charset=utf-8 | 549B | links 0 | words 0 |  | https://www4.ti.ch/robots.txt | file /tmp/sg-verify-run3-e/p_617c9fa93b
200 | text/html; charset=utf-8 | 7206B | links 71 | words 439 | PG - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/pg | file /tmp/sg-verify-run3-e/p_5092ceb2f3
404 | text/html; charset=utf-8 | 2123B | links 15 | words 57 | 404 - Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/home/ | file /tmp/sg-verify-run3-e/p_06e5eab9fc
200 | text/html; charset=utf-8 | 7662B | links 74 | words 392 | Divisione - DG (DI) - Repubblica e Cantone Ticino | https://www4.ti.ch/index.php?id=1711 | file /tmp/sg-verify-run3-e/p_ad55b9eeb5
404 | text/html; charset=utf-8 | 2123B | links 15 | words 57 | 404 - Cantone Ticino | https://www4.ti.ch/tribunali/ | file /tmp/sg-verify-run3-e/p_f086ae9e57
User-agent: *
Allow: /
Disallow: /poteri/gc/ricerca-messaggi-e-atti/ricerca/
Disallow: /user_allegati/DI/Aste/
Disallow: /di/dg/uef/aste/
Disallow: /mcsn/tour_virtuale_no_limits_MCSN/
Disallow: /area-media/home/preview/
Disallow: /user_librerie/php/GC/allegato.php
Disallow: /user_librerie/php/CAN/rassegnastampa/articolo.php
Disallow: /fileadmin/POTERI/CdS/procedure_di_consultazione_cantonali/CAN/strategia_trasformazione_digitale_ticino/Consultazione_Strategia_Digitale_Documento.pdf
Disallow: /fileadmin/DSS/DSP/canicola/map-data.php

User-agent: gsa-crawler-TI
Disallow: /user_allegati/DI/Aste/
Disallow: /di/dg/uef/aste/
Disallow: /mcsn/tour_virtuale_no_limits_MCSN/
Disallow: /area-media/home/preview/
Disallow: /dt/da/spaas/uacer/
Disallow: /dt/da/spaas/ugras/

User-agent: Googlebot-Image
Disallow: /fileadmin/DI/POLIZIA/documentazione/prevenzione/Radar/

User-agent: TurnitinBot
Disallow: /

User-agent: PetalBot
Disallow: /

User-agent: Yahoo! Slurp
```

> The TI root answered 200 for me (redirects to /tich/stato-e-organizzazione), and the judiciary lives at /poteri/giudiziario/pg. Let me read its links.

## Step 17: Bash: List links on TI judiciary page
```
cd /tmp/sg-verify-run3-e && python3 - <<'EOF'
import re,html
t=open('p_5092ceb2f3',encoding='utf-8',errors='ignore').read()
for h,txt in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S|re.I):
    txt=html.unescape(re.sub(r'<[^>]+>|\s+',' ',txt)).strip()
    print(h,'|',txt[:70])
EOF
```
Result:
```
#maincontent | Vai al contenuto principale
/tich/cerca-nel-sito/ | Vai alla ricerca
/ | 
/tich | Repubblica e Cantone Ticino
http://www.ti.ch/pg | www.ti.ch/pg
/tich/cerca-nel-sito/ricerca/ | 
# | 
/poteri/giudiziario | Potere giudiziario (PG)
/poteri/giudiziario/pg | PG
/poteri/giudiziario/giustizia-civile/presentazione | Giustizia Civile
/poteri/giudiziario/giustizia-penale/presentazione | Giustizia Penale
/poteri/giudiziario/giustizia-amministrativa/presentazione | Giustizia Amministrativa
/poteri/giudiziario/avvocatura-e-notariato/presentazione | Avvocatura e Notariato
/poteri/giudiziario/locazione/la-locazione | Locazione
/poteri/giudiziario/sportello/temi | Sportello
/poteri/giudiziario/tribunale-dappello | Tribunale d'appello
/poteri/giudiziario/giustizia-amministrativa/tribunale-di-espropriazione | Tribunale delle espropriazioni
/poteri/giudiziario/giustizia-penale/tribunale-dei-minorenni | Tribunale dei minorenni
/poteri/giudiziario/io-e-il-diritto/io-e-il-divorzio | Divorzio
/poteri/giudiziario/io-e-il-diritto/io-e-la-locazione | Locazione
/poteri/giudiziario/io-e-il-diritto/io-e-il-lavoro | Lavoro
/poteri/giudiziario/io-e-il-diritto/io-e-lautorita-di-protezione | L'autorità di protezione
/poteri/giudiziario/consiglio-della-magistratura | Consiglio della Magistratura
/poteri/giudiziario/giustizia-penale/ministero-pubblico | Ministero pubblico
/poteri/giudiziario/giustizia-civile/preture | Preture
/poteri/giudiziario/giustizia-penale/pretura-penale | Pretura penale
/poteri/giudiziario/giustizia-penale/magistratura-dei-minorenni | Magistratura dei minorenni
/poteri/giudiziario/giustizia-civile/giudici-di-pace | Giudici di pace
/poteri/giudiziario/giustizia-civile/la-camera-1 | Camera di esecuzione e fallimenti (Tribunale d'appello)
/poteri/giudiziario/giustizia-civile/la-parita-di-sessi | Parità dei sessi
/poteri/giudiziario/locazione/giurisprudenza | Locazione: giurisprudenza
http://www.sentenze.ti.ch | 
http://www.sentenze.ti.ch/ | Sentenze online
/poteri/giudiziario/giustizia-amministrativa/tribunale-di-espropriazione | 
/poteri/giudiziario/giustizia-amministrativa/tribunale-di-espropriazione | Espropriazioni
/poteri/giudiziario/locazione | 
/poteri/giudiziario/locazione | Locazione
/poteri/giudiziario/giustizia-civile/giudici-di-pace | 
/poteri/giudiziario/giustizia-civile/giudici-di-pace | Giudice di pace
https://www3.ti.ch/CAN/comunicati/2026-09-17-comunicato-Tpc-2008656.pdf | 17.09.2026   Aggiornamento stampa - processi dal 21.09.2026 al 09.
```

> The TI judiciary has resident guidance ("io e il diritto"), a Sportello, the Giudici di pace and tenancy pages, plus sentenze.ti.ch. Probing them all.

## Step 18: Bash: Probe TI court guidance, conciliation and decision pages
```
cd /tmp/sg-verify-run3-e && B=https://www4.ti.ch/poteri/giudiziario; python3 probe.py $B/sportello/temi $B/io-e-il-diritto/io-e-il-divorzio $B/io-e-il-diritto/io-e-la-locazione $B/io-e-il-diritto/io-e-il-lavoro $B/io-e-il-diritto/io-e-lautorita-di-protezione $B/giustizia-civile/giudici-di-pace $B/locazione/la-locazione $B/giustizia-civile/preture $B/tribunale-dappello $B/sportello/pubblicazioni http://www.sentenze.ti.ch/
```
Result:
```
200 | text/html; charset=utf-8 | 6127B | links 50 | words 474 | Temi - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/sportello/temi | file /tmp/sg-verify-run3-e/p_67d6e04833
200 | text/html; charset=utf-8 | 5016B | links 39 | words 281 | Io e il divorzio - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/io-e-il-diritto/io-e-il-divorzio | file /tmp/sg-verify-run3-e/p_063df9bc8c
200 | text/html; charset=utf-8 | 4986B | links 40 | words 297 | Io e la locazione - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/io-e-il-diritto/io-e-la-locazione | file /tmp/sg-verify-run3-e/p_cc5c6eae78
200 | text/html; charset=utf-8 | 5056B | links 39 | words 316 | Io e il lavoro - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/io-e-il-diritto/io-e-il-lavoro | file /tmp/sg-verify-run3-e/p_1dc5526de9
200 | text/html; charset=utf-8 | 4897B | links 40 | words 247 | Io e l'Autorità di protezione - GIUDIZIARIO (POTERI) - Repubblica e Cantone Tici | https://www4.ti.ch/poteri/giudiziario/io-e-il-diritto/io-e-lautorita-di-protezione | file /tmp/sg-verify-run3-e/p_3b38600f72
200 | text/html; charset=utf-8 | 9594B | links 87 | words 1067 | Giudici di pace - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/giustizia-civile/giudici-di-pace | file /tmp/sg-verify-run3-e/p_eda1b22156
200 | text/html; charset=utf-8 | 8542B | links 58 | words 821 | La locazione - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/locazione/la-locazione | file /tmp/sg-verify-run3-e/p_020ec7a605
200 | text/html; charset=utf-8 | 5782B | links 69 | words 458 | Preture - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/giustizia-civile/preture | file /tmp/sg-verify-run3-e/p_435bcc1818
200 | text/html; charset=utf-8 | 6262B | links 42 | words 461 | Presentazione - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/tribunale-dappello/presentazione | file /tmp/sg-verify-run3-e/p_cdc26727f7
200 | text/html; charset=utf-8 | 4880B | links 37 | words 239 | Pubblicazioni - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino | https://www4.ti.ch/poteri/giudiziario/sportello/pubblicazioni | file /tmp/sg-verify-run3-e/p_ad7ecc6c34
200 | text/html | 747B | links 0 | words 2 | FindinfoWeb TI | htt
```

## Step 19: Bash: List TI Sportello topic links and sentenze home
```
cd /tmp/sg-verify-run3-e && python3 - <<'EOF'
import re,html
def links(fn, filt=None):
    t=open(fn,encoding='utf-8',errors='ignore').read()
    out=[]
    for h,txt in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S|re.I):
        txt=html.unescape(re.sub(r'<[^>]+>|\s+',' ',txt)).strip()
        if filt and not re.search(filt,h): continue
        out.append((h,txt[:80]))
    return out
print('--- sportello/temi')
for h,t in links('p_67d6e04833', r'giudiziario|fileadmin|\.pdf'): print(h,'|',t)
print('--- sentenze.ti.ch')
print(open('p_c6c4cea000').read())
EOF
```
Result:
```
--- sportello/temi
/poteri/giudiziario | Potere giudiziario (PG)
/poteri/giudiziario/pg | PG
/poteri/giudiziario/giustizia-civile/presentazione | Giustizia Civile
/poteri/giudiziario/giustizia-penale/presentazione | Giustizia Penale
/poteri/giudiziario/giustizia-amministrativa/presentazione | Giustizia Amministrativa
/poteri/giudiziario/avvocatura-e-notariato/presentazione | Avvocatura e Notariato
/poteri/giudiziario/locazione/la-locazione | Locazione
/poteri/giudiziario/sportello/temi | Sportello
/poteri/giudiziario/sportello/temi | Temi
/poteri/giudiziario/sportello/formulari | Formulari
/poteri/giudiziario/sportello/pubblicazioni | Pubblicazioni
/poteri/giudiziario/avvocatura-e-notariato/registro-cantonale-avvocati | Albo pubblico degli avvocati
/poteri/giudiziario/giustizia-amministrativa/tribunale-di-espropriazione | Fondi, espropriazioni
/poteri/giudiziario/locazione | Locazione, controversie derivanti da contratti
/poteri/giudiziario/giustizia-penale/mediazione-penale-minorile | Mediazione penale minorile
/poteri/giudiziario/giustizia-civile/la-parita-di-sessi | Parità dei sessi, controversie
/poteri/giudiziario/pg | Potere giudiziario
https://twitter.com/share?original_referer=https://www4.ti.ch//poteri/giudiziario/sportello/temi | 
https://www.facebook.com/sharer.php?u=https://www4.ti.ch//poteri/giudiziario/sportello/temi | 
--- sentenze.ti.ch
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<script type="text/javascript">
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');
  ga('create', 'UA-2454755-7', 'auto');
  ga('send', 'pageview');
 </script>

<html>
<head>
	<title>FindinfoWeb TI</title>
	<meta http-equiv="expires" content="0">
	<meta http-equiv="refresh" content="0; URL=/findinfo/ti/index.htm" />
</head>
<body>
</body>
</html>
```

## Step 20: Bash: Probe TI decisions search FindinfoWeb
```
cd /tmp/sg-verify-run3-e && python3 probe.py https://www.sentenze.ti.ch/findinfo/ti/index.htm && f=$(ls -t p_* | head -1) && sed -e 's/<[^>]*>/ /g' $f | tr -s ' \n' | head -c 1500; echo; grep -o -i -E '(href|src|action)="[^"]+"' $f | head -30
```
Result:
```
200 | text/html | 311B | links 0 | words 2 | FindinfoWeb TI | https://www.sentenze.ti.ch/findinfo/ti/index.htm | file /tmp/sg-verify-run3-e/p_5133603458
 
 
 
	 FindinfoWeb TI
```

## Step 21: Bash: Show TI FindinfoWeb index source
```
cd /tmp/sg-verify-run3-e && cat p_5133603458; echo; 
```
Result:
```
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>
<head>
	<title>FindinfoWeb TI</title>
	<meta http-equiv="expires" content="0">
 	<meta http-equiv="refresh" content="0; URL=/findinfo/ti/home.htm" />
</head>
<body>
</body>
</html>
```

## Step 22: Bash: Follow TI FindinfoWeb home page
```
cd /tmp/sg-verify-run3-e && python3 probe.py https://www.sentenze.ti.ch/findinfo/ti/home.htm && f=$(ls -t p_* | head -1) && grep -o -i -E '(href|src|action)="[^"]+"' $f | sort -u | head -40; sed -e 's/<[^>]*>/ /g' $f | tr -s ' \n\t' ' ' | head -c 1500
```
Result:
```
200 | text/html | 1093B | links 0 | words 10 | Sentenze e decisioni - Home - Repubblica e cantone ticino | https://www.sentenze.ti.ch/findinfo/ti/home.htm | file /tmp/sg-verify-run3-e/p_d9689378da
 (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){ (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o), m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m) })(window,document,'script','https://www.google-analytics.com/analytics.js','ga'); ga('create', 'UA-2454755-7', 'auto'); ga('send', 'pageview'); Sentenze e decisioni - Home - Repubblica e cantone ticino
```

## Step 23: Bash: Show TI FindinfoWeb home source
```
cd /tmp/sg-verify-run3-e && cat p_d9689378da
```
Result:
```
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<script type="text/javascript">
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');
  ga('create', 'UA-2454755-7', 'auto');
  ga('send', 'pageview');
 </script>
<html>
<head>
	<title>Sentenze e decisioni - Home - Repubblica e cantone ticino</title>
	<meta http-equiv="expires" content="0">
 	<meta http-equiv="refresh" content="0; URL=/cgi-bin/nph-omniscgi?OmnisPlatform=WINDOWS&WebServerUrl=www.sentenze.ti.ch&WebServerScript=/cgi-bin/nph-omniscgi&OmnisLibrary=JURISWEB&OmnisClass=rtFindinfoWebHtmlService&OmnisServer=JURISWEB,193.246.182.54:6000&Aufruf=home&Template=home.fiw&Schema=TI_WEB&cLanguage=ITA&Parametername=WWWTI&nAnzahlTrefferProSeite=10&nSeite=1" />
</head>
<body>
</body>
</html>
```

## Step 24: Bash: Fetch TI FindinfoWeb home CGI
```
cd /tmp/sg-verify-run3-e && python3 probe.py 'https://www.sentenze.ti.ch/cgi-bin/nph-omniscgi?OmnisPlatform=WINDOWS&WebServerUrl=www.sentenze.ti.ch&WebServerScript=/cgi-bin/nph-omniscgi&OmnisLibrary=JURISWEB&OmnisClass=rtFindinfoWebHtmlService&OmnisServer=JURISWEB,193.246.182.54:6000&Aufruf=home&Template=home.fiw&Schema=TI_WEB&cLanguage=ITA&Parametername=WWWTI&nAnzahlTrefferProSeite=10&nSeite=1' && f=$(ls -t p_* | head -1) && sed -e 's/<script.*<\/script>//g; s/<[^>]*>/ /g' $f | tr -s ' \n\t' ' ' | head -c 1200
```
Result:
```
200 | text/html; charset=iso-8859-1 | 14995B | links 26 | words 474 | Sentenze e decisioni - Repubblica e Cantone Ticino | https://www.sentenze.ti.ch/cgi-bin/nph-omniscgi?OmnisPlatform=WINDOWS&WebServerUrl=www.sentenze.ti.ch&WebServerScript=/cgi-bin/nph-omniscgi&OmnisLibrary=JURISWEB&OmnisClass=rtFindinfoWebHtmlService&OmnisServer=JURISWEB,193.246.182.54:6000&Aufruf=home&Template=home.fiw&Schema=TI_WEB&cLanguage=ITA&Parametername=WWWTI&nAnzahlTrefferProSeite=10&nSeite=1 | file /tmp/sg-verify-run3-e/p_4e4fcc34b4
sed: RE error: illegal byte sequence
 
 
 
 
 Sentenze e decisioni - Repubblica e Cantone Ticino 
 
 
 
 
 
 
 
 
 
 
 
 
 AIUTO &nbsp;&nbsp;&nbsp;
 RICERCA 
 
 
 
 
 PG 
 &gt; Sentenze e decisioni
 
 
 
 
 
 
 
 
 
 
 
 Home 
 
 
 Cerca 
 
 
 Categorie 
 
 
 Abbreviazioni 
 
 
 Istruzioni 
 
 
 Contatti
```

## Step 25: Bash: Grep TI guidance pages for fee and cost mentions
```
cd /tmp/sg-verify-run3-e && for f in p_063df9bc8c p_cc5c6eae78 p_1dc5526de9 p_3b38600f72 p_eda1b22156 p_020ec7a605 p_435bcc1818; do echo "=== $f"; python3 - "$f" <<'EOF'
import re,html,sys
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
m=re.search(r'<title>(.*?)</title>',t,re.S); print(m.group(1).strip()[:80])
body=re.sub(r'<script.*?</script>|<style.*?</style>',' ',t,flags=re.S|re.I)
txt=html.unescape(re.sub(r'<[^>]+>',' ',body)); txt=re.sub(r'\s+',' ',txt)
for kw in ['CHF','fr\.','tass','spese','cost','gratuit','anticip','tariff']:
    for mm in re.finditer(kw,txt,re.I):
        print('  ',kw,'::',txt[max(0,mm.start()-150):mm.end()+150]); break
for h in re.findall(r'href="([^"]+\.pdf[^"]*)"',t): print('  PDF',h)
EOF
done
```
Result:
```
=== p_063df9bc8c
Io e il divorzio - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino
=== p_cc5c6eae78
Io e la locazione - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino
=== p_1dc5526de9
Io e il lavoro - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino
  PDF /fileadmin/POTERI/GIUDIZIARIO/IoDiritto/opuscolo_lavoro.pdf
=== p_3b38600f72
Io e l'Autorità di protezione - GIUDIZIARIO (POTERI) - Repubblica e Cantone Tici
=== p_eda1b22156
Giudici di pace - GIUDIZIARIO (POTERI) - Repubblica e Cantone Ticino
   fr\. :: e competenze del Giudice di Pace Il Giudice di pace: funge da autorità di conciliazione nelle controversie patrimoniali fino a un valore litigioso di fr. 5’000, con possibilità di sottoporre alle parti una proposta di giudizio; giudica in prima istanza le cause patrimoniali fino a un valore litigioso d
   tass :: zione e fallimenti La Camera Vigilanza sull'operato degli uffici Potere disciplinare e regolamentare Ispettorato di esecuzione e fallimenti Circolari Tassazioni Riserva di proprietà Pegno del Bestiame Ricorsi in cause giudiziarie Fallimenti internazionali Tabella dei minimi d'esistenza Basi Legali CEF P
   cost :: olo 271 LEF Istanza di divieto giudiziale Giurisprudenza Sentenze del Tribunale federale Sentenze del Tribunale d’appello Legislazione Leggi federali Costituzione federale della Confederazione Svizzera del 18 aprile 1999 Codice civile svizzero del 10 dicembre 1907 Legge federale di complemento del Codic
   gratuit :: ogorno --- Seleziona la località per conoscere l'ufficio competente Link utili Riorganizzazione delle Giudicature di pace Moduli/formulari Istanza di gratuito patrocinio in virtù dell'articolo 119 CPC Domanda di rigetto dell'opposizione in virtù degli articoli 80/82 LEF Azione semplificata in virtù dell'ar
   tariff :: i applicazione del codice di diritto processuale civile svizzero del 24 giugno 2010 Legge sugli onorari dei magistrati del 14 maggio 1973 Legge sulla tariffa giudiziaria del 30 novembre 2010 Regolamento sulla tariffa per i casi di patrocinio d’ufficio e di assistenza giudiziaria e per la fissazione delle 
  PDF /fileadmin/POTERI/GIUDIZIARIO/GiudiciPace/MOD20110104-Istanza-gratuito-patrocinio.pdf
  PDF /fileadmin/POTERI/GIUDIZIARIO/GiudiciPace/MOD20110104-Domanda-rigetto-opposizione.pdf
  PDF /fileadmin/POTERI/GIUDIZIARIO/GiudiciPace/MOD20110104-Azione-semplificata.pdf
  PDF /fileadmin/POTERI/GIUDIZIARIO/GiudiciPace/MOD20110104-Instanza-conciliazione-202CPC.pdf
  PDF /fileadmin/POTERI/GIUDIZIARIO/Giu
```

## Step 26: Bash: Extract main text of TI divorce and tenancy pages
```
cd /tmp/sg-verify-run3-e && python3 - <<'EOF'
import re,html
for fn in ['p_063df9bc8c','p_cc5c6eae78','p_020ec7a605']:
    t=open(fn,encoding='utf-8',errors='ignore').read()
    body=re.sub(r'<script.*?</script>|<style.*?</style>',' ',t,flags=re.S|re.I)
    m=re.search(r'id="maincontent"(.*)',body,re.S)
    txt=html.unescape(re.sub(r'<[^>]+>',' ',m.group(1) if m else body)); txt=re.sub(r'\s+',' ',txt)
    print('===',fn, txt[:1400]); print()
EOF
```
Result:
```
=== p_063df9bc8c > Io e il divorzio Difficoltà familiari, separazione, divorzio: come fare? A chi rivolgersi? Per avere maggiori informazioni e dettagli in merito alla tematica vi invitiamo a consultare i seguenti siti: Portale Internet svizzero: informazioni sulla procedura di divorzio Divorzio e diritto Nel Cantone Ticino le cause relative al diritto delle persone e della famiglia (misure di protezione dell’unione coniugale, separazione, divorzio, modifica di una precedente sentenza di divorzio o di separazione) sono trattate dal Pretore del luogo di domicilio dell’uno o dell’altro coniuge secondo una procedura particolare. Ulteriori informazioni Registro cantonale degli avvocati del Cantone Ticino Divisione dell'azione sociale Applicazione mobile Per un accesso diretto alle informazioni e ai servizi offerti dall'Amministrazione Cantonale, sono disponibili le seguenti applicazioni per "smartphone" da installare sui vostri dispositivi personali. Primi soccorsi Vedi in App Store Vedi in Google Play PescaTI Vedi in App Store Vedi in Google Play RL Ticino Vedi in App Store Vedi in Google Play Polizia e Territorio Vedi in App Store Vedi in Google Play Social media L'Amministrazione cantonale è presente su Facebook, Instagram, X, Youtube, WhatsApp e Threema con diversi profili legati a servizi e uffici. Per maggiori informazioni potete visitare questa pagina . Condividi È possibile condividere ques

=== p_cc5c6eae78 > Io e la locazione Come fare in caso di litigio tra proprietario e inquilino? Dove rivolgersi? Chi decide? In caso di vertenze tra proprietario di casa (locatore) o amministrazione e inquilino (conduttore) ci si deve prima rivolgere obbligatoriamente agli Uffici di conciliazione in materia di locazione . Nella pagina degli Uffici di conciliazione in materia di locazione si trovano le indicazioni sulle competenze degli Uffici e su come prendere contatto con l’Ufficio competente in un singolo caso (luogo, numeri di telefono, orai, ecc.). A disposizione ci sono inoltre moduli ufficiali per la notifica di aumento e di disdetta, la raccolta di giurisprudenza e diversa altra documentazione utile. Pubblicazioni Raccolta di giurisprudenza in materia di locazione Applicazione mobile Per un accesso diretto alle informazioni e ai servizi offerti dall'Amministrazione Cantonale, sono disponibili le seguenti applicazioni per "smartphone" da installare sui vostri dispositivi personali. Primi soccorsi Vedi in App Store Vedi in Google Play PescaTI Vedi in App Stor
```

## Step 27: Bash: Test TI site search endpoint
```
cd /tmp/sg-verify-run3-e && python3 probe.py 'https://www4.ti.ch/tich/cerca-nel-sito/ricerca/?q=tariffa+giudiziaria' 'https://www4.ti.ch/tich/cerca-nel-sito/ricerca/?query=tariffa+giudiziaria' && f=$(ls -t p_* | head -2 | tail -1) && grep -o -i -E '(action|src)="[^"]+"' $f | head; grep -i -o -E 'google|gsa|cse|search[^"]{0,60}' $f | sort | uniq -c | head -20
```
Result:
```
200 | text/html; charset=utf-8 | 5126B | links 33 | words 170 | Ricerca | https://www4.ti.ch/tich/cerca-nel-sito/ricerca/?q=tariffa+giudiziaria | file /tmp/sg-verify-run3-e/p_3e5c75e112
200 | text/html; charset=utf-8 | 5128B | links 33 | words 170 | Ricerca | https://www4.ti.ch/tich/cerca-nel-sito/ricerca/?query=tariffa+giudiziaria | file /tmp/sg-verify-run3-e/p_238d918033
src="/ruxitagentjs_ICA15789NPRTUVXfqrux_10343260715123811.js"
src="/typo3temp/assets/js/e9e07c5ca0.js?1672136945"
src="https://www.googletagmanager.com/ns.html?id=GTM-PSV3WQ6"
src="/typo3conf/ext/theme/Resources/Public/images/comune/ti-ch.png"
src="//www4.ti.ch/fileadmin/HOME/images/MedicoCantonale.png"
src="//www4.ti.ch/fileadmin/HOME/images/pescati.png"
src="//www4.ti.ch/fileadmin/HOME/images/RaccoltaLeggi.png"
src="//www4.ti.ch/fileadmin/HOME/images/polizia_e_territorio.png"
src="/typo3conf/ext/theme/Resources/Public/bowercomponents/jquery/dist/jquery.js?1776399229"
src="/typo3conf/ext/theme/Resources/Public/js/bootstrap.min.js?1776399231"
   8 Google
   2 Gsa
  14 google
   3 search
   1 search=
```

## Step 28: ToolSearch: 
```
{"query": "select:WebSearch,WebFetch", "max_results": 2}
```
Result:
```


```

> Running WebSearches in parallel for breadth across the three cantons.

## Step 29: WebSearch: 
```
{"query": "Obergericht Graub\u00fcnden Justizreform 2025 Kantonsgericht Verwaltungsgericht zusammengelegt Website"}
```
Result:
```
Web search results for query: "Obergericht Graubünden Justizreform 2025 Kantonsgericht Verwaltungsgericht zusammengelegt Website"

Links: [{"title":"Kanton Graubünden: Neues Obergericht nimmt am 1. Januar 2025 Rechtsprechungstätigkeit auf","url":"https://www.weblaw.ch/community/personalia/2024/graubuenden-neues-obergericht.html"},{"title":"Kantonsgericht von Graubünden Verwaltungsgericht Graubünden EINGANG","url":"https://cdws-staka-gr.gr.ch/cdws/files/1863bd3011484d469ca2be649dce224f-332/1/pdf"},{"title":"Obergericht - Über uns - Aufgaben","url":"https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/"},{"title":"Aufgaben","url":"https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben.html"},{"title":"Neues Bündner Obergericht nimmt Gestalt an | Engadiner Post/Posta Ladina","url":"https://www.engadinerpost.ch/news/2024/11/07/Neues-Buendner-Obergericht-nimmt-Gestalt-an"},{"title":"Abstimmungen Kanton Graubünden - Ein Obergericht soll Justiz effizienter machen - News - SRF","url":"https://www.srf.ch/news/abstimmungen-27-november/abstimmungen-kanton-graubuenden-ein-obergericht-soll-justiz-effizienter-machen"},{"title":"Graubünden: ein historisches Gebäude für das Obergericht","url":"https://www.weblaw.ch/en/community/personalia/2025/obergericht-graubuenden.html"},{"title":"Infos","url":"https://www.justiz-gr.ch/gerichte/obergericht/aktuelles/infos/"},{"title":"Erfolgreicher Start für das Obergericht","url":"https://grheute.ch/erfolgreicher-start-fuer-das-obergericht"},{"title":"Das Obergericht hat jetzt ins Staatsgebäude gezügelt","url":"https://grheute.ch/das-obergericht-hat-jetzt-ins-staatsgebaeude-gezuegelt"}]

Based on the search results, here's what I found regarding the Obergericht Graubünden Justizreform 2025:

## Key Information about the Justice Reform 2025

The new Supreme Court of the Canton Graubünden (Obergericht) was created through the consolidation of the District Court and Administrative Court, and began its judicial work at the beginning of January 2025.

The court consists of 14 judges, and the first president in Graubünden's history is Remo Cavegn, the former district court president.

This represents a milestone in Graubünden's judicial history, as new structures are being created both in the area of jurisdiction and court administration.

## Physical Location

Initially, court operations were conducted at two locations in Chur (Obere Plessurstrasse 1 and Poststrasse 14), but since late October, the court has been unit
```

## Step 30: WebSearch: 
```
{"query": "Tribunal cantonal Valais site officiel jurisprudence recherche d\u00e9cisions"}
```
Result:
```
Web search results for query: "Tribunal cantonal Valais site officiel jurisprudence recherche décisions"

Links: [{"title":"Tribunal Cantonal - tribunaux - vs.ch","url":"https://www.vs.ch/web/tribunaux/tribunal-cantonal"},{"title":"2C_559/2023 – Décision du 01.05.2024 – Arrêts du TF – Jurisprudence – Droit pour la pratique","url":"https://droitpourlapratique.ch/decision/90659/2024"},{"title":"Jurisprudence du Tribunal cantonal et du TRIPAC | État de Vaud","url":"https://www.vd.ch/justice/jurisprudence-et-lois/jurisprudence-du-tribunal-cantonal-et-du-tripac"},{"title":"Jurisprudence - tribunaux - vs.ch","url":"https://www.vs.ch/web/tribunaux/jurisprudence"},{"title":"Aide à la recherche | État de Vaud","url":"https://www.vd.ch/justice/jurisprudence-et-lois/jurisprudence-du-tribunal-cantonal-et-du-tripac/aide-a-la-recherche"},{"title":"Accueil - tribunaux - vs.ch","url":"https://www.vs.ch/web/tribunaux"},{"title":"Search for cases | CISG-online.org","url":"https://cisg-online.org/search-for-cases?caseId=7942"},{"title":"Jurisprudence du Tribunal cantonal","url":"https://jurisprudence.ne.ch/"},{"title":"Constituent Assembly of Valais","url":"https://en.wikipedia.org/wiki/Constituent_Assembly_of_Valais"}]

Based on the search results, here's what I found regarding the Tribunal cantonal Valais and its jurisprudence:

## Official Site and Jurisprudence

The jurisprudence of Valais courts published online presents a selection of decisions chosen based on their interest for knowledge of law and responds to a need for information of litigants and aims at better understanding in their part in the application of law.

## Publication of Decisions

According to Article 38 of the law on the organization of Justice of February 11, 2009, the Cantonal Court publishes important decisions and judgments for knowledge of law rendered by the Civil and Criminal Courts, by the Court of Public Law and by the Court of Social Insurance of the Cantonal Court, as well as by first instance jurisdictions. The important judgments are generally placed online within three months following their entry into force.

## Official Website

The official website for the Tribunal cantonal Valais is available at **https://www.vs.ch/web/tribunaux/**, with a dedicated jurisprudence section at **https://www.vs.ch/web/tribunaux/jurisprudence**.


REMINDER: You MUST include the sources above in your response to the user using markdown hyperlinks.
```

## Step 31: WebSearch: 
```
{"query": "site:ti.ch cani detenzione ufficio del veterinario cantonale"}
```
Result:
```
Web search results for query: "site:ti.ch cani detenzione ufficio del veterinario cantonale"

Links: [{"title":"Ufficio del veterinario cantonale Scheda informativa","url":"https://www4.ti.ch/fileadmin/DSS/DSP/UVC/pdf/PA/TenutaProf/Attivita_professionali_con_animali_domestici.pdf"},{"title":"CAN - Raccolta delle leggi del Cantone Ticino","url":"https://m3.ti.ch/CAN/RLeggi/public/index.php/raccolta-leggi/legge/num/478"},{"title":"482.310 Regolamento sui cani (RCani) - 30 dicembre 2025","url":"https://m3.ti.ch/CAN/RLeggi/public/index.php/raccolta-leggi/legge/num/869"},{"title":"Ufficio - UVC (DSS) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/dss/dsp/uvc/ufficio"},{"title":"Razze soggette a restrizioni - UVC (DSS) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/dss/dsp/uvc/temi/tenuta-di-animali/cani/razze-soggette-a-restrizioni"},{"title":"Home - UVC (DSS) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/dss/dsp/uvc/home"},{"title":"Cani","url":"https://www.blv.admin.ch/it/cani"},{"title":"CAN - Raccolta delle leggi del Cantone Ticino","url":"https://www3.ti.ch/CAN/RLeggi/public/raccolta-leggi/legge/numero/8.3.1.2"},{"title":"482.300 Legge sui cani - 19 febbraio 2008","url":"https://m3.ti.ch/CAN/RLeggi/public/index.php/raccolta-leggi/legge/num/479"}]

Ho completato la ricerca web per il tuo query. I risultati mostrano informazioni relative alla detenzione di cani e alle competenze dell'Ufficio del veterinario cantonale (UVC) nel Canton Ticino.

Alcuni dei risultati più rilevanti includono:

1. **Disposizioni sulla detenzione di cani**: La detenzione in gruppo di animali non provenienti dallo stesso detentore è consentita unicamente in presenza di una persona responsabile.

2. **Strutture per pensioni e rifugi**: Una pensione o rifugio per animali è un centro di detenzione che prende a pensione o accoglie e accudisce cani o gatti per periodi di tempo limitati o a cui il proprietario ha rinunciato o che sono stati abbandonati.

3. **Autorizzazioni per attività professionali**: L'autorizzazione dell'ufficio del veterinario cantonale (UVC) è obbligatoria per le attività professionali con cani e gatti che coinvolgono più di cinque animali.

4. **Contatti dell'UVC**: L'Ufficio del veterinario cantonale si trova a Via Dogana 16 a 6500 Bellinzona, con il veterinario cantonale Luca Bacciarini raggiungibile al numero +41 91 814 41 00.

I risultati includono anche informazioni sulla legislazione ticinese riguardante le razze di cani soggett
```

## Step 32: WebSearch: 
```
{"query": "site:ti.ch calendario scolastico vacanze scolastiche"}
```
Result:
```
Web search results for query: "site:ti.ch calendario scolastico vacanze scolastiche"

Links: [{"title":"ANNO SCOLASTICO 2025/2026 Vacanze scolastiche SECONDO SEMESTRE SETTEMBRE","url":"https://www.cptmendrisio.ti.ch/fileadmin/SP/cptmendrisio/files/orari_calendario_scolastico/Calendario-scolastico-2025-2026.pdf"},{"title":"VACANZE SCOLASTICHE giorno giorno giorno 1 FESTA NAZIONALE S M G OGNISSANTI D M","url":"https://www.cpttrevano.ti.ch/fileadmin/SP/cpttrevano/files/Orari_e_calendario_scolastico/Calendario_scolastico_2025-2026.pdf"},{"title":"Calendario scolastico","url":"https://www.liceomendrisio.ti.ch/allievi/calendario-interno/"},{"title":"Calendario scolastico 2021/22 e 2022/23","url":"https://locarno2.sm.edu.ti.ch/wp-content/uploads/sites/32/2022/01/Calendari-scolastici-21-22-23-24.pdf"},{"title":"Calendario scolastico - INFOGIOVANI (TICH)","url":"https://www4.ti.ch/generale/infogiovani/formazione-e-lavoro/scuole/calendario-scolastico"},{"title":"CENTRO SCOLASTICO PER LE INDUSTRIE ARTISTICHE ...","url":"https://www.csia.ti.ch/fileadmin/SP/csia/files/orari_calendario_scolastico/CSIA_Calendario2025-2026.pdf"},{"title":"Calendario scolastico 2027-2028","url":"https://m4.ti.ch/fileadmin/DECS/calendario_scolastico/Calendario_scolastico_2027-2028.pdf"},{"title":"Calendario scolastico 2026-2027","url":"https://m4.ti.ch/fileadmin/DECS/calendario_scolastico/Calendario_scolastico_2026_2027.pdf"},{"title":"Calendario scolastico 2024/2025","url":"https://www4.ti.ch/decs/cosa-facciamo/calendario-scolastico/2024-2025"},{"title":"Calendario scolastico 2025/2026","url":"https://www4.ti.ch/decs/cosa-facciamo/calendario-scolastico/2025-2026"}]

I've performed the web search with your query "site:ti.ch calendario scolastico vacanze scolastiche". The search returned several results related to school calendars and school holidays in Ticino (ti.ch). Here's what I found:

**Available Results:**

1. **CPT Mendrisio** - School calendar for 2025/2026 (PDF)
2. **CPT Trevano** - School calendar 2025/2026 showing school holidays (PDF)
3. **Liceo Mendrisio** - Calendario scolastico page with holiday information
4. **Locarno2 Secondary School** - School calendars for 2021/22 and 2022/23 with holiday dates specified
5. **CSIA (Centro Scolastico per le Industrie Artistiche)** - School calendar 2025/2026 with vacation periods listed

**Key Information Found:**

From the CSIA calendar for 2025/2026, school holidays include autumn break from November 1-9, 2025, Christmas holidays from 
```

## Step 33: WebSearch: 
```
{"query": "site:ti.ch sezione della circolazione tariffe immatricolazione"}
```
Result:
```
Web search results for query: "site:ti.ch sezione della circolazione tariffe immatricolazione"

Links: [{"title":"www.ti.ch/circolazione Aggiornamento luglio 2025 Repubblica e Cantone Ticino","url":"https://www4.ti.ch/fileadmin/DI/Formulari/SC/comuni/MOD20050802-cessione-targhe-controllo-immatricolazioni.pdf"},{"title":"Sezione della circolazione","url":"https://www4.ti.ch/di/sc/home/"},{"title":"www.ti.ch/circolazione Aggiornamento dicembre 2020 Repubblica e Cantone Ticino","url":"https://www4.ti.ch/fileadmin/DI/Formulari/SC/conducenti/ciclomotori/Richiesta-immatricolazione-ciclomotori.pdf"},{"title":"Immatricolazione di un veicolo nuovo - SC (DI) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/di/sc/veicoli/immatricolazioni/immatricolazione-di-un-veicolo-nuovo"},{"title":"Immatricolazioni - SC (DI) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/di/sc/veicoli/immatricolazioni"},{"title":"Targhe d'esportazione - SC (DI) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/di/sc/veicoli/targhe-desportazione"},{"title":"Repubblica e Cantone Ticino Dipartimento delle istituzioni 1 di 6","url":"https://m4.ti.ch/fileadmin/DI/SC/asta_targhe/Condizioni-Vendita-targhe.pdf"},{"title":"Imposta di circolazione - SC (DI) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/di/sc/veicoli/imposta-di-circolazione"},{"title":"Ufficio amministrativo - SC (DI) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/di/sc/contatti/ufficio-amministrativo"},{"title":"Formulari - SC (DI) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/di/sc/sportello/formulari"}]

I've performed the web search for "site:ti.ch sezione della circolazione tariffe immatricolazione". The search returned several results from the Ticino cantonal administration website related to vehicle registration and circulation matters.

The results include:

1. **Sezione della circolazione** (Section of Circulation) - The Section controls and regulates the circulation of vehicles and vessels (registrations), checks their safety (inspections), and issues related driving licenses upon passing driving exams.

2. **Registration services** - The Registration Service handles first registration of vehicles, vehicle changes, registration of transferable vehicles, plate deposits, reserve vehicle registration, cantonal changes, vehicles from abroad, vehicle export, vehicle import, temporary plates and licenses, and plate reprints.

3. **Contact information** - The Sezione della circolaz
```

## Step 34: WebSearch: 
```
{"query": "site:ti.ch istruzioni compilazione dichiarazione d'imposta persone fisiche divisione contribuzioni"}
```
Result:
```
Web search results for query: "site:ti.ch istruzioni compilazione dichiarazione d'imposta persone fisiche divisione contribuzioni"

Links: [{"title":"per la compilazione della dichiarazione d’imposta delle persone giuridiche","url":"https://m4.ti.ch/fileadmin/DFE/DC/DOC-IPG/2018/2018_Istruzioni_PG.pdf"},{"title":"Repubblica e Cantone Ticino - Dichiarazione d’imposta 2024 delle persone fisiche","url":"https://www4.ti.ch/tich/area-media/comunicati/dettaglio-comunicato?NEWS_ID=249038"},{"title":"Creazione di una nuova dichiarazione d’imposta - istruzioni","url":"https://www4.ti.ch/fileadmin/DFE/DC/DOC-IPG/2024/4_-_Istruzioni_eTaxPG.pdf"},{"title":"Imposte persone fisiche - Istruzioni 2025","url":"https://www4.ti.ch/dfe/dc/dichiarazione/istruzioni-pf/istr-pf-attuale?noMobile=1&cHash=dbf92ced9c67d60b7abcc5155cbc5b9d"},{"title":"Informazioni utili Dichiarazione d’imposta 2025","url":"https://www4.ti.ch/fileadmin/DFE/DC/DOC-IPF/2025/Istruzioni/Flyer_2025.pdf"},{"title":"Imposta cantonale Imposta federale diretta Istruzioni 2024 per la compilazione","url":"https://m4.ti.ch/fileadmin/DFE/DC/DOC-IPG/2024/2_-_Istruzioni_Modulo_C.pdf"},{"title":"per la compilazione della dichiarazione d’imposta delle persone giuridiche","url":"https://www4.ti.ch/fileadmin/DFE/DC/DOC-IPG/2022/2022_Istruzioni_PG.pdf"},{"title":"Imposte persone giuridiche - Istruzioni 2023","url":"https://www4.ti.ch/dfe/dc/dichiarazione/istruzioni-pg/istr-pg-attuale/?noMobile=1"},{"title":"Formulari - DC (DFE) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/dfe/dc/dichiarazione/imposte-alla-fonte-1/formulari"}]

I've performed the web search for you. The results show several documents from the Ticino Canton (ti.ch) related to tax declarations. Here's what I found:

**Key Results:**

1. Instructions for compiling tax declarations for individuals (persone fisiche) are available, accessible through www.ti.ch/etax in the "Instructions and deductions table" section.

2. The Division of Contributions (Divisione delle contribuzioni) is responsible for sending tax declaration modules to taxpayers for compilation of their tax declarations for individuals.

3. The 2025 tax declaration instructions booklet is no longer included in paper form, but is available online to reduce paper usage.

4. The eTax software program allows electronic transmission of tax declarations and can be downloaded free of charge from www.ti.ch/etax.

The search results contain references to official instruction documents from the 
```

> Found the real GR court host paths (www.justiz-gr.ch/gerichte/obergericht/) and the VS courts under www.vs.ch/web/tribunaux. Next search batch.

## Step 35: WebSearch: 
```
{"query": "site:gr.ch Hunde Hundehaltung Amt f\u00fcr Lebensmittelsicherheit und Tiergesundheit"}
```
Result:
```
Web search results for query: "site:gr.ch Hunde Hundehaltung Amt für Lebensmittelsicherheit und Tiergesundheit"

Links: [{"title":"Amt für Lebensmittelsicherheit und Tiergesundheit","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/tiere/hundewesen/Documents/1960%20GL_Merkblatt%20bewilligungspflichtige%20Hundehaltung%20im%20Kanton%20Glarus.pdf"},{"title":"Kontakt - Amt für Lebensmittelsicherheit und Tiergesundheit","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/Seiten/Kontakt.aspx"},{"title":"08.09.2012/tbu Seite 1 von 1 Amt für Lebensmittelsicherheit und Tiergesundheit","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/tiere/tierschutz/Documents/TSch_04.1a_Wildtiere_Frettchen_Information_%C3%9Cberblick_20120908ok_erl.pdf"},{"title":"Wegleitung Herdenschutzhunde Kanton Graubünden","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/lbbz/aktuelles/Documents/Wegleitung%20Herdenschutzhunde%20%20GR%202025_DEF.pdf"},{"title":"Tiergesundheit - Tiergesundheit","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/tiere/Seiten/default.aspx"},{"title":"Tierschutz - Tierschutz","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/tiere/tierschutz/Seiten/default.aspx"},{"title":"Botschaft der Regierung an den Grossen Rat Heft Nr. 2 / 2007– 2008 Inhalt Seite","url":"https://www.gr.ch/Botschaften/2007/02_2007-08.pdf"},{"title":"Kynologischer Ausbildungslehrgang (KAL)","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/tiere/hundewesen/Documents/Erkl%C3%A4rung%20KAL%20f%C3%BCr%20Homepage.pdf"},{"title":"A L T Amt für Lebensmittelsicherheit und Tiergesundheit","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/ueberuns/Jahresberichte/Jahresbericht%202015.pdf"},{"title":"Auftrag Danuser betreffend Einführung obligatorischer Sachkundenachweis für Hundehalter","url":"https://www.gr.ch/DE/institutionen/parlament/PV/Seiten/20170614Danuser09.aspx"}]

I've successfully performed the web search for your query on the Graubünden (gr.ch) website about dog keeping and the Food Safety and Animal Health Office.

The search returned several relevant results:

1. A document from the Office for Food Safety and Animal Health (Amt für Lebensmittelsicherheit und Tiergesundheit) regarding permit-required dog keeping in Canton Glarus, which includes information on requirements such as passing an obedience test and being at least 18 years old to provide guarantee for safe and animal welfare-compliant keeping of the ani
```

## Step 36: WebSearch: 
```
{"query": "site:gr.ch Steuerbuch Praxis Steuerverwaltung Graub\u00fcnden"}
```
Result:
```
Web search results for query: "site:gr.ch Steuerbuch Praxis Steuerverwaltung Graubünden"

Links: [{"title":"Praxisfestlegung Steuerverwaltung Graubünden 1.12.2024 ha/te 045-01.doc P","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/Grundstckgewinnsteuer/045-01.pdf"},{"title":"Praxisfestlegung Steuerverwaltung Graubünden 1.1.2025 He/AJ 122-01.doc P","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/Verfahren/122-01.pdf"},{"title":"Praxisfestlegung Steuerverwaltung Graubünden 27.2.2026 He/te 036-o-01.doc P","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/PraxisEinkommenVermgen/036-o-01.pdf"},{"title":"Praxisfestlegung Steuerverwaltung Graubünden 1.9.2025 He/te 174-03-01.docx P","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/Verfahren/174-03-01.pdf"},{"title":"Praxisfestlegung Steuerverwaltung Graubünden 1.9.2025 He/te 145-01.doc P","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/Verfahren/145-01.pdf"},{"title":"Praxisfestlegung Steuerverwaltung Graubünden 1.2.2025 He/te 057-01.doc P","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/PraxisEinkommenVermgen/057-01.pdf"},{"title":"Praxis - Praxis - Dokumentation","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/Seiten/default.aspx"},{"title":"Willkommen - Über uns","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/ueberuns/Seiten/default_bak.aspx"},{"title":"Willkommen bei der Steuerverwaltung","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/Seiten/startseite.aspx"}]

The search returned several results from the Graubünden Tax Administration (Steuerverwaltung Graubünden). Here's what I found:

The Steuerverwaltung Graubünden publishes practice guidelines ("Praxisfestlegungen") on selected topics and provisions for various types of taxes. These practice guidelines regularly include references to circulars from the federal tax administration (EStV), the Swiss tax conference, specialized literature, and court rulings.

The search results show multiple practice guidelines (Praxisfestlegungen) available on the gr.ch domain, covering topics such as:

- Real estate capital gains tax (Grundstückgewinnsteuer)
- Tax secrecy procedures (Steuergeheimnis)
- Training and continuing education costs (Aus- und Weiterbildungskosten)
- Tax-free self-disclosure and simplified re
```

## Step 37: WebSearch: 
```
{"query": "site:gr.ch Schulferien Volksschule Graub\u00fcnden Ferienordnung Gemeinden"}
```
Result:
```
Web search results for query: "site:gr.ch Schulferien Volksschule Graubünden Ferienordnung Gemeinden"

Links: [{"title":"BR 421.000 - Gesetz für die Volksschulen des Kantons Graubünden - Kanton Graubünden - Erlasssammlung","url":"https://www.gr-lex.gr.ch/app/de/texts_of_law/421.000"},{"title":"Schul- und Ferienplan Schuljahr 2025/26 Kanton Graubünden","url":"https://www.gr.ch/DE/institutionen/verwaltung/ekud/avs/Volksschule/SB_Ferienplaene_20252026_de.pdf"},{"title":"BR 421.010 - Verordnung zum Volksschulgesetz - Kanton Graubünden - Erlasssammlung","url":"https://www.gr-lex.gr.ch/app/de/texts_of_law/421.010"},{"title":"Schule / Schulferien","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/soa/familie/kinderbetreuung/Seiten/schulzeit-schulferien.aspx"},{"title":"Schul- und Ferienplan Schuljahr 2026/27 Kanton Graubünden","url":"https://www.gr.ch/DE/institutionen/verwaltung/ekud/avs/Volksschule/SB_Ferienplaene_2026_2027_de.pdf"},{"title":"421.000 Gesetz für die Volksschulen des Kantons Graubün- den (Schulgesetz)","url":"https://www.gr-lex.gr.ch/api/de/versions/915/pdf_file"},{"title":"Schul- und Ferienplan der Bündner Kantonsschule","url":"https://www.gr.ch/DE/institutionen/verwaltung/ekud/ahb/mittelschulen/uberuns/bks/ferienplan_BKS/Seiten/default.aspx"},{"title":"Ferienplan für das aktuelle Schuljahr - Chur","url":"https://www.gr.ch/DE/institutionen/verwaltung/ekud/ahb/bks/uberuns/ferienplan/Seiten/default.aspx"},{"title":"Verdabbio","url":"https://en.wikipedia.org/wiki/Verdabbio"}]

Based on the web search results, I found several relevant sources related to school holidays and vacation planning for primary schools (Volksschule) in the Canton of Graubünden:

**Key Findings:**

1. **School and Vacation Plans**: School and vacation plans are available for the school year 2025/26 for the Canton of Graubünden, and also for the school year 2026/27. These appear to be available as PDF documents on the official Graubünden website.

2. **Legal Framework**: The school year begins after summer holidays, earliest mid-August, and the terms for the school year and holidays are determined by the school board.

3. **Holiday Care Services**: During school holidays, individual municipalities offer care services for school-age children, which take place during individual weeks or the entire school holidays.

4. **Responsibility**: Responsibility for these services lies with the respective school authorities.

The search results point to the official gr.ch website wh
```

## Step 38: WebSearch: 
```
{"query": "Strassenverkehrsamt Graub\u00fcnden Geb\u00fchren Fahrzeugausweis Website stva"}
```
Result:
```
Web search results for query: "Strassenverkehrsamt Graubünden Gebühren Fahrzeugausweis Website stva"

Links: [{"title":"Fahrzeugausweis - Fahrzeugausweise","url":"https://www.gr.ch/DE/institutionen/verwaltung/djsg/stva/fahrzeugausweis/fahrzeugausweise/Seiten/default.aspx"},{"title":"Über uns - Über uns - Strassenverkehrsamt des Kantons Graubünden","url":"https://www.gr.ch/DE/institutionen/verwaltung/djsg/stva/ueberuns/Seiten/default.aspx"},{"title":"Gebühren - Steuern und Gebühren","url":"https://www.gr.ch/DE/institutionen/verwaltung/djsg/stva/ueberuns/steuern-gebuehren/Seiten/Geb%C3%BChrenverordnung.aspx"},{"title":"Strassenverkehrsamt","url":"https://stva.tg.ch/"},{"title":"Strassenverkehrsamt Graubünden in Chur, Ringstrasse 2","url":"https://tel.help.ch/f.cfm?key=163847&firma=Strassenverkehrsamt-Graubuenden&ort=Chur"},{"title":"Strassenverkehrsamt Graubünden - Basel BS","url":"https://baselbs.ch/strassenverkehrsamt-graubuenden/"},{"title":"Koordinaten aller Strassenverkehrsämter - Fahrzeugausweise","url":"https://fahrzeugausweise.ch/strassenverkehrsaemter/"},{"title":"Strassenverkehrsamt Graubünden – Chur, Samedan und alle Prüforte - DriveLab","url":"https://drivelab.ch/strassenverkehrsamt-graubuenden/"},{"title":"Willkommen beim Strassenverkehrsamt","url":"https://www.gr.ch/DE/institutionen/verwaltung/djsg/stva/Seiten/Start.aspx"}]

Based on the search results, here's the information about the Strassenverkehrsamt (Road Traffic Office) Graubünden:

## Official Website
The official website is www.stva.gr.ch

## Contact Information
The address is Ringstrasse 2, 7000 Chur, with phone number 081 257 80 00 and email info@stva.gr.ch. There is also an office branch in Samedan at Cho d'Punt 53, 7503 Samedan, with phone +41 81 257 49 53

## Fahrzeugausweis (Vehicle Registration Certificate)
For vehicle registration matters, you can contact the Chur office at Ringstrasse 2, 7000 Chur, Tel. +41 81 257 80 62, fahrzeugzulassung@stva.gr.ch

## Gebühren (Fees)
Information about fees can be found in the Gebührenverordnung (Fee Regulation) 870.130 for services of the Road Traffic Office for motor vehicle holders. For motorcycles and e-bikes, costs consist of the annual fee (including vignette), vehicle registration certificate, control plate, and insurance fee


REMINDER: You MUST include the sources above in your response to the user using markdown hyperlinks.
```

## Step 39: WebSearch: 
```
{"query": "Kantonsamtsblatt Graub\u00fcnden online amtsblatt"}
```
Result:
```
Web search results for query: "Kantonsamtsblatt Graubünden online amtsblatt"

Links: [{"title":"Amtsblatt des Kantons Graubünden = Foglio Ufficiale del Cantone dei Grigioni = Fegl Uffizial dal Chantun Grischun : amtliches Publikationsorgan des Kantons Graubünden | Elektronische Zeitschriftenbibliothek","url":"https://ezb.uni-regensburg.de/detail.phtml?bibid=LEIFH&colors=7&lang=de&jour_id=243239"},{"title":"Amtsblatt Kanton Graubünden | Somedia Promotion","url":"https://www.somedia-promotion.ch/medien/online/amtsblatt-kanton-graubuenden"},{"title":"Kantonsamtsblatt Graubünden Willkommen beim Amtsblatt des Kantons Graubünden","url":"https://www.kantonsamtsblatt.gr.ch/digitales-amtsblatt-graubuenden-diam/"},{"title":"Elektronisches Kantonsamtsblatt | Das Kantonsamtsblatt ist online: Neu erscheint das Amtsblatt des Kantons Graubünden ausschliesslich in elektronischer Form. Unter... | By Kanton Graubünden | Facebook","url":"https://www.facebook.com/KantonGR/videos/elektronisches-kantonsamtsblatt/920470794696856/"},{"title":"Kantonsamtsblatt Graubünden Informationen","url":"https://www.kantonsamtsblatt.gr.ch/publizieren/informationen/"},{"title":"Kantonsamtsblatt Graubünden Hilfe - Gr.ch","url":"https://www.kantonsamtsblatt.gr.ch/service/hilfe/"},{"title":"Kantonsamtsblatt Graubünden Publikationen","url":"https://www.kantonsamtsblatt.gr.ch/"},{"title":"Registrierung digitales Amtsblatt des Kantons Graubünden","url":"https://www.kantonsamtsblatt.gr.ch/service/registrierung/?tx_diamcore_registration%5Baction%5D=enterUser&tx_diamcore_registration%5Bcontroller%5D=RegistrationUser&tx_diamcore_registration%5BpublicationAuthority%5D=467&cHash=14bd7aeb1c0d6e5a219c8a4e7a2e124c"},{"title":"DIAM - Digitales Amtsblatt für kantonale und kommunale Institutionen","url":"https://www.digitales-amtsblatt.ch/"},{"title":"Grisons","url":"https://en.wikipedia.org/wiki/Grisons"}]

Based on the search results, here's what I found about the Kantonsamtsblatt Graubünden online amtsblatt:

## Overview

All official publications, particularly of the canton, regions and municipalities, as well as private notices, are published daily on https://kantonsamtsblatt.gr.ch.

## Key Features

- **Digital Publication**: The electronic Kantonsamtsblatt has replaced the printed version of the amtsblatt since January 1, 2016
- **Legal Status**: The electronic publication of the publications is legally binding
- **Free Access**: The use of the digital amtsblatt is free of charge, and the content can be 
```

## Step 40: WebSearch: 
```
{"query": "site:gr.ch Gemeinden Graub\u00fcnden Verzeichnis Amt f\u00fcr Gemeinden Liste"}
```
Result:
```
Web search results for query: "site:gr.ch Gemeinden Graubünden Verzeichnis Amt für Gemeinden Liste"

Links: [{"title":"Entwicklung der Anzahl Gemeinden Graubündens","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/afg/Dokumentenliste/Entwicklung%20Anzahl%20Gemeinden%20GR.pdf"},{"title":"Gemeinderecht - Gemeinderecht","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/afg/gemeinden/Gemeinderecht/Seiten/default.aspx"},{"title":"Einteilung - Unsere Gemeinden","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/afg/gemeinden/UnsereGemeinden/Seiten/Einteilung.aspx"},{"title":"Willkommen Amt für Gemeinden","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/afg/Seiten/home.aspx"},{"title":"Gemeinden – geo.gr.ch - Geoportal - Kanton Graubünden","url":"https://geo.gr.ch/informationen/gemeinden"},{"title":"Die Gemeinden des Kantons Graubünden (sortiert nach Name) Gemeinde BFS-Nr.","url":"https://www.gr.ch/DE/institutionen/verwaltung/dvs/alg/Dokumente%20Geoinformation/AV_HS_02_DE_Die_Gemeinden_des_Kantons_Graub%C3%BCnden.pdf"},{"title":"Verdabbio","url":"https://en.wikipedia.org/wiki/Verdabbio"},{"title":"Liste Ortschaften/Gemeinden","url":"https://www.gr.ch/DE/institutionen/verwaltung/djsg/kesb/organisation/Seiten/Info.aspx"},{"title":"Leggia","url":"https://en.wikipedia.org/wiki/Leggia"},{"title":"Organigramm - Über uns","url":"https://www.gr.ch/DE/institutionen/verwaltung/dfg/afg/ueberuns/Seiten/Organigramm.aspx"}]

I found relevant search results for your query about municipalities in Graubünden. Here are the key resources from the official canton website (gr.ch):

**Key Results:**

1. The "Amt für Landwirtschaft und Geoinformation" (Office for Agriculture and Geoinformation) provides a list of municipalities in Canton Graubünden sorted by BFS number, updated as of April 16, 2026.

2. The "Amt für Gemeinden" (Office for Municipalities) provides information on the administrative divisions and municipalities under their section "Unsere Gemeinden" (Our Municipalities).

3. The geoportal geo.gr.ch contains a list of municipalities in Canton Graubünden.

4. The Amt für Gemeinden also publishes documentation on the development of the number of municipalities in Graubünden over time.

The main resources for finding comprehensive municipality lists and directories appear to be:
- The Amt für Gemeinden website (gr.ch/afg)
- The geo.gr.ch geoportal
- The Amt für Landwirtschaft und Geoinformation


REMINDER: You MUST include the sources above in you
```

> GR's real paths use `djsg` (not `djs`), `dvs/alt/tiere/hundewesen`, `dfg/stv/dokumentation/praxis`, and `ekud/avs/Volksschule/*.pdf`. Now VS and TI searches.

## Step 41: WebSearch: 
```
{"query": "site:vs.ch chiens d\u00e9tention SCAV v\u00e9t\u00e9rinaire cantonal Valais"}
```
Result:
```
Web search results for query: "site:vs.ch chiens détention SCAV vétérinaire cantonal Valais"

Links: [{"title":"Sécurité publique - EXT-CANT-ADM-SCAV-NEW - vs.ch","url":"https://www.vs.ch/web/scav/veterinaire/securit%C3%A9-publique"},{"title":"Affaires vétérinaires - EXT-CANT-ADM-SCAV-NEW - vs.ch","url":"https://www.vs.ch/web/scav/veterinaire"},{"title":"RS 455.1 - Loi d'application de la loi fédérale sur la protection des animaux - Canton du Valais - Recueil de la législation","url":"https://lex.vs.ch/app/fr/texts_of_law/455.1"},{"title":"Documents d'aide - - vs.ch","url":"https://www.vs.ch/web/scav/veterinaire/documents"},{"title":"Prise en charge professionnelle d'animaux - EXT-CANT-ADM-SCAV-NEW - vs.ch","url":"https://www.vs.ch/web/scav/veterinaire/prise-en-charge-professionnelle-animaux"},{"title":"Affaires canines - EXT-CANT-ADM-SCAV-NEW - vs.ch","url":"https://www.vs.ch/web/scav/veterinaire/affaires-canines"},{"title":"Révision de la loi cantonale sur la protection des animaux et nouvelle loi cantonale sur les chiens - Mise en consultation publique - - vs.ch","url":"https://www.vs.ch/web/communication/w/ision-de-la-loi-cantonale-sur-la-protection-des-animaux-et-nouvelle-loi-cantonale-sur-les-chiens-mise-en-consultation-publique"},{"title":"Protection des animaux - EXT-CANT-ADM-SCAV-NEW - vs.ch","url":"https://www.vs.ch/web/scav/veterinaire/protection-des-animaux"},{"title":"Département de la santé, des affaires sociales et de la culture","url":"https://www.vs.ch/documents/24255259/28611861/Information+d%C3%A9nonciation.pdf/656f5184-e184-8466-1906-4137065b598a?t=1706600780762&v=1.2"}]

I've successfully performed a web search for your query. Here are the key results found on the vs.ch website regarding dog detention (chiens détention), the cantonal veterinary office (vétérinaire cantonal), and related regulations in Valais:

**Key Findings:**

1. **Banned Breeds**: Since 2005, the detention of dogs whose breed appears on a specific list has been prohibited in the Valais canton.

2. **Office Vétérinaire Cantonal (Cantonal Veterinary Office) Mandates**: The cantonal veterinary office controls the detention of pets and livestock; professional detentions of pets and authorizations for detention of wild animals; prevention and treatment of dog aggression; and controls of dogs of prohibited breeds in the canton.

3. **Dog Detention Requirements**: In Valais, the responsibility for ensuring dogs are kept on leashes in designated areas falls to the communes,
```

## Step 42: WebSearch: 
```
{"query": "site:vs.ch vacances scolaires calendrier scolaire Valais"}
```
Result:
```
Web search results for query: "site:vs.ch vacances scolaires calendrier scolaire Valais"

Links: [{"title":"Echanges de courte durée - Programmes d'échanges individuel pendant les vacances scolaires - bel-new - vs.ch","url":"https://www.vs.ch/web/bel/echange-de-courte-dur%C3%A9e"},{"title":"Plan de travail et vacances - SRH - vs.ch","url":"https://www.vs.ch/web/srh/plan-de-travail"},{"title":"CALENDRIER SCOLAIRE 2018-2019","url":"https://www.vs.ch/documents/212242/1551993/Plans%20de%20scolarit%E9%202018-2021_f%E9vrier%202018.pdf/38b95004-db00-4827-9d54-8287478fc756"},{"title":"Rentrée scolaire 2025-2026 - Les grandes lignes et nouveautés de l’année scolaire présentées - - vs.ch","url":"https://www.vs.ch/web/communication/w/rentr%C3%A9e-scolaire-2025-2026-les-grandes-lignes-et-nouveaut%C3%A9s-de-l-ann%C3%A9e-scolaire-pr%C3%A9sent%C3%A9es"},{"title":"Plans de scolarité - se-new - vs.ch","url":"https://www.vs.ch/web/se/plans-de-scolarite"},{"title":"Calendrier des cours 2017 2018","url":"https://www.vs.ch/documents/1279920/0/Calendrier+des+cours+2017-2018/11b1e8fc-4136-4496-a0d3-1e658ca3d53b"},{"title":"Valais romand - Plan de scolarité 2024 / 2025","url":"https://www.vs.ch/documents/33324396/33330726/Plan+de+scolarit%C3%A9+2024-2025+(.pdf).pdf/796b4c64-504e-46ee-9274-f0d54c15350b?t=1571206216127&v=1.0"},{"title":"Département de l'économie et de la formation Service de l'enseignement","url":"https://www.vs.ch/documents/33324396/33330774/Plan+de+scolarite+valais+romand+2026-2027.pdf/7db0f178-fedf-b5b9-64e3-14a66129c6f3?t=1709298119700&v=1.0"},{"title":"Top vacances-scolaires-education.fr competitors & alternatives","url":"https://ahrefs.com/websites/vacances-scolaires-education.fr/competitors"}]

I've completed the web search for you. The search found relevant results from the vs.ch website regarding school calendars and vacations in Valais.

Key findings:

1. The official page for school plans (plans de scolarité) provides downloadable documents for Valais romand for the years 2025-2026, 2026-2027, 2027-2028, and 2028-2029.

2. For precise vacation dates, it's recommended to contact the school direction or municipality directly, as the plans are indicative.

3. The school year 2025-2026 begins on August 18 for students in Haut-Valais and all apprentices, and August 21 for students in Valais romand.

The most useful resource appears to be the official "Plans de scolarité" page on the vs.ch website, which contains downloadable PDF documents with the complete sc
```

## Step 43: WebSearch: 
```
{"query": "site:vs.ch guide d\u00e9claration d'imp\u00f4t personnes physiques instructions Valais"}
```
Result:
```
Web search results for query: "site:vs.ch guide déclaration d'impôt personnes physiques instructions Valais"

Links: [{"title":"Guide de la déclaration d'impôts 2020 Service cantonal des contributions","url":"https://www.vs.ch/documents/508074/8569689/Guide+2020_F.pdf/3b77330b-544e-37c7-a5c7-2f896c2dee59?t=1608039742617"},{"title":"Formulaires déclaration d'impôts personnes physiques - Service cantonal des contributions - vs.ch","url":"https://www.vs.ch/web/scc/formulaires-declaration-d-impots-personnes-physiques"},{"title":"Guide de la déclaration d'impôts 2022 Service cantonal des contributions","url":"https://www.vs.ch/documents/508074/21394236/Guide_2022_FR.pdf/f1a3c17d-8351-e214-44e0-b44333df1bf5?t=1672814469874"},{"title":"Formulaires 2023 - Service cantonal des contributions - vs.ch","url":"https://www.vs.ch/fr/web/scc/formulaires-2023"},{"title":"Guide de la déclaration d'impôts 2019 Service cantonal des contributions","url":"https://www.vs.ch/documents/508074/6126024/Guide+2019+FR.pdf/40f7fd9a-ad59-4ecc-a286-140da49d2045"},{"title":"Guide « simplifié » de la déclaration d'impôts 2024","url":"https://www.vs.ch/documents/508074/36083053/Guide_simplifi%C3%A9_2024_F.pdf"},{"title":"Guide « simplifié » de la déclaration d'impôts 2023 Service ...","url":"https://www.vs.ch/documents/508074/27571942/Guide_simplifi%C3%A9_2023_F.pdf/e1c0d9b4-d011-9750-8764-1338d6475358?t=1706017128507"},{"title":"Guide de la déclaration d'impôts 2023","url":"https://www.vs.ch/documents/508074/27571942/Guide+2023_F_PDF24.pdf/bc2bd700-0662-93eb-4c73-7657e8426761?t=1703060875846"},{"title":"INSTRUCTIONS D'APPLICATION DU CAHIER DES CHARGES","url":"https://www.vs.ch/documents/508074/636574/Conf%C3%A9rence+aux+communes+-+p%C3%A9rode+fiscal+2016/73f4571a-63cd-4113-a222-ffa3b4f91f98"}]

The search has successfully returned results from the vs.ch (Valais cantonal) website regarding tax declaration guides for individuals. Here's what I found:

The search results show several **guides for tax declarations (déclaration d'impôts) for individuals (personnes physiques)** published by the Service cantonal des contributions (SCC) in Valais:

1. **Most recent guides available:**
   - Simplified tax declaration guide for 2024
   - Simplified guide for 2023, with information and instructions available online
   - 2023 tax declaration guide

2. **Key information for tax filers:**
   - The guide contains all necessary instructions for completing the tax declaration and annexes
   - You can use t
```

## Step 44: WebSearch: 
```
{"query": "Bulletin officiel du canton du Valais Amtsblatt Wallis en ligne"}
```
Result:
```
Web search results for query: "Bulletin officiel du canton du Valais Amtsblatt Wallis en ligne"

Links: [{"title":"Accueil | Bulletin Valais Wallis - L'hebdomadaire des informations officielles du Valais","url":"https://www.bulletinvalaiswallis.ch/fr/accueil/"},{"title":"App Bulletin officiel Valais - App Store","url":"https://apps.apple.com/ch/app/bulletin-officiel-valais/id1413086783?l=fr-FR"},{"title":"Bulletin Valais Wallis | L'hebdomadaire des informations officielles du Valais","url":"https://www.bulletinvalaiswallis.ch/fr"},{"title":"Canton | Bulletin Valais Wallis - L'hebdomadaire des informations officielles du Valais","url":"https://www.bulletinvalaiswallis.ch/fr/canton/"},{"title":"Annonces officielles | Bulletin Valais Wallis - L'hebdomadaire des informations officielles du Valais","url":"https://www.bulletinvalaiswallis.ch/fr/articles/annonces-officielles/"},{"title":"ePaper | Bulletin Valais Wallis - L'hebdomadaire des informations officielles du Valais","url":"https://jd.bulletinvalaiswallis.ch/bo-vs"},{"title":"Avis officiels | Bulletin Valais Wallis - L'hebdomadaire des informations officielles du Valais","url":"https://www.bulletinvalaiswallis.ch/fr/avis-officiels/"},{"title":"Valais: le «Bulletin officiel» passe à l’ère numérique dès le 1er mars","url":"https://www.lenouvelliste.ch/valais/valais-le-bulletin-officiel-passe-a-lere-numerique-des-le-1ermars-1264075"},{"title":"Walliser Bote","url":"https://en.wikipedia.org/wiki/Walliser_Bote"},{"title":"Constituent Assembly of Valais","url":"https://en.wikipedia.org/wiki/Constituent_Assembly_of_Valais"}]

Based on the search results, here's what I found about the Bulletin officiel du canton du Valais / Amtsblatt Wallis:

The Bulletin Valais Wallis publishes information each week from the official Canton platform, with paper and e-paper editions appearing on Fridays. Starting March 1st, official notices from Valais became accessible for free on an electronic platform, while a paper offering renamed "Bulletin Valais-Wallis" is still maintained.

The official website for accessing the bulletin online is **bulletinvalaiswallis.ch** (available in both French and German versions). There is also a dedicated mobile application that provides access to all official canton communications, including news, media communications, legislative and administrative acts, job postings, and official announcements.

Only publication on the Canton's official website has legal validity.


REMINDER: You MUST include 
```

## Step 45: WebSearch: 
```
{"query": "site:vs.ch liste des communes valaisannes Service des affaires int\u00e9rieures et communales"}
```
Result:
```
Web search results for query: "site:vs.ch liste des communes valaisannes Service des affaires intérieures et communales"

Links: [{"title":"Affaires intérieures et communales - Rapport annuel 2021 - vs.ch","url":"https://www.vs.ch/web/rapport-annuel-2021/affaires-int%C3%A9rieures-et-communales"},{"title":"Service des affaires intérieures et communales","url":"https://www.vs.ch/web/saic"},{"title":"Service des affaires intérieures et communales - saic-new - vs.ch","url":"https://www.vs.ch/web/saic/particuliers/-/asset_publisher/d6U8h4VWoSpM/content/service-des-affaires-interieures-et-communales"},{"title":"Présentation du service des Affaires intérieures et communales - saic-new - vs.ch","url":"https://www.vs.ch/web/saic/autorites/-/asset_publisher/9MBk7AGTDoMR/content/presentation-du-service-des-affaires-interieures-et-communales"},{"title":"Finances communales: Partenariats canton - communes - saic-new - vs.ch","url":"https://www.vs.ch/web/saic/partenariat-canton-communes"},{"title":"Conseil et soutien aux communes valaisannes","url":"https://www.vs.ch/web/culture/conseil-et-soutien-aux-communes-valaisannes"},{"title":"Assembl%C3%A9e communale","url":"https://en.wikipedia.org/wiki/Assembl%C3%A9e_communale"},{"title":"Région District Commune - vs.ch","url":"https://www.vs.ch/web/communes"},{"title":"Communes - Région District Commune - vs.ch","url":"https://www.vs.ch/web/communes/commune"},{"title":"Val de Bagnes, Switzerland","url":"https://en.wikipedia.org/wiki/Val_de_Bagnes,_Switzerland"}]

I found search results related to the Service des affaires intérieures et communales (SAIC) on the vs.ch website. Here's what the search retrieved:

The Service des affaires intérieures et communales (SAIC) is responsible for relations between local authorities and the Canton. It supports and advises communes and bourgeoisies in its areas of competence, particularly at the legal and financial level as well as regarding mergers.

The search results include references to pages on the vs.ch website related to communes (such as https://www.vs.ch/web/communes), but the specific page content listing all Valais communes appears not to have been fully loaded in these search results. You may want to visit https://www.vs.ch/web/communes directly to access the complete list of Valais communes.


REMINDER: You MUST include the sources above in your response to the user using markdown hyperlinks.
```

## Step 46: WebSearch: 
```
{"query": "site:ti.ch Foglio ufficiale Cancelleria dello Stato Ticino"}
```
Result:
```
Web search results for query: "site:ti.ch Foglio ufficiale Cancelleria dello Stato Ticino"

Links: [{"title":"Repubblica e Cantone Ticino - Il Foglio ufficiale diventa digitale","url":"https://www4.ti.ch/tich/area-media/comunicati/dettaglio-comunicato/?NEWS_ID=189702"},{"title":"Cancelleria dello Stato - Annuario (CAN) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/can/annuario/cantone/amministrazione-cantonale/cancelleria-dello-stato/"},{"title":"Cancelleria dello Stato - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/tich/area-media/informazioni/persone-di-riferimento-per-i-media/cancelleria-dello-stato"},{"title":"CAN - Raccolta delle leggi del Cantone Ticino","url":"https://m3.ti.ch/CAN/RLeggi/public/index.php/raccolta-leggi/legge/num/59"},{"title":"Il nuovo portale dedicato al Foglio Ufficiale","url":"https://www4.ti.ch/can/argomenti/home/dettaglio/?aid=il-nuovo-portale-dedicato-al-foglio-ufficiale"},{"title":"Cancelleria dello Stato Piazza Governo 6 6501 Bellinzona","url":"https://www4.ti.ch/can/cancelleria"},{"title":"Foglio ufficiale - Repubblica e Cantone Ticino","url":"https://foglioufficiale.ti.ch/"},{"title":"Pubblicazioni - CAN (CAN) - Repubblica e Cantone Ticino","url":"https://www4.ti.ch/can/cosa-facciamo/pubblicazioni/"},{"title":"Informazioni ufficiali | Sportello dei servizi","url":"https://www.ti.ch/sportello/tematiche/politica-leggi-e-pubblicazioni/informazioni-ufficiali"}]

I've performed the web search for "site:ti.ch Foglio ufficiale Cancelleria dello Stato Ticino" and found several relevant results about the Official Gazette of the Canton Ticino.

Here are the key findings:

**Digital Transformation:**
As of February 1, 2021, the Foglio Ufficiale (Official Gazette) moved to the web portal www.foglioufficiale.ti.ch, over 175 years after the first print publication in 1844.

**Publication Form:**
The Official Gazette is published in electronic form. The new platform allows authorities and businesses to publish their announcements directly and at any time of the week, and all publications are signed with qualified electronic signatures.

**Official Structure:**
The Cancelleria dello Stato (State Chancellery) manages various services including the administrative services of the State Council and external relations services. The State Chancellor (Cancelliere dello Stato) is based at Piazza Governo 6, 6501 Bellinzona.

**Portal Integration:**
The new portal is also integrated into www.amtsblattportal.ch, the central plat
```

> Now verifying GR courts on www.justiz-gr.ch with curl: root, robots, sitemap and the Obergericht paths.

## Step 47: Bash: Probe justiz-gr.ch root, robots, sitemap, Obergericht
```
cd /tmp/sg-verify-run3-e && python3 probe.py https://www.justiz-gr.ch/ https://www.justiz-gr.ch/robots.txt https://www.justiz-gr.ch/sitemap.xml https://www.justiz-gr.ch/gerichte/obergericht/ https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/ https://www.justiz-gr.ch/gerichte/obergericht/aktuelles/infos/; cat $(ls -t p_* | head -6 | sed -n 5p) | head -20
```
Result:
```
200 | text/html;charset=utf-8 | 4751B | links 328 | words 484 | Justiz Graubünden | https://www.justiz-gr.ch/ | file /tmp/sg-verify-run3-e/p_63fba30fa8
200 | text/plain | 24B | links 0 | words 0 |  | https://www.justiz-gr.ch/robots.txt | file /tmp/sg-verify-run3-e/p_68ca7ea3c9
200 | text/xml;charset=UTF-8 | 4719B | links 0 | words 0 |  | https://www.justiz-gr.ch/sitemap.xml | file /tmp/sg-verify-run3-e/p_2925d29141
200 | text/html;charset=utf-8 | 5251B | links 309 | words 617 | Aufgaben | https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/ | file /tmp/sg-verify-run3-e/p_ce44368ebf
200 | text/html;charset=utf-8 | 5251B | links 309 | words 617 | Aufgaben | https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/ | file /tmp/sg-verify-run3-e/p_e22f9f8506
200 | text/html;charset=utf-8 | 6797B | links 321 | words 979 | Infos | https://www.justiz-gr.ch/gerichte/obergericht/aktuelles/infos/ | file /tmp/sg-verify-run3-e/p_959a43ad29
User-agent: *
Disallow:
```

## Step 48: Bash: Inspect justiz-gr.ch sitemap
```
cd /tmp/sg-verify-run3-e && cat p_2925d29141 | head -c 3000; echo; echo ---; grep -o '<loc>[^<]*</loc>' p_2925d29141 | wc -l
```
Result:
```
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
	<url>
		<loc>https://www.justiz-gr.ch/</loc>
		<lastmod>2024-10-02T11:10:45+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/</loc>
		<lastmod>2013-10-23T17:20:50+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/</loc>
		<lastmod>2024-11-20T12:18:12+01:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/</loc>
		<lastmod>2024-12-27T11:56:33+01:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/dretgiras/dretgira-da-giustia-dal-chantun-grischun/ueber-uns/incumbensas/</loc>
		<lastmod>2025-09-29T07:40:06+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/personelles/</loc>
		<lastmod>2025-01-01T10:04:12+01:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/organisation/</loc>
		<lastmod>2025-01-02T09:13:32+01:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/interessenbindungen/</loc>
		<lastmod>2026-06-10T16:41:57+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/kontakt-und-standort/</loc>
		<lastmod>2025-03-31T14:08:19+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/aktuelles/</loc>
		<lastmod>2024-11-20T14:32:27+01:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/aktuelles/pressemedien/</loc>
		<lastmod>2025-03-31T14:10:23+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/dienstleistungenthemen/</loc>
		<lastmod>2024-11-20T14:33:36+01:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/dienstleistungenthemen/information-zu-prozessenverfahren/</loc>
		<lastmod>2025-03-31T14:11:52+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/dokumentation/</loc>
		<lastmod>2024-11-20T14:52:57+01:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/dokumentation/rechtsprechung/</loc>
		<lastmod>2026-04-28T14:24:00+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/justizgericht/dokumentation/geschaeftsberichte/</loc>
		<lastmod>2026-06-03T13:40:16+02:00</lastmod>
	</url>
	<url>
		<loc>https://www.justiz-gr.ch/gerichte/obergericht/</loc>
		<lastmod>2024-09-30T16:43:14+
```

> justiz-gr.ch has a 305-URL sitemap. Let me list its structure.

## Step 49: Bash: Summarise justiz-gr.ch sitemap by section
```
cd /tmp/sg-verify-run3-e && grep -o '<loc>[^<]*</loc>' p_2925d29141 | sed 's/<[^>]*>//g' > justizgr_sitemap.txt; awk -F/ '{print $4"/"$5}' justizgr_sitemap.txt | sort | uniq -c | sort -rn | head -40; echo; grep -v -E '/(gerichte|dretgiras|tribunali)/' justizgr_sitemap.txt | head -20
```
Result:
```
 148 gerichte/regionalgerichte
  24 gerichte/obergericht
  17 advokatur-und-notariat/aufsichtskommission-rechtsanwaelte
  13 gerichte/justizgericht
   9 schlichtungsbehoerden-und-mediation/ueber-uns
   9 advokatur-und-notariat/notariatskommission
   8 quicklinks-footer/schlichtungsbehoerden
   8 quicklinks-footer/gerichte
   8 gerichte/enteignungskommission
   7 schuldbetreibung-und-konkurs/dienstleistungenthemen
   6 quicklinks-footer/advokatur-und-notariat
   5 quicklinks-footer/schuldbetreibung-und-konkurs
   4 schuldbetreibung-und-konkurs/ueber-uns
   4 schlichtungsbehoerden-und-mediation/dienstleistungenthemen
   4 quicklinks-footer/suche
   3 schuldbetreibung-und-konkurs/dokumentation
   3 schuldbetreibung-und-konkurs/aktuelles
   3 schlichtungsbehoerden-und-mediation/dokumentation
   2 tribunali/tribunale-dappello
   1 tribunali/tribunali-regionali
   1 suche/volltextsuche
   1 suche/stellensuche
   1 suche/behoerdensuche
   1 suche/
   1 schuldbetreibung-und-konkurs/
   1 schlichtungsbehoerden-und-mediation/aktuelles
   1 schlichtungsbehoerden-und-mediation/
   1 quicklinks/advokatur-und-notariat
   1 infos/rechtshinweise
   1 infos/login
   1 infos/impressum
   1 gerichte/zwangsmassnahmengericht.html
   1 gerichte/weitere-behoerden
   1 gerichte/
   1 dretgiras/dretgira-da-giustia-dal-chantun-grischun
   1 advokatur-und-notariat/register
   1 advokatur-und-notariat/
   1 advocatura-e-notariat/cumissiun-da-surveglianza-davart-ils-advocats
   1 /

https://www.justiz-gr.ch/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/allgemeine-informationen/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/vermittleraemter/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/mietsachen/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/gleichstellungssachen/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/sozialversicherungssachen/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/mediation/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/interessenbindungen/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/offene-stellen/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/aktuelles/
https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/dienst
```

## Step 50: Bash: List Obergericht and regional court URLs in sitemap
```
cd /tmp/sg-verify-run3-e && grep -E '/gerichte/(obergericht|justizgericht)/|/tribunali/|/suche/' justizgr_sitemap.txt; echo; grep -E '/regionalgerichte/' justizgr_sitemap.txt | awk -F/ '{print $6}' | sort | uniq -c; grep -E '/regionalgerichte/' justizgr_sitemap.txt | grep -i -E 'kosten|gebuehr|dienstleist|themen|merkbl|rechtsprech' | head -30
```
Result:
```
https://www.justiz-gr.ch/gerichte/justizgericht/
https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/
https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/personelles/
https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/organisation/
https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/interessenbindungen/
https://www.justiz-gr.ch/gerichte/justizgericht/ueber-uns/kontakt-und-standort/
https://www.justiz-gr.ch/gerichte/justizgericht/aktuelles/
https://www.justiz-gr.ch/gerichte/justizgericht/aktuelles/pressemedien/
https://www.justiz-gr.ch/gerichte/justizgericht/dienstleistungenthemen/
https://www.justiz-gr.ch/gerichte/justizgericht/dienstleistungenthemen/information-zu-prozessenverfahren/
https://www.justiz-gr.ch/gerichte/justizgericht/dokumentation/
https://www.justiz-gr.ch/gerichte/justizgericht/dokumentation/rechtsprechung/
https://www.justiz-gr.ch/gerichte/justizgericht/dokumentation/geschaeftsberichte/
https://www.justiz-gr.ch/gerichte/obergericht/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/personelles/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/organisation/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/gremien/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/kammern/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/interessensbindungen/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/kontakt-und-standort/
https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/offene-stellen/
https://www.justiz-gr.ch/gerichte/obergericht/aktuelles/
https://www.justiz-gr.ch/gerichte/obergericht/aktuelles/infos/
https://www.justiz-gr.ch/tribunali/tribunale-dappello/attualita/dibattimenti/
https://www.justiz-gr.ch/gerichte/obergericht/aktuelles/pressemedien/
https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/
https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/prozess-und-verfahrenskosten/
https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/unentgeltliche-rechtspflege/
https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/bibliothek/
https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/allgemeine-rechtsauskuenfte/
https://www.justiz-gr.ch/gerichte/obergericht/dokumentation/
https://www.justiz-gr.ch/gerichte/obergericht/dokumentation/rechtsprechung/
https://www.justiz-gr.ch/gerichte/oberge
```

> justiz-gr.ch covers the Obergericht, Justizgericht, 11 Regionalgerichte, the Schlichtungsbehörden (with a costs page), and SchKG. Probing the key pages.

## Step 51: Bash: Probe GR Obergericht fee, guidance, decisions and conciliation pages
```
cd /tmp/sg-verify-run3-e && B=https://www.justiz-gr.ch; python3 probe.py $B/gerichte/obergericht/dienstleistungenthemen/prozess-und-verfahrenskosten/ $B/gerichte/obergericht/dienstleistungenthemen/unentgeltliche-rechtspflege/ $B/gerichte/obergericht/dienstleistungenthemen/allgemeine-rechtsauskuenfte/ $B/gerichte/obergericht/dokumentation/rechtsprechung/ $B/schlichtungsbehoerden-und-mediation/dienstleistungenthemen/kosten/ $B/schlichtungsbehoerden-und-mediation/dienstleistungenthemen/verfahren/ $B/schlichtungsbehoerden-und-mediation/ueber-uns/vermittleraemter/ $B/schlichtungsbehoerden-und-mediation/ueber-uns/mietsachen/ $B/gerichte/obergericht/
```
Result:
```
200 | text/html;charset=utf-8 | 8610B | links 336 | words 1739 | Prozess- und Verfahrenskosten | https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/prozess-und-verfahrenskosten/ | file /tmp/sg-verify-run3-e/p_e02075cdb6
200 | text/html;charset=utf-8 | 8340B | links 331 | words 2031 | Unentgeltliche Rechtspflege | https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/unentgeltliche-rechtspflege/ | file /tmp/sg-verify-run3-e/p_18175f0459
200 | text/html;charset=utf-8 | 4806B | links 308 | words 493 | Allgemeine Rechtsauskünfte | https://www.justiz-gr.ch/gerichte/obergericht/dienstleistungenthemen/allgemeine-rechtsauskuenfte/ | file /tmp/sg-verify-run3-e/p_ceb6a8de11
200 | text/html;charset=utf-8 | 5020B | links 312 | words 509 | Rechtsprechung | https://www.justiz-gr.ch/gerichte/obergericht/dokumentation/rechtsprechung/ | file /tmp/sg-verify-run3-e/p_d9c3763304
200 | text/html;charset=utf-8 | 5691B | links 316 | words 726 | Kosten | https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/dienstleistungenthemen/kosten/ | file /tmp/sg-verify-run3-e/p_5b599b1ebe
200 | text/html;charset=utf-8 | 6214B | links 324 | words 911 | Verfahren | https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/dienstleistungenthemen/verfahren/ | file /tmp/sg-verify-run3-e/p_fe459d77f3
200 | text/html;charset=utf-8 | 6734B | links 317 | words 1034 | Vermittlerämter | https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/vermittleraemter/ | file /tmp/sg-verify-run3-e/p_f82d5b321a
200 | text/html;charset=utf-8 | 6942B | links 319 | words 1064 | Mietsachen | https://www.justiz-gr.ch/schlichtungsbehoerden-und-mediation/ueber-uns/mietsachen/ | file /tmp/sg-verify-run3-e/p_386cdd046c
200 | text/html;charset=utf-8 | 5251B | links 309 | words 617 | Aufgaben | https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/ | file /tmp/sg-verify-run3-e/p_ce44368ebf
```

## Step 52: Bash: Extract CHF samples from GR court costs page
```
cd /tmp/sg-verify-run3-e && cat > maintext.py <<'EOF'
import re,html,sys
def main_text(fn, start_markers=('id="maincontent"','<main','id="content"','role="main"')):
    t=open(fn,encoding='utf-8',errors='ignore').read()
    body=re.sub(r'<script.*?</script>|<style.*?</style>|<nav.*?</nav>',' ',t,flags=re.S|re.I)
    for m in start_markers:
        i=body.find(m)
        if i>=0: body=body[i:]; break
    txt=html.unescape(re.sub(r'<[^>]+>',' ',body)); return re.sub(r'\s+',' ',txt)
if __name__=='__main__':
    fn=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 1200
    kws=sys.argv[3:] 
    txt=main_text(fn)
    if kws:
        for kw in kws:
            for mm in list(re.finditer(kw,txt,re.I))[:3]:
                print(f'[{kw}]', txt[max(0,mm.start()-200):mm.end()+200]); print()
    else:
        print(txt[:n])
EOF
python3 maintext.py p_e02075cdb6 0 'CHF|Fr\.' | head -30
```
Result:
```
[CHF|Fr\.] Fällen – insbesondere in Rechtsmittelverfahren - aber auch in der vollen Höhe ( Art. 98 Abs. 2 lit. d ). Es setzt dabei eine Frist für dessen Leistung an. Wird der Vorschuss auch nicht innert einer Nachfrist geleistet, so tritt das Gericht auf die Klage oder auf das Gesuch nicht ein. Parteientschädigung Als Parteientschädigung gilt: der Ersatz notwendiger Auslagen, die Kosten einer berufsmässigen (me

[CHF|Fr\.] erstatten, sobald es ihre wirtschaftlichen Verhältnisse erlauben ( Art. 135 Abs. 4 StPO ). Hat die beschuldigte Person die Einleitung des Verfahrens rechtswidrig und schuldhaft bewirkt oder dessen Durchführung erschwert, so trägt sie die Kosten auch bei Einstellung oder Freispruch ( Art. 426 Abs. 2 StPO ). Privatklägerschaft und antragstellende Person Bei Antragsdelikten können die Verfahrenskosten d

[CHF|Fr\.] i Antragsdelikten können die Verfahrenskosten der antragstellenden Person oder der Privatklägerschaft, sofern diese mutwillig oder grob fahrlässig die Einleitung des Verfahrens bewirkt oder dessen Durchführung erschwert hat, auferlegt werden, wenn kein Schuldspruch erfolgt und soweit die beschuldigte Person nicht die Kosten zu tragen hat ( Art. 427 Abs. 2 StPO ). Bei Einstellung oder Freispruch, bei
```

## Step 53: Bash: Find CHF amounts on GR cost and conciliation pages
```
cd /tmp/sg-verify-run3-e && for f in p_e02075cdb6 p_5b599b1ebe p_18175f0459; do echo "=== $f"; python3 maintext.py $f 0 'CHF' 'Franken' '[0-9]{3,}\s?(\.–|\.-|\')' | head -12; done; echo; python3 maintext.py p_5b599b1ebe 1500
```
Result:
```
Exit code 1
(eval):1: parse error near `)'
```

## Step 54: Bash: Find CHF amounts on GR cost and conciliation pages
```
cd /tmp/sg-verify-run3-e && for f in p_e02075cdb6 p_5b599b1ebe p_18175f0459; do echo "=== $f"; python3 maintext.py $f 0 'CHF' 'Franken' | head -12; done; echo; python3 maintext.py p_5b599b1ebe 1800
```
Result:
```
=== p_e02075cdb6
[CHF] Fällen – insbesondere in Rechtsmittelverfahren - aber auch in der vollen Höhe ( Art. 98 Abs. 2 lit. d ). Es setzt dabei eine Frist für dessen Leistung an. Wird der Vorschuss auch nicht innert einer Nachfrist geleistet, so tritt das Gericht auf die Klage oder auf das Gesuch nicht ein. Parteientschädigung Als Parteientschädigung gilt: der Ersatz notwendiger Auslagen, die Kosten einer berufsmässigen (me

[CHF] erstatten, sobald es ihre wirtschaftlichen Verhältnisse erlauben ( Art. 135 Abs. 4 StPO ). Hat die beschuldigte Person die Einleitung des Verfahrens rechtswidrig und schuldhaft bewirkt oder dessen Durchführung erschwert, so trägt sie die Kosten auch bei Einstellung oder Freispruch ( Art. 426 Abs. 2 StPO ). Privatklägerschaft und antragstellende Person Bei Antragsdelikten können die Verfahrenskosten d

[CHF] i Antragsdelikten können die Verfahrenskosten der antragstellenden Person oder der Privatklägerschaft, sofern diese mutwillig oder grob fahrlässig die Einleitung des Verfahrens bewirkt oder dessen Durchführung erschwert hat, auferlegt werden, wenn kein Schuldspruch erfolgt und soweit die beschuldigte Person nicht die Kosten zu tragen hat ( Art. 427 Abs. 2 StPO ). Bei Einstellung oder Freispruch, bei 

[Franken] t. 426 Abs. 1 StPO ). In diesem Fall hat sie auch die Kosten der amtlichen Verteidigung dem Kanton zurückzuzahlen und der Verteidigung die Differenz zwischen der tieferen amtlichen Entschädigung (200 Franken) und dem vollen vereinbarten Honorar zu erstatten, sobald es ihre wirtschaftlichen Verhältnisse erlauben ( Art. 135 Abs. 4 StPO ). Hat die beschuldigte Person die Einleitung des Verfahrens rechtswidr

[Franken]  bei Streitigkeiten über IV-Leistungen vor dem kantonalen Versicherungsgericht kostenpflichtig. Diese Kosten werden nach dem Verfahrensaufwand und unabhängig vom Streitwert im Umfang von 200 bis 1000 Franken festgelegt. Für andere Streitigkeiten im Anwendungsbereich des ATSG, welche nicht als Leistungsstreitigkeiten im Sinne von Art. 61 lit. fbis ATSG gelten, wie insbesondere Beitragsstreitigkeiten, rich

=== p_5b599b1ebe
[CHF]  Person ( Art. 15 Abs. 2 EGzZPO ). Gerichtskosten Das Obergericht des Kantons Graubünden hat in der VGZ die entsprechenden Pauschalen festgelegt. Im Schlichtungsverfahren beträgt diese Pauschalgebühr CHF 100.00 bis CHF 500.00. Beantragt die klagende Partei einen Entscheid oder wird von den Parteien ein Urteilsvorschlag angenommen, beträgt die Gebühr CHF 300.00 bis CHF 3000.00. In Verfah
```

> GR fee samples found. Now the GR decisions page links.

## Step 55: Bash: List links on GR Obergericht jurisprudence page
```
cd /tmp/sg-verify-run3-e && python3 maintext.py p_d9c3763304 0 'Rechtsprechung' | tail -3; python3 - <<'EOF'
import re,html
t=open('p_d9c3763304',encoding='utf-8',errors='ignore').read()
for h,txt in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S|re.I):
    txt=html.unescape(re.sub(r'<[^>]+>|\s+',' ',txt)).strip()
    if 'justiz-gr.ch' in h and '/gerichte/' in h and 'rechtsprechung' not in h: continue
    if h.startswith('/') and not any(k in h for k in ['rechtsprech','entscheid','urteil','suche']): continue
    print(h,'|',txt[:80])
EOF
```
**No result: this is the command that was waiting for approval when the run stalled.**
