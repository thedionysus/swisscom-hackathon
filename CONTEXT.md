# Swiss Grounding

An MCP server that hands a language model cited evidence from Swiss public sources, scoped to the jurisdiction a question applies to. This glossary fixes the terms used when talking about the server, its sources, and its failure modes.

## Language

### Jurisdiction

**Extent**:
The jurisdiction node a document or chunk applies to: Switzerland, a canton, a municipality, a Kreis, or a Quartier.
_Avoid_: Scope, region, area

**Extent path**:
The chain of extents from Switzerland down to a resolved location, inclusive. A search returns only chunks whose extent lies on this path.
_Avoid_: Ancestor list, hierarchy

**Ambiguous location**:
An input naming more than one place that does not sit on a single path, such as Wil in Zurich and Wil in St. Gallen, or a Quartier and a commune sharing a name. The server asks which one is meant instead of guessing.
_Avoid_: Fallback, best guess

**Coverage signal**:
The part of a search result that states, per extent on the path, whether any indexed document exists there. A result stays `results` when only parent extents have data; the signal is what makes the gap visible.
_Avoid_: Fallback notice, warning

**Calendar evidence**:
A chunk that describes one dated event, such as a waste collection on a given day. Ranked by nearness to today among future events; past events stay visible but sink to the bottom. "Upcoming" is used interchangeably with "future" for this evidence, including in code (e.g. `UPCOMING_CALENDAR_CAP`).
_Avoid_: Schedule entry, event record

**Commune register**:
The Federal Statistical Office list of every Swiss commune with its BFS number and canton. The location tree is meant to hold all of them, whether or not any source covers them, so a place always resolves to its own node.
_Avoid_: Municipality list, gazetteer

**Topic**:
The subject a question is about, drawn from the fixed list of twenty citizen-facing topics. Fixed before searching, alongside the extent path: a chunk that does not carry the topic is not evidence for that question.
_Avoid_: Category hint, tag, subject area

**Off-topic evidence**:
A chunk that sits on the extent path and carries the topic, but does not address what was asked. A referendum clause returned for a question about dog tax is off-topic evidence, not weak evidence.
_Avoid_: Irrelevant result, low-quality hit, noise

**Boilerplate chunk**:
A stored chunk that carries a page's furniture -- navigation menus, download links, postal addresses, office hours -- rather than its substance. Indistinguishable from content by topic or by similarity, so it must be excluded at ingestion, not at ranking.
_Avoid_: Chrome, navigation junk, nav text

**Reclean**:
The maintenance step that deletes boilerplate chunks already sitting in the index, and any document left with none, undoing the fact that they were ingested at all. A separate command run after the fact, not part of ingestion itself, until a later step excludes boilerplate at ingestion time and this has nothing left to do.
_Avoid_: Cleanup, purge, prune

**Recontext**:
The maintenance step that gives every stored chunk a description and its own topics, read from the English text already in the index -- no re-crawl and no re-translation. One model call per chunk, committed as it is paid for, so an interrupted run resumes where it stopped and a chunk that already carries a context is left alone. It quotes the document's title, so a document whose title is only its own identifier is refused until that title is repaired. The same pass deletes the chunks the model judges boilerplate, which is the only thing it destroys; a document those drops leave with no chunks at all is reported and left standing, and erased only when a run is told to.
_Avoid_: Re-enrichment, re-tagging, reprocessing

**Narrowing**:
The ingestion step that moves a document from its source's default extent to a more specific one found in its text. Only a level marker, or a bare name in the title or a heading, may narrow. A name shared with an ancestor of the default extent never narrows on its own.
_Avoid_: Localisation, scoping

**Level marker**:
A word that fixes which level a place name means: Kanton, Stadt, Gemeinde, Kreis, Quartier, or a postal code. "Stadt Zürich" is marked; "Zürich" is bare.
_Avoid_: Qualifier, prefix

**Specificity tier**:
How far a chunk's extent sits from the jurisdiction a question resolved to, counted in steps up the extent path: 0 is that jurisdiction itself, 1 its parent, rising to the federal root. Published on every citation as `tier`, and one of the features of the relevance probability. It no longer orders results by itself.
_Avoid_: Level, depth, rank, specificity score

**Relevance floor**:
Retired. The uncalibrated cosine distance that let a chunk claim a specificity tier. Replaced by the reranker score and, once fitted, the relevance probability.

**Reranker**:
The cross-encoder model that reads the question and a candidate passage together and scores how well the passage answers it. Not the old tier-first ordering, which also went by this name.
_Avoid_: Scorer, ranking stage

**Relevance probability**:
The calibrated probability that a passage answers the question, fitted on judged pairs from the golden set. It orders results and decides abstention. Until it is fitted, the reranker score stands in for it.
_Avoid_: Confidence score, similarity

**Abstention threshold**:
The relevance probability below which the server answers `no_evidence` rather than cite its best passage. It is chosen for a target precision, not set by hand.
_Avoid_: Cutoff, floor

**Distance**:
Overloaded, and both senses are published side by side on every citation. A citation's `distance` is a *cosine distance* in embedding space, from the chunk to the vector that was searched. Its `tier` is a distance in the *location tree*, counted in hops up the extent path. Name the sense whenever both are in scope; in code `Hit.distance` is the first and `hops_to_extent` the second, and `LocationTree.distance` is the second under the ambiguous name.
_Avoid_: Similarity or relevance for the cosine sense; tree distance or depth for the hop sense

