# Encoding runbook — 2026-09-24

Paid run for the declared-scope corpus (ADR 0009, `manifests/declared-scope.yaml`, tier 1). Verified against the
CLI as implemented (`uv run swiss-grounding corpus --help`, `corpus_commands.py`, `corpus_source_commands.py`,
`config.py`) on 2026-09-23, after the plan-review amendments (A1–A3). Supersedes the draft runbook in
`docs/superpowers/plans/2026-09-23-encoding-track.md` (Task 21 Step 3), which predates those fixes and drifted
from the shipped CLI in a few places — see the notes at the bottom.

**Pre-state (2026-09-23):** Fedlex is already fetched into the dev DB — 128 documents, 42,436 live chunks
(de/fr/it: 28 current + 10 scheduled each; en: 14 current). The HTML/PDF crawl
(`corpus fetch --manifest manifests/declared-scope.yaml --tier 1`) started 2026-09-23 evening and may still be
running or finished. `fetch` is incremental and free — re-running it just resumes, so Step 1 is safe either way.

**Why the local index waits for the key:** bge-m3 runs locally, but it embeds breadcrumb + description + text
(ADR 0005), and the descriptions come from the paid `describe` stage. Run `embed --index bge-m3` after `describe`,
or you will embed every chunk twice. A keyless build is possible with `--allow-undescribed` (lower quality; those
chunks are embedded again once described). See "Which steps need an API key" in the README.

**Where to run:** every command below runs from the repo root — page-image paths stored for OCR are relative to
`DATA_DIR`, which is resolved from the working directory. Run the paid commands (§5–§8) inside `tmux` (or
`nohup … &`, logging to a file): Batch API commands poll for hours, and a closed terminal kills the poll. If one
dies anyway, re-running the same command is the resume path (see "Resuming" below).

**Safety:** `ocr`/`describe`/`embed` without `--dry-run` refuse to write against a non-test database while
`CORPUS_LLM_PROVIDER` (or `EMBEDDING_BACKEND` for `bge-m3`) is `fake`, unless `--allow-fake` is passed. Never
pass `--allow-fake` against the dev database. `--dry-run` is always safe (no writes, no spend).

---

## 1. Check crawl status, resume if needed

First wait for any running fetch to exit — this must print nothing:

```bash
pgrep -f "corpus fetch"
```

Never run two fetches at once. A source's documents are written only when that source finishes, so a fetch that
is still running can look incomplete in `status`. Once nothing is running:

```bash
uv run swiss-grounding corpus status
uv run swiss-grounding corpus fetch --manifest manifests/declared-scope.yaml --tier 1
uv run swiss-grounding corpus status
```

Confirms documents exist for every declared source/language. `fetch` resumes incrementally and costs nothing.

## 2. Set up `.env`

Edit `.env` (based on `.env.example`):

```
OPENAI_API_KEY=sk-...
CORPUS_LLM_PROVIDER=openai        # default is "fake"; paid commands refuse to write with fake unless --allow-fake
CORPUS_BUDGET_USD=100
CORPUS_OCR_BUDGET_USD=10
EMBEDDING_BACKEND=sentence_transformers   # needed later for the local bge-m3 pass (uv sync --extra embed first)
CORPUS_CHAT_TOKENS_PER_FILE=<account limit>
CORPUS_EMBED_TOKENS_PER_FILE=<account limit>
```

`CORPUS_CHAT_TOKENS_PER_FILE` / `CORPUS_EMBED_TOKENS_PER_FILE` (config.py defaults: 2,000,000 each) are the
estimated input tokens per Batch API file. Files are submitted **one at a time**, so set these to the org's
actual per-model enqueued-token limit (OpenAI dashboard → Settings → Limits → Batch queue limits) — too small a
value means many sequential batches, each up to 24h. A batch that exceeds the account's limit fails and leaves
its tasks pending (see "Resuming" below).

Leave `ANTHROPIC_API_KEY` / `LLM_BACKEND` alone — the corpus track's Anthropic fallback
(`CORPUS_LLM_PROVIDER=anthropic`) is sync-only and not used in this run.

## 3. Verify prices

Check current per-token prices at https://developers.openai.com/api/docs/pricing (Batch API tier) against
`PRICES` in `src/swiss_grounding/corpus/budget.py`:

