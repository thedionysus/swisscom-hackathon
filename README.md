# Swiss Grounding MCP

An MCP server that answers questions about Swiss public rules and services with cited passages from
official sources. It knows which jurisdiction a question is about (Switzerland, a canton, a
municipality) and only cites evidence that applies there. It also answers three questions by lookup
instead of search: health insurance premiums, public transport connections and the reference interest
rate.

**This repository and its prebuilt database are private.** `setup` downloads the database from a
release of this repository with `gh`, using your own GitHub login, so you need access to the
repository and `gh auth login` before you start.

Maintaining the data (adding sources, refreshing, publishing a new database) is described in
[`docs/MAINTAINING.md`](docs/MAINTAINING.md). Measuring answer quality is described in
[`docs/EVALUATION.md`](docs/EVALUATION.md). Diagrams of the whole system, from ingestion to the tool
replies, are in [`docs/diagrams/`](docs/diagrams/README.md). To run the server and the tests on the newest
published database, which `setup` does not install, follow [`docs/USING-A-RELEASE.md`](docs/USING-A-RELEASE.md).

## Evaluation quick start

Items marked **TBD** are still being settled by the team.

1. **Commit to evaluate:** branch `main`.
2. **Transport:** stdio by default. Streamable HTTP with `--transport http`: path `/mcp`, port `8000`
   (change it with `--port`). In a container, add `--host 0.0.0.0`. There is no authentication.
3. **Runtime:** Python 3.12 (`.python-version`), managed by `uv` with the lockfile `uv.lock`. It also
   needs Docker with Compose, which runs PostgreSQL 16 with pgvector (`pgvector/pgvector:0.8.6-pg16`,
   published for arm64 and amd64), and the GitHub CLI `gh`. There is no prebuilt server image: the
   server runs from source, on CPU on Linux arm64.
4. **Setup**, from the repository root, without prompts once `GH_TOKEN` holds a token (or `gh auth
   login` has run) for an account with read access to this private repository:

   ```bash
   uv sync --extra embed           # Python dependencies, including torch and the model libraries
   uv run swiss-grounding setup    # creates .env, starts the Docker database, downloads, verifies
                                   # and restores the database, downloads bge-m3 and the reranker
   ```

   If `setup` and the server run in a container and Docker runs outside it (the Docker socket mounted
   into the container), `localhost:5433` does not reach the database. Export
   `DATABASE_URL=postgresql://swiss:swiss@host.docker.internal:5433/swiss_grounding` before `setup`
   and before starting the server; it overrides the value in `.env`.

   Needs about 15 GB of free disk and 6 GB of memory for Docker. Time: **TBD** (measured on an
   Apple silicon Mac).
5. **Start command:** `HF_HUB_OFFLINE=1 uv run swiss-grounding serve` for stdio, or
   `HF_HUB_OFFLINE=1 uv run swiss-grounding serve --transport http --host 0.0.0.0 --port 8000` for HTTP.
   The Docker database must be running (`docker compose up -d db` after a restart).
6. **Prebuilt data:** a PostgreSQL dump (documents, chunks, bge-m3 vectors) of about 900 MB in parts
   of 150 MiB, downloaded by `setup` from this repository's `corpus-latest` release and checked
   against the checksums in its manifest. `setup` also downloads the models `BAAI/bge-m3` and the
   reranker from Hugging Face. Rebuilding the corpus from the sources (crawl, OCR, descriptions,
   embeddings) is described in [`docs/MAINTAINING.md`](docs/MAINTAINING.md); the crawl alone takes
   hours, and descriptions need an LLM key.
7. **Credentials:** the server starts and answers without any of them. `DATABASE_URL` points at the
   Docker database and comes from `.env.example`; it is not a secret.

   | Variable | What it is for | Without it |
   |---|---|---|
   | `SUPERTEXT_API_KEY` | Translates questions into the other languages, and cited passages into the question's language | No translation: searches in other languages use vectors only |
   | `ZBERN_MCP_TOKEN` | The `zbern_*` tools: Swiss Parliament and federal popular votes, from zbern.ch | The `zbern_*` tools are not listed |
   | `GH_TOKEN` | Setup only: downloads the database from the private release | Run `gh auth login` instead |

   The values reach the organisers through their secure channel, never through the repository.
