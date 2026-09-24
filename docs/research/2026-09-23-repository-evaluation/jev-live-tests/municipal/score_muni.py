"""Score muni/results/results.json against the two-labeller gold, exactly as fixed in muni/prereg.json."""
import json, math, random, pathlib
HERE = pathlib.Path(__file__).parent
chunks = {c["id"]: c for c in json.loads((HERE / "chunks.json").read_text())}
A = json.loads((HERE / "labels_A.json").read_text()); B = json.loads((HERE / "labels_B.json").read_text())
res = json.loads((HERE / "results" / "results.json").read_text())
CATS = ["hiking", "waste", "dogs", "taxes", "housing", "transport", "parking", "schools", "health", "safety"]
out = []; p = out.append

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"), float("nan"))
    ph = k / n; d = 1 + z * z / n; c = ph + z * z / (2 * n); r = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)
def kappa(x, y):
    n = len(x); po = sum(a == b for a, b in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n; pe = px * py + (1 - px) * (1 - py)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")
def fmt(k, n):
    lo, hi = wilson(k, n); return f"{k}/{n} = {k/n:.2f} (95% CI {lo:.2f}–{hi:.2f})" if n else "n/a"

missing = [i for i in chunks if i not in A or i not in B]
p(f"# Municipal / cantonal Jev test\n\nLabel files complete: {not missing} (missing: {missing[:5]})\n")
ids = [i for i in chunks if i in A and i in B]

# ---- agreement ----
p("## Labeller agreement\n")
p(f"- Junk flag: Cohen's κ = {kappa([bool(A[i]['junk']) for i in ids], [bool(B[i]['junk']) for i in ids]):.2f}; "
  f"agree on {sum(bool(A[i]['junk']) == bool(B[i]['junk']) for i in ids)}/{len(ids)} chunks")
xa = [c in A[i]["primary"] for i in ids for c in CATS]; xb = [c in B[i]["primary"] for i in ids for c in CATS]
p(f"- Primary topics per (chunk, category): Cohen's κ = {kappa(xa, xb):.2f} over {len(xa)} pairs")

# ---- gold ----
gold = {}
for i in ids:
    for c in CATS:
        a_p, b_p = c in A[i]["primary"], c in B[i]["primary"]
        a_any, b_any = a_p or c in A[i].get("acceptable", []), b_p or c in B[i].get("acceptable", [])
        gold[(i, c)] = True if (a_p and b_p) else (False if not (a_any or b_any) else None)
jgold = {i: bool(A[i]["junk"]) for i in ids if bool(A[i]["junk"]) == bool(B[i]["junk"])}
pos_per_chunk = {i: [c for c in CATS if gold[(i, c)] is True] for i in ids}
p(f"- Gold topic pairs: {sum(v is True for v in gold.values())} positive, {sum(v is False for v in gold.values())} negative, "
  f"{sum(v is None for v in gold.values())} ambiguous (excluded)")
p(f"- Chunks with ≥ 2 gold topics: {sum(len(v) >= 2 for v in pos_per_chunk.values())}; with exactly 1: {sum(len(v) == 1 for v in pos_per_chunk.values())}; "
  f"with none: {sum(len(v) == 0 for v in pos_per_chunk.values())}; gold junk: {sum(jgold.values())} of {len(jgold)} agreed\n")

# ---- M1 topics ----
probs = {i: res["m12"][i] for i in ids if res["m12"].get(i) and all(res["m12"][i].get(c) is not None for c in CATS)}
def rule(name, pr):
    top = max(CATS, key=lambda c: pr[c]); t = pr[top]
    if name == "R1": return {top} if t >= 0.10 else set()
    if name == "R2": return {c for c in CATS if pr[c] >= 0.5 * t} if t >= 0.10 else set()
    return {c for c in CATS if pr[c] >= float(name)}
def evaluate(name, subset):
    tp = fp = fn = tn = 0
    for i in subset:
        P = rule(name, probs[i])
        for c in CATS:
            g = gold[(i, c)]
            if g is None: continue
            if c in P and g: tp += 1
            elif c in P and not g: fp += 1
            elif g: fn += 1
            else: tn += 1
    return tp, fp, fn, tn
p("## M1: topics (original-language text; rules fixed in advance)\n")
p(f"Chunks answered: {len(probs)}/{len(ids)}\n")
subsets = {"all": list(probs), "random": [i for i in probs if not chunks[i]["targeted"]], "targeted": [i for i in probs if chunks[i]["targeted"]],
           "German": [i for i in probs if chunks[i]["language"] == "de"], "French": [i for i in probs if chunks[i]["language"] == "fr"],
           "≥2 gold topics": [i for i in probs if len(pos_per_chunk[i]) >= 2]}
p("| subset | rule | TP | FP | FN | precision | recall |"); p("|---|---|---|---|---|---|---|")
for sname, sub in subsets.items():
    for r in ("R1", "R2", "0.3", "0.5"):
        tp, fp, fn, tn = evaluate(r, sub)
        pr = f"{tp/(tp+fp):.2f}" if tp + fp else "—"; rc = f"{tp/(tp+fn):.2f}" if tp + fn else "—"
        p(f"| {sname} (n={len(sub)}) | {r} | {tp} | {fp} | {fn} | {pr} | {rc} |")
tops = [i for i in probs if pos_per_chunk[i]]
hit = sum(max(CATS, key=lambda c: probs[i][c]) in pos_per_chunk[i] for i in tops)
p(f"\nTop category is a gold topic: {fmt(hit, len(tops))}")
junk_ids = [i for i in probs if jgold.get(i) is True]
p(f"Gold-junk chunks given a topic under R1: {sum(bool(rule('R1', probs[i])) for i in junk_ids)}/{len(junk_ids)}")

# ---- M2 junk ----
p("\n## M2: junk screening (substance < 0.3 ⇒ junk; jev-mcp wording)\n")
sub = {i: res["m12"][i].get("substance") for i in jgold if res["m12"].get(i) and res["m12"][i].get("substance") is not None}
tp = sum(sub[i] < 0.3 and jgold[i] for i in sub); fp = sum(sub[i] < 0.3 and not jgold[i] for i in sub)
fn = sum(sub[i] >= 0.3 and jgold[i] for i in sub); tn = sum(sub[i] >= 0.3 and not jgold[i] for i in sub)
p(f"Chunks with agreed junk label: {len(sub)} ({tp+fn} junk, {fp+tn} content)")
p(f"- Junk caught (recall): {fmt(tp, tp+fn)}")
p(f"- Flagged junk that is junk (precision): {fmt(tp, tp+fp)}")
p(f"- **Content wrongly flagged as junk** (the costly error): {fmt(fp, fp+tn)}")
js = sorted(sub[i] for i in sub if jgold[i]); cs = sorted(sub[i] for i in sub if not jgold[i])
if js and cs:
    auc = sum((c > j) + 0.5 * (c == j) for c in cs for j in js) / (len(cs) * len(js))
    p(f"- Substance score separates content from junk: AUC {auc:.2f}; junk median {js[len(js)//2]:.2f}, content median {cs[len(cs)//2]:.2f}")

# ---- M3 dates ----
p("\n## M3: in-force date of Basel-Stadt laws (gold = portal API `enactment`)\n")
m3 = [r for r in res["m3"].values() if "correct" in r]
p(f"Correct: {fmt(sum(r['correct'] for r in m3), len(m3))}; gold among candidates in {sum(r['gold_in_candidates'] for r in res['m3'].values())}/{len(res['m3'])}\n")
p("| SR | gold | Jev picked | confidence | correct | #candidates |"); p("|---|---|---|---|---|---|")
for sn, r in res["m3"].items():
    p(f"| {sn} | {r['gold']} | {r.get('picked')} | {(r.get('answer') or {}).get('confidence')} | {r.get('correct')} | {len(r['candidates'])} |")

# ---- ops ----
p(f"\n## Operations\n\n{json.dumps(res.get('meta'))}\n")

# ---- human spot-check ----
p("## Human spot-check (10 chunks, seed 424242, fixed in advance)\n")
for i in random.Random(424242).sample(ids, 10):
    pr = res["m12"].get(i) or {}
    jv = ", ".join(f"{c} {pr[c]:.2f}" for c in sorted(CATS, key=lambda c: -(pr.get(c) or 0)) if (pr.get(c) or 0) >= 0.10) or "—"
    c = chunks[i]
    p(f"**{i}** ({c['language']}, {c['url']})\n> {c['heading_path'][:80]} — {c['text'][:260].replace(chr(10), ' ')}\n\n"
      f"- Labeller A: {A[i]['primary'] or '—'} (acceptable {A[i].get('acceptable') or '—'}), junk {A[i]['junk']}\n"
      f"- Labeller B: {B[i]['primary'] or '—'} (acceptable {B[i].get('acceptable') or '—'}), junk {B[i]['junk']}\n"
      f"- Jev: {jv}; substance {pr.get('substance')}\n")
text = "\n".join(out); (HERE / "results" / "summary.md").write_text(text); print(text)
