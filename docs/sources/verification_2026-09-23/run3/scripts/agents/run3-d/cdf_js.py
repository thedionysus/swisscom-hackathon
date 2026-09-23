#!/usr/bin/env python3
"""Ladder step 4 for www.chaux-de-fonds.ch: fetch same-host JS bundles and grep for endpoints."""
import glob
import re
import subprocess

UA = "Mozilla/5.0 swiss-grounding-check"
page = open(glob.glob("pages/https_www_chaux_de_fonds_ch_rapports_et_reglements_243538")[0],
            encoding="utf-8", errors="replace").read()
srcs = re.findall(r'<script[^>]*src="([^"]+)"', page)
print("script srcs:", len(srcs))
for s in srcs:
    if s.startswith("http") and "chaux-de-fonds" not in s:
        continue
    url = s if s.startswith("http") else "https://www.chaux-de-fonds.ch" + (s if s.startswith("/") else "/" + s)
    r = subprocess.run(["curl", "-sL", "--max-time", "30", "-A", UA, "-w", "\n%{http_code} %{size_download}", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    body, _, meta = r.stdout.rpartition("\n")
    hits = sorted(set(re.findall(r"(?:url\s*:\s*['\"][^'\"]{3,120}['\"]|\.svc/[A-Za-z]+|/api/[A-Za-z0-9_/]+|getJSON\(['\"][^'\"]+|ajax\(\{[^}]{0,120})", body)))
    if hits or "content" in s.lower():
        print(meta, url)
        for h in hits[:8]:
            print("    ", h[:160])