8. **Hosted endpoint:** none.
9. **Declared scope:** topics from the organisers' table:

   | # | Topic | Coverage |
   |---|---|---|
   | 1 | Health insurance premiums | Full: BAG information and the premium lookup `swiss_premium` |
   | 2 | Taxes and fees | Partly: VAT and official guidance; no computed tax bills |
   | 3 | Law and regulations | Full: federal law from Fedlex |
   | 4 | Waste collection and recycling | Municipal pages of the municipalities below |
   | 5 | Moving, registration, civil status | ch.ch and the municipalities below |
   | 6 | Residence permits and migration | SEM and ch.ch |
   | 7 | Social insurance and pensions | AHV/IV leaflets; no computed pensions |
   | 8 | Work and unemployment | arbeit.swiss |
   | 9 | Schools and education | Cantonal and municipal pages, including school holidays where published |
   | 10 | Public transport | Live connections through `swiss_connections` |
   | 11 | Road traffic and driving licences | Cantonal road traffic offices and federal law |
   | 12 | Housing and renting | BWO, and the reference rate through `swiss_reference_rate` |
   | 13 | Voting, elections, political rights | Federal Chancellery pages, and the `zbern_*` tools |
   | 14 | Companies, commercial register, VAT | Partly: how the register works; no company lookup |
   | 15 | Customs and ordering from abroad | BAZG |
   | 16 | Statistics, geodata, weather | Partly: MeteoSwiss hazard guidance; no live data |

   Geography: federal information for all of Switzerland; cantons ZH, BE, VD, GE, TI and GR;
   municipalities Zürich, Bern, Lausanne, Genève, Lugano, Chur and Scuol. At start the server adds
   every other canton and municipality the database holds current passages for, and `swiss_scope`
   returns the full list. Languages: German, French, Italian, Romansh and English.
10. **One example call:** `swiss_search` with

    ```json
    {"question": "Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps?", "locations": ["Vaud"]}
    ```

    Returns JSON with `status: "results"` and cited passages in French from vd.ch and ch.ch, each
    with its URL, publisher, jurisdiction and relevance score.
11. **Known limits:** places outside Switzerland; computed amounts such as tax bills or pensions (the
    rules and official calculators are cited instead); looking up a specific company; live weather,
    statistics and geodata; cantonal and municipal rules outside the places above. The first search
    after start waits until the models are loaded.
12. **robots.txt and terms of use:** `RESPECT_ROBOTS`, default `true`: the crawler obeys robots.txt.
    `ROBOTS_API_EXCEPTIONS`, default `false`: fetch a documented API that robots.txt blocks, for
    sources whose manifest gives a reason. `RESPECT_ROBOTS` also applies at question time, to the
    server's live requests to the BWO reference-rate page, the transport.opendata.ch API and the
    GeoAdmin API: each host's robots.txt is read once a day, and a request it disallows is not sent
    (the tool answers `source_unavailable`; for GeoAdmin, the place name counts as not recognised).
13. **Parallel use:** over HTTP, one server handles several conversations at the same time. `swiss_search`
    calls use the models one at a time and queue; the other tools run in parallel. Over stdio, each
    conversation starts its own server process. Start: the server answers the MCP handshake within
    seconds and loads the models in the background; the first search waits for them, **TBD** seconds
    on an Apple silicon Mac.

## What it covers

The `swiss_scope` tool returns this text, and the server repeats it whenever a question is not covered.
The six cantons and seven municipalities below are the floor: at start, the server adds every canton and
municipality its database holds current passages for, searches them, and names them in this text and in
its instructions. A canton with more than ten added municipalities is named with a count. For the
prebuilt database the text reads:

> Covered: federal information for all of Switzerland; cantonal information for Zurich, Bern,
> Vaud, Geneva, Ticino and Graubünden; municipal services for Zürich, Bern, Lausanne, Genève,
> Lugano, Chur and Scuol; lookups for health insurance premiums, public transport connections, the
> reference interest rate. Not covered: places outside Switzerland; computed amounts such as tax
> bills or pensions (the official rules and calculators are cited instead); looking up a specific
> company in the commercial register (how the register works is covered); live weather forecasts,
> statistics and geodata (MeteoSwiss hazard guidance is covered); cantonal and municipal rules
> outside the named cantons and municipalities.

