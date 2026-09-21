---
status: accepted
date: 2026-09-21
---

# Every chunk carries generated context, which steers retrieval and is never cited

A chunk is stored with no indication of what it belongs to. The article setting penalties for mistreating animals reads, in the index, as a bare sentence about penalties: nothing says it comes from the Animal Welfare Act, and nothing says it has no bearing on dogs. Fedlex titles compound this, because the SPARQL title binding is optional and never binds, so all five acts are titled by their SR number and one is titled with an empty string. The subject of a document is therefore absent from the one place retrieval looks.

Each chunk gains a short generated description of what its document is about and what the chunk itself covers. That text is prepended to the chunk before embedding and included in the keyword index, so retrieval sees it, and it is excluded from citations, so a caller is never shown generated prose as though it were the source. Where the original wording carries a term with no English equivalent, the description keeps that term, which puts `Grüngutabfuhr` into an English index without building a multilingual one.

The same pass identifies boilerplate. A chunk whose honest description is that it lists a site's navigation sections is page furniture, not evidence, and is dropped rather than stored. Every one of the seventy-nine chunks currently held at canton and city level is this, which is why the city of Zurich reports seventeen indexed documents and can answer nothing.

## Consequences

- Generated text enters the retrieval surface. A wrong description makes a chunk findable under the wrong subject, and the source text no longer constrains what the chunk appears to be about.
- Citations must draw only on `text_original` and `text_en`. A future change that quotes the indexed text would leak generated prose into an answer presented as sourced.
- Boilerplate becomes a classification rather than a guess, which is what makes dropping it safe. Similarity could not separate it: a download link scored closer to a forest question than the page's only real sentence about forests.
- Generation costs one model call per chunk and reads only stored text, so it needs no re-crawl. Re-embedding afterwards is local and free.
- Coverage counts fall to zero for canton and city once boilerplate is dropped. That is the honest number, and it is what makes the coverage signal of ADR 0001 mean anything.
