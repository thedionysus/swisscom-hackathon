You grade one answer given to a resident of Switzerland. You see the question, the evidence the answering model
received from the tools (verbatim), and the answer.

Return JSON: {"faithful": true|false, "unsupported_claims": ["..."], "cited_urls_in_evidence": true|false}

- faithful is true only if every factual claim in the answer (numbers, dates, deadlines, fees, rules, places)
  is stated in or directly implied by the evidence. Advice to contact an office is not a factual claim.
- An answer that says the question is not covered, or asks for the user's place, is faithful when the evidence
  says so (status outside_scope / needs_location / no_evidence).
- cited_urls_in_evidence is false if the answer cites any URL that does not appear in the evidence.

Question:
{question}

Evidence:
{evidence}

Answer:
{answer}
