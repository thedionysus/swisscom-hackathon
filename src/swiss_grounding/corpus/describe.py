"""Document and chunk descriptions with topics, one call per translation group.

Documents first: one task per translation group with live documents and no description. Then chunks:
one task per (translation group, status, align_key) with undescribed chunks, once the group has its
document description. Each call writes a description in every language the task holds. A failed reply
quarantines the task and leaves the rows undescribed, so a re-run retries them. Every run commits after
each outcome, because the batch runner marks a batch ingested only once its last outcome has been consumed;
an outcome whose target is already described (a resumed batch replaying it) is skipped before any spend.

Custom ids: `doc|<group>|<langs>` and `chunk|<group>|<status>|<lang>=<chunk id>,...|<align_key>`. A chunk
task holds one chunk per language (the newest document's), written back by (id, language); a same-language
duplicate in the group keeps its empty description and is picked up by the next build. The align key is
last and may contain any character; it is recovered with `split("|", 4)`.
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
# Output caps leave headroom so a verbose reply is not truncated (which loses every language); the
# estimate uses the expected length instead.
MAX_TOKENS_PER_LANGUAGE = 180
DOC_MAX_TOKENS_PER_LANGUAGE = 200
MAX_TOKENS_OVERHEAD = 150
ESTIMATE_TOKENS_PER_LANGUAGE = 110
ESTIMATE_TOKENS_OVERHEAD = 40
DEFAULT_JURISDICTION = "Switzerland"
LAW_AUTHORITIES = ("federal_law", "cantonal_law", "municipal_law")
QUARANTINE_SOURCE = "describe"
LEDGER_KIND = "describe"
TOPIC_LIST = "\n".join(f"- {t.id}: {t.label} ({t.covers})" for t in TOPICS)
LIVE = "('current','scheduled')"

SYSTEM = "You describe official Swiss public information for a multilingual search index. Reply with JSON only."
DOC_PROMPT = """Below are the language versions of one document published by {publisher}.
For EACH language key in the versions, write one or two sentences IN THAT LANGUAGE that say what the document is
(name the act, page or leaflet explicitly), who publishes it, and which jurisdiction it applies to ({jurisdiction}).
Then choose up to three topic ids from this list that the whole document is about:
{topics}
Reply as {example}. Use exactly these keys: {keys}.

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
Reply as {example}. Use exactly these keys: {keys}.

Passage:
{versions}"""


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
        out[lang] = text.replace("\x00", "").strip()[:MAX_DESCRIPTION_CHARS]  # PostgreSQL rejects NUL
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


# --- custom ids -------------------------------------------------------------------------------------

def _chunk_ids(field: str) -> dict[str, int]:
    """`de=12,fr=34` -> {"de": 12, "fr": 34}."""
    return {lang: int(chunk_id) for lang, chunk_id in (pair.split("=") for pair in field.split(","))}


def _task_languages(custom_id: str) -> list[str]:
    parts = custom_id.split("|", 4)
    if parts[0] == "doc":
        return parts[2].split(",")
    return list(_chunk_ids(parts[3]))


def _reply_example(languages: Sequence[str], boilerplate: bool) -> str:
    example = {"descriptions": {lang: "..." for lang in languages}, "topics": ["<id>"]}
    if boilerplate:
        example["boilerplate"] = False
    return json.dumps(example)


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
                               "where document_id = %s and status <> 'boilerplate'",
                               (DOC_EXCERPT_CHARS, d["id"])).fetchone()["t"] or ""
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
        languages = sorted(versions)
        user = DOC_PROMPT.format(publisher=docs[0]["publisher"], jurisdiction=docs[0]["place"] or DEFAULT_JURISDICTION,
                                 topics=TOPIC_LIST, example=_reply_example(languages, boilerplate=False),
                                 keys=", ".join(languages),
                                 versions=json.dumps(versions, ensure_ascii=False, indent=1))
        tasks.append(LlmTask(custom_id=f"doc|{group['id']}|{','.join(languages)}", model=model,
                             system=SYSTEM, user=user,
                             max_output_tokens=DOC_MAX_TOKENS_PER_LANGUAGE * len(languages) + MAX_TOKENS_OVERHEAD))
    return tasks


# One chunk per (group, status, align_key, language): the newest document's. Groups wait for their
# document description, except in the projection.
_PENDING_CHUNKS = """
select distinct on (c.translation_group_id, c.status, c.align_key, c.language)
       c.id, c.language, c.translation_group_id, c.status, c.align_key, c.breadcrumb, c.text, c.topics
