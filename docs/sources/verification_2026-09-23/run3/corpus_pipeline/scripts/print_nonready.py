import csv, os
R = "<scratchpad>/wt-run3/docs/sources/verification_2026-09-23/run3"
rows = list(csv.DictReader(open(f"{R}/source_catalogue.csv", encoding="utf-8")))
ready = {f[:-5] for f in os.listdir(f"{R}/ready_sources")}
for r in rows:
    if r["id"] in ready:
        continue
    print(f"=== {r['id']} | {r['canton']} | extent={r['default_extent_id']} | auth={r['authority']} | cats={r['categories']} | missing={r['category_missing']}")
    print(f"  data_type: {r['data_type']}")
    print(f"  strategy: {r['fetch_strategy']} | base: {r['base_url']}")
    print(f"  entry_points: {r['entry_points']}")
    print(f"  fetch_config: {r['fetch_config'][:400]}")
    print(f"  readiness: {r['readiness']}")
    print(f"  notes: {r['notes'][:700]}")
    print(f"  report: {r['report']}")