```python
PRICES = {
    "text-embedding-3-large": (0.065, 0.0),
    "gpt-5-mini": (0.125, 1.0),
    "gpt-5-nano": (0.025, 0.2),
}
```

`corpus_doc_model` = `gpt-5-mini`, `corpus_chunk_model` = `gpt-5-nano`, `corpus_ocr_model` = `gpt-5-mini`
(config.py). Edit `PRICES` if a price changed — every command prices from this table, and refuses with
"no price for ... in budget.PRICES" if a model used is missing.

## 4. Estimate (go/no-go)

```bash
uv run swiss-grounding corpus estimate
```

Prints per-stage estimates (OCR, describe docs, describe chunks, embed openai-3l), batches in flight, total
spent so far, and last a single go/no-go line:

```
total estimate (batch price): $X
```

`$X` = OCR + describe docs + the projected chunk pass (every group, once documents are described) + openai-3l
projected with descriptions. **Stop and re-scope (lower `max_pages` on the largest HTML sources, re-fetch) if that
total is above roughly $90** — the $100 cap (`CORPUS_BUDGET_USD`) refuses the run outright above $100, but leave headroom
for re-runs and the bge-m3 pass. Fedlex alone is ≈$2.70 at batch price (chunk descriptions ≈$1.68, embeddings
≈$0.95, doc descriptions ≈$0.03); HTML/PDF/OCR adds the rest.

## 5. OCR pilot, then full OCR

```bash
uv run swiss-grounding corpus ocr --pilot 10
```

Runs 10 pages synchronously, prints the measured per-page cost and a batch-price projection for the remaining
pages. Check that the projection fits under the $10 OCR sub-cap (`CORPUS_OCR_BUDGET_USD`). If it doesn't, either
accept a partial OCR pass with `corpus ocr --limit N`, or reduce the PDF scope (`max_pdfs` in the manifest) and
re-fetch. If the projection is near the $10 sub-cap, size `N` from the pilot's own numbers: `N` ≈ (sub-cap − spent
on OCR so far) ÷ the projected batch cost per page, rounded down with some margin.

A page whose image file is missing (e.g. the command was run outside the repo root) is quarantined — stage `ocr`,
reason `page image missing: <path>` — and skipped; it stays pending and is picked up by the next run from the
right directory.

```bash
uv run swiss-grounding corpus ocr
```

Runs the rest via the Batch API, in rounds of up to 1,000 pages, stopping if the OCR sub-cap or the total cap
would be exceeded.

Dry run form (no writes, no spend — safe to run any time): `uv run swiss-grounding corpus ocr --dry-run`.

## 6. Describe documents

```bash
uv run swiss-grounding corpus describe --what docs --limit 5 --sync
```

Runs 5 document-description tasks synchronously so you can inspect them immediately. Check the descriptions in
`corpus.translation_group`:

```sql
select id, description_by_lang, topics from corpus.translation_group where description_by_lang <> '{}'::jsonb order by id desc limit 5;
```

Are the languages right, is the act named correctly, is the jurisdiction right? Like `describe --what chunks`,
this first marks repeated site furniture as `boilerplate`, so document excerpts leave it out.

```bash
uv run swiss-grounding corpus describe --what docs
```

Runs the rest via the Batch API.

## 7. Describe chunks

```bash
uv run swiss-grounding corpus describe --what chunks --limit 20 --sync
```

Spot-check 20 chunk descriptions synchronously:

```sql
select id, language, description, topics from corpus.chunk where description <> '' order by id desc limit 20;
select count(*) from corpus.chunk where status = 'boilerplate';
```

Note: `describe --what chunks` first marks repeated site furniture as `boilerplate` (RAG review E2) — boilerplate
chunks are neither described nor embedded, so a lower task count than `corpus estimate` projected is expected.

```bash
uv run swiss-grounding corpus describe --what chunks
```

Runs the rest via the Batch API. **Then re-run the same command until it reports 0 tasks**: chunks whose
align_key repeats within a group are left for a second pass, so the first full run does not describe everything.
Only then move on to embedding. (`--what all` also exists — docs then chunks in one command — but running the
two phases separately, as above, is what lets you inspect docs before spending on chunks.)

## 8. Embed (openai-3l)

```bash
uv run swiss-grounding corpus embed --index openai-3l --dry-run
```

Prints the pending count and estimate with no writes. Confirm it is reasonable, then:

