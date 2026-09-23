"""Document and chunk descriptions with topics, one call per translation group (Task 17).

Documents first: one task per translation group with live documents and no description. Then chunks:
one task per (translation group, status, align_key) with undescribed chunks. Each call writes a
description in every language the group has. A failed reply quarantines the task and leaves the rows
undescribed, so a re-run retries them. Every run commits after each outcome, because the batch runner
marks a batch ingested only once its last outcome has been consumed.

Custom ids: `doc|<group>|<langs>` and `chunk|<group>|<status>|<langs>|<align_key>` (the align key is
last and may contain any character; it is recovered with `split("|", 4)`).
"""
import json
from collections.abc import Sequence

import psycopg

from swiss_grounding.corpus.budget import cost_usd, estimate_tokens, record_spend
from swiss_grounding.corpus.persist import quarantine
from swiss_grounding.corpus.runner import LlmOutcome, LlmTask
from swiss_grounding.corpus.topics import TOPIC_IDS, TOPICS
from swiss_grounding.db.connection import connect

MAX_DESCRIPTION_CHARS = 600
MAX_TOPICS = 3
DOC_EXCERPT_CHARS = 3000
CHUNK_TEXT_CHARS = 2500
OUTPUT_TOKENS_PER_LANGUAGE = 90
DEFAULT_JURISDICTION = "Switzerland"
LAW_AUTHORITIES = ("federal_law", "cantonal_law", "municipal_law")
QUARANTINE_SOURCE = "describe"
LEDGER_KIND = "describe"
TOPIC_LIST = "\n".join(f"- {t.id}: {t.label} ({t.covers})" for t in TOPICS)

SYSTEM = "You describe official Swiss public information for a multilingual search index. Reply with JSON only."
DOC_PROMPT = """Below are the language versions of one document published by {publisher}.
For EACH language key in the versions, write one or two sentences IN THAT LANGUAGE that say what the document is
(name the act, page or leaflet explicitly), who publishes it, and which jurisdiction it applies to ({jurisdiction}).
Then choose up to three topic ids from this list that the whole document is about:
{topics}
Reply as {{"descriptions": {{"<language>": "<sentence(s)>"}}, "topics": ["<id>"]}}.

Versions:
{versions}"""
CHUNK_PROMPT = """Document: {document}
Below is one passage of this document in each language it is published in.
For EACH language key, write one or two sentences IN THAT LANGUAGE saying what the passage covers and which
questions a resident could answer with it, using the words a resident would use. Keep legal references (article,
paragraph, letter) exact. Do not add facts that are not in the passage.
Choose up to three topic ids from the list below; the starting guess is {prior}.
Set "boilerplate" to true only if the passage is navigation, a cookie notice, contact details or other page
furniture with no substantive content.
{topics}
Reply as {{"descriptions": {{"<language>": "<sentence(s)>"}}, "topics": ["<id>"], "boilerplate": false}}.

Passage:
{versions}"""
LIVE = "('current','scheduled')"


# --- reply validation -------------------------------------------------------------------------------

def _descriptions(reply: dict, languages: tuple[str, ...]) -> dict[str, str]:
    given = reply.get("descriptions")
    if not isinstance(given, dict):
        raise ValueError("descriptions missing")  # noqa: TRY004 - callers quarantine on ValueError
    out = {}
    for lang in languages:
        text = given.get(lang)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"description missing for {lang}")
        out[lang] = text.strip()[:MAX_DESCRIPTION_CHARS]
    return out


def _topics(reply: dict, prior: list[str]) -> list[str]:
    raw = reply.get("topics") if isinstance(reply.get("topics"), list) else []
    chosen = [t for t in dict.fromkeys(x for x in raw if isinstance(x, str)) if t in TOPIC_IDS][:MAX_TOPICS]
    return chosen or list(prior)


def parse_doc_reply(reply: dict, languages: tuple[str, ...]) -> tuple[dict[str, str], list[str]]:
    return _descriptions(reply, languages), _topics(reply, [])


def parse_chunk_reply(reply: dict, languages: tuple[str, ...],
                      prior: list[str]) -> tuple[dict[str, str], list[str], bool]:
    boilerplate = reply.get("boilerplate", False)
    if not isinstance(boilerplate, bool):
        raise ValueError("boilerplate must be true or false")  # noqa: TRY004 - callers quarantine on ValueError
    return _descriptions(reply, languages), _topics(reply, prior), boilerplate


# --- task building ----------------------------------------------------------------------------------

