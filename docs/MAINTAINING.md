# Maintaining the corpus

This guide is for the person who runs the server and maintains its data: building the corpus,
adding sources, refreshing them, loading lookup data and publishing the prebuilt database that
`setup` downloads. Everything here uses the `swiss-grounding` command from the repository root.
Settings are described in the README's Configuration section. The steps are drawn in
[`docs/diagrams/`](diagrams/README.md): the build in 01–07, the stored data in 08–12, refreshing in 13–15,
and the release in 30.

## Rules of thumb

1. **Set the budget to the credit you have.** `CORPUS_BUDGET_USD` is the hard cap across every paid
   stage, and `CORPUS_OCR_BUDGET_USD` the OCR share of it. Every paid command checks the cap before it
   spends. Never set it above the real credit.
2. **Test the key before a large run.** `corpus describe --what docs --limit 1 --sync` costs under a
   cent and proves the key, the model and the reply format.
3. **Run `corpus estimate` (or `corpus run --dry-run`) before `corpus run`.**
4. **Never write fake output into the real database.** `CORPUS_LLM_PROVIDER=fake` and
   `EMBEDDING_BACKEND=fake` are for tests. Paid commands refuse to write with them unless
   `--allow-fake` is passed; don't pass it outside tests.
5. **Never crawl one source twice at once.** A second `corpus fetch` may run beside a running one only
   with `--source` flags naming other sources. Check with `pgrep -fl "corpus fetch"`.
6. **Run long commands in `tmux` or with `nohup`.** Batch API commands poll for hours. Re-running the
   same command resumes it.
7. **Run from the repository root.** Paths to raw files and page images are stored relative to
   `DATA_DIR`, which is resolved from the working directory.

## Building from an empty database

1. **Prepare the machine.**

   ```bash
   docker compose up -d db
   uv sync --extra embed
   cp .env.example .env
   ```

   In `.env`, set the provider and its key (`CORPUS_LLM_PROVIDER=openai` with `OPENAI_API_KEY`,
   `CORPUS_LLM_PROVIDER=anthropic` with `ANTHROPIC_API_KEY`, or `CORPUS_LLM_PROVIDER=apertus` with
   `APERTUS_API_KEY`), the budget, and `EMBEDDING_BACKEND=sentence_transformers`.

2. **Create the schemas.**

   ```bash
   uv run swiss-grounding corpus init       # the public schema and the corpus schema
   ```

3. **Load the location tree.**

   ```bash
   uv run swiss-grounding db seed           # Switzerland, the cantons, every commune, the Zürich Kreise
   ```

   Every source's jurisdiction must exist in this tree, so `check-manifest` and `fetch` fail without
   it. The commune list comes from the snapshot `src/swiss_grounding/locations/data/communes.csv`;
   `locations fetch-register` regenerates it from the Federal Statistical Office and LINDAS.

4. **Create the serving tables.**

   ```bash
   uv run swiss-grounding serving init
   ```

5. **Check the manifest and fetch.**

   ```bash
   uv run swiss-grounding corpus check-manifest manifests/declared-scope.yaml
   uv run swiss-grounding corpus fetch --manifest manifests/declared-scope.yaml --tier 3
   uv run swiss-grounding corpus status
   ```

   `check-manifest` validates the file, requests every start URL and SR number, and reports robots.txt
   verdicts and language alternates. `fetch` costs nothing but takes hours: some sites ask for 10
   seconds between requests. `--tier 3` fetches every tier: 1 (the declared scope), 2 (other cantons
   and cities) and 3 (bulk and gazette collections); the manifest header says which is which. The
   default, `--tier 1`, skips the Run 3 sources.
   A `json` source whose manifest entry gives a `robots_exception_reason` is fetched where robots.txt
   disallows its documented API (Opendatasoft portals disallow `/api/` for every crawler except
   Googlebot) only with `ROBOTS_API_EXCEPTIONS=true`; the default is false, and each such request is logged.

6. **Import the Zürich waste calendar.**

   ```bash
   uv run swiss-grounding serving calendar
   ```

   It is not in the manifest; this command writes its documents like any other source, so the next
   step describes and embeds them too.

7. **Describe and embed.**

   ```bash
   uv run swiss-grounding corpus describe --what docs --limit 1 --sync   # key smoke test
   uv run swiss-grounding corpus estimate
   uv run swiss-grounding corpus run
   ```

