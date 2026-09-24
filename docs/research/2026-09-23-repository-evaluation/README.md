# Jev topic check, and ideas worth borrowing (2026-09-23 / 24)

**Useful now: a cheap check on chunk topics.**
- **The result.** Ask Jev one "which topic, or none?" question with structured topic descriptions. On 75
  municipal chunks: precision 0.91, recall 0.91, against 0.29 / 0.64 for ten yes/no questions. This is
  in-sample, and a fresh sample must confirm it.
- **Read these files:**
  - `findings/2026-09-24-jev-topic-question-design.md`: the finding, where it would sit in the pipeline,
    and its limits.
  - `HANDOFF-topic-retest.md`: one page to run the confirmation on any chunks and any topic set.
  - `drafts/issue-jev-topics-second-opinion.md`: the implementation proposal if it is confirmed (not filed).

**Worth borrowing later:** `borrow-later.md`. It covers a claim-by-claim faithfulness check for ADR 0016's
judge, in-force dates picked among candidates, and the operational lessons for calling Jev.

| Path | What it is |
|---|---|
| `findings/2026-09-24-jev-topic-question-design.md` | Three question designs compared: results with intervals, errors, limits, where it fits in `main` @ `159ac23`, how to reproduce |
| `HANDOFF-topic-retest.md` | The fresh-sample test, step by step; every command tested in zsh |
| `drafts/issue-jev-topics-second-opinion.md` | Draft enhancement issue: a paced Jev second opinion after describe, gated on the re-test |
| `borrow-later.md` | Faithfulness-check template, date candidate-pick, operational lessons |
| `jev-live-tests/retest-kit/` | Plan (draft), labelling guide, export query, runner (structured and plain designs), scorer, topic-table helper |
| `jev-live-tests/topic-evidence/` | E3 and E4 answers in compact form, plus `old10.json`. They reproduce the numbers through the kit's scorer (`summary.md` is its output) |
| `jev-live-tests/municipal/` | The 75 chunks, two blind labellers' labels (hashes sealed in `results/seal.json` before any call), M1's answers and scorer, and the Basel-Stadt date test |
| `jev-live-tests/typesafe-mcp/` | The plans fixed before E3 and E4 (with sha256), and `results/summary.md` (E1–E3: wrapper fidelity, batching loss) |
| `jev-live-tests/federal/` | The federal test's report and printed scorer output: the T2 claim check and T3 dates behind `borrow-later.md` |

**Kept out of git** (untracked in the local worktree):
- the evaluation record and the reports on jev-mcp, jev-ultrafast and typesafe-mcp;
- the triage of seven more Jev repositories and Firecrawl Alexandria (none is useful for the platform);
- the federal scripts, whose input data was lost;
- raw HTTP logs, full response dumps, and the harness for the `evaluate` binary.

**Provenance:**
- The files were rebuilt from session transcripts after a restart wiped the scratchpad.
- Re-crawling and re-running the seeded sampler reproduced, byte for byte, the municipal sample both
  labellers had read.
- The label hashes equal the ones sealed before the first call.
- No API key is stored here.
