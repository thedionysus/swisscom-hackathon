# Finding: Jev tags chunk topics best as one choice with structured criteria and a "none" option

**Status (2026-09-24):** in-sample result, **not yet confirmed**, and nothing is implemented. Everything
below compares ways of asking **Jev** (TypeSafe's judgment model). The production topics, which the paid
describe call writes, were not measured. A fresh labelled sample decides whether this goes further (§6).
Code references are to `main` at `159ac23`.

## TL;DR

**Recommended design (E4):** one `choice` question per chunk over the topics plus `none_of_these`. Each
option is described in Winnow's structured form: `what` / `examples` / `not_for`.

| Design, same 75 municipal chunks, same sealed labels | Precision (95% CI) | Recall (95% CI) | False topics on junk |
|---|---|---|---|
| **E4: one choice, structured criteria, "none" option** | **0.91** (0.62–0.98) | **0.91** (0.62–0.98) | **1** |
| E3: one choice, one-line criteria, "none" option | 0.77 (0.50–0.92) | 0.91 (0.62–0.98) | 3 |
| M1: ten independent yes/no questions, "top if ≥ 0.10" | 0.29 (0.15–0.49) | 0.64 (0.35–0.85) | 10 |

- **The big step is from ten yes/no questions to one choice with "none".**
  - Per chunk, E3 made fewer errors than M1 on 16 chunks and more on 1 (sign test p = 0.0003).
  - On German pages: 0.07 / 0.20 → 0.57 / 0.80, and 0.80 / 0.80 with E4.
- **Structured criteria add a little on top.** E4 removed two of E3's three junk errors and added none. That
  is a 2-chunk difference (p = 0.5), so it is a hint, not proof.
- **Ranking was never the problem.** All three designs put gold topics above the rest almost perfectly (AUC
  0.999 / 0.998 / 0.986). They differ in where the cut falls between "a topic" and "none", and an explicit
  "none" option supplies that cut.
- **Limits:**
  - In-sample: the designs were fixed after M1's errors had been seen.
  - The old ten categories; production now has twenty (ADR 0007).
  - Only 11 gold-positive pairs.
  - Effectively one topic per chunk, where production allows three.

## 1. The three designs

| | M1 | E3 | E4 (recommended) |
|---|---|---|---|
| Question | 10 `noul` (yes/no) | 1 `choice`, 11 options | 1 `choice`, 11 options |
| Instructions | "The passage is about {label} ({desc}): a person asking a question on this topic would want this passage as evidence." | "Which of the listed topics does the passage's own content in `item.passage` concern? Pick the single best match." | same as E3 |
| Option text | true / false criteria per question | `"<label>: <desc>"`, plus `none_of_these`: "The passage's own content concerns none of these topics" | `{what: <label>, examples: <desc split at commas>, not_for: <shared>}`, plus `none_of_these` as `{what, examples}` |
| Decision | top category if its probability ≥ 0.10 | the choice, unless `none_of_these` | same as E3 |
| Fixed before calls | `municipal/prereg.json` | `typesafe-mcp/prereg_typesafe.json` | `typesafe-mcp/prereg_e4.json` |

- **E4's shared `not_for`:** "A topic the passage only mentions in passing; page furniture (navigation, a
  cookie notice, contact details or other page furniture with no substantive content) has no topic."
  - It restates two rules the labellers were given, in production's own boilerplate wording
    (`corpus/describe.py:60-61`).
  - The structured form follows GhalebDweikat/winnow `sidecar/src/winnow/questions.py:43-70`.
- **Same for all three:**
  - the 75 chunks (Stadt Zürich, Ville de Genève, Kanton Zürich; German and French; text ≤ 1,500 characters);
  - the model `typesafe-ai/jev` via Vercel AI Gateway;
  - the gold from two blind labellers (κ 1.00 on junk, 0.78 on topics).
- **Gold rule:** a (chunk, topic) pair is positive when both labellers call the topic primary; negative when
  neither lists it at all; otherwise excluded.

## 2. Results in detail

| Subset | E4 | E3 | M1 |
|---|---|---|---|
| German, 49 chunks | 0.80 / 0.80 | 0.57 / 0.80 | 0.07 / 0.20 |
| French, 26 | 1.00 / 1.00 | 1.00 / 1.00 | 0.67 / 1.00 |
| Content both labellers agree on, 40 | 1.00 / 0.91 | 1.00 / 0.91 | 0.50 / 0.64 |
| Junk both labellers agree on, 35 | 1 false topic, 25 "none" | 3 false topics, 23 "none" | 10 false topics |
| AUC over (chunk, topic) pairs | 0.999 | 0.998 | 0.986 |

E4's two remaining errors:

| Chunk | What it is | Gold | E4 answered |
|---|---|---|---|
| stadt_zuerich#0 (de, junk) | "Umwelt und Energie" hub page, links including Entsorgung | none | `waste` 0.84, none 0.16 |
| zh_ch#772 (de, content) | registering livestock with the veterinary office | dogs ("Dogs and pets") | none 0.61, dogs 0.36. The old text named no livestock; the new `animals` topic does |

