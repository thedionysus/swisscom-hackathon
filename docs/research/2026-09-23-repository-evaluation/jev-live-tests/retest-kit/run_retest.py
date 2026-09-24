"""Ask Jev the E3 topic question for every chunk of a fresh labelled sample (see prereg_retest.json).

Input: chunks.json, a list of {"id", "language", "page_title", "heading", "text"} (prepare.py writes it).
Output: responses.jsonl, one {"id", "status", "response"} line per call. Re-running skips chunks already
answered with HTTP 200 and retries the rest.

Calls Vercel AI Gateway's TypeSafe-compatible route one at a time, 1 s apart, and honours retry-after on
429 and 5xx. (Eight parallel requests with a fixed 1-2-4 s backoff lost half the items in our test.)
The key comes from AI_GATEWAY_API_KEY in the environment and is never printed.
"""
import argparse, json, os, pathlib, sys, time

URL = "https://ai-gateway.vercel.sh/typesafe/v1/systemone"
MODEL = "typesafe-ai/jev"
NONE_ID = "none_of_these"
TEXT_CHARS = 2500          # what the describe stage shows the paid model (corpus/describe.py:29)
INSTRUCTIONS = ("Which of the listed topics does the passage's own content in `passage` concern? "
                "Pick the single best match.")
NONE_TEXT = "The passage's own content concerns none of these topics"
# Winnow-style structured criteria (GhalebDweikat/winnow, sidecar/src/winnow/questions.py:43-70), built by the
# same mechanical rule as E4: what = label, examples = the topic's `covers` split at commas, and one shared
# not_for that restates two labelling rules (passing mentions do not count; junk has no topic), in the
# production boilerplate wording (corpus/describe.py:60-61).
SHARED_NOT_FOR = ("A topic the passage only mentions in passing; page furniture (navigation, a cookie notice, contact "
                  "details or other page furniture with no substantive content) has no topic.")
NONE_STRUCTURED = {"what": NONE_TEXT,
                   "examples": ["page furniture: navigation, a cookie notice, contact details or other page furniture "
                                "with no substantive content", "a passage whose subject is not among the listed topics"]}


def load_topics(path: str | None) -> list[tuple[str, str, str]]:
    if path:
        return [(t["id"], t["label"], t["covers"]) for t in json.loads(pathlib.Path(path).read_text())]
    from swiss_grounding.corpus.topics import TOPICS  # the twenty topics of ADR 0007
    return [(t.id, t.label, t.covers) for t in TOPICS]


def structured_criteria(topics: list[tuple[str, str, str]]) -> dict:
    criteria = {tid: {"what": label, "examples": [x.strip() for x in covers.split(",")], "not_for": SHARED_NOT_FOR}
                for tid, label, covers in topics}
    criteria[NONE_ID] = NONE_STRUCTURED
    return criteria


def question(topics: list[tuple[str, str, str]], mode: str = "plain", criteria_file: str | None = None) -> dict:
    if criteria_file:
        criteria = json.loads(pathlib.Path(criteria_file).read_text())
        if set(criteria) != {t[0] for t in topics} | {NONE_ID}:
            sys.exit("criteria file ids differ from the topic ids plus none_of_these")
    elif mode == "structured":
        criteria = structured_criteria(topics)
    else:
        criteria = {tid: f"{label}: {covers}" for tid, label, covers in topics}
        criteria[NONE_ID] = NONE_TEXT
    # keys sorted, as the evaluate binary sent them in E3
    return {"topic": {"type": "choice", "instructions": INSTRUCTIONS, "criteria": dict(sorted(criteria.items()))}}


def body(chunk: dict, questions: dict) -> dict:
    passage = {"page_title": chunk["page_title"], "heading": chunk["heading"], "text": chunk["text"][:TEXT_CHARS]}
    return {"model": MODEL, "state": {"passage": passage}, "questions": questions}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("chunks")
    ap.add_argument("--out", default="responses.jsonl")
    ap.add_argument("--topics", help="JSON list of {id, label, covers}; default: swiss_grounding.corpus.topics.TOPICS")
    ap.add_argument("--criteria", choices=("plain", "structured"), default="plain",
                    help="plain = E3 (one line per topic); structured = E4 (what / examples / not_for)")
    ap.add_argument("--criteria-file", help="a reviewed criteria JSON {topic id: description, ..., none_of_these: ...}")
    ap.add_argument("--write-criteria", help="write the generated criteria to this JSON file for review, then exit")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true", help="print the first request body and exit; no call")
    a = ap.parse_args()
    topics = load_topics(a.topics)
    questions = question(topics, a.criteria, a.criteria_file)
    if a.write_criteria:
        pathlib.Path(a.write_criteria).write_text(json.dumps(questions["topic"]["criteria"], ensure_ascii=False, indent=1))
        print("wrote", a.write_criteria)
        return
    chunks = json.loads(pathlib.Path(a.chunks).read_text())[: a.limit]
    if a.dry_run:
        print(json.dumps(body(chunks[0], questions), ensure_ascii=False, indent=1))
        return
    import httpx
    key = os.environ.get("AI_GATEWAY_API_KEY") or sys.exit("set AI_GATEWAY_API_KEY")
    out = pathlib.Path(a.out)
    done = {r["id"] for r in map(json.loads, out.read_text().splitlines()) if r["status"] == 200} if out.exists() else set()
    http = httpx.Client(timeout=60, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for c in chunks:
        if c["id"] in done:
            continue
        for attempt in range(1, 8):
            time.sleep(1.0)
            r = http.post(URL, json=body(c, questions))
            if r.status_code not in (429, 500, 502, 503, 504):
                break
            wait = float(r.headers.get("retry-after") or min(60, 2 ** attempt))
            print(f"{c['id']}: HTTP {r.status_code}, waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
        try:
            resp = r.json()
        except ValueError:
            resp = {"raw": r.text[:300]}
        with out.open("a") as fh:
            fh.write(json.dumps({"id": c["id"], "status": r.status_code, "response": resp}, ensure_ascii=False) + "\n")
    ok = {r["id"] for r in map(json.loads, out.read_text().splitlines()) if r["status"] == 200}
    print(f"answered {len(ok & {c['id'] for c in chunks})} of {len(chunks)}")


if __name__ == "__main__":
    main()
