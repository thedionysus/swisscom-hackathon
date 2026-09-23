#!/usr/bin/env python3
"""Fetch a LexWork lightweight_index and grep titles; then fetch detail for chosen numbers.

Usage: lexwork_idx.py HOST REGEX [NR ...]
"""
import json
import re
import subprocess
import sys
import time

UA = "Mozilla/5.0 swiss-grounding-check"


def get(url):
    r = subprocess.run(["curl", "-g", "-sL", "-m", "60", "-A", UA, "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    time.sleep(0.5)
    return r.stdout


host, pat = sys.argv[1], sys.argv[2]
nrs = sys.argv[3:]
raw = get(f"https://{host}/api/de/texts_of_law/lightweight_index")
try:
    d = json.loads(raw)
except Exception:
    print("index not JSON:", raw[:300])
    d = []
items = d if isinstance(d, list) else (d.get("texts_of_law") or d.get("items") or d.get("data") or [])
if isinstance(d, dict) and not items:
    # dict keyed by category id -> list of items (or dict with a list)
    for v in d.values():
        if isinstance(v, list):
            items.extend(v)
        elif isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, list):
                    items.extend(vv)
print(f"{host}: index items {len(items)}")
if items:
    print("  first item keys:", list(items[0].keys()) if isinstance(items[0], dict) else type(items[0]))
for it in items:
    if not isinstance(it, dict):
        continue
    t = it.get("title") or ""
    if re.search(pat, t, re.I):
        print("  ", it.get("systematic_number"), "|", t[:150], "| abrogated" if it.get("abrogated") else "")
for nr in nrs:
    raw = get(f"https://{host}/api/de/texts_of_law/{nr}")
    try:
        j = json.loads(raw)
    except Exception:
        print(nr, "detail not JSON:", raw[:200])
        continue
    tol = j.get("text_of_law", j) if isinstance(j, dict) else j
    keys = list(tol.keys())[:30] if isinstance(tol, dict) else []
    print("==", nr, "keys:", keys)
    for k in ["systematic_number", "title", "abbreviation", "canonical_link", "enactment", "is_active", "abrogated"]:
        if isinstance(tol, dict) and k in tol:
            print("    ", k, "=", str(tol[k])[:200])
    s = json.dumps(j, ensure_ascii=False)
    for k in ["version_active_since", "enactment", "valid_from", "date_of_entry_into_force", "in_force"]:
        m = re.search(r'"%s"\s*:\s*"?([^",}]+)' % k, s)
        if m:
            print("    ", k, "~", m.group(1))
