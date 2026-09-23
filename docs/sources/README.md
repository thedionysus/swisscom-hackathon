# Source discovery data

> **Note (2026-09-24): written for the legacy registry** (`registry/sources/*.yaml`, `fetch_strategy:
> html_crawl | api | fedlex_sparql | pdf`). The legacy pipeline is being retired (#52). **The links, endpoints
> and findings below are still valid.** To add a source now, write an entry in `manifests/declared-scope.yaml`
> (`connector: html | fedlex`, `start_urls`, `allow_prefixes`, `level`, `extent_id`, `tier`, `languages`; ADR
> 0009) or a new connector in `corpus/connectors/`. The open source work is tracked in #37, #39, #45, #46 and
> #47.


## `commune_sites.csv`

Every Swiss commune in the location tree mapped to its official website, for registering
municipal `html_crawl` sources and for extending `official_domains.CITY_DOMAINS`.

| column | meaning |
|---|---|
| `extent_id` | node id in the location tree (`CH-<canton>-<BFS>`), joins `location.id` |
| `bfs` | BFS commune number (Wikidata `P771`), joins `location.bfs_id` |
| `canton` | parent node, e.g. `CH-ZH` |
| `label` | German label |
| `website` | official website (Wikidata `P856`); empty for 7 communes |
| `population` | Wikidata `P1082`, for prioritising; may be empty |

Provenance: Wikidata SPARQL, items typed `Q70208` (municipality of Switzerland), fetched
2026-09-22; 2,173 items, 2,110 join the tree (every commune in the register), 2,103 with a site.

Known quirks to handle before registering a site from this list:

- 5 communes live on their canton's domain (`bs.ch`, `zg.ch`, `kanton.baselland.ch`, ...);
  `classify_domain` files those as the canton.
- 13 sites are not on `.ch`/`.swiss` and fail the TLD check in `classify_domain`.
- 17 entries are sub-paths (`zurzach.ch/gemeinde`), not bare domains.
- Sites often link language-neutral paths (`/themes/x`) beside `/fr/themes/x`; allow only one
  form or the same page is stored twice (#27). See `registry/sources/ge_ville.yaml`.
