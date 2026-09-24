# Re-test kit: the Jev topic question on a fresh labelled sample

This kit confirms, or refutes, the in-sample finding in `../../findings/2026-09-24-jev-topic-question-design.md`.
It asks Jev one "which topic, or none of these?" question per chunk, over the twenty production topics. It
scores the answers against two blind labellers, next to the topics production already stored.

**The step-by-step procedure is `../../HANDOFF-topic-retest.md`.** This README is the reference. For another
topic set, pass `--topics topics.json` (a list of `{id, label, covers}`) to `run_retest.py` and
`--topic-ids topics.json` to `score_retest.py`. Print the labelling table for it with `topics_table.py`.

Run everything from the repository root with `uv run` (the repo needs Python 3.12). Put the kit's files in a
working directory outside `docs/`, because the steps write chunks, labels and responses.

1. **Freeze the plan.** Confirm the thresholds in `prereg_retest.json`, then record its hash before anyone
   labels: `shasum -a 256 prereg_retest.json > prereg_retest.sha256; date >> prereg_retest.sha256`.
2. **Export a sample** from the corpus database, with production topics as the baseline:
   `psql "$DATABASE_URL" -At -f export_sample.sql > chunks_with_baseline.json`
   (not yet run against a database).
3. **Split it:** `uv run python prepare.py chunks_with_baseline.json` writes `chunks.json` for labellers and
   Jev, and `baseline.json`, which labellers must not see.
4. **Label** with `LABELLING.md`: two labellers, independently, into `labels_A.json` and `labels_B.json`.
5. **Ask Jev, once per design** (about $0.05 per 1,000 chunks per design at list price; one request per second):
   - `AI_GATEWAY_API_KEY=… uv run python run_retest.py chunks.json --criteria structured --out responses_structured.jsonl`
     (the primary design: Winnow-style `what` / `examples` / `not_for`, E4)
   - `AI_GATEWAY_API_KEY=… uv run python run_retest.py chunks.json --criteria plain --out responses_plain.jsonl`
     (the replication check of E3)
   - `--dry-run` prints the first request without calling anything, and re-running resumes.
   - The structured texts come from `corpus/topics.py` by a fixed rule; `criteria_structured.json` is that
     output. To use edited texts, pass `--criteria-file` and hash the file together with the plan, before
     labelling.
6. **Score:**
   `uv run python score_retest.py --chunks chunks.json --labels-a labels_A.json --labels-b labels_B.json --responses structured=responses_structured.jsonl --responses plain=responses_plain.jsonl --baseline baseline.json --prereg prereg_retest.json`
   It writes `summary.md`: every design against gold and against production (B), structured vs plain per
   chunk, and AUC next to precision and recall.

## Checked on 2026-09-24

- **Two designs, fed E4's and E3's saved answers and the old labels** (`--topic-ids` set to the old ten ids):
  the scorer reproduces both.
  - Structured: TP 10, FP 1, FN 1 (precision and recall 0.91).
  - Plain: TP 10, FP 3, FN 1.
  - AUC 0.999 and 0.998.
  - Per chunk, structured vs plain: 2 fewer errors, 0 more.
  - The prereg decision on the primary design: replicates = True, with a precision interval lower bound of 0.62.
- `run_retest.py --criteria structured` on the 20 production topics builds 21 options that follow the rule
  exactly (`criteria_structured.json`). Live, on the same two chunks as below:
  - the pet-travel page: `animals` 0.63;
  - the title-only junk chunk: **none_of_these 0.42** (`municipal_services` 0.35), where the plain design
    had picked `municipal_services`.
  - One chunk, and a close call.

- `score_retest.py`, fed E3's saved answers and the old labels with `--topic-ids` set to the old ten ids,
  reproduces E3 exactly: TP 10, FP 3, FN 1; precision 0.77 (0.50–0.92), recall 0.91 (0.62–0.98); 23 of
  35 junk chunks answered none; κ 1.00 and 0.78.
- **The thresholds are sized for the target sample.** On E3's own 13 topic picks, the precision interval's
  lower bound is 0.497, so `replicates` prints False. With 40 or more positive pairs, the same precision gives
  a lower bound near 0.6.
- `run_retest.py --dry-run` builds 21 options (20 topics plus none) whose text equals `corpus/topics.py`.
  The topic table in `LABELLING.md` also equals `corpus/topics.py`.
- A live run on two chunks returned HTTP 200 for both:
  - A pet-travel page: `animals` 0.64, `travel` 0.36.
  - A title-only junk chunk ("101 Gemeindeordnung"): `municipal_services` 0.51, none_of_these 0.18.
  - One junk chunk is not evidence. But the new broad administrative topic may take junk that the old ten left as
    none, so watch the "agreed junk" row.
