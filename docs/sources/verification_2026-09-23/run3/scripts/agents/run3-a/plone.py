#!/usr/bin/env python3
"""Probe Plone REST content on bl-api.webcloud7.ch (Accept: application/json).

Usage: plone.py [-g REGEX] [-k N] [-i] PATH_OR_URL [...]
Prints status, @type, title, modified/effective, #items, #blocks, words of block text,
and up to N snippets matching REGEX from the block/description text. -i lists child items.
"""
import json
import re
import subprocess
import sys
import time

BASE = "https://bl-api.webcloud7.ch"
UA = "Mozilla/5.0 swiss-grounding-check"


def get(url):
    r = subprocess.run(["curl", "-g", "-sL", "-m", "45", "-A", UA, "-H", "Accept: application/json",
                        "-w", "\n%{http_code}", url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    time.sleep(0.5)
    return code, body


def texts(o, out):
    """Collect human text from Volto blocks (slate 'text', draftjs 'text', 'value' children)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "@components":
                continue
            if k in ("text",) and isinstance(v, str):
                out.append(v)
            elif k == "text" and isinstance(v, dict) and isinstance(v.get("data"), str):
                out.append(re.sub(r"<[^>]+>", " ", v["data"]))
            elif k in ("title", "description", "plaintext") and isinstance(v, str):
                out.append(v)
            else:
                texts(v, out)
    elif isinstance(o, list):
        for x in o:
            texts(x, out)


def main():
    args = sys.argv[1:]
    grep = None
    k = 3
    listing = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-g":
            grep = args[i + 1]; i += 2; continue
        if a == "-k":
            k = int(args[i + 1]); i += 2; continue
        if a == "-i":
            listing = True; i += 1; continue
        url = a if a.startswith("http") else BASE + a
        i += 1
        code, body = get(url)
        try:
            d = json.loads(body)
        except Exception:
            print(code, url, "NOT JSON", body[:150].replace("\n", " "))
            continue
        if not isinstance(d, dict):
            print(code, url, type(d).__name__, len(d))
            continue
        blocks = d.get("blocks") or d.get("slblocks") or {}
        out = []
        texts(blocks, out)
        txt = re.sub(r"\s+", " ", " ".join(out))
        print(f"{code} | {d.get('@type')} | {d.get('title')!r} | modified={d.get('modified')} | "
              f"effective={d.get('effective')} | items={d.get('items_total')} | blocks={len(blocks)} | "
              f"words={len(txt.split())} | {url}")
        if d.get("description"):
            print("   desc:", d["description"][:200])
        if grep:
            n = 0
            for m in re.finditer(grep, txt, re.I):
                print("   ~", txt[max(0, m.start() - 140): m.end() + 180])
                n += 1
                if n >= k:
                    break
            if n == 0:
                print(f"   ~ (no match for {grep})")
        if listing:
            for it in d.get("items", [])[:60]:
                print("     -", it.get("@type"), "|", it.get("@id", "").replace(BASE, ""), "|", it.get("title"))
        if "error" in d or "message" in d:
            print("   error:", str(d.get("message") or d.get("error"))[:200])


if __name__ == "__main__":
    main()
