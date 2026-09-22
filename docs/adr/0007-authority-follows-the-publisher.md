---
status: accepted
date: 2026-09-22
---

# Authority follows the publisher and the kind of text, never the topic

The registry has five authority levels and the reranker orders evidence by them (`federal_law` 1.0, `cantonal_law` 0.9, `municipal_law` 0.8, `official_info` 0.6, `institutional` 0.4). Nothing enforced which level a new source may claim, so a gazette notice about a dog ordinance, a court ruling from an aggregator, or a crawled information page could have been registered as law and outranked the ordinance itself. With official gazettes, court decisions, parliamentary material and textbooks now identified as sources, we decided the rule and made the registry enforce it. The three law authorities are reserved for the legal text itself, read from an official law platform that the registry knows by host (`LAW_PLATFORM_HOSTS` in `registry/official_domains.py`: Fedlex, the 26 cantonal collections including the vendor-hosted ones, and a commune's own compilation), landing at that platform's jurisdiction and at the matching level of the location tree: federal law at the country, cantonal law at a canton, municipal law at a commune. The fetch strategy is free: SPARQL, an API, PDFs or a crawl can all carry legal text, what matters is whose platform it comes from. `official_info` is for official entities and the online systems they run: governments, municipalities, administration offices, gazettes (every rubric, including enactment notices), portals, calendars, data services, and courts publishing their own decisions. A source on a non-government host may carry `official_info` only with a stated `authority_reason` naming the official publisher it re-serves. `institutional` is for everyone else, including aggregators that republish official text. We rejected assigning authority by topic or rubric, because a notice about law is information about law and not the law; and we rejected leaving the choice to each YAML, because the failure class this protects against (authority-hierarchy violation) is silent at query time.

## Consequences

- `Source` validation rejects a law authority whose `base_url` host is not in `LAW_PLATFORM_HOSTS`, whose default extent is at the wrong level, or whose default extent is not the platform's jurisdiction. A new official platform (e.g. a commune's collection) is added to that table with its jurisdiction; an aggregator (opencaselaw, LexFind) is never added, it may only be used to fetch text that is cited to the official platform (#37).
- `official_info` on a non-official domain requires `authority_reason`; the seed source `open_erz` carries one (it re-serves the City of Zurich's open-data calendar). A reviewer approving a suggested source passes the review note as the reason.
- Court decisions are `official_info` from a court's own portal and `institutional` from an aggregator; the citation should point at the court.
- The English editions of federal acts are federal law like the German ones; the non-binding status of the translation is a property of the text, not of the authority.
- `geneve.ch` is registered as the City of Geneva's domain so the Ville de Genève source classifies as official.
