#!/usr/bin/env python3
"""Grep a stage0 sitemap URL list (local, no network).

Usage: smgrep.py HOSTFILE [-x EXCLUDE_REGEX] [-k N] PATTERN [PATTERN ...]
For each PATTERN (case-insensitive regex) print the count and the N shortest matching URLs.
"""
import re
import sys

SM = "<scratchpad>/stage0/sitemaps/"


def main():
    args = sys.argv[1:]
    host = args.pop(0)
    excl = None
    k = 12
    pats = []
    i = 0
    while i < len(args):
        if args[i] == "-x":
            excl = args[i + 1]; i += 2; continue
        if args[i] == "-k":
            k = int(args[i + 1]); i += 2; continue
        pats.append(args[i]); i += 1
    urls = [u.strip() for u in open(SM + host + ".txt", encoding="utf-8", errors="replace") if u.strip()]
    print(f"### {host}: {len(urls)} URLs")
    for p in pats:
        hits = [u for u in urls if re.search(p, u, re.I) and not (excl and re.search(excl, u, re.I))]
        hits = sorted(set(hits), key=lambda u: (len(u), u))
        print(f"=== {p}: {len(hits)}")
        for u in hits[:k]:
            print("   ", u)


if __name__ == "__main__":
    main()
