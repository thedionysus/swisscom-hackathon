import csv, os, json
R = "<scratchpad>/wt-run3/docs/sources/verification_2026-09-23/run3"
rows = list(csv.DictReader(open(f"{R}/source_catalogue.csv", encoding="utf-8")))
ready = {f[:-5] for f in os.listdir(f"{R}/ready_sources") if f.endswith(".yaml")}
cat_ids = {r["id"] for r in rows}
print("ready yaml not in catalogue:", sorted(ready - cat_ids))
print("catalogue ids with yaml:", len(cat_ids & ready))
for i, r in enumerate(rows, 1):
    y = "Y" if r["id"] in ready else "-"
    print(f"{i:3} {y} {r['canton'] or '..':3} {r['fetch_strategy'] or '(none)':12} {r['id']:40} | {r['readiness'][:110]}")
