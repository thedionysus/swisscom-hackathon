#!/usr/bin/env python3
"""Batch-verify URLs. Spec file lines: cell|url|regex[|width]  ('#' = comment).
Prints: cell, status, content type, bytes, title, links, words, and the first regex match (HTML text or PDF text via pypdf)."""
import sys, re, io, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import fetch, analyse

def pdf_text(body, maxpages=6):
    try:
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(body))
        n = len(r.pages)
        txt = " ".join((r.pages[i].extract_text() or "") for i in range(min(n, maxpages)))
        return n, re.sub(r"\s+", " ", txt)
    except Exception as e:
        return -1, f"(pypdf error: {e})"

spec = sys.argv[1]
for line in open(spec, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    parts = line.split("|")
    cell, url = parts[0], parts[1]
    rest = parts[2:]
    w = 160
    if rest and rest[-1].strip().isdigit():
        w = int(rest[-1]); rest = rest[:-1]
    rx = "|".join(rest)
    code, ct, size, final, body, fn = fetch(url)
    if "pdf" in ct.lower() or body[:5] == b"%PDF-":
        n, txt = pdf_text(body)
        head = f"PDF pages={n} textchars={len(txt)}"
        title = ""
    else:
        title, links, words, txt, raw = analyse(body)
        head = f"title='{title[:90]}' links={links} words={words}"
    fin = "" if final.rstrip("/") == url.rstrip("/") else f" final={final}"
    print(f"[{cell}] {code} {ct.split(';')[0]} {size}B {url}{fin}\n      {head}")
    if rx:
        m = re.search(rx, txt, re.I)
        if m:
            s = max(0, m.start() - w // 3)
            print("      ~ " + txt[s:m.end() + w])
        else:
            print(f"      ~ (no match for /{rx}/)")
