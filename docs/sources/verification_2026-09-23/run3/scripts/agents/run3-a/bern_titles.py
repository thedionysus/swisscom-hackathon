#!/usr/bin/env python3
"""Fetch DOCX exports of Bern SSSB texts and print their title / date lines.

Usage: bern_titles.py NR [NR ...]   (NR like 559_51)
"""
import io
import re
import subprocess
import sys
import time
import zipfile

UA = "Mozilla/5.0 swiss-grounding-check"
for nr in sys.argv[1:]:
    url = f"https://stadtrecht.bern.ch/lex-{nr}.docx"
    r = subprocess.run(["curl", "-sL", "-m", "40", "-A", UA, url], capture_output=True)
    time.sleep(0.6)
    b = r.stdout
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    except Exception:
        print(nr, "| not a docx |", b[:60])
        continue
    paras = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)).strip()
        if t:
            paras.append(t)
    head = " | ".join(paras[:4])
    print(f"{nr} | {len(b)}B | paras={len(paras)} | {head[:230]}")