def _group_versions(conn: psycopg.Connection, gid: str) -> tuple[list[dict], dict[str, dict]]:
    """Live versions of a group, one per language. The place name comes from `public.location.names`,
    stored as {"labels": {lang: name}, "aliases": [...]}; communes carry only a German label."""
    docs = conn.execute(
        "select distinct on (d.language) d.id, d.language, d.title, d.publisher, "
        "coalesce(l.names->'labels'->>'en', l.names->'labels'->>'de', l.names->'labels'->>'fr', "
        "l.names->'labels'->>'it') as place "
        "from corpus.document d join public.location l on l.id = d.extent_id "
        f"where d.translation_group_id = %s and d.status in {LIVE} "
        "order by d.language, (d.status = 'current') desc, d.id desc", (gid,)).fetchall()
    versions = {}
    for d in docs:
        excerpt = conn.execute("select left(string_agg(text, ' ' order by ordinal), %s) as t from corpus.chunk "
                               "where document_id = %s", (DOC_EXCERPT_CHARS, d["id"])).fetchone()["t"] or ""
        versions[d["language"]] = {"title": d["title"], "excerpt": excerpt}
    return docs, versions


def build_doc_tasks(conn: psycopg.Connection, model: str, limit: int | None) -> list[LlmTask]:
    groups = conn.execute(
        "select g.id from corpus.translation_group g where g.description_by_lang = '{}'::jsonb and exists "
        f"(select 1 from corpus.document d where d.translation_group_id = g.id and d.status in {LIVE}) "
        "order by g.id limit %s", (limit,)).fetchall()
    tasks = []
    for group in groups:
        docs, versions = _group_versions(conn, group["id"])
        user = DOC_PROMPT.format(publisher=docs[0]["publisher"], jurisdiction=docs[0]["place"] or DEFAULT_JURISDICTION,
                                 topics=TOPIC_LIST, versions=json.dumps(versions, ensure_ascii=False, indent=1))
        tasks.append(LlmTask(custom_id=f"doc|{group['id']}|{','.join(sorted(versions))}", model=model,
                             system=SYSTEM, user=user,
                             max_output_tokens=OUTPUT_TOKENS_PER_LANGUAGE * len(versions) + 100))
    return tasks


def build_chunk_tasks(conn: psycopg.Connection, model: str, limit: int | None) -> list[LlmTask]:
    rows = conn.execute(
        "select c.translation_group_id as gid, c.status, c.align_key, g.description_by_lang as doc, "
        "jsonb_object_agg(c.language, jsonb_build_object('breadcrumb', c.breadcrumb, 'text', left(c.text, %s))) as v, "
        "(array_agg(to_jsonb(c.topics)))[1] as prior "
        "from corpus.chunk c join corpus.translation_group g on g.id = c.translation_group_id "
        f"where c.status in {LIVE} and c.description = '' and c.text <> '' "
        "group by c.translation_group_id, c.status, c.align_key, g.description_by_lang "
        "order by c.translation_group_id, c.align_key limit %s", (CHUNK_TEXT_CHARS, limit)).fetchall()
    tasks = []
    for r in rows:
        languages = sorted(r["v"])
        doc = r["doc"] or {}
        document = next((doc[lang] for lang in languages if lang in doc), next(iter(doc.values()), ""))
        user = CHUNK_PROMPT.format(document=document, prior=json.dumps(r["prior"] or []), topics=TOPIC_LIST,
                                   versions=json.dumps(r["v"], ensure_ascii=False, indent=1))
        tasks.append(LlmTask(custom_id=f"chunk|{r['gid']}|{r['status']}|{','.join(languages)}|{r['align_key']}",
                             model=model, system=SYSTEM, user=user,
                             max_output_tokens=OUTPUT_TOKENS_PER_LANGUAGE * len(languages) + 80))
    return tasks


def mark_repeated_furniture(conn: psycopg.Connection, min_documents: int = 3) -> int:
    """Set status 'boilerplate' on chunks whose exact text recurs in `min_documents`+ live documents of one source.

    RAG review E2: a footer, contact block or cookie notice that survived HTML cleaning is the same chunk on
    every page; finding it by repetition is free, where the model's verdict is paid per copy. Law is exempt:
    identical articles across acts ("Aufgehoben") are rare, legitimate, and carry different breadcrumbs.
    Returns the number of chunks marked.
    """
    return conn.execute(
        "with live as (select c.id, c.language, c.chunk_hash, d.source_id, c.document_id from corpus.chunk c "
        f"join corpus.document d on d.id = c.document_id where c.status in {LIVE} "
        "and c.text <> '' and d.authority <> all(%s)), "
        "repeated as (select source_id, chunk_hash from live group by source_id, chunk_hash "
        "having count(distinct document_id) >= %s) "
        "update corpus.chunk c set status = 'boilerplate' from live l join repeated r "
        "on r.source_id = l.source_id and r.chunk_hash = l.chunk_hash "
        "where c.id = l.id and c.language = l.language", (list(LAW_AUTHORITIES), min_documents)).rowcount