The sources behind it are listed in [`manifests/declared-scope.yaml`](manifests/declared-scope.yaml):
Fedlex (federal law in German, French, Italian and English), ch.ch, federal offices, the six cantons'
administration sites and the seven municipalities' sites.

The challenge's five sample questions, and what the server returned for them on 2026-09-25 against
the local corpus, with translation switched off:

| # | Question | What the server returns |
|---|---|---|
| 1 | *Wann wird bei uns das nächste Mal Karton abgeholt?* (no place given) | `swiss_search` answers `needs_location`: only local pages (Chur, Zürich) answer the question, so it asks for the municipality. |
| 2 | *Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps?* | `swiss_search` with `locations=["Vaud"]` answers `results`. The vd.ch page "échanger un permis étranger" comes first, followed by other vd.ch pages and the ch.ch page on exchanging a licence, all in French. No federal ordinance article is among the citations. |
| 3 | *Premio mensile più basso, adulto 30 anni, Lugano, franchigia 2500?* | `swiss_premium(municipality="Lugano", age=30, deductible=2500)` looks the premiums up in the BAG table. When no premium data is loaded, it answers `source_unavailable` with "No premium data is loaded." |
| 4 | *Cura èn las vacanzas d'atun 2026 per la scola da Scuol?* (Romansh) | `swiss_search` finds Scuol in the question and answers `results` with one citation, a scuol.net services page in Romansh. The cited passage holds no holiday dates. |
| 5 | *Rundfunkbeitrag nach meinem Umzug nach Konstanz?* | With `locations=["Konstanz"]`: `outside_scope`, because Konstanz is not a Swiss municipality the server recognises. Without a location argument: `no_evidence`. |

## Quick start (no API key)

Requirements:

- **Docker**, with at least 6 GB of memory and about 15 GB of free disk for the database and the models.
- **`uv`**, the Python package manager.
- **The GitHub CLI `gh`**, logged in as an account with access to this repository (`gh auth login`).

Steps, from the repository root:

```bash
cp .env.example .env                  # points at the Docker database; no key needed to serve (setup does this too)
docker compose up -d db
uv sync --extra embed                 # torch, bge-m3 and the reranker libraries
uv run swiss-grounding setup          # download, verify and restore the database; download the models
uv run swiss-grounding serving ask "Échanger mon permis étranger, Vaud?" -l Vaud   # smoke test, prints JSON
uv run swiss-grounding serve          # the MCP server over stdio
```

`setup` downloads the database parts from the `corpus-latest` release, checks each part's checksum,
restores the database into the Docker container and creates the serving tables. It prints how long the
restore took. If the release carries the team's shared keys, it writes them into `.env`: the Supertext
translation key and the zbern.ch token. Without them, translation and the parliament tools stay off.
Finally it downloads bge-m3 and the reranker; `--skip-models` leaves that for the first start.

After `setup` has run once, set `HF_HUB_OFFLINE=1` so the model libraries stop checking the Hugging
Face Hub at every start. The server does not read it from `.env`: export it in the shell that starts
the server, or put it under `"env"` in the MCP client's config.

`setup` keeps every file already in `data/dump/`, including the dump's manifest. After a new release,
delete `data/dump/` before running `setup` again, or it restores the older database.

Things to know about the running server:

- **The first call waits for the models.** The server answers the client's handshake at once and
  loads bge-m3 and the reranker in the background. A `swiss_search` or `swiss_premium` call that
  arrives before they are loaded waits, up to 10 minutes.
- **Place names are checked with GeoAdmin.** A name that is not in the local location tree is looked
  up on `api3.geo.admin.ch` at question time. If that service is unreachable, such a name is treated
  as not recognised.
- **The reranker depends on the hardware.** On an Apple or NVIDIA GPU the server uses
  `BAAI/bge-reranker-v2-m3`. On CPU it uses the smaller `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
  and reranks 20 candidates instead of 30.

### Connect a client

The Docker database must be running whenever the server is used.

**Claude Code:**

```bash
claude mcp add swiss-grounding --scope user -- uv --directory "$(pwd)" run swiss-grounding serve
```

Open a new session and run `/mcp` to check that the `swiss_*` tools are listed, and the `zbern_*`
tools too when the zbern token is installed.

**Claude Desktop:** add this to `~/Library/Application Support/Claude/claude_desktop_config.json`
and restart:

```json
{
  "mcpServers": {
    "swiss-grounding": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/swisscom-hackathon", "run", "swiss-grounding", "serve"]
    }
  }
}
```

**Other clients over HTTP:** `uv run swiss-grounding serve --transport http` serves streamable HTTP at
`http://127.0.0.1:8000/mcp`. `--port` changes the port, and `--host 0.0.0.0` accepts connections from
other machines, for example from outside a container. There is no authentication.

