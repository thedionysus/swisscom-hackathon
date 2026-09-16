---
status: accepted
date: 2026-09-16
---

# A bare place name in body text never narrows a document

Extent narrowing matched any capitalised word against every node name, with deeper nodes winning ties. Because the city of Zurich sits below the canton of the same name, the word "Zürich" on a canton page moved the page to the city, which emptied the canton level entirely. Quartier names that are ordinary words, such as City, Hard, and Werd, captured unrelated city pages. We decided that only a level marker (Kanton, Stadt, Gemeinde, Kreis, Quartier, or a postal code) may narrow from anywhere in the text; a bare name may narrow only from the title or a heading; a name that also belongs to an ancestor of the source's default extent never narrows without a marker; and common-word Quartier names always require a marker. We accepted losing the narrowing of pages that name a place only in passing, because a document filed one level too high is still returned for every question under it, while a document filed at the wrong sibling or too deep is invisible to the questions it should answer.

## Consequences

- Existing documents must be re-narrowed from their stored English text. This needs no translation or tagging, so it costs no API credits.
- `extent_reason` must name the marker or heading that moved a document, so a probe can assert why a document sits where it does.
