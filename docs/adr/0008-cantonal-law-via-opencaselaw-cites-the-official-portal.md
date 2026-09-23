---
status: accepted
date: 2026-09-23
---

# Cantonal law comes from the official portals where they have an API and from opencaselaw elsewhere, and is labelled cantonal law either way

Twelve cantons (BS, BE, BL, LU, ZG, GL, TG, AR, AI, NW, UR, SH) serve their law through the same official JSON API; the other fourteen, Zurich and Geneva among them, publish PDFs or JavaScript applications. opencaselaw.ch (LexFind data, keyless, CC0) serves article-structured text for all twenty-six cantons together with each act's official portal URL (verified 2026-09-23: Zurich LS 554.5 Hundegesetz, 30 articles, official zh.ch URL). We take the twelve from their official APIs and the fourteen from opencaselaw, and label both `cantonal_law`, citing the official portal URL as the source and recording `retrieved_via: opencaselaw` in provenance. This amends the rule of 2026-09-22 that text obtained through an aggregator is `institutional`: under that rule the whole of Zurich's cantonal law would rank below an information page, which is the authority-hierarchy failure the system exists to prevent.

## Considered Options

- Official portals only: ZH, GE, VD and TI would have no cantonal law at all.
- opencaselaw for all 26: one connector instead of two, but it gives up official text where it is freely available.

## Consequences

- opencaselaw text is extracted from PDFs: line-end hyphenation must be rejoined, and an article's first line sometimes arrives in the `heading` field; the connector repairs both.
- The aggregator's text may lag or differ from the official one. A later check compares a sample against the official portal PDFs, and a divergence found there reopens this decision.
