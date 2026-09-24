"""Count Stage 0 sitemap URLs under each Run 3 html_crawl allow-prefix (offline) to size max_pages."""
import os, yaml
from urllib.parse import urljoin, urlparse
S = "<scratchpad>"
R = S + "/newpipe/run3_copy/docs/sources/verification_2026-09-23/run3/ready_sources"
SM = {}
for d in (S + "/stage0/sitemaps", S + "/run3-c/sitemaps"):
    for f in os.listdir(d):
        if f.endswith(".txt"):
            SM[f[:-4]] = open(os.path.join(d, f)).read().split()
jus = S + "/run3-e/justizgr_sitemap.txt"
SM["www.justiz-gr.ch"] = open(jus).read().split()
for f in sorted(os.listdir(R)):
    d = yaml.safe_load(open(os.path.join(R, f)))
    if d["fetch_strategy"] != "html_crawl":
        continue
    base = d["base_url"]
    host = urlparse(base).netloc
    prefixes = [urljoin(base, p) for p in d["fetch_config"]["path_allowlist"]]
    urls = SM.get(host)
    if urls is None:
        print(f"{d['id']:28} {host:32} no sitemap on disk"); continue
    n = sum(1 for u in urls if any(u.replace('http://', 'https://').startswith(p) for p in prefixes))
    print(f"{d['id']:28} {host:32} sitemap={len(urls):6} under_prefixes={n}")