8. **Load the premium data** (see "Lookup data" below).

9. **Publish the database** (see "Publishing the prebuilt database" below).

### Starting from a teammate's database instead

The crawl takes hours, so a teammate can hand over a copy. On the machine that crawled, after every
fetch has exited:

```bash
docker compose exec -T db pg_dump -U swiss -d swiss_grounding -Fc > corpus.dump
tar czf corpus-data.tgz data/        # raw files and page images; paths in the database are relative to data/
```

On the receiving machine, from the repository root:

```bash
docker compose up -d db
docker compose exec -T db pg_restore -U swiss -d swiss_grounding --clean --if-exists --no-owner < corpus.dump
tar xzf corpus-data.tgz
uv run swiss-grounding corpus status
```

Then run `corpus fetch` as in step 5 and `corpus run` as in step 7. `fetch` adds sources missing from
the copy and re-checks the rest.

## Adding a source

Sources are entries in `manifests/declared-scope.yaml`. Each entry has:

| Field | Meaning |
|---|---|
| `id` | Lowercase letters, digits and underscores; unique. |
| `name`, `publisher` | Shown to users; `publisher` is on every citation. |
| `authority` | `federal_law`, `cantonal_law` or `municipal_law` for the legal text itself; `official_info` for pages of governments and offices; `institutional` for other publishers. |
| `level`, `extent_id` | `federal`, `cantonal` or `municipal`, and the node of the location tree the source applies to (`CH`, `CH-VD`, `CH-GR-3762`). Every document of the source gets this jurisdiction. |
| `connector` | `fedlex`, `html`, or `json` for records from a JSON/REST API (its config keys are documented in `src/swiss_grounding/corpus/connectors/json_api.py`). |
| `tier` | 1 to 3. `fetch --tier N` takes every source at or below N. |
| `languages` | The languages to keep: `de`, `fr`, `it`, `en`, `rm`. |
| `config` | Connector settings, below. |

**`fedlex`** needs `config.sr_numbers`, a list of SR numbers. Each act is fetched in every listed
language, with its current consolidation and, when one exists, the next scheduled one. English is
optional: an act without an English version is not an error.

**`html`** needs `config.start_urls` and `config.allow_prefixes`. Optional keys:

| Key | Meaning |
|---|---|
| `max_pages` | Pages fetched per run (default 300). |
| `sitemap_urls`, `sitemap_include` | Sitemaps to seed the crawl from, and regular expressions a URL must match. |
| `language_links_selector` | CSS selector of the site's language switcher, when the pages carry no hreflang links. |
| `content_selector` | CSS selector of the content area, when the page has no usable `<main>`. |
| `pdf_allow_prefixes`, `pdf_link_patterns`, `max_pdfs` | Which linked PDFs to download (default: under `allow_prefixes`, at most 50). |
| `delay_seconds` | A longer delay between requests for this site. |

Two sources may not have overlapping URL prefixes; loading the manifest fails if they do.

Then:

```bash
uv run swiss-grounding corpus check-manifest manifests/declared-scope.yaml
uv run swiss-grounding corpus fetch --manifest manifests/declared-scope.yaml --tier 3 --source <id>
uv run swiss-grounding corpus run
```

`--source` only narrows the sources selected by `--tier`, which defaults to 1. A source of a higher
tier is silently skipped unless `--tier` is at least its tier.

and publish a new database when the evaluators should get it.

**Other kinds of source.** PDFs are only fetched when a crawled page links to them. A JSON feed needs
an importer of its own that turns its records into documents and saves them with
`corpus.persist.persist_document`, as `corpus/calendar.py` does for the OpenERZ waste calendar. Its
documents then get the same versioning as every other source.

## Refreshing

Re-running `corpus fetch` and then `corpus run` refreshes everything. Nothing is scheduled; run them
when the sources should be re-checked. Each source is crawled in its own thread (`--workers`, default
4), and its documents are written when that source finishes. At the end, `fetch` promotes scheduled
versions whose start date has arrived.

### What happens to each document

