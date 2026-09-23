#!/usr/bin/env python3
"""Sitemap grep: python3 smgrep.py <host.txt> '<label>=<regex>' ... [--x <exclude regex>] [--n N]
Prints the count per pattern and the N shortest matches."""
import os
import re
import sys

SM = "<scratchpad>/stage0/sitemaps"
args = sys.argv[1:]
host = args.pop(0)
excl = None
n = 15
pats = []
i = 0
while i < len(args):
    if args[i] == "--x":
        excl = args[i + 1]
        i += 2
    elif args[i] == "--n":
        n = int(args[i + 1])
        i += 2
    else:
        pats.append(args[i])
        i += 1
urls = [u.strip() for u in open(host if host.startswith("/") or host.startswith(".") else os.path.join(SM, host)) if u.strip()]
print(f"# {host}: {len(urls)} URLs")
for p in pats:
    label, _, rx = p.partition("=")
    hits = [u for u in urls if re.search(rx, u, re.I) and not (excl and re.search(excl, u, re.I))]
    print(f"== {label}: {len(hits)}")
    for u in sorted(set(hits), key=len)[:n]:
        print("   ", u)
