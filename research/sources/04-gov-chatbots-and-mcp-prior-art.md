# Grounding & Jurisdiction in Public-Sector AI Chatbots, and MCP Prior Art

## TOPIC A — Government chatbots: what worked, what failed

### 1. NYC MyCity chatbot (failure case, 2023–2026)
- Launched Oct 2023 on Microsoft Azure AI, grounded on "trusted information from more than 2,000 NYC Business web pages." ([The Markup, Mar 2024](https://themarkup.org/artificial-intelligence/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law))
- Told employers they could take workers' tips (illegal), that landlords could refuse housing-voucher tenants (illegal), that businesses could go cash-free (illegal). Only a small disclaimer. ([follow-up](https://themarkup.org/artificial-intelligence/2024/04/02/malfunctioning-nyc-ai-chatbot-still-active-despite-widespread-evidence-its-encouraging-illegal-behavior))
- Killed in Jan 2026 as "functionally unusable." ~$600k build, ~$500k/yr. No formal post-mortem. ([StateScoop](https://statescoop.com/mamdani-kill-nyc-ai-chatbot/))
- **Lesson:** grounding on *service pages* is not grounding on *the law*. Service pages don't state prohibitions, so the model "filled in" with parametric priors. No groundedness gate, no refusal path, no citation requirement, no expert eval before launch.

### 2. GOV.UK Chat (best-documented)
GDS engineering write-up, May 2026 ([Developing GOV.UK Chat](https://insidegovuk.blog.gov.uk/2026/05/15/developing-gov-uk-chat-our-data-science-and-ai-engineering-journey/)):
- **Corpus restriction:** solely published GOV.UK content (~700k pages); metadata filters prioritise authoritative, up-to-date sources. ([private beta](https://insidegovuk.blog.gov.uk/2024/11/05/were-running-a-private-beta-of-gov-uk-chat/))
- **Chunking:** hierarchical semantic chunking preserving HTML header structure ([2024 findings](https://insidegovuk.blog.gov.uk/2024/01/18/the-findings-of-our-first-generative-ai-experiment-gov-uk-chat/)).
- **Retrieval:** Titan embeddings + metadata-weighted re-ranking designed with content designers, after testing hybrid search and cross-encoders.
- **Routing:** LLM tool-calling classifies intent and picks a response strategy.
- **Generation:** structured JSON I/O, partial answers allowed, must cite GOV.UK content and "avoid hallucinated hyperlinks."
- **Guardrails:** pre- and post-generation LLM guardrails, red-teamed with AISI. 508 jailbreak attempts blocked.
- **Evaluation:** automated LLM-as-judge (groundedness, relevance, factual accuracy, completeness, reliability, reputational safety), manual expert log review, live monitoring. Accuracy 76% → 90%; in-scope answer rate 88% via clarifying questions. ([5 things](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government/))
- **Warning:** users "underestimated or dismissed the inaccuracy risks… because of the credibility… associated with the GOV.UK brand."

### 3. Switzerland
- **ZüriCityGPT / SwissGovernmentChatbots (Liip):** RAG over crawled city sites: HTML→Markdown, header-based chunking, embeddings + NER + full-text + Cohere re-rank, source links with modification dates. **Jurisdiction handling:** explicit *query routing* — tax questions redirected to Canton data when the city lacks answers. LLM self-rates plausibility 1–6. ([Liip: 10 months later](https://www.liip.ch/en/blog/zuricitygpt-10-months-later)) The [SwissGovernmentChatbots repo](https://github.com/liip/SwissGovernmentChatbots) lists official deployments (fragesi.ch, moudon.ch, bs.ch/alva) and ~11 unofficial ones.
- **Kanton Luzern "Luzi" (failure, 2025–26):** Swiss Moonshot contract CHF 677k; launched 24 Sep 2025 with source links over all public web content; **switched off after three days**. Official reason: bot "functioned technically flawlessly" but the data was "too poorly structured, not consistently current, and insufficiently maintained." ([Luzerner Zeitung](https://www.luzernerzeitung.ch/zentralschweiz/stadt-region-luzern/kanton-luzern-stellt-ki-chatbot-luzi-nach-drei-tagen-ab-ld.4204011), [inside-it](https://www.inside-it.ch/das-kurze-leben-des-luzerner-chatbots-luzi-20260727)) **Lesson: freshness and content hygiene of the source corpus, not the model, is the bottleneck.**
- **Stadt Zürich:** "ZüriA" internal assistant (Mar 2026), "Zü-Re" circular-economy bot; Kanton Zürich "SynerKI" platform. No public citizen-facing general RAG bot yet. Zug planning a cantonal bot.

### 4. Singapore
- **Ask Jamie** suspended by MOH in Oct 2021 after giving safe-sex advice to COVID questions — intent-classifier domain mismatch. ([Marketing-Interactive](https://www.marketing-interactive.com/moh-suspends-ask-jamie-chatbot-for-misaligned-responses-to-covid-19-queries))
- **VICA refresh:** 88 bots migrated to LLM engines, grounded on **human-reviewed Q&A pairs** (not raw pages); answer-scoring; clustering of unanswerable questions. ([GovInsider](https://govinsider.asia/intl-en/article/is-it-time-to-say-goodbye-to-ask-jamie-inside-govtechs-refresh-of-government-chatbots))

### 5. Germany / Austria / EU / Estonia / Netherlands / Canada / Australia
- **F13 (Baden-Württemberg):** sovereign, model-agnostic assistant, open-sourced July 2025. Internal-facing. ([STM BW](https://stm.baden-wuerttemberg.de/de/service/presse/pressemitteilung/pid/ki-assistenz-f13-wird-zur-open-source-software))
- **Austria "ida" (oesterreich.gv.at):** Mistral models hosted in Austria; sources restricted to oesterreich.gv.at and id-austria.gv.at; explicit "preliminary information" disclaimer. ([ida](https://www.oesterreich.gv.at/de/landingpages/chatbot-ida))
- **EU Publications Office "Publio":** **does not generate answers with an LLM** — LLM only for entity extraction; all messages are templates; search constrained using EuroVoc and authority tables. ([Explainability notice](https://op.europa.eu/en/web/about-us/explainability-notice))
- **Estonia Bürokratt:** open-source network of agency bots with shared front end — jurisdiction = agency ownership. ([OSOR](https://interoperable-europe.ec.europa.eu/collection/open-source-observatory-osor/document/digital-public-services-based-open-source-case-study-burokratt))
- **Netherlands:** municipal "Guus" (Goes) uses only pre-approved goes.nl URLs.
- **Canada:** CRA GenAI chatbot restricted to Canada.ca pages, "not legal advice" disclaimer, PII detection. ([CRA](https://www.canada.ca/en/revenue-agency/corporate/contact-information/cra-chatbot/genai-chatbot-beta.html))
- **Australia:** NSW AI Assessment Framework rates public-facing chatbots **high risk**.

### 6. Legal-RAG evidence on jurisdiction/temporal errors
- Stanford "Hallucination-Free?": Lexis+ AI 17%, Westlaw AI-AR 33%, GPT-4 43% hallucination; error taxonomy = **jurisdiction confusion, authority-hierarchy violations, temporal misapplication, entity substitution**. ([PDF](https://law.stanford.edu/wp-content/uploads/2024/05/Legal_RAG_Hallucinations.pdf))
- "Temporal Misgrounding in Legal RAG": static RAG retrieved the date-applicable version **0%** of the time; a versioned multi-index retriever reached 98.3%. ([arXiv 2608.09393](https://arxiv.org/html/2608.09393v1))

## TOPIC B — MCP prior art and design guidance

### 1. Existing legal/government MCP servers
- **Fedlex:** [malkreide/fedlex-mcp](https://github.com/malkreide/fedlex-mcp) — 12 tools (`fedlex_search_laws`, `fedlex_get_law_by_sr`, `fedlex_get_law_history`, `fedlex_get_upcoming_changes`, gazette/BBl/treaty search, consultations, TERMDAT lookup) over the Fedlex SPARQL endpoint and LINDAS; DE/FR/IT/RM; ELI URIs; **no caching** ("to avoid stale law references"), hard boundary "federal only, cantonal excluded," all tools `readOnlyHint`/`idempotentHint`. Also [JayTheSkier/fedlex-connector](https://github.com/JayTheSkier/fedlex-connector).
- **EUR-Lex:** [cyanheads/eur-lex-mcp-server](https://github.com/cyanheads/eur-lex-mcp-server) — 7 tools incl. CELEX/ELI resolver, relation traversal, EuroVoc browser, 24 languages with declared fallback ("requested vs effective language").
- **US:** [federal-register-mcp](https://github.com/aml25/federal-register-mcp), [mcp-congress_gov_server](https://github.com/bsmi021/mcp-congress_gov_server), [us-gov-open-data-mcp](https://github.com/lzinga/us-gov-open-data-mcp) (250+ tools — an anti-pattern).
- **Generic:** [mcp-server-sparql](https://github.com/ekzhu/mcp-server-sparql), [wikidata-mcp](https://github.com/ryge/wikidata-mcp).
- **Search/grounding MCPs:** Perplexity Sonar (prose with inline citations); Exa/Tavily/Brave (raw results with URLs). [Context7](https://context7.com/docs/overview) is the best pattern analog: two tools (`resolve-library-id` → `query-docs`), version-matched docs, tiered background refresh.

### 2. MCP tool-design best practices
- Anthropic "[Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)": few high-impact tools; namespace prefixes; descriptions as onboarding docs; `response_format: concise|detailed`; pagination/truncation with actionable guidance; consolidate multi-step ops; evaluation-driven iteration.
- Anthropic "[Advanced tool use](https://anthropic.com/engineering/advanced-tool-use)": Tool Search (defer_loading) cuts context 85%; keep 3–5 core tools loaded; tool-use examples raise parameter accuracy 72→90%.
- **Resources vs tools:** resources are application-controlled, read-only, good for deterministic fetch-by-URI (e.g. `fedlex://sr/235.1/de@2025-01-01`); tools are model-controlled for search. ([MCP spec 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25))

### 3. Source/query routing research
- [Adaptive-RAG](https://arxiv.org/pdf/2403.14403), Self-RAG, CRAG, [RAGRouter](https://arxiv.org/abs/2505.23052), [RAGRouter-Bench](https://arxiv.org/html/2604.03455).
- "[Learning to Route: rule-driven hybrid-source RAG](https://arxiv.org/pdf/2510.02388)": explicit rules beat learned routing in controlled domains — a strong argument for **deterministic jurisdiction routing** (Bund → Kanton → Gemeinde).
- Metadata pre-filtering before vector search is the standard practical pattern ([Qdrant agentic RAG](https://qdrant.tech/articles/agentic-rag/)).

### 4. Evaluation of grounding
- [ALCE](https://github.com/princeton-nlp/ALCE): fluency, correctness, **citation precision/recall** via NLI.
- RAGAS faithfulness; citation accuracy without attribution training averages only 65–70%. ([Survey](https://arxiv.org/html/2504.14891v1))
- Legal-specific: Stanford taxonomy; GOV.UK's six criteria; GovTech's "cluster unanswerable questions."

## Key takeaways for a Swiss Grounding MCP

1. **Jurisdiction must be a hard parameter, not a hope.** Every search tool should take `jurisdiction` (CH / canton code / BFS municipality ID) and `level` and filter *before* retrieval; return the jurisdiction on every hit. Rule-based routing beats learned routing here.
2. **Versioning/freshness is the #1 failure mode** (0% correct date-applicable retrieval with static RAG; Luzi died from stale data). Expose `as_of` dates, return `in_force_from/to`, `last_modified`, and the ELI version URI.
3. **Return citations as structured data** (ELI/SR number, article, language, URL, effective date, snippet) rather than prose. Never let the model synthesise URLs.
4. **Few, namespaced, well-described tools** (~5–8), with `concise|detailed` output modes, pagination, `readOnlyHint`. Avoid the 250-tool anti-pattern.
5. **Prefer curated Q&A / structured provisions over raw crawled pages** where stakes are legal; crawled service pages produced NYC's illegal advice.
6. **Ship with an eval harness:** gold set of jurisdiction- and date-specific Swiss questions, citation precision/recall, faithfulness, Stanford's four legal error categories; log unanswerable queries.
7. **Honesty > coverage:** partial answers and refusals with a handoff beat confident wrong answers; add a disclaimer at the tool-result level so downstream agents inherit it.
8. **Sovereignty/hosting matters politically**; a Swiss MCP should be deployable on Swiss cloud and require no API keys for public sources.
