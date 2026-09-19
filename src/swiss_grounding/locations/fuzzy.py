"""Token-level tolerance for place names: a hit counts only when every input token is accounted for."""
from swiss_grounding.locations.tree import normalize

MIN_FUZZY_LENGTH = 6      # tokens shorter than this must match exactly
MAX_EDITS = 1
LABEL_PUNCTUATION = "()[],."


def edit_distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(t.strip(LABEL_PUNCTUATION) for t in normalize(text).split() if t.strip(LABEL_PUNCTUATION))


def token_matches(token: str, candidate: str) -> bool:
    if token == candidate:
        return True
    if len(token) < MIN_FUZZY_LENGTH:
        return False
    return edit_distance(token, candidate) <= MAX_EDITS


def tokens_covered(text: str, label: str) -> bool:
    """True when every token of text matches some token of label (exactly, or within one edit for long tokens)."""
    label_tokens = _tokens(label)
    return all(any(token_matches(t, c) for c in label_tokens) for t in _tokens(text))
