"""Per-task cost estimates computed only from constants in the main worktree's source.

Reads describe.py / budget.py / ocr.py with `ast` (no psycopg import, no DB, no network, no API).
Uses the pipeline's own estimator: tokens = len(text) // 3 (budget.CHARS_PER_TOKEN).
"""
import ast
import json
import sys
from pathlib import Path

WT = Path("<claude-tmp>/"
          "3eb7adc0-9d1e-4fdc-8182-f9c4b1379c86/scratchpad/wt-main/src")
from collections import namedtuple  # noqa: E402

_Topic = namedtuple("_Topic", "id label covers")


def _topics(path: Path) -> list:
    """Topic("id", "label", "covers") calls from topics.py, read with ast (system python is 3.9)."""
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Topic" and len(node.args) == 3:
            found.append(_Topic(*(ast.literal_eval(a) for a in node.args)))
    return found


TOPICS = _topics(WT / "swiss_grounding" / "corpus" / "topics.py")
assert len(TOPICS) == 20, len(TOPICS)


def constants(path: Path) -> dict:
    out = {}
    for node in ast.parse(path.read_text()).body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            value = node.value
        for name in targets:
            try:
                out[name] = ast.literal_eval(value)
            except Exception:
                pass
    return out


corpus = WT / "swiss_grounding" / "corpus"
D = constants(corpus / "describe.py")
B = constants(corpus / "budget.py")
O = constants(corpus / "ocr.py")
PRICES, SYNC = B["PRICES"], B["SYNC_MULTIPLIER"]
CPT = B["CHARS_PER_TOKEN"]
TOPIC_LIST = "\n".join(f"- {t.id}: {t.label} ({t.covers})" for t in TOPICS)


def tok(text: str) -> int:
    return max(1, len(text) // CPT)


def usd(model: str, tin: int, tout: int, batch: bool) -> float:
    pin, pout = PRICES[model]
    v = (tin * pin + tout * pout) / 1_000_000
    return v if batch else v * SYNC


def example(langs, boiler):
    e = {"descriptions": {l: "..." for l in langs}, "topics": ["<id>"]}
    if boiler:
        e["boilerplate"] = False
    return json.dumps(e)


def chunk_task(text_chars: int, langs=("de",), doc_desc_chars: int = 250, crumbs=("Page title", "Section")):
    versions = {l: {"breadcrumb": list(crumbs), "text": "x" * min(text_chars, D["CHUNK_TEXT_CHARS"])} for l in langs}
    user = D["CHUNK_PROMPT"].format(document="d" * doc_desc_chars, prior=json.dumps([]), topics=TOPIC_LIST,
                                    example=example(langs, True), keys=", ".join(langs),
                                    versions=json.dumps(versions, ensure_ascii=False, indent=1))
    tin = tok(D["SYSTEM"] + user)
    tout = D["ESTIMATE_TOKENS_PER_LANGUAGE"] * len(langs) + D["ESTIMATE_TOKENS_OVERHEAD"]
    return tin, tout


def doc_task(excerpt_chars: int, langs=("de",)):
    versions = {l: {"title": "t" * 60, "excerpt": "x" * min(excerpt_chars, D["DOC_EXCERPT_CHARS"])} for l in langs}
    user = D["DOC_PROMPT"].format(publisher="p" * 30, jurisdiction="Zürich", topics=TOPIC_LIST,
                                  example=example(langs, False), keys=", ".join(langs),
                                  versions=json.dumps(versions, ensure_ascii=False, indent=1))
    tin = tok(D["SYSTEM"] + user)
    tout = D["ESTIMATE_TOKENS_PER_LANGUAGE"] * len(langs) + D["ESTIMATE_TOKENS_OVERHEAD"]
    return tin, tout


print(f"TOPIC_LIST chars={len(TOPIC_LIST)}; CHUNK_PROMPT template chars={len(D['CHUNK_PROMPT'])}; "
      f"DOC_PROMPT template chars={len(D['DOC_PROMPT'])}")
print("prices (USD per 1M tokens, batch basis):", PRICES, "sync multiplier", SYNC)
print()
print("CHUNK description task (one language, as for every HTML/PDF chunk):")
for chars in (400, 1000, 1800, 2500):
    tin, tout = chunk_task(chars)
    print(f"  text {chars:>4} chars -> in {tin:>4} tok, out {tout} tok | "
          f"gpt-5-nano batch ${usd('gpt-5-nano', tin, tout, True):.6f}  sync ${usd('gpt-5-nano', tin, tout, False):.6f} | "
          f"claude-haiku-4-5 (sync) ${usd('claude-haiku-4-5-20251001', tin, tout, False):.6f}")
print()
print("DOC description task (one language):")
for chars in (1000, 3000):
    tin, tout = doc_task(chars)
    print(f"  excerpt {chars:>4} chars -> in {tin:>4} tok, out {tout} tok | "
          f"gpt-5-mini batch ${usd('gpt-5-mini', tin, tout, True):.6f}  sync ${usd('gpt-5-mini', tin, tout, False):.6f} | "
          f"claude-haiku-4-5 (sync) ${usd('claude-haiku-4-5-20251001', tin, tout, False):.6f}")
print()
tin = B["OCR_IMAGE_TOKENS"] + O["OCR_PROMPT_TOKENS"]
tout = O["OCR_OUTPUT_TOKENS"]
print(f"OCR page: in {tin} tok (placeholder image tokens), out {tout} tok | "
      f"gpt-5-mini batch ${usd('gpt-5-mini', tin, tout, True):.6f} sync ${usd('gpt-5-mini', tin, tout, False):.6f} | "
      f"claude-haiku-4-5 (sync) ${usd('claude-haiku-4-5-20251001', tin, tout, False):.6f}")
print()
# Worked example: a municipal source of 300 pages, ~6 chunks per page, 10 PDFs x 8 pages with 25% scanned.
pages, chunks_per_page, pdfs, pdf_pages, scanned_share = 300, 6, 10, 8, 0.25
docs = pages + pdfs
chunks = pages * chunks_per_page + pdfs * pdf_pages
scanned = int(pdfs * pdf_pages * scanned_share)
c_in, c_out = chunk_task(1000)
d_in, d_out = doc_task(3000)
for label, cm, dm, om, batch in (("OpenAI batch", "gpt-5-nano", "gpt-5-mini", "gpt-5-mini", True),
                                 ("Anthropic sync", "claude-haiku-4-5-20251001", "claude-haiku-4-5-20251001",
                                  "claude-haiku-4-5-20251001", False)):
    total = (chunks * usd(cm, c_in, c_out, batch) + docs * usd(dm, d_in, d_out, batch)
             + scanned * usd(om, B["OCR_IMAGE_TOKENS"] + O["OCR_PROMPT_TOKENS"], O["OCR_OUTPUT_TOKENS"], batch))
    print(f"worked example ({docs} docs, {chunks} chunks of ~1000 chars, {scanned} scanned pages), {label}: ${total:.2f}")
