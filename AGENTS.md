# Instructions for agents working in this repository

Read this before running anything in the `swiss-grounding corpus …` pipeline, the encoding track that builds the
searchable corpus. The step-by-step procedure is `docs/ENCODING-RUNBOOK.md`; this file is the set of rules around it.

## What the pipeline is

`corpus fetch` crawls the declared sources (free). `corpus run` does everything after it in order: `ocr` and
`describe` (a paid language model), then `embed` and `index` for the configured indexes (bge-m3 locally, free). The
server answers questions from the local bge-m3 index and needs no key.

The local index embeds breadcrumb + description + text, and descriptions are written by the paid model. So even a
local build needs an API key for full quality (README, "Which steps need an API key").

## Providers are interchangeable

The pipeline runs with **OpenAI or Anthropic**. The choice is one setting, not a different procedure:

- Anthropic key: `ANTHROPIC_API_KEY=…` and `CORPUS_LLM_PROVIDER=anthropic`
- OpenAI key: `OPENAI_API_KEY=…` and `CORPUS_LLM_PROVIDER=openai`

Anthropic calls run synchronously. OpenAI calls use the Batch API unless `--sync` is passed.

## The serving keys are separate

`SUPERTEXT_API_KEY` is used by the running server only (ADR 0018): it translates each question into the other
language stores and the cited passages back. It never touches the corpus pipeline. Leave it unset to run the
server and the evals for free; set it before a golden run only when the run is meant to measure translation.
`ZBERN_MCP_TOKEN` likewise serves only the running server: with it present the server also lists the zbern.ch
parliament tools (`zbern_*`). Both come from the private release through `swiss-grounding setup`.

## Which work the key pays for is configuration

`CORPUS_INDEXES` (default `bge-m3`, local). With only local indexes, the key pays for OCR and descriptions; add
`openai-3l` to also build the OpenAI index. The code enforces this — use `corpus run` and don't pass `--index` by
hand.

## Rules

1. **Set the budget to the credit you have.** `CORPUS_BUDGET_USD` is the hard cap across all paid stages;
   `CORPUS_OCR_BUDGET_USD` is the OCR share of it. Every paid command checks the cap before it spends. Never raise
   the cap above the real credit.
2. **Smoke-test the key first.** Run one small sync call per paid stage before any full run:
   `corpus describe --what docs --limit 1 --sync`, then inspect `corpus.translation_group`. It costs under a cent
   and proves the key, the model and the reply format work.
3. **Then `corpus estimate` (or `corpus run --dry-run`), then `corpus run`.** It runs OCR, document and chunk
   descriptions, embeddings and indexes in the right order (descriptions before embeddings, so nothing is embedded
   twice). A paid stage that does not fit the remaining budget runs only the part that fits; if the credit runs
   out before every chunk is described, the index still covers every chunk. `--skip-ocr` leaves scanned pages for
   later. Re-running `corpus run` continues where it stopped.
4. **Don't run the stages by hand** (`ocr`, `describe`, `embed`, `index`) unless the person you work for asks; the
   runbook keeps them as the manual path.
5. **Never use fake providers against a real database.** `CORPUS_LLM_PROVIDER=fake` and `EMBEDDING_BACKEND=fake`
   are for tests; paid commands refuse to write with them unless `--allow-fake` is passed. Never pass it outside
   tests.
6. **Never crawl one source twice at once.** A second `corpus fetch` may run beside a running one only with
   `--source` flags naming other sources (other hosts); otherwise the same site is hit twice as fast and the two
   runs race on the same URLs. Check `pgrep -fl "corpus fetch"` first. Documents are written only when each source
   finishes crawling, so start paid stages after every fetch has exited.
7. **Long commands run in `tmux` or `nohup`.** Re-running the same command resumes it; submitted batches and
   finished work are skipped.
8. **Report what you did:** `corpus status` numbers, spend per kind, quarantine count, and anything refused.

## Starting from a handed-over database

A teammate may give you a database dump of the `corpus` schema plus the `data/` directory (raw files, PDF page
images). Restore both (see `docs/ENCODING-RUNBOOK.md`), then run `corpus fetch` once: it is incremental, so it
only adds sources missing from the dump or newly added to `manifests/declared-scope.yaml`, and re-checks the rest.
