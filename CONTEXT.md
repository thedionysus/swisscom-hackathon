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
A chunk that describes one dated event, such as a waste collection on a given day. Ranked by nearness to today among future events; past events stay visible but sink to the bottom.
_Avoid_: Schedule entry, event record

**Commune register**:
The Federal Statistical Office list of every Swiss commune with its BFS number and canton. The location tree is meant to hold all of them, whether or not any source covers them, so a place always resolves to its own node..
_Avoid_: Municipality list, gazetteer

**Narrowing**:
The ingestion step that moves a document from its source's default extent to a more specific one found in its text. Only a level marker, or a bare name in the title or a heading, may narrow. A name shared with an ancestor of the default extent never narrows on its own.
_Avoid_: Localisation, scoping

**Level marker**:
A word that fixes which level a place name means: Kanton, Stadt, Gemeinde, Kreis, Quartier, or a postal code. "Stadt Zürich" is marked; "Zürich" is bare.
_Avoid_: Qualifier, prefix

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

**Silent under-coverage**:
The server returns evidence from a parent extent for a location it holds no local data on, without signalling that the local level is missing. Distinct from `no_evidence`, which is an explicit signal.
_Avoid_: Fallback, graceful degradation
