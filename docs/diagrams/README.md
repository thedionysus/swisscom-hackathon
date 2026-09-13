# Diagrams

Six editorial diagrams describing Swiss Grounding MCP. Open [`index.html`](index.html) for the set,
or any file directly — each is self-contained HTML with inline SVG, no build step and no JavaScript.

| # | File | Type | Drawn from |
|---|---|---|---|
| 01 | [architecture.html](architecture.html) | Architecture | whole tree |
| 02 | [ingest-data-flow.html](ingest-data-flow.html) | Data flow | `ingest/pipeline.py`, `ingest/fetchers/` |
| 03 | [query-sequence.html](query-sequence.html) | Sequence | `retrieval/query_core.py`, `retrieval/search.py` |
| 04 | [document-lifecycle.html](document-lifecycle.html) | State machine | `ingest/persist.py` |
| 05 | [jurisdiction-tree.html](jurisdiction-tree.html) | Tree | `locations/tree.py`, `locations/seed.py` |
| 06 | [source-approval.html](source-approval.html) | Flowchart | `registry/suggestions.py`, `registry/official_domains.py` |

## How these were made

Generated with the [diagram-design](https://github.com/cathrynlavery/diagram-design) skill (v2.6.22,
commit `8d8b299`), installed as a Claude Code plugin. Content was read out of the source — no facts
were inferred from module names.

**Drawn against `55f48df`** (`feat: fetch-health signal in swiss_coverage`). If you are reading these
against a later tip, re-check the claims below before trusting them.

### Deliberately not drawn

- **`pending_enrichment`** is permitted by the `document.status` check constraint but no code path
  writes it, so the state machine omits it. If a transition to it ever lands, diagram 04 needs a
  fourth state.
- **`ingest_run`** appears in diagram 01 as part of the store, but the run-log write itself is not
  drawn — it happens in `cli/main.py` after the pipeline returns, not inside it, so putting it in the
  data flow would have misplaced it. `swiss_coverage` derives fetch health from that table.
- The **`origin`** column (`crawl` / `fixture`) is not drawn; it distinguishes demo fixtures from
  crawled documents and does not affect the flows shown.

Skin: the shipped default (white-smoke paper, jet-black ink, atomic-tangerine accent). To rebrand the
set for a presentation, run `/profile` and onboard from a website URL, then regenerate.

## Verification

Every file passes both of the skill's checkers, plus a visual render pass:

```bash
SKILL=~/.claude/plugins/cache/diagram-design/diagram-design/2.6.22/skills/diagram-design
(cd "$SKILL" && for f in <repo>/docs/diagrams/*.html; do python3 scripts/self_check.py "$f"; done)
```

`self_check.py` enforces the accessible-SVG contract (`role="img"`, prefixed `<title>`/`<desc>`) and
the single-file safety rules — no remote references except the Google Fonts stylesheet.

`verify-geometry.py`, from a repository checkout of diagram-design, confirms no arrow label collides
with a node drawn after it.

The linters cannot see text overflow, so each diagram was also rendered headless and inspected; two
sublabels were shortened as a result.

## Caveats

- **Static artifacts.** They do not track the code. When the pipeline or schema changes, regenerate.
- **Google Fonts.** Each file links `fonts.googleapis.com`. Opening one makes that request. Ask for a
  system-font stack if these need to travel without it.
- **Export.** `/export-diagram <file>` writes `.svg` and `.png` next to the source. It needs Playwright;
  headless Chrome works as a fallback.
