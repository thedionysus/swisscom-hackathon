#!/usr/bin/env python3
"""show.py <url-or-slugprefix> [--from MARKER] [--len N] [--grep REGEX] [--links REGEX]
Reads the page saved by probe.py (by URL -> slug) and prints main text / regex hits / links."""
import glob
import hashlib
import html
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "pages")


def slug(u):
    s = re.sub(r"[^A-Za-z0-9]+", "_", u)[:110]
    return s + "_" + hashlib.md5(u.encode()).hexdigest()[:6]


args = sys.argv[1:]
target = args.pop(0)
opts = {}
while args:
    k = args.pop(0)
    opts[k] = args.pop(0)
fn = os.path.join(OUT, slug(target)) if target.startswith("http") else (glob.glob(os.path.join(OUT, target + "*")) or [""])[0]
raw = open(fn, "rb").read().decode("utf-8", "replace")
if "--main" in opts:
    mm = re.search(r"<main[^>]*>(.*)</main>", raw, re.S | re.I)
    raw = mm.group(1) if mm else raw
    print("MAIN:", "found" if mm else "not found", len(raw), "chars")
body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
n = int(opts.get("--len", 900))
if "--from" in opts:
    i = text.find(opts["--from"])
    print("TEXT:", text[i:i + n] if i >= 0 else f"<marker {opts['--from']!r} not found>")
if "--grep" in opts:
    for k, m in enumerate(re.finditer(opts["--grep"], text, re.I)):
        s = max(0, m.start() - 150)
        print("HIT:", text[s:m.end() + 250])
        if k >= int(opts.get("--max", 3)) - 1:
            break
if "--links" in opts:
    seen = set()
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw, re.S | re.I):
        h = html.unescape(m.group(1))
        lab = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip())
        if re.search(opts["--links"], h + " " + lab, re.I) and (h, lab) not in seen:
            seen.add((h, lab))
            print("LINK:", h, "|", lab[:110])
