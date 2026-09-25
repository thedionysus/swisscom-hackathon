"""Deterministic perturbations of a question, for robustness checks without LLM spend."""
import random
import re
import unicodedata

FILLER = {"de": "bitte", "fr": "s'il vous plaît", "it": "per favore", "en": "please", "rm": "per plaschair"}
_TRAIL = re.compile(r"([?!.]*)\s*$")


def lowercase(q: str) -> str:
    return q.lower()


def strip_diacritics(q: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", q) if not unicodedata.combining(c))


def drop_question_mark(q: str) -> str:
    return q.rstrip().rstrip("?").rstrip()


def typo(q: str, seed: int) -> str:
    """Swaps two adjacent, different letters inside one word of four letters or more."""
    spots = [m.start() + i for m in re.finditer(r"\w{4,}", q) for i in range(1, len(m.group()) - 2)
             if q[m.start() + i] != q[m.start() + i + 1]]
    if not spots:
        return q
    i = random.Random(seed).choice(spots)
    return q[:i] + q[i + 1] + q[i] + q[i + 2:]


def _split_tail(q: str) -> tuple[str, str]:
    m = _TRAIL.search(q)
    return q[:m.start()].rstrip(), m.group(1)


def add_filler(q: str, language: str) -> str:
    body, tail = _split_tail(q)
    return f"{body} {FILLER[language]}{tail}"


def strip_filler(q: str, language: str) -> str:
    body, tail = _split_tail(q)
    word = FILLER[language]
    return f"{body[:-len(word)].rstrip(' ,')}{tail}" if body.lower().endswith(" " + word) else q


def perturbations(q: str, language: str, seed: int) -> dict[str, str]:
    """Named variants of the question; a variant equal to the original is left out."""
    variants = {"lowercase": lowercase(q), "no_diacritics": strip_diacritics(q), "typo": typo(q, seed),
                "add_filler": add_filler(q, language), "strip_filler": strip_filler(q, language),
                "no_question_mark": drop_question_mark(q)}
    return {name: v for name, v in variants.items() if v != q}