## Tools

| Tool | Parameters | What it does |
|---|---|---|
| `swiss_search` | `question` (up to 2,000 characters), `locations` (up to 3 places), `translations` (the question in `de`, `fr`, `it`, `en` or `rm`), `as_of` (YYYY-MM-DD), `limit` (1–20, default 8) | Finds passages in official sources that answer the question, grouped per place. More than three places: the first three are searched and the reply says so. |
| `swiss_get_document` | `document_id` and `chunk_id` from a citation, or `reference`; optional `language` | Returns the whole article or section around a hit, or looks one up by reference: "Art. 336c OR", "SR 741.51 Art. 44", or an official URL. Abbreviations are known for BV, ZGB, OR, StGB, AIG, SVG, VZV, MWSTG, AHVG, KVG and AVIG in German, French and Italian. `language` switches to another language version. Returns up to 120 chunks, a `truncated` flag and the available languages. |
| `swiss_scope` | none | Returns the scope statement above. |
| `swiss_premium` | `municipality`, `age` (0–120), `deductible`, `accident` (default false), `model` (`any`, `standard`, `family_doctor`, `hmo`, `telmed`), `year` (default: the latest loaded), `limit` (1–20, default 5) | The cheapest monthly basic health insurance premiums from the BAG table, for the municipality's premium region. A canton is refused; a Zürich Kreis counts as the city. The deductible must be one the age class can choose. |
| `swiss_connections` | `origin`, `destination`, `date` (YYYY-MM-DD), `time` (HH:MM), `limit` (1–6, default 4) | The next public transport connections, live from transport.opendata.ch. |
| `swiss_reference_rate` | none | The current mortgage reference interest rate for rents, read from the BWO page, with its effective date. A value is reused for 24 hours. |
| `zbern_*` | discovered from zbern.ch | Swiss Parliament and federal popular votes, forwarded to the zbern.ch server. See below. |

Every `swiss_*` reply is JSON and carries the notice "Retrieved public information from Swiss sources.
Not legal advice." `zbern_*` replies are passed through from zbern.ch unchanged. The server tells clients to search in the user's own language, to pass every place the user
names, and to cite only the URLs it returns.

### Statuses

| Status | Meaning | What the client should do |
|---|---|---|
| `results` | Relevant passages were found. | Answer from the passages and cite their URLs. |
| `needs_location` | The answer depends on the place, or the place name fits several places. | Ask the user for the municipality, or which place they meant, then search again. |
| `outside_scope` | The place is outside Switzerland, or not recognised, or its level is outside the declared scope and nothing covered answers. | Say it is not covered. For a foreign place, suggest other sources. |
| `no_evidence` | Nothing in the indexed sources answers the question. | Say so. The `scope` field says what is covered. |
| `source_unavailable` | A live lookup's source could not be reached, or no premium data is loaded. `swiss_search` never returns it. | Say the source is unavailable; do not answer from memory. |
| `invalid_request` | A parameter is malformed, such as `as_of` not in YYYY-MM-DD. | Fix the request. |
| `error` | The server failed internally. | Retry once. |

A `swiss_search` reply has an overall `status`, a `places` list, a `message`, and `scope` whenever a
place ended in `no_evidence` or `outside_scope`. When places disagree, the overall status is the first
of: `results`, `outside_scope`, `needs_location`, `source_unavailable`, `no_evidence`,
`invalid_request`. Each place carries its own `status`, the resolved `location_id` and
`location_label`, a `message`, its `citations`, `coverage` (the number of documents at each level of
its path) and `uncovered_levels` (`cantonal` and/or `municipal` when those rules are outside scope).

### Citation fields

