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

Anthropic calls run synchronously. OpenAI calls use the Batch API unless `--sync` is passed.

## The API key is for OCR and descriptions only, never for embeddings

Embeddings are computed **locally** with bge-m3 (`corpus embed --index bge-m3`), and the server answers from that
index. **Do not run `corpus embed --index openai-3l` or `corpus index --index openai-3l`**, even when an OpenAI key
is set, unless the person you work for explicitly asks for the OpenAI index. Those two steps are optional and are
marked so in the runbook. `corpus estimate` prints an `embed openai-3l` line and includes it in its total; subtract
it when judging what the run will cost.

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
