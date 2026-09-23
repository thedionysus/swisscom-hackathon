# Brief v5: source verification agents (read fully before starting)

_v4 = v3 plus the learnings of the 2026-09-23 runs (pilot + 5 groups). The new sections are marked **NEW v4**._

## Why you are doing this
We build **Swiss Grounding**, an MCP server that gives a chat model *cited evidence* from Swiss
public sources, scoped to the jurisdiction a question applies to (CH → canton → district → commune).
Typical questions: "When is cardboard collected in 8003?", "Can my dog run off leash in my commune?",
"What does a dog cost in tax here?", "When are school holidays in Bern?", "What is the waste bag fee?"

You get a small set of **candidate links** that came from a Google AI answer. **That AI is
unreliable.** It invents URLs, shortens links to bare domains and mislabels pages. Each link comes
with the AI's *claim*. Your job:

1. **Find the real data** behind each lead. Start from the link (or the bare domain) and dig.
2. **Decide: can we get it?** If so, **in what exact format**, and **how would a fetcher get it**.
3. **Test the AI's claim**: confirmed, wrong or partly right.

## THE MOST IMPORTANT RULE: find the real source, and explore freely to do it
**What matters most to us is that you find where the actual data lives.** The given link is a
starting point, not the answer. In the pilot run, **3 of 4 leads only became useful after a web
search or after following a hop to another site.** An agent that had stopped at the given link
would have missed all three. In the five group runs that followed, the best finds were all one hop
away from the given lead (intlex.ch, tlex.ch, ÖREB LegalProvisions, the zh.ch child sitemap, REAL Luzern's ICS). So:

- **You are free to explore.** If the lead points somewhere better (another official host, the
  cantonal law collection, an open-data portal, a commune's own site, a vendor platform that hosts
  many communes), go there. Up to **2 hops** from the given link is in scope when each hop lands
  on an official or data-bearing host. If a find is outside your leads but clearly valuable
  (e.g. a platform covering many communes), report it under "Related finds".
- **Do not stop at a landing or guidance page.** Keep going until you reach the layer that holds
  the actual content (the individual regulation, the calendar entry, the record), or you have
  proven it is not reachable.
- **Before you are allowed to write "Blocked", "No data" or "Partly" for a lead, you must have
  tried every step of this ladder and logged each result:**

1. The given URL with curl (follow redirects, browser-like User-Agent).
2. If 404 or a bare domain: the site root, then `robots.txt` (it often names the sitemap),
   `/sitemap.xml`, `/sitemap_index.xml`, and the site's own search (`/suche?q=`, `/search?q=`, `?s=`).
3. A WebSearch restricted to the host (`site:host.ch Reglement`, `site:host.ch filetype:pdf`),
   in the right language: Reglement / Verordnung / règlement / regolamento / Gebühren / tarif / Ferien.
4. If the page is a JavaScript shell: read the JS bundles (`<script src>`) and grep them for `api`,
   `json`, `graphql`, `/rest/`, `fetch(`, `.json`. Try the endpoints you find. Look for
   `__NEXT_DATA__`, `window.__INITIAL_STATE__` or JSON-LD in the HTML.
5. **Open-data portal probe** (this worked generically in the pilot):
   - opendata.swiss CKAN: `https://ckan.opendata.swiss/api/3/action/package_search?q=<terms>&rows=20`
     (use a browser User-Agent), also `organization_list?all_fields=true`.
   - Opendatasoft portals (data.bs.ch, data.bl.ch, daten.sg.ch, daten.stadt.sg.ch, data.tg.ch,
     data.sz.ch, opendata.fr.ch, ...): `https://<portal>/api/explore/v2.1/catalog/datasets?where=search("<term>")&limit=20`
     (use `where=`; `search=` does not filter), records via `/api/explore/v2.1/catalog/datasets/<id>/records?limit=100&offset=N`.
   - Also check for RSS/Atom, `?format=json`, `.ics`, CSV/XLSX, "Open Data", "Schnittstelle", "API", "Download".
   - **NEW v4:** WordPress sites: `/wp-json/wp/v2/media?mime_type=application/pdf&search=<term>&per_page=100`
     (total in the `x-wp-total` header). Plone: request the page with `Accept: application/json`.
   - **NEW v4:** Sitemaps are often **indexes of child sitemaps**. Open every child before concluding "not in the sitemap"
     (the pilot missed 159 ZH Steuerbuch entries this way: `zh.ch/de/steuern-finanzen.zhweb-sitemap.xml`).
6. One or two hops: follow the official host that holds the real content and apply the ladder there.

"I tried X, got Y" is valuable. "It seems not available" is not.

Also: **we can build new fetchers.** "Our four strategies can't read it" does NOT mean "not
usable". If the data is reachable, describe how a new fetcher would get it.

## NEW v4: What we already know (do not redo; use it to go faster)

### Platform signatures: detect these first, they decide the fetcher
| Signature in the page or host | Platform | What to call | Coverage known on 2026-09-23 |
|---|---|---|---|
| `<title>LexWork</title>`, `/api/de/settings` answers JSON, host `*.tlex.ch` | **Sitrox LexWork** | `/api/{lang}/texts_of_law/lightweight_index` (list), `/texts_of_law/{nr}` or `/show_as_json` (articles), `/status/recent_changes` | 19 cantonal law portals, intlex.ch (317 concordats), ≥49 communes on tlex |
| `stats.i-web.ch`, `pcdn1.i-web.ch`, `<table class="icms-dt" data-entities=` , `/_rte/publikation/`, `/_doc/` | **i-web / i-CMS** | parse the `data-entities` JSON on `/reglemente`, `/reglements`, `/rechtssammlung`, `/gesetzessammlung`; follow `/_rte/publikation/<id>` → `/_doc/<id>` PDF | 496 commune homepages; 438 with a regulations table (18,418 rows) |
| `public/upload/assets/<id>/<name>.pdf?fp=N`, "backslash AG", govis.ch | **govis** | scrape PDF links on the Reglemente page | ~264 homepages (AG, ZH, TG, SO, LU, BE) |
| `/wAssets/docs/`, `weblication`, `stats.talus.ch` | **Weblication (Talus)** | `/de/verwaltung/dokumente/` + `wList.php?action=createListAjaxOfData…&pageId=N` | ~113 homepages, mostly BE |
| `wp-content`, `wp-json` | WordPress | wp media API (above) | many |
| `bl-api.webcloud7.ch`, Plone | Plone REST | `Accept: application/json`, `@search`, page with `b_start` | Kanton BL + 12 small BL communes |
| `data-*.opendatasoft`, `/api/explore/v2.1/` | Opendatasoft | catalog `where=search("…")`, records `limit=100&offset=N`, `/exports/json` (all rows, one GET) | BS, BL, SG, TG, SZ, FR, SBB, … |
| `entsorglos.swiss` | waste-calendar vendor | `https://<slug>.entsorglos.swiss/calendar.ics` (no auth) | 10 Zimmerberg communes |
| `sammelkalender.ch` | waste-calendar vendor | API needs auth (401) | 5 central-Swiss associations |
| ÖREB web service | federal standard | `getegrid/json?EN=x,y` → `extract/json?EGRID=…` → `LegalProvisions` (links to communal Baureglement PDFs) | every canton runs one; links confirmed only in SZ, ZH |

### Already verified: cite it, do not re-verify
LexWork (19 cantons, intlex, tlex) · LexFind (28 entities, no communes; listing = `entities/{id}/systematics?tols_for_systematics[]=` in batches ≤100) ·
VD `prestations.vd.ch/pub/blv-publication/api/…`, NE `rsn.ne.ch/DATA/program/books/rsne/{pdf|htm}/{nr}`, TI `www3.ti.ch/CAN/RLeggi/…/num/{n}`, JU `rsju.jura.ch viewdocument.html?…&download=1` ·
concordat conference pages (EDK, BPUK, KKJPD, KKPKS, GESPA) · cantonal guidance ZH/GE/BE/BS (dogs, tax, road traffic, school holidays) ·
BS 100397 / BL 13350 school holidays, GE `.ics` holidays, ZH holiday XLSX · SZ districts (Küssnacht, Einsiedeln, Gersau) · gerichte-zh.ch · BE RSTA ·
geobasisdaten API, geodienste OGC API, BFS commune snapshot API · ZAB, REAL Luzern, SRFWL, Diessenhofen, SIGE, Schöftland · SBB Tarifverbundkarte ·
Bern ArcGIS waste zones, Lausanne WFS dog zones, Biel parking, Lugano/Winterthur/Uster portals · Fribourg commune sites (sample of 12 + homepage scan of 119).
Full evidence: `docs/sources/subnational_sources.md` and `docs/sources/verification_2026-09-23/`. Also `docs/sources/ogd_lists_assessment.md` in the repo.

### Traps met (each cost an agent time)
- **The AI list is unreliable.** About half of its claims were wrong or partly wrong (wrong domains, a Ukraine pet-import PDF labelled
  "dog rules", a private law firm labelled official, an outdated version id). Always test the claim.
- **Landing pages are thin.** The data is one layer down (per-entry pages, per-commune PDFs, JSON in an attribute).
- **Associations rarely set resident fees.** Fees are usually in each member commune's Gebührenreglement. Check the commune too.
- **Parking rules are municipal**, not cantonal.
- **Scanned PDFs exist** (SRFWL 2025, the SIGE water tariff, OCR-quality text in the SZ ÖREB). Always test the text layer with pypdf.
- **Bot walls:** edudoc.ch (AWS WAF, 202 with 0 bytes; its OAI policy forbids harvesting). www.admin.ch returns 403. Some sites need the `www.` host
  (www.gesetzessammlung.sg.ch, www.gr-lex.gr.ch). Some rate-limit (kuessnacht sitemap 429; BE and BS set Crawl-delay 10).
- **curl globbing:** URLs with `[` `]` need `curl -g`.
- **Intlex accession tables miss withdrawals.** Cross-check member lists with the conference's own list.
- **Stay read-only:** agents may not write report files (the harness blocked `report.md` for 3 of 5 agents). Put the full report in your final message.

## What our pipeline supports TODAY (verified in the code)
Every fetcher returns documents (url, title, language, identifier, dates, in_force, event_date)
split into sections (heading_path, anchor, text). Four strategies:

- `html_crawl`: server-rendered HTML. Config: `start_paths`, `path_allowlist`, `language`. A plain
  HTTP client must see real `<a href>` links and text. JavaScript-only pages do NOT work.
- `pdf`: a **fixed list of PDF URLs** in config (`urls: [...]`), text extracted with **pypdf, no
  OCR**. So: the PDF must have a text layer, and there is no discovery. Someone must list the URLs,
  or a new fetcher must discover them from an index page.
- `api`: ONE GET request to a JSON endpoint. Config: `url` (may contain `{start}`/`{today}`
  placeholders), `records_path` (dotted path to the list), `id_field` or `id_template`,
  `title_template`, `text_template` (Python format strings over record fields),
  `event_date_field`, `language`. No pagination (so max 1 page, typically 100 records).
- `fedlex_sparql`: federal law only (already done, ignore).

Example of an `api` source that works today:
```yaml
fetch_strategy: api
fetch_config:
  url: https://openerz.metaodi.ch/api/calendar?region=zurich&zip=8003&start={start}&sort=date&limit=100
  records_path: result
  id_template: "{waste_type}-{date}"
  event_date_field: date
  title_template: "Waste collection {waste_type} in {zip} on {date}"
  text_template: "Collection of {waste_type} in Zurich postal code {zip} on {date}."
```

NOT supported today (new fetcher needed): scanned PDFs (OCR), `.ics` calendars, CSV/XLSX, XML,
paginated APIs, PDF discovery from an index page, JS apps (unless a JSON API is found behind them).

**NEW v4, facts from the code that change verdicts:**
- `api` accepts a list at the **root** of the response when `records_path: ""` (`api.py:20-27`), and templates can index
  nested fields: `{attributes[Zone]}`, `{fields[name]}` (Python `str.format_map`).
- There is **no per-record jurisdiction** in `api`. Every document lands on `default_extent_id`, or on the result of text
  narrowing (`enrich.py:42-44`, only if `allow_narrowing: true`, and never for law authorities). So a source with one record per
  commune needs either one source per commune or narrowing that works. Say which in your fetcher hint.
- **Categories allowed today:** `dogs, health, hiking, housing, parking, safety, schools, taxes, transport, waste`.
  Anything else (building, water, fire service, gambling, courts) must be reported as "category missing: <name>".
- Landing contract (`ingest/models.py:14-28`): `url, title, language, sections[heading_path, anchor, text], identifier,
  published_at, valid_from, valid_to, in_force, event_date`. Name the source field for each one you can fill.

## Rules every source must meet
- **Jurisdiction:** content lands on ONE node: `CH`, `CH-XX` (canton), `CH-XX-<BFS commune number>`.
  A commune association that covers several communes cannot sit on one node. Note that explicitly
  and list the member communes if the site says who they are.
- **Authority by publisher:** `cantonal_law`/`municipal_law` only for the legal text itself on an
  official law platform. `official_info` for official bodies (cantons, communes, associations of
  communes, courts, offices) and their guidance/calendars/tariffs. `institutional` for everyone
  else (vendors, NGOs, aggregators).
- **Dates:** find a publication/validity date or in-force date if one exists (for regulations)
  and an event date (for calendars).

## Useful repo data (read-only)
- `<repo>/docs/sources/commune_sites.csv`: 2,110 communes with
  columns `extent_id,bfs,canton,label,website,population` (e.g. `CH-ZH-261,261,CH-ZH,Zürich,https://www.stadt-zuerich.ch/,452421`).
  Use it to count how many communes a pattern would cover, to sample communes, and to give BFS ids.
- `<repo>/docs/sources/ogd_lists_assessment.md`: sources already verified
  on 2026-09-22. Do not redo what is there; cite it.

## Method
- `curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o /tmp/<file> -w "%{http_code} %{content_type} %{size_download}B %{url_effective}\n" <url>`
- HTML: count `<a href` occurrences and words after stripping tags. ~2 KB with 0 links = JS shell.
- PDF: check for a text layer: `python3 -c "from pypdf import PdfReader; r=PdfReader('/tmp/x.pdf'); print(len(r.pages)); print(r.pages[0].extract_text()[:500])"`.
  If pypdf is missing, use `pdftotext` or report "text layer not checked". Empty text = scanned.
- JSON: print the top-level keys, one record, the field names AND types, and the total count.
- Sample real content: quote 1–3 lines that prove the data is what we want (e.g. a fee, a date, an article).
- WebFetch is allowed for reading, but **confirm every format/endpoint claim with curl**.
  **Never report a count or a list from WebFetch alone.** In the pilot it undercounted member lists that curl+grep found in full.
- Read-only. Write scratch files only under `<scratchpad>/run3-<group>/`. Do not modify any repository.
- Budget: about 8 minutes per lead by default (actual 2026-09-23 runs: 27–43 min per agent for 4–10 leads), **up to 20 minutes** for a lead that turns out
  high-value (multi-commune coverage, an API, a platform). Every claim must come from a request you
  made. Otherwise write "not checked".
- Put the complete report in your final message. Do not rely on a backup file: the harness may block it.

## Report format: one block per lead, exactly this structure (≤ 350 words per lead)
```
### <id> — <short name>
- **AI claim:** <what the list says>  →  **Claim check:** Confirmed / Wrong / Partly (one line why)
- **Real location:** <final URL(s) you found; how you found them (ladder step #)>
- **What data is there:** <one to three sentences: content, language, coverage, volume/count>
- **Format:** <server HTML | JS shell | JS app + JSON API | PDF text | PDF scanned | JSON | ICS | CSV | XML | other>
  with evidence numbers (bytes, #links, words, pages, record count)
- **Sample:** <field names+types or a 1–3 line quote>
- **Dates & jurisdiction:** <dates found; node(s): CH-XX / CH-XX-BFS / multi-commune (list)>
- **Authority:** <per the rule>   **Categories:** <waste/dogs/taxes/parking/schools/...>
- **Can we get it?** Yes today (strategy) / Yes with new fetcher / Partly / No
- **Destination label (NEW v4):** exactly one of `yaml-now:<api|pdf|html_crawl>` · `fetcher:<name>` (use the names in
  `docs/sources/subnational_sources.md` §H, e.g. `fetcher:lexwork`, `fetcher:iweb-table`, `fetcher:pdf-index`, `fetcher:ics`) · `resolver` ·
  `design:<question>` · `not-a-source` · `blocked:<why>`
- **Landing-contract mapping (NEW v4):** which field gives url / title / identifier / valid_from / in_force / event_date / sections
- **Fetcher hint:** if today: a draft `fetch_config` YAML. If new: which new fetcher class
  (e.g. "PDF index discoverer", "ICS calendar", "paginated JSON", "OCR PDF", "vendor platform X"),
  the URL pattern(s), how to enumerate, how to split into sections, what gives the title/date/id.
  Also say whether the same fetcher would cover OTHER communes/cantons (same vendor, same template).
- **Ladder log (required unless the answer is a clean "Yes today"):** step 1…6 → result
- **Related finds (one hop):** <anything better you found on the way>
- **Unknowns:** <what you could not verify>
```
End your report with:
1. A **summary table**: id | can we get it | format | strategy/new fetcher | value (high/med/low).
2. **New fetcher classes needed**: a deduplicated list across your leads, each with the leads it
   would serve and roughly how many communes/cantons it would cover.
3. **Best finds**: the 3 most valuable sources you found (including one-hop finds), one line each.

---

# RUN 3 ADDENDUM (v5): courts, cantonal guidance, directories, city law. The GRID CONTRACT

This addendum overrides the per-lead report format above. You are not testing loose leads. You are filling a
**fixed grid for each of your cantons**. The orchestrator checks every grid. **If a cell is empty, or says "not found"
without the ladder log, you will be sent back to fill it.** Completeness is the job.

## Your inputs (already prepared; read them first, do not redo them)
All paths are under `<scratchpad>/`:
- `precheck_entry_points_2026-09-23.md`: **verified** entry points per canton (each answered 200 with real content), plus a
  **do-not-retry** list (invented domains, bot walls, rate limits, id traps). Start from these.
- `stage0/law_hits.json`: per canton and topic (dogs, court_fees, court_org, conciliation, holidays, tax, road), the matching
  **laws** from the official collections: systematic number, title, API URL. LexWork: `/api/{lang}/texts_of_law/{nr}` returns
  `canonical_link`. LexFind: `texts-of-law/{id}` returns `original_url`. Use these as the legal basis. Do not scrape law PDFs from court sites.
- `stage0/sitemap_topic_candidates.json`: per canton and topic, the count and the 40 shortest sitemap URLs
  (topics: courts, dogs, tax, holidays, road, communes, chancellery, city_law).
- `stage0/sitemaps/<host>.txt`: the **full** sitemap URL list per host. Grep it (e.g. `grep -i hund stage0/sitemaps/www.ag.ch.txt`).
  There was **no usable sitemap** for www.baselland.ch (Cloudflare), www.gr.ch (404), www4.ti.ch (only a culture-agenda map),
  www.vs.ch (99 URLs only), www.ne.ch (0 parsed), www.scan-ne.ch, www.chaux-de-fonds.ch, www.stadt-zuerich.ch.
- `opencaselaw_courts_2026-09-23.json`: decision coverage per court (code, canton, decision_count, earliest, latest).
  1,081,345 decisions, 136 courts, all 26 cantons. There is an Atom feed per court: `https://mcp.opencaselaw.ch/api/atom/{court}.xml`.
- The AI answers the user pasted, and their pre-check: `courts_s1_rows.py` + `courts_s1_probe.json`, `guidance_s3a_rows.py` +
  `guidance_s3a_probe.json`, `s3b_s4_rows.py` + `s3b_s4_probe.json`, `cities_s2_links.txt` (all 10 were 404).
- Earlier verified work: `reports/g5-guidance.md` (ZH/GE/BE/BS dogs, tax, holidays, road already verified) and
  `reports/g2-districts.md` (gerichte-zh.ch, BE Regierungsstatthalter, SZ districts). **Cite, do not redo.**

## The grid (one per canton): every cell is VERIFIED or NONE
| Cell | What |
|---|---|
| C1 courts-home | official courts portal or landing page of the canton |
| C2 court-fees | the fee page for residents **and** the fee ordinance (systematic number from law_hits.json) |
| C3 court-guidance | resident guidance pages (family/divorce, tenancy, employment, debt enforcement, inheritance, costs/legal aid): up to 10 URLs, format, and how many such pages the sitemap lists |
| C4 court-decisions | the court's own decision search (URL, format, API/feed?) **plus** opencaselaw coverage (court codes, counts, latest date). Flag it as stale if opencaselaw's latest date is before 2026. No deep dive |
| C5 conciliation | conciliation authority / justice of the peace / tenancy conciliation (Schlichtungsbehörde, juge de paix, conciliazione): URL, and whether it has guidance or fees |
| G1 dogs | cantonal guidance page(s) for dog keepers **and** the dog law or ordinance (systematic number) |
| G2 tax guide | Wegleitung / Steuerbuch / guide: URL, format, entry count, whether it is enumerable (sitemap, listing, API) |
| G3 school holidays | page / PDF / ICS / data. **Who sets them** (canton, or communes/schools with a cantonal recommendation?) |
| G4 road office | the office page + key pages (fees/tariffs, registration, licences) and format |
| D1 communes directory | the official cantonal list of communes, with links: URL, format, number of communes |
| D2 chancellery | the state chancellery page + the **official gazette** (Amtsblatt / Feuille officielle / Foglio ufficiale) URL |
| L1 city law | only for the cities assigned to you: the city's law collection (URL, platform: i-web / tlex / LexWork / PDF list / other, number of texts, whether dog/waste/parking regulations are present) |

**VERIFIED** means: URL + HTTP status + page `<title>` + format (server HTML / JS app / PDF text / PDF scanned / ICS / JSON / XLSX)
+ **one quoted sample line** (fees: a CHF amount; holidays: a date range; dogs: a rule; directory: a commune name + link).
**NONE** means: the full ladder with the result of each step: entry points → sitemap grep → the site's own search →
WebSearch `site:<host>` → navigation from the canton portal → law_hits.json. "None exists" is a valid answer only with that log.

Per canton, also give a **site recipe**:
- host(s), sitemap URL(s) and counts, CMS signature, robots / crawl-delay, bot walls;
- a **draft source YAML** for each ingestible piece: `html_crawl` (start_paths, path_allowlist, language), `pdf` (urls) or `api`.

Authority:
- court pages and cantonal guidance: `official_info`;
- law texts: `cantonal_law` through `fetcher:lexwork` (not your job to ingest);
- commune and city collections: `official_info` until the host is registered as a law platform.

Categories: `dogs, taxes, schools, transport, parking`. For courts use "category missing: courts".

**Order of work: breadth before depth.** First give every cell of every canton a VERIFIED-or-NONE answer (quick).
Then deepen: samples, counts, YAML. Budget about 60–70 minutes in total.

## New lessons from the pre-check (2026-09-23): obey them
1. **AI links:** only Gemini's directly shown links were reliable (21/22). Wrapped and plain-text links were mostly wrong
   (~5 of 193 and 20 of 76 usable). Dead links are already listed: **do not re-request them, and do not guess variants of
   invented domains** (gerichte-zg.ch, gerichte.tg.ch, tribunaux.vs.ch, vg.justice.be.ch, justiz-gr.ch, jgk.be.ch, gem.lu.ch, bare tg.ch).
   Report the correct URL next to each dead AI link ("claim check").
2. Court and office pages usually live **inside the canton portal**: bs.ch, sg.ch/recht/gerichte.html, ag.ch/de/ueber-uns/gerichte-kanton-aargau,
   vd.ch/ojv, ai.ch/gerichte, ur.ch/gerichtefs, so.ch/gerichte. Some have their own subdomain: gerichte.lu.ch, zsg.justice.be.ch, steuerbuch.lu.ch,
   strassenverkehrsamt.lu.ch/.tg.ch, justice.ge.ch, ocn.ch, scan-ne.ch.
3. **Bot walls:**
   - www.baselland.ch: Cloudflare "Just a moment…" (403). Try once with a full desktop Chrome User-Agent and report the result.
     Otherwise identify the URLs through WebSearch and mark the cell "blocked: Cloudflare". Use bl.clex.ch (laws) and data.bl.ch (data).
   - www.sz.ch and www.gl.ch return 429: wait ≥3 s between requests.
   - BE (*.be.ch) and BS (bs.ch) set Crawl-delay 10: be gentle.
4. **ID traps:**
   - gl.ch routes by the trailing number (any path ending /720 is the same page): check the `<title>`.
   - sh.ch: unknown ids answer 500 "Maintenance Page", but the site itself is up.
5. **No sitemap** for GR, TI, VS, NE, BL: navigate from the portal home, use the site search, and WebSearch `site:`.
6. **Decisions** are already aggregated (opencaselaw). Only record the court's own route and whether coverage is stale.
7. **Laws** come through LexWork/LexFind (law_hits.json). Cite systematic numbers. Pages that explain the law to residents are the guidance we want.
8. **School holidays** are often set by communes or schools. Say who sets them, and find the canton-wide source
   (ZH: XLSX per Schulgemeinde; GE: ICS; BS/BL: open data; BE: PDF).
9. Put the **complete report in your final message**: the harness may block report files. Scratch files go under `<scratchpad>/run3-<group>/`.

## Final message format
For each canton: the grid table (cells as rows: status VERIFIED/NONE/BLOCKED, URL, evidence, format, sample, notes), the site recipe, the draft YAMLs,
and the claim checks. Then a cross-canton section:
- new fetcher classes needed (reuse the names in brief v4: lexwork, iweb-table, pdf-index, sitemap-crawl, ics, xlsx, …);
- blocked items;
- the 5 best finds.
