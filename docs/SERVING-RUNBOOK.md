# Serving runbook — 2026-09-24

The commands below run **after** the encoding run (`docs/ENCODING-RUNBOOK.md`) has produced the
corpus tables. They set up the serving schema and lookup data, run the evaluation gates in order,
and publish the prebuilt dump that `setup` downloads. Run every command from the repo root.

## 1. Apply the serving schema

```bash
uv run swiss-grounding serving init
```

Idempotent: creates or updates the `serving` schema (call log, premium table, and anything else
`apply_serving_schema` defines). Safe to re-run after a pull.

## 2. Waste calendar and its embeddings

```bash
uv run swiss-grounding serving calendar    # imports the Zürich OpenERZ waste calendar as documents
uv run swiss-grounding corpus embed        # embeds the new documents into the configured indexes
```

`serving calendar` only ingests; it does not embed. Run `corpus embed` afterwards or the calendar
documents are not searchable.

## 3. Load premium data

BAG's premium archive keys rows by a BAG insurer number, not a name. The names come from BAG's
register of approved health insurers ("Verzeichnis der zugelassenen Krankenversicherer",
https://www.bag.admin.ch/de/verzeichnisse-der-zugelassenen-kranken-und-rueckversicherer, XLSX).
For 2026 (checked 2026-09-24: all 34 insurers in the premium table are named in the register of 1.1.2026):

```bash
curl -sL -o data/premium/insurers_2026.xlsx \
  "https://www.bag.admin.ch/dam/de/sd-web/wKeV97535ICf/Zugelassene%20Krankenversicherer_1.1.2026.xlsx"
uv run --with openpyxl python -c "
import openpyxl
ws = openpyxl.load_workbook('data/premium/insurers_2026.xlsx', read_only=True)['Index   Indice   Index ']
rows = [(int(r[1]), ' '.join(str(r[3]).split())) for r in ws.iter_rows(values_only=True)
        if isinstance(r[1], (int, float))]
open('data/premium/insurers_2026.csv', 'w', encoding='utf-8').writelines(f'{n};{name}\\n' for n, name in rows)"
uv run swiss-grounding lookups load-premiums data/premium/Prämien_CH.csv data/premium/regions_2026.csv 2026 \
  --insurers data/premium/insurers_2026.csv
```

`load-premiums` warns about any insurer number the register does not name; with the command above it
prints no warning. For a later year, take the newest register from the same page.

## 4. Golden set: dev split and labelling

```bash
uv run swiss-grounding eval golden --split dev
uv run swiss-grounding eval label --confirm-spend      # gpt-5-mini judges top citations; writes evals/golden/labels.jsonl
uv run swiss-grounding eval label-check                # agreement with the human-checked sample; must be >= 0.85 (ADR 0016)
```

`label-check` gates the next step: do not fit the relevance model on labels that fail agreement.

## 5. Fit the relevance model and re-run the golden set

```bash
uv run swiss-grounding eval fit                            # fits the relevance probability + abstention threshold (ADR 0012)
uv run swiss-grounding eval golden --split holdout --record  # the number that goes in the README
```

## 6. Generated-question recall and faithfulness

```bash
uv run swiss-grounding eval generate --confirm-spend    # gpt-5-mini writes one question per sampled chunk (ADR 0016)
uv run swiss-grounding eval recall                       # recall@5 against the generated questions
uv run swiss-grounding eval faithfulness                 # start `serve --transport http` first; see its --help
```

## 7. Publish the prebuilt dump

```bash
uv run swiss-grounding dump export
gh release create corpus-latest dist/* --repo thedionysus/swisscom-hackathon \
  --title "Prebuilt corpus" --notes "Restore with: uv run swiss-grounding setup"
# or, to replace an existing release:
gh release upload corpus-latest dist/* --clobber
```

`dump export` prints the exact `gh` command with the current `dist/` contents; use that output
rather than retyping it, in case the part count changed.

### Dump rehearsal (still to do)

Before the release is called final, rehearse the full round trip on a machine that has never seen
this database, and record the measurements in the README's evaluation section (Task 28 checks 10
and 12):

1. `dump export` on the machine that ran encoding; note the size of each `corpus.dump.part*` file
   (must be under 2 GiB — GitHub's per-file release limit).
2. Publish the release with `gh release create`/`gh release upload` as above.
3. On a separate machine (or `docker compose down -v` on the same one to get a genuinely empty
   volume), run `uv run swiss-grounding setup` from a clean checkout and time it end to end.
4. Record: total download size, restore time (`setup` prints this), and time to the first answered
   `swiss_search` after `serve` starts (Task 28 check 12, cold start with and without `setup`'s
   model pre-download).

## 8. Validate against the encoded corpus

Task 28 lists thirteen checks that must be run against the real corpus before the plan's numeric
claims (thresholds, quotas, latency budgets) are trusted: volume and coverage per declared
canton/city (checks 1–2), cross-language reranker bias and latency on real text (checks 3–4), the
provisional abstention threshold and local quota (checks 5–6), Fedlex anchor spelling and language
detection accuracy (checks 7–8), how often each model passes a location for the Konstanz-style
question (check 9), the dump rehearsal above (checks 10, 12), the CPU-only reranker path (check
11), and the ADR 0016 thresholds on holdout (check 13). Run them in the order given in
Task 28 of `docs/superpowers/plans/2026-09-23-serving-track.md`, record failures and the fix in `docs/RESEARCH.md` (section H3), and re-run before
submitting.
