# Instructions for agents working in this repository

Read this before running anything in the `swiss-grounding corpus …` pipeline, the encoding track that builds the
searchable corpus. The step-by-step procedure is `docs/ENCODING-RUNBOOK.md`; this file is the set of rules around it.

## What the pipeline is

`corpus fetch` crawls the declared sources (free). `corpus ocr` and `corpus describe` call a paid language model.
`corpus embed --index bge-m3` embeds every chunk locally (free). `corpus index` builds the search indexes. The
server answers questions from the local bge-m3 index and needs no key.

The local index embeds breadcrumb + description + text, and descriptions are written by the paid model. So even a
local build needs an API key for full quality (README, "Which steps need an API key").

## Providers are interchangeable

The pipeline runs with **OpenAI or Anthropic**. The choice is one setting, not a different procedure:

- Anthropic key: `ANTHROPIC_API_KEY=…` and `CORPUS_LLM_PROVIDER=anthropic`
- OpenAI key: `OPENAI_API_KEY=…` and `CORPUS_LLM_PROVIDER=openai`

Anthropic calls run synchronously. OpenAI calls use the Batch API unless `--sync` is passed. Only the optional
`openai-3l` index needs an OpenAI key; skip `embed --index openai-3l` and `index --index openai-3l` without one.

## Rules

1. **Set the budget to the credit you have.** `CORPUS_BUDGET_USD` is the hard cap across all paid stages;
   `CORPUS_OCR_BUDGET_USD` is the OCR share of it. Every paid command checks the cap before it spends. Never raise
   the cap above the real credit.
2. **Smoke-test the key first.** Run one small sync call per paid stage before any full run:
   `corpus describe --what docs --limit 1 --sync`, then inspect `corpus.translation_group`. It costs under a cent
   and proves the key, the model and the reply format work.
3. **Always run `--dry-run` or `corpus estimate` before a paid command.** If a stage is refused for budget, the
   message says how many tasks fit; re-run with `--limit <that number>`. Spend in this order: document
   descriptions, chunk descriptions, OCR.
4. **Order matters:** documents are described before chunks, and chunks before `embed`. Otherwise every chunk is
   embedded twice. If the credit runs out, finish with `corpus embed --index bge-m3 --allow-undescribed`.
5. **Never use fake providers against a real database.** `CORPUS_LLM_PROVIDER=fake` and `EMBEDDING_BACKEND=fake`
   are for tests; paid commands refuse to write with them unless `--allow-fake` is passed. Never pass it outside
   tests.
6. **One fetch at a time.** Check `pgrep -f "corpus fetch"` prints nothing before starting a fetch or a paid
   stage. Documents are written only when each source finishes crawling.
7. **Long commands run in `tmux` or `nohup`.** Re-running the same command resumes it; submitted batches and
   finished work are skipped.
8. **Report what you did:** `corpus status` numbers, spend per kind, quarantine count, and anything refused.

## Starting from a handed-over database

A teammate may give you a database dump of the `corpus` schema plus the `data/` directory (raw files, PDF page
images). Restore both (see `docs/ENCODING-RUNBOOK.md`), then run `corpus fetch` once: it is incremental, so it
only adds sources missing from the dump or newly added to `manifests/declared-scope.yaml`, and re-checks the rest.