def estimate_describe(tasks: Sequence[LlmTask], model: str, languages_per_task: float = 2.0,
                      batch: bool = True) -> float:
    input_tokens = sum(estimate_tokens(t.system + t.user) for t in tasks)
    output_tokens = int(len(tasks) * (OUTPUT_TOKENS_PER_LANGUAGE * languages_per_task + 40))
    return cost_usd(model, input_tokens, output_tokens, batch=batch)


# --- ingesting outcomes -----------------------------------------------------------------------------

def _spend(conn: psycopg.Connection, model: str, outcome: LlmOutcome, batch: bool) -> None:
    if outcome.input_tokens or outcome.output_tokens:
        record_spend(conn, kind=LEDGER_KIND, model=model,
                     usd=cost_usd(model, outcome.input_tokens, outcome.output_tokens, batch=batch),
                     input_tokens=outcome.input_tokens, output_tokens=outcome.output_tokens, estimated=False)


def _reply(outcome: LlmOutcome) -> dict:
    if not isinstance(outcome.data, dict):
        raise ValueError(outcome.error or "no reply")  # noqa: TRY004 - callers quarantine on ValueError
    return outcome.data


def _clear_quarantine(conn: psycopg.Connection, key: str, stage: str) -> None:
    conn.execute("delete from corpus.quarantine where source_id = %s and url = %s and stage = %s",
                 (QUARANTINE_SOURCE, key, stage))


def run_doc_descriptions(database_url: str, runner, tasks: Sequence[LlmTask], model: str, batch: bool,
                         estimated_usd: float = 0.0) -> dict[str, int]:
    report = {"done": 0, "failed": 0}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="describe-doc", estimated_usd=estimated_usd):
            _, gid, langs = outcome.custom_id.split("|")
            key = f"group:{gid}"
            _spend(conn, model, outcome, batch)
            try:
                descriptions, topics = parse_doc_reply(_reply(outcome), tuple(langs.split(",")))
            except ValueError as exc:
                quarantine(conn, QUARANTINE_SOURCE, key, "describe-doc", str(exc))
                report["failed"] += 1
            else:
                conn.execute("update corpus.translation_group set description_by_lang = %s, topics = %s where id = %s",
                             (json.dumps(descriptions, ensure_ascii=False), topics, gid))
                _clear_quarantine(conn, key, "describe-doc")
                report["done"] += 1
            conn.commit()
    return report


def _prior(conn: psycopg.Connection, gid: str, align_key: str) -> list[str]:
    row = conn.execute("select topics from corpus.chunk where translation_group_id = %s and align_key = %s "
                       "order by id limit 1", (gid, align_key)).fetchone()
    return list(row["topics"]) if row else []


def _write_chunk(conn: psycopg.Connection, gid: str, status: str, align_key: str,
                 descriptions: dict[str, str], topics: list[str], boilerplate: bool) -> None:
    """The `status` filter is the status seen when the task was built: a chunk that meanwhile became
    boilerplate (mark_repeated_furniture) or superseded is left alone."""
    for lang, text in descriptions.items():
        conn.execute(
            "update corpus.chunk set description = %s, topics = %s, "
            "status = case when %s then 'boilerplate' else status end "
            "where translation_group_id = %s and align_key = %s and language = %s and status = %s",
            (text, topics, boilerplate, gid, align_key, lang, status))


def run_chunk_descriptions(database_url: str, runner, tasks: Sequence[LlmTask], model: str, batch: bool,
                           estimated_usd: float = 0.0) -> dict[str, int]:
    report = {"done": 0, "failed": 0}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="describe-chunk", estimated_usd=estimated_usd):
            _, gid, status, langs, align_key = outcome.custom_id.split("|", 4)
            key = f"chunk:{gid}:{align_key}"
            _spend(conn, model, outcome, batch)
            try:
                descriptions, topics, boilerplate = parse_chunk_reply(
                    _reply(outcome), tuple(langs.split(",")), _prior(conn, gid, align_key))
            except ValueError as exc:
                quarantine(conn, QUARANTINE_SOURCE, key, "describe-chunk", str(exc))
                report["failed"] += 1
            else:
                _write_chunk(conn, gid, status, align_key, descriptions, topics, boilerplate)
                _clear_quarantine(conn, key, "describe-chunk")
                report["done"] += 1
            conn.commit()
    return report
