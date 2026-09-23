#!/usr/bin/env python3
"""Print the full slblocks text and all hrefs of Plone pages on bl-api.webcloud7.ch.

Usage: plone_text.py [-c CHARS] PATH [...]
"""
import html
import json
import re
import subprocess
import sys
import time

BASE = "https://bl-api.webcloud7.ch"
UA = "Mozilla/5.0 swiss-grounding-check"
args = sys.argv[1:]
chars = 900
if args and args[0] == "-c":
    chars = int(args[1])
    args = args[2:]
for p in args:
    url = p if p.startswith("http") else BASE + p
    r = subprocess.run(["curl", "-g", "-sL", "-m", "45", "-A", UA, "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    time.sleep(0.5)
    try:
        d = json.loads(r.stdout)
    except Exception:
        print("NOT JSON", url, r.stdout[:120])
        continue
    htmls = []
    layout = (d.get("slblocks_layout") or {})
    order = re.findall(r'"([0-9a-f]{32})"', json.dumps(layout))
    blocks = d.get("slblocks") or {}
    keys = [k for k in order if k in blocks] + [k for k in blocks if k not in order]
    for k in keys:
        b = blocks[k]
        t = b.get("text")
        if isinstance(t, dict) and isinstance(t.get("data"), str):
            htmls.append(t["data"])
        if b.get("title") and b.get("show_title"):
            htmls.append("<h3>" + b["title"] + "</h3>")
    raw = " ".join(htmls)
    hrefs = []
    for h in re.findall(r'href="([^"]+)"', raw):
        h = html.unescape(h)
        if h not in hrefs:
            hrefs.append(h)
    txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))).strip()
    print(f"== {d.get('title')!r} | modified={d.get('modified')} | words={len(txt.split())} | {url}")
    print("   text:", txt[:chars])
    print("   hrefs:", len(hrefs))
    for h in hrefs[:25]:
        print("     ", h)
