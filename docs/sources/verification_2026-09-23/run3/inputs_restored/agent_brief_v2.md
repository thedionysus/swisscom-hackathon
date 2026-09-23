# Brief v2: source verification agents (read fully before starting)

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

## THE MOST IMPORTANT RULE: do not give up early
Earlier agents stopped at "it's a JavaScript site" or "404". That is not an acceptable finish.
**Before you are allowed to write the verdict "Blocked" or "No data" for a lead, you must have tried
every step of this ladder and recorded the result of each:**

1. The given URL with curl (follow redirects, browser-like User-Agent).
2. If 404 or a bare domain: the site root, then `/sitemap.xml`, `/sitemap_index.xml`, `robots.txt`
   (which often lists sitemaps), and the site's own search (`/suche?q=`, `/search?q=`, `?s=`).
3. A WebSearch restricted to the host (`site:host.ch Reglement`, `site:host.ch filetype:pdf`,
   in the right language: Reglement / Verordnung / règlement / regolamento / Gebühren / tarif / Ferien).
4. If the page is a JavaScript shell: read the JS bundles (`<script src>`) and grep them for `api`,
   `json`, `graphql`, `/rest/`, `fetch(`, `.json`. Try the endpoints you find. Look for
   `__NEXT_DATA__`, `window.__INITIAL_STATE__` or JSON-LD embedded in the HTML.
5. Look for alternative outputs: RSS/Atom, `?format=json`, `.ics`, CSV/XLSX downloads, "Open Data",
   "Schnittstelle", "API", "Download" links, and the canton's open-data portal or opendata.swiss
   for the same content.
6. One hop: if the page names a different official host that holds the real content (a cantonal
   law collection, a commune-association site, a vendor platform), follow it and apply the ladder there.

Only after all six steps may you conclude it is not obtainable, and you must list what each step
returned. "I tried X, got Y" is valuable. "It seems not available" is not.

Also: **we can build new fetchers.** "Our four strategies can't read it" does NOT mean "not
usable". If the data is reachable, your job is to describe how a new fetcher would get it.

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

## Method
- `curl -sL -A "Mozilla/5.0 swiss-grounding-check" -o /tmp/<file> -w "%{http_code} %{content_type} %{size_download}B %{url_effective}\n" <url>`
- HTML: count `<a href` occurrences and words after stripping tags. ~2 KB with 0 links = JS shell.
- PDF: check for a text layer: `python3 -c "from pypdf import PdfReader; r=PdfReader('/tmp/x.pdf'); print(len(r.pages)); print(r.pages[0].extract_text()[:500])"`.
  If pypdf is missing, use `pdftotext` or report "text layer not checked". Empty text = scanned.
- JSON: print the top-level keys, one record, the field names AND types, and the total count.
- Sample real content: quote 1–3 lines that prove the data is what we want (e.g. a fee, a date, an article).
- WebFetch is allowed for reading, but **confirm every format/endpoint claim with curl** (WebFetch paraphrases).
- Read-only. Write scratch files only under `/tmp/sg-verify-<your-group>/`. Do not modify any repository.
- Budget: about 8 minutes per lead, and spend more on a lead that looks valuable. Breadth of
  *verified* findings beats speculation. Every claim must come from a request you made.
  Otherwise write "not checked".

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
- **Fetcher hint:** if today: a draft `fetch_config` YAML. If new: which new fetcher class
  (e.g. "PDF index discoverer", "ICS calendar", "paginated JSON", "OCR PDF", "vendor platform X"),
  the URL pattern(s), how to enumerate, how to split into sections, what gives the title/date/id.
  Also say whether the same fetcher would cover OTHER communes/cantons (same vendor, same template).
- **Ladder log (only if not fully obtainable):** step 1…6 → result
- **Related finds (one hop):** <anything better you found on the way>
- **Unknowns:** <what you could not verify>
```
End your report with a **summary table**: id | can we get it | format | strategy/new fetcher | value (high/med/low).