from corpus.chunk c join corpus.translation_group g on g.id = c.translation_group_id
where c.status in {live} and c.description = '' and c.text <> ''{doc_condition}
order by c.translation_group_id, c.status, c.align_key, c.language, c.document_id desc
"""
_DOC_DESCRIBED = " and g.description_by_lang <> '{}'::jsonb"
PENDING_CHUNKS = _PENDING_CHUNKS.format(live=LIVE, doc_condition=_DOC_DESCRIBED)
PROJECTED_CHUNKS = _PENDING_CHUNKS.format(live=LIVE, doc_condition="")
# Input tokens a document description adds to a chunk prompt, for groups not yet described.
PROJECTED_DOC_DESCRIPTION_TOKENS = 85


def _chunk_rows(conn: psycopg.Connection, pending_sql: str, limit: int | None) -> list[dict]:
    return conn.execute(
        "select p.translation_group_id as gid, p.status, p.align_key, g.description_by_lang as doc, "
        "jsonb_object_agg(p.language, jsonb_build_object('breadcrumb', p.breadcrumb, 'text', left(p.text, %s))) as v, "
        "jsonb_object_agg(p.language, p.id) as ids, "
        "(array_agg(to_jsonb(p.topics) order by p.language))[1] as prior "
        f"from ({pending_sql}) p join corpus.translation_group g on g.id = p.translation_group_id "
        "group by p.translation_group_id, p.status, p.align_key, g.description_by_lang "
        "order by p.translation_group_id, p.align_key limit %s", (CHUNK_TEXT_CHARS, limit)).fetchall()


def build_chunk_tasks(conn: psycopg.Connection, model: str, limit: int | None) -> list[LlmTask]:
    return [_chunk_task(r, model) for r in _chunk_rows(conn, PENDING_CHUNKS, limit)]


def project_chunk_tasks(conn: psycopg.Connection, model: str, batch: bool = True) -> tuple[int, float]:
    """(task count, USD) of the chunk pass as it will be once every document is described: groups without a
    document description yet are counted too, with PROJECTED_DOC_DESCRIPTION_TOKENS added to their prompt."""
    rows = _chunk_rows(conn, PROJECTED_CHUNKS, None)
    undescribed = sum(1 for r in rows if not r["doc"])
    extra = cost_usd(model, undescribed * PROJECTED_DOC_DESCRIPTION_TOKENS, 0, batch=batch) if undescribed else 0.0
    return len(rows), estimate_describe([_chunk_task(r, model) for r in rows], model, batch=batch) + extra


def _chunk_task(r: dict, model: str) -> LlmTask:
    languages = sorted(r["v"])
    doc = r["doc"] or {}
    document = next((doc[lang] for lang in languages if lang in doc), next(iter(doc.values()), ""))
    user = CHUNK_PROMPT.format(document=document, prior=json.dumps(r["prior"] or []), topics=TOPIC_LIST,
                               example=_reply_example(languages, boilerplate=True), keys=", ".join(languages),
                               versions=json.dumps(r["v"], ensure_ascii=False, indent=1))
    ids = ",".join(f"{lang}={r['ids'][lang]}" for lang in languages)
    return LlmTask(custom_id=f"chunk|{r['gid']}|{r['status']}|{ids}|{r['align_key']}", model=model,
                   system=SYSTEM, user=user,
                   max_output_tokens=MAX_TOKENS_PER_LANGUAGE * len(languages) + MAX_TOKENS_OVERHEAD)


def mark_repeated_furniture(conn: psycopg.Connection, min_documents: int = 3, keep_one: bool = False) -> int:
    """Set status 'boilerplate' on chunks whose exact text recurs in `min_documents`+ live documents of one source.

    A footer, contact block or cookie notice that survived HTML cleaning is the same chunk on
    every page; finding it by repetition is free, where the model's verdict is paid per copy. Law is exempt:
    identical articles across acts ("Aufgehoben") are rare, legitimate, and carry different breadcrumbs.
    With `keep_one`, the copy in the source's lowest document id stays live and only the other copies are
    marked, so the text is still found once. Afterwards a single live copy is left, which a later run of
    either kind leaves alone until new copies arrive. Returns the number of chunks marked. The caller commits.
    """
    return conn.execute(
        "with live as (select c.id, c.language, c.chunk_hash, d.source_id, c.document_id from corpus.chunk c "
        f"join corpus.document d on d.id = c.document_id where c.status in {LIVE} "
        "and c.text <> '' and d.authority <> all(%s)), "
        "repeated as (select source_id, chunk_hash, min(document_id) as keeper from live "
        "group by source_id, chunk_hash having count(distinct document_id) >= %s) "
        "update corpus.chunk c set status = 'boilerplate' from live l join repeated r "
        "on r.source_id = l.source_id and r.chunk_hash = l.chunk_hash "
        "where c.id = l.id and c.language = l.language and not (%s and l.document_id = r.keeper)",
        (list(LAW_AUTHORITIES), min_documents, keep_one)).rowcount


def estimate_describe(tasks: Sequence[LlmTask], model: str, batch: bool = True) -> float:
    """Expected cost; the language count of each task is read from its custom id."""
    input_tokens = sum(estimate_tokens(t.system + t.user) for t in tasks)
    output_tokens = sum(ESTIMATE_TOKENS_PER_LANGUAGE * len(_task_languages(t.custom_id)) + ESTIMATE_TOKENS_OVERHEAD
                        for t in tasks)
    return cost_usd(model, input_tokens, output_tokens, batch=batch)


# --- ingesting outcomes -----------------------------------------------------------------------------

def _spend(conn: psycopg.Connection, model: str, outcome: LlmOutcome, batch: bool) -> None:
    """A direct call is priced at the sync rate even in a batch run (HybridRunner)."""
    if outcome.input_tokens or outcome.output_tokens:
        record_spend(conn, kind=LEDGER_KIND, model=model,
                     usd=cost_usd(model, outcome.input_tokens, outcome.output_tokens,
                                  batch=batch and not outcome.sync),
                     input_tokens=outcome.input_tokens, output_tokens=outcome.output_tokens, estimated=False)


def _reply(outcome: LlmOutcome) -> dict:
    if not isinstance(outcome.data, dict):
        raise ValueError(outcome.error or "no reply")  # noqa: TRY004 - callers quarantine on ValueError
    return outcome.data


def _clear_quarantine(conn: psycopg.Connection, key: str, stage: str) -> None:
    conn.execute("delete from corpus.quarantine where source_id = %s and url = %s and stage = %s",
                 (QUARANTINE_SOURCE, key, stage))


def _group_described(conn: psycopg.Connection, gid: str) -> bool:
    row = conn.execute("select description_by_lang <> '{}'::jsonb as done from corpus.translation_group "
                       "where id = %s", (gid,)).fetchone()
    return bool(row and row["done"])


def run_doc_descriptions(database_url: str, runner, tasks: Sequence[LlmTask], model: str, batch: bool,
                         estimated_usd: float = 0.0) -> dict[str, int]:
    report = {"done": 0, "failed": 0, "skipped": 0}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="describe-doc", estimated_usd=estimated_usd):
            _, gid, langs = outcome.custom_id.split("|")
            if _group_described(conn, gid):
                report["skipped"] += 1
                continue
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


def _chunks_described(conn: psycopg.Connection, ids: dict[str, int]) -> bool:
    """True when every target chunk already has a description (a replayed outcome)."""
    rows = conn.execute("select description from corpus.chunk where (id, language) in "
                        "(select * from unnest(%s::bigint[], %s::text[]))",
                        (list(ids.values()), list(ids))).fetchall()
    return bool(rows) and all(r["description"] for r in rows)


def _prior(conn: psycopg.Connection, ids: dict[str, int]) -> list[str]:
    lang = min(ids)
    row = conn.execute("select topics from corpus.chunk where id = %s and language = %s",
                       (ids[lang], lang)).fetchone()
    return list(row["topics"]) if row else []


def _write_chunks(conn: psycopg.Connection, status: str, ids: dict[str, int], descriptions: dict[str, str],
                  topics: list[str], boilerplate: bool) -> None:
    """The `status` filter is the status seen when the task was built: a chunk that meanwhile became
    boilerplate (mark_repeated_furniture) or superseded is left alone."""
    for lang, text in descriptions.items():
        conn.execute(
            "update corpus.chunk set description = %s, topics = %s, "
            "status = case when %s then 'boilerplate' else status end "
            "where id = %s and language = %s and status = %s",
            (text, topics, boilerplate, ids[lang], lang, status))


def run_chunk_descriptions(database_url: str, runner, tasks: Sequence[LlmTask], model: str, batch: bool,
                           estimated_usd: float = 0.0) -> dict[str, int]:
    report = {"done": 0, "failed": 0, "skipped": 0}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="describe-chunk", estimated_usd=estimated_usd):
            _, gid, status, id_field, align_key = outcome.custom_id.split("|", 4)
            ids = _chunk_ids(id_field)
            if _chunks_described(conn, ids):
                report["skipped"] += 1
                continue
            key = f"chunk:{gid}:{align_key}"
            _spend(conn, model, outcome, batch)
            try:
                descriptions, topics, boilerplate = parse_chunk_reply(_reply(outcome), tuple(ids), _prior(conn, ids))
            except ValueError as exc:
                quarantine(conn, QUARANTINE_SOURCE, key, "describe-chunk", str(exc))
                report["failed"] += 1
            else:
                _write_chunks(conn, status, ids, descriptions, topics, boilerplate)
                _clear_quarantine(conn, key, "describe-chunk")
                report["done"] += 1
            conn.commit()
    return report
