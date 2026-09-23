#!/usr/bin/env python3
"""Paginate the Ville de Geneve regulations listing (?page=N) and collect entries."""
import html
import re
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"
BASE = "https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux"
entries = {}
for n in range(0, 30):
    url = BASE + (f"?page={n}" if n else "")
    r = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    body, _, code = r.stdout.rpartition("\n")
    found = re.findall(r'href="(/administration-municipale/reglements-municipaux/lc[^"]+)"[^>]*>(.*?)</a>', body, re.S)
    new = 0
    for h, lab in found:
        lab = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", lab))).strip()
        if lab.startswith("https://"):
            continue
        if h not in entries:
            entries[h] = lab
            new += 1
    t = re.search(r"<title>(.*?)</title>", body, re.S)
    print(n, code, (t.group(1).strip()[:60] if t else ""), "links", len(found), "new", new)
    if new == 0:
        break
    time.sleep(0.5)
print("TOTAL distinct regulation pages:", len(entries))
for kw in ["chien", "déchet", "stationnement", "parcage", "circulation", "taxe", "émolument"]:
    hits = [v for v in entries.values() if kw in v.lower()]
    print(f"  {kw}: {len(hits)}", [h[:90] for h in hits[:3]])
open("vdg_entries.txt", "w").write("\n".join(f"{k}\t{v}" for k, v in entries.items()))
