#!/usr/bin/env python3
"""Offline analysis of pages already saved by probe.fetch (no network).
Usage: offline.py [-c CHARS] [-l LINKREGEX] [-L N] [-g REGEX] URL..."""
import sys, os, re, html, hashlib, argparse
D = "<scratchpad>/run3-b/pages/"
ap = argparse.ArgumentParser()
ap.add_argument("-c", type=int, default=700)
ap.add_argument("-l", "--links", default=r"\.pdf|upload/assets|_doc")
ap.add_argument("-L", type=int, default=15)
ap.add_argument("-g", "--grep")
ap.add_argument("urls", nargs="+")
a = ap.parse_args()

def clean(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>", " ", s, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

for u in a.urls:
    fn = D + hashlib.md5(u.encode()).hexdigest()[:12]
    if not os.path.exists(fn):
        print(f"== {u}: not saved"); continue
    raw = open(fn, encoding="utf-8", errors="ignore").read()
    m = re.search(r"<main[^>]*>(.*?)</main>", raw, re.S | re.I)
    region = m.group(1) if m else raw
    txt = clean(region)
    print(f"== {u}\n   main={'yes' if m else 'no'} words={len(txt.split())}\n   text: {txt[:a.c]}")
    if a.grep:
        for mm in list(re.finditer(a.grep, txt, re.I))[:3]:
            print("   ~ " + txt[max(0, mm.start() - 150):mm.end() + 250])
    seen = []
    for mm in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', region, re.S | re.I):
        h, t = mm.group(1), clean(mm.group(2))
        if re.search(a.links, h + " " + t, re.I) and (h, t) not in seen:
            seen.append((h, t))
    print(f"   links /{a.links}/: {len(seen)}")
    for h, t in seen[:a.L]:
        print(f"    -> {h} [{t[:90]}]")
