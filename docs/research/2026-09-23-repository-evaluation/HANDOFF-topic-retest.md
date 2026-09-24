# Handoff: re-test the Jev topic check on a fresh labelled sample

**Why this test.** On 75 municipal chunks, asking Jev *one* question ("which topic, or none?") with
structured topic descriptions scored precision 0.91 and recall 0.91. Ten yes/no questions scored
0.29 / 0.64. That was in-sample, so a fresh sample decides whether we propose it (details:
`findings/2026-09-24-jev-topic-question-design.md`). It works for any chunks and any topic set.

**Where it is.**
- Branch `docs/repository-evaluation` (committed locally, not pushed), checked out at
  `~/swisscom-hackathon-docs`.
- The scripts are in `jev-live-tests/retest-kit/`.
- To push the branch: `git -C ~/swisscom-hackathon-docs push -u origin docs/repository-evaluation`.

## 0. Once per shell (zsh)

```sh
REPO=~/swisscom-hackathon-docs; KIT=$REPO/docs/research/2026-09-23-repository-evaluation/jev-live-tests/retest-kit
py() { PYTHONPATH=$REPO/src uv run --no-project --python 3.12 --with httpx python "$@"; }
read -s "AI_GATEWAY_API_KEY?Vercel AI Gateway key: "; export AI_GATEWAY_API_KEY; echo
mkdir -p ~/jev-retest && cd ~/jev-retest          # work outside the repo
T=(); S=(); B=()   # new topic set: T=(--topics topics.json); S=(--topic-ids topics.json). baseline: B=(--baseline baseline.json)
```

## 1. Inputs, in `~/jev-retest`

- **`chunks.json`**: a list of `{"id", "language", "page_title", "heading", "text"}`.
  - From the corpus database: `psql "$DATABASE_URL" -At -f $KIT/export_sample.sql > chunks_with_baseline.json`,
    then `py $KIT/prepare.py chunks_with_baseline.json`. That writes `chunks.json` and `baseline.json`.
  - From anywhere else, write it in that shape. Aim for 150 or more chunks, including some with two topics.
- **`baseline.json`** (optional): the topics the existing system gave each chunk,
  `{"<id>": {"topics": [...], "boilerplate": false}}`. It lets the score compare Jev with production.
- **`topics.json`**: only for a new topic set; a list of `{"id", "label", "covers"}`. Without it, the
  twenty topics in `src/swiss_grounding/corpus/topics.py` are used.

## 2. Freeze the plan before anyone labels

```sh
cp $KIT/prereg_retest.json .      # check the thresholds; note your topic set in it
shasum -a 256 prereg_retest.json topics.json > plan.sha256; date >> plan.sha256   # drop topics.json if unused
```

Do not edit these files afterwards. Freezing them first is what makes the result trustworthy.

## 3. Label blind, twice

- **Build the guide.** Run `py $KIT/topics_table.py` (add `topics.json` for a new set) and paste its table into a copy of
  `$KIT/LABELLING.md`.
- **Two labellers work independently.** They can be two people, or two Claude sessions given only
  `chunks.json` and the guide. Each writes `labels_A.json` or `labels_B.json` in the guide's format.
- **What labellers must never see:** `baseline.json`, Jev's answers, or each other's labels.

## 4. Ask Jev: both designs, dry run first

```sh
py $KIT/run_retest.py chunks.json $T --criteria structured --dry-run   # no call
py $KIT/run_retest.py chunks.json $T --criteria structured --out responses_structured.jsonl
py $KIT/run_retest.py chunks.json $T --criteria plain      --out responses_plain.jsonl
```

- **Pacing:** one request per second, and it waits when Vercel asks (429). Re-running resumes.
- **Cost:** about $0.05 per 1,000 chunks per design.

## 5. Score

```sh
py $KIT/score_retest.py --chunks chunks.json --labels-a labels_A.json --labels-b labels_B.json \
  --responses structured=responses_structured.jsonl --responses plain=responses_plain.jsonl \
  $B $S --prereg prereg_retest.json
```

The last line of `summary.md` is the decision. The structured design **replicates** if precision ≥ 0.70,
recall ≥ 0.70, and the precision interval's lower bound ≥ 0.50. Also read:
- **"agreed junk":** does Jev answer "none" for junk?
- **">= 2 gold topics":** one choice gives one topic.
- **The comparison with B:** where Jev and the baseline disagree, whom does gold side with?

## 6. Afterwards

- **It replicates, and gold sides with Jev in at least a third of the disagreements:**
  1. Copy `summary.md` next to the findings.
  2. Push the branch and open a PR.
  3. File `drafts/issue-jev-topics-second-opinion.md`.
- **Otherwise:** add the result to the findings and stop.
- **Either way, keep:** `summary.md`, the three frozen files (`prereg_retest.json`, `plan.sha256`,
  `topics.json`) and both label files. Nobody can check the result without them.
