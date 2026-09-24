# Source discovery data

Material for choosing new sources to add to `manifests/declared-scope.yaml` (see
[`docs/MAINTAINING.md`](../MAINTAINING.md), "Adding a source").

## `commune_sites.csv`

Every Swiss commune in the location tree mapped to its official website, for finding the start URL
of a new municipal source.

| Column | Meaning |
|---|---|
| `extent_id` | Node id in the location tree (`CH-<canton>-<BFS number>`); the manifest's `extent_id` |
| `bfs` | BFS commune number (Wikidata `P771`) |
| `canton` | Parent node, for example `CH-ZH` |
| `label` | German name |
| `website` | Official website (Wikidata `P856`); empty for 7 communes |
| `population` | Wikidata `P1082`, for prioritising; may be empty |

Provenance: Wikidata SPARQL, items typed `Q70208` (municipality of Switzerland), fetched on
2026-09-22. 2,110 of them join the location tree, and 2,103 have a website.

Things to check before adding a site from this list:

- 5 communes live on their canton's domain (`bs.ch`, `zg.ch`, `kanton.baselland.ch`, ...). Their
  `allow_prefixes` must not overlap with the canton's source, or the manifest refuses to load.
- 17 entries are sub-paths (`zurzach.ch/gemeinde`), not bare domains.
- Many sites serve the same page under a language-neutral path (`/themes/x`) and a language path
  (`/fr/themes/x`). Allow only one of the two forms in `allow_prefixes`, or each page is stored twice.

## `ogd_lists_assessment.md`

An assessment, made on 2026-09-22, of two curated lists of Swiss open government and open legal
data as candidate sources. It was written against the earlier ingestion pipeline, so its notes on
fetch strategies and categories predate the manifest; the sources and their formats are still valid
research for expanding the corpus.
