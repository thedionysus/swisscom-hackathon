---
status: accepted
date: 2026-09-23
amends: 0009-declared-scope
---

# The MCP contract is six read-only tools, each with one job, checked against every sample and practice question

The evaluators use two unknown clients with two unknown models and grade agent efficiency. The contract follows two rules: no two tools may answer the same request, and every sample question, practice case and topic area must be answerable in as few calls as possible.

| Tool | Job |
|---|---|
| `swiss_search(question, locations?, translations?, as_of?, limit?)` | Evidence retrieval. Accepts up to three locations and returns results grouped by place, never merged. Resolves places itself and applies the status order of ADR 0013. `translations` is an optional `{de, fr, it, en}` map (ADR 0011). Every `no_evidence` response carries a one-line statement of the declared scope. |
| `swiss_get_document(document_id? , chunk_id?, reference?, language?)` | The whole article or section around a hit. Also takes an official reference (SR number and article, or an official URL), and a language to switch to another version of the same document. |
| `swiss_scope()` | The declared scope, including what is not covered. Replaces `swiss_coverage` and `swiss_list_categories`. |
| `swiss_premium`, `swiss_connections`, `swiss_reference_rate` | Lookups (ADR 0014). |

Removed: `swiss_resolve_location` (search resolves places and asks back itself), `swiss_suggest_source` (the only write tool, and it answers nothing), the `question_en`/`topic_en` parameters (ADR 0011), and the client-chosen `topics`/`categories` filter, because an unknown model choosing a filter risks filtering out the answer. Topic remains an internal per-chunk signal (ADR 0003).

Declared outside the scope (amending ADR 0009): computed amounts such as a tax bill or a pension (we give the official rules and link the official calculator), and the commercial register, since Zefix's REST API needs registered credentials. Statistics, geodata and weather were already outside it.

## Considered Options

- Keep all tools and add the lookups (nine): overlapping place-taking tools lead weaker models into three calls where one would do.
- One call per place for multi-place questions: correct only when the model thinks to split the question.

## Consequences

- The search tool description lists what is not covered, so a model can answer "not covered" after a single call.
- Adding a tool later is allowed when it does a job no other tool does, for example a company-register lookup if the keyless UID register service turns out usable.