| Situation | Result |
|---|---|
| Same URL, same content | Only `last_seen_at` is updated. Pages the crawler did not reach through links are re-checked last, with a conditional request, so an unchanged page is not downloaded again. |
| Same URL, changed content | A new document with new chunks is written. The old one becomes `superseded`, points to the new one and gets a `valid_to`. It is never deleted. |
| New Fedlex consolidation | Its URL carries the consolidation date, so it is a new document. It becomes `current` and retires the older versions of the same act, language and source that started on or before it. |
| Consolidation that starts in the future | Stored as `scheduled`. It becomes `current` on its start date, at the end of a later `fetch`, and the version it replaces is retired then. |
| One language of a Fedlex act changed | Every language version of that act is downloaded again, so articles and paragraphs stay aligned across languages. |
| Page returns 404 or 410, or a known URL now redirects elsewhere | The document becomes `withdrawn`. |
| URL already owned by another source | Left alone and counted as a duplicate. |

After `fetch`, `corpus run` only works on what is new. A chunk whose text did not change keeps its
description, topics and boilerplate verdict from the earlier version. A vector is reused whenever the
embedded text is identical. So only changed chunks cost money.

Search only returns chunks of `current` documents, or, with `as_of`, the dated version in force on
that day, which may be a superseded one. Otherwise superseded, withdrawn and boilerplate chunks stay in
the database but are never cited.

### What a refresh does not retire

- A page the crawl did not reach because `max_pages` ran out stays `current`.
- A source removed from the manifest keeps its documents `current`; `fetch` only visits manifest
  sources.
- A Fedlex act with no consolidation in force any more is reported as an error, and its last version
  stays `current`.

To retire a whole source, run in the database (`docker compose exec db psql -U swiss -d swiss_grounding`):

```sql
update corpus.chunk c set status = 'withdrawn' from corpus.document d
 where d.id = c.document_id and d.source_id = '<id>' and c.status in ('current', 'scheduled');
update corpus.document set status = 'withdrawn' where source_id = '<id>' and status in ('current', 'scheduled');
delete from corpus.fetch_state where source_id = '<id>';
```

### What a chunk holds after each stage

| After | The chunk has |
|---|---|
| `fetch` | Its text, or empty text and a page image when the PDF page had too little text. |
| `ocr` | The transcribed text; the document's extraction becomes `ocr`. |
| `describe` | A description in its language and up to three topics, or status `boilerplate`. Document descriptions are written first, per translation group. |
| `embed` | A vector row per configured index, made from breadcrumb, description and text. |
| `index` | A vector index per language partition. Later embeddings are added to it automatically. |

Before describing, chunks whose exact text recurs in three or more documents of one source (footers,
cookie notices, contact blocks) are marked `boilerplate` for free. Law is exempt.

## The paid stages

### Providers

The pipeline runs with OpenAI, Anthropic or Apertus; switch with `CORPUS_LLM_PROVIDER` and the
matching key. OpenAI calls go through the Batch API at half price unless `--sync` is passed.
Anthropic calls are always synchronous. With `CORPUS_DIRECT_WORKERS` above 0, direct OpenAI calls run
beside the batches while describing: faster, at twice the batch price, and the budget is checked at
that price. Apertus runs direct calls only (no Batch API) and is priced at $0 for the hackathon key,
whose gateway caps it at 10M input and 2.5M output tokens; the ledger still records the tokens.
The key is also limited to 50,000 input and 12,500 output tokens per minute and 5 requests per
second. A description call uses about 1,200 input tokens, so a run tops out near 40 calls a minute;
runs use `APERTUS_WORKERS` (default 3) parallel calls, calls over the limit get a 429 and are
retried up to 8 times, and a task that still fails is quarantined and retried by the next run.

Prices live in `PRICES` in `src/swiss_grounding/corpus/budget.py`, per million tokens at batch
price. Check them against the provider's price list before a large run; a model missing from the
table is refused.

| Model | Input | Output |
|---|---|---|
| `text-embedding-3-large` | 0.065 | 0 |
| `gpt-5-mini` | 0.125 | 1.0 |
| `gpt-5-nano` | 0.025 | 0.2 |
| `claude-haiku-4-5-20251001` | 0.5 | 2.5 |
| `swiss-ai/Apertus-v1.5-70B` | 0 | 0 |

Synchronous calls cost twice these prices, except Apertus, which is always $0.

### What the key pays for

| Stage | Needs a key |
|---|---|
| `corpus fetch` | No |
| `corpus ocr` | Yes |
| `corpus describe` | Yes |
| `corpus embed` for `bge-m3` | No, it runs locally, but it embeds the descriptions |
| `corpus embed` for `openai-3l` | Yes (OpenAI), and only when it is in `CORPUS_INDEXES` |
| Serving | No |

