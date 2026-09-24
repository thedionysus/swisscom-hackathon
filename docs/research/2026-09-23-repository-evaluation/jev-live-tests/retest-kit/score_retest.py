"""Score the re-test against two blind labellers' gold, by the rules fixed in prereg_retest.json.

Each `--responses name=path` is one Jev design (for example structured=responses_structured.jsonl and
plain=responses_plain.jsonl). For every design:
  <name>        primary rule: {choice} unless none_of_these
  <name>-floor  secondary: only when the choice's confidence >= 0.6
  <name>-tie    descriptive: every topic with probability >= 0.5 x the top topic (multi-label variant)
  AUC           over (chunk, topic) pairs, from the topic's choice probability: ranking quality, reported
                beside the decision metrics because calibration or ranking alone can mislead (Winnow)
B is the baseline, if baseline.json is given: production corpus.chunk.topics; boilerplate status means no topics.
Gold, per (chunk, topic): positive if both labellers list it as primary; negative if neither lists it as primary
or acceptable; otherwise excluded. Junk counts only where both labellers agree.
"""
import argparse, json, math, pathlib

NONE_ID = "none_of_these"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - r) / d, (c + r) / d


def kappa(x: list[bool], y: list[bool]) -> float:
    n = len(x); po = sum(a == b for a, b in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n; pe = px * py + (1 - px) * (1 - py)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def sign_test(better: int, worse: int) -> float:
    n = better + worse
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(better, worse) + 1)) / 2 ** n) if n else 1.0


