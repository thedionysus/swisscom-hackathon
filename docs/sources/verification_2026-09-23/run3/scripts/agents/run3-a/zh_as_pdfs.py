#!/usr/bin/env python3
"""Extract the Rechtstexte PDF link and dates from Stadt Zürich AS detail pages (stzh-datatable rows JSON)."""
import html
import json
import re
import subprocess
import sys
import time
from urllib.parse import quote

UA = "Mozilla/5.0 swiss-grounding-check"
BASE = "https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung/"
for rel in sys.argv[1:]:
    url = BASE + rel
    r = subprocess.run(["curl", "-sL", "--compressed", "-m", "40", "-A", UA, url], capture_output=True, text=True)
    time.sleep(0.5)
    raw = r.stdout
    m = re.search(r'<stzh-datatable[^>]*rows="([^"]+)"', raw)
    if not m:
        print(rel, "| no datatable")
        continue
    rows = json.loads(html.unescape(m.group(1)))
    vals = {c["id"]: c["value"] for row in rows for c in row if not c.get("isHeader")}
    pdf = re.search(r'href="([^"]+\.pdf)"', vals.get("rechtstexte", ""))
    title = re.sub(r"<[^>]+>|\r", " ", vals.get("title", ""))
    title = re.sub(r"\s+", " ", title).strip()
    pdf_url = "https://www.stadt-zuerich.ch" + quote(pdf.group(1)) if pdf else None
    print(f"{vals.get('ASZ')} | {title[:90]} | Beschluss {vals.get('erlassdatum')} | in Kraft {vals.get('inkrafttretendatum')} | {pdf_url}")
