#!/usr/bin/env python3
"""Fetch every Stadt Zürich Amtliche Sammlung group page and count Erlass entries.

Reads zh_as_groups.txt (one group URL per line). For each page: status, title, PDF links, links to
deeper AS pages, and titles matching dog/waste/parking terms.
"""
import html
import os
import re
import subprocess
import time
from urllib.parse import urljoin

BASE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 swiss-grounding-check"
groups = [l.strip() for l in open(os.path.join(BASE, "zh_as_groups.txt")) if l.strip()]
pat = re.compile(r"hund|abfall|entsorg|kehricht|park|blaue zone|gebühr", re.I)
all_pdfs = set()
all_detail = set()
hits = []
os.makedirs(os.path.join(BASE, "zh_as"), exist_ok=True)
for g in groups:
    url = urljoin("https://www.stadt-zuerich.ch/", g)
    out = os.path.join(BASE, "zh_as", re.sub(r"[^0-9A-Za-z]+", "_", g.split("amtliche-sammlung/")[-1]))
    r = subprocess.run(["curl", "-sL", "--compressed", "-m", "40", "-A", UA, "-o", out, "-w", "%{http_code}", url],
                       capture_output=True, text=True)
    time.sleep(0.5)
    raw = open(out, encoding="utf-8", errors="replace").read() if os.path.exists(out) else ""
    title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S)
    title = html.unescape(re.sub(r"\s+", " ", title.group(1)).strip()) if title else ""
    pdfs = set(urljoin(url, html.unescape(h)) for h in re.findall(r'href="([^"]+\.pdf[^"]*)"', raw, re.I))
    detail = set(urljoin(url, h) for h in re.findall(r'href="([^"]*amtliche-sammlung/\d+/\d+/[^"]+\.html)"', raw))
    all_pdfs |= pdfs
    all_detail |= detail
    # entry titles: anchor texts
    for m in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", raw, re.S):
        t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        if pat.search(t) and len(t) < 200:
            hits.append((g.split("amtliche-sammlung/")[-1], t, urljoin(url, html.unescape(m.group(1)))))
    print(r.stdout, g.split("amtliche-sammlung/")[-1], "|", title[:60], "| pdfs", len(pdfs), "| detail", len(detail))
print("TOTAL distinct PDFs", len(all_pdfs), "| distinct detail pages", len(all_detail))
seen = set()
for g, t, u in hits:
    if (t, u) in seen:
        continue
    seen.add((t, u))
    print("  HIT", g, "|", t[:120], "|", u)
open(os.path.join(BASE, "zh_as_detail.txt"), "w").write("\n".join(sorted(all_detail)))
open(os.path.join(BASE, "zh_as_pdfs.txt"), "w").write("\n".join(sorted(all_pdfs)))
