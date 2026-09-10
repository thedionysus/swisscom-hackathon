# Swiss Grounding MCP — Sources, Prior Art, myAI, Multilinguality, Legal Hierarchy

Scope note: "Confirmed" = seen in an official page or repo; "Uncertain" = reported second-hand or from prior knowledge; verify before relying on it in the demo.

---

## 1. Official machine-readable data sources

### 1.1 Federal law — Fedlex (Federal Chancellery)

- **Portal:** https://www.fedlex.admin.ch — publishes the Federal Gazette (BBl/FF), Official Compilation (AS/RO) and the Classified/Systematic Compilation (SR/RS = consolidated law in force).
- **Open data hub:** https://fedlex.data.admin.ch/ — RDF knowledge graph, downloadable; all resource URIs start with `https://fedlex.data.admin.ch/eli/...` (ELI = European Legislation Identifier). Confirmed.
- **SPARQL endpoint:** `https://fedlex.data.admin.ch/sparqlendpoint` (GUI at https://fedlex.data.admin.ch/sparql). Confirmed via the fedlex.data.admin.ch home page and the LINDAS Fedlex page (https://int.lindas.admin.ch/data-usage/fedlex/).
- **Ontology:** JOLux (adopted from Luxembourg's Casemates suite) plus ELI. FRBR-style abstraction: `jolux:Act` (work) → `jolux:Expression` (language version) → manifestation (file). Docs: https://swiss.github.io/fedlex-jolux/introduction.html. Official SPARQL tutorial (JupyterLite notebooks): https://github.com/swiss/fedlex-sparql.
- **Formats:** HTML, PDF, DOCX for texts; **Akoma Ntoso-compatible XML for all new publications since 30 May 2022** (confirmed on fedlex.data.admin.ch). Controlled vocabularies as SKOS/RDF/XLSX.
- **Licensing:** fedlex.data.admin.ch states texts and metadata are provided per the "technical and legal information for third-party users" (https://www.fedlex.admin.ch/de/broadcasters), which "authorises their re-use for commercial and other purposes". Confirmed permissive, exact wording uncertain.
- **Community mirrors:** https://github.com/droid-f/fedlex (Fedlex crawled into a git repo) — useful for offline demos.
- **Practical caveats (uncertain):** the SPARQL endpoint is slow for large queries; the consolidated-text XML must be fetched per expression via the manifestation URL found in SPARQL; article-level anchors exist in the HTML/XML (`art_X`), which is what you should cite.

### 1.2 LINDAS (federal Linked Data Service)

- **Portal:** https://lindas.admin.ch, datasets list at https://lindas.admin.ch/datasets/, FAQ queries at https://lindas.admin.ch/know-how/fa-queries/. Fair-use guidance and status page (status.lindas.admin.ch); no hard rate limits published. Confirmed.
- **Endpoint:** the site links `/sparql/`; the actual production endpoint is `https://lindas.admin.ch/query` (formerly `https://ld.admin.ch/query`) — verify.
- **Why it matters:** LINDAS hosts the federal **municipality/canton/district hierarchy as linked data** (historized, with BFS numbers), usable for jurisdiction resolution, plus statistical cubes. Fedlex is federated through LINDAS too. There is already a `lindas-mcp` (see §2).

### 1.3 opendata.swiss

- CKAN API base: `https://ckan.opendata.swiss/api/3/action/` (JSON). DCAT-AP CH metadata; per-resource terms of use from a controlled vocabulary (e.g. "Opendata BY", "Opendata BY ASK"); an `isopen` flag exists. Handbook: https://handbook.opendata.swiss/de/content/nutzen/api-nutzen.html; legal framework: https://opendata.swiss/de/legal-framework. Confirmed.
- Useful as a *catalog* tool (find dataset → distribution URL), not as an evidence source in itself.

### 1.4 Cantonal law

- **LexFind** (https://www.lexfind.ch): unified full-text search over federal + all 26 cantonal collections, updated daily, DE/FR/IT UI, version history and version comparison. No official public API documented. Uncertain whether LexFind tolerates scraping — check their terms.
- **Cantonal portals** (full table with URLs in https://github.com/rnckp/awesome-open-legal-switzerland). Platform families:
  - **CLEX / LexWork** family (Weblaw): AI (ai.clex.ch), AR, BL (bl.clex.ch), SH (sh.clex.ch), GL, NW, TG, plus BS (https://www.gesetzessammlung.bs.ch/app/) and LU (srl.lu.ch). Same HTML/JSON structure → one scraper covers ~10 cantons. Confirmed family, exact endpoint formats uncertain.
  - **SIL** (Francophone cantons: GE ge.ch/legislation, NE rsn.ne.ch, JU rsju.jura.ch, VD prestations.vd.ch/pub/blv-publication, VS lex.vs.ch, FR bdlf.fr.ch). OpenCaseLaw scrapes "SIL" portals directly.
  - **Custom:** ZH (ZH-Lex), BE (BELEX, https://belex.sites.be.ch), GR (gr-lex.gr.ch), SG, AG, SO, ZG, SZ, UR, OW, TI.
- **Zürich specifics:** ZH-Lex historical acts 1803–1998 are open data in TEI-XML (https://opendata.swiss/de/dataset/erlasse-der-zurcher-gesetzessammlung-seit-1803). The current ZH-Lex has an undocumented JSON backend that `openlex-mcp` uses (see §2).
- **OpenCaseLaw** (§2) reports: direct scrapers for 22 cantons, PDF extraction via LexFind for 4; 15,600 cantonal laws / 361k articles in its corpus. Fastest path to cantonal coverage for a hackathon.

### 1.5 Municipal law

- No national aggregator. Municipalities are obliged (by cantonal law) to keep a systematic collection; Kanton Zürich publishes a guide. Stadt Zürich publishes its Amtliche Sammlung as PDFs (https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung.html). Many municipalities use LexWork/clex-style hosted collections or the "i-web" CMS. Recommend a per-municipality "official website search" tool with domain allow-listing rather than a corpus.
- **City open data with real APIs:** Stadt Zürich (https://data.stadt-zuerich.ch, waste calendars as CSV per PLZ), plus the community **Open ERZ API** (JSON/iCal waste dates for Zürich, Basel, St. Gallen; https://www.stadt-zuerich.ch/de/politik-und-verwaltung/statistik-und-daten/open-government-data/anwendungen/anwendungen-2019/open_erz_api.html). Bern, Basel-Stadt (data.bs.ch, OpenDataSoft), Genève (SITG), St. Gallen (daten.stadt.sg.ch) all have OpenDataSoft/CKAN portals with REST APIs.

### 1.6 Court decisions

- **bger.ch** publishes Federal Supreme Court decisions as HTML (no API).
- **entscheidsuche.ch** (non-profit): ~1.05M decisions from all federal courts and all 26 cantons; **Elasticsearch endpoint `https://entscheidsuche.ch/_search.php`**, document store `https://entscheidsuche.ch/docs/`. Confirmed via https://github.com/self-tech-labs/entscheidsuche-MCP-server (archived May 2026; README says an official entscheidsuche MCP server now exists).
- **OpenCaseLaw** (https://opencaselaw.ch, https://github.com/jonashertner/opencaselaw): 1M+ decisions 1875–today from 118 courts, 5,525 federal + 15,600 cantonal laws, 9.65M citation edges; CC0 data / MIT code; Parquet on HuggingFace; REST API; remote MCP at **https://mcp.opencaselaw.ch** (38 tools). Fedlex refreshed monthly via SPARQL in DE/FR/IT; BGer decisions indexed ~15 min after publication. Confirmed.
- Research datasets: rcds/swiss_leading_decisions etc. on HuggingFace (CC-BY 4.0).

### 1.7 Jurisdiction resolution (address → municipality → canton)

- **swisstopo GeoAdmin API:** `GET https://api3.geo.admin.ch/rest/services/api/SearchServer?searchText=...&type=locations` returns addresses, communes, cantons, districts, ZIPs; `identify` on the `ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill` layer gives BFS number for a coordinate. Docs: https://api3.geo.admin.ch/services/sdiservices.html and https://docs.geo.admin.ch/access-data/search.html. Free, no key. Confirmed.
- **BFS official commune register (AGVCH):** https://www.agvchapp.bfs.admin.ch/de — snapshot (XLSX), historized directory (XML/TXT, eCH-0071), mutations since 2016, and documented **REST services** (PDF: https://www.bfs.admin.ch/bfs/de/home/grundlagen/agvch/historisiertes-gemeindeverzeichnis.assetdetail.15224054.html; API page https://www.bfs.admin.ch/bfs/de/home/dienstleistungen/forschung/api/api-gemeinde.html). Confirmed existence.
- **i14y** (https://www.i14y.admin.ch, handbook https://i14y-ch.github.io/handbook/en/): national data/API catalogue by BFS; Public API without auth for dataset/interface/concept metadata and code lists. Confirmed.
- **Swiss Post:** address verification/autocomplete REST API on https://developer.post.ch (account required). Confirmed; onboarding friction likely.

### 1.8 Other service APIs

- **Public transport:** https://opentransportdata.swiss — OJP 2.0 (`POST https://api.opentransportdata.swiss/ojp20`, XML), GTFS-RT, SIRI-SX; token required. The unofficial transport.opendata.ch REST API is simpler for a demo.
- **ch.ch:** the Confederation/cantons/communes citizen portal (DE/FR/IT/RM/EN). No API; pages are well structured for scraping/RAG. Its topic pages routinely say "ask your municipality/canton" — good signal for routing.
- **Amtsblattportal** (SHAB/official gazettes) has a REST API; **Zefix** commercial register has REST + LOD.

---

## 2. Prior art: Swiss AI/LLM on legal & public data

**Existing MCP servers (do not rebuild what exists):**
- https://github.com/malkreide/swiss-public-data-mcp — index of **42 MIT-licensed, read-only Python MCP servers**: `fedlex-mcp`, `openlex-mcp` (ZH-Lex), `swiss-courts-mcp` (entscheidsuche), `lindas-mcp`, `swisstopo-mcp`, `swiss-transport-mcp`, `zurich-opendata-mcp`, `amtsblatt-mcp`, `parlament-mcp`, `register-mcp`, etc. Confirmed.
- https://github.com/clement8426/swiss-apis-mcp — 29 tools over 9 APIs (transport, swisstopo, Zefix, opendata.swiss, MeteoSwiss, Fedlex, SNB, PLZ).
- https://github.com/vikramgorla/mcp-swiss — transport/weather/geodata/companies, zero keys.
- Ansvar-Systems/switzerland-law-mcp (Fedlex/SR provisions, citation validation, currency checks, EU cross-refs) and loicvuilliomenet-boop/fedlex-mcp — reported in search, not inspected.
- **OpenCaseLaw remote MCP** https://mcp.opencaselaw.ch — the most complete legal-grounding backend; federal + cantonal law + case law with citation graph.
- Hackathon precedent: FEDLEXplorer at Open Legal Lab 2023 (https://hack.opendata.ch/project/986).

**Gap analysis (differentiator):** none of these do *jurisdiction routing* (which level/which canton/which Gemeinde applies to this user's question and location) nor unify federal → cantonal → municipal → institutional sources with a consistent citation schema.

**Official/state AI:**
- **Fedlex KI-Suche** (pilot, https://fedlex.omnilex.ai/de/search, v2.0.0 dated 06.06.2026): semantic search over in-force federal law + binding international law in DE/FR/IT/EN; explicitly *does not generate text*; no cantonal/municipal law, case law or gazette. Built with Omnilex for ~CHF 40k (https://www.tagesanzeiger.ch/fedlex-bundesrecht-neu-per-ai-durchsuchen-324805635863). Confirmed.
- Federal administration: 2024 overview of five federal chatbot projects (https://www.netzwoche.ch/news/2024-10-18/diese-fuenf-chatbots-sollen-die-bundesverwaltung-entlasten) incl. SECO RAG evaluation and "KI-Chatbot ParlData". Federal Council AI coordination: https://www.admin.ch/de/newnsb/nTc28qni5hdpzQ0tH6RGa and https://www.bk.admin.ch/de/ki.
- **Cantons/cities:** ZüriCityGPT (Liip, June 2023; https://algorithmwatch.ch/en/atlas-db/zuricitygpt/); Kanton Luzern chatbot (Swiss Moonshot, CHF 677k; https://www.inside-it.ch/kanton-luzern-vergibt-auftrag-fuer-ki-chatbot-20241129); AargauGPT + Adnovum RAG voice bot; St. Gallen KI-Systemplattform for municipalities (https://kisg.ch/); Kanton Zürich AI page https://www.zh.ch/de/politik-staat/kanton/kantonale-verwaltung/digitale-verwaltung/kuenstliche-intelligenz.html. Abraxas markets an e-gov chatbot to municipalities.
- **Justitia 4.0 / justitia.swiss** (https://www.justitia40.ch/de): e-filing platform for courts — not a data source, but context.

**Research & models:**
- Joel Niklaus / Uni Bern RCDS: Swiss-Judgment-Prediction, LEXTREME (https://github.com/JoelNiklaus/LEXTREME), MultiLegalPile, SwiLTra-Bench (https://aclanthology.org/2025.acl-long.725.pdf), SwissLegalTranslations (https://github.com/JoelNiklaus/SwissLegalTranslations — aligned DE/FR/IT law text pairs from Fedlex), criticality prediction. SwissBERT.
- **Apertus** (Swiss AI Initiative, EPFL/ETH/CSCS, released 2 Sept 2025): 8B and 70B fully open models, 1,000+ languages incl. Swiss German and Romansh; Swisscom is a strategic partner and serves it on its Swiss AI Platform (https://www.swisscom.ch/en/about/news/2025/09/02-apertus.html). Confirmed.
- Commercial Swiss legal AI: Swisslex AI, Weblaw Lawsearch AI, Omnilex, Legartis, DeepLegal, Jurata AI, Alma Lex. Comparison: https://www.getcasus.com/blog/legal-ai-switzerland-comparison-2026.

---

## 3. Swisscom myAI

- Launched 24 Sept 2025 (https://www.swisscom.ch/en/about/news/2025/09/24-myai.html): consumer assistant at https://myai.swisscom.ch (web + iOS/Android), any Swisscom Login. **Model: Anthropic Claude Sonnet 4 via AWS Bedrock**, hosted on AWS "under Swisscom's control"; no training on user data. Free tier permanent; Pro CHF 14.90/month. Confirmed.
- Product page (https://www.swisscom.ch/en/residential/internet-subscription/myai.html): **integrated Swiss-focused web search with source citations**, document/image upload, dialect + national language support, Pro adds "advanced models", voice, "Superchats" (own documents + fixed instructions), and "integration with local services (timetables, weather, blue TV)". Confirmed.
- **MCP/tool use: no public statement.** Built-in timetable/weather tools imply an internal tool-calling layer, but nothing published says myAI accepts third-party MCP servers. Ship a remote MCP (Streamable HTTP) server with clean JSON-schema tools plus a thin REST facade so it works either way. Uncertain.
- Related: Swisscom "Swiss AI Assistant" for businesses (Feb 2026, Apertus on Swiss AI Platform; https://www.swisscom.ch/en/about/news/2026/02/18-swiss-ai-assistant.html). Pitching the server as also usable with Apertus (sovereign path) is a strong angle.

---

## 4. Multilinguality

- **Federal law:** DE/FR/IT versions are equally authentic (Publications Act, SR 170.512, Art. 14 — verify). **Romansh** versions exist only for selected acts, only in Rumantsch Grischun, not authentic (https://www.bk.admin.ch/en/romansh). English translations on Fedlex are unofficial. In JOLux, each language is a separate `jolux:Expression` of the same `jolux:Act`, sharing the ELI work URI — article-level alignment is by structure (same article numbering).
- **Cantonal law:** monolingual except bilingual cantons (BE de/fr, FR fr/de, VS fr/de) and trilingual GR (de/rm/it).
- **Case law:** court language = language of proceedings; OpenCaseLaw corpus is 46.7% DE, 45.1% FR, 8.2% IT.
- **Design implications:** (a) detect user language, but *retrieve in the source's language* — for federal law retrieve all three and cite the one matching the user; for cantonal law translate the query (cross-lingual embeddings such as multilingual-e5/bge-m3 handle DE↔FR↔IT well); (b) normalize identifiers, not titles: SR number + article (e.g. "SR 741.01 Art. 90") is language-independent; ELI URIs carry the language code; (c) Swiss German input should be normalized before keyword search.

---

## 5. Legal hierarchy & competence split (for routing)

Three levels: **Confederation → 26 cantons → ~2,100 communes** (2,121 as of 1 Jan 2026 per BFS snapshot; verify). Residual competence lies with the cantons (BV Art. 3); subsidiarity (BV Art. 5a); communes' autonomy is defined by cantonal law (BV Art. 50). Sources: https://www.aboutswitzerland.eda.admin.ch/en/federalism, Institute of Federalism Fribourg (https://www.unifr.ch/federalism/en/topics/chfederalism.html) and expert report on task allocation (https://www.unifr.ch/federalism/en/assets/public/files/NZ/Gutachten_final.pdf).

| Topic | Primary level | Notes / where to look |
|---|---|---|
| Foreign policy, army, customs, currency, civil & criminal law (ZGB/OR/StGB), social insurance (AHV/IV), asylum, nationality (framework), road traffic rules (SVG), telecom, energy policy | Federal | Fedlex SR |
| Income/wealth tax | Federal (DBG) **and** cantonal (StHG framework, cantonal Steuergesetz) **and** communal multiplier (Steuerfuss) | Fedlex + cantonal law + Gemeinde website |
| Schools (Volksschule), holidays, curricula | Cantonal (communes run schools) | cantonal Volksschulgesetz; municipal school calendar |
| Police, public order, hospitals, health | Cantonal | cantonal law |
| Spatial planning / building permits | Federal framework (RPG), cantonal PBG, **communal Bau- und Zonenordnung** | municipal BZO is decisive |
| Waste collection, water, sewage fees | Communal (within cantonal/federal environmental law) | municipal Abfallreglement + waste calendar |
| Dog tax, dog rules | Cantonal dog law + communal tax/leash rules (https://www.ch.ch/de/steuern-und-finanzen/steuerarten/hundesteuer/) | ask municipality |
| Parking (blue zone, permits) | Communal (federal SSV signage rules) | municipal Parkierungsverordnung |
| Shop opening hours | Cantonal (Ladenöffnungsgesetz), sometimes communal for Sundays; federal ArG for workers | cantonal law |
| Residents' register, civil defence, local roads | Communal | municipal website |
| Naturalisation | Federal BüG framework + cantonal + communal decision | all three |

Heuristic: if a question contains a place name, resolve place → BFS commune → canton via GeoAdmin/AGVCH first, then pick sources top-down: federal SR (always check), cantonal collection, municipal site; cite the most specific source that actually decides the matter.

---

## Key takeaways

1. **Federal law is solved infrastructure:** Fedlex SPARQL, ELI URIs, Akoma Ntoso XML since 2022, commercial reuse allowed. Cite by SR number + article + ELI URI + language.
2. **Cantonal law is scrapable, not API-served:** ~10 cantons share CLEX/LexWork, ~6 share SIL; LexFind is the human-facing union index. **OpenCaseLaw** (CC0, remote MCP) already has 22 cantons scraped — reuse it or its Parquet dump.
3. **Municipal law has no aggregator;** treat it as domain-allow-listed web retrieval per Gemeinde plus city OGD APIs.
4. **Jurisdiction routing is the unfilled niche.** GeoAdmin SearchServer + BFS AGVCH/eCH-0071 + LINDAS give address → commune → canton for free; none of the 40+ existing Swiss MCP servers do level-of-government reasoning.
5. **Case law:** entscheidsuche.ch Elasticsearch and OpenCaseLaw; both free.
6. **Prior art to acknowledge:** malkreide's 42-server index, swiss-apis-mcp, mcp-swiss, Fedlex KI-Suche (federal only, non-generative), ZüriCityGPT, Luzern/Aargau cantonal bots, Apertus.
7. **myAI runs Claude Sonnet 4 on AWS Bedrock** with built-in Swiss web search and local-service tools; no public MCP support.
8. **Multilingual:** DE/FR/IT federal texts equally authentic and structurally aligned by article; cantonal sources monolingual — retrieve in source language, normalize on identifiers, answer in the user's language while citing the authentic text.
9. **Licensing mostly fine:** Fedlex (reuse permitted), opendata.swiss (per-dataset), OpenCaseLaw (CC0), GeoAdmin/BFS (free); check LexFind and Swiss Post terms.