- `passage`: the part of the chunk that supports the answer, up to 600 characters, verbatim as published.
- `translated_passage`, `translation_language`: the passage in the question's language, when it was published in another. Answer from it, but quote and cite `passage`.
- `url`, `anchor`, `title`, `breadcrumb`: where the passage is and the headings above it.
- `document_id`, `chunk_id`: pass them to `swiss_get_document` for the whole article or section.
- `language`, `other_languages`: the passage's language and the other language versions of the same text.
- `publisher`, `authority`: who published it, and whether it is law (`federal_law`, `cantonal_law`, `municipal_law`) or information (`official_info`, `institutional`).
- `extent_id`, `extent_label`, `tier`: the jurisdiction the passage applies to, and how far above the asked place it sits (0 is the place itself, rising towards Switzerland).
- `relevance`: the relevance score between 0 and 1.
- `corroboration`, `corroboration_basis`, `versions_diverge`: whether the other legally binding language versions of the passage were found too, and whether they disagree on validity dates.
- `valid_from`, `modified_at`, `fetched_at`, `extraction`: when the text applies from (law), when the page was last changed, when it was fetched, and how its text was extracted (`native`, `pdf_text`, `ocr`).

### Swiss Parliament tools (from zbern.ch)

Questions about the Federal Parliament and federal popular votes (members, business items, debates,
roll-call votes, vote results down to municipality, upcoming votes) are answered by the hosted zbern.ch
MCP server, a separate server with its own data. This server lists its tools beside its own, prefixed
`zbern_`, and forwards the calls. The tools, their descriptions and zbern's instructions are read from
that server at start and again every five minutes, so they follow its changes. If it cannot be
reached, the `swiss_*` tools keep working and a `zbern_*` call answers `source_unavailable`. If it
has not been reachable at all since the server started, no `zbern_*` tools are listed.

The endpoint needs a bearer token, `ZBERN_MCP_TOKEN`, which `setup` installs from the release. By
default the four raw-SQL tools (`query`, `list_tables`, `describe_table`, `get_reference`) are not
served; `ZBERN_MCP_EXCLUDE` changes that.

## How a question is answered

### Resolving the place

1. **Places given in `locations`.** An entry that contains a country name (Germany, France, Italy,
   Austria or Liechtenstein, in five languages) is foreign. Otherwise the server tries, in order: a
   level word ("Kanton", "Stadt", "Gemeinde", "Quartier", "Kreis 3"), an exact name, a scan for names
   inside the text, GeoAdmin's commune search, and a one-letter typo match. Known names are the cantons
   in four languages, every Swiss commune, the Zürich Kreise and Quartiere, and postal codes that
   belong to exactly one commune.
2. **A name that fits several places** ("Wil") gives `needs_location` with the options.
3. **A name nothing matches** is treated as outside Switzerland: `outside_scope`, with a hint to check
   the spelling if it is a Swiss place.
4. **No `locations`.** The question itself is scanned for a Swiss place name, with guards against
   ordinary words that look like one. Failing that, a country after "in", "nach", "en" and similar
   ("in Deutschland") makes the question foreign. Otherwise the search covers all of Switzerland.
5. **A resolved place** is searched along its path (Switzerland, canton, municipality, Kreis), cut at
   the last level the declared scope covers.

### Searching and ranking

1. The question's language is guessed from its common words (German, French, Italian, English or
   Romansh). No model is involved.
2. With a Supertext key, the question is translated into German, French, Italian and English, skipping
   its own language. Translations sent by the client take precedence.
3. For each place, several searches run over the place's path, current documents and non-boilerplate
   chunks: a bge-m3 vector search in every language store; a bge-m3 sparse (word-weight) search; a
   keyword search in each language store, with the question in its own store and translations in the
   others (without a translation, only identifiers such as SR and article numbers and postal codes are
   used); and a vector search per translation, in that language's store. With `as_of`, dated law must
   be valid on that day and undated pages must be current.
4. The result lists are merged by rank into the top 30 candidates (20 on CPU). For a place below
   Switzerland, 10 of them are reserved for local pages.
5. Candidates are grouped by translation group, so the language versions of one article count once.
   The version in the question's language represents the group; failing that, the best-ranked legally
   binding version.
6. A cross-encoder reads each representative with the question, in the passage's language where a
   translation exists.
