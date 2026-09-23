#!/usr/bin/env python3
"""Fetch a LexWork text via show_as_json and grep its text for a regex.

Usage: lexwork_grep.py HOST NR REGEX [N]
"""
import html
import json
import re
import subprocess
import sys

UA = "Mozilla/5.0 swiss-grounding-check"
host, nr, pat = sys.argv[1], sys.argv[2], sys.argv[3]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 5
url = f"https://{host}/api/de/texts_of_law/{nr}/show_as_json"
r = subprocess.run(["curl", "-g", "-sL", "-m", "60", "-A", UA, "-H", "Accept: application/json", "-w", "\n%{http_code}", url],
                   capture_output=True, text=True)
body, _, code = r.stdout.rpartition("\n")
print(code, len(body), "B", url)
try:
    j = json.loads(body)
except Exception:
    print("not JSON:", body[:200])
    sys.exit()
s = json.dumps(j, ensure_ascii=False)
txt = html.unescape(re.sub(r"<[^>]+>", " ", s))
txt = re.sub(r"\\n|\\t", " ", txt)
txt = re.sub(r"\s+", " ", txt)
print("top keys:", list(j.keys())[:12] if isinstance(j, dict) else type(j))
k = 0
for m in re.finditer(pat, txt, re.I):
    print("  ~", txt[max(0, m.start() - 160): m.end() + 200])
    k += 1
    if k >= n:
        break
print("matches:", len(re.findall(pat, txt, re.I)))
