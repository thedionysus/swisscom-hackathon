#!/usr/bin/env python3
"""i-web page inspector: fetch URL(s) (via probe.fetch, throttled), decode every data-entities JSON table,
print row count, column keys, first N rows (key fields), plus main text after the H1.
Usage: iweb.py [-n N] [-t CHARS] [-g REGEX] URL..."""
import sys, os, re, json, html, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import fetch, analyse, to_text

ap = argparse.ArgumentParser()
ap.add_argument("-n", type=int, default=3)
ap.add_argument("-t", type=int, default=500)
ap.add_argument("-g", "--grep")
ap.add_argument("urls", nargs="+")
a = ap.parse_args()

def strip(v):
    if isinstance(v, str):
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", v))).strip()
    return v

for u in a.urls:
    code, ct, size, final, body, fn = fetch(u)
    title, links, words, txt, raw = analyse(body)
    print(f"== {u} -> {code} {size}B title='{title}' links={links} words={words}")
    i = txt.find("Inhaltsverzeichnis")
    if i >= 0:
        print("   main: " + txt[i + 18:i + 18 + a.t])
    tables = re.findall(r'data-entities="([^"]*)"', raw)
    print(f"   data-entities tables: {len(tables)}")
    for k, t in enumerate(tables):
        try:
            d = json.loads(html.unescape(t))
        except Exception as e:
            print(f"   [table {k}] undecodable ({e}); head={html.unescape(t)[:200]}")
            continue
        rows = d.get("data") if isinstance(d, dict) else d
        if isinstance(d, dict) and rows is None:
            print(f"   [table {k}] dict keys={list(d.keys())[:10]}")
            continue
        print(f"   [table {k}] rows={len(rows)} keys={list(rows[0].keys()) if rows and isinstance(rows[0], dict) else type(rows[0]).__name__ if rows else '-'}")
        ds = [k2 for k2 in (rows[0].keys() if rows and isinstance(rows[0], dict) else []) if k2 in ("_datum-sort", "datum-sort")]
        if ds:
            rows = sorted(rows, key=lambda r: str(r.get(ds[0]) or ""), reverse=True)
            print(f"      (sorted by {ds[0]} desc; newest={rows[0].get(ds[0])}, oldest={rows[-1].get(ds[0])})")
        for r in rows[:a.n]:
            hrefs = sorted(set(re.findall(r'href=\\?"([^"\\]+)', json.dumps(r))))
            if hrefs:
                print("        links: " + ", ".join(hrefs[:4]))
            if isinstance(r, dict):
                print("      - " + " | ".join(f"{kk}={str(strip(vv))[:90]}" for kk, vv in r.items() if vv not in (None, "", [], {}))[:600])
    if a.grep:
        for mm in list(re.finditer(a.grep, txt, re.I))[:3]:
            print("   ~ " + txt[max(0, mm.start() - 120):mm.end() + 200])