def load_responses(path: str) -> dict:
    out = {}
    for line in pathlib.Path(path).read_text().splitlines():
        r = json.loads(line)
        if r["status"] == 200:
            out[r["id"]] = (r["response"].get("answers") or {}).get("topic") or {}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chunks", required=True); ap.add_argument("--labels-a", required=True)
    ap.add_argument("--labels-b", required=True)
    ap.add_argument("--responses", required=True, action="append", help="name=path, repeatable; a bare path is named J")
    ap.add_argument("--baseline", help="baseline.json from prepare.py: {id: {topics: [...], boilerplate: bool}}")
    ap.add_argument("--topic-ids", help="JSON list of topic ids, or a topics.json of {id, label, covers}; default: swiss_grounding.corpus.topics.TOPICS")
    ap.add_argument("--prereg", help="prereg_retest.json, for the decision thresholds and the primary design")
    ap.add_argument("--out", default="summary.md")
    a = ap.parse_args()
    if a.topic_ids:  # a list of ids, or the same topics.json run_retest.py takes (a list of {id, label, covers})
        cats = [t["id"] if isinstance(t, dict) else t for t in json.loads(pathlib.Path(a.topic_ids).read_text())]
    else:
        from swiss_grounding.corpus.topics import TOPICS
        cats = [t.id for t in TOPICS]
    chunks = {c["id"]: c for c in json.loads(pathlib.Path(a.chunks).read_text())}
    A = json.loads(pathlib.Path(a.labels_a).read_text()); B = json.loads(pathlib.Path(a.labels_b).read_text())
    ids = [i for i in chunks if i in A and i in B]
    designs = {}
    for spec in a.responses:
        name, _, path = spec.partition("=") if "=" in spec else ("J", "", spec)
        designs[name] = load_responses(path)
    base = json.loads(pathlib.Path(a.baseline).read_text()) if a.baseline else None

    out = []; p = out.append
    p(f"# Re-test: Jev topic question on a fresh sample\n\nChunks {len(chunks)}; labelled by both {len(ids)}; "
      + "; ".join(f"{n} answers {sum(i in d for i in ids)}" for n, d in designs.items()) + f"; baseline {'yes' if base else 'no'}\n")
    ja = [bool(A[i]["junk"]) for i in ids]; jb = [bool(B[i]["junk"]) for i in ids]
    p(f"- Labeller agreement: junk κ = {kappa(ja, jb):.2f}; primary topics κ = "
      f"{kappa([c in A[i]['primary'] for i in ids for c in cats], [c in B[i]['primary'] for i in ids for c in cats]):.2f}")
    gold = {}
    for i in ids:
        for c in cats:
            ap_, bp = c in A[i]["primary"], c in B[i]["primary"]
            aa, ba = ap_ or c in A[i].get("acceptable", []), bp or c in B[i].get("acceptable", [])
            gold[(i, c)] = True if (ap_ and bp) else (False if not (aa or ba) else None)
    junk = {i: bool(A[i]["junk"]) for i in ids if bool(A[i]["junk"]) == bool(B[i]["junk"])}
    npos = {i: sum(gold[(i, c)] is True for c in cats) for i in ids}
    p(f"- Gold: {sum(v is True for v in gold.values())} positive pairs, {sum(v is False for v in gold.values())} negative, "
      f"{sum(v is None for v in gold.values())} excluded; chunks with >= 2 gold topics: {sum(n >= 2 for n in npos.values())}; "
      f"agreed junk {sum(junk.values())} of {len(junk)}\n")

    # score only chunks every design answered, so designs are compared on the same chunks
    scored = [i for i in ids if all(i in d and d[i].get("choice") for d in designs.values())]
    preds = {}
    for name, d in designs.items():
        preds[name], preds[f"{name}-floor"], preds[f"{name}-tie"] = {}, {}, {}
        for i in scored:
            ch, conf, pr = d[i]["choice"], d[i].get("confidence") or 0, d[i].get("probabilities") or {}
            preds[name][i] = set() if ch == NONE_ID else {ch}
            preds[f"{name}-floor"][i] = set() if ch == NONE_ID or conf < 0.6 else {ch}
            top = max((pr.get(c, 0) for c in cats), default=0)
            preds[f"{name}-tie"][i] = set() if ch == NONE_ID else {c for c in cats if top and pr.get(c, 0) >= 0.5 * top}
    if base:
        preds["B"] = {i: set() if base[i]["boilerplate"] else set(base[i]["topics"]) for i in scored if i in base}

    def tally(pred: dict, sub: list[str]) -> tuple[int, int, int]:
        tp = fp = fn = 0
        for i in sub:
            if i not in pred:
                continue
            for c in cats:
                g = gold[(i, c)]
                if g is None:
                    continue
                tp += c in pred[i] and g; fp += c in pred[i] and not g; fn += c not in pred[i] and g
        return tp, fp, fn

    subsets = {"all": scored, "agreed content": [i for i in scored if junk.get(i) is False],
               "agreed junk": [i for i in scored if junk.get(i) is True], ">= 2 gold topics": [i for i in scored if npos[i] >= 2]}
    for lang in sorted({chunks[i]["language"] for i in scored}):
        subsets[f"language {lang}"] = [i for i in scored if chunks[i]["language"] == lang]
    p(f"Scored chunks (answered by every design): {len(scored)}\n")
    p("| prediction | subset | TP | FP | FN | precision (95% CI) | recall (95% CI) |"); p("|---|---|---|---|---|---|---|")
    results = {}
    for name, pred in preds.items():
        for sn, sub in subsets.items():
            tp, fp, fn = tally(pred, sub)
            pl, ph = wilson(tp, tp + fp); rl, rh = wilson(tp, tp + fn)
            prec = f"{tp/(tp+fp):.2f} ({pl:.2f}–{ph:.2f})" if tp + fp else "—"
            rec = f"{tp/(tp+fn):.2f} ({rl:.2f}–{rh:.2f})" if tp + fn else "—"
            p(f"| {name} | {sn} (n={len(sub)}) | {tp} | {fp} | {fn} | {prec} | {rec} |")
            results[(name, sn)] = (tp, fp, fn)

    p("")
    for name, d in designs.items():
        jn = subsets["agreed junk"]
        pos = [d[i]["probabilities"].get(c, 0) for i in scored for c in cats if gold[(i, c)] is True]
        neg = [d[i]["probabilities"].get(c, 0) for i in scored for c in cats if gold[(i, c)] is False]
        auc = sum((x > y) + 0.5 * (x == y) for x in pos for y in neg) / (len(pos) * len(neg)) if pos and neg else float("nan")
        p(f"- {name}: none_of_these on agreed junk {sum(not preds[name][i] for i in jn)}/{len(jn)}; AUC {auc:.3f} "
          f"({len(pos)} positive, {len(neg)} negative pairs)")

    def errs(pred: set, i: str) -> int:
        return sum((c in pred) != gold[(i, c)] for c in cats if gold[(i, c)] is not None)

    def paired(x: str, y: str) -> str:
        both = [i for i in scored if i in preds[x] and i in preds[y]]
        better = sum(errs(preds[x][i], i) < errs(preds[y][i], i) for i in both)
        worse = sum(errs(preds[x][i], i) > errs(preds[y][i], i) for i in both)
        return (f"{x} vs {y} per chunk: fewer errors {better}, more {worse}, equal {len(both) - better - worse}; "
                f"sign test p = {sign_test(better, worse):.4f}")

    names = list(designs)
    if len(names) >= 2:
        p("- " + paired(names[0], names[1]))
    if base:
        for name in names:
            p("- " + paired(name, "B"))
            dis = [i for i in scored if i in preds["B"] and preds[name][i] != preds["B"][i]]
            sj = sum(errs(preds[name][i], i) < errs(preds["B"][i], i) for i in dis)
            sb = sum(errs(preds[name][i], i) > errs(preds["B"][i], i) for i in dis)
            p(f"  - disagreements with B: {len(dis)} chunks; gold sides with {name} in {sj}, with B in {sb}, neither/tied {len(dis) - sj - sb}")

    if a.prereg:
        d = json.loads(pathlib.Path(a.prereg).read_text())["decision"]
        primary = d.get("primary_design", names[0])
        tp, fp, fn = results[(primary, "all")]
        prec, rec = (tp / (tp + fp) if tp + fp else 0), (tp / (tp + fn) if tp + fn else 0)
        low = wilson(tp, tp + fp)[0] if tp + fp else 0
        r = d["replicates"]
        ok = prec >= r["precision_min"] and rec >= r["recall_min"] and low >= r["precision_ci_low_min"]
        p(f"\n**Decision (prereg), primary design `{primary}`:** replicates = {ok} "
          f"(precision {prec:.2f}, recall {rec:.2f}, precision CI low {low:.2f})")
    text = "\n".join(out)
    pathlib.Path(a.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