### Scope

**Declared scope**:
The topics and places the server states it answers for: federal information for all of Switzerland, six named cantons, seven named municipalities, and a named set of live lookups. Answer quality is promised inside it and nowhere else.
_Avoid_: Coverage, supported area

**Outside-scope question**:
A question about a place outside Switzerland, or about a topic or place outside the declared scope. It is answered by saying so, never by asking the user for a location and never by answering from nearby evidence.
_Avoid_: Unsupported query, out-of-coverage, fallback

**Live lookup**:
An answer read at question time from an official data service rather than retrieved from the index, such as a premium, a connection, or a collection date. It carries the service's own reference date.
_Avoid_: Real-time search, API tool

**Source unavailable**:
The state in which the official source for an in-scope question could not be reached. It is reported as such, distinct from the source being reachable and holding no answer.
_Avoid_: Error, no results

### Languages and versions

**Language store**:
The part of the index holding every chunk written in one language: German, French, Italian or English. A chunk lives in the store of the language it was published in, and is never translated into another store.
_Avoid_: Language index, language collection

**Language version**:
One publication of a document in one language, such as the French text of the Code of Obligations. Versions of the same document are not duplicates; each is evidence in its own right.
_Avoid_: Translation, copy

**Translation group**:
The set of language versions that publish the same document. A document published in only one language forms a group of one.
_Avoid_: Language family, document cluster

**Aligned chunk**:
A chunk's counterpart in another language version of its translation group, matched by position in the document's structure (for law, the same article and paragraph).
_Avoid_: Parallel chunk, sibling chunk

**Authentic version**:
A language version that has legal force. German, French and Italian federal law are equally authentic; an English version is published for information only.
_Avoid_: Official translation, original

**Corroboration**:
The evidence that a chunk is relevant because its aligned chunks in other language versions were also retrieved for the same question. It is the share of the group's other existing authentic versions found among the candidates. A group with no other authentic version is "not applicable", not zero, so a page published in one language is never marked down. English federal law is shown but never counts. Aligned versions that carry different validity dates are divergent and do not corroborate each other.
_Avoid_: Cross-check, consensus, agreement score

**Divergent versions**:
Aligned chunks of one translation group whose language versions disagree on validity date or were fetched from different consolidations. Flagged on the citation; never counted as corroboration.
_Avoid_: Conflict, mismatch

**Corroboration basis**:
How the aligned chunks were found: `independent` when each language store was queried in its own language, `cross_lingual` when one multilingual query found them all. Each is a separate feature of the relevance probability, so the weight comes from the evals.
_Avoid_: Corroboration type, mode

### Descriptions

**Document description**:
A short generated statement of what a whole document is, who published it and which jurisdiction it applies to.
_Avoid_: Summary, abstract

**Chunk description**:
A short generated statement of what one chunk covers and what questions it answers, written once per translation group in each language the group has.
_Avoid_: Generated context, summary, blurb

**Breadcrumb**:
The path of headings above a chunk within its document, such as Code of Obligations > Employment contract > Art. 336c.
_Avoid_: Heading path, section trail

Descriptions and breadcrumbs are indexed with the chunk so retrieval can find it, and are never quoted: a citation draws on the published text alone.

### Index

**Embedding index**:
The set of vectors one embedding model, at one version and dimension, produced for the corpus. Two indexes are never compared with each other; changing the model means building a new index.
_Avoid_: Vector store, embeddings table

### Evaluation

**Probe**:
A hand-written question with a location, and the behaviour the raw tool response must show: status, resolved extent, required and forbidden sources or documents, coverage signal, event date rule. Graded deterministically without a model.
_Avoid_: Test case, gold question, eval

**Structural probe**:
A probe whose expected behaviour does not depend on ranking: status, resolved extent, coverage signal, event date rule. Runs on fixture data in CI.

**Ranking probe**:
A probe whose expected behaviour is about which evidence ranks where: a sibling must not appear in the top results, the right article must outrank a lookalike. Runs only against the live database with the real embedder.

**Judge case**:
A probe additionally answered by a language model using the tools, with the final answer graded by a second model. Used to measure how much an answer degrades across models; never the primary gate.
_Avoid_: End-to-end test, LLM eval

### Failure classes

**Jurisdiction confusion**:
Evidence from a sibling or unrelated jurisdiction is presented as applying to the asked location.

**Authority-hierarchy violation**:
Lower-authority evidence (institutional guidance, municipal information) is presented as overriding higher-authority law, or the reverse.

**Temporal misapplication**:
Evidence from a superseded or future version, or a past calendar event, is presented as current.

**Entity substitution**:
Evidence about a different named thing (another Kreis, waste type, animal, act) is presented as answering the question.

**Off-topic retrieval**:
Evidence is returned for a question that no indexed chunk addresses, because the server ranks whatever passed the extent filter instead of reporting that nothing is on topic.
_Avoid_: Poor relevance, bad ranking

**Silent under-coverage**:
The server returns evidence from a parent extent for a location it holds no local data on, without signalling that the local level is missing. Distinct from `no_evidence`, which is an explicit signal.
_Avoid_: Fallback, graceful degradation
