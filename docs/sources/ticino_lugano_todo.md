# Future job: every source for Lugano and the Canton of Ticino

**Status:** not started. Planned for the week after 2026-10-06. Anyone on the team may pick it up.

## Why

We will meet the mayor of Lugano. The server should then answer as much as possible about the City of
Lugano and the Canton of Ticino, with cited official pages.

## Goal

Find every official source for Lugano (city) and Ticino (canton) that the crawler can read and that
robots.txt allows, and add it to `manifests/declared-scope.yaml` (see
[`docs/MAINTAINING.md`](../MAINTAINING.md), "Adding a source").

## Steps

1. **What we have:** list the Ticino and Lugano sources already in `manifests/declared-scope.yaml`, and
   the documents per source in the current release `corpus-full-sources-described-2026-09-25`.
2. **What is missing:** search for official pages in the areas below. Use the start URL in
   [`commune_sites.csv`](commune_sites.csv) for the city.
3. **Test each candidate URL:** robots.txt allows it, and the page is readable HTML or PDF.
4. **Add, crawl, describe, embed**, then publish a new release and point `DUMP_RELEASE_TAG` at it.
5. **Test questions:** add Italian golden questions about Lugano and Ticino (see
   [`docs/EVALUATION.md`](../EVALUATION.md)).

## Areas to check

- **City of Lugano:** residents' office, moving in and out, waste collection, parking and permits,
  building permits, schools and childcare, local taxes and fees, social services, culture and events.
- **Canton of Ticino:** cantonal law (see issue #37), taxes, vehicles and driving licences, residence
  permits, health and social insurance, schools, building and land use, official gazette.

## Search sentences to start with

- Città di Lugano sportello cittadino
- Lugano calendario raccolta rifiuti
- Lugano permesso di parcheggio residenti
- Lugano domanda di costruzione
- Cantone Ticino raccolta delle leggi
- Ticino imposte persone fisiche istruzioni
- Ticino sezione della circolazione licenza di condurre
- Ticino permesso di dimora
