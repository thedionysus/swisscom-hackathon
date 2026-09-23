S=<scratchpad>
{ sed 's/^# Brief v4: source verification agents (read fully before starting)/# Brief v5: source verification agents (read fully before starting)/' $S/agent_brief_v4.md; cat <<'E'

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
E
} > $S/agent_brief_v5.md
wc -l $S/agent_brief_v5.md; grep -c "RUN 3 ADDENDUM" $S/agent_brief_v5.md