E3's extra two errors were both on junk chunks, and E4 fixed both:
- a contact card of the nature-protection office, which E3 tagged hiking at 0.55;
- a feedback widget ("Ist diese Seite verständlich? Ja Nein"), which E3 tagged waste at 0.58.

## 3. Why it probably works (*inferred*; the factors were not tested one at a time)

1. **Yes/no answers for topics come out low and bunched together.** Correct federal labels scored as low as
   0.09; German pet pages scored 0.08–0.10. So no fixed cutoff works, although the ranking is fine
   (AUC 0.986). A `choice` spreads one unit of probability over the options, so the best option stands out.
2. **An explicit "none" gives junk and off-list content somewhere to go.** With ten yes/no questions, 22
   of 35 junk chunks got a topic.
3. **`not_for` puts the labelling rules into the question.** Passing mentions and page furniture get no
   topic, which is what removed E4's two extra junk errors.

Winnow reports the same pattern on its own task: ordering right, probabilities underconfident. That is its
measurement, not reproduced here.

## 4. What this does not show

- **Confirmation on fresh data.** The designs were chosen after seeing M1's errors.
- **The twenty production topics.** Their boundaries differ: `building` is split from `housing`, and
  `municipal_services` is a broad administrative topic.
  - In a two-chunk smoke test with the twenty, a title-only junk chunk got `municipal_services` (0.51)
    under plain criteria and `none_of_these` (0.42) under structured ones. One chunk is not evidence.
- **Multi-topic chunks.** None were in the gold. A single choice gives one topic: keeping near-ties added no
  second topic to any chunk.
- **Italian; federal or cantonal law text; other sites.**
- **Production topic quality.** It has never been scored on labels like these.

## 5. Where it would sit in the current system

```
corpus fetch ─► corpus run:  ocr ─► describe ─────────────────────► embed ─► index
                                   (paid LLM: descriptions,
                                    ≤ 3 topics, boilerplate flag)
                                          │
                                          └─► NEW: jev-topics   (E4 question, about $0.05 per 1,000 chunks)
                                                  writes a side table, reports where Jev and chunk.topics disagree
serving (no key, no model call): reads the stored topics as a filter
```

- **Where topics come from today.** The paid describe call picks up to three topic ids
  (`corpus/describe.py:54-66`, `:27`). If it picks none, the chunk keeps its prior (`:84-87`), which is
  empty except for Fedlex's SR-number topic (`corpus/persist.py:84-88`). The prompt never offers "none"
  explicitly.
- **Why after describe.** Comparing with production needs describe's topics. Topics are not embedded (the
  local index embeds breadcrumb + description + text, `AGENTS.md:12`), so a topic correction never forces a
  re-embed. Jev runs at ingest only; the server keeps answering with no key (`AGENTS.md:8-10`).
- **Why not as a filter before describe.** Jev's "none" is not a junk detector: E4 answered none on 23 of 40
  chunks both labellers call real content, because they fit no category. Skipping describe for those would
  lose real content. Junk already has two guards: describe's `boilerplate` flag (`describe.py:60-61`) and
  `mark_repeated_furniture` (`describe.py:216`).
- **How the 0.91 could reach production.** Only by letting Jev's answer confirm or change `chunk.topics`.
  Which mode depends on the fresh re-test, which scores production's own topics (B) on the same labels:
  - Jev clearly better: use it to correct topics, e.g. drop a production topic Jev rates near zero, or add
    Jev's choice where production has none.
  - About equal: keep it as a cheap independent check that lists disagreements for review.
  - Worse: drop it.

## 6. How to confirm it

Use `../jev-live-tests/retest-kit/`:
1. **Freeze** `prereg_retest.json` (record its hash).
2. **Export** a sample with production topics (`export_sample.sql`) and **split** off the baseline (`prepare.py`).
3. **Label** it twice, blind, on the twenty topics (`LABELLING.md`).
4. **Run** both designs (`run_retest.py --criteria structured`, then `--criteria plain`) and **score**
   (`score_retest.py`).

Pre-registered decision (draft; confirm the numbers before labelling):
- **The primary design is structured.**
- **It replicates** if precision ≥ 0.70, recall ≥ 0.70, and the precision interval's lower bound ≥ 0.50.
- **It is worth building as a second opinion** if it also holds that, where Jev and production disagree and
  gold decides, gold sides with Jev at least one third of the time.

## 7. If it is confirmed

Implement as described in `../drafts/issue-jev-topics-second-opinion.md`.

## Reproduce the numbers above

From `../jev-live-tests/topic-evidence/`:

```
uv run python ../retest-kit/score_retest.py --chunks ../municipal/chunks.json \
  --labels-a ../municipal/labels_A.json --labels-b ../municipal/labels_B.json \
  --responses structured=responses_e4_structured.jsonl --responses plain=responses_e3_plain.jsonl --topic-ids old10.json
python3 ../municipal/score_muni.py        # M1
```

The first command prints E4 and E3; the second prints M1. Both were checked on 2026-09-24 to reproduce the
tables above.