```bash
uv run swiss-grounding corpus embed --index openai-3l
```

This reuses embeddings from earlier document versions where possible (`reuse_embeddings`, RAG review E3)
before submitting new Batch API work for the rest.

## 9. Disk and Docker memory check before building the index

```bash
df -h .
docker stats --no-stream
docker info --format '{{.MemTotal}}'
```

~9 GB free was available on 2026-09-23; free more if needed before building — HNSW builds need several GB
headroom. Budget per language partition: OpenAI `halfvec(3072)` ≈ 6 KB/vector plus an HNSW index of similar
size again; `bge-m3` (1024-dim) ≈ 4 KB/vector. The DB container's `shm_size` is `2gb`
(`docker-compose.yml`); index builds run serially by default (`CORPUS_INDEX_PARALLEL_WORKERS=0` in config.py).
`corpus index` builds one HNSW index per language partition, one after another: de, fr, it, en, rm. Before
raising `CORPUS_INDEX_PARALLEL_WORKERS`, check that the container really has the 2 GB of shared memory:

```bash
docker exec swisscom-hackathon-db-1 df -h /dev/shm     # Size must read 2.0G, not 64M
```

## 10. Build the openai-3l index

```bash
uv run swiss-grounding corpus index --index openai-3l
```

## 11. Local index (bge-m3, free)

```bash
uv sync --extra embed
uv run swiss-grounding corpus embed --index bge-m3
uv run swiss-grounding corpus index --index bge-m3
```

Requires `EMBEDDING_BACKEND=sentence_transformers` (set in §2) — with `fake` (the default), `embed --index bge-m3`
refuses to write against the dev database unless `--allow-fake` is passed. With FlagEmbedding installed this also
fills bge-m3's sparse (lexical) vectors; check with:

```sql
select count(*) filter (where sparse is not null), count(*) from corpus.emb_bge_m3;
```

## 12. Final status

```bash
uv run swiss-grounding corpus status
```

Record: document counts per source/language/status, `chunks live=... described=... awaiting_ocr=...`,
`embeddings openai-3l: N` / `embeddings bge-m3: N`, spend per kind and total, `batches not ingested`, and
`quarantine: N`. Put these numbers in the commit or PR that reports the run.

## 13. Quarantine review

```sql
select source_id, stage, reason, count(*) from corpus.quarantine group by 1, 2, 3 order by 1, 2, 3;
```

`corpus.quarantine` holds documents/pages that failed at `fetch`, `persist`, or a describe/OCR stage, with the
reason and an attempt count (`attempts` increments on repeat failures of the same `(source_id, url, stage)`).
Re-running the relevant stage's command retries anything not yet fixed; entries clear automatically once the
retry succeeds.

---

## Resuming an interrupted run

Re-running the **same command** first collects that stage's unfinished batches (listed in `corpus.batch_job`,
kind `describe-doc` / `describe-chunk` / `ocr` / `embed`), then continues with new work. Unfinished batches count
against the budget cap even while still in flight, so a second run cannot silently double-spend past the cap.

```bash
uv run swiss-grounding corpus batches
```

Lists every Batch API job: id, kind, status, request count, estimate, submitted/ingested times.

If a batch failed (e.g. it exceeded the account's enqueued-token limit), its tasks are left pending in the
database — lower `CORPUS_CHAT_TOKENS_PER_FILE` / `CORPUS_EMBED_TOKENS_PER_FILE` in `.env` and re-run the same
`describe`/`ocr`/`embed` command; it will rebuild smaller files for the still-pending work.

---

## Notes on the plan draft (docs/superpowers/plans/2026-09-23-encoding-track.md, Task 21 Step 3)

The draft predates the plan-review amendments; a few details changed during implementation:

- Fake-provider writes now refuse against a non-test database unless `--allow-fake` — never pass it here.
- `corpus describe --what all` exists (docs then chunks in one call) alongside `docs`/`chunks` separately; run
  them separately (§6–§7) so docs can be inspected before paying for chunks.
- `corpus embed --limit` applies only to the Batch path, not the local bge-m3 path.
- `corpus ocr --pilot N` always runs sync, regardless of `--sync`.
- `corpus status` already reports live/described/awaiting-OCR chunk totals, so §12 uses it instead of the
  draft's hand-rolled `psycopg` query.
