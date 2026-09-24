# Run 3 sources and the corpus pipeline

This folder compares the Run 3 sources (`../`, 148 candidates) with the corpus pipeline on `main` at `159ac23` and converts them into the pipeline's manifest format.
- The work was done offline on 2026-09-24: no source website contacted, no database touched, no `corpus` command run.
- **Nothing here changes `main`, `manifests/declared-scope.yaml` or `src/`.** The entries are candidates for review.

## Result

| Status (`compatibility.csv`) | Rows |
|---|---:|
| Convertible now | 79 |
| Already inside a declared source (do not add again) | 20 |
| Convertible after a small pipeline change | 13 |
| Needs a new connector | 25 |
| Not a document source (commune directories) | 10 |
| Blocked, decision pending (fo.fr.ch) | 1 |

- **`manifest_candidates.yaml`: 75 entries.**
  - Section 1 holds 74 that work with today's `html` connector.
  - Section 2 holds 1 that is valid but blocked by TLS.
  - Tiers: 9 are tier 1 (inside ADR 0009's scope), 63 tier 2, 3 tier 3.
- **Validated with the pipeline's own code:**
  - `load_manifest` passes on the 75 entries;
  - merged with `declared-scope.yaml`, all 102 sources validate, with no prefix clashes and no duplicate ids;
  - every `extent_id` exists in the location seed.
- **Before merging, check the entries flagged `UNVERIFIED` in the YAML:**
  - the Neuchâtel `/fr/` start-URL workaround;
  - the Vernier list;
  - the LU `content_selector: "#mainContent"`, which was found in saved pages rather than in an agent report;
  - three single-PDF pins without a verified parent page.

## Files

| File | What it is |
|---|---|
| `manifest_candidates.yaml` | The 75 manifest entries. Comments on each entry name the Run 3 rows and the evidence. |
| `connector_specs.md` | **Instructions for each pipeline change**: what it unlocks, where it plugs in (verified `file:line`), the proposed config, the behaviour, the tests. |
| `compatibility.csv` | One row per Run 3 catalogue row: new connector, status, required pipeline change, manifest id |
| `compatibility_report.md` | Full report on converting the Run 3 sources (agent B) |
| `capabilities_report.md` | Full report on what the corpus pipeline does and what changed from the legacy pipeline (agent A) |
| `conversion_report.json` | Overlap and per-entry checks behind the CSV |
| `evidence/` | Offline parse results (`dry_parse_all.json`), PDF discovery on saved pages, the parent page of each PDF |
| `scripts/` | The offline scripts that produced all of the above |

## Re-validate

```bash
PYTHONPATH=src python -c "
from swiss_grounding.corpus.manifest import load_manifest, Manifest; import yaml
c = load_manifest('docs/sources/verification_2026-09-23/run3/corpus_pipeline/manifest_candidates.yaml')
d = yaml.safe_load(open('manifests/declared-scope.yaml'))
m = Manifest.model_validate({'version': 1, 'sources': d['sources'] + [s.model_dump() for s in c.sources]})
print(len(c.sources), 'candidates;', len(m.sources), 'merged')"
```

Run it from a checkout of `main` with this folder copied in.

## Where each item is tracked

| Item | Where |
|---|---|
| Adding the candidates to the manifest, tier decision | #45 |
| Gazette connector (Amtsblattportal) | #39. Our 13 gazette rows and the query facts verified on 2026-09-23 go there. |
| robots.txt for PDFs, Crawl-delay for PDFs, robots groups naming our token | PR #51 (open) |
| Law-platform registration for the three city law collections marked `municipal_law` | #44 |
| JSON / REST connector, PDF discovery gaps, smaller fetch fixes | new issues, spec in `connector_specs.md` |

**Decided by the user on 2026-09-23:**
- Gazettes go through the documented Amtsblattportal API.
- Basel-Landschaft goes through `bl-api.webcloud7.ch`.
- fo.fr.ch must not be left out; ask the publisher. It is not in the candidates.