A chunk without a description is only embedded with `--allow-undescribed`, as breadcrumb and text.
Once it is described, the next `embed` embeds it again.

### The whole run

```bash
uv run swiss-grounding corpus estimate          # pending work per stage, its cost, spend so far
uv run swiss-grounding corpus run --dry-run     # the plan, without writing
uv run swiss-grounding corpus run               # add --skip-ocr to leave scanned pages for later
```

`corpus run` does OCR, document descriptions, chunk descriptions (repeated while they progress), then
embeds and indexes every index in `CORPUS_INDEXES`, local first. OCR and descriptions that do not fit
the remaining budget run only the part that fits. A paid embedding index (`openai-3l`) that does not
fit is skipped, and its vector index is not built. If descriptions stop for lack of budget, the indexes
are still built over every chunk, and those chunks are embedded again once described. It ends with a
summary of every stage, the spend per kind and the embedding counts.

### Stage by stage

For inspecting each step, the stages can be run by hand:

```bash
uv run swiss-grounding corpus ocr --pilot 10                       # 10 pages synchronously, then a cost projection
uv run swiss-grounding corpus ocr                                  # the rest, in rounds of 1,000 pages
uv run swiss-grounding corpus describe --what docs --limit 5 --sync
uv run swiss-grounding corpus describe --what docs
uv run swiss-grounding corpus describe --what chunks               # repeat until it reports 0 tasks
uv run swiss-grounding corpus describe --what docs --source bazg --source bk_votes  # limit to these sources
uv run swiss-grounding corpus embed                                # every configured index
uv run swiss-grounding corpus index
```

Every paid command accepts `--dry-run`. When the budget refuses a stage, the message says how many tasks
fit; re-run with `--limit` that number. `corpus embed --limit` applies to the Batch path only.

Chunks whose position repeats within a translation group are described in a second pass, which is why
`describe --what chunks` is repeated.

To look at the results:

```sql
select id, description_by_lang, topics from corpus.translation_group
 where description_by_lang <> '{}'::jsonb order by id desc limit 5;
select id, language, description, topics from corpus.chunk where description <> '' order by id desc limit 20;
select count(*) filter (where sparse is not null), count(*) from corpus.emb_bge_m3;
```

### Resuming, batches and failures

Re-running the same command first collects that stage's unfinished Batch API jobs, then continues.
Unfinished batches count against the budget while they are in flight, so a second run cannot spend
past the cap. `corpus batches` lists every job.

A batch that fails, for example because it exceeded the account's enqueued-token limit, leaves its
tasks pending. Lower `CORPUS_CHAT_TOKENS_PER_FILE` or `CORPUS_EMBED_TOKENS_PER_FILE` and re-run.

`corpus status` reports documents per source, language and status, chunk and embedding counts, spend
per kind, unfinished batches and the quarantine count. The quarantine holds pages and tasks that failed
at fetch, persist, OCR or describe, with the reason and an attempt count:

```sql
select source_id, stage, reason, count(*) from corpus.quarantine group by 1, 2, 3 order by 1, 2, 3;
```

Re-running the stage retries them; an entry disappears once the retry succeeds. A page image that is
missing (usually the command was run outside the repository root) is quarantined and stays pending.

### Disk and memory before building indexes

Vector index builds need several GB of headroom. Check with `df -h .` and `docker stats --no-stream`.
Indexes are built one language partition at a time. Before raising `CORPUS_INDEX_PARALLEL_WORKERS`,
check that the container has the shared memory `docker-compose.yml` asks for:

```bash
docker compose exec db df -h /dev/shm        # must read 2.0G, not 64M
```

## Lookup data

### Health insurance premiums

BAG publishes the premiums yearly. For a business year (2026 below), put three files in
`data/premium/`:

1. **The premium table:** `Prämien_CH.csv` from the archive `Archiv_Praemien_2026.zip` on
   https://opendata.swiss/de/dataset/health-insurance-premiums.
