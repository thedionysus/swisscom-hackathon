# Research: Mapping Documents to Jurisdictions for Swiss Grounding

Date: 2026-09-10. Synthesis of four research tracks (full reports with URLs in `sources/`):

1. `sources/01-jurisdiction-aware-legal-rag.md` — how commercial legal AI, academic RAG work and RegTech handle jurisdiction
2. `sources/02-swiss-data-sources-and-prior-art.md` — Swiss data sources, existing Swiss MCP servers, myAI, multilinguality, competence split
3. `sources/03-jurisdiction-metadata-standards.md` — ELI, JOLux, Akoma Ntoso, schema.org, DCAT-AP CH, CPSV-AP, Swiss identifiers
4. `sources/04-gov-chatbots-and-mcp-prior-art.md` — government chatbot successes/failures, MCP design guidance, routing and evaluation research

---

## 1. The core finding: nobody classifies jurisdiction from text

Every production system that handles jurisdiction well does it the same way. Jurisdiction is assigned at **ingestion from provenance** (which portal, court or gazette the document came from) and encoded in identifiers and metadata. It is never predicted from the document text at scale.

- Open US Law encodes jurisdiction in the ID path (`us/co/statutes/...`).
- OpenCaseLaw (Swiss) has a `canton` field: `CH` for federal, `ZH`/`BE`/`GE` for cantonal.
- Fedlex ELI URIs are federal by construction; cantonal collections are separate portals.
- SAT-Graph RAG uses `urn:lex:br:federal:...`.
- RegTech (Compliance.ai, Corlytics) tags by regulator at ingestion with ML plus human review, never by inference alone.

On the **query side**, jurisdiction is made explicit rather than guessed. Westlaw uses checkboxes, Lexis allows up to 3 jurisdictions or all, Vincent stores a default jurisdiction, and Harvey makes jurisdiction a tool *parameter* the agent must fill. Lexis's 2026 rebuild shows the plan to the user so they can correct the jurisdiction before execution. Where inference happens, it happens as an auditable parameter, not as a side effect of relevance ranking.

The Stanford "Hallucination-Free?" study shows what happens otherwise. Its error taxonomy for legal RAG is jurisdiction confusion, authority-hierarchy violations, temporal misapplication and entity substitution. Hallucination rates were *higher* on jurisdiction- or time-specific questions.

## 2. Techniques with evidence

| Technique | Evidence | Relevance to us |
|---|---|---|
| Metadata-filtered hybrid search (jurisdiction, date, doc type filtered before vector search) | Standard in Harvey, OpenCaseLaw, Qdrant/Weaviate guidance; metadata-in-chunk cut wrong-document retrieval from 87% to 13% | Core pattern |
| Per-jurisdiction partitioned indexes with routing | STARA (state-by-state) scored 83% vs Westlaw 58% / Lexis 64%; India domain-partitioned RAG 70% vs 37.5% flat | Bund / Kanton / Gemeinde partitions |
| Rule-based routing over learned routing | "Learning to Route" paper: explicit rules beat learned routers in controlled domains and are interpretable | Swiss competence split is a rule table |
| Versioned corpus with as-of date as a hard filter | Static RAG found the date-applicable version 0% of the time; versioned index reached 98.3% | Fedlex is natively versioned via JOLux |
| Chunking on legal structure (article-level), with definitions and cross-refs attached | ClaimRAG-LAW: most wrong claims came from chunks spanning article boundaries; BM25 beat dense retrieval there | Fedlex XML has article anchors |
| Citation/status metadata as currency signal | KeyCite, Shepard's, `act_status` fields | `jolux:inForceStatus` is free |
| Knowledge graph of norm hierarchy | SAT-Graph, OpenCaseLaw citation graph; qualitative evidence only | Nice-to-have, not hackathon-critical |

**Gap in the literature:** no system found encodes lex superior / lex specialis conflict rules explicitly. The proven pattern is a `level` enum plus `based_on` links, and ranking by level and specificity.

## 3. What Switzerland already has

**Solved:** federal law. Fedlex publishes ELI URIs, a SPARQL endpoint, Akoma Ntoso XML since 2022, JOLux metadata with `dateApplicability`, `dateEndApplicability`, `inForceStatus`, and the SR taxonomy. Commercial reuse is permitted. DE/FR/IT texts are equally authentic and aligned by article number.

**Solved by others:** cantonal law and case law. OpenCaseLaw (CC0) has 22 cantons scraped, 15,600 cantonal laws, 1M+ decisions, a remote MCP at `mcp.opencaselaw.ch`, and Parquet dumps. entscheidsuche.ch exposes an Elasticsearch endpoint. Around 10 cantons share the CLEX/LexWork platform and 6 share SIL, so custom scrapers cover most of the rest.

**Solved for free:** location to jurisdiction. GeoAdmin SearchServer resolves addresses, PLZ and place names to commune and canton with no API key. The BFS commune register (AGVCH, eCH-0071) gives BFS numbers and historic mergers. LINDAS exposes the commune/canton hierarchy as linked data at `ld.admin.ch/municipality/N` and `ld.admin.ch/canton/N`. DCAT-AP CH already uses those URIs for `dct:spatial` on opendata.swiss.

**Not solved:** municipal law. There is no aggregator. Municipalities publish PDFs or hosted collections on their own sites. The realistic approach is domain-allow-listed retrieval per Gemeinde plus city open-data APIs (Open ERZ waste calendar, data.stadt-zuerich.ch, OpenDataSoft portals in Basel, Bern, Geneva, St. Gallen).

