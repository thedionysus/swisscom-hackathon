# Evaluation

How answer quality is measured, how the relevance model is fitted, what has been measured so far, and
why the scorer looks the way it does.

## The gates

| Metric | Pass at | Measured by |
|---|---|---|
| Status accuracy | 0.9 | `eval golden`: the share of probes whose status is the expected one |
| Recall@5 | 0.8 | `eval golden` (expected sources in the top 5) and `eval recall` (generated questions) |
| Precision@5 | 0.7 | `eval golden`, over labelled citations |
| nDCG@5 | 0.7 | `eval golden`, over labelled citations |
| Faithfulness | 0.9 | `eval faithfulness`: answers written by a model through the MCP server, graded by a judge model |

## The golden set

`evals/golden/*.yaml` holds hand-written probes, split by level: `federal`, `cantonal`, `municipal`,
`scope` (questions that must be refused or asked back) and `challenge` (the challenge's sample
questions and practice cases). All files share one `version`. Each probe has:

- `question`, `locations`, `language`, `area` (one of the challenge's sixteen topic areas), `level`;
- `split`: `dev` for labelling and fitting, `holdout` for the reported numbers;
- `tool`: `swiss_search` by default; probes for other tools are kept in the set but not run by
  `eval golden`;
- `expect`: the `status`, and for a `results` probe the expected `sources` (URL fragments such as
  `233_245_233/20260701/de#art_94`) and the `key_fact` the answer must contain. `place_statuses` gives
  one status per place for multi-place probes.

The golden runner sends no client translations. With `SUPERTEXT_API_KEY` set, every probe spends
Supertext requests for the question and the cited passages. Run once without the key and once with it
to measure what translation adds; `TRANSLATE_CITATIONS=false` measures query translation alone.

## Running the evaluation

In this order, from the repository root, with `uv sync --extra embed --extra eval`:

```bash
uv run swiss-grounding eval golden --split dev
uv run swiss-grounding eval label --confirm-spend
uv run swiss-grounding eval label-check
uv run swiss-grounding eval fit
uv run swiss-grounding eval golden --split holdout --record
uv run swiss-grounding eval generate --confirm-spend
uv run swiss-grounding eval recall
uv run swiss-grounding serve --transport http        # in another terminal, for the next command
uv run swiss-grounding eval faithfulness
uv run swiss-grounding serving stats
```

What each step does:

- **`eval golden`** runs the `swiss_search` probes of a split (`dev`, `holdout` or `all`) and prints
  each probe's status against the expected one, then the metrics against the gates. `--record` writes
  the report, with the reranker, the threshold and the git commit, to `evals/golden/runs/`.
- **`eval label`** asks `gpt-5-mini` whether each citation answers its question: the top 10 citations
  per place of every `results` probe, plus 5 randomly chosen lower ones, searched with the threshold
  at 0 so the model also learns where to abstain. It needs `OPENAI_API_KEY`, is capped at $2 in the
  budget ledger, and appends to `evals/golden/labels.jsonl`. It then writes 100 pairs to
  `evals/golden/label_review.csv` for a person to check.
- **`eval label-check`** compares the model's labels with the `human_says` column you filled in, and
  fails below 0.85 agreement. `eval fit` does not check this; don't run it if `label-check` fails.
- **`eval fit`** fits the relevance model on the dev labels (see below) and reports its precision and
  recall on the holdout labels.
- **`eval generate`** has `gpt-5-mini` write one question for each of up to 35 random chunks per
  language and source level, into `evals/generated/questions.jsonl`. Capped at $2. These questions
  measure recall only; they are never used to tune anything.
- **`eval recall`** asks each generated question and checks whether the chunk it was written from is
  among the top 5 citations, per language and overall.
- **`eval faithfulness`** answers the holdout probes with `claude -p` (default model
  `claude-sonnet-5`) through the running server, using `evals/judge/mcp-http.json`, and has
  `claude-fable-5-1` grade each answer with `evals/judge/faithfulness.md`. It needs the `claude` CLI,
  writes `evals/judge/faithfulness.jsonl` and skips ids already in it. Errors and unparsed verdicts
  count as failures.
- **`serving stats`** prints p50 and p95 latency, the abstention rate and the empty-result rate per
  tool, from the call log of every served tool call.

`eval judge` is a separate cross-model check. It answers the probes marked `judge: true` in
`evals/probes/` with four models through the MCP server (`evals/judge/mcp.json`) and grades them with
`evals/judge/rubric.md` for jurisdiction confusion, authority mix-ups, outdated rules, the wrong
entity, unsignalled gaps in coverage and made-up URLs.

## The relevance model

Until a model is fitted, the server scores relevance provisionally: the reranker score when it is below
0.20, otherwise half the reranker score plus half of 1 ÷ retrieval rank, with a threshold of 0.20.

`eval fit` replaces that with a logistic regression over ten features: the reranker score (as a
logit), whether the passage is in the question's language, 1 ÷ retrieval rank, corroboration and
whether it applies, whether the corroborating versions were found independently, the tier and whether
it applies, whether the passage is law, and the page's age in years. The threshold is the lowest
probability at which out-of-fold predictions on the dev labels reach 0.9 precision.

The model is written to `evals/relevance_model.<reranker>.json`, with `/` in the reranker's name
replaced by `__`. The reranker depends on the hardware, so a model fitted on a GPU machine
(`BAAI/bge-reranker-v2-m3`) is not used on a CPU machine (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`),
which falls back to the provisional score. Commit the file for others to get it; it is not part of the
prebuilt database.

## Results so far

No golden-set run has been recorded in the repository, and no relevance model has been fitted.

Faithfulness, measured on 2026-09-24 with `claude-sonnet-5` answering the holdout probes:

| Run | File | Faithful |
|---|---|---|
| Without the zbern tools | `evals/judge/faithfulness-baseline.jsonl` | 11 of 12 |
| With the zbern tools | `evals/judge/faithfulness-zbern.jsonl` | 11 of 12 |
| With the zbern tools, after vote information pages were kept with `swiss_search` | `evals/judge/faithfulness-zbern-rerouted.jsonl` | 12 of 12 |

`evals/judge/results.json` is an `eval judge` run from 2026-09-21, made before the current server and
its tools existed. It does not describe today's behaviour.

## Why the scorer looks like this

Measured on an Apple M1 Pro with 16 GB, with sentence-transformers' `CrossEncoder`, on 2026-09-23 and
2026-09-24.

**Merging by rank cannot abstain.** Reciprocal rank fusion scores a chunk only by its rank in each
list, so the top chunk of every question gets about the same score whether or not it is relevant. It is
used to merge candidate lists, never as the confidence.

**The cross-encoder can abstain, but it is biased across languages.** `BAAI/bge-reranker-v2-m3` on
hand-picked pairs:

| Question | Passage | Score |
|---|---|---|
| DE "Kündigungsfrist Mietwohnung" | Art. 266c OR, German | 0.978 |
| same | Art. 266c CO, French (the same article) | 0.020 |
| same | Art. 266c CO, Italian (the same article) | 0.117 |
| same | Art. 335c OR, employment notice (wrong topic) | 0.013 |
| IT "termine di disdetta appartamento" | Italian / German / French 266c | 0.821 / 0.139 / 0.012 |
| RM "vacanzas d'atun Scuol" | Romansh / German Scuol calendar | 0.998 / 0.997 |
| same | German Zürich calendar | 0.436 |
| FR "permis de conduire Vaud" | French Vaud page | 0.997 |
| DE "Rundfunkbeitrag Konstanz" | five unrelated Swiss passages | all 0.000 |

Same-language scores separate relevant from irrelevant sharply, and a question with nothing relevant
scores near zero everywhere. But the same article in another language scores as if it were
irrelevant. So a passage is reranked against the question in its own language wherever a translation
exists, a group is represented by its question-language version, and the fitted model gets a
same-language feature. Place is not the reranker's job either: the Zürich calendar scored 0.44 for a
Scuol question, which is why the jurisdiction is a filter applied before scoring. The smaller
`mmarco-mMiniLMv2` model scored the cross-language pairs close to the same-language ones (German
question, French 266c: 0.98) and kept the rest of the pattern.

**Speed, 30 question–passage pairs of up to about 500 tokens:**

| Model | Device | Max tokens | 30 pairs |
|---|---|---|---|
| bge-reranker-v2-m3 | MPS | 512 | 2.7 s (2.4 s in fp16) |
| bge-reranker-v2-m3 | MPS | 256 | 1.5 s |
| bge-reranker-v2-m3 | CPU | 512 | 12.3 s |
| bge-reranker-v2-m3 | CPU | 256 | 4.5 s |
| mmarco-mMiniLMv2-L12 | CPU | 512 | 1.2 s |

On CPU the large model is about ten times slower, so a CPU machine uses the small model with 20
candidates of at most 256 tokens.

**The reranker alone mis-ordered real pages.** On the encoded corpus, for the Vaud licence question,
bge-m3 retrieval ranked the right vd.ch passage ("délai de 12 mois dès votre arrivée") first, but the
reranker scored it 0.29 and a wrong page 0.45. Hence the provisional blend with the retrieval rank,
which puts the Vaud page first (0.69). Markdown emphasis ("**12** **mois**") lowered the right
passage's score, so it is stripped before reranking (0.29 became 0.37). Scores below 0.20 keep the
reranker's value so that a question with nothing relevant still abstains.

**Duplicates filled result slots.** ch.ch serves many pages at two URLs with identical text, and HTML
sections of different language versions do not share position keys, so one page could appear three
times. Citations are de-duplicated by text and by translation group, preferring the question's
language.

**Romansh is not a translation target.** Measured on 2026-09-24, the reranker scored weak Romansh
passages 0.95 against a Romansh translation of the question (0.00 against the German question), which
pushed the right German page out of the top five. The Romansh store is still searched with the
multilingual embedding, and a Romansh question is translated into the other languages.

**How many labels a fitted model needs.** Logistic regression outputs are well calibrated, and Platt
(sigmoid) calibration suits small samples; isotonic calibration overfits below about 1,000 samples.
A common rule of thumb is 10 to 20 examples of the rarer outcome per feature, so about 100 to 200
relevant and as many irrelevant judged pairs.
