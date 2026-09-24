"""Jev on municipal/cantonal data, per muni/prereg.json. Refuses to run until both label files exist (sealed)."""
import json, re, sys, time, pathlib, statistics
import httpx

HERE = pathlib.Path(__file__).parent
RES = HERE / "results"; RES.mkdir(exist_ok=True)
URL, MODEL = "https://ai-gateway.vercel.sh/typesafe/v1/systemone", "typesafe-ai/jev"
import hashlib
SEAL = {}
for f in ("labels_A.json", "labels_B.json", "prereg.json"):
    if not (HERE / f).exists():
        sys.exit(f"sealed: {f} missing; labels must exist before any Jev call")
    SEAL[f] = hashlib.sha256((HERE / f).read_bytes()).hexdigest()
(RES / "seal.json").write_text(json.dumps({"sealed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "sha256": SEAL}, indent=1))

CATEGORIES = [  # verbatim from src/swiss_grounding/registry/categories.py:12-21, same wording as the federal test T1
    ("hiking", "Hiking and outdoor recreation", "Trails, safety, nature protection, alpine rules"),
    ("waste", "Waste and recycling", "Collection schedules, fees, disposal rules"),
    ("dogs", "Dogs and pets", "Dog tax, leash rules, registration, training requirements"),
    ("taxes", "Taxes", "Income, wealth and municipal taxes, filing"),
    ("housing", "Housing and building", "Renting, building permits, zoning"),
    ("transport", "Transport and mobility", "Public transport, road traffic rules, cycling"),
    ("parking", "Parking", "Blue zones, permits, fees"),
    ("schools", "Schools and education", "Compulsory school, holidays, enrolment"),
    ("health", "Health", "Insurance, hospitals, emergencies"),
    ("safety", "Public safety and police", "Police, emergencies, public order"),
]
def noul(i, t, f): return {"type": "noul", "instructions": i, "criteria": {"true": t, "false": f}}
def choice(i, c): return {"type": "choice", "instructions": i, "criteria": c}
QUESTIONS = {cid: noul(f"The passage is about {label} ({desc}): a person asking a question on this topic would want this passage as evidence.",
                       "The passage's own content concerns this topic",
                       "The passage does not concern this topic, or mentions it only in passing") for cid, label, desc in CATEGORIES}
QUESTIONS["substance"] = noul("The text contains substantive readable content",  # jev-mcp src/index.ts:285-288
                              "Meaningful prose, data, or documentation — not an empty page, error message, or pure boilerplate",
                              "Empty, truncated to nothing, an error page, or only navigation/boilerplate")

MONTHS = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12}
DATE_RE = re.compile(r"\b(\d{1,2})\.\s?(Januar|Jan\.?|Februar|Feb\.?|März|Mär\.?|April|Apr\.?|Mai|Juni|Jun\.?|Juli|Jul\.?|August|Aug\.?|"
                     r"September|Sept\.?|Sep\.?|Oktober|Okt\.?|November|Nov\.?|Dezember|Dez\.?)\s?(\d{4})\b|\b(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})\b")
def iso(m):
    if m.group(1): return f"{int(m.group(3)):04d}-{MONTHS[m.group(2).lower().rstrip('.')[:3]]:02d}-{int(m.group(1)):02d}"
    return f"{int(m.group(6)):04d}-{int(m.group(5)):02d}-{int(m.group(4)):02d}"

def key():
    for line in (HERE.parent / ".env").read_text().splitlines():
        if line.startswith("AI_GATEWAY_API_KEY=") and line.split("=", 1)[1].strip():
            return line.split("=", 1)[1].strip()
    sys.exit("no key")

http = httpx.Client(timeout=60, headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"})
cache = {}
for f in RES.glob("raw_*.jsonl"):
    for l in f.read_text().splitlines():
        r = json.loads(l)
        if r["status"] == 200: cache[(r["test"], r["id"])] = r["response"]
attempts = []
def ask(test, item, state, questions):
    if (test, item) in cache: return cache[(test, item)]
    for a in range(1, 8):
        time.sleep(1.0)
        t0 = time.perf_counter(); r = http.post(URL, json={"model": MODEL, "state": state, "questions": questions})
        rec = {"test": test, "id": item, "status": r.status_code, "ms": round((time.perf_counter() - t0) * 1000), "attempt": a}
        try: rec["response"] = r.json()
        except ValueError: rec["response"] = {"raw_text": r.text[:300]}
        attempts.append(rec)
        with (RES / f"raw_{test}.jsonl").open("a") as fh: fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if r.status_code in (401, 403): sys.exit(f"auth {r.status_code}")
        if r.status_code not in (429, 500, 502, 503, 504): break
        wait = float(r.headers.get("retry-after") or min(60, 2 ** a)); print(f"{test} {item}: {r.status_code}, wait {wait:.0f}s", flush=True); time.sleep(wait)
    return rec["response"] if r.status_code == 200 else None

out = {"m12": {}, "m3": {}}
for c in json.loads((HERE / "chunks.json").read_text()):
    d = ask("m12", c["id"], {"passage": {"page_title": c["page_title"], "heading": c["heading_path"], "text": c["text"]}}, QUESTIONS)
    ans = (d or {}).get("answers", {})
    out["m12"][c["id"]] = {k: (ans.get(k) or {}).get("noul") for k in QUESTIONS}
desc = json.loads((HERE / "prereg.json").read_text())["decision_rules_fixed_in_advance"]["date_field_description"]
for law in json.loads((HERE / "bs_laws.json").read_text()):
    doc = law["document"]; cands, seen = [], set()
    for m in DATE_RE.finditer(doc):
        if m.group(0) not in seen: seen.add(m.group(0)); cands.append((m.group(0), iso(m)))
    cands = cands[:20]
    rec = {"title": law["title"], "gold": law["gold"], "candidates": [c for c, _ in cands], "gold_in_candidates": any(i == law["gold"] for _, i in cands)}
    if cands:
        crit = {f"c{j}": f"Candidate value: {json.dumps(c, ensure_ascii=False)}" for j, (c, _) in enumerate(cands)}
        crit["none_of_them"] = "None of the candidates is the value this field asks for"
        q = {"entry_into_force": choice(f'Which candidate is the correct value of the field "entry_into_force" ({desc}) in the document in the state? '
                                        "Pick the exact substring the document presents as this field's value.", crit)}
        d = ask("m3", law["sn"], {"purpose": "Find when this enactment took effect", "document": doc,
                                  "fields": [{"id": "entry_into_force", "description": desc}]}, q)
        a = ((d or {}).get("answers") or {}).get("entry_into_force") or {}
        pick = a.get("choice"); idx = int(pick[1:]) if isinstance(pick, str) and pick[1:].isdigit() else None
        rec.update(answer=a, picked=cands[idx][0] if idx is not None else pick, picked_iso=cands[idx][1] if idx is not None else None)
        rec["correct"] = (rec["picked_iso"] == law["gold"]) if rec["gold_in_candidates"] else (pick == "none_of_them")
    out["m3"][law["sn"]] = rec
ok = [a for a in attempts if a["status"] == 200]
out["meta"] = {"http_attempts": len(attempts), "status_counts": {str(s): sum(a["status"] == s for a in attempts) for s in sorted({a["status"] for a in attempts})},
               "latency_ms_median": statistics.median([a["ms"] for a in ok]) if ok else None,
               "tokens_in": sum(a["response"].get("usage", {}).get("input_tokens", 0) for a in ok),
               "cost_reported": sorted({str(a["response"].get("provider_metadata", {}).get("gateway", {}).get("cost")) for a in ok})}
(RES / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out["meta"]))
