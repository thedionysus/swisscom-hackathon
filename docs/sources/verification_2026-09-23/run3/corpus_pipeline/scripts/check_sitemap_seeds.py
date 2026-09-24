"""Offline: how many Stage 0 / agent sitemap URLs would each candidate's sitemap seeding accept (include regex + prefixes)."""
import os, re, yaml
from urllib.parse import urlparse
S = "<scratchpad>"
SM = {}
for d in (S + "/stage0/sitemaps", S + "/run3-c/sitemaps"):
    for f in os.listdir(d):
        if f.endswith(".txt"):
            SM[f[:-4]] = open(os.path.join(d, f)).read().split()
cand = yaml.safe_load(open(S + "/newpipe/run3_manifest_candidates.yaml"))
SKIP = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".xml", ".json", ".ics", ".csv", ".docx", ".doc", ".xlsx", ".xls", ".mp4", ".mp3")
for e in cand["sources"]:
    c = e["config"]
    if not c.get("sitemap_urls"):
        continue
    host = urlparse(c["sitemap_urls"][0]).netloc
    urls = SM.get(host, [])
    pats = [re.compile(p) for p in c.get("sitemap_include", [])]
    ok = [u for u in urls if (not pats or any(p.search(u) for p in pats)) and any(u.startswith(p) for p in c["allow_prefixes"])
          and not urlparse(u).path.lower().endswith(SKIP)]
    print(f"{e['id']:26} sitemap urls on disk={len(urls):5} accepted={len(ok):5} max_pages={c['max_pages']}")
