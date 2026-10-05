# Running the server and the tests on a published database

This guide is for collaborators on `thedionysus/swisscom-hackathon`. `swiss-grounding setup` installs the
newest release into your `swiss_grounding` database. This guide restores a release **next to** your own
database instead, as `swiss_grounding_full`, for example to compare two databases or to keep data you built
yourself. Then it runs the MCP server and the golden tests on it. Every command runs from the repository root.

| Release | Contents |
|---|---|
| `corpus-full-sources-described-2026-09-25` | 252 sources, about 271,000 searchable chunks. Every document and chunk has a description, and every chunk has an OpenAI vector (text-embedding-3-large) made from its breadcrumb, description and text. |

## Before you start

- Access to this repository, and `gh auth login` done.
- Docker with at least 6 GB of memory, and about 25 GB of free disk: the parts, the joined dump and the
  restored database take about 4 GB each, and the models take the rest.
- `uv`.
- An OpenAI API key. This database has only OpenAI vectors, so every question is embedded with
  text-embedding-3-large.

## 1. Set up the repository

```bash
git clone https://github.com/thedionysus/swisscom-hackathon.git
cd swisscom-hackathon
cp .env.example .env
docker compose up -d db
uv sync --extra embed
```

With an existing clone, run `git pull` and `uv sync --extra embed` instead, and keep your `.env`.

## 2. Download and check the release

```bash
gh release download corpus-full-sources-described-2026-09-25 \
  --repo thedionysus/swisscom-hackathon --dir data/full-dump
cd data/full-dump
cat swiss_grounding-full-described-2026-09-25.dump.part* > swiss_grounding-full-described-2026-09-25.dump
shasum -a 256 -c swiss_grounding-full-described-2026-09-25.dump.sha256
cd ../..
```

The last check must print `swiss_grounding-full-described-2026-09-25.dump: OK`. `data/` is not tracked by git.

## 3. Restore it into a new database

```bash
docker compose exec -T db createdb -U swiss swiss_grounding_full
docker compose exec -T db pg_restore -U swiss -d swiss_grounding_full --no-owner \
  < data/full-dump/swiss_grounding-full-described-2026-09-25.dump
```

This takes about two minutes. Your own `swiss_grounding` database is not changed; `setup` would restore the
release over it instead.

## 4. Point the server at the new database

```bash
export DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding_full
export SERVING_INDEX=openai-3l
export OPENAI_API_KEY=sk-...
uv run swiss-grounding serving init
```

`serving init` prints `serving schema ready`. These variables take precedence over `.env` and last for the
current terminal session only.

## 5. Check the restore

```bash
LC_ALL=C sort data/full-dump/counts-full-described-2026-09-25.tsv \
  data/full-dump/counts-per-source-full-described-2026-09-25.tsv > data/full-dump/expected.tsv
docker compose exec -T db psql -U swiss -d swiss_grounding_full -At -F$'\t' \
  < data/full-dump/verify-counts.sql | LC_ALL=C sort > data/full-dump/restored.tsv
diff data/full-dump/expected.tsv data/full-dump/restored.tsv && echo "counts match"
uv run swiss-grounding serving ask "Échanger mon permis étranger, Vaud?" -l Vaud
```

Expect `counts match`, then a JSON reply with status `results` whose first citation is the vd.ch page
"Échanger un permis de conduire étranger".

## 6. Run the tests

```bash
uv run swiss-grounding eval golden --split all
```

This prints one line per golden question and a summary, and takes about four minutes. On 2026-09-25, with
`main` at `10559bf` (97 questions), it reported status accuracy 0.845 and recall@5 0.747. The golden set
changes with `main`, so other commits give other numbers. The other evaluation commands are described in
[`EVALUATION.md`](EVALUATION.md).

## 7. Connect an MCP client

The database container must be running (`docker compose up -d db`) whenever the server is used. The name
`swiss-grounding-full` keeps this entry apart from an existing `swiss-grounding` entry.

**Claude Code**, from the repository root:

```bash
claude mcp add swiss-grounding-full --scope user \
  -e DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding_full \
  -e SERVING_INDEX=openai-3l \
  -e OPENAI_API_KEY=sk-... \
  -- uv --directory "$(pwd)" run swiss-grounding serve
```

Open a new session and run `/mcp` to check that the `swiss_*` tools are listed.

**Claude Desktop:** add this entry to `~/Library/Application Support/Claude/claude_desktop_config.json`, then
restart the app:

```json
{
  "mcpServers": {
    "swiss-grounding-full": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/swisscom-hackathon", "run", "swiss-grounding", "serve"],
      "env": {
        "DATABASE_URL": "postgresql://swiss:swiss@localhost:5433/swiss_grounding_full",
        "SERVING_INDEX": "openai-3l",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

## Removing it

```bash
claude mcp remove swiss-grounding-full
docker compose exec -T db dropdb -U swiss swiss_grounding_full
rm -rf data/full-dump
```
