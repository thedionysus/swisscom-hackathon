---
status: accepted
date: 2026-09-16
---

# Results for an uncovered location carry a coverage signal rather than becoming `no_evidence`

Most Swiss places have no local documents indexed, and after the planned expansion to all public sources that will still be true for many of them. A question about such a place still gets the federal and cantonal evidence that applies there, with status `results`, and the response states per extent on the path whether any document exists at that level. We rejected returning `no_evidence` whenever the most specific levels are empty, because federal law is often the correct answer and discarding it lowers recall for no gain. We rejected leaving the response as it was, because a caller cannot tell "answered from local rules" apart from "answered from parent rules", which is the failure class the glossary calls silent under-coverage.

## Consequences

- The response contract of `swiss_search` gains a field. Clients that read the signal must repeat it in their answer; the judge cases check for that.
- `swiss_coverage` and `swiss_search` share the per-extent document count; keep one implementation.
