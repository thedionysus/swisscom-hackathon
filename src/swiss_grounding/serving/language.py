"""Which language a question is in, from function words only (no model at question time)."""
import re

FUNCTION_WORDS: dict[str, frozenset[str]] = {
    "rm": frozenset({"cura", "èn", "las", "ils", "da", "dal", "dals", "per", "la", "scola", "scoula",
                     "co", "tge", "vegn", "nus", "vus", "quai", "pli", "betg", "brich",
                     "nossa", "vossa", "vschinauncha", "vischnanca", "atun", "d'atun"}),
    "de": frozenset({"der", "die", "das", "und", "ist", "wie", "wann", "wird", "bei", "uns", "ich",
                     "mein", "meine", "meinem", "nach", "für", "mit", "nicht", "ein", "eine", "im",
                     "den", "dem", "des", "zu", "auf", "was", "welche", "muss", "kann"}),
    "fr": frozenset({"la", "de", "le", "les", "des", "et", "est", "mon", "ma", "mes", "dans", "pour", "combien",
                     "quand", "comment", "une", "du", "au", "aux", "je", "que", "qui", "sur", "en",
                     "pas", "quel", "quelle", "doit", "peut"}),
    "it": frozenset({"la", "il", "lo", "gli", "le", "di", "del", "della", "per", "con", "un", "una", "è",
                     "più", "quando", "come", "quanto", "mio", "mia", "che", "non", "sono", "nel",
                     "alla", "dove", "quale", "devo", "posso"}),
    "en": frozenset({"the", "is", "what", "when", "how", "for", "my", "of", "and", "to", "in", "do",
                     "does", "can", "which", "a", "an", "i", "must", "should"}),
}
# Words only Romansh uses. Romansh shares many short words with Italian and French, so it wins
# only when one of these matched; then it also wins ties (a Romansh question must reach the rm store).
ROMANSH_MARKERS: frozenset[str] = frozenset({"cura", "èn", "tge", "betg", "brich", "vschinauncha", "vischnanca",
                                             "scoula", "atun", "d'atun", "vegn", "nossa", "vossa", "quai", "dals"})
# Order breaks remaining ties: German before English, French before Italian.
TIE_ORDER: tuple[str, ...] = ("de", "fr", "it", "en")
WORD = re.compile(r"[a-zà-ÿ']+")


def detect_language(text: str) -> str | None:
    words = WORD.findall(text.lower())
    counts = {lang: sum(1 for w in words if w in vocab) for lang, vocab in FUNCTION_WORDS.items()}
    if any(w in ROMANSH_MARKERS for w in words) and counts["rm"] >= max(counts.values()):
        return "rm"
    counts["rm"] = 0
    best = max(counts.values(), default=0)
    if best == 0:
        return None
    return next(lang for lang in TIE_ORDER if counts[lang] == best)
