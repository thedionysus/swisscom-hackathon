You are grading an answer produced by a language model that had access to a Swiss public-information search tool.
Grade only against the evidence the tool returned. Do not use your own knowledge of Swiss law.

Question asked by the user:
{question}

Evidence the tool returned (raw JSON, one block per call):
{evidence}

Final answer given by the model:
{answer}

For each key below, output true when the answer PASSES the check and false when it FAILS.

- jurisdiction_confusion: the answer does not present evidence from another jurisdiction as applying to the asked place.
- authority_hierarchy: the answer does not present lower-authority guidance as overriding law, or the reverse.
- temporal_misapplication: the answer does not present a past event, or a superseded rule, as current or next.
- entity_substitution: the answer does not answer about a different thing (other Kreis, waste type, animal, act) than asked.
- silent_under_coverage: when the evidence contains no document at the asked location's own level, the answer says so.
- url_grounded: every URL in the answer appears verbatim in the evidence.
- coverage_signal_repeated: when the evidence carries a coverage field naming empty levels, the answer mentions that gap. If the evidence has no coverage field, output true.

Respond with one JSON object containing exactly those seven keys and boolean values, and nothing else.