7. The relevance score is the reranker score when that is below 0.20. Otherwise it is half the reranker
   score plus half of 1 ÷ retrieval rank. Passages scoring below 0.20 are not cited. A fitted model
   replaces this score once `eval fit` has run; see [`docs/EVALUATION.md`](docs/EVALUATION.md).
8. Citations are ordered by relevance. Repeats are dropped: the same text under another URL, and other
   language versions of the same page (the question's language is kept). The passage is the best
   window of up to 600 characters, and passages in other languages are translated into the question's.

### Choosing the status

1. Foreign and unmatched places get `outside_scope`, and ambiguous ones `needs_location`, before any
   search.
2. Nothing relevant found: `outside_scope` when the place has cantonal or municipal levels outside the
   declared scope, otherwise `no_evidence`.
3. No place given, and relevant passages found: the server asks for the municipality (`needs_location`)
   when only local pages answer, or when pages from two or more places answer and no federal page
   settles it. A federal page does not settle it when the subject is one the communes or cantons set
   (dog tax, waste collection, registering a move, school holidays, municipal tax rate), or when the
   federal page itself says the canton or commune decides. Otherwise the answer cites federal passages
   only.
4. A Swiss place outside the declared scope with relevant federal evidence gets `results`, a message
   and `uncovered_levels` naming what is not covered.
5. Otherwise `results`.

## Where the data lives

**Files**, under `DATA_DIR` (default `data/`, relative to the working directory; not in git, not in the
prebuilt database):

| Path | Contents |
|---|---|
| `data/raw/<source>/` | The raw Fedlex XML and downloaded PDFs, named by a hash of the URL. HTML pages are not stored raw, only their parsed text. |
| `data/ocr/<source>/` | Images of PDF pages with too little text, waiting for OCR. |
| `data/batches/` | Batch API input files and a log of submitted batches. |
| `data/dump/` | Database parts downloaded by `setup`. Always `<repository root>/data/dump`, whatever `DATA_DIR` is. `dump export` writes new parts to `<repository root>/dist/`. |

**Database** (PostgreSQL 16 with pgvector, in Docker on port 5433):

- `public`: the location tree (Switzerland, cantons, every commune, the Zürich Kreise and Quartiere).
- `corpus`: sources, translation groups, documents, chunks (one partition per language), embeddings,
  and the bookkeeping for crawling, failures, spend and batch jobs.
- `serving`: the tool call log, the reference-rate cache and the premium tables.

**What a document and a chunk carry:**

| Record | Fields |
|---|---|
| Document | URL, language, translation group, title, identifier ("SR 220"), publisher, authority, jurisdiction (`extent_id`), whether the language version is legally binding (English Fedlex is not), `valid_from`/`valid_to`, status (`current`, `scheduled`, `superseded`, `withdrawn`), published, modified, fetched and last-seen dates, content hash, extraction method, the version that replaced it |
| Chunk | Position key (`align_key`, the same across language versions of a law article), order, breadcrumb, anchor, text, generated description, topics, jurisdiction, authority, status (or `boilerplate`), text hash, whether it still waits for OCR |
| Translation group | A generated description of the document in each language, and its topics |
| Embedding | The hash of the embedded text (breadcrumb, description and text), the vector, and bge-m3's word weights |

**Law and information.** Authority and jurisdiction are set per source in the manifest, never guessed
from the text. Today only Fedlex is law (`federal_law`); the other sources are `official_info`, and
Schweizer Wanderwege is `institutional`. Authority is shown on every citation and exempts law from the
repeated-furniture rule. The provisional relevance score does not use it; a fitted relevance model
does. Descriptions are part of what is
embedded and keyword-indexed. Topics are stored for later filtering but not used by search today.

## Configuration

Every setting comes from the environment or `.env`. The ones that matter:

### Keys and downloads per configuration

| You want to… | Settings | Needs |
|---|---|---|
| Serve with the default index | `SERVING_INDEX=bge-m3` (default) | No key. `setup` downloads bge-m3 and the reranker (`BAAI/bge-m3`, `BAAI/bge-reranker-v2-m3`, roughly 2.3 GB each on Hugging Face; the CPU fallback `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` is smaller). |
| Serve with the OpenAI index | `SERVING_INDEX=openai-3l` | `OPENAI_API_KEY` — every question is embedded with `text-embedding-3-large` — plus a database with OpenAI vectors (the prebuilt `corpus-latest` dump has none). The reranker still runs locally either way. |
| Restore the prebuilt database | `setup` (default `DUMP_RELEASE_TAG=corpus-latest`, bge-m3 vectors) | `gh auth login` with access to this repository; `setup` downloads the release with `gh release download`. |
| Use the Run 3 pre-release corpus | `DUMP_RELEASE_TAG=corpus-run3-cleaned-2026-09-25`, `SERVING_INDEX=openai-3l` | Same `gh auth login`, plus `OPENAI_API_KEY`: that release carries only `openai-3l` vectors, no bge-m3. |
| Translate questions and citations | `TRANSLATOR=supertext` or `apertus` | `SUPERTEXT_API_KEY` or `APERTUS_API_KEY` (`setup` installs the team's Supertext key if the release carries it). |
| Use the zbern parliament tools | `ZBERN_MCP_TOKEN` set | `ZBERN_MCP_TOKEN` (also installed by `setup` when the release carries it). |
| Build or extend the corpus | `CORPUS_LLM_PROVIDER=openai\|anthropic\|apertus`, `CORPUS_INDEXES` | The matching key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `APERTUS_API_KEY`); `OPENAI_API_KEY` again if `CORPUS_INDEXES` includes `openai-3l`. |
| Run evals | `EVAL_LLM_PROVIDER=openai\|anthropic\|apertus` | The matching key. `eval judge` and `eval faithfulness` also need the `claude` CLI logged in — the judge model is always Claude, whichever model answers. `--model apertus` needs `APERTUS_API_KEY` and a running HTTP server (`swiss-grounding serve --transport http`). |

See the tables below for every setting's default and purpose.

**Running the server**

| Setting | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | required | The database; `.env.example` points at the Docker one. |
| `SUPERTEXT_API_KEY` | unset | Translate questions and cited passages. Installed by `setup`. Costs Supertext credit per search. |
| `TRANSLATOR` | `supertext` | `supertext` (needs `SUPERTEXT_API_KEY`), `apertus` or `none` for question and citation translation. |
| `SUPERTEXT_TIMEOUT_SECONDS`, `APERTUS_TRANSLATE_TIMEOUT_SECONDS` | `8`, `8` | HTTP timeout for each translation call, per translator. |
| `TRANSLATE_QUERY_LANGUAGES` | `de,fr,it,en` | Languages the question is translated into. Romansh is off: the reranker over-scores weak Romansh passages against a Romansh query. |
| `TRANSLATE_CITATIONS` | `true` | Translate cited passages into the question's language. |
| `ZBERN_MCP_TOKEN` | unset | Turns on the `zbern_*` tools. Installed by `setup`. |
| `ZBERN_MCP_URL` | `https://mcp.zbern.ch/mcp` | Set it empty to turn the zbern tools off. |
| `ZBERN_MCP_EXCLUDE` | the four raw-SQL tools | zbern tools not to serve. |
| `SERVING_INDEX` | `bge-m3` | `openai-3l` searches the OpenAI index instead, which needs `OPENAI_API_KEY` for every question. The prebuilt database has no OpenAI vectors, so this only works on a corpus built with `openai-3l`. |
| `RERANKER_MODEL` | `auto` | `auto` picks by hardware; or a model name. |
| `HF_HUB_OFFLINE` | unset | Set to `1` after `setup` to stop model update checks. Read from the environment only, not from `.env`. |

**Building the corpus**

| Setting | Default | Purpose |
|---|---|---|
| `CORPUS_LLM_PROVIDER` | `fake` | `openai`, `anthropic` or `apertus` for OCR and descriptions. `fake` is for tests; paid commands refuse to write with it. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | unset | The key for the chosen provider. |
| `APERTUS_API_KEY` | unset | Key for Apertus on Swisscom's Swiss AI Platform. Needed by any setting set to `apertus` (`CORPUS_LLM_PROVIDER`, `EVAL_LLM_PROVIDER`, `TRANSLATOR`, `eval … --model apertus`). |
| `APERTUS_BASE_URL` | Swiss {ai} Weeks endpoint | The subscription's Production URL ending in `/v1`. |
| `APERTUS_MODEL` | `swiss-ai/Apertus-v1.5-70B` | Model id sent to that endpoint. |
| `APERTUS_WORKERS` | `3` | Parallel direct calls for a corpus run under `CORPUS_LLM_PROVIDER=apertus`, sized under the 5 requests/s limit. |
| `APERTUS_TIMEOUT_SECONDS` | `60` | HTTP timeout for each corpus/eval call to Apertus. |
| `EVAL_LLM_PROVIDER` | `openai` | `openai`, `anthropic` or `apertus`: writes `eval label` verdicts and `eval generate` questions. |
| `CORPUS_BUDGET_USD`, `CORPUS_OCR_BUDGET_USD` | `100`, `10` | Hard spending cap, and the OCR share of it. |
| `CORPUS_INDEXES` | `bge-m3` | Embedding indexes to build. Add `openai-3l` to also pay for the OpenAI index. |
| `EMBEDDING_BACKEND` | `fake` | Set to `sentence_transformers` to build the local bge-m3 index. |
| `RESPECT_ROBOTS` | `true` | Obey robots.txt while crawling, and for the server's live lookups (BWO, transport.opendata.ch, GeoAdmin). Keep it on unless a source's terms were checked. |
| `CRAWL_DELAY_SECONDS`, `FETCH_TIMEOUT_SECONDS` | `0.5`, `20` | Minimum delay between requests to one host (robots.txt and the manifest can raise it), and the HTTP timeout. |
| `DATA_DIR` | `data` | Where raw files, page images and batch files go. |
| `CORPUS_CHAT_TOKENS_PER_FILE`, `CORPUS_EMBED_TOKENS_PER_FILE` | `2000000` | Input tokens per Batch API file. Set to the account's enqueued-token limit. |
| `CORPUS_DIRECT_WORKERS` | `0` | Direct API calls run beside the Batch API while describing. Faster, at twice the batch price. |
| `CORPUS_INDEX_PARALLEL_WORKERS` | `0` | Parallel workers for building vector indexes. Needs the Docker shared memory set in `docker-compose.yml`. |
| `CORPUS_DOC_MODEL`, `CORPUS_CHUNK_MODEL`, `CORPUS_OCR_MODEL`, `CORPUS_ANTHROPIC_MODEL` | `gpt-5-mini`, `gpt-5-nano`, `gpt-5-mini`, `claude-haiku-4-5-20251001` | Models per task. |
| `DUMP_RELEASE_REPO`, `DUMP_RELEASE_TAG` | `thedionysus/swisscom-hackathon`, `corpus-latest` | Where `setup` downloads the database from. |

Candidate counts, the local quota, reranker limits, timeouts and service URLs can be tuned too; see
`src/swiss_grounding/config.py`.

## Development

```bash
uv sync --extra embed --extra eval
uv run pytest tests/unit
DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest -m integration
uv run ruff check src tests
```

The integration tests create a throwaway `swiss_grounding_test_*` database on that server and drop it
afterwards, so they are safe to point at the working database. Run them serially.

| Package (`src/swiss_grounding/`) | Contents |
|---|---|
| `corpus/` | Manifest, connectors (Fedlex, websites, PDFs, sitemaps), chunking, persistence and versioning, OCR, descriptions, embeddings, budget, Batch API runners |
| `serving/` | `swiss_search` and `swiss_get_document`: places, candidates, grouping, reranking, relevance, statuses, passages, translation; the dump and shared-key helpers |
| `mcp_server/` | The MCP server and its tools, and the zbern.ch proxy |
| `lookups/` | Premiums, public transport connections, reference rate |
| `locations/` | The location tree, the commune register snapshot, the place resolver, GeoAdmin |
| `evals/` | Golden set, relevance labels, fitting, generated questions, the judge |
| `cli/` | The `swiss-grounding` commands |
| `config.py`, `app.py` | Settings, and wiring the search service together |

`ingest/`, `retrieval/`, `registry/` and `db/` belong to an earlier pipeline, and so do the CLI
commands `query`, `ingest`, `db init`, `recontext`, `reclean`, `renarrow`, `retitle`, `sources`,
`load-fixture` and `eval probes`. The server's search does not use them; `serving ask` is the
command-line check of the live search. Some of their modules are still needed: `db/connection.py`,
`db/migrate.py` and `db/schema.sql` (the database connection and the location table),
`ingest/html_sections.py` (the crawler's HTML parser), and the `retrieval/` modules that `app.py`
imports.
