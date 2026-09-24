"""The passage inside a chunk that supports the answer (practice case citation_support)."""
import re
from collections.abc import Sequence

MAX_PASSAGE_CHARS = 600
SENTENCE = re.compile(r"(?<=[.!?;:])\s+|\n+")
TOKEN = re.compile(r"[\wà-ÿ]{4,}|\d+[a-z]?", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN.findall(text)}


def _windows(sentences: Sequence[str]) -> list[str]:
    out = []
    for start in range(len(sentences)):
        window = ""
        for s in sentences[start:]:
            candidate = f"{window} {s}".strip()
            if len(candidate) > MAX_PASSAGE_CHARS:
                break
            window = candidate
        out.append(window or sentences[start][:MAX_PASSAGE_CHARS])
    return out


def best_passage(text: str, queries: Sequence[str]) -> str:
    if len(text) <= MAX_PASSAGE_CHARS:
        return text
    wanted = set().union(*(_tokens(q) for q in queries)) if queries else set()
    sentences = [s.strip() for s in SENTENCE.split(text) if s.strip()]
    windows = _windows(sentences)
    return max(windows, key=lambda w: (len(wanted & _tokens(w)), -windows.index(w)))
