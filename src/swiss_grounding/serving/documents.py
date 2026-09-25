"""swiss_get_document: whole articles around a hit, by id, official reference, or URL; any language version."""
import re
from dataclasses import dataclass

import psycopg

# Abbreviations of the acts in the declared scope (DE / FR / IT), to their SR number.
ACTS: dict[str, str] = {
    "BV": "101", "CST": "101", "COST": "101",
    "ZGB": "210", "CC": "210",
    "OR": "220", "CO": "220",
    "STGB": "311.0", "CP": "311.0",
    "AIG": "142.20", "LEI": "142.20", "LSTRI": "142.20",
    "SVG": "741.01", "LCR": "741.01", "LCSTR": "741.01",
    "VZV": "741.51", "OAC": "741.51", "OAC-TI": "741.51",
    "MWSTG": "641.20", "LTVA": "641.20", "LIVA": "641.20",
    "AHVG": "831.10", "LAVS": "831.10",
    "KVG": "832.10", "LAMAL": "832.10",
    "AVIG": "837.0", "LACI": "837.0", "LADI": "837.0",
}
# The suffix (336c, 12bis) is written without a space; with a space, "Art. 8 BV" would read "BV" as a suffix.
ARTICLE = re.compile(r"\b(?:art\.?|artikel|article|articolo)\s*(\d+)"
                     r"((?:bis|ter|quater|quinquies|sexies|septies|octies|[a-z])?)\b", re.IGNORECASE)
SR = re.compile(r"\bSR\s*(\d{1,3}(?:\.\d+)*)", re.IGNORECASE)
URL = re.compile(r"^(https?://\S+?)(?:#(\S+))?$")
WORD = re.compile(r"\b([A-Za-z]{2,6})\b")
MAX_CHUNKS = 120
DOC_COLUMNS = ("id, source_id, url, language, translation_group_id, title, identifier, publisher, authority, "
               "extent_id, is_authentic, valid_from, valid_to, status, modified_at, fetched_at, extraction")
CHUNK_COLUMNS = "id as chunk_id, align_key, ordinal, breadcrumb, anchor, text"


@dataclass(frozen=True)
class Reference:
    sr: str | None = None
    article: str | None = None
    url: str | None = None


def _article_eid(number: str, suffix: str) -> str:
    return f"art_{number}_{suffix.lower()}" if suffix else f"art_{number}"


def parse_reference(text: str) -> Reference | None:
    text = text.strip()
    if m := URL.match(text):
        return Reference(url=m.group(1), article=m.group(2))
    art = ARTICLE.search(text)
    article = _article_eid(art.group(1), art.group(2)) if art else None
    if m := SR.search(text):
        return Reference(sr=m.group(1), article=article)
    rest = ARTICLE.sub(" ", text)
    act = next((ACTS[w.upper()] for w in WORD.findall(rest) if w.upper() in ACTS), None)
    return Reference(sr=act, article=article) if act else None


def _find_by_reference(conn, ref: Reference, language: str | None) -> dict | None:
    lang = language or "de"
    if ref.url:
        return conn.execute(f"select {DOC_COLUMNS} from corpus.document where url = %s and status = 'current'",
                            (ref.url,)).fetchone()
    return conn.execute(f"select {DOC_COLUMNS} from corpus.document where identifier = %s and language = %s "
                        "and status = 'current'", (f"SR {ref.sr}", lang)).fetchone()


def _switch_language(conn, doc: dict, language: str) -> dict | None:
    return conn.execute(f"select {DOC_COLUMNS} from corpus.document where translation_group_id = %s "
                        "and language = %s and status = 'current'",
                        (doc["translation_group_id"], language)).fetchone()


def _chunks(conn, doc_id: int, anchor: str | None, align_key: str | None) -> list[dict]:
    if anchor:
        sql = f"select {CHUNK_COLUMNS} from corpus.chunk where document_id = %s and anchor = %s order by ordinal"
        return conn.execute(sql, (doc_id, anchor)).fetchall()
    if align_key:
        sql = f"select {CHUNK_COLUMNS} from corpus.chunk where document_id = %s and align_key = %s order by ordinal"
        return conn.execute(sql, (doc_id, align_key)).fetchall()
    sql = (f"select {CHUNK_COLUMNS} from corpus.chunk where document_id = %s and status <> 'boilerplate' "
           f"order by ordinal limit {MAX_CHUNKS + 1}")
    return conn.execute(sql, (doc_id,)).fetchall()


def get_document(conn: psycopg.Connection, *, document_id: int | None = None, chunk_id: int | None = None,
                 reference: str | None = None, language: str | None = None) -> dict:
    anchor = align_key = None
    if reference:
        ref = parse_reference(reference)
        if ref is None:
            return {"error": f"could not read the reference {reference!r}; use e.g. 'Art. 336c OR' or an official URL"}
        doc = _find_by_reference(conn, ref, language)
        anchor = ref.article
    elif document_id is not None:
        doc = conn.execute(f"select {DOC_COLUMNS} from corpus.document where id = %s", (document_id,)).fetchone()
        if doc and chunk_id is not None:
            chunk = conn.execute("select anchor, align_key from corpus.chunk where id = %s and document_id = %s",
                                 (chunk_id, document_id)).fetchone()
            if chunk is None:
                return {"error": f"chunk {chunk_id} is not part of document {document_id}"}
            anchor, align_key = chunk["anchor"], chunk["align_key"]
    else:
        return {"error": "give document_id, or reference"}
    if doc is None:
        return {"error": f"no current document for {reference or document_id!r}"}
    if language and doc["language"] != language:
        switched = _switch_language(conn, doc, language)
        if switched is None:
            return {"error": f"no {language} version of this document"}
        doc = switched
    chunks = _chunks(conn, doc["id"], anchor, None if anchor else align_key)
    if (anchor or align_key) and not chunks:
        return {"error": f"{anchor or align_key} not found in document {doc['id']}"}
    langs = conn.execute("select distinct language from corpus.document where translation_group_id = %s "
                         "and status = 'current' order by language", (doc["translation_group_id"],)).fetchall()
    return {"document": doc, "chunks": chunks[:MAX_CHUNKS], "truncated": len(chunks) > MAX_CHUNKS,
            "available_languages": [r["language"] for r in langs]}