**Not solved by anyone:** jurisdiction routing. There are 40+ existing Swiss MCP servers (malkreide's 42-server index, swiss-apis-mcp, mcp-swiss, fedlex-mcp, opencaselaw). None of them reasons about *which level of government and which canton or commune applies to this question*. That is the open niche.

## 4. Government chatbot lessons

- **NYC MyCity** told businesses to break the law. It was grounded on service pages, not the law, and had no groundedness gate or refusal path. Shut down in 2026.
- **Kanton Luzern "Luzi"** (CHF 677k) was switched off after three days. The model worked; the underlying web content was stale and poorly structured. Freshness of the corpus was the bottleneck.
- **GOV.UK Chat** is the best-documented success: corpus restricted to gov.uk, hierarchical chunking, metadata-weighted reranking, intent routing, structured JSON output with mandatory citations, pre- and post-generation guardrails, and LLM-as-judge evaluation on groundedness. Accuracy went from 76% to 90%. Its warning: brand trust makes users dismiss inaccuracy risk.
- **ZüriCityGPT (Liip)** already does city-to-canton fallback routing for tax questions. That is the only Swiss example of jurisdiction routing found.
- **Publio (EU)** and **Singapore VICA** avoid free generation: templates or human-reviewed Q&A pairs. Lower risk, lower coverage.
- **Sovereignty** is a recurring political requirement (F13, ida, Vlam-chat, ZüriA). myAI runs Claude Sonnet 4 on AWS Bedrock; Swisscom also serves Apertus on its Swiss AI Platform.

## 5. Standards worth adopting

- **Metadata schema:** ELI / schema.org Legislation property names (`jurisdiction`, `spatialCoverage`, `legislationLegalForce`, `legislationDateOfApplicability`, `legislationType`, `legislationPassedBy`, `legislationConsolidates`). Fedlex data then drops in unchanged and cantonal/communal documents get equivalent fields.
- **Territorial key:** compound `country=CH`, `canton=BFS number or ISO 3166-2:CH`, `commune=BFS Gemeindenummer + eCH-0071 histId`, resolved to LINDAS URIs.
- **Applicability pattern:** legislation.gov.uk's provision-level `RestrictExtent` plus `RestrictStartDate/EndDate`. Store `applies_to: [territory URIs]` and `valid_from/valid_to` on every chunk.
- **Competence model:** CPSV-AP's (service, competent authority, territory, legal basis) triple, with SDG Annex I life events or eCH-0070 tasks as the topic axis. Germany's LeiKa/XZuFi split between a service catalogue and a competence-by-territory lookup is the model to copy.
- **Identifiers:** SR number + article is language-independent. Cantonal law needs minted ELI-like URIs (`/eli/ch-zh/cc/554.5/...`). Court decisions use court code + docket, since Switzerland does not use ECLI.

## 6. Implications for the hackathon design

1. **Route deterministically.** Resolve place to commune to canton via GeoAdmin, classify the topic against a competence table (federal / cantonal / communal / mixed), and search the matching partitions. Rules, not embeddings, decide jurisdiction.
2. **Make jurisdiction and as-of date explicit tool parameters.** Return them on every hit so the client can show and correct them. This is what Harvey, Lexis and the Stanford paper all point to.
3. **Reuse existing backends rather than rebuilding.** Fedlex SPARQL for federal, OpenCaseLaw for cantonal law and case law, GeoAdmin and LINDAS for jurisdiction resolution, opendata.swiss and city OGD for local services. Our value is the routing and unified citation layer.
4. **Return structured citations, never prose URLs.** ELI or systematic number, article, language, in-force date, source URL, snippet, and a `level` field.
5. **Treat freshness as a first-class field.** No long-lived caching of consolidated texts. Stamp `retrieved_at` and `valid_from/to`.
6. **Say "no authority found" rather than returning a neighbour's rule.** Publish coverage per jurisdiction so gaps are distinguishable from retrieval faults.
7. **Ship an eval set.** A gold set of Swiss questions that are jurisdiction- and date-specific, scored on citation precision/recall and the Stanford error categories.
8. **Keep the tool surface small.** Roughly 5 to 8 namespaced tools with concise/detailed output modes, following Anthropic's tool-design guidance.

## 7. Open questions to settle before building

- **Jurisdiction inference when the user gives no location.** Ask a clarifying question (GOV.UK style), default to federal, or use a myAI profile default? Each changes tool design.
-- Ask clarifying question, like which city, canton, or PLZ is the user interested in?
- **Topic-to-competence table.** How large does it need to be for a demo, and where does it come from? ch.ch pages are the best source but are not machine-readable.
-- This is to be decided, we still don't know exactly what will our datasources
- **Corpus versus live retrieval.** Index everything up front (fast, controllable, stale) or query Fedlex/OpenCaseLaw live (fresh, slower, dependent on third parties)? Likely a hybrid: index federal and cantonal law, live-fetch municipal pages.
-- Index everything up front
- **Municipal depth.** How many communes to support in the demo, and whether scraping their sites is acceptable.
-- We can scrape their sites.
- **myAI integration surface.** No public MCP support is documented. A remote Streamable HTTP MCP server plus a thin REST facade covers both possibilities.
-- I am even thinking if we can make a CLI tool out of it.
- **Language strategy.** Retrieve in source language and answer in user language is the consensus. Whether to embed cross-lingually or translate queries is an implementation choice.
-- We are concerned with English only at the moment. But we must support storing non English sources as well, so maybe we translate them before storing. 