2. **The premium regions:** the XLSX "Anhang der EDI Verordnung über die Prämienregionen" from
   https://www.bag.admin.ch/de/krankenversicherung-praemienregionen, converted to a semicolon CSV.
   It lists only the municipalities of cantons divided into premium regions; a canton it does not
   list has a single region, numbered 0 in the premium table, and `swiss_premium` uses that one.

   ```bash
   uv run --with openpyxl python -c "
   import openpyxl, csv
   wb = openpyxl.load_workbook('data/premium/regions_2026.xlsx', data_only=True)
   rows = list(wb['Anhang EDI Ver. über die PR'].iter_rows(values_only=True))
   start = next(i for i, r in enumerate(rows) if r[0] and 'Kanton' in str(r[0])) + 1
   with open('data/premium/regions_2026.csv', 'w', newline='', encoding='utf-8') as f:
       w = csv.writer(f, delimiter=';')
       w.writerow(['Kanton', 'BFS-Nr.', 'Gemeinde', 'Region'])
       w.writerows([r[0], r[1], r[2], r[3]] for r in rows[start:] if r[0] is not None and r[1] is not None)
   "
   ```

3. **The insurer names:** the premium table names insurers by BAG number only. The names come from
   BAG's register of approved insurers
   (https://www.bag.admin.ch/de/verzeichnisse-der-zugelassenen-kranken-und-rueckversicherer):

   ```bash
   curl -sL -o data/premium/insurers_2026.xlsx \
     "https://www.bag.admin.ch/dam/de/sd-web/wKeV97535ICf/Zugelassene%20Krankenversicherer_1.1.2026.xlsx"
   uv run --with openpyxl python -c "
   import openpyxl
   ws = openpyxl.load_workbook('data/premium/insurers_2026.xlsx', read_only=True)['Index   Indice   Index ']
   rows = [(int(r[1]), ' '.join(str(r[3]).split())) for r in ws.iter_rows(values_only=True)
           if isinstance(r[1], (int, float))]
   open('data/premium/insurers_2026.csv', 'w', encoding='utf-8').writelines(f'{n};{name}\n' for n, name in rows)"
   ```

Then load them:

```bash
uv run swiss-grounding lookups load-premiums data/premium/Prämien_CH.csv data/premium/regions_2026.csv 2026 \
  --insurers data/premium/insurers_2026.csv
```

Loading a year replaces that year's rows. The command warns about insurer numbers the register does
not name; those are shown as numbers.

### Zürich waste calendar

`serving calendar` imports the OpenERZ calendar of Stadt Zürich: one document per postal code, one
section per waste type with the upcoming dates. It lists dates from the day it runs, so re-run it
regularly, followed by `corpus run`. A changed calendar supersedes the previous version like any other
document. Its new chunks have no description yet, so `corpus embed` alone skips them; `corpus run`
describes and embeds them, and `corpus embed --allow-undescribed` embeds them for free without a
description.

### Reference interest rate and connections

Both are live. The reference rate is read from the BWO page and kept for 24 hours in
`serving.lookup_cache`; when BWO is unreachable, the last value is returned with its date. Connections
come from transport.opendata.ch on every call.

## Shared keys

The Supertext key and the zbern.ch token reach collaborators through the private release, never
through git. With both in your `.env`:

```bash
uv run swiss-grounding dump publish-key
```

uploads them as the asset `supertext.env` to the `corpus-latest` release. Every collaborator's next
`setup` writes them into their `.env`. To rotate a key, create a new one, put it in `.env`, run
`publish-key` again and revoke the old one. Anyone with access to the repository can read the asset,
so use keys dedicated to this project.

## Publishing the prebuilt database

```bash
uv run swiss-grounding dump export
gh release upload corpus-latest dist/* --clobber --repo thedionysus/swisscom-hackathon
```

`dump export` writes the database to `dist/` in parts of 150 MiB, with a manifest of their checksums,
and prints the exact `gh` command. The first time, create the release with
`gh release create corpus-latest dist/* --repo thedionysus/swisscom-hackathon --title "Prebuilt corpus"`
instead. The dump leaves out the
data of `public.chunk`, `public.document`, `public.document_change` and `public.eval_run` (the earlier
pipeline's content), the OpenAI vectors (`--openai` writes them to a separate `openai.dump`, which
`setup` does not restore), the call log and the lookup cache. Everything else is included: the location
tree, the corpus with its descriptions and bge-m3 vectors, and the premium tables.

When a new dump has fewer parts than the old one, delete the extra old parts from the release.
`setup` keeps every file already in `data/dump/`, including the manifest, so a collaborator who ran it
before restores the older database again. Tell them to delete `data/dump/` before running `setup`.

Before calling a release final, restore it once on a machine that has never seen the database (or
after `docker compose down -v`), time `setup` end to end, and ask one question through `serve`.
