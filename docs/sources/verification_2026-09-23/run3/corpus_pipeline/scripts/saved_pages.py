"""Offline index of the Run 3 agents' saved raw pages: URL -> local file (no network)."""
import hashlib, os, re, glob, json
S = "<scratchpad>"
R3 = S + "/newpipe/run3_copy/docs/sources/verification_2026-09-23/run3"  # git archive of c93ae3f; wt-run3 was removed mid-session

def md5(u): return hashlib.md5(u.encode()).hexdigest()

def candidates(u):
    h = md5(u)
    return [
        f"{S}/run3-a/pages/" + re.sub(r"[^A-Za-z0-9]+", "_", u.split("//", 1)[-1])[:90] + "_" + h[:10],
        f"{S}/run3-b/pages/" + h[:12],
        f"{S}/run3-c/pages/" + re.sub(r"[^A-Za-z0-9]+", "_", u.split("://", 1)[-1])[:90] + "_" + h[:6],
        f"{S}/run3-d/pages/" + re.sub(r"[^A-Za-z0-9]+", "_", u)[:110] + "_" + h[:6],
        f"{S}/run3-e/p_" + h[:10],
    ]

def variants(u):
    out = [u]
    out.append(u[:-1] if u.endswith("/") else u + "/")
    if u.startswith("https://"): out.append("http://" + u[8:])
    return out

def find(u):
    for v in variants(u):
        for c in candidates(v):
            if os.path.isfile(c):
                return v, c
    return None

URL_RE = re.compile(r"https?://[^\s\"'`<>)\]|,]+")

def all_urls():
    texts = []
    for p in glob.glob(R3 + "/**/*", recursive=True):
        if os.path.isfile(p) and p.endswith((".md", ".yaml", ".csv", ".txt", ".json", ".py")) and os.path.getsize(p) < 5_000_000:
            texts.append(open(p, encoding="utf-8", errors="replace").read())
    for p in glob.glob(S + "/run3-*/*"):
        if os.path.isfile(p) and p.endswith((".txt", ".py", ".json", ".jsonl", ".out")) and os.path.getsize(p) < 5_000_000:
            texts.append(open(p, encoding="utf-8", errors="replace").read())
    urls = set()
    for t in texts:
        for m in URL_RE.findall(t):
            urls.add(m.rstrip(".;:"))
    return urls

if __name__ == "__main__":
    idx = {}
    for u in sorted(all_urls()):
        hit = find(u)
        if hit:
            idx[hit[0]] = hit[1]
    json.dump(idx, open(S + "/newpipe/saved_index.json", "w"), indent=0)
    print(len(idx), "URLs mapped to saved files")
    from collections import Counter
    print(Counter(re.sub(r"^https?://([^/]+).*", r"\1", u) for u in idx).most_common(80))
