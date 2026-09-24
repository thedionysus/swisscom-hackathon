"""grep a saved page (by URL or by file path) for a regex, printing context. offline."""
import json, re, sys, os
S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
target, pat = sys.argv[1], re.compile(sys.argv[2])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
width = int(sys.argv[4]) if len(sys.argv) > 4 else 160
path = idx.get(target, target)
html = open(path, "rb").read().decode("utf-8", errors="replace")
hits = list(pat.finditer(html))
print(f"{target}: {len(hits)} matches")
for m in hits[:n]:
    print("   ...", html[max(0, m.start() - width):m.end() + width].replace("\n", " "), "...")
